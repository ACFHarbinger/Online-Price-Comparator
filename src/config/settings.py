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

    request_jitter_fraction: float = 0.20
    retry_max_attempts: int = 2
    retry_initial_backoff_seconds: float = 2.0
    retry_max_backoff_seconds: float = 30.0
    block_circuit_breaker_failures: int = 2
    block_circuit_breaker_cooldown_hours: float = 24.0
    response_cache_ttl_seconds: int = 600
    robots_cache_ttl_hours: float = 24.0

    # Headless-browser fallback (Playwright) for sites whose Cloudflare/
    # similar JS challenge blocks a plain httpx request. Off by default;
    # explicitly allowlisted per site. Renders the page with a plain,
    # honestly-identified browser and nothing more - no stealth plugins,
    # fingerprint spoofing, or CAPTCHA-solving. See
    # docs/moon/roadmaps/scrapers_and_retailers.md.
    browser_fallback_enabled: bool = False
    browser_fallback_sites: str = ""

    # False opens a real, visible browser window instead of a headless one,
    # for sites whose challenge doesn't auto-resolve and needs a human to
    # click through it - a person solving their own challenge, not
    # automated CAPTCHA-solving. The wait is extended accordingly so
    # there's real time to interact with it before the page is captured.
    browser_fallback_headless: bool = True
    browser_fallback_headless_wait_seconds: float = 5.0
    browser_fallback_manual_wait_seconds: float = 45.0

    def enabled_scraper_keys(self) -> set[str] | None:
        """Return the configured scraper allowlist, or None to mean "all"."""
        keys = {key.strip() for key in self.enabled_scrapers.split(",") if key.strip()}
        return keys or None

    def browser_fallback_site_keys(self) -> set[str]:
        """Return the set of site keys allowed to use the browser fallback."""
        return {
            key.strip() for key in self.browser_fallback_sites.split(",") if key.strip()
        }


def get_settings() -> Settings:
    """Load settings from the environment / .env file."""
    return Settings()
