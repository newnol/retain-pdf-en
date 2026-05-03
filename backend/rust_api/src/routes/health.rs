use axum::extract::State;
use axum::Json;
use serde::Serialize;

use crate::models::ApiResponse;
use crate::models::JobStatusKind;
use crate::ocr_provider::supported_provider_keys;
use crate::routes::common::{build_health_route_deps, HealthRouteDeps};
use crate::AppState;

#[derive(Serialize)]
pub struct HealthView {
    pub status: &'static str,
    pub db: &'static str,
    pub queue_depth: i64,
    pub running_jobs: i64,
    pub provider_backends: Vec<&'static str>,
    pub time: String,
}

fn build_health_view(deps: HealthRouteDeps<'_>) -> HealthView {
    let db_ok = deps.db.ping().is_ok();
    let queued = deps
        .db
        .count_jobs_with_status(&JobStatusKind::Queued)
        .unwrap_or(0);
    let running = deps
        .db
        .count_jobs_with_status(&JobStatusKind::Running)
        .unwrap_or(0);
    HealthView {
        status: if db_ok { "up" } else { "degraded" },
        db: if db_ok { "ok" } else { "error" },
        queue_depth: queued,
        running_jobs: running,
        provider_backends: supported_provider_keys(),
        time: crate::models::now_iso(),
    }
}

pub async fn health(State(state): State<AppState>) -> Json<ApiResponse<HealthView>> {
    Json(ApiResponse::ok(build_health_view(build_health_route_deps(
        &state,
    ))))
}
