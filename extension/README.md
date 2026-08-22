# OPC Client-Side Monitor (v2.20, PT/ES tier)

A **Manifest V3** browser extension. On a **tracked retailer listing page** it
reads the schema.org `Product`/`Offer` JSON-LD already rendered in the page,
derives the site from the hostname, keeps a per-URL local snapshot, and records
a change only when the price/title moved. The popup sends the detected changes
to OPC's localhost endpoint, or exports them as a JSON-lines file, which OPC
consumes via `cli refresh --import-extension-file <path>`. No live HTTP callback
to a remote server; the extension makes zero network calls of its own except the
user-initiated localhost send.

**Scope (2026-08-22):** PT/ES tier — Amazon.es (`/dp/*`), PcComponentes
(`.pt`/`.com`), PCDIGA, Worten.pt, Fnac.pt, Chip7.pt, Wallapop.es (`/item/*`),
plus the original Leboncoin.fr (`/ad/*`). Listings are matched by the
`content_scripts.matches` in `manifest.json`.

## What's here

- `manifest.json` — Manifest V3. Permissions are minimal (`storage`, `downloads`)
  plus `http://127.0.0.1/*` and `http://localhost/*` so the popup can POST to
  OPC. `host_permissions` / `content_scripts.matches` are scoped to each site's
  listing-page URL pattern only.
- `content.js` — derives `site_key`/`site_display_name` from the hostname,
  reads the `Product`/`Offer` JSON-LD (or a site's CSS fallback), compares to the
  last snapshot for that URL, and appends detected changes to `opc_changes`.
- `site_fallbacks.js` — per-site CSS-selector fallback config, consulted only
  when JSON-LD is absent. **Selectors are intentionally left empty** — fill each
  per site only after verifying a real listing page (see below).
- `popup.js` / `popup.html` — send detected changes to OPC's localhost endpoint,
  or export them as JSON-lines.

## Load it unpacked (manual test)

1. Open Chrome and go to `chrome://extensions`.
2. Toggle **Developer mode** (top right).
3. Click **Load unpacked** and select this `extension/` directory.
4. Open a real listing page for any of the scoped sites.

## Per-site verification (required before a site is trusted / flipped)

For each site, load the extension unpacked and visit a real listing page, then
confirm in the dev-tools console (F12):

```
[OPC] <Site display name> first snapshot: {...}
```

(a fresh snapshot) or a `change detected` / `snapshot unchanged` line. If a site
logs `No Product data found on <site> ...`, then either (a) the page isn't
covered by `content_scripts.matches` in `manifest.json`, or (b) the page lacks
complete JSON-LD — in which case add that site's selectors to
`site_fallbacks.js` **only after** you've verified them against a real page.

Console helpers:

```js
chrome.storage.local.get(["opc_changes"], (r) => console.log(r.opc_changes));
location.reload(); // re-run the content script on the current page
```

## Send to OPC

1. Click the extension's toolbar action and press **Send changes to OPC** (POSTs
   to `http://127.0.0.1:8050/api/extension/import`) or **Export to JSON-lines
   file** (for `cli refresh --import-extension-file <path>`).
2. Either path pushes each record through the same identity-matching → condition
   → FX → `persist_snapshot` pipeline (`src/pipeline/extension_import.py`), no
   trust shortcut. Records whose URL isn't attributable to a tracked product are
   skipped.

## Field mapping (matches the Python side's expectations)

The snapshot keys mirror `src/models/listing.py`'s `RawListing`:

- `title` → `RawListing.title`
- `price_text` (display string, e.g. `"299,00 €"`) → `RawListing.price_text`
- `currency_hint` (`"EUR"`, etc.) → `RawListing.currency_hint`
- `site_key` / `site_display_name` (hostname-derived), `url`, `observed_at` → context
