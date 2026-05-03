use crate::error::AppError;
use crate::models::{ApiResponse, JobSubmissionView};
use crate::AppState;
use axum::extract::{Path as AxumPath, State};
use axum::http::HeaderMap;
use axum::Json;

use super::common::build_jobs_route_deps;
use super::query_adapter::cancel_job_response;

pub async fn cancel_ocr_job(
    State(state): State<AppState>,
    AxumPath(job_id): AxumPath<String>,
    headers: HeaderMap,
) -> Result<Json<ApiResponse<JobSubmissionView>>, AppError> {
    cancel_job_response(build_jobs_route_deps(&state), &headers, &job_id, true).await
}

pub async fn cancel_job(
    State(state): State<AppState>,
    AxumPath(job_id): AxumPath<String>,
    headers: HeaderMap,
) -> Result<Json<ApiResponse<JobSubmissionView>>, AppError> {
    cancel_job_response(build_jobs_route_deps(&state), &headers, &job_id, false).await
}
