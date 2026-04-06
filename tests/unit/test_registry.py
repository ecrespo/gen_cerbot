"""Unit tests for CertRegistry."""

from __future__ import annotations

from pathlib import Path

from gen_cerbot.domain.models import (
    CertificateRecord,
    DistroFamily,
    ServerType,
)
from gen_cerbot.utils.registry import CertRegistry


def _make_record(domain: str = "test.example.com") -> CertificateRecord:
    return CertificateRecord(
        domain=domain,
        email="admin@example.com",
        server_type=ServerType.NGINX,
        distro_family=DistroFamily.DEBIAN,
        project_name="test",
    )


class TestCertRegistry:
    def test_add_and_get(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        record = _make_record()
        registry.add(record)
        result = registry.get("test.example.com")
        assert result is not None
        assert result.domain == "test.example.com"

    def test_add_is_idempotent(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        record = _make_record()
        registry.add(record)
        registry.add(record)
        assert len(registry.list_all()) == 1

    def test_remove(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        registry.add(_make_record())
        assert registry.remove("test.example.com") is True
        assert registry.get("test.example.com") is None

    def test_remove_nonexistent(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        assert registry.remove("nonexistent.com") is False

    def test_list_all(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        registry.add(_make_record("a.example.com"))
        registry.add(_make_record("b.example.com"))
        assert len(registry.list_all()) == 2

    def test_exists(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        registry.add(_make_record())
        assert registry.exists("test.example.com") is True
        assert registry.exists("other.com") is False

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        path = tmp_path / "registry.json"
        registry1 = CertRegistry(path)
        registry1.add(_make_record())

        registry2 = CertRegistry(path)
        assert registry2.get("test.example.com") is not None

    def test_empty_registry(self, tmp_path: Path) -> None:
        registry = CertRegistry(tmp_path / "registry.json")
        assert registry.list_all() == []
