const { app, BrowserWindow, Menu, Tray, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const DESKTOP_API_KEY = "retain-pdf-desktop";
let backendChild = null;
let backendStopping = false;
let splashWindow = null;
let mainWindow = null;
let usingExternalBackend = false;
let tray = null;
let isQuitting = false;
let closeToTrayHintShown = false;

const DEFAULT_OCR_PROVIDER = "paddle";
const DEFAULT_MODEL = "deepseek-v4-flash";
const DEFAULT_BASE_URL = "https://api.deepseek.com/v1";

function createDefaultDesktopConfig() {
  return {
    firstRunCompleted: false,
    ocrProvider: DEFAULT_OCR_PROVIDER,
    mineruToken: "",
    paddleToken: "",
    modelApiKey: "",
    model: DEFAULT_MODEL,
    baseUrl: DEFAULT_BASE_URL,
    developerConfig: {},
    closeToTrayHintShown: false,
  };
}

function hasOwn(target, key) {
  return Object.prototype.hasOwnProperty.call(target, key);
}

function normalizeOcrProvider(value) {
  return value === "paddle" ? "paddle" : DEFAULT_OCR_PROVIDER;
}

function normalizeTrimmedString(value, fallback = "") {
  return typeof value === "string" ? value.trim() : fallback;
}

function normalizeDesktopConfig(raw = {}) {
  const defaults = createDefaultDesktopConfig();
  return {
    firstRunCompleted: !!raw.firstRunCompleted,
    ocrProvider: normalizeOcrProvider(raw.ocrProvider),
    mineruToken: normalizeTrimmedString(raw.mineruToken, defaults.mineruToken),
    paddleToken: normalizeTrimmedString(raw.paddleToken, defaults.paddleToken),
    modelApiKey: normalizeTrimmedString(raw.modelApiKey, defaults.modelApiKey),
    model: normalizeTrimmedString(raw.model, defaults.model),
    baseUrl: normalizeTrimmedString(raw.baseUrl, defaults.baseUrl),
    developerConfig: typeof raw.developerConfig === "object" && raw.developerConfig !== null
      ? { ...raw.developerConfig }
      : {},
    closeToTrayHintShown: !!raw.closeToTrayHintShown,
  };
}

function mergeDesktopConfig(currentConfig, payload = {}) {
  const merged = { ...currentConfig };
  const runtimeConfig = typeof payload.runtimeConfig === "object" && payload.runtimeConfig !== null
    ? payload.runtimeConfig
    : {};
  const keys = [
    "ocrProvider",
    "mineruToken",
    "paddleToken",
    "modelApiKey",
    "model",
    "baseUrl",
    "closeToTrayHintShown",
  ];
  for (const key of keys) {
    if (hasOwn(payload, key)) {
      merged[key] = payload[key];
      continue;
    }
    if (hasOwn(runtimeConfig, key)) {
      merged[key] = runtimeConfig[key];
    }
  }
  if (typeof payload.developerConfig === "object" && payload.developerConfig !== null) {
    merged.developerConfig = { ...payload.developerConfig };
  }
  if (hasOwn(payload, "firstRunCompleted")) {
    merged.firstRunCompleted = !!payload.firstRunCompleted;
  }
  return normalizeDesktopConfig(merged);
}

function buildBrowserConfig(config) {
  return {
    ocrProvider: config.ocrProvider || DEFAULT_OCR_PROVIDER,
    mineruToken: config.mineruToken || "",
    paddleToken: config.paddleToken || "",
    modelApiKey: config.modelApiKey || "",
  };
}

function resolveDesktopConfigPath() {
  return path.join(app.getPath("userData"), "desktop-config.json");
}

function loadDesktopConfig() {
  const configPath = resolveDesktopConfigPath();
  if (!fs.existsSync(configPath)) {
    return createDefaultDesktopConfig();
  }
  try {
    const raw = fs.readFileSync(configPath, "utf8");
    return normalizeDesktopConfig(JSON.parse(raw));
  } catch (error) {
    console.error(`[desktop] failed to load desktop config: ${error?.message || error}`);
    return createDefaultDesktopConfig();
  }
}

function saveDesktopConfig(payload = {}) {
  const nextConfig = mergeDesktopConfig(loadDesktopConfig(), payload);
  const configPath = resolveDesktopConfigPath();
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  fs.writeFileSync(configPath, `${JSON.stringify(nextConfig, null, 2)}\n`, "utf8");
  return nextConfig;
}

function buildDesktopRuntimeConfig(config) {
  return {
    apiBase: "http://127.0.0.1:41000",
    xApiKey: DESKTOP_API_KEY,
    ...buildBrowserConfig(config),
    model: config.model || DEFAULT_MODEL,
    baseUrl: config.baseUrl || DEFAULT_BASE_URL,
    developerConfig: config.developerConfig || {},
  };
}

function updateSplashProgress(progress, title, detail) {
  if (!splashWindow || splashWindow.isDestroyed()) {
    return;
  }
  splashWindow.webContents.send("startup-progress", {
    progress,
    title,
    detail,
  });
}

function resolveWindowIcon() {
  if (app.isPackaged) {
    return path.join(__dirname, "assets", "RetainPDF-logo.png");
  }
  return path.join(__dirname, "assets", "RetainPDF-logo.png");
}

function resolveTrayIcon() {
  return resolveWindowIcon();
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
}

function hideMainWindowToTray() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }
  mainWindow.hide();
  maybeShowCloseToTrayHint();
}

