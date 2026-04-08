"""Certbot lifecycle manager.

Wraps the ``certbot`` CLI for certificate request, renewal, revocation and
listing. All commands are executed through :class:`SystemRunner` so sudo is
handled uniformly and tests can mock subprocess calls.

Traefik is intentionally **not** supported here — ACME is configured natively
inside ``traefik.yml`` and never goes through certbot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from gen_cerbot.core.exceptions import (
    CertbotError,
    CommandError,
    ServerConfigError,
    SudoError,
)
from gen_cerbot.domain.models import DistroFamily, ServerType
from gen_cerbot.utils.system import SystemRunner


@dataclass
class CertbotCertificate:
    """Lightweight view of a cert as reported by ``certbot certificates``.

    This mirrors only the fields certbot actually prints, so it is distinct
    from :class:`gen_cerbot.domain.models.CertificateRecord` (which is the
    richer record persisted to the local registry).
    """

    name: str
    domains: list[str] = field(default_factory=list)
    expiry: datetime | None = None
    certificate_path: str = ""
    private_key_path: str = ""
    serial: str = ""


class CertbotManager:
    """Orchestrates certbot invocations for the supported providers."""

    def __init__(self, runner: SystemRunner | None = None) -> None:
        self._runner = runner or SystemRunner()

    def request(
        self,
        domain: str,
        email: str,
        server_type: ServerType,
        staging: bool = False,
    ) -> None:
        """Request a certificate for ``domain`` via certbot.

        Builds the command per server:
          * Nginx  → ``sudo certbot --nginx ...``
          * Apache → ``sudo certbot --apache ...``

        Always appends ``--non-interactive --agree-tos --email <email>
        -d <domain>``; adds ``--staging`` when ``staging=True`` so CI
        pipelines can exercise the flow without hitting Let's Encrypt rate
        limits.

        Args:
            domain: Fully qualified domain name to request the cert for.
            email: Contact email required by Let's Encrypt.
            server_type: Target web server. ``TRAEFIK`` is rejected because
                Traefik handles ACME natively.
            staging: If True, use the Let's Encrypt staging environment.

        Raises:
            CertbotError: If ``server_type`` is Traefik, or if certbot exits
                with a non-zero status code.
        """
        plugin_flag = self._plugin_flag(server_type)

        cmd = [
            "certbot",
            plugin_flag,
            "--non-interactive",
            "--agree-tos",
            "--email",
            email,
            "-d",
            domain,
        ]
        if staging:
            cmd.append("--staging")

        try:
            self._runner.run(cmd, sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(
                f"certbot request failed for '{domain}' ({server_type.value}): {exc}"
            ) from exc

    def renew(self, domain: str) -> None:
        """Renew a single certificate by domain (certbot ``--cert-name``).

        Certbot only renews certificates that are within 30 days of
        expiration; calling this before that window is a no-op and still
        exits 0, which makes the operation idempotent.

        Args:
            domain: Certificate name (``--cert-name``) as shown by
                ``certbot certificates``.

        Raises:
            CertbotError: If certbot exits with a non-zero status code.
        """
        cmd = [
            "certbot",
            "renew",
            "--cert-name",
            domain,
            "--non-interactive",
        ]
        try:
            self._runner.run(cmd, sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(f"certbot renew failed for '{domain}': {exc}") from exc

    def renew_all(self) -> None:
        """Renew every certificate managed by certbot on this host.

        Equivalent to ``sudo certbot renew --non-interactive``. Intended
        for cron-driven bulk renewals.

        Raises:
            CertbotError: If certbot exits with a non-zero status code.
        """
        cmd = ["certbot", "renew", "--non-interactive"]
        try:
            self._runner.run(cmd, sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(f"certbot renew (all) failed: {exc}") from exc

    def get_certificates(self) -> list[CertbotCertificate]:
        """Return all certificates known to certbot on this host.

        Runs ``sudo certbot certificates`` and parses the human-readable
        output into :class:`CertbotCertificate` entries. Returns an empty
        list when certbot reports no certificates.

        Raises:
            CertbotError: If ``certbot certificates`` exits with a non-zero
                status code.
        """
        try:
            result = self._runner.run(["certbot", "certificates"], sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(f"certbot certificates failed: {exc}") from exc

        return self._parse_certificates_output(result.stdout)

    @staticmethod
    def _parse_certificates_output(output: str) -> list[CertbotCertificate]:
        """Parse the human-readable ``certbot certificates`` output.

        The output follows a stable shape:

            Certificate Name: example.com
              Serial Number: <hex>
              Domains: example.com www.example.com
              Expiry Date: 2026-06-30 12:00:00+00:00 (VALID: 89 days)
              Certificate Path: /etc/letsencrypt/live/example.com/fullchain.pem
              Private Key Path: /etc/letsencrypt/live/example.com/privkey.pem

        Blocks are separated by ``Certificate Name:``. Fields unknown to
        this parser are simply ignored.
        """
        certs: list[CertbotCertificate] = []
        current: CertbotCertificate | None = None

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("Certificate Name:"):
                if current is not None:
                    certs.append(current)
                current = CertbotCertificate(name=line.split(":", 1)[1].strip())
                continue

            if current is None:
                continue

            if line.startswith("Domains:"):
                current.domains = line.split(":", 1)[1].split()
            elif line.startswith("Serial Number:"):
                current.serial = line.split(":", 1)[1].strip()
            elif line.startswith("Certificate Path:"):
                current.certificate_path = line.split(":", 1)[1].strip()
            elif line.startswith("Private Key Path:"):
                current.private_key_path = line.split(":", 1)[1].strip()
            elif line.startswith("Expiry Date:"):
                current.expiry = CertbotManager._parse_expiry(line)

        if current is not None:
            certs.append(current)

        return certs

    @staticmethod
    def _parse_expiry(line: str) -> datetime | None:
        """Extract the ISO-ish datetime from an ``Expiry Date:`` line.

        Example input::

            Expiry Date: 2026-06-30 12:00:00+00:00 (VALID: 89 days)
        """
        match = re.search(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[+-]\d{2}:?\d{2})?)",
            line,
        )
        if not match:
            return None
        raw = match.group(1)
        # Python's fromisoformat needs a 'T' separator before 3.11; 3.11+
        # accepts the space form natively.
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    def revoke(self, domain: str) -> None:
        """Revoke a certificate with Let's Encrypt (keeps the local files).

        Uses ``--no-delete-after-revoke`` so the local certificate files
        are preserved for auditing; call :meth:`delete` afterwards if you
        also want to remove them from disk.

        Args:
            domain: Certificate name (``--cert-name``).

        Raises:
            CertbotError: If certbot exits with a non-zero status code.
        """
        cmd = [
            "certbot",
            "revoke",
            "--cert-name",
            domain,
            "--non-interactive",
            "--no-delete-after-revoke",
        ]
        try:
            self._runner.run(cmd, sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(f"certbot revoke failed for '{domain}': {exc}") from exc

    def delete(self, domain: str) -> None:
        """Delete a certificate's local files via ``certbot delete``.

        Removes the live symlinks and the ``archive/`` directory for the
        given cert name. Does **not** revoke with Let's Encrypt — call
        :meth:`revoke` first when decommissioning a domain.

        Args:
            domain: Certificate name (``--cert-name``).

        Raises:
            CertbotError: If certbot exits with a non-zero status code.
        """
        cmd = [
            "certbot",
            "delete",
            "--cert-name",
            domain,
            "--non-interactive",
        ]
        try:
            self._runner.run(cmd, sudo=True)
        except (SudoError, CommandError) as exc:
            raise CertbotError(f"certbot delete failed for '{domain}': {exc}") from exc

    def verify_service(
        self,
        server_type: ServerType,
        distro_family: DistroFamily,
    ) -> None:
        """Post-cert health check: ensure the web server is active.

        Runs ``systemctl status <service> --no-pager`` for Nginx/Apache
        (service name depends on distro) or ``docker compose ps`` for
        Traefik. A non-zero exit code is treated as "service not active"
        and raises :class:`ServerConfigError`.

        Args:
            server_type: Target web server.
            distro_family: Detected Linux distro family (controls the
                Apache service name: ``apache2`` on Debian/Ubuntu vs.
                ``httpd`` on Fedora/openSUSE).

        Raises:
            ServerConfigError: If the service is not running after
                certificate issuance.
        """
        if server_type == ServerType.TRAEFIK:
            cmd = ["docker", "compose", "ps"]
            sudo = False
        else:
            service = self._service_name(server_type, distro_family)
            cmd = ["systemctl", "status", service, "--no-pager"]
            sudo = True

        result = self._runner.run(cmd, sudo=sudo, check=False)
        if not result.success:
            label = (
                "traefik (docker compose)"
                if server_type == ServerType.TRAEFIK
                else self._service_name(server_type, distro_family)
            )
            raise ServerConfigError(
                f"Service '{label}' is not active after certificate issuance. "
                f"Exit code: {result.returncode}. stderr: {result.stderr.strip()}"
            )

    @staticmethod
    def _service_name(server_type: ServerType, distro_family: DistroFamily) -> str:
        """Map (server, distro) → systemd unit name."""
        if server_type == ServerType.NGINX:
            return "nginx"
        if server_type == ServerType.APACHE:
            return "apache2" if distro_family == DistroFamily.DEBIAN else "httpd"
        raise ServerConfigError(
            f"No systemd service mapping for server type '{server_type.value}'"
        )

    @staticmethod
    def _plugin_flag(server_type: ServerType) -> str:
        """Map a ``ServerType`` to the corresponding certbot plugin flag."""
        if server_type == ServerType.NGINX:
            return "--nginx"
        if server_type == ServerType.APACHE:
            return "--apache"
        raise CertbotError(
            f"Certbot does not manage '{server_type.value}': "
            "Traefik handles ACME natively in traefik.yml"
        )
