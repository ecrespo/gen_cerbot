"""NginxProvider — web server provider for Nginx."""

from __future__ import annotations

import tempfile
from pathlib import Path

from gen_cerbot.domain.models import CertificateConfig, DistroFamily
from gen_cerbot.providers.base import ServerProvider
from gen_cerbot.utils.package_manager import PackageManager
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer

# Nginx config paths per distro family
_SITES_AVAILABLE: dict[DistroFamily, Path] = {
    DistroFamily.DEBIAN: Path("/etc/nginx/sites-available"),
    DistroFamily.REDHAT: Path("/etc/nginx/conf.d"),
    DistroFamily.SUSE: Path("/etc/nginx/conf.d"),
}

_SITES_ENABLED = Path("/etc/nginx/sites-enabled")


class NginxProvider(ServerProvider):
    """Provider for Nginx web server across all supported distro families.

    Accepts an optional config_root for testing, which redirects all
    file operations to a local directory instead of /etc/nginx/.
    """

    def __init__(
        self,
        runner: SystemRunner,
        pkg_manager: PackageManager,
        template_renderer: TemplateRenderer,
        distro_family: DistroFamily,
        *,
        config_root: Path | None = None,
    ) -> None:
        super().__init__(runner, pkg_manager, template_renderer, distro_family)
        self._config_root = config_root

    def _sites_available_dir(self) -> Path:
        if self._config_root is not None:
            return self._config_root / "sites-available"
        return _SITES_AVAILABLE[self._distro_family]

    def _sites_enabled_dir(self) -> Path:
        if self._config_root is not None:
            return self._config_root / "sites-enabled"
        return _SITES_ENABLED

    def _config_filename(self, config: CertificateConfig) -> str:
        return config.project_name if config.project_name else config.domain

    def install(self) -> None:
        """Install Nginx using the distro's package manager."""
        self._pkg_manager.install(["nginx"])

    def configure(self, config: CertificateConfig) -> None:
        """Generate and activate the Nginx site configuration.

        On Debian/Ubuntu: writes to sites-available/ and creates symlink in sites-enabled/.
        On Fedora/openSUSE: writes directly to conf.d/ (no symlink needed).
        """
        context = {
            "domain": config.domain,
            "port": config.port,
            "project_name": config.project_name or config.domain,
        }
        content = self._template_renderer.render("nginx/site.conf.j2", context)

        filename = self._config_filename(config)
        available_dir = self._sites_available_dir()
        config_path = available_dir / filename

        self._write_config(config_path, content)

        # On Debian: create symlink in sites-enabled
        if self._distro_family == DistroFamily.DEBIAN:
            enabled_dir = self._sites_enabled_dir()
            symlink_path = enabled_dir / filename
            if self._config_root is not None:
                enabled_dir.mkdir(parents=True, exist_ok=True)
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                symlink_path.symlink_to(config_path)
            else:
                self._runner.run(
                    ["ln", "-sf", str(config_path), str(symlink_path)],
                    sudo=True,
                )

    def _write_config(self, dest: Path, content: str) -> None:
        """Write configuration content to dest path.

        In test mode (config_root set): writes directly.
        In production: writes to a tempfile, then moves with sudo.
        """
        if self._config_root is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        else:
            self._runner.run(["mkdir", "-p", str(dest.parent)], sudo=True)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".conf", delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            self._runner.run(["mv", tmp_path, str(dest)], sudo=True)
            self._runner.run(["chmod", "644", str(dest)], sudo=True)

    def verify(self) -> None:
        """Verify the Nginx configuration with nginx -t.

        Raises:
            ServerConfigError: If the configuration test fails.
        """
        from gen_cerbot.core.exceptions import ServerConfigError

        result = self._runner.run(["nginx", "-t"], sudo=True, check=False)
        if not result.success:
            raise ServerConfigError(
                f"Nginx configuration test failed:\n{result.stderr}"
            )

    def remove(self, domain: str) -> None:
        """Remove the Nginx site configuration for a domain.

        On Debian: removes symlink from sites-enabled/ and file from sites-available/.
        On Fedora/openSUSE: removes file from conf.d/.
        """
        available_dir = self._sites_available_dir()
        config_path = available_dir / domain

        # On Debian: remove symlink first
        if self._distro_family == DistroFamily.DEBIAN:
            symlink_path = self._sites_enabled_dir() / domain
            if self._config_root is not None:
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
            else:
                self._runner.run(
                    ["rm", "-f", str(symlink_path)], sudo=True
                )

        # Remove config file
        if self._config_root is not None:
            if config_path.exists():
                config_path.unlink()
        else:
            self._runner.run(["rm", "-f", str(config_path)], sudo=True)

    def get_service_name(self) -> str:
        """Return the systemd service name for Nginx."""
        return "nginx"
