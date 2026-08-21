# OPC Client-Side Monitor — Leboncoin (v2.20, first slice)

A from-scratch **Manifest V3** browser extension skeleton. It is deliberately
tiny: on a Leboncoin ad page it reads the schema.org `Product`/`Offer` JSON-LD
that is already rendered in the page and stores a timestamped snapshot in
`chrome.storage.local`. That is the whole point of this slice — prove "we can
read Leboncoin's DOM from an extension."

**There is no OPC integration here yet**: no local snapshot-diff / change
detection, no JSON-lines handoff file, no `cli refresh` import flag. Those are
the rest of `docs/moon/roadmaps/client_side_monitor.md`'s v0 scope and come
later.

## What's here

- `manifest.json` — Manifest V3. Permissions are minimal (`storage` only) and
  the host permission / content-script match is scoped to
  `https://www.leboncoin.fr/ad/*`. Nothing broader.
- `content.js` — reads the `Product`/`Offer` JSON-LD, extracts `title`, `price`
  (display string), and `priceCurrency` into a snapshot, and appends it to
  `chrome.storage.local` under the key `opc_snapshots`.

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
[OPC] Leboncoin snapshot captured: {...}
```

(`...` being the `{ url, title, price, currency_hint, observed_at }` object the
script read from the page), or, if the page had no `Product` JSON-LD:

```
[OPC] No Product JSON-LD found on this Leboncoin page: <url>
```

To read back the stored snapshots from the console, paste:

```js
chrome.storage.local.get(["opc_snapshots"], (r) => console.log(r.opc_snapshots));
```

To force the content script to re-run on the current page, reload it:

```js
location.reload();
```

## Field mapping (matches the Python side's expectations)

The snapshot's keys mirror what `src/models/listing.py`'s `RawListing` already
carries, so a later handoff-import pass can map straight through:

- `title` → `RawListing.title`
- `price` (display string, e.g. `"299.00"` or `"299,00 €"`) → `RawListing.price_text`
- `currency_hint` (`"EUR"`, etc.) → `RawListing.currency_hint`
- `url`, `observed_at` → recording context
