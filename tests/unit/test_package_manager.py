"""Unit tests for PackageManager implementations."""

from __future__ import annotations

from gen_cerbot.domain.models import DistroFamily
from gen_cerbot.utils.package_manager import (
    AptPackageManager,
    DnfPackageManager,
    PackageManagerFactory,
    ZypperPackageManager,
)
from tests.conftest import MockSystemRunner


class TestAptPackageManager:
    def test_install_uses_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = AptPackageManager(mock_runner)
        mgr.install(["nginx"])
        assert len(mock_runner.calls) == 1
        call = mock_runner.calls[0]
        assert call["sudo"] is True
        assert "apt-get" in call["cmd"]
        assert "nginx" in call["cmd"]

    def test_update_uses_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = AptPackageManager(mock_runner)
        mgr.update()
        assert mock_runner.calls[0]["sudo"] is True
        assert "apt-get" in mock_runner.calls[0]["cmd"]
        assert "update" in mock_runner.calls[0]["cmd"]

    def test_is_installed_no_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = AptPackageManager(mock_runner)
        mgr.is_installed("nginx")
        assert mock_runner.calls[0]["sudo"] is False
        assert "dpkg" in mock_runner.calls[0]["cmd"]

    def test_remove_uses_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = AptPackageManager(mock_runner)
        mgr.remove(["nginx"])
        assert mock_runner.calls[0]["sudo"] is True


class TestDnfPackageManager:
    def test_install_uses_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = DnfPackageManager(mock_runner)
        mgr.install(["nginx"])
        call = mock_runner.calls[0]
        assert call["sudo"] is True
        assert "dnf" in call["cmd"]
        assert "nginx" in call["cmd"]

    def test_is_installed_uses_rpm(self, mock_runner: MockSystemRunner) -> None:
        mgr = DnfPackageManager(mock_runner)
        mgr.is_installed("httpd")
        assert "rpm" in mock_runner.calls[0]["cmd"]
        assert mock_runner.calls[0]["sudo"] is False


class TestZypperPackageManager:
    def test_install_uses_sudo(self, mock_runner: MockSystemRunner) -> None:
        mgr = ZypperPackageManager(mock_runner)
        mgr.install(["nginx"])
        call = mock_runner.calls[0]
        assert call["sudo"] is True
        assert "zypper" in call["cmd"]
        assert "nginx" in call["cmd"]

    def test_update_uses_zypper_refresh(self, mock_runner: MockSystemRunner) -> None:
        mgr = ZypperPackageManager(mock_runner)
        mgr.update()
        assert "zypper" in mock_runner.calls[0]["cmd"]
        assert "refresh" in mock_runner.calls[0]["cmd"]


class TestPackageManagerFactory:
    def test_create_apt_for_debian(self, mock_runner: MockSystemRunner) -> None:
        mgr = PackageManagerFactory.create(DistroFamily.DEBIAN, mock_runner)
        assert isinstance(mgr, AptPackageManager)

    def test_create_dnf_for_redhat(self, mock_runner: MockSystemRunner) -> None:
        mgr = PackageManagerFactory.create(DistroFamily.REDHAT, mock_runner)
        assert isinstance(mgr, DnfPackageManager)

    def test_create_zypper_for_suse(self, mock_runner: MockSystemRunner) -> None:
        mgr = PackageManagerFactory.create(DistroFamily.SUSE, mock_runner)
        assert isinstance(mgr, ZypperPackageManager)
