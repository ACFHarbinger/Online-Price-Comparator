/**
 * OPC Leboncoin monitor — popup handler (v2.20 v1).
 *
 * Sends accumulated detected changes (`opc_changes`, written by content.js) to
 * OPC's localhost endpoint (`/api/extension/import`), or downloads them as a
 * JSON-lines file for `cli refresh --import-extension-file`. Either way each
 * record goes through the normal identity-matching -> condition -> FX ->
 * persist_snapshot pipeline; there is no trust shortcut. After a successful
 * send/export the change queue is cleared.
 */
"use strict";

const CHANGES_KEY = "opc_changes";
const DEFAULT_ENDPOINT = "http://127.0.0.1:8050/api/extension/import";

function getChanges() {
  return chrome.storage.local.get([CHANGES_KEY]).then((data) => {
    return Array.isArray(data[CHANGES_KEY]) ? data[CHANGES_KEY] : [];
  });
}

function clearChanges() {
  return chrome.storage.local.set({ [CHANGES_KEY]: [] });
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

function postChanges() {
  const endpointInput = document.getElementById("endpoint");
  const endpoint = (endpointInput && endpointInput.value.trim()) || DEFAULT_ENDPOINT;
  getChanges().then((changes) => {
    if (changes.length === 0) {
      setStatus("No detected changes to send.");
      return;
    }
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ records: changes }),
    })
      .then((response) => {
        if (!response.ok) {
          setStatus(`OPC returned HTTP ${response.status}.`);
          return;
        }
        return response.json();
      })
      .then((result) => {
        const n = result && typeof result.imported === "number" ? result.imported : changes.length;
        setStatus(`Sent ${n} change(s) to OPC.`);
        return clearChanges();
      })
      .catch((err) => {
        setStatus(`Send failed: ${err.message}`);
      });
  });
}

function exportChanges() {
  getChanges().then((changes) => {
    if (changes.length === 0) {
      setStatus("No detected changes to export.");
      return;
    }
    const jsonl = changes.map((record) => JSON.stringify(record)).join("\n");
    const blob = new Blob([jsonl], { type: "application/x-ndjson" });
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    chrome.downloads.download(
      { url, filename: `opc-leboncoin-export-${stamp}.jsonl`, saveAs: true },
      (downloadId) => {
        URL.revokeObjectURL(url);
        if (chrome.runtime.lastError) {
          setStatus(`Export failed: ${chrome.runtime.lastError.message}`);
          return;
        }
        setStatus(`Exported ${changes.length} change(s).`);
        clearChanges();
      }
    );
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("post").addEventListener("click", postChanges);
  document.getElementById("export").addEventListener("click", exportChanges);
});
