import { $ } from "./dom.js";
import {
  BROWSER_CONFIG_STORAGE_KEY,
  DEVELOPER_CONFIG_STORAGE_KEY,
  DEFAULT_BASE_URL,
  DEFAULT_MODEL,
} from "./constants.js";
import { getDesktopHost, isDesktopHostAvailable } from "./desktop-host.js";
import { DEFAULT_OCR_PROVIDER, normalizeOcrProvider } from "./provider-config.js";

let runtimeConfig = { ...(window.__FRONT_RUNTIME_CONFIG__ || {}) };
let desktopPersistedSnapshot = null;

const API_V1_SUFFIX = "/api/v1";
const desktopBridge = getDesktopHost();

export function isFileProtocol() {
  return window.location.protocol === "file:";
}

export function buildFrontendPageUrl(relativePath, params = {}) {
  const url = new URL(relativePath, window.location.href);
  for (const [key, value] of Object.entries(params || {})) {
    const normalized = `${value ?? ""}`.trim();
    if (!normalized) {
      url.searchParams.delete(key);
      continue;
    }
    url.searchParams.set(key, normalized);
  }
  return url.toString();
}

export function readerMessageTargetOrigin() {
  return isFileProtocol() ? "*" : window.location.origin;
}

export function isTrustedWindowMessage(event, expectedSource = null) {
  if (expectedSource && event.source !== expectedSource) {
    return false;
  }
  if (isFileProtocol()) {
    return event.origin === "null" || !event.origin;
  }
  return event.origin === window.location.origin;
}

export function apiBase() {
  if (typeof runtimeConfig.apiBase === "string" && runtimeConfig.apiBase.trim()) {
    return runtimeConfig.apiBase.trim().replace(/\/+$/, "").replace(new RegExp(`${API_V1_SUFFIX}$`), "");
  }
  const host = window.location.hostname || "127.0.0.1";
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  return `${protocol}//${host}:41000`;
}

export function buildApiUrl(apiPrefix = "", relativePath = "") {
  const normalizedPrefix = `${apiPrefix || ""}`.trim().replace(/^\/+/, "").replace(/\/+$/, "");
  const normalizedPath = `${relativePath || ""}`.trim().replace(/^\/+/, "");
  const segments = [apiBase(), normalizedPrefix].filter(Boolean);
  if (normalizedPath) {
    segments.push(normalizedPath);
  }
  return segments.join("/");
}

export function mockScenario() {
  const value = new URLSearchParams(window.location.search).get("mock")?.trim().toLowerCase() || "";
  return ["queued", "running", "succeeded", "failed"].includes(value) ? value : "";
}

export function isMockMode() {
  return !!mockScenario();
}

export function frontendApiKey() {
  return typeof runtimeConfig.xApiKey === "string" ? runtimeConfig.xApiKey.trim() : "";
}

export function buildApiHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const apiKey = frontendApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

export function defaultMineruToken() {
  return typeof runtimeConfig.mineruToken === "string" ? runtimeConfig.mineruToken : "";
}

export function defaultPaddleToken() {
  return typeof runtimeConfig.paddleToken === "string" ? runtimeConfig.paddleToken : "";
}

export function defaultOcrProvider() {
  return normalizeOcrProvider(runtimeConfig.ocrProvider);
}

export function defaultModelApiKey() {
  return typeof runtimeConfig.modelApiKey === "string" ? runtimeConfig.modelApiKey : "";
}

export function defaultModelName() {
  return typeof runtimeConfig.model === "string" && runtimeConfig.model.trim()
    ? runtimeConfig.model.trim()
    : DEFAULT_MODEL;
}

export function defaultModelBaseUrl() {
  return typeof runtimeConfig.baseUrl === "string" && runtimeConfig.baseUrl.trim()
    ? runtimeConfig.baseUrl.trim()
    : DEFAULT_BASE_URL;
}

