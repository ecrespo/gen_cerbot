"""Unit tests for TraefikProvider."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml

from gen_cerbot.core.exceptions import ServerConfigError
from gen_cerbot.domain.models import CertificateConfig, DistroFamily, ServerType
from gen_cerbot.providers.traefik import TraefikProvider
from gen_cerbot.utils.package_manager import AptPackageManager
from gen_cerbot.utils.system import CommandResult
from gen_cerbot.utils.templates import TemplateRenderer
from tests.conftest import MockSystemRunner


def _make_provider(
    mock_runner: MockSystemRunner,
    output_dir: Path | None = None,
    distro: DistroFamily = DistroFamily.DEBIAN,
) -> TraefikProvider:
    # Traefik is distro-agnostic; we use AptPackageManager arbitrarily —
    # the provider must not depend on it for install().
    pkg_manager = AptPackageManager(mock_runner)
    renderer = TemplateRenderer()
    return TraefikProvider(
        mock_runner, pkg_manager, renderer, distro, output_dir=output_dir
    )


def _make_config(**overrides: object) -> CertificateConfig:
    defaults: dict[str, object] = {
        "domain": "app.example.com",
        "email": "admin@example.com",
        "server_type": ServerType.TRAEFIK,
        "port": 8080,
        "project_name": "myapp",
    }
    defaults.update(overrides)
    return CertificateConfig(**defaults)  # type: ignore[arg-type]


class TestTraefikProviderInstall:
    def test_install_checks_docker_version(
        self, mock_runner: MockSystemRunner
    ) -> None:
        provider = _make_provider(mock_runner)
        provider.install()

        assert len(mock_runner.calls) == 1
        call = mock_runner.calls[0]
        assert call["cmd"] == ["docker", "--version"]
        assert call["sudo"] is False
        assert call["check"] is False

    def test_install_raises_when_docker_missing(
        self, mock_runner: MockSystemRunner
    ) -> None:
        mock_runner.set_response(
            "docker --version",
            CommandResult(returncode=127, stdout="", stderr="command not found"),
        )
        provider = _make_provider(mock_runner)

        with pytest.raises(ServerConfigError, match="Docker is not installed"):
            provider.install()

    def test_install_does_not_use_package_manager(
        self, mock_runner: MockSystemRunner
    ) -> None:
        """Traefik must be distro-agnostic — no apt/dnf/zypper calls."""
        provider = _make_provider(mock_runner)
        provider.install()

        for call in mock_runner.calls:
            assert "apt-get" not in call["cmd"]
            assert "dnf" not in call["cmd"]
            assert "zypper" not in call["cmd"]

    def test_get_service_name(self, mock_runner: MockSystemRunner) -> None:
        assert _make_provider(mock_runner).get_service_name() == "traefik"


class TestTraefikProviderConfigure:
    def test_generates_compose_and_traefik_files(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        assert (tmp_path / "docker-compose.yml").exists()
        assert (tmp_path / "traefik.yml").exists()
        assert (tmp_path / "acme.json").exists()

    def test_compose_and_traefik_are_valid_yaml(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        compose = yaml.safe_load((tmp_path / "docker-compose.yml").read_text())
        traefik = yaml.safe_load((tmp_path / "traefik.yml").read_text())

        assert isinstance(compose, dict)
        assert "services" in compose
        assert "traefik" in compose["services"]
        assert isinstance(traefik, dict)
        assert "entryPoints" in traefik
        assert "certificatesResolvers" in traefik

    def test_compose_contains_domain_and_port(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config(domain="app.example.com", port=9000))

        content = (tmp_path / "docker-compose.yml").read_text()
        assert "Host(`app.example.com`)" in content
        assert "loadbalancer.server.port=9000" in content

    def test_traefik_yml_contains_email(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config(email="me@example.com"))

        content = (tmp_path / "traefik.yml").read_text()
        assert "me@example.com" in content
        assert "letsencrypt" in content

    def test_acme_json_chmod_600_called_with_sudo(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        chmod_calls = [
            call for call in mock_runner.calls if "chmod" in call["cmd"]
        ]
        assert len(chmod_calls) == 1
        assert "600" in chmod_calls[0]["cmd"]
        assert str(tmp_path / "acme.json") in chmod_calls[0]["cmd"]
        assert chmod_calls[0]["sudo"] is True

    def test_acme_json_file_is_created(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        acme = tmp_path / "acme.json"
        assert acme.exists()
        assert acme.is_file()

    def test_output_dir_created_if_missing(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        target = tmp_path / "nested" / "traefik"
        provider = _make_provider(mock_runner, output_dir=target)
        provider.configure(_make_config())

        assert target.exists()
        assert (target / "docker-compose.yml").exists()


class TestTraefikProviderVerify:
    def test_verify_runs_docker_compose_config_without_sudo(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())
        mock_runner.calls.clear()  # isolate verify calls

        provider.verify()

        verify_calls = [
            c for c in mock_runner.calls if "docker" in c["cmd"] and "config" in c["cmd"]
        ]
        assert len(verify_calls) == 1
        call = verify_calls[0]
        assert call["sudo"] is False
        assert "compose" in call["cmd"]
        assert "-f" in call["cmd"]

    def test_verify_raises_when_compose_missing(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        with pytest.raises(ServerConfigError, match="not found"):
            provider.verify()

    def test_verify_raises_on_invalid_compose(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())
        mock_runner.set_response(
            "docker compose",
            CommandResult(
                returncode=1,
                stdout="",
                stderr="services.traefik.image must be a string",
            ),
        )

        with pytest.raises(ServerConfigError, match="validation failed"):
            provider.verify()


class TestTraefikProviderRemove:
    def test_remove_deletes_generated_files(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        assert (tmp_path / "docker-compose.yml").exists()
        assert (tmp_path / "traefik.yml").exists()
        assert (tmp_path / "acme.json").exists()

        provider.remove("app.example.com")

        assert not (tmp_path / "docker-compose.yml").exists()
        assert not (tmp_path / "traefik.yml").exists()
        assert not (tmp_path / "acme.json").exists()

    def test_remove_runs_docker_compose_down(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())
        mock_runner.calls.clear()

        provider.remove("app.example.com")

        down_calls = [c for c in mock_runner.calls if "down" in c["cmd"]]
        assert len(down_calls) == 1
        assert "compose" in down_calls[0]["cmd"]
        assert down_calls[0]["sudo"] is False

    def test_remove_nonexistent_does_not_raise(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        target = tmp_path / "nothing"
        provider = _make_provider(mock_runner, output_dir=target)
        provider.remove("app.example.com")  # must not raise

    def test_remove_idempotent(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        provider = _make_provider(mock_runner, output_dir=tmp_path)
        provider.configure(_make_config())

        provider.remove("app.example.com")
        provider.remove("app.example.com")  # second call must not raise

    def test_remove_cleans_up_empty_project_dir(
        self, mock_runner: MockSystemRunner, tmp_path: Path
    ) -> None:
        target = tmp_path / "proj"
        provider = _make_provider(mock_runner, output_dir=target)
        provider.configure(_make_config())

        provider.remove("app.example.com")

        assert not target.exists()
