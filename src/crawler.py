from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

from src.client import DNSClient
from src.graph import DNSGraph, NodeType, RelationType
from src.scans import ALL_STRATEGIES

def load_blacklist() -> list[str]:
    path = Path(__file__).parent.parent / "data" / "blacklist.txt"
    if path.exists():
        return [line.strip().lower() for line in path.read_text().splitlines() 
                if line.strip() and not line.startswith("#")]
    return []

class DNSCrawler:
    def __init__(self, max_depth=2, max_workers=5, blacklist=None, verbose=False):
        self.max_depth = max_depth
        self.max_workers = max_workers
        self.verbose = verbose
        self.dns = DNSClient()
        self.strategies = [S(self.dns) for S in ALL_STRATEGIES]
        self.blacklist = blacklist if blacklist is not None else load_blacklist()

    def crawl(self, domain: str) -> DNSGraph:
        domain = domain.lower().rstrip(".")
        graph = DNSGraph(root=domain, blacklist=self.blacklist)
        graph.add_node(domain, NodeType.DOMAIN, depth=0, strategy="root")

        for depth in range(self.max_depth + 1):
            to_explore = [d for d in graph.get_unexplored() if graph.nodes[d].depth == depth]
            if not to_explore:
                break
            self._log(f"Depth {depth}: {len(to_explore)} domains")

            if self.max_workers > 1:
                with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                    futures = {ex.submit(self._explore, d, graph, depth): d for d in to_explore}
                    for f in as_completed(futures):
                        try:
                            f.result()
                        except Exception as e:
                            self._log(f"Error: {e}")
            else:
                for d in to_explore:
                    self._explore(d, graph, depth)

        return graph

    def _explore(self, domain: str, graph: DNSGraph, depth: int):
        graph.mark_explored(domain)
        for strategy in self.strategies:
            try:
                for r in strategy.discover(domain, graph):
                    val = r.value.lower().rstrip(".")
                    if val == domain:
                        continue
                    node_type = NodeType.IP if r.is_ip else NodeType.DOMAIN
                    if graph.add_node(val, node_type, depth + 1, strategy.name):
                        self._log(f"  + {val} ({r.relation_type})")
                    try:
                        rel = RelationType[r.relation_type.upper()]
                    except KeyError:
                        rel = RelationType.A
                    graph.add_edge(domain, val, rel, r.extra_info)
            except Exception as e:
                self._log(f"  {strategy.name}: {e}")

    def _log(self, msg: str):
        if self.verbose:
            print(msg, file=sys.stderr)