export function isDesktopMode() {
  return isDesktopHostAvailable();
}

export function setRuntimeConfig(nextConfig = {}) {
  runtimeConfig = {
    ...runtimeConfig,
    ...nextConfig,
  };
}

function isObject(value) {
  return typeof value === "object" && value !== null;
}

function readStoredConfig(key) {
  if (typeof window.localStorage === "undefined") {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return isObject(parsed) ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function writeStoredConfig(key, payload = {}) {
  if (typeof window.localStorage === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(payload));
  } catch (_err) {
    // Ignore storage quota / privacy mode failures.
  }
}

function normalizeBrowserStoredConfig(payload = {}) {
  const source = isObject(payload) ? payload : {};
  return {
    ocrProvider: normalizeOcrProvider(source.ocrProvider),
    mineruToken: typeof source.mineruToken === "string" ? source.mineruToken : "",
    paddleToken: typeof source.paddleToken === "string" ? source.paddleToken : "",
    modelApiKey: typeof source.modelApiKey === "string" ? source.modelApiKey : "",
  };
}

function normalizeDeveloperStoredConfig(payload = {}) {
  return isObject(payload) ? { ...payload } : {};
}

function currentBrowserStoredConfig() {
  return normalizeBrowserStoredConfig({
    ocrProvider: $("ocr_provider")?.value || DEFAULT_OCR_PROVIDER,
    mineruToken: $("mineru_token")?.value || "",
    paddleToken: $("paddle_token")?.value || "",
    modelApiKey: $("api_key")?.value || "",
  });
}

function desktopRuntimeToBrowserConfig(runtime = {}) {
  const source = isObject(runtime) ? runtime : {};
  return normalizeBrowserStoredConfig({
    ocrProvider: source.ocrProvider,
    mineruToken: source.mineruToken,
    paddleToken: source.paddleToken,
    modelApiKey: source.modelApiKey,
  });
}

function buildRuntimeConfig(browserConfig = {}, developerConfig = {}, baseRuntimeConfig = {}) {
  const nextBrowserConfig = normalizeBrowserStoredConfig(browserConfig);
  const nextDeveloperConfig = normalizeDeveloperStoredConfig(developerConfig);
  const nextRuntimeConfig = {
    ...(isObject(baseRuntimeConfig) ? baseRuntimeConfig : {}),
    ocrProvider: nextBrowserConfig.ocrProvider,
    mineruToken: nextBrowserConfig.mineruToken,
    paddleToken: nextBrowserConfig.paddleToken,
    modelApiKey: nextBrowserConfig.modelApiKey,
    developerConfig: nextDeveloperConfig,
  };
  if (typeof nextDeveloperConfig.model === "string" && nextDeveloperConfig.model.trim()) {
    nextRuntimeConfig.model = nextDeveloperConfig.model.trim();
  }
  if (typeof nextDeveloperConfig.baseUrl === "string" && nextDeveloperConfig.baseUrl.trim()) {
    nextRuntimeConfig.baseUrl = nextDeveloperConfig.baseUrl.trim();
  }
  return nextRuntimeConfig;
}

function normalizeDesktopPersistedConfig(payload = {}, fallback = {}) {
  const source = isObject(payload) ? payload : {};
  const base = isObject(fallback) ? fallback : {};
  const runtimeSource = {
    ...(isObject(base.runtimeConfig) ? base.runtimeConfig : {}),
    ...(isObject(source.runtimeConfig) ? source.runtimeConfig : {}),
  };
  const browserConfig = normalizeBrowserStoredConfig({
    ...(isObject(base.browserConfig) ? base.browserConfig : {}),
    ...desktopRuntimeToBrowserConfig(runtimeSource),
    ...(isObject(source.browserConfig) ? source.browserConfig : {}),
  });
  const developerConfig = normalizeDeveloperStoredConfig(
    source.developerConfig
      ?? runtimeSource.developerConfig
      ?? base.developerConfig
      ?? {},
  );
  return {
    firstRunCompleted: source.firstRunCompleted ?? base.firstRunCompleted ?? false,
    closeToTrayHintShown: source.closeToTrayHintShown ?? base.closeToTrayHintShown ?? false,
    browserConfig,
    developerConfig,
    runtimeConfig: buildRuntimeConfig(browserConfig, developerConfig, runtimeSource),
  };
}

function persistShadowConfig(browserConfig, developerConfig) {
  writeStoredConfig(BROWSER_CONFIG_STORAGE_KEY, normalizeBrowserStoredConfig(browserConfig));
  writeStoredConfig(DEVELOPER_CONFIG_STORAGE_KEY, normalizeDeveloperStoredConfig(developerConfig));
}

async function saveDesktopPersistedConfig(partial = {}) {
  const baseline = desktopPersistedSnapshot || normalizeDesktopPersistedConfig({}, {
    browserConfig: readStoredConfig(BROWSER_CONFIG_STORAGE_KEY),
    developerConfig: readStoredConfig(DEVELOPER_CONFIG_STORAGE_KEY),
    runtimeConfig,
  });
  const merged = normalizeDesktopPersistedConfig({
    ...baseline,
    ...partial,
    browserConfig: partial.browserConfig
      ? { ...baseline.browserConfig, ...partial.browserConfig }
      : baseline.browserConfig,
    developerConfig: partial.developerConfig
      ? { ...baseline.developerConfig, ...partial.developerConfig }
      : baseline.developerConfig,
    runtimeConfig: {
      ...baseline.runtimeConfig,
      ...(isObject(partial.runtimeConfig) ? partial.runtimeConfig : {}),
    },
  });
  const savePayload = {
    firstRunCompleted: merged.firstRunCompleted,
    closeToTrayHintShown: merged.closeToTrayHintShown,
    ocrProvider: merged.browserConfig.ocrProvider,
    mineruToken: merged.browserConfig.mineruToken,
    paddleToken: merged.browserConfig.paddleToken,
    modelApiKey: merged.browserConfig.modelApiKey,
    developerConfig: merged.developerConfig,
    runtimeConfig: merged.runtimeConfig,
  };
  const response = await desktopBridge.saveDesktopConfig(savePayload);
  desktopPersistedSnapshot = normalizeDesktopPersistedConfig(response, savePayload);
  setRuntimeConfig(desktopPersistedSnapshot.runtimeConfig);
  persistShadowConfig(desktopPersistedSnapshot.browserConfig, desktopPersistedSnapshot.developerConfig);
  return desktopPersistedSnapshot;
}

export async function savePersistedDesktopConfig(partial = {}) {
  if (!isDesktopMode()) {
    return {
      browserConfig: normalizeBrowserStoredConfig(partial.browserConfig),
      developerConfig: normalizeDeveloperStoredConfig(partial.developerConfig),
      runtimeConfig: buildRuntimeConfig(
        partial.browserConfig,
        partial.developerConfig,
        partial.runtimeConfig,
      ),
      firstRunCompleted: !!partial.firstRunCompleted,
      closeToTrayHintShown: !!partial.closeToTrayHintShown,
    };
  }
  return saveDesktopPersistedConfig(partial);
}

export async function loadPersistedConfig() {
  const shadowBrowserConfig = readStoredConfig(BROWSER_CONFIG_STORAGE_KEY);
  const shadowDeveloperConfig = readStoredConfig(DEVELOPER_CONFIG_STORAGE_KEY);
  if (!isDesktopMode()) {
    return {
      browserConfig: normalizeBrowserStoredConfig(shadowBrowserConfig),
      developerConfig: normalizeDeveloperStoredConfig(shadowDeveloperConfig),
      runtimeConfig,
      firstRunCompleted: false,
      closeToTrayHintShown: false,
    };
  }
  const payload = await desktopBridge.loadDesktopConfig();
  desktopPersistedSnapshot = normalizeDesktopPersistedConfig(payload, {
    browserConfig: shadowBrowserConfig,
    developerConfig: shadowDeveloperConfig,
    runtimeConfig,
  });
  setRuntimeConfig(desktopPersistedSnapshot.runtimeConfig);
  persistShadowConfig(desktopPersistedSnapshot.browserConfig, desktopPersistedSnapshot.developerConfig);
  return desktopPersistedSnapshot;
}

export function loadBrowserStoredConfig() {
  return isDesktopMode() && desktopPersistedSnapshot
    ? desktopPersistedSnapshot.browserConfig
    : normalizeBrowserStoredConfig(readStoredConfig(BROWSER_CONFIG_STORAGE_KEY));
}

export function saveBrowserStoredConfig(payload = currentBrowserStoredConfig()) {
  writeStoredConfig(BROWSER_CONFIG_STORAGE_KEY, normalizeBrowserStoredConfig(payload));
}

export async function savePersistedBrowserStoredConfig(payload = currentBrowserStoredConfig()) {
  const nextBrowserConfig = normalizeBrowserStoredConfig(payload);
  saveBrowserStoredConfig(nextBrowserConfig);
  if (!isDesktopMode()) {
    return {
      browserConfig: nextBrowserConfig,
      developerConfig: loadDeveloperStoredConfig(),
      runtimeConfig,
      firstRunCompleted: false,
      closeToTrayHintShown: false,
    };
  }
  return saveDesktopPersistedConfig({ browserConfig: nextBrowserConfig });
}

export function loadDeveloperStoredConfig() {
  return isDesktopMode() && desktopPersistedSnapshot
    ? desktopPersistedSnapshot.developerConfig
    : normalizeDeveloperStoredConfig(readStoredConfig(DEVELOPER_CONFIG_STORAGE_KEY));
}

export function saveDeveloperStoredConfig(payload = {}) {
  writeStoredConfig(DEVELOPER_CONFIG_STORAGE_KEY, normalizeDeveloperStoredConfig(payload));
}

export async function savePersistedDeveloperStoredConfig(payload = {}) {
  const nextDeveloperConfig = normalizeDeveloperStoredConfig(payload);
  saveDeveloperStoredConfig(nextDeveloperConfig);
  if (!isDesktopMode()) {
    return {
      browserConfig: loadBrowserStoredConfig(),
      developerConfig: nextDeveloperConfig,
      runtimeConfig,
      firstRunCompleted: false,
      closeToTrayHintShown: false,
    };
  }
  return saveDesktopPersistedConfig({ developerConfig: nextDeveloperConfig });
}

export function applyKeyInputs(credentialsOrMineruToken, legacyModelApiKey = "") {
  const credentials = typeof credentialsOrMineruToken === "object" && credentialsOrMineruToken
    ? credentialsOrMineruToken
    : {
        ocrProvider: DEFAULT_OCR_PROVIDER,
        mineruToken: credentialsOrMineruToken,
        paddleToken: "",
        modelApiKey: legacyModelApiKey,
      };
  const ocrProvider = normalizeOcrProvider(credentials.ocrProvider);
  const mineruToken = credentials.mineruToken || "";
  const paddleToken = credentials.paddleToken || "";
  const modelApiKey = credentials.modelApiKey || "";
  $("ocr_provider").value = ocrProvider;
  $("mineru_token").value = mineruToken;
  $("paddle_token").value = paddleToken;
  $("api_key").value = modelApiKey;
}

export async function desktopInvoke(command, args = {}) {
  if (!desktopBridge) {
    throw new Error("Desktop interface not available");
  }
  return desktopBridge.invoke(command, args);
}

export async function openDesktopOutputDirectory() {
  if (!desktopBridge) {
    throw new Error("Desktop interface not available");
  }
  return desktopBridge.openOutputDirectory();
}
