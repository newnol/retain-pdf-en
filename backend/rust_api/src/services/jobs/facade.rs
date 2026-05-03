mod command;
mod query;

use axum::http::HeaderMap;

use crate::models::{JobSnapshot, JobStatusKind, JobSubmissionView, WorkflowKind};

use super::creation::context::{CommandJobsDeps, QueryJobsDeps};
use super::support::{build_submission_view, request_base_url};

#[derive(Clone)]
pub struct JobsFacade<'a> {
    pub(super) command: CommandJobsDeps<'a>,
    pub(super) query: QueryJobsDeps<'a>,
}

impl<'a> JobsFacade<'a> {
    pub(crate) fn new(command: CommandJobsDeps<'a>, query: QueryJobsDeps<'a>) -> Self {
        Self { command, query }
    }

    fn base_url(&self, headers: &HeaderMap) -> String {
        request_base_url(headers, self.query.config.port)
    }

    fn build_submission_view(
        &self,
        headers: &HeaderMap,
        job: &JobSnapshot,
        status: JobStatusKind,
        workflow: WorkflowKind,
    ) -> JobSubmissionView {
        build_submission_view(job, status, workflow, &self.base_url(headers))
    }
}

pub(crate) fn build_jobs_facade<'a>(
    command: CommandJobsDeps<'a>,
    query: QueryJobsDeps<'a>,
) -> JobsFacade<'a> {
    JobsFacade::new(command, query)
}
