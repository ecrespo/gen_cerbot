"""Certbot installer — handles per-distro installation of Certbot.

Entry point: ``CertbotInstaller.ensure_installed(distro_family, server_type)``.

The method is idempotent: if ``certbot --version`` already succeeds, the call
returns immediately without touching the system. Per-distro branches and the
Traefik shortcut are implemented in subsequent tasks (F4-03a..F4-03d).
"""

from __future__ import annotations

from gen_cerbot.core.exceptions import GenCerbotError
from gen_cerbot.domain.models import DistroFamily, ServerType
from gen_cerbot.utils.system import SystemRunner


class CertbotInstaller:
    """Install Certbot on the host, selecting the method per distro family."""

    def __init__(self, runner: SystemRunner | None = None) -> None:
        self._runner = runner or SystemRunner()

    def is_installed(self) -> bool:
        """Return True if ``certbot --version`` exits successfully.

        In dry-run mode this always returns ``False`` so that the install
        branch still runs (and prints its would-be commands) rather than
        short-circuiting on the dry-run stub exit code.
        """
        if self._runner.dry_run:
            return False
        result = self._runner.run(["certbot", "--version"], check=False)
        return result.success

    def ensure_installed(
        self,
        distro_family: DistroFamily,
        server_type: ServerType,
    ) -> None:
        """Ensure Certbot is installed on the host.

        Idempotent: if Certbot is already available it returns immediately.
        Otherwise it dispatches to the per-distro install branch.

        Args:
            distro_family: Detected Linux distribution family.
            server_type: Target web server. Traefik skips installation
                entirely because ACME is native to ``traefik.yml``.
        """
        # F4-03d: Traefik handles ACME natively via traefik.yml, so Certbot
        # is never installed for this server type. Short-circuit before any
        # filesystem or package-manager work happens.
        if server_type == ServerType.TRAEFIK:
            return

        if self.is_installed():
            return

        if distro_family == DistroFamily.DEBIAN:
            self._install_debian()
        elif distro_family == DistroFamily.REDHAT:
            self._install_redhat()
        elif distro_family == DistroFamily.SUSE:
            self._install_suse()
        else:  # pragma: no cover - enum exhausted above
            raise GenCerbotError(f"Unsupported distro family: {distro_family}")

    # ------------------------------------------------------------------
    # Per-distro branches — implemented in F4-03a / F4-03b / F4-03c.
    # ------------------------------------------------------------------

    def _install_debian(self) -> None:
        """Install Certbot on Debian/Ubuntu via snap.

        Steps:
        1. Check if ``snapd`` is installed (``dpkg -l snapd``).
        2. If missing, ``sudo apt install -y snapd``.
        3. ``sudo snap install --classic certbot``.
        4. ``sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot`` so the
           binary is on ``PATH`` regardless of the user's shell config.
        """
        if not self._snapd_installed():
            self._runner.run(["apt-get", "install", "-y", "snapd"], sudo=True)

        self._runner.run(
            ["snap", "install", "--classic", "certbot"],
            sudo=True,
        )
        self._runner.run(
            ["ln", "-sf", "/snap/bin/certbot", "/usr/local/bin/certbot"],
            sudo=True,
        )

    def _snapd_installed(self) -> bool:
        """Return True if the ``snapd`` package is registered with dpkg.

        In dry-run mode returns ``False`` so the ``apt install snapd`` step
        is still surfaced to the user as a would-be command.
        """
        if self._runner.dry_run:
            return False
        result = self._runner.run(["dpkg", "-l", "snapd"], check=False)
        return result.success

    def _install_redhat(self) -> None:
        """Install Certbot on Fedora/RHEL via dnf.

        Installs ``certbot`` plus the nginx and apache plugins in a single
        transaction so both providers are immediately usable.
        """
        self._runner.run(
            [
                "dnf",
                "install",
                "-y",
                "certbot",
                "python3-certbot-nginx",
                "python3-certbot-apache",
            ],
            sudo=True,
        )

    def _install_suse(self) -> None:
        """Install Certbot on openSUSE via zypper.

        Installs ``certbot`` plus the nginx and apache plugins in a single
        non-interactive transaction.
        """
        self._runner.run(
            [
                "zypper",
                "--non-interactive",
                "install",
                "certbot",
                "python3-certbot-nginx",
                "python3-certbot-apache",
            ],
            sudo=True,
        )
