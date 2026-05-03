class PageRangeDialog extends HTMLElement {
  connectedCallback() {
    if (this.dataset.hydrated === "1") {
      return;
    }
    this.dataset.hydrated = "1";
    this.innerHTML = `
      <dialog id="page-range-dialog" class="desktop-dialog page-range-dialog">
        <form method="dialog" class="desktop-shell">
          <div class="desktop-head">
            <h2 id="page-range-title">Page Range Translation</h2>
            <button id="page-range-close-btn" type="submit" class="dialog-close-btn" aria-label="Close">×</button>
          </div>
          <div class="desktop-body">
            <p id="page-range-limit-text" class="muted">Limit this translation by page range. Pages start from 1.</p>
            <div class="grid two">
              <label>
                <span>Start Page</span>
                <input id="page-range-start" type="number" min="1" step="1" inputmode="numeric" autocomplete="off" placeholder="e.g. 1" />
              </label>
              <label>
                <span>End Page</span>
                <input id="page-range-end" type="number" min="1" step="1" inputmode="numeric" autocomplete="off" placeholder="e.g. 15" />
              </label>
            </div>
            <div class="actions">
              <button id="page-range-clear-btn" type="button" class="secondary">Clear</button>
              <button id="page-range-apply-btn" type="button">Apply</button>
            </div>
          </div>
        </form>
      </dialog>
    `;
  }
}

if (!customElements.get("page-range-dialog")) {
  customElements.define("page-range-dialog", PageRangeDialog);
}
