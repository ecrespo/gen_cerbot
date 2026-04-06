"""DistroDetector — reads /etc/os-release to determine the Linux distribution family."""

from __future__ import annotations

from pathlib import Path

from gen_cerbot.core.exceptions import UnsupportedDistroError
from gen_cerbot.domain.models import DistroFamily

_DEBIAN_IDS = {"debian", "ubuntu", "linuxmint", "pop", "elementary", "zorin"}
_REDHAT_IDS = {"fedora", "rhel", "centos", "rocky", "alma", "ol"}
_SUSE_IDS = {"opensuse-leap", "opensuse-tumbleweed", "sles", "opensuse"}

_DEFAULT_OS_RELEASE = Path("/etc/os-release")


class DistroDetector:
    """Detects the Linux distribution family from /etc/os-release."""

    def __init__(self, os_release_path: Path | None = None) -> None:
        self._path = os_release_path or _DEFAULT_OS_RELEASE

    def detect(self) -> DistroFamily:
        """Detect the distribution family.

        Returns:
            DistroFamily enum value.

        Raises:
            UnsupportedDistroError: If the distro is not recognized.
            FileNotFoundError: If /etc/os-release does not exist.
        """
        data = self._parse_os_release()
        distro_id = data.get("ID", "").lower().strip('"')
        id_like = data.get("ID_LIKE", "").lower().strip('"')

        if distro_id in _DEBIAN_IDS or "debian" in id_like:
            return DistroFamily.DEBIAN
        if distro_id in _REDHAT_IDS or "fedora" in id_like or "rhel" in id_like:
            return DistroFamily.REDHAT
        if distro_id in _SUSE_IDS or "suse" in id_like:
            return DistroFamily.SUSE

        raise UnsupportedDistroError(distro_id)

    def get_info(self) -> dict[str, str]:
        """Return the full parsed os-release data."""
        return self._parse_os_release()

    def _parse_os_release(self) -> dict[str, str]:
        """Parse /etc/os-release into a dictionary."""
        data: dict[str, str] = {}
        content = self._path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip().strip('"')
        return data
