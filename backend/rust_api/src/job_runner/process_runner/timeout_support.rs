use anyhow::Result;

use crate::job_events::persist_job_with_resources;
use crate::models::JobStatusKind;

use super::super::ProcessRuntimeDeps;

pub(super) fn timeout_detail_for_stage(stage: Option<&str>) -> &'static str {
    match stage {
        Some("normalizing") => "normalization timeout",
        _ => "provider timeout",
    }
}

pub(super) fn apply_timeout_failure(job: &mut crate::models::JobSnapshot, timestamp: String) {
    let timeout_detail = timeout_detail_for_stage(job.stage.as_deref()).to_string();
    job.pid = None;
    job.updated_at = timestamp.clone();
    job.finished_at = Some(timestamp);
    job.status = JobStatusKind::Failed;
    job.stage = Some("failed".to_string());
    job.stage_detail = Some(timeout_detail.clone());
    job.error = Some(timeout_detail);
    job.sync_runtime_state();
    job.replace_failure_info(crate::job_failure::classify_job_failure(job));
}

pub(super) fn persist_timeout_failure(
    deps: &ProcessRuntimeDeps,
    stdout_job: (String, crate::models::JobRuntimeState),
) -> Result<crate::models::JobRuntimeState> {
    let mut timed_out_job = deps.db.get_job(&stdout_job.1.job_id)?;
    apply_timeout_failure(&mut timed_out_job, crate::models::now_iso());
    persist_job_with_resources(
        deps.db.as_ref(),
        &deps.config.data_root,
        &deps.config.output_root,
        &timed_out_job,
    )?;
    Ok(timed_out_job.into_runtime())
}
