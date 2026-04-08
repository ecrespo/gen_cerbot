"""DNS pre-flight validation.

Resolves a domain via ``socket.getaddrinfo`` and compares the resolved IPs
against the set of IPs bound to the local machine. Raises
``DNSValidationError`` when there is no overlap, so the CLI can surface an
actionable error before calling Certbot.
"""

from __future__ import annotations

import socket
from collections.abc import Iterable

from gen_cerbot.core.exceptions import DNSValidationError


class DNSValidator:
    """Verify that a domain resolves to one of the server's local IPs."""

    def __init__(self, local_ips: Iterable[str] | None = None) -> None:
        self._local_ips: set[str] = (
            set(local_ips) if local_ips is not None else self._discover_local_ips()
        )

    @staticmethod
    def _discover_local_ips() -> set[str]:
        """Return the set of non-loopback IPs bound to the local host.

        Uses ``socket.getaddrinfo`` on the local hostname. Loopback addresses
        (127.0.0.0/8, ::1) are excluded because Let's Encrypt will never
        match them against a public domain.
        """
        ips: set[str] = set()
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                ip = str(info[4][0])
                if ip.startswith("127.") or ip == "::1":
                    continue
                ips.add(ip)
        except socket.gaierror:
            pass
        return ips

    @staticmethod
    def _resolve(domain: str) -> set[str]:
        """Resolve ``domain`` to a set of IP strings (IPv4 and IPv6)."""
        try:
            return {str(info[4][0]) for info in socket.getaddrinfo(domain, None)}
        except socket.gaierror as exc:
            raise DNSValidationError(domain) from exc

    def check(self, domain: str, skip: bool = False) -> None:
        """Validate that ``domain`` resolves to one of the local IPs.

        Args:
            domain: Fully qualified domain name to check.
            skip: If True, bypass the check entirely (for ``--skip-dns-check``).

        Raises:
            DNSValidationError: If the domain cannot be resolved or none of
                its resolved IPs match the local host's IPs.
        """
        if skip:
            return

        resolved = self._resolve(domain)
        if not resolved:
            raise DNSValidationError(domain)

        if not resolved & self._local_ips:
            expected = next(iter(resolved))
            raise DNSValidationError(domain, expected_ip=expected)
