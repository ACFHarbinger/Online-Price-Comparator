"""Unit tests for cli module."""

from __future__ import annotations

import pytest

from cli import main


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI --version flag output."""
    exit_code = main(["--version"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "python-module-template v0.1.0" in captured.out


def test_cli_batch_size(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI execution with custom --batch-size parameter."""
    exit_code = main(["--batch-size", "250"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "batch size: 250" in captured.out
