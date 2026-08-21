"""Tests for the Telegram / Discord dispatch channels (mocked over HTTP)."""

from __future__ import annotations

import httpx
import respx

from alerting.dispatch import (
    TELEGRAM_SEND_URL,
    DiscordDispatcher,
    TelegramDispatcher,
    build_dispatchers,
)
from config.settings import Settings


def test_telegram_configured_only_with_token_and_chat() -> None:
    assert TelegramDispatcher("tok", "chat").is_configured() is True
    assert TelegramDispatcher(None, "chat").is_configured() is False
    assert TelegramDispatcher("tok", None).is_configured() is False
    assert TelegramDispatcher("   ", "").is_configured() is False


def test_telegram_send_success() -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    with respx.mock() as router:
        route = router.post(url).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        dispatcher = TelegramDispatcher("tok", "chat", client=httpx.Client())
        assert dispatcher.send("hello") is True
        assert route.called is True


def test_telegram_send_http_error_returns_false() -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    with respx.mock() as router:
        router.post(url).mock(return_value=httpx.Response(500))
        dispatcher = TelegramDispatcher("tok", "chat", client=httpx.Client())
        assert dispatcher.send("hello") is False


def test_telegram_send_transport_error_returns_false() -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    with respx.mock() as router:
        router.post(url).mock(side_effect=httpx.ConnectError("boom"))
        dispatcher = TelegramDispatcher("tok", "chat", client=httpx.Client())
        assert dispatcher.send("hello") is False


def test_telegram_unconfigured_send_returns_false() -> None:
    assert TelegramDispatcher(None, None).send("hello") is False


def test_discord_configured_only_with_url() -> None:
    dispatcher = DiscordDispatcher("https://discord.com/api/webhooks/1")
    assert dispatcher.is_configured() is True
    assert DiscordDispatcher(None).is_configured() is False


def test_discord_send_success() -> None:
    url = "https://discord.com/api/webhooks/1"
    with respx.mock() as router:
        route = router.post(url).mock(return_value=httpx.Response(204))
        dispatcher = DiscordDispatcher(url, client=httpx.Client())
        assert dispatcher.send("hello") is True
        assert route.called is True


def test_discord_send_error_returns_false() -> None:
    url = "https://discord.com/api/webhooks/1"
    with respx.mock() as router:
        router.post(url).mock(return_value=httpx.Response(400))
        dispatcher = DiscordDispatcher(url, client=httpx.Client())
        assert dispatcher.send("hello") is False


def test_discord_unconfigured_send_returns_false() -> None:
    assert DiscordDispatcher(None).send("hello") is False


def test_build_dispatchers_from_channel_setting() -> None:
    none_settings = Settings(_env_file=None, alert_channel="none")  # type: ignore[call-arg]
    assert build_dispatchers(none_settings) == []

    tg = Settings(  # type: ignore[call-arg]
        _env_file=None,
        alert_channel="telegram",
        telegram_bot_token="tok",
        telegram_chat_id="chat",
    )
    tg_names = [d.name for d in build_dispatchers(tg)]
    assert tg_names == ["telegram"]

    both = Settings(  # type: ignore[call-arg]
        _env_file=None,
        alert_channel="both",
        telegram_bot_token="tok",
        telegram_chat_id="chat",
        discord_webhook_url="https://discord.com/api/webhooks/1",
    )
    assert {d.name for d in build_dispatchers(both)} == {"telegram", "discord"}
