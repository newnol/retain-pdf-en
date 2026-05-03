# Job Details and Timeline

## 1. Main Endpoint

The main endpoint for the job details page is:

`GET /api/v1/jobs/{job_id}`

Most of the core information for the details page should be fetched from this single endpoint:

- Current status
- Current stage
- Current stage description
- Runtime timeline
- Failure attribution
- Download button state
- OCR sub-task summary
- Current task execution protocol summary
- Normalization summary and glossary summary

## 2. Fields Frontend Should Care About Most

Key fields are in `data`:

- `request_payload`
- `status`
- `stage`
- `stage_detail`
- `runtime`
- `failure`
- `actions`
- `artifacts`
- `timestamps`
- `log_tail`
- `normalization_summary`
- `glossary_summary`
- `invocation`

Where:

- `request_payload` is the snapshot of request parameters actually saved by the backend for this task
- During integration testing, if you need to confirm whether a certain parameter was received by the backend, check here first
- For example, OCR page range should be read as: `data.request_payload.ocr.page_ranges`
- Formula translation mode should be read as: `data.request_payload.translation.math_mode`
- `invocation` answers "whether this task was run via the legacy path or the current stage spec path"
- `normalization_summary` answers "whether the normalization result uses the current `schema_version=1.1` and whether default value consolidation occurred"
- `glossary_summary` answers "whether the glossary is enabled, and the hit/miss statistics"

## 3. How to Check the Execution Protocol for New Tasks

Current new tasks should show:

```json
{
  "invocation": {
    "stage": "provider",
    "input_protocol": "stage_spec",
    "stage_spec_schema_version": "provider.stage.v1"
  }
}
```

Integration testing judgment principles:

- `input_protocol=stage_spec` indicates the task used the current spec-only worker
- `stage_spec_schema_version` indicates the specific stage spec version
- If this information is not available, it doesn't necessarily mean the endpoint is broken; it could be that historical tasks did not retain this summary

## 4. Timeline Source of Truth

"Overview -> Process Timeline" must be based on `runtime.stage_history`.

Do not reverse-engineer the main timeline from `/events`. The reason is straightforward:

- `runtime.stage_history` is already the backend-organized stage segments
- Each segment has entry and exit timestamps
- Each segment can directly attach terminal state information
- The frontend does not need to do merging, deduplication, or inference

## 5. Key Fields in `runtime`

Current key fields:

- `current_stage`
- `stage_started_at`
- `last_stage_transition_at`
- `total_elapsed_ms`
- `active_stage_elapsed_ms`
- `retry_count`
- `last_retry_at`
- `terminal_reason`
- `final_failure_category`
- `final_failure_summary`
- `stage_history`

## 6. Fixed Structure of `stage_history`

Each entry is a stage time segment:

```json
{
  "stage": "translating",
  "detail": "Translating, batch 12/22",
  "enter_at": "2026-04-04T15:31:02Z",
  "exit_at": null,
  "duration_ms": null,
  "terminal_status": null
}
```

Field meanings:

- `stage`: Stage name
- `detail`: Main description when entering that stage
- `enter_at`: Time when the stage was entered
- `exit_at`: Time when the stage was exited; usually null for the currently active stage
- `duration_ms`: Only stable when the stage is completed; usually null for the currently active stage
- `terminal_status`: If this is the last stage before completion, it can be marked as `succeeded / failed / canceled`

## 7. How to Read Running Tasks

If a task is still running:

- The currently active stage will also appear in `stage_history`
- That entry typically has `exit_at = null`
- That entry typically has `duration_ms = null`
- The real-time elapsed time for the current stage should be read from `runtime.active_stage_elapsed_ms`

This means the frontend should not compute display values by doing "current time - enter_at" on its own, unless just for local frame interpolation; the API source of truth should still be `active_stage_elapsed_ms`.

## 8. How to Read Completed Tasks

If a task has ended:

- `status` will be `succeeded / failed / canceled`
- `runtime.terminal_reason` will explain the terminal state reason
- `runtime.total_elapsed_ms` is the total elapsed time for the entire pipeline
- The last entry in `runtime.stage_history` will typically carry `terminal_status`

## 9. How to Understand `normalization_summary`

The `normalization_summary` in the current task details is a lightweight summary, not a full report.

Key fields:

- `provider`
- `detected_provider`
- `schema`
- `schema_version`
- `document_defaults`
- `page_defaults`
- `block_defaults`
- `page_count`
- `block_count`

Recommended frontend usage:

- Page display should only read this summary
- If you truly need to troubleshoot adapter/defaults/validation details, download `artifacts.normalization_report`

Note:

- The current main pipeline only accepts `schema_version=1.1`
- The `*_defaults` fields here represent the count of default value consolidations, no longer called `compat_*`

## 10. Why Historical Tasks May Not Have a Timeline

This is the most common source of misjudgment recently.

Historical old tasks may have:

```json
{
  "runtime": null
}
```

This does NOT mean:

- The frontend read it wrong
- The current backend is broken
- The current task failed to write

It only means:

- When this task was created and executed, the backend had not yet persisted the runtime timeline to the database

So the frontend should treat such tasks as "missing historical data".

## 11. "Historical Task Missing Fields" and "Old Task Rejected" Are Not the Same Thing

These are the two concepts most easily confused during recent integration testing:

- `runtime = null`
  - This is missing historical data
  - The task itself may still be viewable with details and event streams
- Details/download endpoint directly reports "old task not supported"
  - This means the task is still using the old directory layout or old artifact storage method
  - The current backend will no longer perform compatibility migration for it; it must be re-run

## 12. Guarantee Scope

The guarantee scope in the current documentation is:

- The task was created by the new backend
- The task was fully executed by the same new backend

Only within this scope is `runtime.stage_history` guaranteed to be the complete full process, rather than retaining only the last stage.

## 13. Recommended Read Order for Frontend Use

1. First read `status`
2. Then read `runtime.current_stage`
3. Read the timeline directly from `runtime.stage_history`
4. Read current stage elapsed time from `runtime.active_stage_elapsed_ms`
5. Read total elapsed time from `runtime.total_elapsed_ms`
6. For failed tasks, first read `failure.summary` and `failure.category`
7. Read the execution protocol from `invocation`
8. Read the normalization summary from `normalization_summary`
9. Read the glossary summary from `glossary_summary`

## 14. How to Understand `translation.math_mode`

The current translation pipeline supports two values:

- `placeholder`
  - Default value
  - Uses the legacy formula protection / placeholder / restoration pipeline
- `direct_typst`
  - Experimental mode
  - Does not use formula placeholder protection; directly lets the model output body text and `$...$` math

The frontend only needs to display or pass through as a string; no need to infer on its own.
