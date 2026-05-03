use std::path::PathBuf;

use crate::error::AppError;
use axum::body::Body;
use axum::http::{header, HeaderValue, StatusCode};
use axum::response::Response;
use tokio_util::io::ReaderStream;

pub async fn stream_file(
    path: PathBuf,
    content_type: &str,
    download_name: Option<String>,
) -> Result<Response, AppError> {
    if !path.exists() || !path.is_file() {
        return Err(AppError::not_found(format!(
            "file not found: {}",
            path.display()
        )));
    }
    let file = tokio::fs::File::open(&path).await?;
    let stream = ReaderStream::new(file);
    let body = Body::from_stream(stream);
    let mut response = Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, content_type)
        .body(body)
        .map_err(|e| AppError::internal(e.to_string()))?;
    if let Some(name) = download_name {
        let value = format!("attachment; filename=\"{name}\"");
        response.headers_mut().insert(
            header::CONTENT_DISPOSITION,
            HeaderValue::from_str(&value).map_err(|e| AppError::internal(e.to_string()))?,
        );
    }
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::to_bytes;

    #[tokio::test]
    async fn stream_file_sets_content_disposition_when_download_name_provided() {
        let temp_path = std::env::temp_dir().join(format!(
            "job-helpers-stream-{}-{}.txt",
            std::process::id(),
            fastrand::u64(..)
        ));
        tokio::fs::write(&temp_path, b"hello world")
            .await
            .expect("write temp file");

        let response = stream_file(
            temp_path.clone(),
            "text/plain",
            Some("result.txt".to_string()),
        )
        .await
        .expect("stream response");

        let content_type = response
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok());
        let content_disposition = response
            .headers()
            .get(header::CONTENT_DISPOSITION)
            .and_then(|value| value.to_str().ok());
        assert_eq!(content_type, Some("text/plain"));
        assert_eq!(
            content_disposition,
            Some("attachment; filename=\"result.txt\"")
        );

        let body = to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read response body");
        assert_eq!(body.as_ref(), b"hello world");

        let _ = tokio::fs::remove_file(temp_path).await;
    }
}
