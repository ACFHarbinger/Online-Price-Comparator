"""robots.txt lookup with a per-host TTL cache; fail-open on errors."""

from __future__ import annotations

import logging
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

LOGGER = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, RobotFileParser]] = {}
_LOCK = threading.Lock()
_FETCH_TIMEOUT_SECONDS = 5.0


def is_allowed(url: str, user_agent: str, *, cache_ttl_hours: float = 24.0) -> bool:
    """True if robots.txt for `url`'s host permits fetching `url` for `user_agent`.

    Uses `urllib.robotparser.RobotFileParser`. Caches the parsed robots.txt
    per-host in a module-level dict with a TTL (re-fetch after
    `cache_ttl_hours`). On any failure to fetch/parse robots.txt (network
    error, 404, malformed file), fail OPEN (return True) - the historical
    convention is "no robots.txt / can't determine it -> assume allowed",
    not "block everything because we couldn't check."
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True

    cache_key = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    ttl_seconds = max(0.0, cache_ttl_hours) * 3600.0
    now = time.monotonic()

    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached is not None and (now - cached[0]) < ttl_seconds:
            parser = cached[1]
        else:
            parser = None

    if parser is None:
        fetched = _fetch_parser(cache_key, user_agent)
        if fetched is None:
            return True
        parser = fetched
        with _LOCK:
            _CACHE[cache_key] = (time.monotonic(), parser)

    try:
        return bool(parser.can_fetch(user_agent, url))
    except Exception:
        LOGGER.debug(
            "robots.txt can_fetch failed for %s; assuming allowed",
            url,
            exc_info=True,
        )
        return True


def _fetch_parser(origin: str, user_agent: str) -> RobotFileParser | None:
    """Download and parse robots.txt for `origin`. Return None to fail open."""
    robots_url = urljoin(origin + "/", "robots.txt")
    request = Request(
        robots_url,
        headers={"User-Agent": user_agent},
        method="GET",
    )
    try:
        with urlopen(request, timeout=_FETCH_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            if int(status) != 200:
                return None
            raw = response.read()
    except HTTPError:
        # Includes 404 and other HTTP errors: cannot determine — fail open.
        LOGGER.debug(
            "robots.txt HTTP error for %s; assuming allowed",
            robots_url,
            exc_info=True,
        )
        return None
    except (URLError, TimeoutError, OSError, ValueError):
        LOGGER.debug(
            "robots.txt fetch failed for %s; assuming allowed",
            robots_url,
            exc_info=True,
        )
        return None

    try:
        text = raw.decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines())
    except Exception:
        LOGGER.debug(
            "robots.txt parse failed for %s; assuming allowed",
            robots_url,
            exc_info=True,
        )
        return None
    return parser
