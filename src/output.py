import subprocess
import sys
import shutil
from pathlib import Path
from src.graph import DNSGraph, NodeType, RelationType

class TextFormatter:
    C = {
        "reset": "\033[0m", "bold": "\033[1m", 
        "cyan": "\033[36m", "green": "\033[32m", "yellow": "\033[33m", 
        "magenta": "\033[35m", "blue": "\033[34m", "white": "\033[37m", "dim": "\033[2m"
    }

    def format(self, graph: DNSGraph) -> str:
        lines = []
        stats = graph.get_stats()
        
        lines.append(f"\n{self.C['bold']}{self.C['cyan']}==============================================================={self.C['reset']}")
        lines.append(f"{self.C['bold']}{self.C['cyan']}  DNS Map: {graph.root}{self.C['reset']}")
        lines.append(f"{self.C['cyan']}==============================================================={self.C['reset']}")
        lines.append(f"  {self.C['white']}{stats['domains']} domains | {stats['ips']} IPs | {stats['edges']} relations{self.C['reset']}\n")

        domains = sorted([n for n in graph.nodes.values() if n.node_type == NodeType.DOMAIN], key=lambda x: x.value)
        ips = sorted([n for n in graph.nodes.values() if n.node_type == NodeType.IP], key=lambda x: x.value)

        if domains:
            lines.append(f"{self.C['bold']}{self.C['cyan']}  DOMAINS{self.C['reset']}")
            lines.append(f"{self.C['dim']}  -----------------------------------------------{self.C['reset']}")
            for n in domains:
                strat = f" {self.C['dim']}({n.strategy}){self.C['reset']}" if n.strategy and n.strategy != "root" else ""
                lines.append(f"  {self.C['cyan']}*{self.C['reset']} {n.value}{strat}")
            lines.append("")

        if ips:
            lines.append(f"{self.C['bold']}{self.C['green']}  IP ADDRESSES{self.C['reset']}")
            lines.append(f"{self.C['dim']}  -----------------------------------------------{self.C['reset']}")
            for n in ips:
                strat = f" {self.C['dim']}({n.strategy}){self.C['reset']}" if n.strategy else ""
                lines.append(f"  {self.C['green']}*{self.C['reset']} {n.value}{strat}")
            lines.append("")

        rel_groups = {}
        for e in graph.edges:
            rel_groups.setdefault(e.relation.value, []).append(e)

        if rel_groups:
            lines.append(f"{self.C['bold']}{self.C['yellow']}  RELATIONS{self.C['reset']}")
            lines.append(f"{self.C['dim']}  -----------------------------------------------{self.C['reset']}")
            for rel in sorted(rel_groups.keys()):
                edges = rel_groups[rel]
                lines.append(f"  {self.C['yellow']}{rel}{self.C['reset']} ({len(edges)})")
                for e in sorted(edges, key=lambda x: x.source)[:10]:
                    lines.append(f"    {self.C['dim']}->{self.C['reset']} {e.source} -> {e.target}")
                if len(edges) > 10:
                    lines.append(f"    {self.C['dim']}... and {len(edges) - 10} more{self.C['reset']}")
            lines.append("")

        lines.append(f"{self.C['cyan']}==============================================================={self.C['reset']}\n")
        return "\n".join(lines)

