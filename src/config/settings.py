"""Application configuration, loaded from environment / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Online Price Comparator.

    All fields are optional so the tool runs with zero configuration:
    scrapers work without any keys, and unconfigured search-API providers
    are skipped rather than causing a startup failure.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_path: str = "data/price_comparator.db"
    enabled_scrapers: str = ""

    serpapi_key: str | None = None
    google_cse_api_key: str | None = None
    google_cse_cx: str | None = None

    def enabled_scraper_keys(self) -> set[str] | None:
        """Return the configured scraper allowlist, or None to mean "all"."""
        keys = {key.strip() for key in self.enabled_scrapers.split(",") if key.strip()}
        return keys or None


def get_settings() -> Settings:
    """Load settings from the environment / .env file."""
    return Settings()
