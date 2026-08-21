/**
 * OPC Client-Side Monitor — Leboncoin content script (v2.20, v0).
 *
 * Runs only on `https://www.leboncoin.fr/ad/*` (see manifest.json). On an ad
 * page it reads the schema.org `Product`/`Offer` JSON-LD already rendered in
 * the DOM - the same structured-data-first preference the Python scrapers use
 * (`src/scrapers/`) - and maintains a per-URL local snapshot in
 * `chrome.storage.local`. It records a change **only when the price (or title)
 * actually moved** vs the last snapshot; that detected change is appended to an
 * `opc_changes` array the popup exports as a JSON-lines file for OPC's
 * `cli refresh --import-extension-file` (see `src/pipeline/extension_import.py`).
 *
 * Field names mirror what the Python side expects from a RawListing: `title`,
 * `price_text` (a display string, e.g. "299,00 €"), `currency_hint` (ISO 4217).
 */
"use strict";

const LAST_KEY_PREFIX = "opc_last:"; // per-URL last snapshot
const STORAGE_KEY = "opc_snapshots"; // full snapshot history (viewing/audit)
const CHANGES_KEY = "opc_changes"; // accumulated detected changes (for export)

/**
 * Walk an arbitrary JSON-LD value (object | array | @graph) and return the
 * first node whose `@type` is "Product" (as string or within an array).
 */
function findProduct(node) {
  if (!node || typeof node !== "object") return null;
  if (Array.isArray(node)) {
    for (const child of node) {
      const found = findProduct(child);
      if (found) return found;
    }
    return null;
  }
  const type = node["@type"];
  const isProduct = type === "Product" || (Array.isArray(type) && type.includes("Product"));
  if (isProduct) return node;
  if (Array.isArray(node["@graph"])) return findProduct(node["@graph"]);
  return null;
}

/** Read + parse every `application/ld+json` script in the page DOM. */
function readJsonLdBlocks() {
  const blocks = [];
  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      blocks.push(JSON.parse(script.textContent));
    } catch (err) {
      console.debug("[OPC] skipped malformed JSON-LD block", err);
    }
  }
  return blocks;
}

/** Extract a normalized snapshot object from Product JSON-LD, or null. */
function extractSnapshot(product, pageUrl) {
  if (!product) return null;
  const title = typeof product.name === "string" ? product.name : null;
  const url = typeof product.url === "string" ? product.url : pageUrl;

  let priceText = null;
  let currencyHint = null;
  const offers = product.offers;
  if (offers) {
    const offer = Array.isArray(offers) ? offers[0] : offers;
    if (offer) {
      const price = offer.price ?? offer.lowPrice ?? offer.highPrice;
      if (price !== null && price !== undefined) priceText = String(price);
      if (typeof offer.priceCurrency === "string") currencyHint = offer.priceCurrency;
    }
  }
  if (!title || !priceText) return null;

  return {
    url,
    title,
    price_text: priceText,
    currency_hint: currencyHint,
    site_key: "leboncoin",
    site_display_name: "Leboncoin",
    observed_at: new Date().toISOString(),
  };
}

/** Extract just the diff-relevant bits (price + title) from a snapshot. */
function fingerprint(snapshot) {
  return `${snapshot.title}@${snapshot.price_text}`;
}

/** Store the snapshot history (capped) in chrome.storage.local. */
function pushSnapshot(snapshot) {
  chrome.storage.local.get([STORAGE_KEY]).then((data) => {
    const snapshots = Array.isArray(data[STORAGE_KEY]) ? data[STORAGE_KEY] : [];
    snapshots.push(snapshot);
    const capped = snapshots.length > 500 ? snapshots.slice(-500) : snapshots;
    chrome.storage.local.set({ [STORAGE_KEY]: capped });
  });
}

/** Record a detected change (used by the export popup). */
function pushChange(snapshot) {
  chrome.storage.local.get([CHANGES_KEY]).then((data) => {
    const changes = Array.isArray(data[CHANGES_KEY]) ? data[CHANGES_KEY] : [];
    changes.push(snapshot);
    const capped = changes.length > 1000 ? changes.slice(-1000) : changes;
    chrome.storage.local.set({ [CHANGES_KEY]: capped });
  });
}

function main() {
  const pageUrl = window.location.href;
  let product = null;
  for (const block of readJsonLdBlocks()) {
    product = findProduct(block);
    if (product) break;
  }

  const snapshot = product ? extractSnapshot(product, pageUrl) : null;
  if (!snapshot) {
    console.info("[OPC] No Product JSON-LD found on this Leboncoin page:", pageUrl);
    return;
  }

  pushSnapshot(snapshot);
  const lastKey = LAST_KEY_PREFIX + pageUrl;
  chrome.storage.local.get([lastKey]).then((data) => {
    const last = data[lastKey];
    if (!last || fingerprint(last) !== fingerprint(snapshot)) {
      const reason = last ? "change detected" : "first snapshot";
      pushChange(snapshot);
      console.log(`[OPC] Leboncoin ${reason}:`, snapshot);
    } else {
      console.log("[OPC] Leboncoin snapshot unchanged:", snapshot.price_text);
    }
    chrome.storage.local.set({ [lastKey]: snapshot });
  });
}

main();
