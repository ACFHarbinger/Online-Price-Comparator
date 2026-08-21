"""Unit tests for the v1.7 runtime Settings additions."""

from __future__ import annotations

from decimal import Decimal

import pytest
from config.settings import Settings, get_settings, override_settings


def test_v17_field_defaults() -> None:
    """The v1.7 fields load with the defaults documented in
    docs/moon/roadmaps/settings_and_config.md's "Runtime `Settings` -
    planned additions (v1.7)" table.
    """
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.display_currency == "EUR"
    assert settings.fx_rate_provider == "ecb"
    assert settings.fx_rate_cache_ttl_hours == 24
    assert settings.default_results_per_source == 10
    assert settings.max_results_per_source == 20
    assert settings.monitoring_enabled is False
    assert settings.refresh_interval_hours == 12
    assert settings.request_timeout_seconds == 15.0
    assert settings.connect_timeout_seconds == 5.0
    assert settings.default_min_request_interval_seconds == 5.0
    assert settings.alerts_enabled is True
    assert settings.alert_drop_percent == 10.0
    assert settings.alert_drop_min_amount == Decimal("10.00")
    assert settings.alert_rolling_window_days == 7
    assert settings.alert_all_time_low_percent == 2.0
    assert settings.alert_all_time_low_min_amount == Decimal("5.00")
    assert settings.alert_cooldown_hours == 72
    assert settings.alert_channel == "none"
    assert settings.telegram_bot_token is None
    assert settings.telegram_chat_id is None
    assert settings.discord_webhook_url is None


def test_alert_channel_rejects_unknown_value() -> None:
    """`alert_channel` is a closed `Literal`, not a free-form string."""
    with pytest.raises(ValueError, match="alert_channel"):
        Settings(_env_file=None, alert_channel="sms")  # type: ignore[call-arg, arg-type]


def test_alert_min_amounts_parse_env_strings_as_decimal() -> None:
    """Env-var-shaped string input still lands as `Decimal`, not `float`."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        alert_drop_min_amount="12.50",  # type: ignore[arg-type]
        alert_all_time_low_min_amount="3.75",  # type: ignore[arg-type]
    )

    assert settings.alert_drop_min_amount == Decimal("12.50")
    assert settings.alert_all_time_low_min_amount == Decimal("3.75")


def test_v17_fields_overridable_via_override_settings() -> None:
    """`override_settings` (used by the dashboard's per-request overrides)
    reaches the new fields the same way it reaches existing ones.
    """
    with override_settings(display_currency="USD", alert_channel="telegram"):
        settings = get_settings()
        assert settings.display_currency == "USD"
        assert settings.alert_channel == "telegram"

    # Override does not leak past the context manager.
    assert get_settings().display_currency == "EUR"
