use crate::error::AppError;
use crate::models::{CreateJobInput, OcrProviderKind, UploadRecord};
use crate::ocr_provider::{
    parse_provider_kind, provider_display_name, provider_token, provider_token_field_name,
    require_supported_provider,
};

const MINERU_MAX_BYTES: u64 = 200 * 1024 * 1024;
const MINERU_MAX_PAGES: u32 = 600;

pub fn validate_provider_credentials(input: &CreateJobInput) -> Result<(), AppError> {
    let provider_kind = require_supported_provider(input.ocr.provider.trim())
        .map_err(|err| AppError::bad_request(err.to_string()))?;
    validate_provider_token(input, &provider_kind)?;

    let base_url = input.translation.base_url.trim();
    if base_url.is_empty() {
        return Err(AppError::bad_request("base_url is required"));
    }
    if !(base_url.starts_with("http://") || base_url.starts_with("https://")) {
        return Err(AppError::bad_request(
            "base_url must start with http:// or https://",
        ));
    }

    let api_key = input.translation.api_key.trim();
    if api_key.is_empty() {
        return Err(AppError::bad_request("api_key is required"));
    }
    if looks_like_url(api_key) {
        return Err(AppError::bad_request(
            "api_key looks like a URL, not a model API key; check whether frontend fields were mixed up",
        ));
    }
    if input.translation.model.trim().is_empty() {
        return Err(AppError::bad_request("model is required"));
    }
    Ok(())
}

pub fn validate_ocr_provider_request(input: &CreateJobInput) -> Result<(), AppError> {
    let provider = input.ocr.provider.trim();
    if provider.is_empty() {
        return Err(AppError::bad_request("provider is required"));
    }
    let provider_kind = require_supported_provider(provider)
        .map_err(|err| AppError::bad_request(err.to_string()))?;
    validate_provider_token(input, &provider_kind)?;
    if !input.source.source_url.trim().is_empty()
        && !(input.source.source_url.starts_with("http://")
            || input.source.source_url.starts_with("https://"))
    {
        return Err(AppError::bad_request(
            "source_url must start with http:// or https://",
        ));
    }
    if input.runtime.timeout_seconds <= 0 {
        return Err(AppError::bad_request(
            "timeout_seconds must be a positive integer",
        ));
    }
    Ok(())
}

pub fn validate_mineru_upload_limits(
    input: &CreateJobInput,
    upload: &UploadRecord,
) -> Result<(), AppError> {
    if !request_uses_mineru(input) {
        return Ok(());
    }
    if upload.bytes >= MINERU_MAX_BYTES {
        return Err(AppError::bad_request(format!(
            "MinerU API limit: PDF file size must be less than 200MB; current file is {:.2}MB",
            upload.bytes as f64 / 1024.0 / 1024.0
        )));
    }
    if upload.page_count > MINERU_MAX_PAGES {
        return Err(AppError::bad_request(format!(
            "MinerU API limit: PDF page count must not exceed 600 pages; current file has {} pages",
            upload.page_count
        )));
    }
    Ok(())
}

fn request_uses_mineru(input: &CreateJobInput) -> bool {
    parse_provider_kind(&input.ocr.provider) == OcrProviderKind::Mineru
}

fn looks_like_url(value: &str) -> bool {
    let value = value.trim().to_ascii_lowercase();
    value.starts_with("http://") || value.starts_with("https://")
}

fn validate_provider_token(
    input: &CreateJobInput,
    provider_kind: &OcrProviderKind,
) -> Result<(), AppError> {
    let token = provider_token(provider_kind, &input.ocr);
    let field_name = provider_token_field_name(provider_kind).unwrap_or("provider_token");
    let display_name = provider_display_name(provider_kind).unwrap_or("Provider");
    if token.is_empty() {
        return Err(AppError::bad_request(format!("{field_name} is required")));
    }
    if looks_like_url(token) {
        return Err(AppError::bad_request(format!(
            "{field_name} looks like a URL, not a {display_name} API key; check whether frontend fields were mixed up",
        )));
    }
    Ok(())
}
