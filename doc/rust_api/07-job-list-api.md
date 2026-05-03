# Job List API

## 1. Main Endpoints

Main task list:

`GET /api/v1/jobs`

OCR sub-task list:

`GET /api/v1/ocr/jobs`

Both endpoints are suitable for:

- Homepage "recent tasks"
- Task history list
- Task panel with simple filtering

## 2. Query Parameters

Currently supported:

- `limit`
- `offset`
- `status`
- `workflow`
- `provider`

Notes:

- `limit`
  - Optional, uses the backend's built-in default value
- `offset`
  - Optional, defaults to `0`
- `status`
  - Optional
  - Current values: `queued` / `running` / `succeeded` / `failed` / `canceled`
- `workflow`
  - Optional
  - Current values: `book` / `ocr`
- `provider`
  - Optional
  - Currently mainly used for filtering by OCR provider diagnostic information, e.g., `mineru`

## 3. Sorting Rules

Current fixed rules:

- Sort by `updated_at DESC`

That is:

- Tasks with the most recent changes appear first
- More suitable for "recent tasks" panels
- Not equivalent to "most recently created"

## 4. Response Structure

Response wrapper:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "job_id": "20260406063244-2176e4",
        "display_name": "paper.pdf",
        "workflow": "book",
        "status": "running",
        "trace_id": "trace-abc",
        "stage": "translating",
        "invocation": {
          "stage": "provider",
          "input_protocol": "stage_spec",
          "stage_spec_schema_version": "provider.stage.v1"
        },
        "created_at": "2026-04-06T06:32:44Z",
        "updated_at": "2026-04-06T06:33:00Z",
        "detail_path": "/api/v1/jobs/20260406063244-2176e4",
        "detail_url": "http://127.0.0.1:41000/api/v1/jobs/20260406063244-2176e4"
      }
    ],
    "invocation_summary": {
      "stage_spec_count": 1,
      "unknown_count": 0
    }
  }
}
```

Each item consistently contains:

- `job_id`
- `display_name`
- `workflow`
- `status`
- `trace_id`
- `stage`
- `created_at`
- `updated_at`
- `detail_path`
- `detail_url`
- `invocation`

The list response also includes an additional aggregation field:

- `data.invocation_summary`

## 5. How to Understand the Fields

- `job_id`
  - Task unique identifier
- `display_name`
  - User-facing task display name
  - Value priority:
    1. Uploaded source PDF filename
    2. Last filename from remote URL
    3. Final fallback to `job_id`
- `workflow`
  - Main task is typically `book`
  - OCR sub-task is typically `ocr`
- `status`
  - Current status or terminal state
- `trace_id`
  - Trace ID attached to artifacts for the current task; may be empty
- `stage`
  - Current coarse-grained stage
  - Suitable for list labels, not a substitute for `stage_detail` in details
- `detail_url`
  - Main entry point for the frontend to continue requesting after clicking into details
- `invocation`
  - List-level execution protocol summary
  - New tasks should show `input_protocol=stage_spec`
  - Suitable for debug labels, not recommended for replacing complete judgments in details
- `invocation_summary`
  - Protocol aggregation statistics for the current page of results
  - Suitable for lightweight frontend hints like "has this page already fully switched to the new protocol"

## 6. Recommended Frontend Reading Methods

Recent tasks list:

`GET /api/v1/jobs?limit=20&offset=0`

Only failed tasks:

`GET /api/v1/jobs?status=failed&limit=20&offset=0`

Only OCR sub-tasks:

`GET /api/v1/ocr/jobs?limit=20&offset=0`

Recommended display:

- Title: `display_name`
- Status: `status`
- Current stage: `stage`
- Protocol label: `invocation.input_protocol`
- Last update time: `updated_at`
- Click to enter: `detail_url`

## 7. What Not to Expect from the List Endpoint

The current list endpoint does not directly return:

- `stage_detail`
- `runtime`
- `runtime.stage_history`
- `failure.summary`
- `artifacts`

So if the frontend wants to display:

- Failure summary
- Total elapsed time
- Download buttons
- Process timeline

It should continue requesting the details endpoint after clicking a list item, rather than expecting the list endpoint to carry all information.

## 8. Relationship Between OCR List and Main List

`GET /api/v1/ocr/jobs` is essentially just:

- Reusing the same list logic
- Additionally fixing `workflow=ocr`

So:

- Response structure is consistent
- Only the data scope differs

## 9. Why It's Designed This Way

The purpose is straightforward:

- The list endpoint stays lightweight
- The details endpoint carries the complete state
- The frontend homepage loads fast first, then fetches full data on the details page

This is more stable and easier to maintain long-term than dumping `runtime`, `failure`, and `artifacts` all into the list at once.