function persistCloseToTrayHintShown() {
  const current = loadDesktopConfig();
  saveDesktopConfig({
    ...current,
    closeToTrayHintShown: true,
  });
  closeToTrayHintShown = true;
}

function maybeShowCloseToTrayHint() {
  if (closeToTrayHintShown || !tray) {
    return;
  }
  if (process.platform === "win32" && typeof tray.displayBalloon === "function") {
    tray.displayBalloon({
      iconType: "info",
      title: "RetainPDF is running in the background",
      content: "Window has been hidden to the system tray. Local API remains available. Right-click the tray icon to quit.",
    });
  }
  persistCloseToTrayHintShown();
}

function createTray() {
  if (tray) {
    return tray;
  }
  tray = new Tray(resolveTrayIcon());
  tray.setToolTip("RetainPDF");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: "Show main window",
        click: () => {
          showMainWindow();
        },
      },
      {
        label: "Quit",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]),
  );
  tray.on("click", () => {
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible()) {
      hideMainWindowToTray();
      return;
    }
    showMainWindow();
  });
  tray.on("double-click", () => {
    showMainWindow();
  });
  return tray;
}

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
}

app.on("second-instance", () => {
  showMainWindow();
});

async function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 520,
    height: 360,
    frame: false,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    autoHideMenuBar: true,
    center: true,
    backgroundColor: "#f5f5f7",
    icon: resolveWindowIcon(),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  await splashWindow.loadFile(path.join(__dirname, "splash.html"));
  updateSplashProgress(6, "Preparing runtime environment", "Checking desktop components and local resources");
}

function waitForPort(host, port, timeoutMs) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();

    function tryConnect() {
      const socket = net.connect({ host, port });
      socket.once("connect", () => {
        socket.destroy();
        resolve();
      });
      socket.once("error", () => {
        socket.destroy();
        if (Date.now() - startedAt >= timeoutMs) {
          reject(new Error(`backend did not become ready on ${host}:${port}`));
          return;
        }
        setTimeout(tryConnect, 500);
      });
    }

    tryConnect();
  });
}

function canConnectToPort(host, port, timeoutMs = 800) {
  return new Promise((resolve) => {
    const socket = net.connect({ host, port });
    const done = (result) => {
      socket.destroy();
      resolve(result);
    };
    socket.setTimeout(timeoutMs);
    socket.once("connect", () => done(true));
    socket.once("timeout", () => done(false));
    socket.once("error", () => done(false));
  });
}

function requestJson(url, headers = {}, timeoutMs = 2000) {
  return new Promise((resolve, reject) => {
    const request = http.get(
      url,
      {
        headers,
        timeout: timeoutMs,
      },
      (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode && response.statusCode >= 400) {
            reject(new Error(`http ${response.statusCode}`));
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        });
      },
    );
    request.on("timeout", () => {
      request.destroy(new Error("request timeout"));
    });
    request.on("error", reject);
  });
}

