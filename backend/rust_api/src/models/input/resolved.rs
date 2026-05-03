use serde::{Deserialize, Serialize};

use crate::models::{
    build_job_id, CreateJobInput, OcrInput, RenderInput, ResolvedSourceSpec, RuntimeInput,
    TranslationInput, WorkflowKind,
};

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct ResolvedJobSpec {
    pub workflow: WorkflowKind,
    pub job_id: String,
    pub source: ResolvedSourceSpec,
    pub ocr: OcrInput,
    pub translation: TranslationInput,
    pub render: RenderInput,
    pub runtime: RuntimeInput,
}

impl ResolvedJobSpec {
    pub fn from_input(input: CreateJobInput) -> Self {
        let job_id = if input.runtime.job_id.trim().is_empty() {
            build_job_id()
        } else {
            input.runtime.job_id.trim().to_string()
        };
        Self {
            workflow: input.workflow,
            job_id,
            source: ResolvedSourceSpec {
                upload_id: input.source.upload_id.trim().to_string(),
                source_url: input.source.source_url.trim().to_string(),
                artifact_job_id: input.source.artifact_job_id.trim().to_string(),
            },
            ocr: input.ocr,
            translation: input.translation,
            render: input.render,
            runtime: input.runtime,
        }
    }

    pub fn resolved_workers(&self) -> i64 {
        if self.translation.workers > 0 {
            return self.translation.workers;
        }
        let model = self.translation.model.to_lowercase();
        let base = self.translation.base_url.to_lowercase();
        if model.contains("deepseek") || base.contains("deepseek.com") {
            100
        } else {
            4
        }
    }
}

impl From<CreateJobInput> for ResolvedJobSpec {
    fn from(value: CreateJobInput) -> Self {
        ResolvedJobSpec::from_input(value)
    }
}
