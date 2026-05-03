use once_cell::sync::Lazy;
use regex::Regex;

use crate::ocr_provider::mineru::models::parse_envelope_fragment;
use crate::ocr_provider::types::{OcrErrorCategory, OcrProviderErrorInfo};

static PROVIDER_CODE_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"A\d{4}|-\d{3,5}").unwrap());

fn make_error(
    category: OcrErrorCategory,
    provider_code: Option<&str>,
    provider_message: impl Into<String>,
    operator_hint: Option<&str>,
    trace_id: Option<&str>,
) -> OcrProviderErrorInfo {
    OcrProviderErrorInfo {
        category,
        provider_code: provider_code.map(str::to_string),
        provider_message: Some(provider_message.into()),
        operator_hint: operator_hint.map(str::to_string),
        trace_id: trace_id.map(str::to_string),
        http_status: None,
    }
}

pub fn extract_provider_error_code(text: &str) -> Option<String> {
    if let Some(envelope) = parse_envelope_fragment(text) {
        match envelope.code {
            serde_json::Value::String(value) => {
                let trimmed = value.trim();
                if !trimmed.is_empty() {
                    return Some(trimmed.to_string());
                }
            }
            serde_json::Value::Number(value) => return Some(value.to_string()),
            _ => {}
        }
    }
    PROVIDER_CODE_RE.find(text).map(|m| m.as_str().to_string())
}

pub fn extract_provider_trace_id(text: &str) -> Option<String> {
    let envelope = parse_envelope_fragment(text)?;
    let trace = envelope.trace_id.trim();
    if trace.is_empty() {
        return None;
    }
    Some(trace.to_string())
}

pub fn extract_provider_message(text: &str) -> Option<String> {
    if let Some(envelope) = parse_envelope_fragment(text) {
        let msg = envelope.msg.trim();
        if !msg.is_empty() {
            return Some(msg.to_string());
        }
    }
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }
    Some(trimmed.to_string())
}

