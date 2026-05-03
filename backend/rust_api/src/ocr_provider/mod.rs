mod catalog;
pub mod mineru;
pub mod paddle;
pub mod types;

use anyhow::{bail, Result};

#[allow(unused_imports)]
pub use catalog::{
    ensure_provider_diagnostics, is_supported_provider, provider_capabilities, provider_definition,
    provider_display_name, provider_model_version, provider_token, provider_token_env_name,
    provider_token_field_name, supported_provider_keys,
};
pub use types::{
    OcrArtifactSet, OcrErrorCategory, OcrProviderCapabilities, OcrProviderDiagnostics,
    OcrProviderErrorInfo, OcrProviderKind, OcrTaskHandle, OcrTaskState, OcrTaskStatus,
};

pub fn parse_provider_kind(value: &str) -> OcrProviderKind {
    match value.trim().to_ascii_lowercase().as_str() {
        "mineru" => OcrProviderKind::Mineru,
        "paddle" => OcrProviderKind::Paddle,
        _ => OcrProviderKind::Unknown,
    }
}

pub fn require_supported_provider(value: &str) -> Result<OcrProviderKind> {
    let kind = parse_provider_kind(value);
    if !is_supported_provider(&kind) {
        bail!("unsupported OCR provider: {}", value.trim());
    }
    Ok(kind)
}
