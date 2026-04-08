"""Unit tests for DNSValidator (TC-014, TC-015, TC-016)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gen_cerbot.core.exceptions import DNSValidationError
from gen_cerbot.utils.dns import DNSValidator


def _addrinfo(ip: str) -> tuple[int, int, int, str, tuple[str, int]]:
    """Build a single ``socket.getaddrinfo``-shaped tuple for the given IP."""
    return (2, 1, 6, "", (ip, 0))


class TestDNSValidator:
    def test_dns_ok(self) -> None:
        """TC-014: domain resolves to one of the server's local IPs."""
        validator = DNSValidator(local_ips={"203.0.113.5"})
        with patch(
            "gen_cerbot.utils.dns.socket.getaddrinfo",
            return_value=[_addrinfo("203.0.113.5")],
        ) as mock_gai:
            validator.check("example.com")
            mock_gai.assert_called_once_with("example.com", None)

    def test_dns_ok_with_multiple_resolved_ips(self) -> None:
        """Any overlap between resolved and local IPs is sufficient."""
        validator = DNSValidator(local_ips={"203.0.113.5"})
        with patch(
            "gen_cerbot.utils.dns.socket.getaddrinfo",
            return_value=[_addrinfo("198.51.100.1"), _addrinfo("203.0.113.5")],
        ):
            validator.check("example.com")

    def test_dns_mismatch_raises(self) -> None:
        """TC-015: resolved IP differs from local IPs → DNSValidationError."""
        validator = DNSValidator(local_ips={"203.0.113.5"})
        with (
            patch(
                "gen_cerbot.utils.dns.socket.getaddrinfo",
                return_value=[_addrinfo("198.51.100.42")],
            ),
            pytest.raises(DNSValidationError) as exc_info,
        ):
            validator.check("example.com")

        err = exc_info.value
        assert err.domain == "example.com"
        assert err.expected_ip == "198.51.100.42"
        assert "example.com" in str(err)
        assert "198.51.100.42" in str(err)

    def test_skip_dns_check_bypasses(self) -> None:
        """TC-016: skip=True must not call socket.getaddrinfo at all."""
        validator = DNSValidator(local_ips={"203.0.113.5"})
        with patch("gen_cerbot.utils.dns.socket.getaddrinfo") as mock_gai:
            validator.check("anything.invalid", skip=True)
            mock_gai.assert_not_called()

    def test_resolution_failure_raises(self) -> None:
        """gaierror during resolution surfaces as DNSValidationError."""
        import socket

        validator = DNSValidator(local_ips={"203.0.113.5"})
        with (
            patch(
                "gen_cerbot.utils.dns.socket.getaddrinfo",
                side_effect=socket.gaierror("name or service not known"),
            ),
            pytest.raises(DNSValidationError) as exc_info,
        ):
            validator.check("no-such-domain.invalid")
        assert exc_info.value.domain == "no-such-domain.invalid"

    def test_discover_local_ips_excludes_loopback(self) -> None:
        """Auto-discovery must drop 127.0.0.1 and ::1."""
        with (
            patch(
                "gen_cerbot.utils.dns.socket.gethostname",
                return_value="host.local",
            ),
            patch(
                "gen_cerbot.utils.dns.socket.getaddrinfo",
                return_value=[
                    _addrinfo("127.0.0.1"),
                    _addrinfo("::1"),
                    _addrinfo("203.0.113.5"),
                ],
            ),
        ):
            validator = DNSValidator()
        assert validator._local_ips == {"203.0.113.5"}

    def test_discover_local_ips_handles_gaierror(self) -> None:
        """If hostname lookup fails, local_ips is empty (no crash)."""
        import socket

        with (
            patch(
                "gen_cerbot.utils.dns.socket.gethostname",
                return_value="host.local",
            ),
            patch(
                "gen_cerbot.utils.dns.socket.getaddrinfo",
                side_effect=socket.gaierror("boom"),
            ),
        ):
            validator = DNSValidator()
        assert validator._local_ips == set()
