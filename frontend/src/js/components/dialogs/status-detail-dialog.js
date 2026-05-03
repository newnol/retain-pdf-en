class StatusDetailDialog extends HTMLElement {
  connectedCallback() {
    if (this.dataset.hydrated === "1") {
      return;
    }
    this.dataset.hydrated = "1";
    this.innerHTML = `
      <dialog id="status-detail-dialog" class="desktop-dialog status-detail-dialog">
        <form method="dialog" class="desktop-shell">
          <div class="desktop-head">
            <div class="status-detail-headline">
              <span id="status-detail-head-icon" class="status-detail-head-icon" aria-hidden="true"></span>
              <div class="status-detail-head-copy">
                <div class="status-detail-head-top">
                  <h2>Job Details</h2>
                  <p class="status-detail-job-meta">Job ID <span id="status-detail-job-id" class="status-detail-job-id mono">-</span></p>
                </div>
                <p id="status-detail-head-note" class="status-panel-note">View task overview, failure reasons, and event stream</p>
              </div>
            </div>
            <button id="status-detail-close-btn" type="submit" class="dialog-close-btn" aria-label="Close">×</button>
          </div>
          <div class="desktop-body status-detail-body">
            <div class="detail-tabs" role="tablist" aria-label="Job Details">
              <button id="detail-tab-overview" type="button" class="detail-tab is-active" data-tab="overview" role="tab" aria-selected="true">Overview</button>
              <button id="detail-tab-failure" type="button" class="detail-tab" data-tab="failure" role="tab" aria-selected="false">Failure</button>
              <button id="detail-tab-events" type="button" class="detail-tab" data-tab="events" role="tab" aria-selected="false">Events</button>
              <button id="detail-tab-translation" type="button" class="detail-tab" data-tab="translation" role="tab" aria-selected="false">Translation Debug</button>
            </div>

            <div class="detail-tab-panels">
              <section id="detail-panel-overview" class="detail-tab-panel is-active" data-panel="overview" role="tabpanel">
                <div class="detail-download-row">
                  <a id="markdown-bundle-btn" class="button-link secondary disabled" href="#" target="_blank" rel="noopener noreferrer">Download Markdown ZIP</a>
                </div>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="label">Current Stage</span>
                    <span id="runtime-current-stage" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Stage Elapsed</span>
                    <span id="runtime-stage-elapsed" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Total Elapsed</span>
                    <span id="runtime-total-elapsed" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Retry Count</span>
                    <span id="runtime-retry-count" class="info-value">0</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Last Transition</span>
                    <span id="runtime-last-transition" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Terminal Reason</span>
                    <span id="runtime-terminal-reason" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Input Protocol</span>
                    <span id="runtime-input-protocol" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Stage Schema</span>
                    <span id="runtime-stage-spec-version" class="info-value">-</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">Math Mode</span>
                    <span id="runtime-math-mode" class="info-value">-</span>
                  </div>
                </div>
                <div class="status-panel detail-stage-panel">
                  <div class="status-panel-head">
                    <h3>Stage Timeline</h3>
                  </div>
                  <div id="overview-stage-empty" class="events-empty">No stage records</div>
                  <div id="overview-stage-list" class="stage-history-list hidden"></div>
                </div>
              </section>

              <section id="detail-panel-failure" class="detail-tab-panel" data-panel="failure" role="tabpanel" hidden>
                <div class="status-panel">
                  <div class="status-panel-head">
                    <h3>Failure Diagnosis</h3>
                    <span class="status-panel-note">Structured failure summary and troubleshooting suggestions</span>
                  </div>
                  <div class="failure-hero-card">
                    <span class="label">Failure Summary</span>
                    <span id="failure-summary" class="info-value">-</span>
                  </div>
                  <div class="info-list detail-info-list">
                    <div class="info-row">
                      <span class="label">Category</span>
                      <span id="failure-category" class="info-value">-</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Stage</span>
                      <span id="failure-stage" class="info-value">-</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Root Cause</span>
                      <span id="failure-root-cause" class="info-value">-</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Suggestion</span>
                      <span id="failure-suggestion" class="info-value">-</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Last Log</span>
                      <span id="failure-last-log-line" class="info-value">-</span>
                    </div>
                    <div class="info-row">
                      <span class="label">Retryable</span>
                      <span id="failure-retryable" class="info-value">-</span>
                    </div>
                  </div>
                </div>
              </section>

              <section id="detail-panel-events" class="detail-tab-panel" data-panel="events" role="tabpanel" hidden>
                <div class="status-panel">
                  <div class="status-panel-head">
                    <h3>Event Stream</h3>
                    <span id="events-status" class="status-panel-note">All Events</span>
                  </div>
                  <p class="events-lead">Shows recent events in reverse chronological order. Useful for identifying which stage a task is stuck at and what happened before the last failure.</p>
                  <div id="events-empty" class="events-empty">No events</div>
                  <div id="events-list" class="events-list hidden"></div>
                </div>
              </section>

              <section id="detail-panel-translation" class="detail-tab-panel" data-panel="translation" role="tabpanel" hidden>
                <div class="status-panel translation-debug-panel">
                  <div class="status-panel-head">
                    <h3>Translation Debug</h3>
                    <span id="translation-debug-status" class="status-panel-note">Debug per-item why translation was skipped or original text was kept</span>
                  </div>
                  <div id="translation-debug-empty" class="events-empty hidden">No translation debug data</div>
                  <div id="translation-debug-content" class="translation-debug-content">
                    <section class="translation-summary-shell">
                      <div class="translation-summary-grid">
                        <div class="translation-summary-card">
                          <span class="label">Translated</span>
                          <span id="translation-count-translated" class="info-value">-</span>
                        </div>
                        <div class="translation-summary-card">
                          <span class="label">Kept Original</span>
                          <span id="translation-count-kept-origin" class="info-value">-</span>
                        </div>
                        <div class="translation-summary-card">
                          <span class="label">Skipped</span>
                          <span id="translation-count-skipped" class="info-value">-</span>
                        </div>
                        <div class="translation-summary-card">
                          <span class="label">Provider</span>
                          <span id="translation-provider-family" class="info-value">-</span>
                        </div>
                      </div>
                      <div class="translation-summary-notes">
                        <span id="translation-summary-scope" class="status-panel-note">Summary scope: -</span>
                        <span id="translation-list-filter" class="status-panel-note">Current list filter: -</span>
                      </div>
                    </section>

                    <section class="translation-filter-panel">
                      <div class="translation-filter-row">
                        <label class="translation-filter-field">
                          <span class="label">Status</span>
                          <select id="translation-filter-final-status">
                            <option value="kept_origin" selected>Kept Original</option>
                            <option value="translated">Translated</option>
                            <option value="skipped">Skipped</option>
                            <option value="">All</option>
                          </select>
                        </label>
                        <label class="translation-filter-field translation-filter-search">
                          <span class="label">Search</span>
                          <input id="translation-filter-query" type="search" placeholder="Enter item_id, route, or source text snippet" />
                        </label>
                        <button id="translation-filter-apply" type="button" class="button-link secondary">Refresh</button>
                      </div>
                    </section>

                    <div class="translation-debug-layout">
                      <section class="translation-debug-column translation-debug-column-list">
                        <div class="translation-debug-subhead">
                          <h4>Item List</h4>
                          <span id="translation-items-meta" class="status-panel-note">-</span>
                        </div>
                        <div class="translation-panel-body">
                          <div id="translation-items-loading" class="events-empty hidden">Reading translation items...</div>
                          <div id="translation-items-empty" class="events-empty hidden">No matching translation items</div>
                          <div id="translation-items-list" class="translation-items-list"></div>
                        </div>
                        <div class="translation-items-pagination">
                          <button id="translation-items-prev" type="button" class="button-link secondary" disabled>Previous</button>
                          <span id="translation-items-page" class="status-panel-note">-</span>
                          <button id="translation-items-next" type="button" class="button-link secondary" disabled>Next</button>
                        </div>
                      </section>

                      <section class="translation-debug-column translation-debug-column-detail">
                        <div class="translation-debug-subhead">
                          <h4>Item Details</h4>
                          <span id="translation-item-meta" class="status-panel-note">-</span>
                        </div>
                        <div class="translation-panel-body translation-panel-body-detail">
                          <div id="translation-item-loading" class="events-empty hidden">Reading item details...</div>
                          <div id="translation-item-empty" class="events-empty">Please select an item from the left</div>
                          <div id="translation-item-detail" class="translation-item-detail hidden"></div>
                        </div>
                        <div class="translation-replay-actions">
                          <button id="translation-item-replay" type="button" class="button-link secondary" disabled>Replay Current Item</button>
                          <span id="translation-replay-status" class="status-panel-note">-</span>
                        </div>
                        <div id="translation-replay-result" class="translation-replay-result hidden"></div>
                      </section>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </form>
      </dialog>
    `;
  }

  dialogElement() {
    return this.querySelector("#status-detail-dialog");
  }

  activateTab(name = "overview") {
    const tabs = this.querySelectorAll(".detail-tab");
    const panels = this.querySelectorAll(".detail-tab-panel");
    tabs.forEach((tab) => {
      const active = tab.dataset.tab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach((panel) => {
      const active = panel.dataset.panel === name;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });
  }

  open(tabName = "overview") {
    this.activateTab(tabName);
    this.dialogElement()?.showModal();
  }

  close() {
    this.dialogElement()?.close();
  }

  setHeadline({ iconMarkup = "", jobId = "-", note = "View task overview, failure reasons, and event stream" } = {}) {
    const icon = this.querySelector("#status-detail-head-icon");
    const jobIdEl = this.querySelector("#status-detail-job-id");
    const noteEl = this.querySelector("#status-detail-head-note");
    if (icon) {
      icon.innerHTML = iconMarkup;
    }
    if (jobIdEl) {
      jobIdEl.textContent = jobId;
    }
    if (noteEl) {
      noteEl.textContent = note;
    }
  }

  renderStageHistory({ markup = "", emptyText = "No stage records", hasItems = false } = {}) {
    const list = this.querySelector("#overview-stage-list");
    const empty = this.querySelector("#overview-stage-empty");
    if (!list || !empty) {
      return;
    }
    if (!hasItems) {
      list.innerHTML = "";
      list.classList.add("hidden");
      empty.textContent = emptyText;
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    list.classList.remove("hidden");
    list.innerHTML = markup;
  }

  renderEvents({ markup = "", count = 0, emptyText = "No events", hasItems = false } = {}) {
    const list = this.querySelector("#events-list");
    const empty = this.querySelector("#events-empty");
    const status = this.querySelector("#events-status");
    if (!list || !empty || !status) {
      return;
    }
    status.textContent = hasItems ? `Latest ${count} items` : "No events";
    if (!hasItems) {
      list.innerHTML = "";
      list.classList.add("hidden");
      empty.textContent = emptyText;
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    list.classList.remove("hidden");
    list.innerHTML = markup;
  }

  setRuntimeDetails(details = {}) {
    const entries = [
      ["runtime-current-stage", details.currentStage],
      ["runtime-stage-elapsed", details.stageElapsed],
      ["runtime-total-elapsed", details.totalElapsed],
      ["runtime-retry-count", details.retryCount],
      ["runtime-last-transition", details.lastTransition],
      ["runtime-terminal-reason", details.terminalReason],
      ["runtime-input-protocol", details.inputProtocol],
      ["runtime-stage-spec-version", details.stageSpecVersion],
      ["runtime-math-mode", details.mathMode],
    ];
    entries.forEach(([id, value]) => {
      const el = this.querySelector(`#${id}`);
      if (el) {
        el.textContent = value ?? "-";
      }
    });
  }

  setFailureDetails(details = {}) {
    const entries = [
      ["failure-summary", details.summary],
      ["failure-category", details.category],
      ["failure-stage", details.stage],
      ["failure-root-cause", details.rootCause],
      ["failure-suggestion", details.suggestion],
      ["failure-last-log-line", details.lastLogLine],
      ["failure-retryable", details.retryable],
    ];
    entries.forEach(([id, value]) => {
      const el = this.querySelector(`#${id}`);
      if (el) {
        el.textContent = value ?? "-";
      }
    });
  }

  renderSnapshot({
    headline = {},
    runtime = {},
    failure = {},
    stageHistory = {},
    events = {},
  } = {}) {
    this.setHeadline(headline);
    this.setRuntimeDetails(runtime);
    this.setFailureDetails(failure);
    this.renderStageHistory(stageHistory);
    this.renderEvents(events);
  }

  renderTranslationSummary({
    counts = {},
    finalStatusCounts = {},
    providerFamily = "",
    emptyText = "",
    hidden = false,
    summaryScopeText = "-",
    filterText = "-",
  } = {}) {
    const content = this.querySelector("#translation-debug-content");
    const empty = this.querySelector("#translation-debug-empty");
    const status = this.querySelector("#translation-debug-status");
    const scope = this.querySelector("#translation-summary-scope");
    const filter = this.querySelector("#translation-list-filter");
    const normalizedCounts = Object.keys(finalStatusCounts || {}).length ? finalStatusCounts : (counts || {});
    const entries = [
      ["translation-count-translated", normalizedCounts.translated],
      ["translation-count-kept-origin", normalizedCounts.kept_origin],
      ["translation-count-skipped", normalizedCounts.skipped],
      ["translation-provider-family", providerFamily || "-"],
    ];
    entries.forEach(([id, value]) => {
      const el = this.querySelector(`#${id}`);
      if (el) {
        el.textContent = value ?? 0;
      }
    });
    if (status) {
      status.textContent = hidden ? "No translation debug data" : "View kept-original, skipped, and replay results per item";
    }
    if (scope) {
      scope.textContent = `Summary scope: ${summaryScopeText}`;
    }
    if (filter) {
      filter.textContent = `Current list filter: ${filterText}`;
    }
    if (content) {
      content.classList.toggle("hidden", hidden);
    }
    if (empty) {
      empty.textContent = emptyText || "No translation debug data";
      empty.classList.toggle("hidden", !hidden);
    }
  }

  renderTranslationItems({
    markup = "",
    hasItems = false,
    emptyText = "No matching translation items",
    meta = "-",
    loading = false,
    pageLabel = "-",
    canPrev = false,
    canNext = false,
  } = {}) {
    const list = this.querySelector("#translation-items-list");
    const empty = this.querySelector("#translation-items-empty");
    const loadingEl = this.querySelector("#translation-items-loading");
    const metaEl = this.querySelector("#translation-items-meta");
    const pageEl = this.querySelector("#translation-items-page");
    const prevBtn = this.querySelector("#translation-items-prev");
    const nextBtn = this.querySelector("#translation-items-next");
    if (metaEl) {
      metaEl.textContent = meta;
    }
    if (pageEl) {
      pageEl.textContent = pageLabel;
    }
    if (prevBtn) {
      prevBtn.disabled = loading || !canPrev;
    }
    if (nextBtn) {
      nextBtn.disabled = loading || !canNext;
    }
    if (loadingEl) {
      loadingEl.classList.toggle("hidden", !loading);
    }
    if (!list || !empty) {
      return;
    }
    if (loading) {
      list.innerHTML = "";
      list.classList.add("hidden");
      empty.classList.add("hidden");
      return;
    }
    if (!hasItems) {
      list.innerHTML = "";
      list.classList.add("hidden");
      empty.textContent = emptyText;
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    list.classList.remove("hidden");
    list.innerHTML = markup;
  }

  renderTranslationItemDetail({
    markup = "",
    meta = "-",
    hasItem = false,
    emptyText = "Please select an item from the left",
    loading = false,
    replayEnabled = false,
  } = {}) {
    const detail = this.querySelector("#translation-item-detail");
    const empty = this.querySelector("#translation-item-empty");
    const loadingEl = this.querySelector("#translation-item-loading");
    const metaEl = this.querySelector("#translation-item-meta");
    const replayButton = this.querySelector("#translation-item-replay");
    if (metaEl) {
      metaEl.textContent = meta;
    }
    if (loadingEl) {
      loadingEl.classList.toggle("hidden", !loading);
    }
    if (replayButton) {
      replayButton.disabled = !replayEnabled;
    }
    if (!detail || !empty) {
      return;
    }
    if (loading) {
      detail.innerHTML = "";
      detail.classList.add("hidden");
      empty.classList.add("hidden");
      return;
    }
    if (!hasItem) {
      detail.innerHTML = "";
      detail.classList.add("hidden");
      empty.textContent = emptyText;
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    detail.classList.remove("hidden");
    detail.innerHTML = markup;
  }

  renderTranslationReplay({
    markup = "",
    hasResult = false,
    status = "-",
  } = {}) {
    const result = this.querySelector("#translation-replay-result");
    const statusEl = this.querySelector("#translation-replay-status");
    if (statusEl) {
      statusEl.textContent = status;
    }
    if (!result) {
      return;
    }
    if (!hasResult) {
      result.innerHTML = "";
      result.classList.add("hidden");
      return;
    }
    result.innerHTML = markup;
    result.classList.remove("hidden");
  }
}

if (!customElements.get("status-detail-dialog")) {
  customElements.define("status-detail-dialog", StatusDetailDialog);
}
