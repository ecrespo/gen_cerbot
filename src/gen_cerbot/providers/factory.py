"""ProviderFactory — creates ServerProvider instances by server type."""

from __future__ import annotations

from gen_cerbot.domain.models import DistroFamily, ServerType
from gen_cerbot.providers.apache import ApacheProvider
from gen_cerbot.providers.base import ServerProvider
from gen_cerbot.providers.nginx import NginxProvider
from gen_cerbot.providers.traefik import TraefikProvider
from gen_cerbot.utils.package_manager import PackageManagerFactory
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer


class ProviderFactory:
    """Factory that creates the correct ServerProvider for a given ServerType.

    Receives a SystemRunner and TemplateRenderer, and builds the appropriate
    PackageManager per distro family internally.
    """

    def __init__(self, runner: SystemRunner, template_renderer: TemplateRenderer) -> None:
        self._runner = runner
        self._template_renderer = template_renderer

    def get(self, server_type: ServerType, distro_family: DistroFamily) -> ServerProvider:
        """Return a ServerProvider for the given server type and distro."""
        pkg_manager = PackageManagerFactory.create(distro_family, self._runner)

        if server_type == ServerType.NGINX:
            return NginxProvider(
                self._runner, pkg_manager, self._template_renderer, distro_family
            )

        if server_type == ServerType.APACHE:
            return ApacheProvider(
                self._runner, pkg_manager, self._template_renderer, distro_family
            )

        if server_type == ServerType.TRAEFIK:
            return TraefikProvider(
                self._runner, pkg_manager, self._template_renderer, distro_family
            )

        raise ValueError(f"Unsupported server type: {server_type}")
