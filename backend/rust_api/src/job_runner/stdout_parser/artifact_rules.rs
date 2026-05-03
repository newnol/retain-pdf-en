use once_cell::sync::Lazy;
use regex::Regex;

use crate::models::JobSnapshot;

use super::{
    job_artifacts_mut, ocr_provider_diagnostics_mut, parse_labeled_value, STDOUT_LABEL_JOB_ROOT,
    STDOUT_LABEL_LAYOUT_JSON, STDOUT_LABEL_NORMALIZATION_REPORT_JSON,
    STDOUT_LABEL_NORMALIZED_DOCUMENT_JSON, STDOUT_LABEL_OUTPUT_PDF, STDOUT_LABEL_PROVIDER_RAW_DIR,
    STDOUT_LABEL_PROVIDER_SUMMARY_JSON, STDOUT_LABEL_PROVIDER_ZIP, STDOUT_LABEL_SCHEMA_VERSION,
    STDOUT_LABEL_SOURCE_PDF, STDOUT_LABEL_SUMMARY, STDOUT_LABEL_TRANSLATIONS_DIR,
};

#[derive(Clone, Copy)]
enum ArtifactField {
    JobRoot,
    SourcePdf,
    LayoutJson,
    NormalizedDocumentJson,
    NormalizationReportJson,
    ProviderRawDir,
    ProviderZip,
    ProviderSummaryJson,
    SchemaVersion,
    TranslationsDir,
    OutputPdf,
    Summary,
    BatchId,
    TaskId,
    FullZipUrl,
}

const ARTIFACT_LABEL_RULES: &[(&str, ArtifactField)] = &[
    (STDOUT_LABEL_JOB_ROOT, ArtifactField::JobRoot),
    (STDOUT_LABEL_SOURCE_PDF, ArtifactField::SourcePdf),
    (STDOUT_LABEL_LAYOUT_JSON, ArtifactField::LayoutJson),
    (
        STDOUT_LABEL_NORMALIZED_DOCUMENT_JSON,
        ArtifactField::NormalizedDocumentJson,
    ),
    (
        STDOUT_LABEL_NORMALIZATION_REPORT_JSON,
        ArtifactField::NormalizationReportJson,
    ),
    (STDOUT_LABEL_PROVIDER_RAW_DIR, ArtifactField::ProviderRawDir),
    (STDOUT_LABEL_PROVIDER_ZIP, ArtifactField::ProviderZip),
    (
        STDOUT_LABEL_PROVIDER_SUMMARY_JSON,
        ArtifactField::ProviderSummaryJson,
    ),
    (STDOUT_LABEL_SCHEMA_VERSION, ArtifactField::SchemaVersion),
    (
        STDOUT_LABEL_TRANSLATIONS_DIR,
        ArtifactField::TranslationsDir,
    ),
    (STDOUT_LABEL_OUTPUT_PDF, ArtifactField::OutputPdf),
    (STDOUT_LABEL_SUMMARY, ArtifactField::Summary),
    ("batch_id", ArtifactField::BatchId),
    ("task_id", ArtifactField::TaskId),
    ("full_zip_url", ArtifactField::FullZipUrl),
];

static PAGES_PROCESSED_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^pages processed:\s*(\d+)$").unwrap());
static TRANSLATED_ITEMS_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^translated items:\s*(\d+)$").unwrap());
static TRANSLATE_TIME_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^translation time:\s*([0-9.]+)s$").unwrap());
static SAVE_TIME_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^(?:render\+save time|save time):\s*([0-9.]+)s$").unwrap());
static TOTAL_TIME_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^total time:\s*([0-9.]+)s$").unwrap());

pub(super) fn apply_artifact_line(job: &mut JobSnapshot, line: &str) {
    for (label, field) in ARTIFACT_LABEL_RULES {
        if let Some(value) = parse_labeled_value(line, label) {
            apply_artifact_field(job, *field, value);
        }
    }
}

pub(super) fn apply_metric_line(job: &mut JobSnapshot, line: &str) {
    if let Some(caps) = PAGES_PROCESSED_RE.captures(line) {
        job_artifacts_mut(job).pages_processed = caps[1].parse::<i64>().ok();
    }
    if let Some(caps) = TRANSLATED_ITEMS_RE.captures(line) {
        job_artifacts_mut(job).translated_items = caps[1].parse::<i64>().ok();
    }
    if let Some(caps) = TRANSLATE_TIME_RE.captures(line) {
        job_artifacts_mut(job).translate_render_time_seconds = caps[1].parse::<f64>().ok();
    }
    if let Some(caps) = SAVE_TIME_RE.captures(line) {
        job_artifacts_mut(job).save_time_seconds = caps[1].parse::<f64>().ok();
    }
    if let Some(caps) = TOTAL_TIME_RE.captures(line) {
        job_artifacts_mut(job).total_time_seconds = caps[1].parse::<f64>().ok();
    }
}

fn apply_artifact_field(job: &mut JobSnapshot, field: ArtifactField, value: &str) {
    match field {
        ArtifactField::JobRoot => job_artifacts_mut(job).job_root = Some(value.to_string()),
        ArtifactField::SourcePdf => job_artifacts_mut(job).source_pdf = Some(value.to_string()),
        ArtifactField::LayoutJson => {
            let value = value.to_string();
            job_artifacts_mut(job).layout_json = Some(value.clone());
            ocr_provider_diagnostics_mut(job).artifacts.layout_json = Some(value);
        }
        ArtifactField::NormalizedDocumentJson => {
            let value = value.to_string();
            job_artifacts_mut(job).normalized_document_json = Some(value.clone());
            ocr_provider_diagnostics_mut(job)
                .artifacts
                .normalized_document_json = Some(value);
        }
        ArtifactField::NormalizationReportJson => {
            let value = value.to_string();
            job_artifacts_mut(job).normalization_report_json = Some(value.clone());
            ocr_provider_diagnostics_mut(job)
                .artifacts
                .normalization_report_json = Some(value);
            job.stage = Some("normalizing".to_string());
            job.stage_detail = Some("Generating normalized OCR document".to_string());
        }
        ArtifactField::ProviderRawDir => {
            job_artifacts_mut(job).provider_raw_dir = Some(value.to_string())
        }
        ArtifactField::ProviderZip => {
            let value = value.to_string();
            job_artifacts_mut(job).provider_zip = Some(value.clone());
            ocr_provider_diagnostics_mut(job)
                .artifacts
                .provider_bundle_zip = Some(value);
        }
        ArtifactField::ProviderSummaryJson => {
            job_artifacts_mut(job).provider_summary_json = Some(value.to_string())
        }
        ArtifactField::SchemaVersion => {
            job_artifacts_mut(job).schema_version = Some(value.to_string())
        }
        ArtifactField::TranslationsDir => {
            job_artifacts_mut(job).translations_dir = Some(value.to_string())
        }
        ArtifactField::OutputPdf => job_artifacts_mut(job).output_pdf = Some(value.to_string()),
        ArtifactField::Summary => job_artifacts_mut(job).summary = Some(value.to_string()),
        ArtifactField::BatchId => {
            ocr_provider_diagnostics_mut(job).handle.batch_id = Some(value.to_string())
        }
        ArtifactField::TaskId => {
            ocr_provider_diagnostics_mut(job).handle.task_id = Some(value.to_string())
        }
        ArtifactField::FullZipUrl => {
            ocr_provider_diagnostics_mut(job).artifacts.full_zip_url = Some(value.to_string())
        }
    }
}