async function canReuseExistingBackend(apiPort) {
  const healthUrl = `http://127.0.0.1:${apiPort}/health`;
  const jobsUrl = `http://127.0.0.1:${apiPort}/api/v1/jobs?limit=1&offset=0`;
  try {
    const healthPayload = await requestJson(healthUrl, {}, 2000);
    if (!(healthPayload && healthPayload.data && healthPayload.data.status === "up")) {
      return false;
    }
    const jobsPayload = await requestJson(jobsUrl, {
      "x-api-key": DESKTOP_API_KEY,
    }, 3000);
    return Array.isArray(jobsPayload?.data?.items);
  } catch (error) {
    console.warn(
      `[desktop] existing backend on :${apiPort} is not reusable: ${error?.message || error}`,
    );
    return false;
  }
}

function resolveBackendRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "backend");
  }
  return path.join(__dirname, "app", "backend");
}

function resolveBackendBinary(backendRoot) {
  const candidates = process.platform === "win32"
    ? [path.join(backendRoot, "bin", "rust_api.exe")]
    : [path.join(backendRoot, "bin", "rust_api")];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return candidates[0];
}

function resolvePythonRuntime(backendRoot) {
  const bundledRoot = path.join(backendRoot, "python");
  const bundledCandidates = process.platform === "win32"
    ? [path.join(bundledRoot, "python.exe")]
    : [
        path.join(bundledRoot, "bin", "python3"),
        path.join(bundledRoot, "bin", "python"),
      ];
  for (const candidate of bundledCandidates) {
    if (fs.existsSync(candidate)) {
      return { command: candidate, bundledHome: bundledRoot };
    }
  }
  if (app.isPackaged) {
    return { command: "", bundledHome: null };
  }
  return { command: "python3", bundledHome: null };
}

function resolveBundledPythonHome(bundledHome) {
  if (!bundledHome || !fs.existsSync(bundledHome)) {
    return "";
  }
  if (process.platform === "darwin") {
    const frameworkHome = path.join(
      bundledHome,
      "Frameworks",
      "Python.framework",
      "Versions",
      "Current",
    );
    if (fs.existsSync(frameworkHome)) {
      return frameworkHome;
    }
  }
  if (!fs.existsSync(path.join(bundledHome, "pyvenv.cfg"))) {
    return bundledHome;
  }
  return "";
}

function buildPythonProbeScript(includeDependencyImports) {
  if (!includeDependencyImports) {
    return [
      "import sys",
      "print(sys.executable, flush=True)",
      "print(f'prefix={sys.prefix} exec_prefix={sys.exec_prefix} base_exec_prefix={sys.base_exec_prefix}', flush=True)",
      "print('python_runtime_startup_check=ok', flush=True)",
    ].join("\n");
  }

  return [
    "import importlib",
    "import sys",
    "print(sys.executable, flush=True)",
    "print(f'prefix={sys.prefix} exec_prefix={sys.exec_prefix} base_exec_prefix={sys.base_exec_prefix}', flush=True)",
    "for module_name in ['_socket', 'socket', 'ssl', 'requests', 'fitz', 'pikepdf', 'PIL', 'urllib3']:",
    "    print(f'importing:{module_name}', flush=True)",
    "    importlib.import_module(module_name)",
    "    print(f'imported:{module_name}', flush=True)",
    "print('python_runtime_import_check=ok', flush=True)",
  ].join("\n");
}

function probePythonRuntime(runtime, options = {}) {
  const {
    timeoutMs = 8000,
    includeDependencyImports = true,
  } = options;
  return new Promise((resolve) => {
    if (!runtime || !runtime.command) {
      resolve({ ok: false, reason: "missing_python_command" });
      return;
    }
    const env = {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      PYTHONUTF8: "1",
    };
    const pythonImportPaths = bundledPythonImportPaths(runtime.bundledHome);
    if (pythonImportPaths.length > 0) {
      env.PYTHONPATH = [
        ...pythonImportPaths,
        process.env.PYTHONPATH || "",
      ].filter(Boolean).join(path.delimiter);
    }
    const bundledPythonHome = resolveBundledPythonHome(runtime.bundledHome);
    if (bundledPythonHome) {
      env.PYTHONHOME = bundledPythonHome;
    } else {
      delete env.PYTHONHOME;
    }
    const child = spawn(
      runtime.command,
      [
        "-c",
        buildPythonProbeScript(includeDependencyImports),
      ],
      {
        env,
        windowsHide: process.platform === "win32",
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.once("error", (error) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        timedOut,
        reason: String(error && error.message ? error.message : error),
        stdout,
        stderr,
      });
    });
    child.once("exit", (code, signal) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve({ ok: true, stdout: stdout.trim(), stderr: stderr.trim() });
        return;
      }
      resolve({
        ok: false,
        timedOut,
        reason: timedOut
          ? `timeout_after_ms=${timeoutMs} exit_code=${code ?? "null"} signal=${signal ?? "null"}`
          : `exit_code=${code ?? "null"} signal=${signal ?? "null"}`,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      });
    });
  });
}

