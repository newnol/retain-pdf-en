use std::path::Path;

use crate::error::AppError;
use crate::models::{redact_json_value, sensitive_values, JobSnapshot, TranslationDebugItemView};
use crate::storage_paths::resolve_translation_manifest;

use super::common::value_string;
use super::index::load_manifest_pages;

pub(crate) fn load_translation_debug_item_view(
    data_root: &Path,
    job: &JobSnapshot,
    item_id: &str,
) -> Result<TranslationDebugItemView, AppError> {
    let manifest_path = resolve_translation_manifest(job, data_root).ok_or_else(|| {
        AppError::not_found(format!("translation manifest not found: {}", job.job_id))
    })?;
    let secrets = sensitive_values(&job.request_payload);
    for (page_idx, page_path, items) in load_manifest_pages(&manifest_path)? {
        for item in items {
            if value_string(item.get("item_id")) == item_id {
                return Ok(TranslationDebugItemView {
                    job_id: job.job_id.clone(),
                    item_id: item_id.to_string(),
                    page_idx,
                    page_number: page_idx + 1,
                    page_path,
                    item: redact_json_value(&item, &secrets),
                });
            }
        }
    }
    Err(AppError::not_found(format!(
        "translation item not found: {}/{}",
        job.job_id, item_id
    )))
}
