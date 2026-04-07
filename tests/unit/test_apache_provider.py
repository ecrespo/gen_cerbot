"""Unit tests for ApacheProvider."""

from __future__ import annotations

from pathlib import Path

import pytest

from gen_cerbot.core.exceptions import ServerConfigError
from gen_cerbot.domain.models import CertificateConfig, DistroFamily, ServerType
from gen_cerbot.providers.apache import ApacheProvider
from gen_cerbot.utils.package_manager import (
    AptPackageManager,
    DnfPackageManager,
    ZypperPackageManager,
)
from gen_cerbot.utils.system import CommandResult
from gen_cerbot.utils.templates import TemplateRenderer
from tests.conftest import MockSystemRunner


def _make_provider(
    mock_runner: MockSystemRunner,
    distro: DistroFamily = DistroFamily.DEBIAN,
    config_root: Path | None = None,
) -> ApacheProvider:
    pkg_managers = {
        DistroFamily.DEBIAN: AptPackageManager,
        DistroFamily.REDHAT: DnfPackageManager,
        DistroFamily.SUSE: ZypperPackageManager,
    }
    pkg_manager = pkg_managers[distro](mock_runner)
    renderer = TemplateRenderer()
    return ApacheProvider(
        mock_runner, pkg_manager, renderer, distro, config_root=config_root
    )


def _make_config(**overrides: object) -> CertificateConfig:
    defaults: dict[str, object] = {
        "domain": "api.example.com",
        "email": "admin@example.com",
        "server_type": ServerType.APACHE,
        "port": 3000,
        "project_name": "myapi",
    }
    defaults.update(overrides)
    return CertificateConfig(**defaults)  # type: ignore[arg-type]


class TestApacheProviderInstall:
    def test_install_debian_uses_apt_and_enables_modules(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN)
        provider.install()

        # First call is the apt-get install
        install_call = mock_runner.calls[0]
        assert "apt-get" in install_call["cmd"]
        assert "apache2" in install_call["cmd"]
        assert "libapache2-mod-proxy-html" in install_call["cmd"]
        assert install_call["sudo"] is True

        # Followed by a2enmod for each required module
        enmod_cmds = [
            call for call in mock_runner.calls[1:] if "a2enmod" in call["cmd"]
        ]
        assert len(enmod_cmds) == 4
        enabled_modules = {call["cmd"][-1] for call in enmod_cmds}
        assert enabled_modules == {"proxy", "proxy_http", "headers", "ssl"}
        for call in enmod_cmds:
            assert call["sudo"] is True

    def test_install_redhat_uses_dnf_with_httpd_and_mod_ssl(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT)
        provider.install()

        install_call = mock_runner.calls[0]
        assert "dnf" in install_call["cmd"]
        assert "httpd" in install_call["cmd"]
        assert "mod_ssl" in install_call["cmd"]
        # No a2enmod on Fedora
        assert not any("a2enmod" in call["cmd"] for call in mock_runner.calls)

    def test_install_suse_uses_zypper(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner, DistroFamily.SUSE)
        provider.install()

        install_call = mock_runner.calls[0]
        assert "zypper" in install_call["cmd"]
        assert "apache2" in install_call["cmd"]
        assert "apache2-mod_proxy_html" in install_call["cmd"]
        # No a2enmod on openSUSE
        assert not any("a2enmod" in call["cmd"] for call in mock_runner.calls)

    def test_get_service_name_debian(self, mock_runner: MockSystemRunner) -> None:
        assert _make_provider(mock_runner, DistroFamily.DEBIAN).get_service_name() == "apache2"

    def test_get_service_name_redhat(self, mock_runner: MockSystemRunner) -> None:
        assert _make_provider(mock_runner, DistroFamily.REDHAT).get_service_name() == "httpd"

    def test_get_service_name_suse(self, mock_runner: MockSystemRunner) -> None:
        assert _make_provider(mock_runner, DistroFamily.SUSE).get_service_name() == "apache2"


