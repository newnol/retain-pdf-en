use anyhow::Result;

use crate::job_events::persist_runtime_job_with_resources;
use crate::models::{now_iso, JobRuntimeState, JobStatusKind};

use super::super::{
    append_error_chain_log, attach_job_provider_failure, format_error_chain, job_artifacts_mut,
    refresh_job_failure, sync_runtime_state, ProcessRuntimeDeps,
};

pub(super) async fn save_ocr_job(
    deps: &ProcessRuntimeDeps,
    job: &JobRuntimeState,
    parent_job_id: Option<&str>,
) -> Result<()> {
    persist_runtime_job_with_resources(
        deps.persist.db.as_ref(),
        &deps.persist.data_root,
        &deps.persist.output_root,
        job,
    )?;
    if let Some(parent_job_id) = parent_job_id {
        mirror_parent_ocr_status(deps, parent_job_id, job).await?;
    }
    Ok(())
}

async fn mirror_parent_ocr_status(
    deps: &ProcessRuntimeDeps,
    parent_job_id: &str,
    ocr_job: &JobRuntimeState,
) -> Result<()> {
    let mut parent_job = deps.db.get_job(parent_job_id)?.into_runtime();
    if matches!(
        parent_job.status,
        JobStatusKind::Succeeded | JobStatusKind::Failed | JobStatusKind::Canceled
    ) {
        return Ok(());
    }
    let parent_artifacts = job_artifacts_mut(&mut parent_job);
    parent_artifacts.ocr_job_id = Some(ocr_job.job_id.clone());
    parent_artifacts.ocr_status = Some(ocr_job.status.clone());
    parent_artifacts.ocr_trace_id = ocr_job
        .artifacts
        .as_ref()
        .and_then(|item| item.trace_id.clone());
    parent_artifacts.ocr_provider_trace_id = ocr_job
        .artifacts
        .as_ref()
        .and_then(|item| item.provider_trace_id.clone());
    parent_artifacts.ocr_provider_diagnostics = ocr_job
        .artifacts
        .as_ref()
        .and_then(|item| item.ocr_provider_diagnostics.clone());

    parent_job.status = JobStatusKind::Running;
    parent_job.stage = ocr_job.stage.clone().or(Some("ocr_submitting".to_string()));
    parent_job.stage_detail = ocr_job
        .stage_detail
        .as_ref()
        .map(|detail| format!("OCR subtask: {detail}"))
        .or_else(|| Some("OCR subtask running".to_string()));
    parent_job.progress_current = ocr_job.progress_current;
    parent_job.progress_total = ocr_job.progress_total;
    parent_job.updated_at = now_iso();
    parent_job.replace_failure_info(None);
    parent_job.sync_runtime_state();
    persist_runtime_job_with_resources(
        deps.persist.db.as_ref(),
        &deps.persist.data_root,
        &deps.persist.output_root,
        &parent_job,
    )?;
    Ok(())
}

pub(super) fn fail_missing_source_pdf(
    job: &mut JobRuntimeState,
    source_pdf_path: &std::path::Path,
) {
    let message = format!("source pdf not found: {}", source_pdf_path.display());
    job.status = JobStatusKind::Failed;
    job.stage = Some("failed".to_string());
    job.stage_detail = Some("OCR completed but source PDF is missing".to_string());
    job.error = Some(message.clone());
    job.updated_at = now_iso();
    job.finished_at = Some(now_iso());
    job.append_log(&message);
    refresh_job_failure(job);
    sync_runtime_state(job);
}

pub(super) fn fail_ocr_transport(job: &mut JobRuntimeState, err: &anyhow::Error) {
    let message = format_error_chain(err);
    append_error_chain_log(job, err);
    attach_job_provider_failure(job, &message);
    job.status = JobStatusKind::Failed;
    job.stage = Some("failed".to_string());
    if job
        .stage_detail
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .is_none()
    {
        job.stage_detail = Some("OCR provider transport failed".to_string());
    }
    job.error = Some(message);
    job.updated_at = now_iso();
    job.finished_at = Some(now_iso());
    refresh_job_failure(job);
    sync_runtime_state(job);
}

pub fn sync_parent_with_ocr_child(
    parent_job: &mut JobRuntimeState,
    ocr_finished: &JobRuntimeState,
) {
    let parent_artifacts = job_artifacts_mut(parent_job);
    parent_artifacts.ocr_job_id = Some(ocr_finished.job_id.clone());
    parent_artifacts.ocr_status = Some(ocr_finished.status.clone());
    parent_artifacts.ocr_trace_id = ocr_finished
        .artifacts
        .as_ref()
        .and_then(|item| item.trace_id.clone());
    parent_artifacts.ocr_provider_trace_id = ocr_finished
        .artifacts
        .as_ref()
        .and_then(|item| item.provider_trace_id.clone());

    if let Some(child_artifacts) = ocr_finished.artifacts.as_ref() {
        if parent_artifacts.job_root.is_none() {
            parent_artifacts.job_root = child_artifacts.job_root.clone();
        }
        parent_artifacts.source_pdf = child_artifacts.source_pdf.clone();
        parent_artifacts.layout_json = child_artifacts.layout_json.clone();
        parent_artifacts.normalized_document_json =
            child_artifacts.normalized_document_json.clone();
        parent_artifacts.normalization_report_json =
            child_artifacts.normalization_report_json.clone();
        parent_artifacts.provider_raw_dir = child_artifacts.provider_raw_dir.clone();
        parent_artifacts.provider_zip = child_artifacts.provider_zip.clone();
        parent_artifacts.provider_summary_json = child_artifacts.provider_summary_json.clone();
        parent_artifacts.schema_version = child_artifacts.schema_version.clone();
        parent_artifacts.trace_id = parent_artifacts
            .trace_id
            .clone()
            .or(child_artifacts.trace_id.clone());
        parent_artifacts.provider_trace_id = child_artifacts.provider_trace_id.clone();
        parent_artifacts.ocr_provider_diagnostics =
            child_artifacts.ocr_provider_diagnostics.clone();
    }
}
