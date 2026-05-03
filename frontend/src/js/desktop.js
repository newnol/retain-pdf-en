import { $ } from "./dom.js";
import {
  applyKeyInputs,
  loadPersistedConfig,
  savePersistedDesktopConfig,
  savePersistedBrowserStoredConfig,
} from "./config.js";
import { state } from "./state.js";

export function showDesktopUi() {
  $("open-output-btn").classList.remove("hidden");
}

export function setDesktopBusy(message = "") {
  const targetIds = ["browser-credentials-status"];
  for (const id of targetIds) {
    const el = $(id);
    if (!el) {
      continue;
    }
    if (message) {
      el.textContent = message;
      el.classList.remove("hidden");
    } else {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }
}

export function openSetupDialog() {
  document.dispatchEvent(new CustomEvent("retainpdf:open-browser-credentials", {
    detail: { setupMode: true },
  }));
}

export function closeSetupDialog() {
  const dialog = $("browser-credentials-dialog");
  if (dialog?.open && dialog.dataset.setupMode === "1") {
    dialog.close();
  }
}

export async function bootstrapDesktop(initialConfig = null) {
  state.desktopMode = true;
  showDesktopUi();
  const payload = initialConfig || await loadPersistedConfig();
  state.developerConfig = payload.developerConfig || {};
  applyKeyInputs(payload.browserConfig || {});
  state.desktopConfigured = !!payload.firstRunCompleted;
  if (!state.desktopConfigured) {
    openSetupDialog();
  } else {
    closeSetupDialog();
  }
}

export async function saveDesktopConfig(mineruToken, modelApiKey, afterSave, extraBrowserConfig = {}) {
  let markConfigured = false;
  let nextBrowserConfig = {
    ...extraBrowserConfig,
    mineruToken,
    modelApiKey,
  };
  let callback = afterSave;
  if (typeof mineruToken === "object" && mineruToken !== null) {
    nextBrowserConfig = { ...(mineruToken.browserConfig || mineruToken) };
    markConfigured = !!mineruToken.markConfigured;
    callback = typeof modelApiKey === "function" ? modelApiKey : afterSave;
  } else {
    markConfigured = !!extraBrowserConfig?.markConfigured;
  }
  let persisted = await savePersistedBrowserStoredConfig({
    ...nextBrowserConfig,
  });
  state.developerConfig = persisted.developerConfig || state.developerConfig;
  applyKeyInputs(persisted.browserConfig || {});
  if (markConfigured && !persisted.firstRunCompleted) {
    persisted = await savePersistedDesktopConfig({ firstRunCompleted: true });
    state.developerConfig = persisted.developerConfig || state.developerConfig;
    applyKeyInputs(persisted.browserConfig || {});
  }
  state.desktopConfigured = !!persisted.firstRunCompleted;
  if (state.desktopConfigured) {
    closeSetupDialog();
    $("error-box").textContent = "-";
  }
  if (callback) {
    try {
      await callback();
    } catch (error) {
      if (state.desktopConfigured) {
        const message = error?.message || String(error);
        throw new Error(`Initial configuration saved, but cannot connect to local backend. ${message}`);
      }
      throw error;
    }
  }
  state.developerConfig = persisted.developerConfig || state.developerConfig;
  applyKeyInputs(persisted.browserConfig || {});
  return persisted;
}
