use std::path::{Path, PathBuf};

use anyhow::Result;

use crate::job_events::{
    persist_runtime_job_with_resources, record_custom_runtime_event_with_resources,
};
use crate::models::{now_iso, JobRuntimeState, JobStatusKind};
use crate::services::job_command_factory::build_translate_only_command;
use crate::storage_paths::JobPaths;

use crate::job_runner::{
    build_render_only_command, clear_job_failure, execute_process_job, sync_runtime_state,
    ProcessRuntimeDeps,
};

use super::translation_flow_support::translation_inputs_from_artifacts;

pub(super) struct TranslationStageResult {
    pub(super) job: JobRuntimeState,
    pub(super) source_pdf_path: PathBuf,
}

pub(super) fn record_ocr_child_finished(
    deps: &ProcessRuntimeDeps,
    parent_job: &JobRuntimeState,
    ocr_finished: &JobRuntimeState,
) {
    let ocr_finished_status = ocr_finished.status.clone();
    record_custom_runtime_event_with_resources(
        deps.persist.db.as_ref(),
        &deps.persist.data_root,
        &deps.persist.output_root,
        &parent_job.snapshot(),
        if matches!(ocr_finished_status, JobStatusKind::Failed) {
            "error"
        } else {
            "info"
        },
        "ocr_child_finished",
        format!("OCR subtask finished, status={:?}", ocr_finished_status),
        Some(serde_json::json!({
            "ocr_job_id": ocr_finished.job_id.clone(),
            "status": format!("{:?}", ocr_finished_status).to_ascii_lowercase(),
        })),
    );
}

pub(super) async fn run_translation_stage(
    deps: &ProcessRuntimeDeps,
    mut parent_job: JobRuntimeState,
    parent_job_paths: &JobPaths,
) -> Result<TranslationStageResult> {
    let translate_inputs = translation_inputs_from_artifacts(&parent_job)?;
    let normalized_path = translate_inputs.normalized_path.to_path_buf();
    let source_pdf_path = translate_inputs.source_pdf_path.to_path_buf();
    let layout_json_path = translate_inputs
        .layout_json_path
        .map(|path| path.to_path_buf());
    prepare_translation_stage(
        deps,
        &mut parent_job,
        parent_job_paths,
        &normalized_path,
        &source_pdf_path,
        layout_json_path.as_deref(),
    )?;
    let job = execute_process_job(deps.clone(), parent_job, &[]).await?;
    Ok(TranslationStageResult {
        job,
        source_pdf_path,
    })
}

fn prepare_translation_stage(
    deps: &ProcessRuntimeDeps,
    parent_job: &mut JobRuntimeState,
    parent_job_paths: &JobPaths,
    normalized_path: &Path,
    source_pdf_path: &Path,
    layout_json_path: Option<&Path>,
) -> Result<()> {
    parent_job.command = build_translate_only_command(
        deps.config.as_ref(),
        &parent_job.request_payload,
        parent_job_paths,
        normalized_path,
        source_pdf_path,
        layout_json_path,
    );
    parent_job.stage = Some("translating".to_string());
    parent_job.stage_detail = Some("OCR completed, starting translation".to_string());
    parent_job.updated_at = now_iso();
    sync_runtime_state(parent_job);
    persist_runtime_job_with_resources(
        deps.persist.db.as_ref(),
        &deps.persist.data_root,
        &deps.persist.output_root,
        parent_job,
    )?;

    Ok(())
}

pub(super) async fn run_render_stage_after_translation(
    deps: ProcessRuntimeDeps,
    mut job: JobRuntimeState,
    job_paths: &JobPaths,
    source_pdf_path: &Path,
) -> Result<JobRuntimeState> {
    job.command = build_render_only_command(
        deps.config.as_ref(),
        &job.request_payload,
        job_paths,
        source_pdf_path,
        &job_paths.translated_dir,
    );
    job.status = JobStatusKind::Running;
    job.stage = Some("rendering".to_string());
    job.stage_detail = Some("Translation completed, starting rendering".to_string());
    job.updated_at = now_iso();
    clear_job_failure(&mut job);
    sync_runtime_state(&mut job);
    persist_runtime_job_with_resources(
        deps.persist.db.as_ref(),
        &deps.persist.data_root,
        &deps.persist.output_root,
        &job,
    )?;
    execute_process_job(deps, job, &[]).await
}
