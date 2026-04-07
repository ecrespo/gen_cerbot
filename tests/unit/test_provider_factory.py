"""Unit tests for ProviderFactory."""

from __future__ import annotations

import pytest

from gen_cerbot.domain.models import DistroFamily, ServerType
from gen_cerbot.providers.apache import ApacheProvider
from gen_cerbot.providers.factory import ProviderFactory
from gen_cerbot.providers.nginx import NginxProvider
from gen_cerbot.providers.traefik import TraefikProvider
from gen_cerbot.utils.templates import TemplateRenderer
from tests.conftest import MockSystemRunner


@pytest.fixture
def factory(mock_runner: MockSystemRunner) -> ProviderFactory:
    renderer = TemplateRenderer()
    return ProviderFactory(mock_runner, renderer)


class TestProviderFactory:
    def test_get_nginx_returns_nginx_provider(
        self, factory: ProviderFactory
    ) -> None:
        provider = factory.get(ServerType.NGINX, DistroFamily.DEBIAN)
        assert isinstance(provider, NginxProvider)

    def test_get_nginx_for_each_distro(
        self, factory: ProviderFactory
    ) -> None:
        for distro in DistroFamily:
            provider = factory.get(ServerType.NGINX, distro)
            assert isinstance(provider, NginxProvider)

    def test_get_apache_returns_apache_provider(
        self, factory: ProviderFactory
    ) -> None:
        provider = factory.get(ServerType.APACHE, DistroFamily.DEBIAN)
        assert isinstance(provider, ApacheProvider)

    def test_get_apache_for_each_distro(
        self, factory: ProviderFactory
    ) -> None:
        for distro in DistroFamily:
            provider = factory.get(ServerType.APACHE, distro)
            assert isinstance(provider, ApacheProvider)
            assert provider._distro_family == distro

    def test_get_traefik_returns_traefik_provider(
        self, factory: ProviderFactory
    ) -> None:
        provider = factory.get(ServerType.TRAEFIK, DistroFamily.DEBIAN)
        assert isinstance(provider, TraefikProvider)

    def test_get_traefik_for_each_distro(
        self, factory: ProviderFactory
    ) -> None:
        for distro in DistroFamily:
            provider = factory.get(ServerType.TRAEFIK, distro)
            assert isinstance(provider, TraefikProvider)

    def test_unsupported_server_type_raises(
        self, factory: ProviderFactory
    ) -> None:
        with pytest.raises(ValueError, match="Unsupported server type"):
            factory.get("unknown", DistroFamily.DEBIAN)  # type: ignore[arg-type]

    def test_provider_receives_correct_distro(
        self, factory: ProviderFactory
    ) -> None:
        provider = factory.get(ServerType.NGINX, DistroFamily.REDHAT)
        assert provider._distro_family == DistroFamily.REDHAT

    def test_provider_has_correct_package_manager(
        self, factory: ProviderFactory
    ) -> None:
        from gen_cerbot.utils.package_manager import (
            AptPackageManager,
            DnfPackageManager,
            ZypperPackageManager,
        )

        debian_provider = factory.get(ServerType.NGINX, DistroFamily.DEBIAN)
        assert isinstance(debian_provider._pkg_manager, AptPackageManager)

        redhat_provider = factory.get(ServerType.NGINX, DistroFamily.REDHAT)
        assert isinstance(redhat_provider._pkg_manager, DnfPackageManager)

        suse_provider = factory.get(ServerType.NGINX, DistroFamily.SUSE)
        assert isinstance(suse_provider._pkg_manager, ZypperPackageManager)
