"""ServerProvider ABC — abstract base class for web server providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gen_cerbot.domain.models import CertificateConfig, DistroFamily
from gen_cerbot.utils.package_manager import PackageManager
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer


class ServerProvider(ABC):
    """Abstract base class for web server providers.

    Each provider (Nginx, Apache, Traefik) implements this interface
    to handle installation, configuration, verification, and removal
    of its respective web server.

    Receives PackageManager and SystemRunner via constructor injection
    so that all system operations go through the centralized abstractions.
    """

    def __init__(
        self,
        runner: SystemRunner,
        pkg_manager: PackageManager,
        template_renderer: TemplateRenderer,
        distro_family: DistroFamily,
    ) -> None:
        self._runner = runner
        self._pkg_manager = pkg_manager
        self._template_renderer = template_renderer
        self._distro_family = distro_family

    @abstractmethod
    def install(self) -> None:
        """Install the web server packages using the package manager."""

    @abstractmethod
    def configure(self, config: CertificateConfig) -> None:
        """Generate and activate the server configuration for the given domain."""

    @abstractmethod
    def verify(self) -> None:
        """Verify that the server configuration is valid."""

    @abstractmethod
    def remove(self, domain: str) -> None:
        """Remove the server configuration for the given domain."""

    @abstractmethod
    def get_service_name(self) -> str:
        """Return the systemd service name for this server on the current distro."""
