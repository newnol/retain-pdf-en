# Backend API Documentation

This document describes the actual API contract of the current backend service, aimed at three types of users:

- Frontend integrators
- Local deployment and operations personnel
- Developers who need to troubleshoot task failure causes

Related documents:

- [Frontend Request Examples](/home/wxyhgk/tmp/Code/backend/rust_api/frontend_request_example.md)
- [OCR-only Service Documentation](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_Service_API.md)
- [API Main Entry](/home/wxyhgk/tmp/Code/doc/API.md)

## 1. Service Overview

The current backend is divided into two layers:

- Rust: External HTTP API, authentication, task queuing, task status persistence, OCR provider transport
- Python: OCR normalization, translation, rendering, PDF artifact generation

Main task workflow:

1. Upload PDF
2. Create main task `POST /api/v1/jobs`
3. Main task internally creates OCR sub-task `{job_id}-ocr`
4. After OCR sub-task completes, a normalized `document.v1.json` is produced
5. Main task continues with translation and rendering
6. Download PDF / Markdown / ZIP

Default ports:

- `41000`: Full API
- `42000`: Simple synchronous endpoint

Base paths:

- Health check: `GET /health`
- Business prefix: `/api/v1`

## 2. Authentication and Configuration

Except for `GET /health`, all other endpoints require by default:

```http
X-API-Key: your-rust-api-key
```

Note the distinction between two types of keys:

- `X-API-Key`: For accessing the Rust API itself
- `api_key` in the request body: For accessing downstream model services

Recommended local configuration file:

- `backend/rust_api/auth.local.json`

Example:

```json
{
  "api_keys": ["replace-with-your-backend-key"],
  "max_running_jobs": 4,
  "simple_port": 42000
}
```

Common environment variables:

- `RUST_API_BIND_HOST`: Listen address, default `0.0.0.0`
- `RUST_API_PORT`: Full API port, default `41000`
- `RUST_API_SIMPLE_PORT`: Simple synchronous endpoint port, default `42000`
- `RUST_API_KEYS`: Backend allowed API key list, comma-separated
- `RUST_API_MAX_RUNNING_JOBS`: Maximum concurrent running tasks, default `4`
- `RUST_API_DATA_ROOT`: Data root directory
- `PYTHON_BIN`: Python executable, default `python`

Configuration priority:

1. Code defaults
2. Local configuration file
3. Environment variables
4. Startup arguments
5. Request body allowlist business parameters

The request body cannot override infrastructure configurations such as paths, ports, or data root directory.

## 3. Storage Conventions

The current runtime uses `DATA_ROOT` as the sole data root directory. The default is `data/` under the repository.

Main directories:

- `DATA_ROOT/uploads/`: Uploaded files
- `DATA_ROOT/jobs/{job_id}/`: Task working directory
- `DATA_ROOT/downloads/`: Download cache
- `DATA_ROOT/db/jobs.db`: SQLite

Standard task directory structure:

- `source/`
- `ocr/`
- `translated/`
- `rendered/`
- `artifacts/`
- `logs/`

Database internal tables:

- `jobs`: Task metadata, status, errors, log tails
- `artifacts`: Artifact index
- `events`: Structured event stream

The database and API responses primarily use relative paths, which are resolved to real files at runtime.

## 4. Unified Response Format

Success:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Failure:

```json
{
  "code": 400,
  "message": "specific error message"
}
```

Conventions:

- `code = 0` indicates success
- `message` is suitable for direct display to frontend users
- Business details are in `data`

## 5. Main Workflow Endpoints

### 5.1 Upload PDF

`POST /api/v1/uploads`

`multipart/form-data` fields:

- `file`: Required, PDF file
- `developer_mode`: Optional, `true/false`

