use anyhow::{anyhow, Context, Result};
use std::path::Path;

use crate::job_runner::{ocr_provider_diagnostics_mut, ProcessRuntimeDeps};
use crate::models::{now_iso, JobRuntimeState};
use crate::ocr_provider::mineru::{parse_extra_formats, MineruClient};

use super::mineru_polling::{poll_remote_task_until_ready, poll_uploaded_batch_until_ready};
use super::mineru_retry::acquire_upload_target_with_retry;
use super::save_ocr_job;
use super::status::record_provider_trace;

pub(super) async fn run_local_ocr_transport_mineru(
    deps: &ProcessRuntimeDeps,
    job: &mut JobRuntimeState,
    client: &MineruClient,
    upload_path: &Path,
    provider_result_json_path: &Path,
    parent_job_id: Option<&str>,
) -> Result<()> {
    let upload_file_name = upload_path
        .file_name()
        .and_then(|item| item.to_str())
        .ok_or_else(|| anyhow!("invalid upload filename"))?;
    let timeout_secs = std::cmp::max(job.request_payload.ocr.poll_timeout, 1) as u64;
    let upload_target = acquire_upload_target_with_retry(
        deps,
        job,
        client,
        upload_file_name,
        timeout_secs,
        parent_job_id,
    )
    .await?;
    record_provider_trace(job, upload_target.trace_id.clone());
    {
        let diagnostics = ocr_provider_diagnostics_mut(job);
        diagnostics.handle.batch_id = Some(upload_target.batch_id.clone());
        diagnostics.handle.file_name = upload_path
            .file_name()
            .and_then(|item| item.to_str())
            .map(|item| item.to_string());
    }
    job.append_log(&format!("batch_id: {}", upload_target.batch_id));
    job.stage = Some("mineru_upload".to_string());
    job.stage_detail = Some("Obtained OCR provider upload URL, starting file upload".to_string());
    job.updated_at = now_iso();
    save_ocr_job(deps, job, parent_job_id).await?;

    client
        .upload_file(&upload_target.upload_url, upload_path)
        .await
        .with_context(|| format!("failed to upload file {}", upload_path.display()))?;
    job.append_log(&format!("upload done: {}", upload_path.display()));
    job.stage = Some("mineru_processing".to_string());
    job.stage_detail = Some("File upload completed, waiting for OCR provider parsing".to_string());
    job.updated_at = now_iso();
    save_ocr_job(deps, job, parent_job_id).await?;

    let file_name = upload_path
        .file_name()
        .and_then(|item| item.to_str())
        .ok_or_else(|| anyhow!("invalid upload filename"))?
        .to_string();
    poll_uploaded_batch_until_ready(
        deps,
        job,
        client,
        &upload_target.batch_id,
        &file_name,
        provider_result_json_path,
        parent_job_id,
    )
    .await
}

pub(super) async fn run_remote_ocr_transport_mineru(
    deps: &ProcessRuntimeDeps,
    job: &mut JobRuntimeState,
    client: &MineruClient,
    provider_result_json_path: &Path,
    parent_job_id: Option<&str>,
) -> Result<()> {
    let created = client
        .create_extract_task(
            &job.request_payload.source.source_url,
            &job.request_payload.ocr.model_version,
            job.request_payload.ocr.is_ocr,
            !job.request_payload.ocr.disable_formula,
            !job.request_payload.ocr.disable_table,
            &job.request_payload.ocr.language,
            &job.request_payload.ocr.page_ranges,
            &job.request_payload.ocr.data_id,
            job.request_payload.ocr.no_cache,
            job.request_payload.ocr.cache_tolerance,
            &parse_extra_formats(&job.request_payload.ocr.extra_formats),
        )
        .await?;
    record_provider_trace(job, created.trace_id.clone());
    ocr_provider_diagnostics_mut(job).handle.task_id = Some(created.task_id.clone());
    job.append_log(&format!("task_id: {}", created.task_id));
    job.stage = Some("mineru_processing".to_string());
    job.stage_detail = Some("Remote PDF submitted to OCR provider, waiting for parsing".to_string());
    job.updated_at = now_iso();
    save_ocr_job(deps, job, parent_job_id).await?;
    poll_remote_task_until_ready(
        deps,
        job,
        client,
        &created.task_id,
        provider_result_json_path,
        parent_job_id,
    )
    .await
}
