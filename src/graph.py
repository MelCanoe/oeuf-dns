from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    DOMAIN = "domain"
    IP = "ip"


class RelationType(Enum):
    A = "A"
    AAAA = "AAAA"
    MX = "MX"
    CNAME = "CNAME"
    NS = "NS"
    TXT = "TXT"
    SOA = "SOA"
    SRV = "SRV"
    PTR = "PTR"
    PARENT = "parent"
    SUBDOMAIN = "subdomain"


@dataclass
class Node:
    value: str
    node_type: NodeType
    depth: int = 0
    strategy: str = ""


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: RelationType
    info: str = ""


@dataclass
class DNSGraph:
    root: str
    nodes: dict = field(default_factory=dict)
    edges: set = field(default_factory=set)
    explored: set = field(default_factory=set)
    blacklist: list = field(default_factory=list)

    def add_node(self, value: str, node_type: NodeType, depth: int = 0, strategy: str = "") -> bool:
        key = value.lower().rstrip(".")
        for pattern in self.blacklist:
            if pattern in key:
                return False
        if key not in self.nodes:
            self.nodes[key] = Node(key, node_type, depth, strategy)
            return True
        return False

    def add_edge(self, source: str, target: str, relation: RelationType, info: str = "") -> bool:
        edge = Edge(source.lower().rstrip("."), target.lower().rstrip("."), relation, info)
        if edge not in self.edges:
            self.edges.add(edge)
            return True
        return False

    def mark_explored(self, value: str):
        self.explored.add(value.lower().rstrip("."))

    def get_unexplored(self) -> list[str]:
        return [k for k, n in self.nodes.items() if n.node_type == NodeType.DOMAIN and k not in self.explored]

    def get_stats(self) -> dict:
        domains = sum(1 for n in self.nodes.values() if n.node_type == NodeType.DOMAIN)
        ips = sum(1 for n in self.nodes.values() if n.node_type == NodeType.IP)
        return {"domains": domains, "ips": ips, "edges": len(self.edges)}