Success example:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "upload_id": "20260402073151-a80618",
    "filename": "paper.pdf",
    "bytes": 1832451,
    "page_count": 18,
    "uploaded_at": "2026-04-02T07:31:55+08:00"
  }
}
```

Current upload limits:

- Normal mode: By default only supports files under `10MB` and under `30` pages
- `developer_mode=true`: Skips normal mode limits
- Currently only `provider=mineru` is additionally subject to upstream MinerU's hard limits: less than `200MB` and no more than `600` pages

### 5.2 Create Main Task

`POST /api/v1/jobs`

The current canonical JSON request body uses a grouped structure; legacy flat JSON is no longer accepted:

```json
{
  "workflow": "book",
  "source": {
    "upload_id": "20260402073151-a80618"
  },
  "ocr": {
    "provider": "mineru",
    "mineru_token": "mineru-xxxx",
    "page_ranges": ""
  },
  "translation": {
    "mode": "sci",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-xxxx",
    "skip_title_translation": false,
    "batch_size": 1,
    "workers": 50,
    "rule_profile_name": "general_sci",
    "custom_rules_text": "",
    "glossary_id": "",
    "glossary_entries": []
  },
  "render": {
    "render_mode": "auto",
    "compile_workers": 8
  },
  "runtime": {
    "job_id": "",
    "timeout_seconds": 1800
  }
}
```

Currently supported `workflow` values:

- `book`: Full pipeline, OCR -> Normalize -> Translate -> Render
- `translate`: OCR -> Normalize -> Translate, does not enter rendering
- `render`: Re-run rendering based on existing job artifacts

Endpoint boundaries:

- `POST /api/v1/jobs` is for `book` / `translate` / `render`
- `workflow=ocr` uses the dedicated endpoint `POST /api/v1/ocr/jobs`

`source` conventions for different workflows:

- `book` / `translate`: Typically use `source.upload_id`
- `render`: Uses `source.artifact_job_id`

Current required fields depend on provider and stage, common requirements:

- When `ocr.provider=mineru`, `ocr.mineru_token` is required
- When `ocr.provider=paddle`, `ocr.paddle_token` is required
- When LLM translation is needed, `translation.base_url`, `translation.api_key`, `translation.model` are required
- `render` workflow does not require OCR or translation credentials

Common translation control fields:

- `translation.skip_title_translation=false`: Translate the title
- `translation.skip_title_translation=true`: Skip title translation, keep the original title

Current validation rules:

- `translation.base_url` must start with `http://` or `https://`
- `translation.api_key` must not look like a URL
- When `ocr.provider=mineru`, additional validation of `200MB / 600 pages` limits is performed

Glossary v1 conventions:

- `translation.glossary_id`: Optional, references a named glossary saved in the backend
- `translation.glossary_entries`: Optional, an array of glossary entries submitted directly with the task; element structure is `{source, target, note}`
- If both are provided, the backend first loads the named glossary, then uses inline entries to normalize and override by `source`
- v1 only performs prompt injection and result recording, not forced post-translation replacement
- If the frontend allows users to upload Excel, it should first parse to JSON on the frontend, then pass to the backend; the backend only accepts JSON entries, or receives `csv_text` through the CSV parsing helper endpoint below
- After translation completes, `translation-manifest.json`, diagnostic files, and pipeline summary will include glossary hit summaries

Compatibility notes:

- The JSON entry for `POST /api/v1/jobs` only accepts grouped structures
- Legacy flat fields are only preserved in a few `multipart/form-data` helper endpoint form mappings, and are no longer considered formal JSON contracts

### 5.2.1 Glossary Resource Endpoints

Named glossary endpoints:

- `POST /api/v1/glossaries`
- `GET /api/v1/glossaries`
- `GET /api/v1/glossaries/{glossary_id}`
- `PUT /api/v1/glossaries/{glossary_id}`
- `DELETE /api/v1/glossaries/{glossary_id}`
- `POST /api/v1/glossaries/parse-csv`

Create or update request body:

```json
{
  "name": "semiconductor",
  "entries": [
    {"source": "band gap", "target": "band gap", "note": "materials"},
    {"source": "density of states", "target": "density of states", "note": ""}
  ]
}
```

Response fields:

- `glossary_id`
- `name`
- `entry_count`
- `entries`
- `created_at`
- `updated_at`

CSV parsing helper endpoint request body:

```json
{
  "csv_text": "source,target,note\nband gap,band gap,materials\n"
}
```

This endpoint is only responsible for parsing CSV text into standard JSON entries; it does not directly receive Excel files.

### 5.3 Query Task Details

`GET /api/v1/jobs/{job_id}`

This is the main polling endpoint for the frontend. Key fields:

