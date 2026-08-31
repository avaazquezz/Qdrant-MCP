"""Blocks BYO Qdrant URLs that resolve to a private/internal address.

`BYOQdrantMiddleware` connects to whatever URL an untrusted public caller
supplies, from a host that also runs other clients' services on Docker
internal networks — an unchecked target turns this server into an SSRF
pivot. Re-resolves on every call (never caches a URL as "already cleared")
because that is exactly what defeats DNS rebinding: a hostname that resolves
publicly the first time and privately afterwards.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class PrivateHostError(ValueError):
    """Raised when a caller-supplied Qdrant URL is not safely public."""


async def assert_public_qdrant_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise PrivateHostError(f"Qdrant URL must be http:// or https://, got: {url!r}")
    hostname = parsed.hostname
    if not hostname:
        raise PrivateHostError(f"Qdrant URL has no host: {url!r}")

    try:
        infos = await asyncio.get_running_loop().getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise PrivateHostError(f"Could not resolve host {hostname!r}: {exc}") from exc

    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private:
            raise PrivateHostError(
                f"Qdrant URL host {hostname!r} resolves to a private/internal "
                f"address ({sockaddr[0]}); only publicly reachable Qdrant "
                "instances are allowed."
            )
