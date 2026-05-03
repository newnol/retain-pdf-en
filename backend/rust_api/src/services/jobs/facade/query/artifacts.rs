use axum::response::Response;

use crate::error::AppError;
use crate::routes::job_helpers::stream_file;
use crate::services::artifacts::{
    artifact_is_direct_downloadable, build_markdown_bundle_for_job, resolve_registry_artifact,
};
use crate::storage_paths::ARTIFACT_KEY_MARKDOWN_BUNDLE_ZIP;

use super::super::JobsFacade;

impl<'a> JobsFacade<'a> {
    pub async fn registered_artifact_response(
        &self,
        job_id: &str,
        artifact_key: &str,
        include_job_dir: bool,
        ocr_only: bool,
    ) -> Result<Response, AppError> {
        let job = self.load_supported_job_snapshot(job_id, ocr_only)?;
        if artifact_key == ARTIFACT_KEY_MARKDOWN_BUNDLE_ZIP {
            let (item, path) = build_markdown_bundle_for_job(
                self.query.db,
                &self.query.config.data_root,
                &job,
                include_job_dir,
            )?;
            return stream_file(path, &item.content_type, item.file_name.clone()).await;
        }
        let Some((item, path)) = resolve_registry_artifact(
            self.query.db,
            &self.query.config.data_root,
            &job,
            artifact_key,
        )?
        else {
            return Err(AppError::not_found(format!(
                "artifact not found: {job_id}/{artifact_key}"
            )));
        };
        if !artifact_is_direct_downloadable(&item) {
            return Err(AppError::conflict(format!(
                "artifact is a directory and cannot be streamed directly: {artifact_key}"
            )));
        }
        if !item.ready || !path.exists() || !path.is_file() {
            return Err(AppError::not_found(format!(
                "artifact not ready: {job_id}/{artifact_key}"
            )));
        }
        stream_file(path, &item.content_type, item.file_name.clone()).await
    }
}
