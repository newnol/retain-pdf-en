use std::path::Path;

use super::super::query::list_jobs_filtered;
use super::helpers::{derive_display_name, job_path_prefix};
use super::live_stage::{list_combined_job_events, load_live_stage_snapshot};
use super::security::redact_job_events;
use super::summary_loaders::load_invocation_summary;
use crate::db::Db;
use crate::error::AppError;
use crate::models::{
    summarize_list_invocation, JobEventListView, JobListItemView, JobListView, JobSnapshot,
    ListJobEventsQuery, ListJobsQuery,
};

pub fn build_job_list_view(
    db: &Db,
    data_root: &Path,
    query: &ListJobsQuery,
    base_url: &str,
) -> Result<JobListView, AppError> {
    let jobs = list_jobs_filtered(db, query)?;
    let items: Vec<_> = jobs
        .iter()
        .map(|job| build_job_list_item_view(db, data_root, job, base_url))
        .collect();
    let invocation_summary = summarize_list_invocation(&items);
    Ok(JobListView {
        items,
        invocation_summary,
    })
}

pub fn build_job_events_view(
    db: &Db,
    data_root: &Path,
    job_id: &str,
    query: &ListJobEventsQuery,
) -> Result<JobEventListView, AppError> {
    let limit = query.limit.clamp(1, 500);
    let job = db.get_job(job_id)?;
    let items = redact_job_events(
        &job,
        list_combined_job_events(db, data_root, &job)?
            .into_iter()
            .skip(query.offset as usize)
            .take(limit as usize)
            .collect(),
    );
    Ok(JobEventListView {
        items,
        limit,
        offset: query.offset,
    })
}

fn build_job_list_item_view(
    db: &Db,
    data_root: &Path,
    job: &JobSnapshot,
    base_url: &str,
) -> JobListItemView {
    let detail_path = format!("{}/{}", job_path_prefix(job), job.job_id);
    let live_stage = load_live_stage_snapshot(job, data_root);
    JobListItemView {
        job_id: job.job_id.clone(),
        display_name: derive_display_name(db, job),
        workflow: job.workflow.clone(),
        status: job.status.clone(),
        trace_id: job
            .artifacts
            .as_ref()
            .and_then(|item| item.trace_id.clone()),
        stage: live_stage
            .as_ref()
            .and_then(|snapshot| snapshot.stage.clone())
            .or_else(|| job.stage.clone()),
        invocation: load_invocation_summary(job, data_root),
        created_at: job.created_at.clone(),
        updated_at: job.updated_at.clone(),
        detail_url: crate::models::to_absolute_url(base_url, &detail_path),
        detail_path,
    }
}
