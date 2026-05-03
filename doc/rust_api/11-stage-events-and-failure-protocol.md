# Stage Events and Failure Protocol

This document describes the formal event/failure conventions currently adopted by `Rust API` and `Python worker`, as well as the backward-compatible fields still retained.

The goal is not to invent another new protocol, but to clarify:

- Which fields are formal sources of truth
- Which fields are only compatibility projections
- How main pipeline stages and provider private stages are layered

## 1. Current Formal Conventions

As of 2026-04-25, this protocol has been implemented as follows:

- Python worker writes `logs/pipeline_events.jsonl`
- Rust query layer merges DB events and `pipeline_events.jsonl`
- Rust detail/list prioritizes live stage snapshots from `pipeline_events.jsonl`
- Both Rust and Python support structured `failure`
- `failure_diagnostic` is still retained but only as a compatibility projection

That is, the current formal source is no longer:

- The old `events` log file convention
- Pure stdout text stage guessing
- Relying solely on `failure_diagnostic` for failure expression

## 2. Stage Layering Rules

The formal top-level `stage` only represents unified main pipeline stages:

- `queued`
- `startup`
- `ocr_submitting`
- `ocr_processing`
- `normalization`
- `translation_prepare`
- `domain_inference`
- `continuation_review`
- `page_policies`
- `translating`
- `render_prepare`
- `rendering`
- `saving`
- `finished`
- `failed`
- `canceled`

Provider private states can only appear in:

- `provider`
- `provider_stage`

For example:

```json
{
  "stage": "ocr_processing",
  "provider": "mineru",
  "provider_stage": "mineru_processing"
}
```

Therefore:

- `mineru_upload`, `mineru_processing`, `paddle_running`

These can no longer be used as formal top-level `stage` examples.

## 3. Formal Event Object

The current event query endpoint returns a unified event object; old fields are retained, new fields take priority.

Example:

```json
{
  "job_id": "job-123",
  "seq": 12,
  "ts": "2026-04-24T10:12:33Z",
  "level": "info",
  "stage": "translating",
  "stage_detail": "Completed batch 18/55 translation",
  "provider": "paddle",
  "provider_stage": "",
  "event_type": "stage_progress",
  "event": "stage_progress",
  "message": "Completed batch 18/55 translation",
  "progress_current": 18,
  "progress_total": 55,
  "retry_count": 0,
  "elapsed_ms": 193822,
  "payload": {
    "origin": "python"
  }
}
```

Field meanings:

- `stage`
  Main pipeline unified stage
- `stage_detail`
  Stage details for direct frontend display
- `provider`
  Current provider name
- `provider_stage`
  Provider private state
- `event_type`
  Formal event type
- `event`
  Legacy compatibility field; defaults to syncing with `event_type`
- `message`
  Legacy compatibility text; formal semantics prefer `stage_detail` and `event_type`
- `progress_current` / `progress_total`
  Formal progress fields
- `payload`
  Extension field container; does not carry main semantics

Currently recommended `event_type` values:

- `job_created`
- `status_changed`
- `stage_transition`
- `stage_progress`
- `artifact_published`
- `job_error`
- `job_terminal`
- `diagnostic`

## 4. Formal Failure Object

The formal failure object in the current job detail response is `failure`.

Example:

```json
{
  "failed_stage": "translation_prepare",
  "provider": "mineru",
  "provider_stage": "mineru_processing",
  "failure_code": "auth_failed",
  "failure_category": "auth",
  "provider_code": "A0211",
  "summary": "Authentication failed",
  "root_cause": "token expired",
  "retryable": false,
  "upstream_host": "mineru.example.test",
  "suggestion": "Check provider token",
  "last_log_line": "token expired during mineru_processing",
  "raw_excerpt": "token expired"
}
```

Field layering:

- `failed_stage`
  Top-level unified failure stage
- `provider` / `provider_stage`
  Provider-side attribution information
- `failure_code`
  Stable machine-readable code
- `failure_category`
  Coarse-grained error grouping
- `provider_code`
  Upstream provider original error code
- `summary` / `root_cause` / `suggestion`
  Human-readable information for frontend and operators
- `raw_excerpt`
  Sanitized original excerpt

## 5. Compatibility Field Strategy

The following fields are still currently retained:

- `JobDetailView.stage`
- `JobDetailView.stage_detail`
- `JobDetailView.failure_diagnostic`
- `JobEventRecord.event`
- `JobEventRecord.message`
- `JobEventRecord.payload`

But their roles are now fixed:

- `stage` / `stage_detail`
  Still the main external display fields, but data source prioritizes live pipeline events
- `failure_diagnostic`
  Only as a legacy projection of `failure`
- `event`
  Backward compatibility for old clients
- `message`
  Backward compatibility for old clients or debug display
- `payload`
  Extension information; does not carry formal main semantics

Recommended mapping:

- `failure_diagnostic.failed_stage` -> `failure.failed_stage`
- `failure_diagnostic.error_kind` -> `failure.failure_code`
- `failure_diagnostic.summary` -> `failure.summary`
- `failure_diagnostic.root_cause` -> `failure.root_cause`
- `failure_diagnostic.retryable` -> `failure.retryable`

## 6. Rust's Current Consumption Method

Rust now has two formal consumption layers:

1. event list
   Merges DB events and `pipeline_events.jsonl`
2. live stage
   detail/list selects the latest displayable stage snapshot from the unified event stream

Current priority rules:

- If a usable live stage exists in `pipeline_events.jsonl`, it takes priority over the stale `job.stage` in DB
- `artifact_published` does not overwrite live stage display
- Failure-related output prioritizes the formal `failure` field; no longer reverse-engineers from the old `failure_diagnostic`

## 7. Remaining Unfinished Items

What has not been fully completed falls into only these categories:

- More fine-grained provider polling events have not all been standardized into unified `event_type` values
- The stdout parser still exists, but its role has been narrowed to compatibility supplement rather than formal event source
- A few historical documents and notes may still contain old terminology; continued cleanup is needed

## 8. Acceptance Criteria

If all of the following hold, the protocol can be considered stable:

- The frontend no longer needs to guess failure reasons from `log_tail`
- detail / list / events use the same live stage priority for the same task
- Provider private stages only appear in `provider_stage`
- `failure_diagnostic` only exists as a compatibility field
- When onboarding new providers, only the unified `stage` / `event_type` / `failure` protocol needs to be populated; no new convention needs to be defined
