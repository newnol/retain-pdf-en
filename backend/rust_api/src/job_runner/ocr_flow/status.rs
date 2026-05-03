use anyhow::Result;

use crate::models::{now_iso, JobRuntimeState};
use crate::ocr_provider::OcrTaskStatus;

use crate::job_runner::{job_artifacts_mut, ocr_provider_diagnostics_mut, ProcessRuntimeDeps};

use super::save_ocr_job;

pub(super) async fn update_ocr_job_from_status(
    deps: &ProcessRuntimeDeps,
    job: &mut JobRuntimeState,
    status: OcrTaskStatus,
    current: Option<i64>,
    total: Option<i64>,
    parent_job_id: Option<&str>,
) -> Result<()> {
    ocr_provider_diagnostics_mut(job).last_status = Some(status.clone());
    if let Some(stage) = status.stage.clone() {
        job.stage = Some(stage);
    }
    job.stage_detail = status.detail.clone().or(status.provider_message.clone());
    job.progress_current = current;
    job.progress_total = total;
    record_provider_trace(job, status.trace_id.clone());
    job.updated_at = now_iso();
    save_ocr_job(deps, job, parent_job_id).await?;
    Ok(())
}

pub(super) fn record_provider_trace(job: &mut JobRuntimeState, trace_id: Option<String>) {
    if let Some(trace_id) = trace_id.filter(|item| !item.trim().is_empty()) {
        job_artifacts_mut(job).provider_trace_id = Some(trace_id);
    }
}