class GraphvizFormatter:
    # Color palette for relations
    REL_COLORS = {
        "A": "#424242",         # Dark Grey (IPs)
        "AAAA": "#9E9E9E",      # Light Grey
        "CNAME": "#FF9800",     # Orange
        "NS": "#9C27B0",        # Purple
        "MX": "#2196F3",        # Blue
        "TXT": "#FFC107",       # Amber/Gold
        "SOA": "#795548",       # Brown
        "SRV": "#E91E63",       # Pink
        "PTR": "#00BCD4",       # Cyan
        "PARENT": "#F44336",    # Red
        "SUBDOMAIN": "#4CAF50", # Green
    }

    def format(self, graph: DNSGraph) -> str:
        lines = [
            f'digraph dns_map {{',
            f'  label="DNS Map: {graph.root}";',
            '  layout=twopi;',
            '  ranksep=3.0;',
            '  ratio=auto;',
            '  overlap=false;',
            '  splines=true;',
            f'  root="{self._id(graph.root)}";',
            '  node [fontsize=10, fontname="Arial"];',
            '  edge [fontsize=8, fontname="Arial"];'
        ]
        
        for k, n in graph.nodes.items():
            safe_id = self._id(k)
            safe_label = k.replace('"', '\\"')
            
            if n.node_type == NodeType.DOMAIN:
                shape = "box"
                color = "#4A90D9"
                if k == graph.root:
                    color = "#D32F2F"
                    shape = "doubleoctagon"
            else:
                shape = "ellipse"
                color = "#7CB342"

            lines.append(f'  {safe_id} [label="{safe_label}", shape={shape}, style=filled, fillcolor="{color}", fontcolor=white];')

        for e in graph.edges:
            rel_color = self.REL_COLORS.get(e.relation.value, "#000000")
            lines.append(f'  {self._id(e.source)} -> {self._id(e.target)} [color="{rel_color}", penwidth=1.5];')
        
        lines.append('  subgraph cluster_legend {')
        lines.append('    rank=sink;')
        lines.append('    label="Legend";')
        lines.append('    fontsize=12;')
        lines.append('    style=filled;')
        lines.append('    color="#EEEEEE";')
        lines.append('    node [shape=plaintext, fontsize=10];')
        
        rows = []
        for rel, color in self.REL_COLORS.items():
            rows.append(f'<tr><td bgcolor="{color}" width="20"></td><td>{rel}</td></tr>')
        
        table = f'''<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
            {"".join(rows)}
        </table>>'''
        
        lines.append(f'    key [label={table}];')
        lines.append('  }')

        lines.append("}")
        return "\n".join(lines)

    def _id(self, v: str) -> str:
        s = "".join(c if c.isalnum() else "_" for c in v.lower())
        return f"n{s}" if s and s[0].isdigit() else s

    def to_image(self, content: str, domain: str) -> Path | None:
        out = Path(f"{domain.replace('.', '_')}_dns_map.jpg")
        
        dot_cmd = "dot"
        if not shutil.which("dot"):
            possible_paths = [
                r"C:\Program Files\Graphviz\bin\dot.exe",
                r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
                r"/usr/bin/dot",
                r"/usr/local/bin/dot",
                r"/opt/homebrew/bin/dot"
            ]
            for p in possible_paths:
                if Path(p).exists():
                    dot_cmd = p
                    break
        
        try:
            r = subprocess.run([dot_cmd, "-Tjpg", "-o", str(out)], input=content, capture_output=True, text=True)
            if r.returncode == 0:
                return out
            else:
                print(f"Graphviz Error: {r.stderr}", file=sys.stderr)
                return None
        except FileNotFoundError:
            print("Warning: Graphviz not installed or not found in PATH.", file=sys.stderr)
            return None


class MarkdownFormatter:
    """Generates a comprehensive Markdown report."""

    def format(self, graph: DNSGraph) -> str:
        lines = []
        stats = graph.get_stats()
        
        lines.append(f"# DNS Map Report: {graph.root}")
        lines.append("")
        lines.append("## Summary")
        lines.append(f"- **Domains**: {stats['domains']}")
        lines.append(f"- **IP Addresses**: {stats['ips']}")
        lines.append(f"- **Relations**: {stats['edges']}")
        lines.append("")

        domains = sorted([n for n in graph.nodes.values() if n.node_type == NodeType.DOMAIN], key=lambda x: x.value)
        ips = sorted([n for n in graph.nodes.values() if n.node_type == NodeType.IP], key=lambda x: x.value)

        lines.append("## Domains")
        if domains:
            lines.append("| Domain | Discovery Strategy | Depth |")
            lines.append("|---|---|---|")
            for n in domains:
                strat = n.strategy if n.strategy else "unknown"
                lines.append(f"| `{n.value}` | {strat} | {n.depth} |")
        else:
            lines.append("*No domains found.*")
        lines.append("")

        lines.append("## IP Addresses")
        if ips:
            lines.append("| IP | Discovery Strategy | Depth |")
            lines.append("|---|---|---|")
            for n in ips:
                strat = n.strategy if n.strategy else "unknown"
                lines.append(f"| `{n.value}` | {strat} | {n.depth} |")
        else:
            lines.append("*No IPs found.*")
        lines.append("")

        lines.append("## Relations")
        if graph.edges:
            lines.append("| Source | Relation | Target | Info |")
            lines.append("|---|---|---|---|")
            for e in sorted(graph.edges, key=lambda x: (x.relation.value, x.source)):
                info = e.info if e.info else "-"
                lines.append(f"| `{e.source}` | **{e.relation.value}** | `{e.target}` | {info} |")
        else:
            lines.append("*No relations found.*")
        
        return "\n".join(lines)
