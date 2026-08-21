"""Alert channel dispatch: one internal protocol, two concrete channels.

Both channels are plain HTTP calls (Telegram ``sendMessage``, Discord webhook
``POST``) via the shared ``fetch.http_client``. Fail-open by contract: a
misconfigured channel or any HTTP error logs and returns ``False`` - it never
raises, so alerting can never break the refresh loop. Adding a third channel
later means implementing ``AlertDispatcher`` and wiring it into
``build_dispatchers``.
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from config.settings import Settings
from fetch.http_client import build_http_client

logger = logging.getLogger(__name__)

TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"


class AlertDispatcher(Protocol):
    """Channel-agnostic alert sink."""

    name: str

    def is_configured(self) -> bool:
        """True when this channel has the credentials/config it needs."""
        ...

    def send(self, message: str) -> bool:
        """Deliver ``message``; return True on success. Never raises."""
        ...


class TelegramDispatcher:
    """Raw Telegram Bot API ``sendMessage`` call to one chat."""

    name = "telegram"

    def __init__(
        self,
        bot_token: str | None,
        chat_id: str | None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._token = bot_token.strip() if bot_token else None
        self._chat_id = chat_id.strip() if chat_id else None
        self._client = client if client is not None else build_http_client()

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, message: str) -> bool:
        if not self.is_configured():
            logger.warning("Telegram not configured; skipping alert")
            return False
        url = TELEGRAM_SEND_URL.format(token=self._token)
        try:
            response = self._client.post(
                url, json={"chat_id": self._chat_id, "text": message}
            )
        except httpx.HTTPError:
            logger.warning("Telegram send failed", exc_info=True)
            return False
        if response.status_code >= 300:
            logger.warning("Telegram send returned HTTP %s", response.status_code)
            return False
        return True


class DiscordDispatcher:
    """Plain Discord webhook ``POST`` (no bot setup required)."""

    name = "discord"

    def __init__(
        self,
        webhook_url: str | None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = webhook_url.strip() if webhook_url else None
        self._client = client if client is not None else build_http_client()

    def is_configured(self) -> bool:
        return bool(self._url)

    def send(self, message: str) -> bool:
        if not self._url:
            logger.warning("Discord not configured; skipping alert")
            return False
        try:
            response = self._client.post(self._url, json={"content": message})
        except httpx.HTTPError:
            logger.warning("Discord send failed", exc_info=True)
            return False
        if response.status_code >= 300:
            logger.warning("Discord send returned HTTP %s", response.status_code)
            return False
        return True


def build_dispatchers(settings: Settings) -> list[AlertDispatcher]:
    """Build the enabled channel dispatchers from ``settings.alert_channel``.

    ``alert_channel`` is one of ``none`` / ``telegram`` / ``discord`` /
    ``both``. Returns an empty list for ``none`` (no channels, alerts are
    evaluated but not delivered - safe for a tool with no keys configured).
    """
    dispatchers: list[AlertDispatcher] = []
    channel = settings.alert_channel
    if channel in ("telegram", "both"):
        dispatchers.append(
            TelegramDispatcher(settings.telegram_bot_token, settings.telegram_chat_id)
        )
    if channel in ("discord", "both"):
        dispatchers.append(DiscordDispatcher(settings.discord_webhook_url))
    return dispatchers
