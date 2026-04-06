"""Shared pytest fixtures for gen_cerbot tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from gen_cerbot.utils.system import CommandResult, SystemRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OS_RELEASE_DIR = FIXTURES_DIR / "os-release"


@pytest.fixture
def os_release_ubuntu() -> Path:
    return OS_RELEASE_DIR / "ubuntu-22.04"


@pytest.fixture
def os_release_fedora() -> Path:
    return OS_RELEASE_DIR / "fedora-40"


@pytest.fixture
def os_release_opensuse() -> Path:
    return OS_RELEASE_DIR / "opensuse-leap-15.5"


class MockSystemRunner(SystemRunner):
    """SystemRunner that records calls instead of executing them."""

    def __init__(self) -> None:
        super().__init__(dry_run=False)
        self.calls: list[dict[str, object]] = []
        self._responses: dict[str, CommandResult] = {}

    def set_response(self, cmd_prefix: str, result: CommandResult) -> None:
        """Pre-configure a response for commands starting with cmd_prefix."""
        self._responses[cmd_prefix] = result

    def run(
        self,
        cmd: list[str],
        *,
        sudo: bool = False,
        check: bool = True,
        capture: bool = True,
    ) -> CommandResult:
        full_cmd = ["sudo", *cmd] if sudo else list(cmd)
        cmd_str = " ".join(full_cmd)
        self.calls.append({"cmd": full_cmd, "sudo": sudo, "check": check})

        for prefix, response in self._responses.items():
            if cmd_str.startswith(prefix):
                if check and not response.success:
                    from gen_cerbot.core.exceptions import CommandError, SudoError

                    if sudo:
                        raise SudoError(cmd_str, response.returncode, response.stderr)
                    raise CommandError(cmd_str, response.returncode, response.stderr)
                return response

        return CommandResult(returncode=0, stdout="", stderr="")


@pytest.fixture
def mock_runner() -> MockSystemRunner:
    return MockSystemRunner()
