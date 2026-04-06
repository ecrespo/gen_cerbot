"""SystemRunner — all subprocess calls go through this module."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from gen_cerbot.core.exceptions import CommandError, SudoError


@dataclass
class CommandResult:
    """Result of a system command execution."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


class SystemRunner:
    """Executes system commands, optionally prepending sudo."""

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run

    def run(
        self,
        cmd: list[str],
        *,
        sudo: bool = False,
        check: bool = True,
        capture: bool = True,
    ) -> CommandResult:
        """Run a system command.

        Args:
            cmd: Command and arguments as a list.
            sudo: If True, prepends ["sudo"] to the command.
            check: If True, raises on non-zero exit code.
            capture: If True, captures stdout/stderr.

        Returns:
            CommandResult with returncode, stdout, stderr.

        Raises:
            SudoError: If sudo command fails and check=True.
            CommandError: If non-sudo command fails and check=True.
        """
        full_cmd = ["sudo", *cmd] if sudo else list(cmd)

        if self._dry_run:
            cmd_str = " ".join(full_cmd)
            return CommandResult(returncode=0, stdout=f"[DRY RUN] {cmd_str}", stderr="")

        result = subprocess.run(
            full_cmd,
            capture_output=capture,
            text=True,
        )

        cmd_result = CommandResult(
            returncode=result.returncode,
            stdout=result.stdout if capture else "",
            stderr=result.stderr if capture else "",
        )

        if check and not cmd_result.success:
            cmd_str = " ".join(full_cmd)
            if sudo:
                raise SudoError(cmd_str, result.returncode, cmd_result.stderr)
            raise CommandError(cmd_str, result.returncode, cmd_result.stderr)

        return cmd_result
