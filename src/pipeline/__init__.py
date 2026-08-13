"""Orchestration: search+scrape -> normalize -> persist."""

from .discover import run_discovery
from .snapshot import persist_snapshot

__all__ = ["persist_snapshot", "run_discovery"]