pub fn map_provider_error_code(
    provider_code: &str,
    provider_message: impl Into<String>,
    trace_id: Option<&str>,
) -> OcrProviderErrorInfo {
    let message = provider_message.into();
    match provider_code.trim() {
        "A0202" => make_error(
            OcrErrorCategory::Unauthorized,
            Some("A0202"),
            message,
            Some("Check if Token is correct, verify Bearer prefix or replace with new Token"),
            trace_id,
        ),
        "A0211" => make_error(
            OcrErrorCategory::CredentialExpired,
            Some("A0211"),
            message,
            Some("Replace with new Token"),
            trace_id,
        ),
        "-500" => make_error(
            OcrErrorCategory::InvalidRequest,
            Some("-500"),
            message,
            Some("Please ensure parameter types and Content-Type are correct"),
            trace_id,
        ),
        "-10001" => make_error(
            OcrErrorCategory::ServiceUnavailable,
            Some("-10001"),
            message,
            Some("Please try again later"),
            trace_id,
        ),
        "-10002" => make_error(
            OcrErrorCategory::InvalidRequest,
            Some("-10002"),
            message,
            Some("Check request parameter format"),
            trace_id,
        ),
        "-60001" => make_error(
            OcrErrorCategory::UploadLinkRequestFailed,
            Some("-60001"),
            message,
            Some("Please try again later"),
            trace_id,
        ),
        "-60002" => make_error(
            OcrErrorCategory::UnsupportedFileFormat,
            Some("-60002"),
            message,
            Some("File type detection failed, ensure the filename and URL have correct extensions and the file is one of: pdf, doc, docx, ppt, pptx, png, jpg/jpeg"),
            trace_id,
        ),
        "-60003" => make_error(
            OcrErrorCategory::FileReadFailed,
            Some("-60003"),
            message,
            Some("Please check if file is corrupted and re-upload"),
            trace_id,
        ),
        "-60004" => make_error(
            OcrErrorCategory::EmptyFile,
            Some("-60004"),
            message,
            Some("Please upload a valid file"),
            trace_id,
        ),
        "-60005" => make_error(
            OcrErrorCategory::FileTooLarge,
            Some("-60005"),
            message,
            Some("Check file size, max supported is 200MB"),
            trace_id,
        ),
        "-60006" => make_error(
            OcrErrorCategory::TooManyPages,
            Some("-60006"),
            message,
            Some("Please split the file and retry"),
            trace_id,
        ),
        "-60007" => make_error(
            OcrErrorCategory::ServiceUnavailable,
            Some("-60007"),
            message,
            Some("Please retry later or contact technical support"),
            trace_id,
        ),
        "-60008" => make_error(
            OcrErrorCategory::RemoteReadTimeout,
            Some("-60008"),
            message,
            Some("Check URL accessibility"),
            trace_id,
        ),
        "-60009" => make_error(
            OcrErrorCategory::QueueFull,
            Some("-60009"),
            message,
            Some("Please try again later"),
            trace_id,
        ),
        "-60010" => make_error(
            OcrErrorCategory::ParseFailed,
            Some("-60010"),
            message,
            Some("Please try again later"),
            trace_id,
        ),
        "-60011" => make_error(
            OcrErrorCategory::UploadedFileMissing,
            Some("-60011"),
            message,
            Some("Please ensure the file has been uploaded"),
            trace_id,
        ),
        "-60012" => make_error(
            OcrErrorCategory::TaskNotFound,
            Some("-60012"),
            message,
            Some("Please ensure task_id is valid and not deleted"),
            trace_id,
        ),
        "-60013" => make_error(
            OcrErrorCategory::PermissionDenied,
            Some("-60013"),
            message,
            Some("Can only access tasks submitted by yourself"),
            trace_id,
        ),
        "-60014" => make_error(
            OcrErrorCategory::OperationNotAllowed,
            Some("-60014"),
            message,
            Some("Running tasks cannot be deleted"),
            trace_id,
        ),
        "-60015" => make_error(
            OcrErrorCategory::ConversionFailed,
            Some("-60015"),
            message,
            Some("You can manually convert to PDF and re-upload"),
            trace_id,
        ),
        "-60016" => make_error(
            OcrErrorCategory::ConversionFailed,
            Some("-60016"),
            message,
            Some("File conversion to specified format failed, try exporting in another format or retry"),
            trace_id,
        ),
        "-60017" => make_error(
            OcrErrorCategory::RetryLimitReached,
            Some("-60017"),
            message,
            Some("Please retry after future model upgrades"),
            trace_id,
        ),
        "-60018" => make_error(
            OcrErrorCategory::QuotaExceeded,
            Some("-60018"),
            message,
            Some("Please try again tomorrow"),
            trace_id,
        ),
        "-60019" => make_error(
            OcrErrorCategory::HtmlQuotaExceeded,
            Some("-60019"),
            message,
            Some("Please try again tomorrow"),
            trace_id,
        ),
        "-60020" => make_error(
            OcrErrorCategory::FileSplitFailed,
            Some("-60020"),
            message,
            Some("Please retry later"),
            trace_id,
        ),
        "-60021" => make_error(
            OcrErrorCategory::PageCountReadFailed,
            Some("-60021"),
            message,
            Some("Please retry later"),
            trace_id,
        ),
        "-60022" => make_error(
            OcrErrorCategory::WebReadFailed,
            Some("-60022"),
            message,
            Some("Read failure may be due to network issues or rate limiting, please retry later"),
            trace_id,
        ),
        other => make_error(
            OcrErrorCategory::Unknown,
            Some(other),
            message,
            None,
            trace_id,
        ),
    }
}

