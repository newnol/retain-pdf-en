use std::error::Error;
use std::fmt;

use reqwest::StatusCode;

use crate::ocr_provider::types::{OcrErrorCategory, OcrProviderErrorInfo};

#[derive(Debug, Clone)]
pub struct PaddleProviderError {
    stage: &'static str,
    detail: String,
    info: OcrProviderErrorInfo,
}

impl PaddleProviderError {
    pub fn request_failed(
        stage: &'static str,
        err: &reqwest::Error,
        trace_id: Option<&str>,
    ) -> Self {
        if let Some(status) = err.status() {
            return Self::http_status(
                stage,
                status,
                &err.to_string(),
                trace_id,
                Some("Paddle HTTP request returned error status"),
            );
        }
        let category = if err.is_timeout() {
            OcrErrorCategory::RemoteReadTimeout
        } else {
            OcrErrorCategory::ServiceUnavailable
        };
        Self::new(
            stage,
            category,
            err.to_string(),
            trace_id,
            None,
            None,
            Some("Please check Paddle service reachability, network connectivity, and timeout configuration"),
        )
    }

    pub fn http_status(
        stage: &'static str,
        status: StatusCode,
        body_excerpt: &str,
        trace_id: Option<&str>,
        detail: Option<&str>,
    ) -> Self {
        let category = match status {
            StatusCode::UNAUTHORIZED => OcrErrorCategory::Unauthorized,
            StatusCode::FORBIDDEN => OcrErrorCategory::PermissionDenied,
            StatusCode::REQUEST_TIMEOUT | StatusCode::GATEWAY_TIMEOUT => {
                OcrErrorCategory::RemoteReadTimeout
            }
            StatusCode::BAD_REQUEST
            | StatusCode::UNPROCESSABLE_ENTITY
            | StatusCode::METHOD_NOT_ALLOWED => OcrErrorCategory::InvalidRequest,
            StatusCode::TOO_MANY_REQUESTS => OcrErrorCategory::QueueFull,
            StatusCode::SERVICE_UNAVAILABLE | StatusCode::BAD_GATEWAY => {
                OcrErrorCategory::ServiceUnavailable
            }
            _ if status.is_server_error() => OcrErrorCategory::ServiceUnavailable,
            _ => OcrErrorCategory::HttpStatus,
        };
        let message = format!(
            "HTTP {}{}",
            status.as_u16(),
            sanitize_body_excerpt(body_excerpt)
                .map(|text| format!(": {text}"))
                .unwrap_or_default()
        );
        Self::new(
            stage,
            category,
            detail.unwrap_or("Paddle HTTP request failed").to_string(),
            trace_id,
            None,
            Some(message),
            Some("Please check Paddle API address, Token, and service status"),
        )
        .with_http_status(status.as_u16())
    }

    pub fn provider_error(
        stage: &'static str,
        provider_code: i64,
        provider_message: &str,
        trace_id: Option<&str>,
    ) -> Self {
        let category = match provider_code {
            401 | 403 => OcrErrorCategory::Unauthorized,
            404 => OcrErrorCategory::TaskNotFound,
            408 => OcrErrorCategory::RemoteReadTimeout,
            409 => OcrErrorCategory::OperationNotAllowed,
            429 => OcrErrorCategory::QueueFull,
            code if code >= 500 => OcrErrorCategory::ServiceUnavailable,
            _ => OcrErrorCategory::ProviderFailed,
        };
        Self::new(
            stage,
            category,
            format!("Paddle returned errorCode={provider_code}"),
            trace_id,
            Some(provider_code.to_string()),
            Some(provider_message.trim().to_string()),
            Some("Please investigate using Paddle provider_message and trace_id"),
        )
    }

    pub fn invalid_response(
        stage: &'static str,
        detail: impl Into<String>,
        trace_id: Option<&str>,
    ) -> Self {
        Self::new(
            stage,
            OcrErrorCategory::InvalidProviderResponse,
            detail.into(),
            trace_id,
            None,
            None,
            Some("Please check if Paddle response structure is complete, verify data/jobId/resultUrl.jsonUrl"),
        )
    }

    pub fn provider_failed(provider_message: &str, trace_id: Option<&str>) -> Self {
        Self::new(
            "poll",
            OcrErrorCategory::ProviderFailed,
            "Paddle task execution failed".to_string(),
            trace_id,
            None,
            Some(provider_message.trim().to_string()),
            Some("Please continue investigation using Paddle provider_message, trace_id, and task status"),
        )
    }

