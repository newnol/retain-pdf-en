function isObject(value) {
  return typeof value === "object" && value !== null;
}

function buildInvokeAdapter(source) {
  if (!isObject(source) || typeof source.invoke !== "function") {
    return null;
  }
  return {
    invoke(command, args = {}) {
      return source.invoke(command, args);
    },
  };
}

function resolveDesktopHost() {
  const preferredBridge = isObject(window.retainPdfDesktop) ? window.retainPdfDesktop : null;
  const legacyBridge = isObject(window.__TAURI_INTERNALS__) ? window.__TAURI_INTERNALS__ : null;
  const invokeAdapter = buildInvokeAdapter(preferredBridge) || buildInvokeAdapter(legacyBridge);

  if (!preferredBridge && !invokeAdapter) {
    return null;
  }

  return {
    invoke(command, args = {}) {
      if (!invokeAdapter) {
        throw new Error("Desktop interface not available");
      }
      return invokeAdapter.invoke(command, args);
    },
    loadDesktopConfig() {
      if (preferredBridge && typeof preferredBridge.loadDesktopConfig === "function") {
        return preferredBridge.loadDesktopConfig();
      }
      return invokeAdapter.invoke("load_desktop_config");
    },
    saveDesktopConfig(payload = {}) {
      if (preferredBridge && typeof preferredBridge.saveDesktopConfig === "function") {
        return preferredBridge.saveDesktopConfig(payload);
      }
      return invokeAdapter.invoke("save_desktop_config", { payload });
    },
    openOutputDirectory() {
      return invokeAdapter.invoke("open_output_directory");
    },
    onStartupProgress(callback) {
      if (preferredBridge && typeof preferredBridge.onStartupProgress === "function") {
        return preferredBridge.onStartupProgress(callback);
      }
      return () => {};
    },
    platform: preferredBridge?.platform || "",
  };
}

const desktopHost = resolveDesktopHost();

export function getDesktopHost() {
  return desktopHost;
}

export function isDesktopHostAvailable() {
  return !!desktopHost;
}
