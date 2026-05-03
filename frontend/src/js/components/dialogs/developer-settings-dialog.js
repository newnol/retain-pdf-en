class DeveloperSettingsDialog extends HTMLElement {
  connectedCallback() {
    if (this.dataset.hydrated === "1") {
      return;
    }
    this.dataset.hydrated = "1";
    this.innerHTML = `
      <dialog id="developer-dialog" class="desktop-dialog">
        <form method="dialog" class="desktop-shell">
          <div class="desktop-head">
            <div class="credential-dialog-head">
              <h2>Developer Settings</h2>
            </div>
            <button id="developer-close-btn" type="submit" class="dialog-close-btn" aria-label="Close">×</button>
          </div>
          <div class="desktop-body credential-dialog-body developer-dialog-body">
            <div class="developer-tabs" role="tablist" aria-label="Developer Settings">
              <button id="developer-tab-model" type="button" class="developer-tab is-active" data-developer-tab="model" role="tab" aria-selected="true">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4 7.5h16M4 12h10M4 16.5h7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                </svg>
                <span>Model</span>
              </button>
              <button id="developer-tab-runtime" type="button" class="developer-tab" data-developer-tab="runtime" role="tab" aria-selected="false">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 3.5v3m0 11v3m8.5-8.5h-3m-11 0h-3M18.01 5.99l-2.12 2.12M8.11 15.89l-2.12 2.12m0-12.02 2.12 2.12m7.78 7.78 2.12 2.12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                  <circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="1.6"/>
                </svg>
                <span>Execution</span>
              </button>
            </div>

            <div class="developer-panels">
              <section id="developer-panel-model" class="developer-panel is-active" data-developer-panel="model" role="tabpanel">
                <div class="credential-card compact-card">
                  <label>
                    <span>Task Workflow</span>
                    <select id="developer-workflow">
                      <option value="book">book · OCR + Translation + Rendering</option>
                      <option value="translate">translate · OCR + Translation</option>
                      <option value="render">render · Reuse existing task artifacts to re-render</option>
                    </select>
                  </label>
                  <label id="developer-render-source-wrap" class="hidden">
                    <span>Render Source Job ID</span>
                    <input id="developer-render-source-job-id" type="text" autocomplete="off" placeholder="Enter existing job_id" />
                  </label>
                  <p id="developer-workflow-note" class="muted">`book` runs OCR, translation, and PDF rendering in full.</p>
                  <label>
                    <span>Model Base URL</span>
                    <input id="developer-base-url" type="text" autocomplete="off" placeholder="e.g. https://api.deepseek.com/v1" />
                  </label>
                  <label>
                    <span>Model Name</span>
                    <input id="developer-model" type="text" autocomplete="off" placeholder="e.g. deepseek-v4-flash" />
                  </label>
                </div>
              </section>

              <section id="developer-panel-runtime" class="developer-panel" data-developer-panel="runtime" role="tabpanel" hidden>
                <div class="credential-card compact-card">
                  <div class="grid two developer-grid">
                    <label>
                      <span class="developer-label">
                        <span>Translation Concurrency</span>
                        <button type="button" class="developer-hint" aria-label="Translation concurrency info" data-tooltip="Number of concurrent requests sent to the translation model. Higher is usually faster but more likely to trigger rate limiting.">i</button>
                      </span>
                      <input id="developer-workers" type="number" min="1" step="1" inputmode="numeric" />
                    </label>
                    <label>
                      <span class="developer-label">
                        <span>Render Concurrency</span>
                        <button type="button" class="developer-hint" aria-label="Render concurrency info" data-tooltip="Number of concurrent tasks allowed during final PDF rendering and compilation.">i</button>
                      </span>
                      <input id="developer-compile-workers" type="number" min="1" step="1" inputmode="numeric" />
                    </label>
                    <label>
                      <span class="developer-label">
                        <span>Translation Batch Size</span>
                        <button type="button" class="developer-hint" aria-label="Translation batch size info" data-tooltip="Text batch size submitted to the translation model per request. Too large may affect stability.">i</button>
                      </span>
                      <input id="developer-batch-size" type="number" min="1" step="1" inputmode="numeric" />
                    </label>
                    <label>
                      <span class="developer-label">
                        <span>Classification Batch Size</span>
                        <button type="button" class="developer-hint" aria-label="Classification batch size info" data-tooltip="Batch size used for paper domain recognition and strategy classification.">i</button>
                      </span>
                      <input id="developer-classify-batch-size" type="number" min="1" step="1" inputmode="numeric" />
                    </label>
                    <label class="developer-span-full">
                      <span class="developer-label">
                        <span>Timeout Seconds</span>
                        <button type="button" class="developer-hint" aria-label="Timeout seconds info" data-tooltip="Total timeout in seconds for a single task. Tasks will be terminated by the backend if exceeded.">i</button>
                      </span>
                      <input id="developer-timeout-seconds" type="number" min="1" step="1" inputmode="numeric" />
                    </label>
                  </div>
                </div>
              </section>
            </div>
            <div class="actions credential-dialog-actions">
              <button id="developer-reset-btn" type="button" class="secondary">Reset Default</button>
              <button id="developer-save-btn" type="button">Save</button>
            </div>
          </div>
        </form>
      </dialog>
    `;
  }
}

if (!customElements.get("developer-settings-dialog")) {
  customElements.define("developer-settings-dialog", DeveloperSettingsDialog);
}
