use crate::job_failure::classify_job_failure;
use crate::models::{
    redact_json_value, redact_optional_text, redact_text, sensitive_values, JobEventRecord,
    JobFailureInfo, JobSnapshot,
};

pub fn redacted_error(job: &JobSnapshot) -> Option<String> {
    let secrets = sensitive_values(&job.request_payload);
    redact_optional_text(job.error.as_deref(), &secrets)
}

pub fn redacted_log_tail(job: &JobSnapshot) -> Vec<String> {
    let secrets = sensitive_values(&job.request_payload);
    job.log_tail
        .iter()
        .map(|line| redact_text(line, &secrets))
        .collect()
}

pub fn redact_job_events(job: &JobSnapshot, items: Vec<JobEventRecord>) -> Vec<JobEventRecord> {
    let secrets = sensitive_values(&job.request_payload);
    let resolved_failure = job
        .failure
        .clone()
        .map(JobFailureInfo::with_formal_fields)
        .or_else(|| classify_job_failure(job).map(JobFailureInfo::with_formal_fields));
    items
        .into_iter()
        .map(|mut item| {
            normalize_failure_event(&mut item, resolved_failure.as_ref());
            item.message = redact_text(&item.message, &secrets);
            item.stage_detail = item
                .stage_detail
                .as_deref()
                .map(|value| redact_text(value, &secrets));
            item.payload = item
                .payload
                .as_ref()
                .map(|payload| redact_json_value(payload, &secrets));
            item
        })
        .collect()
}

fn normalize_failure_event(item: &mut JobEventRecord, resolved_failure: Option<&JobFailureInfo>) {
    let is_failure_event = matches!(item.event.as_str(), "failure_classified" | "job_terminal")
        || matches!(
            item.event_type.as_deref(),
            Some("failure_classified" | "job_terminal")
        );
    if !is_failure_event {
        return;
    }

    let payload_failure = item
        .payload
        .as_ref()
        .and_then(JobFailureInfo::from_json_value)
        .map(|failure| match resolved_failure {
            Some(fallback) => failure.merge_missing_from(fallback),
            None => failure,
        });
    let failure = payload_failure.or_else(|| resolved_failure.cloned());
    let Some(failure) = failure else {
        return;
    };

    item.stage = Some(failure.failed_stage_value().to_string());
    item.provider = failure
        .provider
        .clone()
        .or_else(|| take_non_empty(item.provider.take()));
    item.provider_stage = failure
        .provider_stage
        .clone()
        .or_else(|| take_non_empty(item.provider_stage.take()));
    if item
        .stage_detail
        .as_deref()
        .map(str::trim)
        .unwrap_or("")
        .is_empty()
    {
        item.stage_detail = Some(failure.summary.clone());
    }
    if item.message.trim().is_empty() {
        item.message = failure.summary.clone();
    }
    item.payload = Some(failure.write_formal_fields_into_payload(item.payload.as_ref()));
}

fn take_non_empty(value: Option<String>) -> Option<String> {
    value.and_then(|item| {
        if item.trim().is_empty() {
            None
        } else {
            Some(item)
        }
    })
}
