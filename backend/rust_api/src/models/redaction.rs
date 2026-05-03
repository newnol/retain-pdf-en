use serde_json::{Map, Value};

use super::input::ResolvedJobSpec;

const REDACTED_SECRET: &str = "[REDACTED]";
const SENSITIVE_JSON_KEYS: &[&str] = &["api_key", "mineru_token", "paddle_token"];

pub fn sensitive_values(spec: &ResolvedJobSpec) -> Vec<String> {
    [
        spec.translation.api_key.trim(),
        spec.ocr.mineru_token.trim(),
        spec.ocr.paddle_token.trim(),
    ]
    .into_iter()
    .filter(|value| !value.is_empty())
    .map(str::to_string)
    .collect()
}

pub fn redact_text(text: &str, secrets: &[String]) -> String {
    let mut redacted = text.to_string();
    for secret in secrets {
        if !secret.is_empty() {
            redacted = redacted.replace(secret, REDACTED_SECRET);
        }
    }
    redacted
}

pub fn redact_optional_text(value: Option<&str>, secrets: &[String]) -> Option<String> {
    value.map(|text| redact_text(text, secrets))
}

pub fn redact_json_value(value: &Value, secrets: &[String]) -> Value {
    match value {
        Value::Object(map) => Value::Object(redact_json_object(map, secrets)),
        Value::Array(items) => Value::Array(
            items
                .iter()
                .map(|item| redact_json_value(item, secrets))
                .collect(),
        ),
        Value::String(text) => Value::String(redact_text(text, secrets)),
        _ => value.clone(),
    }
}

fn redact_json_object(map: &Map<String, Value>, secrets: &[String]) -> Map<String, Value> {
    let mut redacted = Map::with_capacity(map.len());
    for (key, value) in map {
        let next = if SENSITIVE_JSON_KEYS.contains(&key.as_str()) {
            Value::String(String::new())
        } else {
            redact_json_value(value, secrets)
        };
        redacted.insert(key.clone(), next);
    }
    redacted
}
