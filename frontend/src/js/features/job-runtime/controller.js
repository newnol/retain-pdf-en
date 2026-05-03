import { $ } from "../../dom.js";
import { normalizeJobPayload, summarizeStatus, isTerminalStatus } from "../../job.js";

export function mountJobRuntimeFeature({
  state,
  apiPrefix,
  buildJobDetailEndpoint,
  fetchJobPayload,
  fetchJobEvents,
  fetchJobArtifactsManifest,
  submitJson,
  renderJob,
  setText,
  setWorkflowSections,
  resetUploadProgress,
  resetUploadedFile,
  applyWorkflowMode,
  clearPageRanges,
  updateJobWarning,
  activateDetailTab,
  onReaderDialogSync,
  onReaderDialogClose,
}) {
  const JOB_EVENTS_PAGE_SIZE = 200;
  const JOB_POLL_INTERVAL_MS = 1000;
  const JOB_EVENTS_REFRESH_MS = 3000;
  const JOB_MANIFEST_REFRESH_MS = 5000;

  function stopPolling() {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
    }
  }

  async function fetchAllJobEvents(jobId) {
    const items = [];
    let offset = 0;
    while (true) {
      const payload = await fetchJobEvents(jobId, apiPrefix, JOB_EVENTS_PAGE_SIZE, offset);
      const batch = Array.isArray(payload?.items) ? payload.items : [];
      items.push(...batch);
      if (batch.length < JOB_EVENTS_PAGE_SIZE) {
        return {
          ...payload,
          items,
          offset: 0,
          limit: items.length,
        };
      }
      offset += batch.length;
    }
  }

  function cachedEventsFor(jobId) {
    return state.currentJobEventsJobId === jobId ? state.currentJobEvents : null;
  }

  function cachedManifestFor(jobId) {
    return state.currentJobManifestJobId === jobId ? state.currentJobManifest : null;
  }

  function shouldRefreshSecondary(lastFetchedAt, refreshMs, force) {
    if (force) {
      return true;
    }
    if (!Number.isFinite(lastFetchedAt) || lastFetchedAt <= 0) {
      return true;
    }
    return (Date.now() - lastFetchedAt) >= refreshMs;
  }

  async function fetchJob(jobId) {
    const payload = await fetchJobPayload(jobId, apiPrefix);
    const cachedEvents = cachedEventsFor(jobId);
    const cachedManifest = cachedManifestFor(jobId);
    renderJob(payload, cachedEvents, cachedManifest);
    if ($("reader-dialog")?.open) {
      onReaderDialogSync?.();
    }
    const job = normalizeJobPayload(payload);
    const terminal = isTerminalStatus(job.status);
    if (isTerminalStatus(job.status)) {
      stopPolling();
    }
    if (shouldRefreshSecondary(state.currentJobEventsFetchedAt, JOB_EVENTS_REFRESH_MS, terminal || !cachedEvents)) {
      void fetchAllJobEvents(jobId)
        .then((eventsPayload) => {
          if (state.currentJobId !== jobId) {
            return;
          }
          state.currentJobEvents = eventsPayload;
          state.currentJobEventsJobId = jobId;
          state.currentJobEventsFetchedAt = Date.now();
          renderJob(payload, eventsPayload, cachedManifestFor(jobId));
        })
        .catch(() => {
          // Event stream is secondary; keep main status usable even if events fail.
        });
    }
    if (shouldRefreshSecondary(state.currentJobManifestFetchedAt, JOB_MANIFEST_REFRESH_MS, terminal || !cachedManifest)) {
      void fetchJobArtifactsManifest(jobId, apiPrefix)
        .then((manifestPayload) => {
          if (state.currentJobId !== jobId) {
            return;
          }
          state.currentJobManifest = manifestPayload;
          state.currentJobManifestJobId = jobId;
          state.currentJobManifestFetchedAt = Date.now();
          renderJob(payload, cachedEventsFor(jobId), manifestPayload);
        })
        .catch(() => {
          // Artifacts manifest is secondary; keep main status usable even if manifest fails.
        });
    }
  }

  function startPolling(jobId) {
    stopPolling();
    state.currentJobId = jobId;
    state.currentJobEvents = null;
    state.currentJobEventsJobId = "";
    state.currentJobEventsFetchedAt = 0;
    state.currentJobManifest = null;
    state.currentJobManifestJobId = "";
    state.currentJobManifestFetchedAt = 0;
    if (!state.currentJobStartedAt) {
      state.currentJobStartedAt = new Date().toISOString();
    }
    setWorkflowSections({ job_id: jobId, status: "queued" });
    fetchJob(jobId).catch((err) => {
      setText("error-box", err.message);
    });
    state.timer = setInterval(() => {
      fetchJob(jobId).catch((err) => {
        setText("error-box", err.message);
      });
    }, JOB_POLL_INTERVAL_MS);
  }

  function returnToHome() {
    stopPolling();
    $("status-detail-dialog")?.close();
    onReaderDialogClose?.();
    $("page-range-dialog")?.close();
    state.currentJobId = "";
    state.currentJobSnapshot = null;
    state.currentJobManifest = null;
    state.currentJobManifestJobId = "";
    state.currentJobManifestFetchedAt = 0;
    state.currentJobEvents = null;
    state.currentJobEventsJobId = "";
    state.currentJobEventsFetchedAt = 0;
    state.currentJobStartedAt = "";
    state.currentJobFinishedAt = "";
    state.appliedPageRange = "";
    setWorkflowSections(null);
    resetUploadProgress();
    resetUploadedFile();
    applyWorkflowMode();
    setText("job-summary", summarizeStatus("idle"));
    setText("job-stage-detail", "-");
    setText("job-id", "-");
    setText("query-job-duration", "-");
    setText("job-finished-at", "-");
    clearPageRanges();
    setText("runtime-current-stage", "-");
    setText("runtime-stage-elapsed", "-");
    setText("runtime-total-elapsed", "-");
    setText("runtime-retry-count", "0");
    setText("runtime-last-transition", "-");
    setText("runtime-terminal-reason", "-");
    setText("runtime-input-protocol", "-");
    setText("runtime-stage-spec-version", "-");
    setText("runtime-math-mode", "-");
    setText("status-detail-job-id", "-");
    setText("failure-summary", "-");
    setText("failure-category", "-");
    setText("failure-stage", "-");
    setText("failure-root-cause", "-");
    setText("failure-suggestion", "-");
    setText("failure-last-log-line", "-");
    setText("failure-retryable", "-");
    setText("events-status", "All Events");
    $("events-empty")?.classList.remove("hidden");
    $("events-list")?.classList.add("hidden");
    if ($("events-list")) {
      $("events-list").innerHTML = "";
    }
    activateDetailTab("overview");
    updateJobWarning("idle");
  }

  async function cancelCurrentJob() {
    const jobId = state.currentJobId;
    if (!jobId) {
      setText("error-box", "No cancelable task available");
      return;
    }
    $("cancel-btn").disabled = true;
    try {
      await submitJson(`${buildJobDetailEndpoint(jobId, apiPrefix)}/cancel`, {});
      await fetchJob(jobId);
    } catch (err) {
      setText("error-box", err.message);
    }
  }

  return {
    cancelCurrentJob,
    fetchJob,
    returnToHome,
    startPolling,
    stopPolling,
  };
}
