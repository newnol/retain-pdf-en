use std::path::Path;

use crate::db::Db;
use crate::error::AppError;
use crate::job_events::persist_job_with_resources;
use crate::models::JobSnapshot;

use super::runtime_gateway::JobRuntimeLauncher;

#[derive(Clone)]
pub struct JobLaunchDeps<'a> {
    pub db: &'a Db,
    pub data_root: &'a Path,
    pub output_root: &'a Path,
    pub runtime: JobRuntimeLauncher,
}

impl<'a> JobLaunchDeps<'a> {
    pub fn new(
        db: &'a Db,
        data_root: &'a Path,
        output_root: &'a Path,
        runtime: JobRuntimeLauncher,
    ) -> Self {
        Self {
            db,
            data_root,
            output_root,
            runtime,
        }
    }
}

pub fn start_job_execution(
    deps: &JobLaunchDeps<'_>,
    job: JobSnapshot,
) -> Result<JobSnapshot, AppError> {
    persist_job_with_resources(deps.db, deps.data_root, deps.output_root, &job)?;
    deps.runtime.launch(job.job_id.clone());
    Ok(job)
}
