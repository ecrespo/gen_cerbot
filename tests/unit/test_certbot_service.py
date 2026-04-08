"""Unit tests for CertbotService orchestration.

Focuses on the end-to-end wiring of flags (``staging``, ``dry_run``,
``skip_dns_check``) through ``generate()`` — the per-component behavior
is covered in the dedicated test files.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gen_cerbot.domain.models import (
    CertificateConfig,
    DistroFamily,
    ServerType,
)
from gen_cerbot.domain.services import CertbotService
from gen_cerbot.utils.system import SystemRunner


@pytest.fixture
def wired_service() -> tuple[CertbotService, dict[str, MagicMock], SystemRunner]:
    """Build a CertbotService with every collaborator mocked.

    Returns the service, a dict of mocks keyed by role, and the real
    ``SystemRunner`` so tests can assert on ``dry_run`` state transitions.
    """
    runner = SystemRunner(dry_run=False)
    mocks = {
        "detector": MagicMock(),
        "dns": MagicMock(),
        "installer": MagicMock(),
        "manager": MagicMock(),
        "provider": MagicMock(),
        "factory": MagicMock(),
    }
    mocks["detector"].detect.return_value = DistroFamily.DEBIAN
    mocks["factory"].get.return_value = mocks["provider"]

    service = CertbotService(
        runner=runner,
        distro_detector=mocks["detector"],
        dns_validator=mocks["dns"],
        certbot_installer=mocks["installer"],
        certbot_manager=mocks["manager"],
        provider_factory=mocks["factory"],
    )
    return service, mocks, runner


class TestStagingPropagation:
    def test_staging_true_reaches_manager_request(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="stg.example.com",
            email="a@b.c",
            server_type=ServerType.NGINX,
            staging=True,
        )
        service.generate(cfg)

        mocks["manager"].request.assert_called_once_with(
            domain="stg.example.com",
            email="a@b.c",
            server_type=ServerType.NGINX,
            staging=True,
        )

    def test_staging_false_is_default(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="prod.example.com",
            email="a@b.c",
            server_type=ServerType.NGINX,
        )
        service.generate(cfg)
        assert mocks["manager"].request.call_args.kwargs["staging"] is False

    def test_traefik_never_calls_request_even_with_staging(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="t.io",
            email="a@b.c",
            server_type=ServerType.TRAEFIK,
            staging=True,
        )
        service.generate(cfg)
        mocks["manager"].request.assert_not_called()
        mocks["manager"].verify_service.assert_called_once()


class TestDryRunToggle:
    def test_dry_run_flag_flipped_during_generate(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, runner = wired_service

        observed: list[bool] = []
        mocks["installer"].ensure_installed.side_effect = (
            lambda *_a, **_kw: observed.append(runner.dry_run)
        )

        service.generate(
            CertificateConfig(
                domain="example.com",
                email="a@b.c",
                server_type=ServerType.NGINX,
                dry_run=True,
            )
        )
        assert observed == [True]
        assert runner.dry_run is False  # restored

    def test_dry_run_restored_on_exception(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, runner = wired_service
        mocks["detector"].detect.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            service.generate(
                CertificateConfig(
                    domain="example.com",
                    email="a@b.c",
                    server_type=ServerType.NGINX,
                    dry_run=True,
                )
            )
        assert runner.dry_run is False


class TestSkipDnsCheck:
    def test_skip_dns_check_forwarded_to_validator(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="x.io",
            email="a@b.c",
            server_type=ServerType.NGINX,
            skip_dns_check=True,
        )
        service.generate(cfg)
        mocks["dns"].check.assert_called_once_with("x.io", skip=True)

    def test_skip_dns_check_default_false(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="x.io", email="a@b.c", server_type=ServerType.NGINX
        )
        service.generate(cfg)
        mocks["dns"].check.assert_called_once_with("x.io", skip=False)


class TestOrchestrationOrder:
    def test_full_happy_path_invokes_all_steps(
        self,
        wired_service: tuple[CertbotService, dict[str, MagicMock], SystemRunner],
    ) -> None:
        service, mocks, _ = wired_service
        cfg = CertificateConfig(
            domain="example.com", email="a@b.c", server_type=ServerType.NGINX
        )
        service.generate(cfg)

        mocks["detector"].detect.assert_called_once()
        mocks["dns"].check.assert_called_once()
        mocks["factory"].get.assert_called_once_with(
            ServerType.NGINX, DistroFamily.DEBIAN
        )
        mocks["provider"].install.assert_called_once()
        mocks["provider"].configure.assert_called_once_with(cfg)
        mocks["provider"].verify.assert_called_once()
        mocks["installer"].ensure_installed.assert_called_once_with(
            DistroFamily.DEBIAN, ServerType.NGINX
        )
        mocks["manager"].request.assert_called_once()
        mocks["manager"].verify_service.assert_called_once_with(
            ServerType.NGINX, DistroFamily.DEBIAN
        )
