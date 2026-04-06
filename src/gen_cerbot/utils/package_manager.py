"""PackageManager ABC and implementations for apt, dnf, and zypper."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gen_cerbot.domain.models import DistroFamily
from gen_cerbot.utils.system import CommandResult, SystemRunner


class PackageManager(ABC):
    """Abstract base class for package manager operations."""

    def __init__(self, runner: SystemRunner) -> None:
        self._runner = runner

    @abstractmethod
    def update(self) -> CommandResult:
        """Update package index."""

    @abstractmethod
    def install(self, packages: list[str]) -> CommandResult:
        """Install one or more packages."""

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""

    @abstractmethod
    def remove(self, packages: list[str]) -> CommandResult:
        """Remove one or more packages."""


class AptPackageManager(PackageManager):
    """Package manager for Debian/Ubuntu using apt-get."""

    def update(self) -> CommandResult:
        return self._runner.run(["apt-get", "update", "-y"], sudo=True)

    def install(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["apt-get", "install", "-y", *packages], sudo=True)

    def is_installed(self, package: str) -> bool:
        result = self._runner.run(["dpkg", "-l", package], sudo=False, check=False)
        return result.success

    def remove(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["apt-get", "remove", "-y", *packages], sudo=True)


class DnfPackageManager(PackageManager):
    """Package manager for Fedora/RHEL using dnf."""

    def update(self) -> CommandResult:
        return self._runner.run(["dnf", "check-update", "-y"], sudo=True, check=False)

    def install(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["dnf", "install", "-y", *packages], sudo=True)

    def is_installed(self, package: str) -> bool:
        result = self._runner.run(["rpm", "-q", package], sudo=False, check=False)
        return result.success

    def remove(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["dnf", "remove", "-y", *packages], sudo=True)


class ZypperPackageManager(PackageManager):
    """Package manager for openSUSE using zypper."""

    def update(self) -> CommandResult:
        return self._runner.run(["zypper", "refresh"], sudo=True)

    def install(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["zypper", "install", "-y", *packages], sudo=True)

    def is_installed(self, package: str) -> bool:
        result = self._runner.run(["rpm", "-q", package], sudo=False, check=False)
        return result.success

    def remove(self, packages: list[str]) -> CommandResult:
        return self._runner.run(["zypper", "remove", "-y", *packages], sudo=True)


class PackageManagerFactory:
    """Factory to create the correct PackageManager based on distro family."""

    @staticmethod
    def create(distro_family: DistroFamily, runner: SystemRunner) -> PackageManager:
        managers: dict[DistroFamily, type[PackageManager]] = {
            DistroFamily.DEBIAN: AptPackageManager,
            DistroFamily.REDHAT: DnfPackageManager,
            DistroFamily.SUSE: ZypperPackageManager,
        }
        manager_cls = managers[distro_family]
        return manager_cls(runner)