function bundledPythonSitePackages(bundledHome) {
  if (!bundledHome || !fs.existsSync(bundledHome)) {
    return [];
  }
  if (process.platform === "win32") {
    const windowsSitePackages = path.join(bundledHome, "Lib", "site-packages");
    return fs.existsSync(windowsSitePackages) ? [windowsSitePackages] : [];
  }

  const libRoot = path.join(bundledHome, "lib");
  if (!fs.existsSync(libRoot)) {
    return [];
  }

  const matches = [];
  for (const entry of fs.readdirSync(libRoot)) {
    if (!/^python\d+\.\d+$/.test(entry)) {
      continue;
    }
    const sitePackages = path.join(libRoot, entry, "site-packages");
    if (fs.existsSync(sitePackages)) {
      matches.push(sitePackages);
    }
  }
  return matches;
}

function bundledPythonLibDynload(bundledHome) {
  if (!bundledHome || !fs.existsSync(bundledHome) || process.platform !== "darwin") {
    return [];
  }
  const pythonHome = resolveBundledPythonHome(bundledHome);
  const libRoot = pythonHome ? path.join(pythonHome, "lib") : "";
  if (!libRoot || !fs.existsSync(libRoot)) {
    return [];
  }

  const matches = [];
  for (const entry of fs.readdirSync(libRoot)) {
    if (!/^python\d+\.\d+$/.test(entry)) {
      continue;
    }
    const libDynload = path.join(libRoot, entry, "lib-dynload");
    if (fs.existsSync(libDynload)) {
      matches.push(libDynload);
    }
  }
  return matches;
}

function bundledPythonImportPaths(bundledHome) {
  return [
    ...bundledPythonSitePackages(bundledHome),
    ...bundledPythonLibDynload(bundledHome),
  ];
}

