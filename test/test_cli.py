"""Unit tests for cli module."""

from __future__ import annotations

from pathlib import Path

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


def test_cli_watchlist_track_sites_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """track / watchlist / sites / untrack persist without scraping."""
    db_path = tmp_path / "watchlist.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    assert (
        main(["track", "AMD Ryzen 9 9950X3D", "--no-refresh", "--scope", "eu_wide"])
        == 0
    )
    tracked_out = capsys.readouterr().out
    assert "Tracking 'AMD Ryzen 9 9950X3D'" in tracked_out
    assert "scope=eu_wide" in tracked_out

    assert main(["watchlist"]) == 0
    listing = capsys.readouterr().out
    assert "AMD Ryzen 9 9950X3D" in listing
    assert "eu_wide" in listing

    assert main(["sites", "disable", "amazon.es"]) == 0
    assert "amazon.es disabled globally" in capsys.readouterr().out
    assert main(["sites", "list"]) == 0
    sites_out = capsys.readouterr().out
    assert "off  amazon.es" in sites_out
    assert "on   pccomponentes" in sites_out or "on  pccomponentes" in sites_out

    assert (
        main(
            [
                "sites",
                "exclude",
                "AMD Ryzen 9 9950X3D",
                "pccomponentes",
                "--reason",
                "bundle",
            ]
        )
        == 0
    )
    assert main(["watchlist"]) == 0
    assert "pccomponentes:out" in capsys.readouterr().out

    assert main(["untrack", "AMD Ryzen 9 9950X3D"]) == 0
    assert main(["watchlist"]) == 0
    untracked = capsys.readouterr().out
    assert "off" in untracked
    assert "AMD Ryzen 9 9950X3D" in untracked

    assert main(["untrack", "does-not-exist"]) == 1


def test_cli_refresh_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI refresh command refreshes due products in watchlist."""
    db_path = tmp_path / "refresh_test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Add product with no-refresh
    assert main(["track", "AMD Ryzen 9 9950X3D", "--no-refresh"]) == 0
    capsys.readouterr()

    from datetime import datetime

    from models.listing import RawListing

    monkeypatch.setattr(
        "pipeline.refresh.run_discovery",
        lambda *args, **kwargs: [
            RawListing(
                source="amazon.es",
                source_kind="scraper",
                title="AMD Ryzen 9 9950X3D Processor",
                price_text="650,00 €",
                currency_hint="EUR",
                image_url=None,
                url="https://amazon.es/dp/B0EXAMPLE",
                site_display_name="Amazon.es",
                fetched_at=datetime.now(),
            )
        ],
    )

    # Run refresh
    assert main(["refresh"]) == 0
    out = capsys.readouterr().out
    assert "Refreshed 1 watchlist product(s)" in out
    assert "650.00 EUR" in out
    assert "AMD Ryzen 9 9950X3D" in out

    # Second refresh without force -> not due
    assert main(["refresh"]) == 0
    out2 = capsys.readouterr().out
    assert "No watchlist products were due for refresh" in out2

    # Second refresh with force -> refreshes again
    assert main(["refresh", "--force"]) == 0
    out3 = capsys.readouterr().out
    assert "Refreshed 1 watchlist product(s)" in out3
