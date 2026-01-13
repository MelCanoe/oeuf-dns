from dns import resolver, reversename
from dns.exception import DNSException
from ipaddress import ip_address

class DNSClient:
    def __init__(self, timeout: float = 2.0):
        self._resolver = resolver.Resolver()
        self._resolver.timeout = timeout
        self._resolver.lifetime = timeout * 2
        self._cache = {}

    def query(self, domain: str, rtype: str = "A") -> list[str]:
        key = (domain.lower(), rtype.upper())
        if key in self._cache:
            return self._cache[key]
        try:
            results = [str(r) for r in self._resolver.resolve(domain, rtype)]
            self._cache[key] = results
            return results
        except DNSException:
            self._cache[key] = []
            return []

    def reverse_lookup(self, ip: str) -> list[str]:
        key = (ip, "PTR")
        if key in self._cache:
            return self._cache[key]
        try:
            rev = reversename.from_address(ip)
            results = [str(r).rstrip(".") for r in self._resolver.resolve(rev, "PTR")]
            self._cache[key] = results
            return results
        except DNSException:
            self._cache[key] = []
            return []

    def query_srv(self, service: str, domain: str) -> list[tuple]:
        full = f"{service}.{domain}"
        key = (full.lower(), "SRV")
        if key in self._cache:
            return self._cache[key]
        try:
            results = [(str(r.target).rstrip("."), r.port, r.priority, r.weight) 
                       for r in self._resolver.resolve(full, "SRV")]
            self._cache[key] = results
            return results
        except DNSException:
            self._cache[key] = []
            return []

def is_ip(value: str) -> bool:
    try:
        ip_address(value)
        return True
    except ValueError:
        return False