function resolveTypstBinary(backendRoot) {
  const bundledCandidates = process.platform === "win32"
    ? [path.join(backendRoot, "typst", "bin", "typst.exe")]
    : [path.join(backendRoot, "typst", "bin", "typst")];
  const candidates = app.isPackaged
    ? bundledCandidates
    : [
        ...bundledCandidates,
        "/usr/local/bin/typst",
        "/opt/homebrew/bin/typst",
      ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return "";
}

async function startBundledBackend() {
  updateSplashProgress(18, "Checking runtime files", "Validating backend, Python, and script resources");
  const backendRoot = resolveBackendRoot();
  const backendBin = resolveBackendBinary(backendRoot);
  let pythonRuntime = resolvePythonRuntime(backendRoot);
  const scriptsDir = path.join(backendRoot, "scripts");
  const typstBin = resolveTypstBinary(backendRoot);
  const bundledFontPath = path.join(backendRoot, "fonts", "SourceHanSerifSC-Regular.otf");
  const bundledTitleBoldFontPath = path.join(backendRoot, "fonts", "SourceHanSerifSC-Bold.otf");
  const bundledTypstFontDir = path.join(backendRoot, "fonts");
  const dataRoot = path.join(app.getPath("userData"), "data");
  const rustApiRoot = path.join(dataRoot, "rust_api");
  const typstPackagePath = path.join(backendRoot, "typst-packages");
  const typstPackageCachePath = path.join(dataRoot, "typst-package-cache");
  const apiPort = 41000;
  const simplePort = 42000;

  if (!fs.existsSync(backendBin)) {
    throw new Error(`missing bundled backend binary: ${backendBin}`);
  }
  if (!pythonRuntime.command) {
    throw new Error("missing python runtime");
  }
  if (!fs.existsSync(scriptsDir)) {
    throw new Error(`missing bundled scripts directory: ${scriptsDir}`);
  }
  if (app.isPackaged && !typstBin) {
    throw new Error(`missing bundled typst runtime under ${path.join(backendRoot, "typst")}`);
  }

  if (process.platform === "darwin") {
    const startupProbe = await probePythonRuntime(pythonRuntime, {
      timeoutMs: app.isPackaged ? 10000 : 8000,
      includeDependencyImports: false,
    });
    if (!startupProbe.ok && pythonRuntime.bundledHome) {
      if (app.isPackaged) {
        throw new Error(
          [
            `packaged macOS bundled python startup probe failed: ${startupProbe.reason}`,
            startupProbe.stderr || startupProbe.stdout || "",
          ].filter(Boolean).join("\n"),
        );
      }
      console.warn(
        `[desktop] bundled mac python startup probe failed, fallback to system python: ${startupProbe.reason}\n${startupProbe.stderr || ""}`.trim(),
      );
      updateSplashProgress(26, "Checking Python runtime", "Built-in Python unavailable, falling back to system Python");
      const fallbackRuntime = { command: "python3", bundledHome: null };
      const fallbackProbe = await probePythonRuntime(fallbackRuntime, {
        timeoutMs: 10000,
        includeDependencyImports: false,
      });
      if (fallbackProbe.ok) {
        pythonRuntime = fallbackRuntime;
      } else {
        throw new Error(
          `macOS Python runtime startup probe failed; bundled=${startupProbe.reason}; fallback=${fallbackProbe.reason}`,
        );
      }
    }

    const dependencyProbe = await probePythonRuntime(pythonRuntime, {
      timeoutMs: app.isPackaged ? 30000 : 8000,
      includeDependencyImports: true,
    });
    if (!dependencyProbe.ok) {
      if (app.isPackaged && pythonRuntime.bundledHome && dependencyProbe.timedOut) {
        console.warn(
          [
            `[desktop] packaged mac python dependency probe timed out; continuing to backend startup: ${dependencyProbe.reason}`,
            dependencyProbe.stderr || dependencyProbe.stdout || "",
          ].filter(Boolean).join("\n"),
        );
        updateSplashProgress(26, "Checking Python runtime", "Built-in Python starting slowly, continuing with local service");
      } else if (pythonRuntime.bundledHome && !app.isPackaged) {
        console.warn(
          `[desktop] bundled mac python dependency probe failed, fallback to system python: ${dependencyProbe.reason}\n${dependencyProbe.stderr || ""}`.trim(),
        );
        updateSplashProgress(26, "Checking Python runtime", "Built-in Python unavailable, falling back to system Python");
        const fallbackRuntime = { command: "python3", bundledHome: null };
        const fallbackProbe = await probePythonRuntime(fallbackRuntime, {
          timeoutMs: 10000,
          includeDependencyImports: true,
        });
        if (fallbackProbe.ok) {
          pythonRuntime = fallbackRuntime;
        } else {
          throw new Error(
            `macOS Python runtime import probe failed; bundled=${dependencyProbe.reason}; fallback=${fallbackProbe.reason}`,
          );
        }
      } else {
        throw new Error(
          [
            `packaged macOS bundled python probe failed: ${dependencyProbe.reason}`,
            dependencyProbe.stderr || dependencyProbe.stdout || "",
          ].filter(Boolean).join("\n"),
        );
      }
    }
  }
  if (app.isPackaged && !pythonRuntime.bundledHome) {
    throw new Error(
      `missing bundled python runtime under ${path.join(backendRoot, "python")}`,
    );
  }

  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(rustApiRoot, { recursive: true });
  fs.mkdirSync(typstPackageCachePath, { recursive: true });
  updateSplashProgress(34, "Preparing working directory", "Initializing local data directory");

  const apiPortBusy = await canConnectToPort("127.0.0.1", apiPort);
  if (apiPortBusy) {
    if (await canReuseExistingBackend(apiPort)) {
      usingExternalBackend = true;
      updateSplashProgress(52, "Existing local service detected", "Desktop app will reuse the current backend directly");
      await waitForPort("127.0.0.1", apiPort, 5000);
      updateSplashProgress(92, "Local service is ready", "Loading main interface");
      return;
    }
    throw new Error(
      `Port ${apiPort} is already occupied by another process and is not a reusable RetainPDF backend. Please close the occupying process before starting the desktop app.`,
    );
  }

  const simplePortBusy = await canConnectToPort("127.0.0.1", simplePort);
  if (simplePortBusy) {
    throw new Error(`Port ${simplePort} is already occupied by another process. Please free it before starting the desktop app.`);
  }

  const env = {
    ...process.env,
    RUST_API_BIND_HOST: "127.0.0.1",
    RUST_API_PORT: String(apiPort),
    RUST_API_SIMPLE_PORT: String(simplePort),
    RUST_API_KEYS: DESKTOP_API_KEY,
    RUST_API_DATA_ROOT: dataRoot,
    RUST_API_ROOT: rustApiRoot,
    RUST_API_NORMAL_MAX_BYTES: String(200 * 1024 * 1024),
    RUST_API_NORMAL_MAX_PAGES: "600",
    RUST_API_PROJECT_ROOT: backendRoot,
    RUST_API_SCRIPTS_DIR: scriptsDir,
    PYTHON_BIN: pythonRuntime.command,
    PYTHONPATH: [
      scriptsDir,
      ...bundledPythonImportPaths(pythonRuntime.bundledHome),
      process.env.PYTHONPATH || "",
    ].filter(Boolean).join(path.delimiter),
    PYTHONUNBUFFERED: "1",
    PYTHONUTF8: "1",
    PYTHONDONTWRITEBYTECODE: "1",
    PDF_TRANSLATOR_TRUST_ENV_PROXY: "1",
    RETAIN_PDF_FONT_PATH: bundledFontPath,
    RETAIN_PDF_TITLE_BOLD_FONT_PATH: bundledTitleBoldFontPath,
    RETAIN_PDF_TYPST_FONT_DIRS: bundledTypstFontDir,
    RETAIN_PDF_TYPST_FONT_FAMILY: "Source Han Serif SC",
    TYPST_PACKAGE_CACHE_PATH: typstPackageCachePath,
  };
  if (fs.existsSync(typstPackagePath)) {
    env.TYPST_PACKAGE_PATH = typstPackagePath;
  }
  const bundledPythonHome = resolveBundledPythonHome(pythonRuntime.bundledHome);
  if (bundledPythonHome) {
    env.PYTHONHOME = bundledPythonHome;
  } else {
    delete env.PYTHONHOME;
  }
  if (fs.existsSync(typstBin)) {
    env.TYPST_BIN = typstBin;
  }

  updateSplashProgress(52, "Starting local service", "Rust API and Python worker are starting");
  backendChild = spawn(backendBin, [], {
    cwd: backendRoot,
    env,
    windowsHide: process.platform === "win32",
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendChild.stdout.on("data", (chunk) => {
    process.stdout.write(`[rust_api] ${chunk}`);
  });
  backendChild.stderr.on("data", (chunk) => {
    process.stderr.write(`[rust_api] ${chunk}`);
  });

  backendChild.once("exit", (code, signal) => {
    backendChild = null;
    if (backendStopping) {
      return;
    }
    const detail = `code=${code ?? "null"} signal=${signal ?? "null"}`;
    dialog.showErrorBox("Rust API worker crashed", detail);
  });

  let waitingProgress = 58;
  const waitingTimer = setInterval(() => {
    waitingProgress = Math.min(waitingProgress + 3, 88);
    updateSplashProgress(
      waitingProgress,
      "Connecting to local service",
      "First startup may be slower, please wait",
    );
  }, 500);
  const backendReadyTimeoutMs = process.platform === "darwin" && app.isPackaged ? 60000 : 30000;
  await waitForPort("127.0.0.1", apiPort, backendReadyTimeoutMs);
  clearInterval(waitingTimer);
  updateSplashProgress(92, "Local service is ready", "Loading main interface");
}

function createWindow() {
  const frontendRoot = resolveFrontendRoot();

  mainWindow = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1200,
    minHeight: 760,
    autoHideMenuBar: true,
    show: false,
    icon: resolveWindowIcon(),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(frontendRoot, "index.html"));

  mainWindow.on("close", (event) => {
    if (isQuitting) {
      return;
    }
    event.preventDefault();
    hideMainWindowToTray();
  });

  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    console.log(
      `[desktop][renderer][level=${level}] ${sourceId || "unknown"}:${line || 0} ${message || ""}`,
    );
  });

  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    const detail = `code=${errorCode} url=${validatedURL || "unknown"} error=${errorDescription || "unknown"}`;
    console.error(`[desktop] renderer load failed: ${detail}`);
    dialog.showErrorBox("RetainPDF page load failed", detail);
  });

  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    const detail = `reason=${details?.reason || "unknown"} exitCode=${details?.exitCode ?? "unknown"}`;
    console.error(`[desktop] renderer process gone: ${detail}`);
    dialog.showErrorBox("RetainPDF rendering process exited abnormally", detail);
  });

  mainWindow.webContents.once("did-finish-load", () => {
    updateSplashProgress(100, "Preparation complete", "Entering main interface");
    mainWindow.show();
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function resolveFrontendRoot() {
  const generatedFrontendRoot = path.join(__dirname, "app", "frontend");
  if (app.isPackaged) {
    return generatedFrontendRoot;
  }
  if (fs.existsSync(path.join(generatedFrontendRoot, "index.html"))) {
    return generatedFrontendRoot;
  }
  const sourceFrontendRoot = path.resolve(__dirname, "..", "frontend");
  if (fs.existsSync(path.join(sourceFrontendRoot, "index.html"))) {
    return sourceFrontendRoot;
  }
  return generatedFrontendRoot;
}

app.whenReady().then(() => {
  closeToTrayHintShown = loadDesktopConfig().closeToTrayHintShown;
  createSplashWindow()
    .then(() => startBundledBackend())
    .then(() => {
      createTray();
      createWindow();
      app.on("activate", () => {
        if (!mainWindow || mainWindow.isDestroyed()) {
          createWindow();
          return;
        }
        showMainWindow();
      });
    })
    .catch((error) => {
      dialog.showErrorBox("RetainPDF startup failed", String(error && error.message ? error.message : error));
      app.quit();
    });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin" && isQuitting) {
    app.quit();
  }
});

app.on("before-quit", () => {
  isQuitting = true;
  if (!usingExternalBackend && backendChild && !backendChild.killed) {
    backendStopping = true;
    backendChild.kill();
  }
});

ipcMain.handle("desktop:invoke", async (_event, command, args = {}) => {
  switch (command) {
    case "load_desktop_config": {
      const config = loadDesktopConfig();
      return {
        firstRunCompleted: config.firstRunCompleted,
        closeToTrayHintShown: config.closeToTrayHintShown,
        browserConfig: buildBrowserConfig(config),
        developerConfig: config.developerConfig || {},
        runtimeConfig: buildDesktopRuntimeConfig(config),
      };
    }
    case "save_desktop_config": {
      const config = saveDesktopConfig(args?.payload || {});
      return {
        firstRunCompleted: config.firstRunCompleted,
        closeToTrayHintShown: config.closeToTrayHintShown,
        browserConfig: buildBrowserConfig(config),
        developerConfig: config.developerConfig || {},
        runtimeConfig: buildDesktopRuntimeConfig(config),
      };
    }
    case "open_output_directory": {
      const outputDir = path.join(app.getPath("userData"), "data", "jobs");
      fs.mkdirSync(outputDir, { recursive: true });
      const result = await shell.openPath(outputDir);
      if (result) {
        throw new Error(result);
      }
      return { ok: true, outputDir };
    }
    default:
      throw new Error(`unsupported desktop command: ${command}`);
  }
});

ipcMain.on("desktop:renderer-issue", (_event, payload = {}) => {
  const type = payload?.type || "unknown";
  const message = payload?.message || "unknown renderer issue";
  const filename = payload?.filename || "";
  const lineno = payload?.lineno || 0;
  const colno = payload?.colno || 0;
  console.error(
    `[desktop][renderer-issue] type=${type} file=${filename} line=${lineno} col=${colno} message=${message}`,
  );
});
