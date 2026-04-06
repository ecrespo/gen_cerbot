"""Unit tests for NginxProvider."""

from __future__ import annotations

from pathlib import Path

import pytest

from gen_cerbot.core.exceptions import ServerConfigError
from gen_cerbot.domain.models import CertificateConfig, DistroFamily, ServerType
from gen_cerbot.providers.nginx import NginxProvider
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
) -> NginxProvider:
    pkg_managers = {
        DistroFamily.DEBIAN: AptPackageManager,
        DistroFamily.REDHAT: DnfPackageManager,
        DistroFamily.SUSE: ZypperPackageManager,
    }
    pkg_manager = pkg_managers[distro](mock_runner)
    renderer = TemplateRenderer()
    return NginxProvider(
        mock_runner, pkg_manager, renderer, distro, config_root=config_root
    )


def _make_config(**overrides: object) -> CertificateConfig:
    defaults: dict[str, object] = {
        "domain": "app.example.com",
        "email": "admin@example.com",
        "server_type": ServerType.NGINX,
        "port": 8000,
        "project_name": "myapp",
    }
    defaults.update(overrides)
    return CertificateConfig(**defaults)  # type: ignore[arg-type]


class TestNginxProviderInstall:
    def test_install_calls_pkg_manager_with_nginx(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner)
        provider.install()
        assert len(mock_runner.calls) == 1
        call = mock_runner.calls[0]
        assert call["sudo"] is True
        assert "nginx" in call["cmd"]

    def test_install_uses_apt_on_debian(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN)
        provider.install()
        assert "apt-get" in mock_runner.calls[0]["cmd"]

    def test_install_uses_dnf_on_redhat(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT)
        provider.install()
        assert "dnf" in mock_runner.calls[0]["cmd"]

    def test_install_uses_zypper_on_suse(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner, DistroFamily.SUSE)
        provider.install()
        assert "zypper" in mock_runner.calls[0]["cmd"]

    def test_get_service_name(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner)
        assert provider.get_service_name() == "nginx"


class TestNginxProviderConfigure:
    def test_creates_config_file_in_sites_available(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        site_file = tmp_path / "sites-available" / "myapp"
        assert site_file.exists()

    def test_config_contains_domain(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        content = (tmp_path / "sites-available" / "myapp").read_text()
        assert "app.example.com" in content

    def test_config_contains_proxy_pass_with_port(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config(port=3000))

        content = (tmp_path / "sites-available" / "myapp").read_text()
        assert "proxy_pass http://localhost:3000;" in content

    def test_debian_creates_symlink_in_sites_enabled(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        symlink = tmp_path / "sites-enabled" / "myapp"
        assert symlink.is_symlink()
        assert symlink.resolve() == (tmp_path / "sites-available" / "myapp").resolve()

    def test_redhat_writes_to_conf_d_no_symlink(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT, config_root=tmp_path)
        provider.configure(_make_config())

        # On RedHat, config_root maps to sites-available which simulates conf.d
        config_file = tmp_path / "sites-available" / "myapp"
        assert config_file.exists()
        # No sites-enabled directory should be created
        assert not (tmp_path / "sites-enabled").exists()

    def test_suse_writes_to_conf_d_no_symlink(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.SUSE, config_root=tmp_path)
        provider.configure(_make_config())

        config_file = tmp_path / "sites-available" / "myapp"
        assert config_file.exists()
        assert not (tmp_path / "sites-enabled").exists()

    def test_uses_domain_as_filename_when_no_project(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config(project_name=""))

        assert (tmp_path / "sites-available" / "app.example.com").exists()

    def test_config_has_security_headers(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config())

        content = (tmp_path / "sites-available" / "myapp").read_text()
        assert "X-Frame-Options" in content
        assert "X-Content-Type-Options" in content


class TestNginxProviderVerify:
    def test_verify_calls_nginx_t_with_sudo(self, mock_runner: MockSystemRunner) -> None:
        provider = _make_provider(mock_runner)
        provider.verify()

        assert len(mock_runner.calls) == 1
        call = mock_runner.calls[0]
        assert call["cmd"] == ["sudo", "nginx", "-t"]
        assert call["sudo"] is True

    def test_verify_raises_on_invalid_config(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response(
            "sudo nginx -t",
            CommandResult(
                returncode=1,
                stdout="",
                stderr="nginx: configuration file /etc/nginx/nginx.conf test failed",
            ),
        )
        provider = _make_provider(mock_runner)

        with pytest.raises(ServerConfigError, match="configuration test failed"):
            provider.verify()

    def test_verify_succeeds_on_valid_config(self, mock_runner: MockSystemRunner) -> None:
        mock_runner.set_response(
            "sudo nginx -t",
            CommandResult(
                returncode=0,
                stdout="",
                stderr="nginx: configuration file /etc/nginx/nginx.conf test is successful",
            ),
        )
        provider = _make_provider(mock_runner)
        provider.verify()  # Should not raise


class TestNginxProviderRemove:
    def test_debian_removes_symlink_and_config(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.configure(_make_config(domain="app.example.com", project_name="app.example.com"))

        # Verify files exist before removal
        assert (tmp_path / "sites-available" / "app.example.com").exists()
        assert (tmp_path / "sites-enabled" / "app.example.com").is_symlink()

        provider.remove("app.example.com")

        assert not (tmp_path / "sites-available" / "app.example.com").exists()
        assert not (tmp_path / "sites-enabled" / "app.example.com").exists()

    def test_redhat_removes_config_only(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT, config_root=tmp_path)
        provider.configure(_make_config(domain="app.example.com", project_name="app.example.com"))

        assert (tmp_path / "sites-available" / "app.example.com").exists()

        provider.remove("app.example.com")

        assert not (tmp_path / "sites-available" / "app.example.com").exists()
        # No sites-enabled involved on RedHat
        assert not (tmp_path / "sites-enabled").exists()

    def test_remove_nonexistent_does_not_raise(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN, config_root=tmp_path)
        provider.remove("nonexistent.example.com")  # Should not raise

    def test_remove_uses_sudo_in_production_mode(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.DEBIAN)
        provider.remove("app.example.com")

        # Should call: rm -f symlink, rm -f config
        assert len(mock_runner.calls) == 2
        for call in mock_runner.calls:
            assert call["sudo"] is True
            assert "rm" in call["cmd"]

    def test_remove_redhat_production_single_rm(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner, DistroFamily.REDHAT)
        provider.remove("app.example.com")

        # RedHat: only rm config, no symlink
        assert len(mock_runner.calls) == 1
        assert mock_runner.calls[0]["sudo"] is True
        assert "rm" in mock_runner.calls[0]["cmd"]