class TestApacheProviderConfigure:
    def test_debian_template_has_apache_log_dir_variable(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        config_path = tmp_path / "sites-available" / "myapi.conf"
        assert config_path.exists()
        content = config_path.read_text()
        assert "${APACHE_LOG_DIR}" in content

    def test_redhat_template_uses_httpd_log_path(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT, config_root=tmp_path)
        provider.configure(_make_config())

        config_path = tmp_path / "sites-available" / "myapi.conf"
        content = config_path.read_text()
        assert "/var/log/httpd/" in content
        assert "${APACHE_LOG_DIR}" not in content

    def test_suse_template_uses_apache2_log_path(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.SUSE, config_root=tmp_path)
        provider.configure(_make_config())

        config_path = tmp_path / "sites-available" / "myapi.conf"
        content = config_path.read_text()
        assert "/var/log/apache2/" in content

    def test_config_contains_domain_and_proxypass(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config(port=5000))

        content = (tmp_path / "sites-available" / "myapi.conf").read_text()
        assert "ServerName api.example.com" in content
        assert "ProxyPass / http://localhost:5000/" in content
        assert "ProxyPassReverse / http://localhost:5000/" in content

    def test_config_has_security_headers(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        content = (tmp_path / "sites-available" / "myapi.conf").read_text()
        assert "X-Frame-Options" in content
        assert "X-Content-Type-Options" in content

    def test_debian_creates_symlink_in_sites_enabled(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        symlink = tmp_path / "sites-enabled" / "myapi.conf"
        assert symlink.is_symlink()
        assert symlink.resolve() == (tmp_path / "sites-available" / "myapi.conf").resolve()

    def test_redhat_no_symlink_created(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT, config_root=tmp_path)
        provider.configure(_make_config())

        assert (tmp_path / "sites-available" / "myapi.conf").exists()
        assert not (tmp_path / "sites-enabled").exists()

    def test_suse_no_symlink_created(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.SUSE, config_root=tmp_path)
        provider.configure(_make_config())

        assert (tmp_path / "sites-available" / "myapi.conf").exists()
        assert not (tmp_path / "sites-enabled").exists()

    def test_uses_domain_as_filename_when_no_project(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config(project_name=""))

        assert (tmp_path / "sites-available" / "api.example.com.conf").exists()


class TestApacheProviderVerify:
    def test_verify_calls_apachectl_t_with_sudo(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner)
        provider.verify()

        assert len(mock_runner.calls) == 1
        call = mock_runner.calls[0]
        assert call["cmd"] == ["sudo", "apachectl", "-t"]
        assert call["sudo"] is True

    def test_verify_raises_on_invalid_config(
        self, mock_runner: MockSystemRunner
    ) -> None:
        mock_runner.set_response(
            "sudo apachectl -t",
            CommandResult(
                returncode=1,
                stdout="",
                stderr="Syntax error on line 12 of /etc/apache2/sites-enabled/myapi.conf",
            ),
        )
        provider = _make_provider(mock_runner)

        with pytest.raises(ServerConfigError, match="configuration test failed"):
            provider.verify()

    def test_verify_succeeds_on_valid_config(
        self, mock_runner: MockSystemRunner
    ) -> None:
        mock_runner.set_response(
            "sudo apachectl -t",
            CommandResult(returncode=0, stdout="", stderr="Syntax OK"),
        )
        provider = _make_provider(mock_runner)
        provider.verify()  # should not raise


class TestApacheProviderRemove:
    def test_debian_removes_symlink_and_config(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(
            _make_config(domain="api.example.com", project_name="api.example.com")
        )

        assert (tmp_path / "sites-available" / "api.example.com.conf").exists()
        assert (tmp_path / "sites-enabled" / "api.example.com.conf").is_symlink()

        provider.remove("api.example.com")

        assert not (tmp_path / "sites-available" / "api.example.com.conf").exists()
        assert not (tmp_path / "sites-enabled" / "api.example.com.conf").exists()

    def test_redhat_removes_config_only(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT, config_root=tmp_path)
        provider.configure(
            _make_config(domain="api.example.com", project_name="api.example.com")
        )

        assert (tmp_path / "sites-available" / "api.example.com.conf").exists()

        provider.remove("api.example.com")

        assert not (tmp_path / "sites-available" / "api.example.com.conf").exists()
        assert not (tmp_path / "sites-enabled").exists()

    def test_remove_nonexistent_does_not_raise(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.remove("nonexistent.example.com")  # should not raise

    def test_debian_production_calls_a2dissite_and_rm(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN)
        provider.remove("api.example.com")

        assert any("a2dissite" in call["cmd"] for call in mock_runner.calls)
        assert any("rm" in call["cmd"] for call in mock_runner.calls)
        for call in mock_runner.calls:
            assert call["sudo"] is True

    def test_redhat_production_rm_only(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT)
        provider.remove("api.example.com")

        assert len(mock_runner.calls) == 1
        assert "rm" in mock_runner.calls[0]["cmd"]
        assert mock_runner.calls[0]["sudo"] is True
        assert not any("a2dissite" in call["cmd"] for call in mock_runner.calls)
