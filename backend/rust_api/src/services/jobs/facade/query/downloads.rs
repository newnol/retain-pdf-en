use axum::http::header;
use axum::http::HeaderMap;
use axum::response::IntoResponse;
use axum::response::Response;
use std::path::{Path, PathBuf};

use crate::error::AppError;
use crate::models::MarkdownView;
use crate::routes::common::ok_json;
use crate::routes::job_helpers::stream_file;
use crate::services::artifacts::{attach_job_id_header, build_bundle_for_job};
use crate::storage_paths::{resolve_markdown_images_dir, resolve_markdown_path};

use super::super::super::presentation::load_supported_job;
use super::super::JobsFacade;

impl<'a> JobsFacade<'a> {
    pub async fn download_job_document_response(
        &self,
        job_id: &str,
        ocr_only: bool,
        resolve_path: impl Fn(&crate::models::JobSnapshot, &Path) -> Option<PathBuf>,
        not_ready_label: &str,
        content_type: &str,
    ) -> Result<Response, AppError> {
        let job = self.load_supported_job_snapshot(job_id, ocr_only)?;
        let path = resolve_path(&job, &self.query.config.data_root)
            .ok_or_else(|| AppError::not_found(format!("{not_ready_label}: {job_id}")))?;
        stream_file(path, content_type, None).await
    }

    pub async fn markdown_response(
        &self,
        headers: &HeaderMap,
        job_id: String,
        raw: bool,
    ) -> Result<Response, AppError> {
        let job = load_supported_job(self.query.db, &self.query.config.data_root, &job_id)?;
        let markdown_path = resolve_markdown_path(&job, &self.query.config.data_root)
            .ok_or_else(|| AppError::not_found(format!("markdown not found: {job_id}")))?;
        let content = tokio::fs::read_to_string(&markdown_path).await?;
        if raw {
            return Ok((
                [(header::CONTENT_TYPE, "text/markdown; charset=utf-8")],
                content,
            )
                .into_response());
        }
        let base_url = self.base_url(headers);
        let raw_path = format!("/api/v1/jobs/{}/markdown?raw=true", job.job_id);
        let images_base_path = format!("/api/v1/jobs/{}/markdown/images/", job.job_id);
        Ok(ok_json(MarkdownView {
            job_id,
            content,
            raw_path: raw_path.clone(),
            raw_url: crate::models::to_absolute_url(&base_url, &raw_path),
            images_base_path: images_base_path.clone(),
            images_base_url: crate::models::to_absolute_url(&base_url, &images_base_path),
        })
        .into_response())
    }

    pub async fn markdown_image_response(
        &self,
        job_id: &str,
        path: &str,
    ) -> Result<Response, AppError> {
        let job = load_supported_job(self.query.db, &self.query.config.data_root, job_id)?;
        let images_dir = resolve_markdown_images_dir(&job, &self.query.config.data_root)
            .ok_or_else(|| AppError::not_found(format!("markdown images not found: {job_id}")))?;
        let file_path = images_dir.join(path);
        if !file_path.exists() || !file_path.is_file() {
            return Err(AppError::not_found(format!(
                "markdown image not found: {path}"
            )));
        }
        let mime = mime_guess::from_path(&file_path).first_or_octet_stream();
        stream_file(file_path, mime.as_ref(), None).await
    }

    pub async fn bundle_response(&self, job_id: &str) -> Result<Response, AppError> {
        let _guard = self.query.downloads_lock.lock().await;
        let job = load_supported_job(self.query.db, &self.query.config.data_root, job_id)?;
        if !matches!(job.status, crate::models::JobStatusKind::Succeeded) {
            return Err(AppError::conflict("job is not finished successfully"));
        }
        let zip_path = build_bundle_for_job(
            self.query.db,
            &self.query.config.data_root,
            &self.query.config.downloads_dir,
            &job,
        )?;
        let mut response =
            stream_file(zip_path, "application/zip", Some(format!("{job_id}.zip"))).await?;
        attach_job_id_header(&mut response, job_id)?;
        Ok(response)
    }
}
