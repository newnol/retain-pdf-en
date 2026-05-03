use std::path::Path;
use std::process::ExitStatus;
use std::time::Instant;

use crate::models::{now_iso, JobRuntimeState, ProcessResult};

pub(super) fn attach_process_result(
    job: &mut JobRuntimeState,
    status: &ExitStatus,
    started: Instant,
    stdout_text: String,
    stderr_text: &str,
    project_root: &Path,
) {
    job.updated_at = now_iso();
    job.finished_at = Some(now_iso());
    job.pid = None;
    job.result = Some(ProcessResult {
        success: status.success(),
        return_code: status.code().unwrap_or(-1),
        duration_seconds: started.elapsed().as_secs_f64(),
        command: job.command.clone(),
        cwd: project_root.to_string_lossy().to_string(),
        stdout: stdout_text,
        stderr: stderr_text.to_string(),
    });
}
