use std::path::Path;

use serde_json::Value;

use crate::error::AppError;

pub(super) fn read_json_value(path: &Path) -> Result<Value, AppError> {
    let text = std::fs::read_to_string(path)?;
    serde_json::from_str(&text)
        .map_err(|err| AppError::internal(format!("parse json {}: {err}", path.display())))
}
