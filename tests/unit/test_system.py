"""Unit tests for SystemRunner."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gen_cerbot.core.exceptions import CommandError, SudoError
from gen_cerbot.utils.system import SystemRunner


class TestSystemRunner:
    def test_run_prepends_sudo_when_requested(self) -> None:
        runner = SystemRunner(dry_run=True)
        result = runner.run(["nginx", "-t"], sudo=True)
        assert "[DRY RUN] sudo nginx -t" in result.stdout

    def test_run_no_sudo_by_default(self) -> None:
        runner = SystemRunner(dry_run=True)
        result = runner.run(["echo", "hello"])
        assert result.stdout == "[DRY RUN] echo hello"
        assert "sudo" not in result.stdout

    def test_dry_run_always_succeeds(self) -> None:
        runner = SystemRunner(dry_run=True)
        result = runner.run(["false"], sudo=True)
        assert result.success

    @patch("gen_cerbot.utils.system.subprocess.run")
    def test_run_real_command_success(self, mock_run: object) -> None:
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result  # type: ignore[attr-defined]

        runner = SystemRunner()
        result = runner.run(["echo", "test"])
        assert result.success
        assert result.stdout == "output"

    @patch("gen_cerbot.utils.system.subprocess.run")
    def test_run_raises_command_error(self, mock_run: object) -> None:
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_run.return_value = mock_result  # type: ignore[attr-defined]

        runner = SystemRunner()
        with pytest.raises(CommandError) as exc_info:
            runner.run(["bad-command"])
        assert exc_info.value.returncode == 1

    @patch("gen_cerbot.utils.system.subprocess.run")
    def test_run_raises_sudo_error(self, mock_run: object) -> None:
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "permission denied"
        mock_run.return_value = mock_result  # type: ignore[attr-defined]

        runner = SystemRunner()
        with pytest.raises(SudoError) as exc_info:
            runner.run(["apt-get", "install"], sudo=True)
        assert exc_info.value.returncode == 1

    @patch("gen_cerbot.utils.system.subprocess.run")
    def test_run_no_check_does_not_raise(self, mock_run: object) -> None:
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_run.return_value = mock_result  # type: ignore[attr-defined]

        runner = SystemRunner()
        result = runner.run(["bad-command"], check=False)
        assert not result.success
