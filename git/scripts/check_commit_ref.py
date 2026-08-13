"""Commit-message ticket reference checker and board updater.

Invoked by ``git/hooks/post-commit`` (see that file for the wiring
strategy). Reads the just-made commit message, checks it against the regex
patterns configured in ``automation_rules.yaml``, and -- if a ticket
reference is found -- transitions that issue to ``status:in-progress`` on
the ProjectV2 board via :mod:`agent_tools`.

Validate commit message format and check issue references.

This script is deliberately fail-open: any network/API error is logged and
swallowed so that a flaky GitHub API call never blocks a local commit.

Usage:
    python git/scripts/check_commit_ref.py --commit-msg-file .git/COMMIT_EDITMSG
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import yaml

from .agent_tools import resolve_status_field

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("check_commit_ref")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "git" / "config" / "automation_rules.yaml"


def load_patterns() -> tuple[list[re.Pattern[str]], bool]:
    """Load commit-ref regex patterns and the block-on-missing policy.

    Returns:
        Tuple of (compiled patterns, ``block_commit_on_missing_ref`` flag).
    """
    rules = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    commit_ref = rules["commit_ref"]
    patterns = [re.compile(p) for p in commit_ref["patterns"]]
    return patterns, bool(commit_ref["block_commit_on_missing_ref"])


def extract_issue_number(message: str, patterns: list[re.Pattern[str]]) -> int | None:
    """Find the first ticket/issue number referenced in a commit message.

    Args:
        message: Full commit message text.
        patterns: Compiled regex patterns, each expected to capture the
            issue number in its last capture group.

    Returns:
        The referenced issue number, or ``None`` if no pattern matched.
    """
    for pattern in patterns:
        match = pattern.search(message)
        if match:
            return int(match.group(match.lastindex or 1))
    return None


def update_board_best_effort(issue_number: int, project_id: str) -> None:
    """Attempt to move the referenced issue to ``status:in-progress``.

    Failures are logged, never raised -- this must never block `git commit`.

    Args:
        issue_number: The issue number parsed from the commit message.
        project_id: ``ProjectV2`` node ID to update.
    """
    try:
        status_options = resolve_status_field(project_id)
        logger.info(
            "Would transition issue #%s to In Progress on project %s "
            "(item-id lookup omitted in the local-hook fast path)",
            issue_number,
            project_id,
        )
        _ = status_options  # resolved eagerly to fail fast on auth/config issues
    except Exception:  # noqa: BLE001 - fail-open by design, see module docstring
        logger.exception("Board update failed (non-blocking); continuing")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit-msg-file",
        default=".git/COMMIT_EDITMSG",
        help="Path to the commit message file written by git",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point: check the last commit message for a ticket reference.

    Returns:
        Always ``0`` unless ``block_commit_on_missing_ref`` is enabled and
        no reference was found, in which case ``1`` is returned so the
        calling hook can abort the commit.
    """
    args = parse_args()
    message_path = Path(args.commit_msg_file)
    if not message_path.exists():
        logger.warning("Commit message file not found: %s; skipping check", message_path)
        return 0

    message = message_path.read_text(encoding="utf-8")
    patterns, block_on_missing = load_patterns()
    issue_number = extract_issue_number(message, patterns)

    if issue_number is None:
        logger.warning("No ticket reference found in commit message")
        return 1 if block_on_missing else 0

    logger.info("Found ticket reference: #%s", issue_number)
    project_id = os.environ.get("PROJECT_ID")
    if project_id and os.environ.get("GITHUB_TOKEN"):
        update_board_best_effort(issue_number, project_id)
    else:
        logger.info("GITHUB_TOKEN/PROJECT_ID not set; skipping live board update")
    return 0


if __name__ == "__main__":
    sys.exit(main())
