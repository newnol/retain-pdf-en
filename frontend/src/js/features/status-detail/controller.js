import { $ } from "../../dom.js";
import { buildFrontendPageUrl } from "../../config.js";

function escapeHtml(value) {
  return `${value ?? ""}`
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stringifyPretty(value) {
  if (value == null || value === "") {
    return "-";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch (_error) {
    return String(value);
  }
}

function boolLabel(value) {
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  return "-";
}

function previewText(value) {
  const text = `${value ?? ""}`.trim();
  if (!text) {
    return "-";
  }
  if (text.length <= 180) {
    return text;
  }
  return `${text.slice(0, 177)}...`;
}

function normalizeRoutePath(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join(" -> ");
  }
  return `${value ?? ""}`.trim();
}

function firstNonEmptyText(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function diagnosticsOf(value) {
  const item = value && typeof value === "object" ? value : {};
  const nested = item.translation_diagnostics;
  return nested && typeof nested === "object" ? nested : {};
}

function pageNumberOf(value, fallback = "-") {
  const pageNumber = Number(value?.page_number);
  if (Number.isFinite(pageNumber) && pageNumber > 0) {
    return `${pageNumber}`;
  }
  const pageIdx = Number(value?.page_idx);
  if (Number.isFinite(pageIdx) && pageIdx >= 0) {
    return `${pageIdx + 1}`;
  }
  return fallback;
}

function finalStatusOf(value) {
  const diagnostics = diagnosticsOf(value);
  return firstNonEmptyText(value?.final_status, diagnostics.final_status);
}

function fallbackToOf(value) {
  const diagnostics = diagnosticsOf(value);
  return firstNonEmptyText(value?.fallback_to, diagnostics.fallback_to);
}

function degradationReasonOf(value) {
  const diagnostics = diagnosticsOf(value);
  return firstNonEmptyText(value?.degradation_reason, diagnostics.degradation_reason);
}

function routePathOf(value) {
  const diagnostics = diagnosticsOf(value);
  return value?.route_path ?? diagnostics.route_path ?? [];
}

function errorTypesOf(value) {
  if (Array.isArray(value?.error_types) && value.error_types.length) {
    return value.error_types;
  }
  const diagnostics = diagnosticsOf(value);
  if (Array.isArray(diagnostics.error_types) && diagnostics.error_types.length) {
    return diagnostics.error_types;
  }
  if (Array.isArray(diagnostics.error_trace) && diagnostics.error_trace.length) {
    return diagnostics.error_trace
      .map((entry) => firstNonEmptyText(entry?.type, entry?.error_type))
      .filter(Boolean);
  }
  return [];
}

function finalStatusLabel(value) {
  switch (`${value || ""}`.trim()) {
    case "translated":
      return "Translated";
    case "kept_origin":
      return "Kept Original";
    case "skipped":
      return "Skipped";
    default:
      return `${value || "-"}`;
  }
}

function finalStatusClass(value) {
  switch (`${value || ""}`.trim()) {
    case "translated":
      return "is-translated";
    case "kept_origin":
      return "is-kept-origin";
    case "skipped":
      return "is-skipped";
    default:
      return "is-neutral";
  }
}

function summarizeTranslationFilter(query = {}) {
  const finalStatus = `${query.finalStatus || ""}`.trim() || "All";
  const search = `${query.q || ""}`.trim() || "No search term";
  return `final_status=${finalStatus}，q=${search}`;
}

export function mountStatusDetailFeature({
  state,
  apiPrefix,
  fetchTranslationDiagnostics,
  fetchTranslationItems,
  fetchTranslationItem,
  replayTranslationItem,
} = {}) {
  const translationState = {
    jobId: "",
    loaded: false,
    summary: null,
    query: {
      finalStatus: "kept_origin",
      q: "",
      limit: 20,
      offset: 0,
    },
    list: [],
    total: 0,
    selectedItemId: "",
    selectedItem: null,
    replay: null,
  };

  function buildDetailPageUrl(jobId) {
    const normalizedJobId = `${jobId || ""}`.trim();
    if (!normalizedJobId) {
      return "";
    }
    return buildFrontendPageUrl("./detail.html", {
      job_id: normalizedJobId,
    });
  }

  function dialogComponent() {
    return document.querySelector("status-detail-dialog");
  }

  function getCurrentJobId() {
    return `${state?.currentJobId || ""}`.trim();
  }

  function activateDetailTab(name = "overview") {
    const component = dialogComponent();
    if (component?.activateTab) {
      component.activateTab(name);
      if (name === "translation") {
        void ensureTranslationData();
      }
      return;
    }
    const tabs = document.querySelectorAll(".detail-tab");
    const panels = document.querySelectorAll(".detail-tab-panel");
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
    if (name === "translation") {
      void ensureTranslationData();
    }
  }

  function openStatusDetailDialog(tabName = "overview") {
    const component = dialogComponent();
    if (component?.open) {
      component.open(tabName);
      if (tabName === "translation") {
        void ensureTranslationData();
      }
      return;
    }
    activateDetailTab(tabName);
    $("status-detail-dialog")?.showModal();
  }

  function resetTranslationState(jobId = "") {
    translationState.jobId = jobId;
    translationState.loaded = false;
    translationState.summary = null;
    translationState.list = [];
    translationState.total = 0;
    translationState.selectedItemId = "";
    translationState.selectedItem = null;
    translationState.replay = null;
  }

  function renderTranslationEmpty(message) {
    const component = dialogComponent();
    component?.renderTranslationSummary({
      hidden: true,
      emptyText: message,
    });
    component?.renderTranslationItems({
      loading: false,
      hasItems: false,
      emptyText: message,
      meta: "-",
    });
    component?.renderTranslationItemDetail({
      loading: false,
      hasItem: false,
      emptyText: "Please select an item from the left",
      meta: "-",
      replayEnabled: false,
    });
    component?.renderTranslationReplay({
      hasResult: false,
      status: "-",
    });
  }

  function renderTranslationSummary() {
    const summary = translationState.summary?.summary || {};
    dialogComponent()?.renderTranslationSummary({
      counts: summary.counts || {},
      finalStatusCounts: summary.final_status_counts || {},
      providerFamily: `${summary.provider_family || ""}`.trim(),
      summaryScopeText: "Full statistics for current job",
      filterText: summarizeTranslationFilter(translationState.query),
      hidden: false,
    });
  }

  function renderTranslationItems({ loading = false, emptyText = "No matching translation items" } = {}) {
    const component = dialogComponent();
    const list = translationState.list || [];
    const offset = Number(translationState.query.offset || 0);
    const limit = Number(translationState.query.limit || 20);
    const total = Number(translationState.total || 0);
    const start = total > 0 ? offset + 1 : 0;
    const end = total > 0 ? Math.min(offset + list.length, total) : 0;
    const totalPages = total > 0 ? Math.ceil(total / Math.max(limit, 1)) : 0;
    const currentPage = total > 0 ? Math.floor(offset / Math.max(limit, 1)) + 1 : 0;
    const meta = loading
      ? "Loading..."
      : `${total} total, ${list.length} on this page, offset ${offset}, limit ${limit}`;
    const pageLabel = loading
      ? "Loading..."
      : total > 0
        ? `Page ${currentPage} / ${totalPages}`
        : "Page 0 / 0";
    const markup = list.map((item) => {
      const active = item.item_id === translationState.selectedItemId;
      const routePath = normalizeRoutePath(routePathOf(item));
      const errorTypes = errorTypesOf(item);
      const errorLabel = errorTypes.length ? errorTypes.join(", ") : "-";
      const degradationReason = degradationReasonOf(item) || "-";
      const finalStatus = finalStatusOf(item);
      return `
        <button
          type="button"
          class="translation-item-card${active ? " is-active" : ""}"
          data-translation-item-id="${escapeHtml(item.item_id)}"
        >
          <div class="translation-item-card-top">
            <span class="translation-item-id mono">${escapeHtml(item.item_id || "-")}</span>
            <span class="translation-item-status ${finalStatusClass(finalStatus)}">${escapeHtml(finalStatusLabel(finalStatus))}</span>
          </div>
          <div class="translation-item-card-meta">
            <span class="translation-item-chip">Page ${escapeHtml(pageNumberOf(item))}</span>
            <span class="translation-item-chip">${escapeHtml(item.block_type || "-")}</span>
            <span class="translation-item-chip">${escapeHtml(item.classification_label || "-")}</span>
          </div>
          <div class="translation-item-card-route"><strong>route</strong> ${escapeHtml(routePath || "-")}</div>
          <div class="translation-item-card-preview">${escapeHtml(previewText(item.source_preview || item.source_text || ""))}</div>
          <div class="translation-item-card-footer">
            <span><strong>fallback</strong> ${escapeHtml(fallbackToOf(item) || "-")}</span>
            <span><strong>error</strong> ${escapeHtml(errorLabel)}</span>
          </div>
          <div class="translation-item-card-route"><strong>degradation</strong> ${escapeHtml(degradationReason)}</div>
        </button>
      `;
    }).join("");
    component?.renderTranslationItems({
      markup,
      hasItems: list.length > 0,
      emptyText,
      meta,
      loading,
      pageLabel,
      canPrev: offset > 0,
      canNext: offset + list.length < total,
    });
  }

  function renderField(label, value) {
    return `
      <div class="info-row translation-detail-row">
        <span class="label">${escapeHtml(label)}</span>
        <span class="info-value">${escapeHtml(value)}</span>
      </div>
    `;
  }

  function renderTextBlock(label, value) {
    return `
      <section class="translation-text-block">
        <div class="translation-debug-subhead">
          <h4>${escapeHtml(label)}</h4>
        </div>
        <pre>${escapeHtml(stringifyPretty(value))}</pre>
      </section>
    `;
  }

  function renderTranslationItemDetail({ loading = false, emptyText = "Please select an item from the left" } = {}) {
    const component = dialogComponent();
    const payload = translationState.selectedItem;
    if (loading) {
      component?.renderTranslationItemDetail({
        loading: true,
        hasItem: false,
        emptyText,
        meta: "Loading...",
        replayEnabled: false,
      });
      return;
    }
    if (!payload?.item) {
      component?.renderTranslationItemDetail({
        loading: false,
        hasItem: false,
        emptyText,
        meta: "-",
        replayEnabled: false,
      });
      return;
    }
    const item = payload.item || {};
    const diagnostics = diagnosticsOf(item);
    const routePath = normalizeRoutePath(routePathOf(item));
    const pageNumber = pageNumberOf(payload, pageNumberOf(item));
    const finalStatus = finalStatusOf(item) || finalStatusOf(payload) || "-";
    const markup = `
      <div class="detail-info-list translation-detail-grid">
        ${renderField("item_id", payload.item_id || item.item_id || "-")}
        ${renderField("page_number", pageNumber)}
        ${renderField("block_type", item.block_type || "-")}
        ${renderField("math_mode", item.math_mode || "-")}
        ${renderField("classification_label", item.classification_label || "-")}
        ${renderField("should_translate", boolLabel(item.should_translate))}
        ${renderField("skip_reason", item.skip_reason || "-")}
        ${renderField("final_status", finalStatus)}
        ${renderField("route_path", routePath || "-")}
        ${renderField("fallback_to", fallbackToOf(item) || "-")}
        ${renderField("degradation_reason", degradationReasonOf(item) || "-")}
      </div>
      ${renderTextBlock("Source", item.source_text || "")}
      ${renderTextBlock("Saved Translation", item.translated_text || item.translation_unit_translated_text || item.group_translated_text || "")}
      ${renderTextBlock("Protected Translation", item.protected_translated_text || item.translation_unit_protected_translated_text || item.group_protected_translated_text || "")}
      ${renderTextBlock("translation_diagnostics", diagnostics || {})}
    `;
    component?.renderTranslationItemDetail({
      loading: false,
      hasItem: true,
      markup,
      meta: `${payload.item_id || item.item_id || "-"} · Page ${pageNumber}`,
      replayEnabled: true,
    });
  }

  function renderTranslationReplay() {
    const replay = translationState.replay;
    if (!replay?.payload) {
      dialogComponent()?.renderTranslationReplay({
        hasResult: false,
        status: "-",
      });
      return;
    }
    const payload = replay.payload || {};
    const markup = `
      <div class="translation-replay-grid">
        ${renderTextBlock("policy_before", payload.policy_before || {})}
        ${renderTextBlock("policy_after", payload.policy_after || {})}
        ${renderTextBlock("replay_result", payload.replay_result || {})}
        ${renderTextBlock("replay_error", payload.replay_error || null)}
      </div>
    `;
    dialogComponent()?.renderTranslationReplay({
      hasResult: true,
      markup,
      status: payload.replay_error ? "Replay returned error" : "Replay complete",
    });
  }

  async function loadTranslationSummary(jobId) {
    translationState.summary = await fetchTranslationDiagnostics(jobId, apiPrefix);
    renderTranslationSummary();
  }

  async function reloadTranslationSummaryAndItems({ selectFirst = false } = {}) {
    const jobId = getCurrentJobId();
    if (!jobId) {
      resetTranslationState("");
      renderTranslationEmpty("Please select a task first");
      return;
    }
    await loadTranslationSummary(jobId);
    await loadTranslationItems(jobId, { selectFirst });
  }

  async function loadTranslationItems(jobId, { selectFirst = false } = {}) {
    renderTranslationItems({ loading: true });
    const payload = await fetchTranslationItems(jobId, apiPrefix, translationState.query);
    translationState.list = Array.isArray(payload?.items) ? payload.items : [];
    translationState.total = Number(payload?.total || 0);
    renderTranslationItems();
    const shouldKeepCurrent = translationState.list.some((item) => item.item_id === translationState.selectedItemId);
    if (shouldKeepCurrent) {
      return;
    }
    const nextItemId = selectFirst && translationState.list.length
      ? `${translationState.list[0].item_id || ""}`.trim()
      : "";
    translationState.selectedItemId = nextItemId;
    translationState.selectedItem = null;
    translationState.replay = null;
    renderTranslationItemDetail({
      emptyText: nextItemId ? "Please select an item from the left" : "No items available to view",
    });
    renderTranslationReplay();
    if (nextItemId) {
      await loadTranslationItem(jobId, nextItemId);
    }
  }

  async function loadTranslationItem(jobId, itemId) {
    if (!itemId) {
      return;
    }
    translationState.selectedItemId = itemId;
    translationState.replay = null;
    renderTranslationItems();
    renderTranslationItemDetail({ loading: true });
    renderTranslationReplay();
    translationState.selectedItem = await fetchTranslationItem(jobId, itemId, apiPrefix);
    renderTranslationItemDetail();
  }

  async function replayCurrentItem() {
    const jobId = getCurrentJobId();
    const itemId = `${translationState.selectedItemId || ""}`.trim();
    if (!jobId || !itemId) {
      return;
    }
    dialogComponent()?.renderTranslationReplay({
      hasResult: false,
      status: "Replaying...",
    });
    translationState.replay = await replayTranslationItem(jobId, itemId, apiPrefix);
    renderTranslationReplay();
  }

  async function ensureTranslationData({ force = false } = {}) {
    const jobId = getCurrentJobId();
    if (!jobId) {
      resetTranslationState("");
      renderTranslationEmpty("Please select a task first");
      return;
    }
    if (translationState.jobId !== jobId) {
      resetTranslationState(jobId);
    }
    if (translationState.loaded && !force) {
      renderTranslationSummary();
      renderTranslationItems();
      renderTranslationItemDetail();
      renderTranslationReplay();
      return;
    }
    renderTranslationEmpty("Loading translation debug data...");
    try {
      await reloadTranslationSummaryAndItems({ selectFirst: true });
      translationState.loaded = true;
    } catch (error) {
      renderTranslationEmpty(error.message || String(error));
    }
  }

  async function handleTranslationApply() {
    translationState.query.finalStatus = `${$("translation-filter-final-status")?.value || ""}`.trim();
    translationState.query.q = `${$("translation-filter-query")?.value || ""}`.trim();
    translationState.query.offset = 0;
    translationState.loaded = true;
    renderTranslationSummary();
    try {
      await reloadTranslationSummaryAndItems({ selectFirst: true });
    } catch (error) {
      renderTranslationItems({
        loading: false,
        hasItems: false,
        emptyText: error.message || String(error),
      });
    }
  }

  async function changeTranslationPage(direction) {
    const limit = Number(translationState.query.limit || 20);
    const nextOffset = direction === "next"
      ? Number(translationState.query.offset || 0) + limit
      : Math.max(0, Number(translationState.query.offset || 0) - limit);
    if (nextOffset === Number(translationState.query.offset || 0)) {
      return;
    }
    translationState.query.offset = nextOffset;
    try {
      await loadTranslationItems(getCurrentJobId(), { selectFirst: true });
    } catch (error) {
      renderTranslationItems({
        loading: false,
        hasItems: false,
        emptyText: error.message || String(error),
      });
    }
  }

  function bindEvents() {
    $("status-detail-btn")?.addEventListener("click", () => openStatusDetailDialog("overview"));
    document.querySelectorAll(".detail-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        activateDetailTab(tab.dataset.tab || "overview");
      });
    });
    $("translation-filter-apply")?.addEventListener("click", () => {
      void handleTranslationApply();
    });
    $("translation-filter-query")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void handleTranslationApply();
      }
    });
    $("translation-items-prev")?.addEventListener("click", () => {
      void changeTranslationPage("prev");
    });
    $("translation-items-next")?.addEventListener("click", () => {
      void changeTranslationPage("next");
    });
    $("translation-items-list")?.addEventListener("click", (event) => {
      const button = event.target?.closest?.("[data-translation-item-id]");
      const itemId = `${button?.dataset?.translationItemId || ""}`.trim();
      if (!itemId) {
        return;
      }
      void loadTranslationItem(getCurrentJobId(), itemId).catch((error) => {
        renderTranslationItemDetail({
          emptyText: error.message || String(error),
        });
      });
    });
    $("translation-item-replay")?.addEventListener("click", () => {
      void replayCurrentItem().catch((error) => {
        dialogComponent()?.renderTranslationReplay({
          hasResult: true,
          status: "Replay failed",
          markup: renderTextBlock("replay_error", {
            message: error.message || String(error),
          }),
        });
      });
    });
  }

  return {
    activateDetailTab,
    bindEvents,
    openStatusDetailDialog,
    buildDetailPageUrl,
    ensureTranslationData,
  };
}
