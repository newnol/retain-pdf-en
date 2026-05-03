use std::path::PathBuf;

use axum::http::HeaderMap;
use axum::response::Response;

use crate::error::AppError;
use crate::models::{CreateJobInput, JobStatusKind, JobSubmissionView, WorkflowKind};
use crate::routes::job_helpers::stream_file;
use crate::services::artifacts::attach_job_id_header;

use super::super::super::creation::context::BundleBuildDeps;
use super::super::super::creation::{
    build_translation_bundle_artifact, create_ocr_job_from_upload, create_translation_job,
    UploadedPdfInput,
};
use super::super::JobsFacade;

impl<'a> JobsFacade<'a> {
    pub fn create_submission(
        &self,
        headers: &HeaderMap,
        request: &CreateJobInput,
    ) -> Result<JobSubmissionView, AppError> {
        let workflow = request.workflow.clone();
        let job = create_translation_job(&self.command.submit, request)?;
        Ok(self.build_submission_view(headers, &job, JobStatusKind::Queued, workflow))
    }

    pub async fn create_ocr_submission(
        &self,
        headers: &HeaderMap,
        request: &CreateJobInput,
        upload: Option<(String, Vec<u8>, bool)>,
    ) -> Result<JobSubmissionView, AppError> {
        let upload = upload.map(|(filename, bytes, developer_mode)| UploadedPdfInput {
            filename,
            bytes,
            developer_mode,
        });
        let job = create_ocr_job_from_upload(&self.command.submit, request, upload).await?;
        Ok(self.build_submission_view(headers, &job, JobStatusKind::Queued, WorkflowKind::Ocr))
    }

    pub async fn build_translation_bundle(
        &self,
        request: CreateJobInput,
        filename: String,
        bytes: Vec<u8>,
        developer_mode: bool,
    ) -> Result<(String, PathBuf), AppError> {
        let artifact = build_translation_bundle_artifact(
            &BundleBuildDeps {
                submit: self.command.submit.clone(),
                downloads_lock: self.command.downloads_lock,
            },
            request,
            UploadedPdfInput {
                filename,
                bytes,
                developer_mode,
            },
        )
        .await?;
        Ok((artifact.job_id, artifact.zip_path))
    }

    pub async fn translation_bundle_response(
        &self,
        request: CreateJobInput,
        filename: String,
        bytes: Vec<u8>,
        developer_mode: bool,
    ) -> Result<Response, AppError> {
        let (job_id, zip_path) = self
            .build_translation_bundle(request, filename, bytes, developer_mode)
            .await?;
        let mut response =
            stream_file(zip_path, "application/zip", Some(format!("{job_id}.zip"))).await?;
        attach_job_id_header(&mut response, &job_id)?;
        Ok(response)
    }
}
