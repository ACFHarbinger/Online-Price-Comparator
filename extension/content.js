/**
 * OPC Client-Side Monitor — content script (v2.20, PT/ES tier).
 *
 * Runs on listing pages of every PT/ES site in `manifest.json` (see that file
 * for the exact URL patterns). On a listing page it reads the schema.org
 * `Product`/`Offer` JSON-LD rendered in the DOM - the same structured-data-first
 * preference the Python scrapers use (`src/scrapers/`) - derives the site from
 * `window.location.hostname`, keeps a per-URL local snapshot, and records a
 * change only when the price/title actually moved. The detected change goes to
 * `opc_changes`, which the popup sends to OPC's localhost endpoint or exports as
 * JSON-lines.
 *
 * Per-site CSS-selector fallback (for a site whose listing page lacks complete
 * JSON-LD) is a small per-site config in `site_fallbacks.js`, consulted only
 * when no Product JSON-LD is found. Field names mirror what the Python side
 * expects from a RawListing: `title`, `price_text` (display string),
 * `currency_hint` (ISO 4217).
 */
"use strict";

const LAST_KEY_PREFIX = "opc_last:"; // per-URL last snapshot
const STORAGE_KEY = "opc_snapshots"; // full snapshot history (viewing/audit)
const CHANGES_KEY = "opc_changes"; // accumulated detected changes (for export)

// hostname (suffix-matched) -> site_key/site_display_name. Matched by exact
// hostname or any subdomain, with the leading "www." stripped.
const SITES = {
  "amazon.es": { site_key: "amazon.es", site_display_name: "Amazon.es" },
  "pccomponentes.pt": { site_key: "pccomponentes", site_display_name: "PcComponentes" },
  "pccomponentes.com": { site_key: "pccomponentes", site_display_name: "PcComponentes" },
  "pcdiga.com": { site_key: "pcdiga", site_display_name: "PCDIGA" },
  "worten.pt": { site_key: "worten", site_display_name: "Worten" },
  "fnac.pt": { site_key: "fnac", site_display_name: "Fnac" },
  "chip7.pt": { site_key: "chip7", site_display_name: "Chip7" },
  "wallapop.com": { site_key: "wallapop", site_display_name: "Wallapop" },
  "leboncoin.fr": { site_key: "leboncoin", site_display_name: "Leboncoin" },
};

/** Resolve the site metadata for a page hostname (www. stripped). */
function deriveSite(hostname) {
  const host = hostname.replace(/^www\./, "").toLowerCase();
  for (const domain of Object.keys(SITES)) {
    if (host === domain || host.endsWith("." + domain)) return SITES[domain];
  }
  return { site_key: host, site_display_name: hostname };
}

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

/** Extract a normalized snapshot from Product JSON-LD, or null. */
function extractSnapshot(product, pageUrl, site) {
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
    site_key: site.site_key,
    site_display_name: site.site_display_name,
    observed_at: new Date().toISOString(),
  };
}

/** CSS fallback via `site_fallbacks.js` (OPC_SITE_FALLBACKS) when JSON-LD is absent. */
function snapshotFromFallback(site, pageUrl) {
  const fallbacks = window.OPC_SITE_FALLBACKS || {};
  const config = fallbacks[site.site_key] || fallbacks[window.location.hostname];
  if (!config) return null;
  const titleEl = config.title ? document.querySelector(config.title) : null;
  const priceEl = config.price ? document.querySelector(config.price) : null;
  const title = titleEl ? titleEl.textContent.trim() : null;
  const priceText = priceEl ? priceEl.textContent.trim() : null;
  if (!title || !priceText) return null;
  return {
    url: pageUrl,
    title,
    price_text: priceText,
    currency_hint: config.currency_hint || null,
    site_key: site.site_key,
    site_display_name: site.site_display_name,
    observed_at: new Date().toISOString(),
  };
}

/** Extract just the diff-relevant bits (price + title) from a snapshot. */
function fingerprint(snapshot) {
  return `${snapshot.title}@${snapshot.price_text}`;
}

function pushSnapshot(snapshot) {
  chrome.storage.local.get([STORAGE_KEY]).then((data) => {
    const snapshots = Array.isArray(data[STORAGE_KEY]) ? data[STORAGE_KEY] : [];
    snapshots.push(snapshot);
    const capped = snapshots.length > 500 ? snapshots.slice(-500) : snapshots;
    chrome.storage.local.set({ [STORAGE_KEY]: capped });
  });
}

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
  const site = deriveSite(window.location.hostname);

  let product = null;
  for (const block of readJsonLdBlocks()) {
    product = findProduct(block);
    if (product) break;
  }

  const snapshot =
    (product ? extractSnapshot(product, pageUrl, site) : null) ||
    snapshotFromFallback(site, pageUrl);

  if (!snapshot) {
    console.info(
      `[OPC] No Product data found on ${site.site_display_name} page:`,
      pageUrl
    );
    return;
  }

  pushSnapshot(snapshot);
  const lastKey = LAST_KEY_PREFIX + pageUrl;
  chrome.storage.local.get([lastKey]).then((data) => {
    const last = data[lastKey];
    const reason = !last ? "first snapshot" : "change detected";
    if (!last || fingerprint(last) !== fingerprint(snapshot)) {
      pushChange(snapshot);
      console.log(`[OPC] ${site.site_display_name} ${reason}:`, snapshot);
    } else {
      console.log(`[OPC] ${site.site_display_name} snapshot unchanged:`, snapshot.price_text);
    }
    chrome.storage.local.set({ [lastKey]: snapshot });
  });
}

main();
