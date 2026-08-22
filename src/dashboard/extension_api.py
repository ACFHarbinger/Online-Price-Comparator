"""Localhost HTTP callback for the v2.20 client-side monitor extension (v1).

The Dash app runs on Flask; this registers a ``localhost``-bound endpoint the
extension can POST detected changes to directly instead of the manual JSON-lines
export/import round-trip. Every record still flows through the same
identity-matching -> condition -> FX -> ``persist_snapshot`` pipeline
(``pipeline.extension_import.import_records``) - an extension observation is not
a trust shortcut.

Security: this is intentionally a localhost-only, unauthenticated endpoint for
a personal tool. The Dash dev server defaults to binding ``127.0.0.1``, but
that default is a `--host` CLI flag, not an enforced guarantee - a user who
runs `dashboard --host 0.0.0.0` (e.g. to view it from their phone on the same
LAN) would otherwise silently expose this unauthenticated write endpoint to
every device on that LAN too. The route itself rejects any request whose
remote address is not loopback, regardless of what host the server is bound
to - the same "don't just document the constraint, enforce it in code"
lesson as the v2.15/Leboncoin server-side-collection fix.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify, request
from sqlalchemy import Engine

from pipeline.extension_import import import_records

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "/api/extension/import"
_LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1"})


def register_extension_api(server: Flask, engine: Engine) -> None:
    """Register the extension-report endpoint on a Flask/Dash ``server``."""

    @server.route(DEFAULT_ENDPOINT, methods=["POST"])
    def _extension_import() -> tuple[Any, int]:
        if request.remote_addr not in _LOOPBACK_ADDRESSES:
            logger.warning(
                "Rejected non-loopback request to %s from %s",
                DEFAULT_ENDPOINT,
                request.remote_addr,
            )
            return jsonify({"error": "loopback requests only"}), 403

        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "expected a JSON body"}), 400

        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
            records = payload["records"]
        else:
            return jsonify(
                {"error": "expected a record object or {'records': [...]}"}
            ), 400

        result = import_records(records, engine)
        return (
            jsonify(
                {
                    "imported": result.records_imported,
                    "products": result.products_handled,
                    "skipped": result.skipped,
                }
            ),
            200,
        )
