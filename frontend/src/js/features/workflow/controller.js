import { $ } from "../../dom.js";
import { DEFAULT_FILE_LABEL } from "../../constants.js";
import { getOcrProviderDefinition, normalizeOcrProvider } from "../../provider-config.js";

export function mountWorkflowFeature({
  state,
  isMockMode,
  saveDeveloperStoredConfig,
  defaultModelName,
  defaultModelBaseUrl,
  defaultMineruToken,
  defaultPaddleToken,
  defaultOcrProvider,
  defaultModelApiKey,
  normalizeWorkflow,
  normalizeMathMode,
  constants,
  currentPageRanges,
  renderPageRangeSummary,
  getBrowserCredentialsFeature,
}) {
  const {
    DEFAULT_WORKERS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CLASSIFY_BATCH_SIZE,
    DEFAULT_COMPILE_WORKERS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MODEL_VERSION,
    DEFAULT_LANGUAGE,
    DEFAULT_MODE,
    DEFAULT_RULE_PROFILE,
    DEFAULT_RENDER_MODE,
    WORKFLOW_BOOK,
    WORKFLOW_TRANSLATE,
    WORKFLOW_RENDER,
  } = constants;

  let refreshSubmitControlsRef = null;
  let applyWorkflowModeRef = null;
  const hasAppliedPageRange = () => workflowNeedsUpload() && `${state.appliedPageRange || ""}`.trim().length > 0;

  function developerConfigWithDefaults() {
    const saved = state.developerConfig || {};
    return {
      workflow: normalizeWorkflow(saved.workflow),
      renderSourceJobId: `${saved.renderSourceJobId || ""}`.trim(),
      mathMode: normalizeMathMode(saved.mathMode),
      model: saved.model || defaultModelName(),
      baseUrl: saved.baseUrl || defaultModelBaseUrl(),
      workers: Number(saved.workers || DEFAULT_WORKERS),
      batchSize: Number(saved.batchSize || DEFAULT_BATCH_SIZE),
      classifyBatchSize: Number(saved.classifyBatchSize || DEFAULT_CLASSIFY_BATCH_SIZE),
      compileWorkers: Number(saved.compileWorkers || DEFAULT_COMPILE_WORKERS),
      timeoutSeconds: Number(saved.timeoutSeconds || DEFAULT_TIMEOUT_SECONDS),
      translateTitles: saved.translateTitles !== false,
    };
  }

  function syncDeveloperDialogFromState() {
    const config = developerConfigWithDefaults();
    $("developer-workflow").value = config.workflow;
    $("developer-render-source-job-id").value = config.renderSourceJobId;
    $("developer-model").value = config.model;
    $("developer-base-url").value = config.baseUrl;
    $("developer-workers").value = `${config.workers}`;
    $("developer-batch-size").value = `${config.batchSize}`;
    $("developer-classify-batch-size").value = `${config.classifyBatchSize}`;
    $("developer-compile-workers").value = `${config.compileWorkers}`;
    $("developer-timeout-seconds").value = `${config.timeoutSeconds}`;
    updateDeveloperWorkflowFormState();
  }

  function currentWorkflow() {
    return developerConfigWithDefaults().workflow;
  }

  function currentRenderSourceJobId() {
    return developerConfigWithDefaults().renderSourceJobId;
  }

  function workflowNeedsUpload(workflow = currentWorkflow()) {
    return workflow !== WORKFLOW_RENDER;
  }

  function workflowNeedsCredentials(workflow = currentWorkflow()) {
    return workflow !== WORKFLOW_RENDER;
  }

  function workflowUsesRenderStage(workflow = currentWorkflow()) {
    return workflow === WORKFLOW_BOOK || workflow === WORKFLOW_RENDER;
  }

  function workflowSubmitLabel(workflow = currentWorkflow()) {
    switch (workflow) {
      case WORKFLOW_RENDER:
        return "Start Rendering";
      case WORKFLOW_TRANSLATE:
        return "Start Translation";
      case WORKFLOW_BOOK:
        return hasAppliedPageRange() ? "Start Translation" : "Full Translation";
      default:
        return hasAppliedPageRange() ? "Start Translation" : "Full Translation";
    }
  }

  function workflowHeadline(workflow = currentWorkflow()) {
    switch (workflow) {
      case WORKFLOW_RENDER:
        return "Current workflow will reuse existing task artifacts to regenerate PDF.";
      case WORKFLOW_TRANSLATE:
        return "OCR and text translation will be performed after upload, without PDF rendering.";
      default:
        return "OCR, translation, and PDF rendering will be performed after upload.";
    }
  }

  function updateDeveloperWorkflowFormState() {
    const workflow = normalizeWorkflow($("developer-workflow")?.value);
    const renderWrap = $("developer-render-source-wrap");
    const note = $("developer-workflow-note");
    renderWrap?.classList.toggle("hidden", workflow !== WORKFLOW_RENDER);
    if (note) {
      note.textContent = workflow === WORKFLOW_RENDER
        ? "render skips OCR and translation, directly reusing existing task artifacts to re-render the PDF."
        : workflow === WORKFLOW_TRANSLATE
          ? "translate performs OCR and translation but does not enter final PDF rendering."
          : "book runs OCR, translation, and PDF rendering in full.";
    }
  }

  function refreshSubmitControls() {
    const workflow = currentWorkflow();
    const showPageRangeButton = workflowNeedsUpload(workflow) && !hasAppliedPageRange();
    if (isMockMode()) {
      $("submit-btn").disabled = false;
      $("submit-btn").textContent = workflowSubmitLabel(workflow);
      $("upload-action-slot")?.classList.remove("hidden");
      $("page-range-btn")?.classList.toggle("hidden", !showPageRangeButton);
      return;
    }
    const needsUpload = workflowNeedsUpload(workflow);
    const needsCredentials = workflowNeedsCredentials(workflow);
    const credentialsMissing = !state.desktopMode
      && needsCredentials
      && !getBrowserCredentialsFeature()?.hasBrowserCredentials();
    const renderReady = Boolean(currentRenderSourceJobId());
    const uploadReady = Boolean(state.uploadId);
    const canSubmit = needsUpload ? uploadReady : renderReady;
    $("submit-btn").disabled = credentialsMissing || !canSubmit;
    $("submit-btn").textContent = workflowSubmitLabel(workflow);
    $("upload-action-slot")?.classList.toggle("hidden", credentialsMissing || (needsUpload ? !uploadReady : false));
    $("page-range-btn")?.classList.toggle("hidden", !showPageRangeButton);
  }

  function updateCredentialGate() {
    if (isMockMode()) {
      return;
    }
    getBrowserCredentialsFeature()?.updateCredentialGate({
      workflowNeedsCredentials: () => workflowNeedsCredentials(currentWorkflow()),
      workflowNeedsUpload: () => workflowNeedsUpload(currentWorkflow()),
      refreshSubmitControls,
    });
  }

  function applyWorkflowMode() {
    const workflow = currentWorkflow();
    const fileInput = $("file");
    const tile = fileInput?.closest(".upload-tile");
    const uploadGlyph = $("upload-glyph");
    const fileLabel = $("file-label");
    const uploadHelp = $("upload-help");
    const uploadMeta = document.querySelector(".upload-meta");
    const uploadStatus = $("upload-status");
    const needsUpload = workflowNeedsUpload(workflow);
    if (isMockMode()) {
      if (fileInput) {
        fileInput.disabled = true;
      }
      tile?.classList.add("is-locked");
      uploadGlyph?.classList.add("hidden");
      uploadMeta?.classList.add("hidden");
      if (fileLabel) {
        fileLabel.textContent = "Mock Mode";
        fileLabel.title = "";
        fileLabel.classList.remove("hidden");
      }
      if (uploadHelp) {
        uploadHelp.textContent = `Mock mode active: ${new URLSearchParams(window.location.search).get("mock") || "running"}. No files will be uploaded and no real backend will be requested.`;
        uploadHelp.classList.remove("hidden");
      }
      if (uploadStatus) {
        uploadStatus.textContent = "Mock mode enabled, click Start Translation to proceed.";
        uploadStatus.classList.remove("hidden");
      }
      renderPageRangeSummary();
      refreshSubmitControls();
      updateCredentialGate();
      return;
    }
    if (fileInput) {
      fileInput.disabled = !needsUpload;
    }
    tile?.classList.toggle("is-locked", !needsUpload);
    uploadGlyph?.classList.toggle("hidden", !needsUpload);
    uploadMeta?.classList.toggle("hidden", !needsUpload);
    if (fileLabel && !state.uploadId) {
      fileLabel.textContent = needsUpload ? DEFAULT_FILE_LABEL : "Reuse existing task artifacts";
      fileLabel.title = "";
      fileLabel.classList.remove("hidden");
    }
    if (uploadHelp) {
      uploadHelp.textContent = workflowHeadline(workflow);
      uploadHelp.classList.remove("hidden");
    }
    if (!needsUpload && uploadStatus) {
      const renderSourceJobId = currentRenderSourceJobId();
      uploadStatus.textContent = renderSourceJobId
        ? `Will reuse task: ${renderSourceJobId}`
        : "Please enter the Render Source Job ID in developer settings first.";
      uploadStatus.classList.remove("hidden");
    } else if (!state.uploadId) {
      uploadStatus?.classList.add("hidden");
    }
    renderPageRangeSummary();
    refreshSubmitControls();
    updateCredentialGate();
  }

  function saveDeveloperDialog() {
    const currentConfig = developerConfigWithDefaults();
    state.developerConfig = {
      workflow: normalizeWorkflow($("developer-workflow")?.value),
      renderSourceJobId: $("developer-render-source-job-id")?.value?.trim() || "",
      mathMode: currentConfig.mathMode,
      model: $("developer-model")?.value?.trim() || defaultModelName(),
      baseUrl: $("developer-base-url")?.value?.trim() || defaultModelBaseUrl(),
      workers: Number($("developer-workers")?.value || DEFAULT_WORKERS),
      batchSize: Number($("developer-batch-size")?.value || DEFAULT_BATCH_SIZE),
      classifyBatchSize: Number($("developer-classify-batch-size")?.value || DEFAULT_CLASSIFY_BATCH_SIZE),
      compileWorkers: Number($("developer-compile-workers")?.value || DEFAULT_COMPILE_WORKERS),
      timeoutSeconds: Number($("developer-timeout-seconds")?.value || DEFAULT_TIMEOUT_SECONDS),
      translateTitles: currentConfig.translateTitles,
    };
    void saveDeveloperStoredConfig(state.developerConfig);
    applyWorkflowMode();
    $("developer-dialog")?.close();
  }

  function resetDeveloperDialog() {
    state.developerConfig = {};
    void saveDeveloperStoredConfig({});
    syncDeveloperDialogFromState();
    applyWorkflowMode();
  }

  function buildSourcePayload(workflow, developerConfig) {
    return workflowNeedsUpload(workflow)
      ? { upload_id: state.uploadId }
      : { artifact_job_id: developerConfig.renderSourceJobId };
  }

  function buildOcrPayload(pageRanges) {
    const provider = normalizeOcrProvider($("ocr_provider")?.value || defaultOcrProvider());
    const definition = getOcrProviderDefinition(provider);
    const token = definition.id === "paddle"
      ? ($("paddle_token")?.value || defaultPaddleToken())
      : ($("mineru_token")?.value || defaultMineruToken());
    return {
      provider,
      [definition.tokenField]: token,
      model_version: DEFAULT_MODEL_VERSION,
      language: DEFAULT_LANGUAGE,
      page_ranges: pageRanges,
    };
  }

  function buildTranslationPayload(developerConfig) {
    return {
      mode: DEFAULT_MODE,
      math_mode: developerConfig.mathMode,
      model: developerConfig.model,
      base_url: developerConfig.baseUrl,
      api_key: $("api_key").value || defaultModelApiKey(),
      workers: developerConfig.workers,
      batch_size: developerConfig.batchSize,
      classify_batch_size: developerConfig.classifyBatchSize,
      rule_profile_name: DEFAULT_RULE_PROFILE,
      custom_rules_text: "",
      glossary_id: "",
      glossary_entries: [],
      skip_title_translation: !developerConfig.translateTitles,
    };
  }

  function buildRenderPayload(developerConfig) {
    return {
      render_mode: DEFAULT_RENDER_MODE,
      compile_workers: developerConfig.compileWorkers,
    };
  }

  function collectRunPayload() {
    const pageRanges = currentPageRanges();
    const developerConfig = developerConfigWithDefaults();
    const workflow = developerConfig.workflow;
    const payload = {
      workflow,
      source: buildSourcePayload(workflow, developerConfig),
      runtime: {
        job_id: "",
        timeout_seconds: developerConfig.timeoutSeconds,
      },
    };
    if (workflow === WORKFLOW_BOOK || workflow === WORKFLOW_TRANSLATE) {
      payload.ocr = buildOcrPayload(pageRanges);
      payload.translation = buildTranslationPayload(developerConfig);
    }
    if (workflowUsesRenderStage(workflow)) {
      payload.render = buildRenderPayload(developerConfig);
    }
    return payload;
  }

  return {
    applyWorkflowMode,
    collectRunPayload,
    currentRenderSourceJobId,
    currentWorkflow,
    developerConfigWithDefaults,
    refreshSubmitControls,
    resetDeveloperDialog,
    saveDeveloperDialog,
    syncDeveloperDialogFromState,
    updateCredentialGate,
    updateDeveloperWorkflowFormState,
    workflowNeedsCredentials,
    workflowNeedsUpload,
  };
}
