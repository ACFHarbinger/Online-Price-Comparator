"""Unit tests for cli module."""

from __future__ import annotations

import pytest

from cli import main


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI --version flag output."""
    exit_code = main(["--version"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "online-price-comparator v0.1.0" in captured.out


def test_cli_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI with no subcommand prints help and exits cleanly."""
    exit_code = main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()