    pub fn result_download_failed(
        detail: impl Into<String>,
        trace_id: Option<&str>,
        http_status: Option<u16>,
    ) -> Self {
        Self::new(
            "download",
            OcrErrorCategory::ResultDownloadFailed,
            detail.into(),
            trace_id,
            None,
            None,
            Some("Please check if Paddle jsonUrl is accessible, or retry later"),
        )
        .with_http_status_opt(http_status)
    }

    pub fn result_unpack_failed(detail: impl Into<String>, trace_id: Option<&str>) -> Self {
        Self::new(
            "download",
            OcrErrorCategory::ResultUnpackFailed,
            detail.into(),
            trace_id,
            None,
            None,
            Some("Please check if Paddle JSONL response is complete and each line is valid JSON"),
        )
    }

    pub fn poll_timeout(job_id: &str) -> Self {
        Self::new(
            "poll",
            OcrErrorCategory::PollTimeout,
            format!("Timed out waiting for Paddle task {job_id}"),
            None,
            None,
            None,
            Some("Please check if Paddle task is stuck, or increase polling timeout"),
        )
    }

    pub fn info(&self) -> &OcrProviderErrorInfo {
        &self.info
    }

    pub fn stage_detail(&self) -> String {
        let prefix = match self.stage {
            "submit" => "Paddle submission failed",
            "poll" => "Paddle polling failed",
            "download" => "Paddle result download failed",
            _ => "Paddle provider failed",
        };
        let message = self
            .info
            .provider_message
            .as_deref()
            .filter(|value| !value.trim().is_empty())
            .unwrap_or(self.detail.as_str());
        let trace_suffix = self
            .info
            .trace_id
            .as_deref()
            .filter(|value| !value.trim().is_empty())
            .map(|value| format!(" trace_id={value}"))
            .unwrap_or_default();
        format!("{prefix}: {message}{trace_suffix}")
    }

    fn new(
        stage: &'static str,
        category: OcrErrorCategory,
        detail: String,
        trace_id: Option<&str>,
        provider_code: Option<String>,
        provider_message: Option<String>,
        operator_hint: Option<&str>,
    ) -> Self {
        Self {
            stage,
            detail,
            info: OcrProviderErrorInfo {
                category,
                provider_code,
                provider_message,
                operator_hint: operator_hint.map(str::to_string),
                trace_id: trace_id
                    .map(str::trim)
                    .filter(|value| !value.is_empty())
                    .map(str::to_string),
                http_status: None,
            },
        }
    }

    fn with_http_status(mut self, http_status: u16) -> Self {
        self.info.http_status = Some(http_status);
        self
    }

    fn with_http_status_opt(mut self, http_status: Option<u16>) -> Self {
        self.info.http_status = http_status;
        self
    }
}

impl fmt::Display for PaddleProviderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.detail)
    }
}

impl Error for PaddleProviderError {}

fn sanitize_body_excerpt(text: &str) -> Option<String> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }
    let single_line = trimmed.replace('\n', " ");
    let excerpt: String = single_line.chars().take(180).collect();
    Some(excerpt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn http_status_maps_unauthorized() {
        let err = PaddleProviderError::http_status(
            "submit",
            StatusCode::UNAUTHORIZED,
            r#"{"message":"bad token"}"#,
            Some("trace-1"),
            None,
        );

        assert_eq!(err.info().category, OcrErrorCategory::Unauthorized);
        assert_eq!(err.info().http_status, Some(401));
        assert_eq!(err.info().trace_id.as_deref(), Some("trace-1"));
    }

    #[test]
    fn provider_error_preserves_code_and_message() {
        let err = PaddleProviderError::provider_error("poll", 429, "busy", Some("trace-2"));

        assert_eq!(err.info().category, OcrErrorCategory::QueueFull);
        assert_eq!(err.info().provider_code.as_deref(), Some("429"));
        assert_eq!(err.info().provider_message.as_deref(), Some("busy"));
    }

    #[test]
    fn poll_timeout_uses_poll_timeout_category() {
        let err = PaddleProviderError::poll_timeout("job-1");

        assert_eq!(err.info().category, OcrErrorCategory::PollTimeout);
        assert!(err.to_string().contains("job-1"));
    }
}
