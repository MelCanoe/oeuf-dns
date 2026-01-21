from src.graph import DNSGraph, NodeType, RelationType
from src.crawler import DNSCrawler

def test_graph_basics():
    g = DNSGraph("example.com")
    g.add_node("example.com", NodeType.DOMAIN)
    g.add_node("1.1.1.1", NodeType.IP)
    
    g.add_edge("example.com", "1.1.1.1", RelationType.A)
    
    assert len(g.nodes) == 2
    assert len(g.edges) == 1

def test_crawler_init():
    c = DNSCrawler(max_depth=1)
    assert c.max_depth == 1
    assert len(c.strategies) > 0

def test_simple_scan():
    crawler = DNSCrawler(max_depth=0)
    assert crawler is not None
