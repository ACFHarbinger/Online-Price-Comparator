/**
 * OPC Leboncoin monitor — popup handler.
 *
 * Reads the accumulated detected changes (`opc_changes`, written by content.js)
 * and downloads them as a JSON-lines file via the downloads API. The user then
 * runs `cli refresh --import-extension-file <downloaded path>` to push the
 * observations through the normal identity-matching → condition → FX →
 * persist_snapshot pipeline. After export the change queue is cleared.
 */
"use strict";

const CHANGES_KEY = "opc_changes";

function exportChanges() {
  const status = document.getElementById("status");
  chrome.storage.local.get([CHANGES_KEY]).then((data) => {
    const changes = Array.isArray(data[CHANGES_KEY]) ? data[CHANGES_KEY] : [];
    if (changes.length === 0) {
      status.textContent = "No detected changes to export.";
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
          status.textContent = `Export failed: ${chrome.runtime.lastError.message}`;
          return;
        }
        status.textContent = `Exported ${changes.length} change(s).`;
        chrome.storage.local.set({ [CHANGES_KEY]: [] });
      }
    );
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("export").addEventListener("click", exportChanges);
});
