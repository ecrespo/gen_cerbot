"""ApacheProvider — web server provider for Apache HTTPD."""

from __future__ import annotations

import tempfile
from pathlib import Path

from gen_cerbot.domain.models import CertificateConfig, DistroFamily
from gen_cerbot.providers.base import ServerProvider
from gen_cerbot.utils.package_manager import PackageManager
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer

# Apache packages per distro family
_APACHE_PACKAGES: dict[DistroFamily, list[str]] = {
    DistroFamily.DEBIAN: ["apache2", "libapache2-mod-proxy-html"],
    DistroFamily.REDHAT: ["httpd", "mod_ssl"],
    DistroFamily.SUSE: ["apache2", "apache2-mod_proxy_html"],
}

# Apache vhost config directories per distro family
_SITES_AVAILABLE: dict[DistroFamily, Path] = {
    DistroFamily.DEBIAN: Path("/etc/apache2/sites-available"),
    DistroFamily.REDHAT: Path("/etc/httpd/conf.d"),
    DistroFamily.SUSE: Path("/etc/apache2/vhosts.d"),
}

_SITES_ENABLED_DEBIAN = Path("/etc/apache2/sites-enabled")

# Per-distro template selection
_TEMPLATES: dict[DistroFamily, str] = {
    DistroFamily.DEBIAN: "apache/vhost-debian.conf.j2",
    DistroFamily.REDHAT: "apache/vhost-redhat.conf.j2",
    DistroFamily.SUSE: "apache/vhost-suse.conf.j2",
}

# Apache modules to enable on Debian/Ubuntu via a2enmod
_DEBIAN_MODULES = ["proxy", "proxy_http", "headers", "ssl"]


class ApacheProvider(ServerProvider):
    """Provider for the Apache HTTP server across all supported distro families.

    Accepts an optional config_root for testing, which redirects all
    file operations to a local directory instead of /etc/apache2 or /etc/httpd.
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

    def install(self) -> None:
        """Install Apache and required modules for the current distro family.

        - Debian/Ubuntu: installs `apache2` + `libapache2-mod-proxy-html`,
          then enables `proxy`, `proxy_http`, `headers`, and `ssl` via `a2enmod`.
        - Fedora/RHEL: installs `httpd` + `mod_ssl` (modules are loaded via
          conf files shipped with the packages, no a2enmod equivalent).
        - openSUSE: installs `apache2` + `apache2-mod_proxy_html` (modules
          are managed through `/etc/sysconfig/apache2`, not enabled here).
        """
        packages = _APACHE_PACKAGES[self._distro_family]
        self._pkg_manager.install(packages)

        if self._distro_family == DistroFamily.DEBIAN:
            for module in _DEBIAN_MODULES:
                self._runner.run(["a2enmod", module], sudo=True)

    def get_service_name(self) -> str:
        """Return the systemd service name for Apache on the current distro."""
        if self._distro_family == DistroFamily.DEBIAN:
            return "apache2"
        if self._distro_family == DistroFamily.SUSE:
            return "apache2"
        return "httpd"

    def _sites_available_dir(self) -> Path:
        if self._config_root is not None:
            return self._config_root / "sites-available"
        return _SITES_AVAILABLE[self._distro_family]

    def _sites_enabled_dir(self) -> Path:
        if self._config_root is not None:
            return self._config_root / "sites-enabled"
        return _SITES_ENABLED_DEBIAN

    def _config_filename(self, config: CertificateConfig) -> str:
        base = config.project_name if config.project_name else config.domain
        return f"{base}.conf"

    def configure(self, config: CertificateConfig) -> None:
        """Generate and activate the Apache VirtualHost configuration.

        On Debian/Ubuntu: writes to `sites-available/` and enables the vhost
        with `a2ensite` (or a manual symlink in test mode).
        On Fedora: writes to `/etc/httpd/conf.d/` (auto-loaded by Apache).
        On openSUSE: writes to `/etc/apache2/vhosts.d/` (auto-loaded).
        """
        template_name = _TEMPLATES[self._distro_family]
        context = {
            "domain": config.domain,
            "port": config.port,
            "project_name": config.project_name or config.domain,
        }
        content = self._template_renderer.render(template_name, context)

        filename = self._config_filename(config)
        available_dir = self._sites_available_dir()
        config_path = available_dir / filename

        self._write_config(config_path, content)

        # On Debian: enable the site (a2ensite creates the sites-enabled symlink).
        if self._distro_family == DistroFamily.DEBIAN:
            site_name = filename.removesuffix(".conf")
            if self._config_root is not None:
                enabled_dir = self._sites_enabled_dir()
                enabled_dir.mkdir(parents=True, exist_ok=True)
                symlink_path = enabled_dir / filename
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                symlink_path.symlink_to(config_path)
            else:
                self._runner.run(["a2ensite", site_name], sudo=True)

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
        """Verify the Apache configuration with `apachectl -t`.

        Raises:
            ServerConfigError: If the configuration test fails.
        """
        from gen_cerbot.core.exceptions import ServerConfigError

        result = self._runner.run(["apachectl", "-t"], sudo=True, check=False)
        if not result.success:
            raise ServerConfigError(
                f"Apache configuration test failed:\n{result.stderr}"
            )

    def remove(self, domain: str) -> None:
        """Remove the Apache vhost configuration for a domain.

        The `domain` argument is used as the base name for the config file
        (matching how `configure()` names files when `project_name` is empty).

        On Debian: disables the site with `sudo a2dissite <name>` and removes
        the config file from `sites-available/`.
        On Fedora/openSUSE: removes the config file from the auto-loaded
        conf directory (`/etc/httpd/conf.d/` or `/etc/apache2/vhosts.d/`).
        """
        filename = f"{domain}.conf"
        available_dir = self._sites_available_dir()
        config_path = available_dir / filename

        # On Debian: disable the site first (removes sites-enabled symlink).
        if self._distro_family == DistroFamily.DEBIAN:
            site_name = domain
            if self._config_root is not None:
                symlink_path = self._sites_enabled_dir() / filename
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
            else:
                self._runner.run(
                    ["a2dissite", site_name], sudo=True, check=False
                )

        # Remove the config file itself.
        if self._config_root is not None:
            if config_path.exists():
                config_path.unlink()
        else:
            self._runner.run(["rm", "-f", str(config_path)], sudo=True)
