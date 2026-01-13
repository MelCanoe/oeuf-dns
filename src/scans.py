import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from ipaddress import ip_address, IPv4Address

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

        for ip in self.dns.query(target, "AAAA"):
            results.append(DiscoveryResult(ip, True, "AAAA", target))

        for mx in self.dns.query(target, "MX"):
            parts = mx.split()
            if len(parts) >= 2:
                results.append(DiscoveryResult(parts[-1].rstrip("."), False, "MX", target, f"pri:{parts[0]}"))

        for ns in self.dns.query(target, "NS"):
            results.append(DiscoveryResult(ns.rstrip("."), False, "NS", target))

        for soa in self.dns.query(target, "SOA"):
            parts = soa.split()
            if parts:
                results.append(DiscoveryResult(parts[0].rstrip("."), False, "SOA", target))

        for cname in self.dns.query(target, "CNAME"):
            results.append(DiscoveryResult(cname.rstrip("."), False, "CNAME", target))

        return results

class ParseTXT(Strategy):
    name = "parse_txt"

    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []

        for record in self.dns.query(target, "TXT"):
            record = record.strip('"\'')
            if record.lower().startswith("v=spf1"):
                results.extend(self._parse_spf(record, target))
            elif record.lower().startswith("v=dmarc1"):
                results.extend(self._parse_dmarc(record, target))

        for record in self.dns.query(f"_dmarc.{target}", "TXT"):
            record = record.strip('"\'')
            if record.lower().startswith("v=dmarc1"):
                results.extend(self._parse_dmarc(record, target))

        return results

    def _parse_spf(self, record: str, source: str) -> list[DiscoveryResult]:
        results = []
        for match in re.finditer(r'ip4:([0-9\./]+)', record, re.I):
            results.append(DiscoveryResult(match.group(1), True, "TXT", source, "SPF"))
        for match in re.finditer(r'include:([a-zA-Z0-9\.-]+)', record, re.I):
            domain = match.group(1).rstrip(".")
            if self._is_resolvable(domain):
                results.append(DiscoveryResult(domain, False, "TXT", source, "SPF"))
        for match in re.finditer(r'redirect=([^\s]+)', record, re.I):
            domain = match.group(1).rstrip(".")
            if self._is_resolvable(domain):
                results.append(DiscoveryResult(domain, False, "TXT", source, "SPF"))
        return results

    def _parse_dmarc(self, record: str, source: str) -> list[DiscoveryResult]:
        results = []
        for match in re.finditer(r'ru[af]=mailto:([^;,\s]+)', record, re.I):
            email = match.group(1)
            if "@" in email:
                domain = email.split("@")[1].rstrip(".")
                if self._is_resolvable(domain):
                    results.append(DiscoveryResult(domain, False, "TXT", source, "DMARC"))
        return results

    def _is_resolvable(self, domain: str) -> bool:
        """Check if a domain has an A record."""
        return bool(self.dns.query(domain, "A"))

class CrawlTLD(Strategy):
    name = "crawl_tld"

    MULTI_TLDS = {"gouv.fr", "co.uk", "com.au", "co.jp", "com.br", "com.cn", "co.nz", "co.za", "github.io", "herokuapp.com", "azurewebsites.net"}

    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        parts = target.lower().rstrip(".").split(".")
        if len(parts) <= 2:
            return results

        tld_len = self._tld_length(parts)
        for i in range(1, len(parts) - tld_len):
            parent = ".".join(parts[i:])
            if self.dns.query(parent, "NS"):
                results.append(DiscoveryResult(parent, False, "PARENT", target, "parent"))
        return results

    def _tld_length(self, parts: list[str]) -> int:
        for length in range(min(3, len(parts) - 1), 0, -1):
            if ".".join(parts[-length:]) in self.MULTI_TLDS:
                return length
        return 1

class ReverseDNS(Strategy):
    name = "reverse_dns"

    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        for ip in self.dns.query(target, "A"):
            for ptr in self.dns.reverse_lookup(ip):
                results.append(DiscoveryResult(ptr.rstrip("."), False, "PTR", target, f"rev:{ip}"))
        return results

class ScanSRV(Strategy):
    name = "scan_srv"
    
    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        services = self._load_data("srv_services.txt") or [
            "_ldap._tcp", "_kerberos._tcp", "_sip._tcp", "_xmpp-client._tcp", "_autodiscover._tcp"
        ]
        
        for svc in services:
            for srv_target, port, _, _ in self.dns.query_srv(svc, target):
                if srv_target and srv_target != target:
                    results.append(DiscoveryResult(srv_target, False, "SRV", target, f"{svc}:{port}"))
        return results

    def _load_data(self, filename: str) -> list[str]:
        path = Path(__file__).parents[1].parent / "data" / filename
        if path.exists():
            return [line.strip() for line in path.read_text().splitlines() 
                    if line.strip() and not line.startswith("#")]
        return []

class IPNeighbors(Strategy):
    name = "ip_neighbors"

    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        for ip in self.dns.query(target, "A"):
            try:
                ip_obj = ip_address(ip)
                if isinstance(ip_obj, IPv4Address):
                    for offset in [-1, 1, -2, 2]:
                        neighbor = ip_address(int(ip_obj) + offset)
                        if (int(ip_obj) & 0xFFFFFF00) == (int(neighbor) & 0xFFFFFF00):
                            for ptr in self.dns.reverse_lookup(str(neighbor)):
                                results.append(DiscoveryResult(ptr.rstrip("."), False, "PTR", target, f"neighbor:{neighbor}"))
                                if len(results) >= 5:
                                    return results
            except:
                pass
        return results

class SubdomainEnum(Strategy):
    name = "subdomain_enum"

    def discover(self, target: str, graph) -> list[DiscoveryResult]:
        results = []
        target = target.lower().rstrip(".")
        subs = self._load_data("subdomains.txt") or [
            "www", "api", "mail", "smtp", "ftp", "admin", "blog", "dev", "staging", "test", "cdn", "static"
        ]
        
        for sub in subs:
            full = f"{sub}.{target}"
            if self.dns.query(full, "A") or self.dns.query(full, "CNAME"):
                results.append(DiscoveryResult(full, False, "SUBDOMAIN", target))
        return results

    def _load_data(self, filename: str) -> list[str]:
        path = Path(__file__).parents[1].parent / "data" / filename
        if path.exists():
            return [line.strip() for line in path.read_text().splitlines() 
                    if line.strip() and not line.startswith("#")]
        return []

ALL_STRATEGIES = [BasicDNS, ParseTXT, CrawlTLD, ReverseDNS, ScanSRV, IPNeighbors, SubdomainEnum]
