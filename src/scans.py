from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveryResult:
    value: str
    is_ip: bool
    relation_type: str
    source: str
    extra_info: str = ""


class Strategy(ABC):
    name: str = "base"
    def __init__(self, dns_client):
        self.dns = dns_client
    @abstractmethod
    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        pass


class BasicDNS(Strategy):
    name = "basic_dns"
    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        target = target.lower().rstrip(".")
        for ip in self.dns.query(target, "A"):
            results.append(DiscoveryResult(ip, True, "A", target))
        for ns in self.dns.query(target, "NS"):
            results.append(DiscoveryResult(ns.rstrip("."), False, "NS", target))
        return results


class SubdomainEnum(Strategy):
    name = "subdomain_enum"
    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        target = target.lower().rstrip(".")
        path = Path(__file__).parents[1].parent / "data" / "subdomains.txt"
        subs = [line.strip() for line in path.read_text().splitlines() if line.strip()] if path.exists() else ["www"]
        for sub in subs:
            full = f"{sub}.{target}"
            if self.dns.query(full, "A"):
                results.append(DiscoveryResult(full, False, "SUBDOMAIN", target))
        return results


ALL_STRATEGIES = [BasicDNS, SubdomainEnum]
