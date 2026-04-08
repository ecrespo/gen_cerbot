"""Unit tests for CertbotManager.

Covers the full certbot CLI surface exposed by the manager:
request / verify_service / renew / renew_all / revoke / delete /
get_certificates (with prod, staging and empty fixtures).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gen_cerbot.certbot.manager import CertbotCertificate, CertbotManager
from gen_cerbot.core.exceptions import (
    CertbotError,
    ServerConfigError,
    SudoError,
)
from gen_cerbot.domain.models import DistroFamily, ServerType
from gen_cerbot.utils.system import CommandResult
from tests.conftest import MockSystemRunner

FIXTURES = Path(__file__).parent.parent / "fixtures" / "certbot"


@pytest.fixture
def certificates_prod() -> str:
    return (FIXTURES / "certificates_prod.txt").read_text()


@pytest.fixture
def certificates_staging() -> str:
    return (FIXTURES / "certificates_staging.txt").read_text()


@pytest.fixture
def certificates_empty() -> str:
    return (FIXTURES / "certificates_empty.txt").read_text()


# ---------------------------------------------------------------------------
# request()
# ---------------------------------------------------------------------------


class TestRequest:
    def test_nginx_production_command(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).request(
            "example.com", "admin@example.com", ServerType.NGINX
        )
        call = mock_runner.calls[0]
        assert call["cmd"] == [
            "sudo",
            "certbot",
            "--nginx",
            "--non-interactive",
            "--agree-tos",
            "--email",
            "admin@example.com",
            "-d",
            "example.com",
        ]
        assert call["sudo"] is True

    def test_apache_production_command(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).request(
            "example.com", "admin@example.com", ServerType.APACHE
        )
        assert "--apache" in mock_runner.calls[0]["cmd"]  # type: ignore[operator]

    def test_staging_appends_flag(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).request(
            "stg.example.com", "a@b.c", ServerType.NGINX, staging=True
        )
        cmd = mock_runner.calls[0]["cmd"]
        assert "--staging" in cmd  # type: ignore[operator]
        # --staging is appended at the end
        assert cmd[-1] == "--staging"  # type: ignore[index]

    def test_non_staging_omits_flag(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).request(
            "example.com", "a@b.c", ServerType.NGINX
        )
        assert "--staging" not in mock_runner.calls[0]["cmd"]  # type: ignore[operator]

    def test_traefik_rejected(self, mock_runner: MockSystemRunner) -> None:
        with pytest.raises(CertbotError, match="Traefik"):
            CertbotManager(runner=mock_runner).request(
                "x.io", "a@b.c", ServerType.TRAEFIK
            )
        assert mock_runner.calls == []

    def test_runner_failure_wrapped_as_certbot_error(
        self, mock_runner: MockSystemRunner
    ) -> None:
        mock_runner.set_response("sudo certbot", CommandResult(1, "", "boom"))
        with pytest.raises(CertbotError, match=r"example\.com"):
            CertbotManager(runner=mock_runner).request(
                "example.com", "a@b.c", ServerType.NGINX
            )


# ---------------------------------------------------------------------------
# verify_service()
# ---------------------------------------------------------------------------


class TestVerifyService:
    def test_nginx_uses_nginx_unit(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).verify_service(
            ServerType.NGINX, DistroFamily.DEBIAN
        )
        assert mock_runner.calls[0]["cmd"] == [
            "sudo",
            "systemctl",
            "status",
            "nginx",
            "--no-pager",
        ]
        assert mock_runner.calls[0]["check"] is False

    def test_apache_on_debian_uses_apache2(
        self, mock_runner: MockSystemRunner
    ) -> None:
        CertbotManager(runner=mock_runner).verify_service(
            ServerType.APACHE, DistroFamily.DEBIAN
        )
        assert "apache2" in mock_runner.calls[0]["cmd"]  # type: ignore[operator]

    def test_apache_on_redhat_uses_httpd(
        self, mock_runner: MockSystemRunner
    ) -> None:
        CertbotManager(runner=mock_runner).verify_service(
            ServerType.APACHE, DistroFamily.REDHAT
        )
        assert "httpd" in mock_runner.calls[0]["cmd"]  # type: ignore[operator]

    def test_apache_on_suse_uses_httpd(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).verify_service(
            ServerType.APACHE, DistroFamily.SUSE
        )
        assert "httpd" in mock_runner.calls[0]["cmd"]  # type: ignore[operator]

    def test_traefik_uses_docker_compose_ps_without_sudo(
        self, mock_runner: MockSystemRunner
    ) -> None:
        CertbotManager(runner=mock_runner).verify_service(
            ServerType.TRAEFIK, DistroFamily.DEBIAN
        )
        assert mock_runner.calls[0]["cmd"] == ["docker", "compose", "ps"]
        assert mock_runner.calls[0]["sudo"] is False

    def test_inactive_service_raises(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response(
            "sudo systemctl", CommandResult(3, "", "inactive (dead)")
        )
        with pytest.raises(ServerConfigError, match="nginx"):
            CertbotManager(runner=mock_runner).verify_service(
                ServerType.NGINX, DistroFamily.DEBIAN
            )


# ---------------------------------------------------------------------------
# renew / renew_all
# ---------------------------------------------------------------------------


class TestRenew:
    def test_renew_single_command(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).renew("example.com")
        assert mock_runner.calls[0]["cmd"] == [
            "sudo",
            "certbot",
            "renew",
            "--cert-name",
            "example.com",
            "--non-interactive",
        ]

    def test_renew_all_command(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).renew_all()
        assert mock_runner.calls[0]["cmd"] == [
            "sudo",
            "certbot",
            "renew",
            "--non-interactive",
        ]

    def test_renew_failure_wrapped(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response("sudo certbot renew", CommandResult(1, "", "err"))
        with pytest.raises(CertbotError, match=r"example\.com"):
            CertbotManager(runner=mock_runner).renew("example.com")

    def test_renew_all_failure_wrapped(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response("sudo certbot renew", CommandResult(1, "", "err"))
        with pytest.raises(CertbotError, match=r"renew \(all\)"):
            CertbotManager(runner=mock_runner).renew_all()


# ---------------------------------------------------------------------------
# revoke / delete
# ---------------------------------------------------------------------------


class TestRevokeDelete:
    def test_revoke_command_preserves_local_files(
        self, mock_runner: MockSystemRunner
    ) -> None:
        CertbotManager(runner=mock_runner).revoke("example.com")
        cmd = mock_runner.calls[0]["cmd"]
        assert "--no-delete-after-revoke" in cmd  # type: ignore[operator]
        assert "--cert-name" in cmd  # type: ignore[operator]
        assert "example.com" in cmd  # type: ignore[operator]

    def test_delete_command(self, mock_runner: MockSystemRunner) -> None:
        CertbotManager(runner=mock_runner).delete("example.com")
        assert mock_runner.calls[0]["cmd"] == [
            "sudo",
            "certbot",
            "delete",
            "--cert-name",
            "example.com",
            "--non-interactive",
        ]

    def test_revoke_failure_wrapped(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response("sudo certbot revoke", CommandResult(1, "", "err"))
        with pytest.raises(CertbotError, match="revoke"):
            CertbotManager(runner=mock_runner).revoke("example.com")

    def test_delete_failure_wrapped(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response("sudo certbot delete", CommandResult(1, "", "err"))
        with pytest.raises(CertbotError, match="delete"):
            CertbotManager(runner=mock_runner).delete("example.com")


# ---------------------------------------------------------------------------
# get_certificates()
# ---------------------------------------------------------------------------


class TestGetCertificates:
    def test_parse_production_fixture(
        self, mock_runner: MockSystemRunner, certificates_prod: str
    ) -> None:
        mock_runner.set_response(
            "sudo certbot certificates", CommandResult(0, certificates_prod, "")
        )
        certs = CertbotManager(runner=mock_runner).get_certificates()

        assert len(certs) == 2
        first, second = certs

        assert first.name == "example.com"
        assert first.domains == ["example.com", "www.example.com"]
        assert first.serial == "3a1b2c3d4e5f6789abcdef0123456789"
        assert (
            first.certificate_path
            == "/etc/letsencrypt/live/example.com/fullchain.pem"
        )
        assert (
            first.private_key_path
            == "/etc/letsencrypt/live/example.com/privkey.pem"
        )
        assert first.expiry is not None
        assert first.expiry.year == 2026
        assert first.expiry.month == 6
        assert first.expiry.day == 30

        assert second.name == "api.example.com"
        assert second.domains == ["api.example.com"]
        assert second.expiry is not None and second.expiry.day == 15

    def test_parse_staging_fixture(
        self, mock_runner: MockSystemRunner, certificates_staging: str
    ) -> None:
        mock_runner.set_response(
            "sudo certbot certificates", CommandResult(0, certificates_staging, "")
        )
        certs = CertbotManager(runner=mock_runner).get_certificates()

        assert len(certs) == 1
        (cert,) = certs
        assert cert.name == "staging.example.com"
        assert cert.domains == ["staging.example.com"]
        assert cert.expiry is not None
        assert cert.expiry.hour == 9
        assert cert.expiry.minute == 30

    def test_parse_empty_fixture(
        self, mock_runner: MockSystemRunner, certificates_empty: str
    ) -> None:
        mock_runner.set_response(
            "sudo certbot certificates", CommandResult(0, certificates_empty, "")
        )
        certs = CertbotManager(runner=mock_runner).get_certificates()
        assert certs == []

    def test_runner_failure_wrapped(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response(
            "sudo certbot certificates", CommandResult(1, "", "permission denied")
        )
        with pytest.raises(CertbotError, match="certbot certificates failed"):
            CertbotManager(runner=mock_runner).get_certificates()

    def test_parse_output_static_is_pure(self, certificates_prod: str) -> None:
        """The parser is a static method — no runner, no side effects."""
        certs = CertbotManager._parse_certificates_output(certificates_prod)
        assert all(isinstance(c, CertbotCertificate) for c in certs)
        assert len(certs) == 2

    def test_parse_unknown_fields_ignored(self) -> None:
        output = (
            "  Certificate Name: weird.example.com\n"
            "    Serial Number: deadbeef\n"
            "    Future Field: should-be-ignored\n"
            "    Domains: weird.example.com\n"
            "    Expiry Date: 2099-01-01 00:00:00+00:00 (VALID)\n"
            "    Certificate Path: /etc/letsencrypt/live/weird.example.com/fullchain.pem\n"
            "    Private Key Path: /etc/letsencrypt/live/weird.example.com/privkey.pem\n"
        )
        certs = CertbotManager._parse_certificates_output(output)
        assert len(certs) == 1
        assert certs[0].name == "weird.example.com"
        assert certs[0].expiry is not None and certs[0].expiry.year == 2099

    def test_parse_malformed_expiry_yields_none(self) -> None:
        output = (
            "  Certificate Name: bad.example.com\n"
            "    Domains: bad.example.com\n"
            "    Expiry Date: not-a-date\n"
        )
        certs = CertbotManager._parse_certificates_output(output)
        assert len(certs) == 1
        assert certs[0].expiry is None


# ---------------------------------------------------------------------------
# Error preservation
# ---------------------------------------------------------------------------


def test_request_preserves_cause(mock_runner: MockSystemRunner) -> None:
    mock_runner.set_response("sudo certbot", CommandResult(1, "", "rate limit"))
    with pytest.raises(CertbotError) as exc_info:
        CertbotManager(runner=mock_runner).request(
            "example.com", "a@b.c", ServerType.NGINX
        )
    assert isinstance(exc_info.value.__cause__, SudoError)
