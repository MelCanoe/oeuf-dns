from dns import resolver
from dns.exception import DNSException


class DNSClient:
    def __init__(self, timeout: float = 2.0):
        self._resolver = resolver.Resolver()
        self._resolver.timeout = timeout
        self._resolver.lifetime = timeout * 2

    def query(self, domain: str, rtype: str = "A") -> list[str]:
        try:
            return [str(r) for r in self._resolver.resolve(domain, rtype)]
        except DNSException:
            return []
