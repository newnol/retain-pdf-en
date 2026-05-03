use std::path::Path;

use crate::models::{GlossaryUsageSummaryView, JobSnapshot};
use crate::storage_paths::{resolve_data_path, resolve_translation_manifest};

use super::shared::read_json_value;

pub(crate) fn load_glossary_summary(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<GlossaryUsageSummaryView> {
    load_glossary_summary_from_manifest(job, data_root)
        .or_else(|| load_glossary_summary_from_pipeline_summary(job, data_root))
}

fn load_glossary_summary_from_manifest(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<GlossaryUsageSummaryView> {
    let path = resolve_translation_manifest(job, data_root)?;
    load_glossary_summary_from_json_path(&path)
}

fn load_glossary_summary_from_pipeline_summary(
    job: &JobSnapshot,
    data_root: &Path,
) -> Option<GlossaryUsageSummaryView> {
    let path = job.artifacts.as_ref()?.summary.as_ref()?;
    let path = resolve_data_path(data_root, path).ok()?;
    load_glossary_summary_from_json_path(&path)
}

fn load_glossary_summary_from_json_path(path: &Path) -> Option<GlossaryUsageSummaryView> {
    let payload = read_json_value(path).ok()?;
    let summary: GlossaryUsageSummaryView =
        serde_json::from_value(payload.get("glossary")?.clone()).ok()?;
    if summary.enabled
        || summary.entry_count > 0
        || !summary.glossary_id.is_empty()
        || !summary.glossary_name.is_empty()
    {
        Some(summary)
    } else {
        None
    }
}
