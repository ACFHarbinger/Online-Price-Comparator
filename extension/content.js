/**
 * OPC Client-Side Monitor — Leboncoin content script (v2.20, first slice).
 *
 * Runs only on `https://www.leboncoin.fr/ad/*` (see manifest.json). On an ad
 * page it reads the schema.org `Product`/`Offer` JSON-LD already rendered in
 * the DOM - the same structured-data-first preference the Python scrapers use
 * (`src/scrapers/`) - and stores a timestamped snapshot in
 * `chrome.storage.local`. That is the whole scope of this slice: prove "we can
 * read Leboncoin's DOM from an extension," nothing more. No diffing, no OPC
 * integration yet (see docs/moon/roadmaps/client_side_monitor.md for the plan).
 *
 * Field names mirror what the Python side already expects from a RawListing:
 * `title`, `price` (as a display string, e.g. "299.00" or "299,00 €"), and
 * `currency_hint` (an ISO 4217 code such as "EUR").
 */
"use strict";

// Storage key for the accumulated snapshots (an array, newest appended).
const STORAGE_KEY = "opc_snapshots";

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
  const typeOfProduct =
    type === "Product" || (Array.isArray(type) && type.includes("Product"));
  if (typeOfProduct) return node;
  if (Array.isArray(node["@graph"])) return findProduct(node["@graph"]);
  return null;
}

/** Read + parse every `application/ld+json` script in the page DOM. */
function readJsonLdBlocks() {
  const blocks = [];
  for (const script of document.querySelectorAll(
    'script[type="application/ld+json"]'
  )) {
    try {
      blocks.push(JSON.parse(script.textContent));
    } catch (err) {
      // A malformed JSON-LD block shouldn't abort the whole read.
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
    // `offers` can be a single Offer or an array of Offers; take the first.
    const offer = Array.isArray(offers) ? offers[0] : offers;
    if (offer) {
      const price = offer.price ?? offer.lowPrice ?? offer.highPrice;
      if (price !== null && price !== undefined) {
        priceText = String(price);
      }
      if (typeof offer.priceCurrency === "string") {
        currencyHint = offer.priceCurrency;
      }
    }
  }

  if (!title || !priceText) return null;

  return {
    url,
    title,
    price: priceText,
    currency_hint: currencyHint,
    observed_at: new Date().toISOString(),
  };
}

/** Append a snapshot to `chrome.storage.local` (oldest first, capped to 200). */
function storeSnapshot(snapshot) {
  chrome.storage.local.get([STORAGE_KEY]).then((data) => {
    const snapshots = Array.isArray(data[STORAGE_KEY]) ? data[STORAGE_KEY] : [];
    snapshots.push(snapshot);
    const capped = snapshots.length > 200 ? snapshots.slice(-200) : snapshots;
    chrome.storage.local.set({ [STORAGE_KEY]: capped });
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
  if (snapshot) {
    storeSnapshot(snapshot);
    // The console confirmation the README points the tester at:
    console.log("[OPC] Leboncoin snapshot captured:", snapshot);
  } else {
    console.info(
      "[OPC] No Product JSON-LD found on this Leboncoin page:",
      pageUrl
    );
  }
}

main();
