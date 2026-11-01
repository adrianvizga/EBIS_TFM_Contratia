
import logging
import ipaddress
from fastapi import Request
from slowapi import Limiter
from core.config import settings

logger = logging.getLogger(__name__)

UNKNOWN_CLIENT = "unknown"


def _parse_ip(value: str | None):
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _trusted_proxy_networks():
    networks = []
    for proxy in settings.trusted_proxies:
        try:
            networks.append(ipaddress.ip_network(proxy, strict=False))
        except ValueError:
            logger.warning("Trusted proxy ignorado por formato invalido: %s", proxy)
    return networks


def _is_trusted_proxy(host: str | None) -> bool:
    client_ip = _parse_ip(host)
    if not client_ip:
        return False
    return any(client_ip in network for network in _trusted_proxy_networks())


def _first_forwarded_ip(header_value: str | None):
    if not header_value:
        return None
    for part in header_value.split(","):
        forwarded_ip = _parse_ip(part)
        if forwarded_ip:
            return str(forwarded_ip)
    return None


def get_rate_limit_key(request: Request) -> str:
    peer_host = request.client.host if request.client else None
    if _is_trusted_proxy(peer_host):
        forwarded_for = _first_forwarded_ip(request.headers.get("x-forwarded-for"))
        if forwarded_for:
            return forwarded_for

        real_ip = _parse_ip(request.headers.get("x-real-ip"))
        if real_ip:
            return str(real_ip)

    return peer_host or UNKNOWN_CLIENT


limiter = Limiter(key_func=get_rate_limit_key)
logger.debug("Rate limiter inicializado")