pub fn classify_runtime_failure(message: &str, trace_id: Option<&str>) -> OcrProviderErrorInfo {
    let provider_message = extract_provider_message(message).unwrap_or_else(|| message.to_string());
    let resolved_trace_id = trace_id
        .map(str::to_string)
        .or_else(|| extract_provider_trace_id(message))
        .unwrap_or_default();
    let trace_ref = if resolved_trace_id.is_empty() {
        None
    } else {
        Some(resolved_trace_id.as_str())
    };

    if let Some(code) = extract_provider_error_code(message) {
        return map_provider_error_code(&code, provider_message, trace_ref);
    }
    let lowered = message.to_ascii_lowercase();
    if lowered.contains("timed out") || lowered.contains("timeout") {
        return make_error(
            OcrErrorCategory::PollTimeout,
            None,
            provider_message,
            Some("Please check if MinerU task is stuck, or increase polling timeout"),
            trace_ref,
        );
    }
    if lowered.contains("upload") {
        return make_error(
            OcrErrorCategory::UploadFailed,
            None,
            provider_message,
            Some("Please check if upload link is valid, or request a new upload URL and retry"),
            trace_ref,
        );
    }
    if lowered.contains("full_zip_url") || lowered.contains("missing field") {
        return make_error(
            OcrErrorCategory::InvalidProviderResponse,
            None,
            provider_message,
            Some("Please check if provider response structure is complete, verify full_zip_url and other key fields"),
            trace_ref,
        );
    }
    make_error(
        OcrErrorCategory::ProviderFailed,
        None,
        provider_message,
        Some("Please continue investigation using provider raw message, trace_id, and task status"),
        trace_ref,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ocr_provider::types::OcrErrorCategory;

    #[test]
    fn maps_readme_codes_60004_to_60022() {
        let cases = [
            ("-60004", OcrErrorCategory::EmptyFile, "Please upload a valid file"),
            (
                "-60005",
                OcrErrorCategory::FileTooLarge,
                "Check file size, max supported is 200MB",
            ),
            ("-60006", OcrErrorCategory::TooManyPages, "Please split the file and retry"),
            (
                "-60007",
                OcrErrorCategory::ServiceUnavailable,
                "Please retry later or contact technical support",
            ),
            (
                "-60008",
                OcrErrorCategory::RemoteReadTimeout,
                "Check URL accessibility",
            ),
            ("-60009", OcrErrorCategory::QueueFull, "Please try again later"),
            ("-60010", OcrErrorCategory::ParseFailed, "Please try again later"),
            (
                "-60011",
                OcrErrorCategory::UploadedFileMissing,
                "Please ensure the file has been uploaded",
            ),
            (
                "-60012",
                OcrErrorCategory::TaskNotFound,
                "Please ensure task_id is valid and not deleted",
            ),
            (
                "-60013",
                OcrErrorCategory::PermissionDenied,
                "Can only access tasks submitted by yourself",
            ),
            (
                "-60014",
                OcrErrorCategory::OperationNotAllowed,
                "Running tasks cannot be deleted",
            ),
            (
                "-60015",
                OcrErrorCategory::ConversionFailed,
                "You can manually convert to PDF and re-upload",
            ),
            (
                "-60016",
                OcrErrorCategory::ConversionFailed,
                "File conversion to specified format failed, try exporting in another format or retry",
            ),
            (
                "-60017",
                OcrErrorCategory::RetryLimitReached,
                "Please retry after future model upgrades",
            ),
            ("-60018", OcrErrorCategory::QuotaExceeded, "Please try again tomorrow"),
            ("-60019", OcrErrorCategory::HtmlQuotaExceeded, "Please try again tomorrow"),
            ("-60020", OcrErrorCategory::FileSplitFailed, "Please retry later"),
            (
                "-60021",
                OcrErrorCategory::PageCountReadFailed,
                "Please retry later",
            ),
            (
                "-60022",
                OcrErrorCategory::WebReadFailed,
                "Read failure may be due to network issues or rate limiting, please retry later",
            ),
        ];
        for (code, category, hint) in cases {
            let mapped = map_provider_error_code(code, "provider says no", Some("trace-1"));
            assert_eq!(mapped.provider_code.as_deref(), Some(code));
            assert_eq!(mapped.category, category, "code={code}");
            assert_eq!(mapped.operator_hint.as_deref(), Some(hint), "code={code}");
            assert_eq!(mapped.trace_id.as_deref(), Some("trace-1"));
            assert_eq!(mapped.provider_message.as_deref(), Some("provider says no"));
        }
    }

    #[test]
    fn extracts_and_maps_code_from_runtime_message() {
        let mapped =
            classify_runtime_failure("MinerU API error -60011: missing upload object", None);
        assert_eq!(mapped.category, OcrErrorCategory::UploadedFileMissing);
        assert_eq!(mapped.provider_code.as_deref(), Some("-60011"));
    }

    #[test]
    fn extracts_trace_and_message_from_embedded_json() {
        let text = r#"requests failed: {"code":-60011,"msg":"Failed to get valid file","trace_id":"trace-xyz","data":null}"#;
        let mapped = classify_runtime_failure(text, None);
        assert_eq!(mapped.provider_code.as_deref(), Some("-60011"));
        assert_eq!(mapped.provider_message.as_deref(), Some("Failed to get valid file"));
        assert_eq!(mapped.trace_id.as_deref(), Some("trace-xyz"));
        assert_eq!(mapped.operator_hint.as_deref(), Some("Please ensure the file has been uploaded"));
    }
}