- `status`
- `stage`
- `stage_detail`
- `progress`
- `timestamps`
- `request_payload`
- `actions`
- `artifacts`
- `glossary_summary`
- `ocr_job`
- `runtime`
- `failure`
- `error`
- `failure_diagnostic`
- `normalization_summary`
- `log_tail`

Notes:

- Frontend should use `status` to determine if a task has ended
- Frontend should use `actions.*.enabled` and `artifacts.*.ready` to determine if download buttons should be enabled
- `failure` is the structured failure information source of truth; `failure_diagnostic` is a simplified view for backward-compatible frontends
- `runtime.stage_history` answers "how did the task stages evolve and how long did each stage take"
- Do not infer task completion from progress percentage

### 5.4 Query Task List

`GET /api/v1/jobs`

Suitable for list pages. Each item returns:

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

### 5.5 Query Event Stream

`GET /api/v1/jobs/{job_id}/events`

Query parameters:

- `limit`
- `offset`

Each event contains:

- `job_id`
- `seq`
- `ts`
- `level`
- `stage`
- `event`
- `message`
- `payload`

Event contract:

- Results are returned in ascending order by `seq`
- `seq` is a monotonically increasing sequence number within the same task
- `stage` indicates the current stage when the event occurred
- `/events` is the append-only event source of truth for troubleshooting
- `runtime.stage_history` is the stage timeline source of truth for the detail page

The event stream is also persisted to:

- `DATA_ROOT/jobs/{job_id}/logs/events.jsonl`

### 5.6 Query Artifacts Manifest

`GET /api/v1/jobs/{job_id}/artifacts-manifest`

This endpoint is the formal artifact discovery entry point. Each entry contains at least:

- `artifact_key`
- `artifact_group`
- `artifact_kind`
- `ready`
- `content_type`
- `relative_path`
- `source_stage`
- `resource_path`
- `resource_url`

Frontend or scripts should prefer:

1. Query `artifacts-manifest`
2. Find the target `artifact_key`
3. Check `ready`
4. Then use `resource_path` / `resource_url`

Where:

- The `artifacts` detail block is suitable for direct button state determination on the page
- `artifacts-manifest` is suitable for complete machine-based discovery and download mapping

### 5.7 Download Artifacts

Main task download endpoints:

- `GET /api/v1/jobs/{job_id}/pdf`
- `GET /api/v1/jobs/{job_id}/markdown`
- `GET /api/v1/jobs/{job_id}/markdown?raw=true`
- `GET /api/v1/jobs/{job_id}/markdown/images/*path`
- `GET /api/v1/jobs/{job_id}/download`
- `GET /api/v1/jobs/{job_id}/normalized-document`
- `GET /api/v1/jobs/{job_id}/normalization-report`

Frontend should primarily read return values from task details:

- `actions.download_pdf`
- `actions.open_markdown`
- `actions.open_markdown_raw`
- `actions.download_bundle`
- `artifacts.pdf`
- `artifacts.markdown`
- `artifacts.bundle`

Additional notes:

- `artifacts.pdf` / `artifacts.markdown` / `artifacts.bundle` are the currently recommended nested object fields to read
- Sibling fields like `pdf_url` / `markdown_url` / `bundle_url` are preserved as compatibility aliases; semantically closer to path aliases, not recommended as primary fields for new frontends

If `ready=false` or `enabled=false`, do not manually construct download links to force access.

### 5.8 Cancel Task

`POST /api/v1/jobs/{job_id}/cancel`

Current semantics:

- Queued tasks will be marked as canceled
- Running tasks will enter the cancellation flow
- Completed tasks will not be rolled back

## 6. OCR-only Endpoints

Suitable for OCR-only usage, without translation and rendering:

- `POST /api/v1/ocr/jobs`
- `GET /api/v1/ocr/jobs`
- `GET /api/v1/ocr/jobs/{job_id}`
- `GET /api/v1/ocr/jobs/{job_id}/events`
- `GET /api/v1/ocr/jobs/{job_id}/artifacts`
- `GET /api/v1/ocr/jobs/{job_id}/artifacts-manifest`
- `GET /api/v1/ocr/jobs/{job_id}/normalized-document`
- `GET /api/v1/ocr/jobs/{job_id}/normalization-report`
- `POST /api/v1/ocr/jobs/{job_id}/cancel`

