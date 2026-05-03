class RecentJobsDialog extends HTMLElement {
  connectedCallback() {
    if (this.dataset.hydrated === "1") {
      return;
    }
    this.dataset.hydrated = "1";
    this.innerHTML = `
      <dialog id="query-dialog" class="desktop-dialog recent-jobs-dialog">
        <form method="dialog" class="desktop-shell recent-jobs-dialog-shell">
          <div class="recent-jobs-sidebar-head">
            <div class="recent-jobs-head">
              <h2>Recent Jobs</h2>
              <p>Sorted by most recent update. Click to switch to that job.</p>
            </div>
            <button id="query-dialog-close-btn" type="submit" class="dialog-close-btn" aria-label="Close">×</button>
          </div>
          <div class="recent-jobs-sidebar-body advanced-content">
            <div class="recent-jobs-toolbar">
              <input id="recent-jobs-date" type="date" aria-label="Select date" />
              <button id="refresh-jobs-btn" class="secondary" type="button">Refresh List</button>
            </div>
            <div id="recent-jobs-summary" class="status-panel-note">Stage Spec 0 · Legacy CLI 0 · Unknown 0</div>
            <div id="recent-jobs-empty" class="events-empty hidden">No recent jobs</div>
            <div id="recent-jobs-list" class="recent-jobs-list hidden"></div>
            <div class="recent-jobs-more-row">
              <button id="load-more-jobs-btn" class="secondary hidden" type="button">More</button>
            </div>

            <div class="top-gap">
              <div class="label">Hints / Errors</div>
              <pre id="error-box" class="log error-box">-</pre>
            </div>

            <div class="top-gap">
              <div class="label">Failure Diagnosis</div>
              <pre id="diagnostic-box" class="log">-</pre>
            </div>
          </div>
        </form>
      </dialog>
    `;
  }

  summaryElement() {
    return this.querySelector("#recent-jobs-summary");
  }

  listElement() {
    return this.querySelector("#recent-jobs-list");
  }

  emptyElement() {
    return this.querySelector("#recent-jobs-empty");
  }

  loadMoreButton() {
    return this.querySelector("#load-more-jobs-btn");
  }

  renderSummary(text) {
    const summary = this.summaryElement();
    if (summary) {
      summary.textContent = text;
    }
  }

  renderLoading() {
    const list = this.listElement();
    const empty = this.emptyElement();
    const loadMoreButton = this.loadMoreButton();
    if (!list || !empty || !loadMoreButton) {
      return;
    }
    empty.classList.add("hidden");
    list.classList.remove("hidden");
    list.innerHTML = '<div class="events-empty">Loading recent jobs...</div>';
    loadMoreButton.classList.add("hidden");
  }

  renderEmpty(message) {
    const list = this.listElement();
    const empty = this.emptyElement();
    const loadMoreButton = this.loadMoreButton();
    if (!list || !empty || !loadMoreButton) {
      return;
    }
    list.innerHTML = "";
    list.classList.add("hidden");
    empty.textContent = message || "No recent jobs";
    empty.classList.remove("hidden");
    loadMoreButton.classList.add("hidden");
    loadMoreButton.disabled = false;
    loadMoreButton.textContent = "More";
  }

  renderError(message, { reset = false } = {}) {
    const list = this.listElement();
    const empty = this.emptyElement();
    const loadMoreButton = this.loadMoreButton();
    if (!list || !empty || !loadMoreButton) {
      return;
    }
    if (reset) {
      list.innerHTML = "";
      list.classList.add("hidden");
      empty.textContent = message || "Failed to load recent jobs";
      empty.classList.remove("hidden");
    } else {
      loadMoreButton.classList.add("hidden");
    }
    loadMoreButton.disabled = false;
    loadMoreButton.textContent = "More";
  }

  renderList(markup, { reset = false, hasMore = false, onSelect } = {}) {
    const list = this.listElement();
    const empty = this.emptyElement();
    const loadMoreButton = this.loadMoreButton();
    if (!list || !empty || !loadMoreButton) {
      return;
    }
    list.classList.remove("hidden");
    empty.classList.add("hidden");
    list.innerHTML = reset ? markup : `${list.innerHTML}${markup}`;
    loadMoreButton.classList.toggle("hidden", !hasMore);
    loadMoreButton.disabled = false;
    loadMoreButton.textContent = "More";
    list.querySelectorAll(".recent-job-item").forEach((button) => {
      button.addEventListener("click", () => {
        onSelect?.(button.dataset.jobId || "");
      });
    });
  }

  setLoadMoreLoading() {
    const loadMoreButton = this.loadMoreButton();
    if (!loadMoreButton) {
      return;
    }
    loadMoreButton.disabled = true;
    loadMoreButton.textContent = "Loading...";
  }
}

if (!customElements.get("recent-jobs-dialog")) {
  customElements.define("recent-jobs-dialog", RecentJobsDialog);
}
