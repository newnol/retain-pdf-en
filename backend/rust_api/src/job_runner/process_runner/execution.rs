use std::process::ExitStatus;
use std::time::Instant;

use anyhow::{Context, Result};
use tokio::time::{timeout, Duration};

use crate::models::JobRuntimeState;

use super::super::{terminate_job_process_tree, ProcessRuntimeDeps};
use super::io_support::{read_stdout, read_stream};
use super::timeout_support::persist_timeout_failure;

pub(super) struct CompletedProcess {
    pub(super) status: ExitStatus,
    pub(super) started: Instant,
    pub(super) stdout_text: String,
    pub(super) stderr_text: String,
    pub(super) latest_job: JobRuntimeState,
}

pub(super) enum ProcessExecution {
    Completed(CompletedProcess),
    TimedOut(JobRuntimeState),
}

pub(super) async fn collect_process_execution(
    deps: &ProcessRuntimeDeps,
    mut child: tokio::process::Child,
    job: JobRuntimeState,
    extra_cancel_job_ids: &[String],
) -> Result<ProcessExecution> {
    let stdout = child.stdout.take().context("missing stdout pipe")?;
    let stderr = child.stderr.take().context("missing stderr pipe")?;
    let child_pid = job.pid;
    let timeout_secs = job.request_payload.runtime.timeout_seconds;
    let stdout_handle = tokio::spawn(read_stdout(
        deps.persist.clone(),
        deps.canceled_jobs.clone(),
        job,
        stdout,
        extra_cancel_job_ids.to_vec(),
    ));
    let stderr_handle = tokio::spawn(read_stream(stderr));
    let started = Instant::now();

    let status = if timeout_secs > 0 {
        match timeout(Duration::from_secs(timeout_secs as u64), child.wait()).await {
            Ok(result) => result?,
            Err(_) => {
                if let Some(pid) = child_pid {
                    let _ = terminate_job_process_tree(pid).await;
                }
                let stdout_job = stdout_handle.await??;
                return Ok(ProcessExecution::TimedOut(persist_timeout_failure(
                    deps, stdout_job,
                )?));
            }
        }
    } else {
        child.wait().await?
    };

    let (stdout_text, latest_job) = stdout_handle.await??;
    let stderr_text = stderr_handle.await??;
    Ok(ProcessExecution::Completed(CompletedProcess {
        status,
        started,
        stdout_text,
        stderr_text,
        latest_job,
    }))
}