The `ocr_job` field in the main task details provides the OCR sub-task summary:

- `job_id`
- `status`
- `trace_id`
- `provider_trace_id`
- `detail_url`

## 7. Simple Synchronous Endpoint

`POST http://host:42000/api/v1/translate/bundle`

Purpose:

- A single request to directly upload a PDF and wait for results
- Returns the final ZIP or a timeout error

Suitable for:

- Internal tools
- Small scripts
- Callers who don't want to manage the three-stage upload + polling + download flow themselves

Not suitable for:

- Frontend pages that need real-time progress display
- Scenarios that need fine-grained troubleshooting

Additional notes:

- This endpoint accepts `multipart/form-data`
- OCR provider is specified via the form field `provider`, currently supporting `mineru` and `paddle`
- For example, when passing `provider=paddle`, `paddle_token` should also be provided
- If you don't need to synchronously wait for the ZIP, the formal three-stage flow is recommended: `uploads -> jobs -> poll`

## 8. Status and Stages

Current possible `status` values:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

Common main task `stage` values:

- `queued`
- `ocr_submitting`
- `mineru_upload`
- `mineru_processing`
- `translation_prepare`
- `normalizing`
- `domain_inference`
- `continuation_review`
- `page_policies`
- `translating`
- `rendering`
- `saving`
- `finished`
- `failed`
- `canceled`

`stage_detail` is the currently most recommended stage description to display to users, with finer granularity than `stage`.

## 9. Failure Diagnostics

`GET /api/v1/jobs/{job_id}` typically returns the following when a task fails:

- `failure.stage`: Structured failure stage
- `failure.category`: Structured failure category
- `failure.summary`: Structured failure summary
- `failure.retryable`: Whether retry is recommended
- `failure.root_cause`: Identified root cause
- `failure.suggestion`: Suggested action
- `failure_diagnostic.failed_stage`: Backward-compatible failure stage field
- `failure_diagnostic.error_kind`: Backward-compatible failure type field
- `error`: Original error summary
- `log_tail`: Recent log tail

Currently covered error types include:

- Authentication errors: e.g., `missing or invalid X-API-Key`
- Configuration errors: e.g., missing `mineru_token`, `api_key`, `model`
- Network errors: e.g., DNS resolution failure, remote disconnection, request timeout
- OCR provider transport errors: Upload URL request failure, polling failure, bundle download failure
- Python worker errors: Normalization, translation, rendering stage exceptions

Frontend recommendations:

- On failure, first display `failure.summary`
- Then display `failure.suggestion`
- If the frontend hasn't switched to the new fields yet, continue reading `failure_diagnostic.summary`
- Include `log_tail` in developer mode

## 10. Common Troubleshooting Points

### 10.1 Task Failed but Frontend Only Shows "Task Failed"

Check in order:

1. `GET /api/v1/jobs/{job_id}`
2. `failure_diagnostic`
3. `log_tail`
4. `GET /api/v1/jobs/{job_id}/events`

### 10.2 Download Button Not Available

First confirm:

- Whether `status` has ended
- Whether `actions.*.enabled` is `true`
- Whether `artifacts.*.ready` is `true`

Do not guess that a file exists just because the status is `running`.

### 10.3 OCR Provider Related Failures

Common causes:

- Provider credentials are missing, invalid, or expired
- Uploaded PDF exceeds upstream provider limits
- DNS or proxy environment issues
- Temporary remote API disconnection or CDN fetch failure

### 10.4 DNS / Network Issues

Typical errors include:

- `Temporary failure in name resolution`
- `Server disconnected without sending a response`
- `Failed to fetch`

These issues are typically not in the frontend, but in the backend host machine's network, proxy, or DNS configuration.

## 11. Integration Recommendations

The most reliable frontend calling pattern:

1. `POST /api/v1/uploads`
2. `POST /api/v1/jobs`
3. Poll `GET /api/v1/jobs/{job_id}`
4. On success, read `actions` / `artifacts` then download
5. On failure, display `failure_diagnostic` and `log_tail`

If you only need a minimal implementation, refer directly to:

- [frontend_request_example.md](/home/wxyhgk/tmp/Code/backend/rust_api/frontend_request_example.md)
