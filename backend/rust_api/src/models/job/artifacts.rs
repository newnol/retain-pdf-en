use serde::{Deserialize, Serialize};

use crate::models::{JobStatusKind, OcrProviderDiagnostics};

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct JobArtifacts {
    pub ocr_job_id: Option<String>,
    pub ocr_status: Option<JobStatusKind>,
    pub ocr_trace_id: Option<String>,
    pub ocr_provider_trace_id: Option<String>,
    pub job_root: Option<String>,
    pub source_pdf: Option<String>,
    pub layout_json: Option<String>,
    pub normalized_document_json: Option<String>,
    pub normalization_report_json: Option<String>,
    pub provider_raw_dir: Option<String>,
    pub provider_zip: Option<String>,
    pub provider_summary_json: Option<String>,
    pub schema_version: Option<String>,
    pub trace_id: Option<String>,
    pub provider_trace_id: Option<String>,
    pub translations_dir: Option<String>,
    pub output_pdf: Option<String>,
    pub summary: Option<String>,
    pub pages_processed: Option<i64>,
    pub translated_items: Option<i64>,
    pub translate_render_time_seconds: Option<f64>,
    pub save_time_seconds: Option<f64>,
    pub total_time_seconds: Option<f64>,
    pub ocr_provider_diagnostics: Option<OcrProviderDiagnostics>,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq, Eq)]
pub struct JobArtifactRecord {
    pub job_id: String,
    pub artifact_key: String,
    pub artifact_group: String,
    pub artifact_kind: String,
    pub relative_path: String,
    pub file_name: Option<String>,
    pub content_type: String,
    pub ready: bool,
    pub size_bytes: Option<u64>,
    pub checksum: Option<String>,
    pub source_stage: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}
