import { $ } from "../../dom.js";
import { buildJobsEndpoint } from "../../network.js";
import { getOcrProviderDefinition } from "../../provider-config.js";

export function mountAppActionsFeature({
  state,
  apiBase,
  apiPrefix,
  buildApiEndpoint,
  isMockMode,
  openSetupDialog,
  renderJob,
  setText,
  submitJson,
  submitJobRequest,
  saveDesktopConfig,
  setDesktopBusy,
  openDesktopOutputDirectory,
  resetUploadedFile,
  currentWorkflow,
  workflowNeedsCredentials,
  workflowNeedsUpload,
  currentRenderSourceJobId,
  collectRunPayload,
  getBrowserCredentialsFeature,
  getJobRuntimeFeature,
  onDesktopConfigSaved,
}) {
  function isMissingUploadError(error) {
    const message = `${error?.message || error || ""}`;
    return message.includes("upload not found");
  }

  function handleMissingUploadError() {
    state.uploadId = "";
    state.uploadedFileName = "";
    state.uploadedPageCount = 0;
    state.uploadedBytes = 0;
    resetUploadedFile?.();
    setText("error-box", "The uploaded file has expired. Please re-upload the PDF before submitting.");
  }

  async function submitForm(event) {
    event.preventDefault();
    const workflow = currentWorkflow();
    if (isMockMode()) {
      $("submit-btn").disabled = true;
      setText("error-box", "-");
      try {
        const payload = await submitJobRequest(apiPrefix, { workflow, source: {}, mock: true });
        state.currentJobStartedAt = new Date().toISOString();
        state.currentJobFinishedAt = "";
        renderJob(payload);
        getJobRuntimeFeature()?.startPolling(payload.job_id);
      } catch (err) {
        setText("error-box", err.message);
      } finally {
        $("submit-btn").disabled = false;
      }
      return;
    }
    if (state.desktopMode && !state.desktopConfigured && workflowNeedsCredentials(workflow)) {
      openSetupDialog();
      setText("error-box", "Please complete the initial configuration first.");
      return;
    }
    if (workflowNeedsUpload(workflow) && !state.uploadId) {
      setText("error-box", "Please select and upload a PDF file first");
      return;
    }
    if (!workflowNeedsUpload(workflow) && !currentRenderSourceJobId()) {
      setText("error-box", "Please enter the Render Source Job ID in developer settings first.");
      return;
    }
    if (workflowNeedsCredentials(workflow) && !(await getBrowserCredentialsFeature()?.ensureOcrCredentialsReady({
      onMissingToken: () => {
        setText("error-box", "Please fill in the current OCR Provider credentials first.");
        if (!state.desktopMode) {
          getBrowserCredentialsFeature()?.openBrowserCredentialsDialog();
        }
      },
      onInvalidToken: (result) => {
        setText("error-box", result.summary || "OCR Provider credential validation failed.");
        if (!state.desktopMode) {
          getBrowserCredentialsFeature()?.openBrowserCredentialsDialog();
        }
      },
    }))) {
      return;
    }

    $("submit-btn").disabled = true;
    setText("error-box", "-");

    try {
      const runPayload = collectRunPayload();
      const payload = await submitJobRequest(apiPrefix, runPayload);
      state.currentJobStartedAt = new Date().toISOString();
      state.currentJobFinishedAt = "";
      renderJob(payload);
      getJobRuntimeFeature()?.startPolling(payload.job_id);
    } catch (err) {
      if (isMissingUploadError(err)) {
        handleMissingUploadError();
        return;
      }
      setText("error-box", err.message);
    } finally {
      $("submit-btn").disabled = false;
    }
  }

  async function checkApiConnectivity() {
    try {
      const resp = await fetch(buildApiEndpoint("", "health"));
      if (!resp.ok) {
        throw new Error(`health ${resp.status}`);
      }
      return true;
    } catch (_err) {
      const message = `Frontend cannot connect to backend. API Base: ${apiBase()}. Please confirm the local service is running and try again.`;
      setText("error-box", message);
      throw new Error(message);
    }
  }

  async function handleOpenOutputDir() {
    try {
      await openDesktopOutputDirectory();
    } catch (err) {
      setText("error-box", err.message || String(err));
    }
  }

  return {
    checkApiConnectivity,
    handleOpenOutputDir,
    submitForm,
  };
}
