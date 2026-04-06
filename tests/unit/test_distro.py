"""Unit tests for DistroDetector using os-release fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from gen_cerbot.core.exceptions import UnsupportedDistroError
from gen_cerbot.domain.models import DistroFamily
from gen_cerbot.utils.distro import DistroDetector


class TestDistroDetector:
    def test_detect_ubuntu(self, os_release_ubuntu: Path) -> None:
        detector = DistroDetector(os_release_path=os_release_ubuntu)
        assert detector.detect() == DistroFamily.DEBIAN

    def test_detect_fedora(self, os_release_fedora: Path) -> None:
        detector = DistroDetector(os_release_path=os_release_fedora)
        assert detector.detect() == DistroFamily.REDHAT

    def test_detect_opensuse(self, os_release_opensuse: Path) -> None:
        detector = DistroDetector(os_release_path=os_release_opensuse)
        assert detector.detect() == DistroFamily.SUSE

    def test_detect_unsupported_distro(self, tmp_path: Path) -> None:
        os_release = tmp_path / "os-release"
        os_release.write_text('ID=archlinux\nNAME="Arch Linux"\n')
        detector = DistroDetector(os_release_path=os_release)
        with pytest.raises(UnsupportedDistroError) as exc_info:
            detector.detect()
        assert "archlinux" in str(exc_info.value)

    def test_detect_missing_file(self, tmp_path: Path) -> None:
        detector = DistroDetector(os_release_path=tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError):
            detector.detect()

    def test_get_info_returns_dict(self, os_release_ubuntu: Path) -> None:
        detector = DistroDetector(os_release_path=os_release_ubuntu)
        info = detector.get_info()
        assert info["ID"] == "ubuntu"
        assert info["VERSION_ID"] == "22.04"

    def test_detect_debian_by_id_like(self, tmp_path: Path) -> None:
        os_release = tmp_path / "os-release"
        os_release.write_text('ID=somedebian\nID_LIKE="debian"\n')
        detector = DistroDetector(os_release_path=os_release)
        assert detector.detect() == DistroFamily.DEBIAN
