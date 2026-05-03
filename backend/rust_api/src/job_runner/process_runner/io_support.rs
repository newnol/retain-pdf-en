use std::collections::HashSet;
use std::sync::Arc;

use anyhow::Result;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::RwLock;

use crate::job_events::persist_runtime_job_with_resources;
use crate::models::{now_iso, JobRuntimeState};

use crate::job_runner::JobPersistDeps;

use super::super::cancel_registry::is_cancel_requested_any;
use super::super::runtime_state::apply_job_stdout_line;

pub(super) async fn read_stream<R>(reader: R) -> Result<String>
where
    R: tokio::io::AsyncRead + Unpin,
{
    let mut lines = BufReader::new(reader).lines();
    let mut out = String::new();
    while let Some(line) = lines.next_line().await? {
        out.push_str(&line);
        out.push('\n');
    }
    Ok(out)
}

pub(super) async fn read_stdout(
    persist: JobPersistDeps,
    canceled_jobs: Arc<RwLock<HashSet<String>>>,
    mut job: JobRuntimeState,
    stdout: tokio::process::ChildStdout,
    extra_cancel_job_ids: Vec<String>,
) -> Result<(String, JobRuntimeState)> {
    let mut out = String::new();
    let mut lines = BufReader::new(stdout).lines();
    while let Some(line) = lines.next_line().await? {
        if is_cancel_requested_any(&canceled_jobs, &job.job_id, &extra_cancel_job_ids).await
            && !should_continue_after_cancel(&job)
        {
            break;
        }
        out.push_str(&line);
        out.push('\n');
        apply_job_stdout_line(&mut job, &line);
        if is_cancel_requested_any(&canceled_jobs, &job.job_id, &extra_cancel_job_ids).await
            && !should_continue_after_cancel(&job)
        {
            break;
        }
        job.updated_at = now_iso();
        persist_runtime_job_with_resources(
            persist.db.as_ref(),
            &persist.data_root,
            &persist.output_root,
            &job,
        )?;
    }
    Ok((out, job))
}

pub(super) fn should_continue_after_cancel(job: &JobRuntimeState) -> bool {
    matches!(job.stage.as_deref(), Some("normalizing"))
}
