use axum::extract::{Path as AxumPath, State};
use axum::Json;

use crate::error::AppError;
use crate::models::{
    ApiResponse, GlossaryCsvParseInput, GlossaryCsvParseView, GlossaryDetailView, GlossaryListView,
    GlossaryUpsertInput,
};
use crate::routes::common::{build_glossary_route_deps, ok_json};
use crate::services::glossary_api::{
    create_glossary_view, delete_glossary_view, get_glossary_view, list_glossaries_view,
    parse_glossary_csv_view, update_glossary_view,
};
use crate::AppState;

pub async fn create_glossary_route(
    State(state): State<AppState>,
    Json(payload): Json<GlossaryUpsertInput>,
) -> Result<Json<ApiResponse<GlossaryDetailView>>, AppError> {
    let deps = build_glossary_route_deps(&state);
    Ok(ok_json(create_glossary_view(deps.db, &payload)?))
}

pub async fn list_glossaries_route(
    State(state): State<AppState>,
) -> Result<Json<ApiResponse<GlossaryListView>>, AppError> {
    let deps = build_glossary_route_deps(&state);
    Ok(ok_json(list_glossaries_view(deps.db)?))
}

pub async fn get_glossary_route(
    State(state): State<AppState>,
    AxumPath(glossary_id): AxumPath<String>,
) -> Result<Json<ApiResponse<GlossaryDetailView>>, AppError> {
    let deps = build_glossary_route_deps(&state);
    Ok(ok_json(get_glossary_view(deps.db, &glossary_id)?))
}

pub async fn update_glossary_route(
    State(state): State<AppState>,
    AxumPath(glossary_id): AxumPath<String>,
    Json(payload): Json<GlossaryUpsertInput>,
) -> Result<Json<ApiResponse<GlossaryDetailView>>, AppError> {
    let deps = build_glossary_route_deps(&state);
    Ok(ok_json(update_glossary_view(
        deps.db,
        &glossary_id,
        &payload,
    )?))
}

pub async fn delete_glossary_route(
    State(state): State<AppState>,
    AxumPath(glossary_id): AxumPath<String>,
) -> Result<Json<ApiResponse<GlossaryDetailView>>, AppError> {
    let deps = build_glossary_route_deps(&state);
    Ok(ok_json(delete_glossary_view(deps.db, &glossary_id)?))
}

pub async fn parse_glossary_csv_route(
    Json(payload): Json<GlossaryCsvParseInput>,
) -> Result<Json<ApiResponse<GlossaryCsvParseView>>, AppError> {
    Ok(ok_json(parse_glossary_csv_view(&payload)?))
}
