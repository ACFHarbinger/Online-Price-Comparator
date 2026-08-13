"""Unit tests for main entry point."""

from __future__ import annotations

import pytest

from main import run


def test_main_run(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main.run() execution with sys.argv."""
    monkeypatch.setattr("sys.argv", ["online-price-comparator", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        run()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "online-price-comparator v0.1.0" in captured.out
