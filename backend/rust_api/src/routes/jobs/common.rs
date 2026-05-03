use axum::Json;

use crate::app::build_jobs_facade_from_state;
use crate::models::ApiResponse;
use crate::services::jobs::JobsFacade;
use crate::AppState;

pub struct JobsRouteDeps<'a> {
    pub jobs: JobsFacade<'a>,
}

pub fn build_jobs_route_deps(state: &AppState) -> JobsRouteDeps<'_> {
    JobsRouteDeps {
        jobs: build_jobs_facade_from_state(state),
    }
}

pub fn jobs_facade(deps: JobsRouteDeps<'_>) -> JobsFacade<'_> {
    deps.jobs
}

pub fn ok_json<T>(value: T) -> Json<ApiResponse<T>> {
    Json(ApiResponse::ok(value))
}
