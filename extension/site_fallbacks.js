/**
 * OPC Client-Side Monitor — per-site CSS fallback config (v2.20 PT/ES tier).
 *
 * Consulted by `content.js` only when no schema.org `Product`/`Offer` JSON-LD
 * is found on a listing page. Mirrors the *shape* of the Python side's split
 * (`scrapers/retailer_base.py`: shared plumbing + per-site fallback parsing) -
 * not the code, since this is a different language.
 *
 * IMPORTANT: selectors here are STRICTLY to be filled in after verifying each
 * site's real listing page DOM by hand. Leaving a site absent from this map is
 * the honest state - the content script will report "no Product data found"
 * rather than guess. Do not populate a site you have not verified against a
 * live page. This tier's seven sites (Amazon.es, PcComponentes, PCDIGA, Worten,
 * Fnac.pt, Chip7, Wallapop.es) are all structured-data-first in the Python
 * scrapers, so JSON-LD should cover most; only add a site here if its page
 * actually lacks complete JSON-LD.
 *
 * Each entry: { title: <selector>, price: <selector>, currency_hint?: "EUR" }.
 */
"use strict";

window.OPC_SITE_FALLBACKS = {
  // TODO(OPC v2.20 PT/ES): fill per-site selectors here after verifying a real
  // listing page for any site whose listing page lacks complete Product JSON-LD.
  // e.g. "chip7.pt": { title: "h1", price: ".price", currency_hint: "EUR" }
};
