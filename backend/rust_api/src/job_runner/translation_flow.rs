use anyhow::Result;

use crate::job_events::persist_runtime_job_with_resources;
use crate::models::{now_iso, JobRuntimeState, JobStatusKind};
use crate::storage_paths::build_job_paths;

#[path = "translation_flow_child.rs"]
mod translation_flow_child;
#[path = "translation_flow_stage.rs"]
mod translation_flow_stage;
#[path = "translation_flow_support.rs"]
mod translation_flow_support;

use self::translation_flow_child::{
    create_ocr_child_job, load_translation_upload_source, mark_parent_ocr_submitting,
};
use self::translation_flow_stage::{
    record_ocr_child_finished, run_render_stage_after_translation, run_translation_stage,
};
use self::translation_flow_support::{finalize_parent_after_ocr, OcrContinuation};
use super::ocr_flow::{execute_ocr_job, sync_parent_with_ocr_child};
use super::{attach_job_paths, ProcessRuntimeDeps};

pub(super) async fn run_translation_job_with_ocr(
    deps: ProcessRuntimeDeps,
    parent_job: JobRuntimeState,
) -> Result<JobRuntimeState> {
    run_job_with_ocr(deps, parent_job, OcrContinuation::FullPipeline).await
}

pub(super) async fn run_translate_only_job_with_ocr(
    deps: ProcessRuntimeDeps,
    parent_job: JobRuntimeState,
) -> Result<JobRuntimeState> {
    run_job_with_ocr(deps, parent_job, OcrContinuation::TranslateOnly).await
}

async fn run_job_with_ocr(
    deps: ProcessRuntimeDeps,
    mut parent_job: JobRuntimeState,
    continuation: OcrContinuation,
) -> Result<JobRuntimeState> {
    let parent_job_paths = build_job_paths(&deps.config.output_root, &parent_job.job_id)?;
    attach_job_paths(&mut parent_job, &parent_job_paths);
    let source = load_translation_upload_source(deps.db.as_ref(), &parent_job)?;
    mark_parent_ocr_submitting(&deps, &mut parent_job)?;
    let ocr_child = create_ocr_child_job(&deps, &mut parent_job, &parent_job_paths, &source)?;

    let ocr_finished = execute_ocr_job(
        deps.clone(),
        ocr_child,
        Some(parent_job.job_id.clone()),
        Some(parent_job.job_id.clone()),
    )
    .await?;
    persist_runtime_job_with_resources(
        deps.db.as_ref(),
        &deps.config.data_root,
        &deps.config.output_root,
        &ocr_finished,
    )?;
    sync_parent_with_ocr_child(&mut parent_job, &ocr_finished);
    record_ocr_child_finished(&deps, &parent_job, &ocr_finished);

    if finalize_parent_after_ocr(&mut parent_job, &ocr_finished, now_iso())? {
        return Ok(parent_job);
    }

    let translation_stage = run_translation_stage(&deps, parent_job, &parent_job_paths).await?;
    let translated_job = translation_stage.job;
    let source_pdf_path = translation_stage.source_pdf_path;

    if !matches!(translated_job.status, JobStatusKind::Succeeded) {
        return Ok(translated_job);
    }
    match continuation {
        OcrContinuation::TranslateOnly => Ok(translated_job),
        OcrContinuation::FullPipeline => {
            run_render_stage_after_translation(
                deps,
                translated_job,
                &parent_job_paths,
                &source_pdf_path,
            )
            .await
        }
    }
}
