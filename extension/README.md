# OPC Client-Side Monitor — Leboncoin (v2.20, v0)

A from-scratch **Manifest V3** browser extension. On a Leboncoin ad page it reads
the schema.org `Product`/`Offer` JSON-LD already rendered in the page, keeps a
per-URL local snapshot, and records a change **only when the price/title moved**.
The popup exports the accumulated detected changes as a JSON-lines file, which
OPC consumes via `cli refresh --import-extension-file <path>`. No live HTTP
callback yet (that's v1, see `docs/moon/roadmaps/client_side_monitor.md`).

## What's here

- `manifest.json` — Manifest V3. Permissions are minimal (`storage`, `downloads`)
  and the host permission / content-script match is scoped to
  `https://www.leboncoin.fr/ad/*`. Nothing broader.
- `content.js` — reads the `Product`/`Offer` JSON-LD, extracts `title`,
  `price_text`, and `priceCurrency` into a snapshot; records a change only when
  it differs from the last snapshot for that URL (stored under
  `opc_last:<url>`); appends detected changes to `opc_changes`.
- `popup.js` / `popup.html` — the browser-action popup that serializes
  `opc_changes` to JSON-lines and downloads it as
  `opc-leboncoin-export-<timestamp>.jsonl`.

## Load it unpacked (manual test)

1. Open Chrome and go to `chrome://extensions`.
2. Toggle **Developer mode** (top right).
3. Click **Load unpacked** and select this `extension/` directory.
4. Open a real Leboncoin ad page — the URL must match
   `https://www.leboncoin.fr/ad/*`.

## Confirm the content script ran and read something

Open the browser dev-tools **console** (F12) on the Leboncoin ad page. You
should see either:

```
[OPC] Leboncoin change detected: {...}
```

(a fresh/changed snapshot) or the first-snapshot log with a "first snapshot"
reason, or, if the price was unchanged since the last visit:

```
[OPC] Leboncoin snapshot unchanged: 299,00
```

To read back the stored detected changes from the console, paste:

```js
chrome.storage.local.get(["opc_changes"], (r) => console.log(r.opc_changes));
```

To force the content script to re-run on the current page, reload it:

```js
location.reload();
```

## Export + import into OPC

1. Click the extension's toolbar action (the popup) and press **Export detected
   changes** — Chrome downloads an `opc-leboncoin-export-<ts>.jsonl` file.
2. Run `cli refresh --import-extension-file <path-to-downloaded-file>`.

The import pushes each record through the same identity-matching → condition →
FX → `persist_snapshot` pipeline every other source uses (see
`src/pipeline/extension_import.py`). Records whose URL is not attributable to a
tracked product are skipped.

## Field mapping (matches the Python side's expectations)

The snapshot keys mirror what `src/models/listing.py`'s `RawListing` already
carries, so a handoff-import pass can map straight through:

- `title` → `RawListing.title`
- `price_text` (display string, e.g. `"299,00 €"`) → `RawListing.price_text`
- `currency_hint` (`"EUR"`, etc.) → `RawListing.currency_hint`
- `site_key`/`site_display_name`, `url`, `observed_at` → recording context
