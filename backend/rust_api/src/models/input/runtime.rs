use serde::{Deserialize, Serialize};

use crate::models::defaults::default_timeout_seconds;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct RuntimeInput {
    #[serde(default)]
    pub job_id: String,
    #[serde(default = "default_timeout_seconds")]
    pub timeout_seconds: i64,
}

impl Default for RuntimeInput {
    fn default() -> Self {
        Self {
            job_id: String::new(),
            timeout_seconds: default_timeout_seconds(),
        }
    }
}
