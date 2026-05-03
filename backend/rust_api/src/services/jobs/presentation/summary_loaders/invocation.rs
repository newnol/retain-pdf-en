use std::path::Path;

use crate::models::{InvocationSummaryView, JobSnapshot};
use crate::storage_paths::{resolve_data_path, resolve_translation_manifest};

use super::shared::read_json_value;

pub(crate) fn load_invocation_summary(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<InvocationSummaryView> {
    load_invocation_summary_from_manifest(job, data_root)
        .or_else(|| load_invocation_summary_from_pipeline_summary(job, data_root))
}

fn load_invocation_summary_from_manifest(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<InvocationSummaryView> {
    let path = resolve_translation_manifest(job, data_root)?;
    load_invocation_summary_from_json_path(&path)
}

fn load_invocation_summary_from_pipeline_summary(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<InvocationSummaryView> {
    let path = job.artifacts.as_ref()?.summary.as_ref()?;
    let path = resolve_data_path(data_root, path).ok()?;
    load_invocation_summary_from_json_path(&path)
}

fn load_invocation_summary_from_json_path(path: &Path) -> Option<InvocationSummaryView> {
    let payload = read_json_value(path).ok()?;
    let summary: InvocationSummaryView =
        serde_json::from_value(payload.get("invocation")?.clone()).ok()?;
    if !summary.stage.is_empty()
        || !summary.input_protocol.is_empty()
        || !summary.stage_spec_schema_version.is_empty()
    {
        Some(summary)
    } else {
        None
    }
}
