# Rust API Spec

`rust_api` is the new external service layer for the PDF translation pipeline.

Doc index:
[`README.md`](/home/wxyhgk/tmp/Code/backend/rust_api/README.md)

If you only need the current active runtime path, read
[`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md) first.

If you need the current team-facing module boundaries and refactor rules, read
[`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md).

Its backend is now split into two layers:

- Rust side:
  - public HTTP API
  - auth / queue / SQLite job state
  - internal persistence split into `jobs`, `artifacts`, and `events`
  - OCR provider transport: submit / upload / poll / bundle download
- Python side:
  - OCR normalization to `document.v1.json`
  - translation
  - Typst rendering
  - PDF merge/post-processing

Current Python entrypoints used by the Rust layer:

- `scripts/entrypoints/run_provider_case.py`
- `scripts/entrypoints/run_document_flow.py`
- `scripts/entrypoints/run_provider_ocr.py`
- `scripts/entrypoints/run_normalize_ocr.py`
- `scripts/entrypoints/run_translate_only.py`
- `scripts/entrypoints/run_render_only.py`

Current top-level workflow contract:

1. `normalize.stage.v1`
   raw OCR payload -> `ocr/normalized/document.v1.json`
2. `translate.stage.v1`
   `document.v1.json` -> `translated/`
3. `render.stage.v1`
   translated payloads + source PDF -> `rendered/*.pdf`

The Rust layer treats the stage workers as the formal production path.
For local manual use, use the neutral wrapper names above.
Regression scripts under `scripts/devtools/` are not part of the runtime contract.

Current `document.v1` consumption contract for downstream workers:

- `geometry`
- `content`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy`
- `provenance`

Compatibility fields such as `type/sub_type/bbox/text/lines/segments` may still be present,
but they are no longer the primary runtime contract between normalization and translation/rendering.

Current worker contract:

- Rust now launches these worker entrypoints through `--spec <job_root>/specs/*.spec.json`
- the worker layer no longer relies on legacy long CLI flag assembly
- both Rust-owned workers and the maintained local job entrypoints are now treated as spec-driven execution paths

Goals:

- JSON-first API for frontend and third-party integration
- Stable resource URLs instead of leaking local filesystem paths
- Clear separation:
  - Rust API: upload, job orchestration, status, download, auth/rate-limit extension point
  - Python worker: OCR transport implementation, translation, Typst, PDF rendering, post-processing

Current internal boundary conventions:

- `routes/*` only adapts HTTP requests/responses
- `services/jobs/*` owns job query, presentation, creation orchestration, and control logic
- `services/job_factory` owns job snapshot assembly vs execution start as two separate steps
- `job_runner/*` owns runtime execution, process lifecycle, OCR-child chaining, and cancellation
- `AppState` should stay at route entrypoints and runtime coordination layers; pure assembly helpers should prefer `&Db`, `&AppConfig`, and explicit arguments

Current scope:

- Upload PDF
- Create `book` / `translate` / `render` jobs under `/api/v1/jobs`
- Create `ocr` jobs under `/api/v1/ocr/jobs`
- Internally create OCR child job first for `book` and `translate`
- Poll job status
- Fetch structured job events
- List jobs
- Fetch final PDF
- Fetch Markdown
- Fetch Markdown images
- Download combined bundle
- Fetch artifact manifest
- Fetch normalized OCR artifacts

Planned but not fully implemented in this first pass:

- callback/webhook
- RBAC / tenant quota
- public/private artifact signing
- SSE push updates
- stronger cancel semantics

## Reading Guide

- Want to know how requests actually run through Rust + Python:
  [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- Want to know team-facing refactor boundaries:
  [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
- Want to know worker/stage spec contracts:
  [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)

## Base

- Base path: `/api/v1`
- Health path: `/health`
- Except for raw file download endpoints, all responses are JSON
- Except `GET /health`, all endpoints require `X-API-Key`

## Auth

Request header:

```http
X-API-Key: your-rust-api-key
```

Config:

- `auth.local.json`: local auth config file, preferred
- `RUST_API_KEYS`: comma-separated API key allowlist, required
- `RUST_API_MAX_RUNNING_JOBS`: max concurrently running jobs, default `4`

Notes:

- `X-API-Key` is for accessing the Rust API itself
- request body `api_key` is still the downstream model provider credential
- browsers may issue `OPTIONS` preflight for CORS; these are allowed through middleware
- if `auth.local.json` exists, it overrides key and concurrency settings from env

## Config Precedence

Current precedence contract is:

1. code defaults
2. local config files
3. environment variables
4. CLI / process startup parameters
5. request whitelist business parameters

Notes:

- request payloads may override business parameters only
- path, bind, data-root, and runtime storage locations are not request-overridable
- `DATA_ROOT` is the single storage root for uploads, jobs, downloads, and SQLite
- runtime persistence is split as:
  - `jobs`: job metadata / status machine
  - `artifacts`: artifact index JSON
  - `events`: structured event stream

## Unified JSON Envelope

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Rules:

- `code = 0` means success
- non-zero means business or server error
- `message` is short, frontend-display-safe text
- `data` is omitted only when no payload is needed

## Status Model

Job status values:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

Typical stage values:

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

Provider-specific state is no longer part of the formal top-level stage enum.
Provider-private progress may still appear through `provider` + `provider_stage`,
for example `mineru_upload`, `mineru_processing`, or `paddle_running`.

Queue semantics:

- newly created jobs enter `queued`
- only `RUST_API_MAX_RUNNING_JOBS` jobs may be `running` at the same time
- queued jobs automatically start when a slot is released

## Job Events

Read-only structured event APIs:

- `GET /api/v1/jobs/{job_id}/events`
- `GET /api/v1/ocr/jobs/{job_id}/events`

Query parameters:

- `limit`
- `offset`

Behavior:

- events are returned in ascending `seq` order
- runtime merges DB events and `DATA_ROOT/jobs/<job_id>/logs/pipeline_events.jsonl`
- each event includes legacy compatibility fields:
  - `job_id`, `seq`, `ts`, `level`, `stage`, `event`, `message`, `payload`
- each event also includes formal fields when available:
  - `stage_detail`
  - `provider`
  - `provider_stage`
  - `event_type`
  - `progress_current`
  - `progress_total`
  - `retry_count`
  - `elapsed_ms`
- `event` remains a compatibility alias for legacy clients; new clients should prefer `event_type`
- `stage` uses the unified pipeline stage enum, while provider-private state stays in `provider_stage`

## 1. Upload PDF

`POST /api/v1/uploads`

Multipart fields:

- `file`: required, PDF file
- `developer_mode`: optional, `true/false`

Upload limit policy:

- `RUST_API_UPLOAD_MAX_BYTES`
- `RUST_API_UPLOAD_MAX_PAGES`
- either value set to `0` means that limit is disabled

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "upload_id": "20260327190000-ab12cd",
    "filename": "paper.pdf",
    "bytes": 1234567,
    "page_count": 18,
    "uploaded_at": "2026-03-27T11:00:00Z"
  }
}
```

## 2. Create Job

`POST /api/v1/jobs`

Note:

- `workflow = "book"` is the current API workflow identifier for the full document flow
- this is a protocol enum; OCR provider selection remains under `ocr.provider`
- local manual entrypoints may use the neutral `run_provider_case.py` name while the API enum remains unchanged

Canonical JSON request:

```json
{
  "workflow": "book",
  "source": {
    "upload_id": "20260327190000-ab12cd",
    "source_url": "",
    "artifact_job_id": ""
  },
  "ocr": {
    "provider": "mineru",
    "mineru_token": "mineru-xxxx",
    "model_version": "vlm",
    "is_ocr": false,
    "disable_formula": false,
    "disable_table": false,
    "language": "ch",
    "page_ranges": "",
    "data_id": "",
    "no_cache": false,
    "cache_tolerance": 900,
    "extra_formats": "",
    "poll_interval": 5,
    "poll_timeout": 1800
  },
  "translation": {
    "mode": "sci",
    "math_mode": "direct_typst",
    "skip_title_translation": false,
    "classify_batch_size": 12,
    "rule_profile_name": "general_sci",
    "custom_rules_text": "",
    "glossary_id": "",
    "glossary_entries": [],
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-xxxx",
    "start_page": 0,
    "end_page": -1,
    "batch_size": 1,
    "workers": 0
  },
  "render": {
    "render_mode": "auto",
    "compile_workers": 0,
    "typst_font_family": "Source Han Serif SC",
    "pdf_compress_dpi": 200,
    "translated_pdf_name": "",
    "body_font_size_factor": 0.95,
    "body_leading_factor": 1.08,
    "inner_bbox_shrink_x": 0.035,
    "inner_bbox_shrink_y": 0.04,
    "inner_bbox_dense_shrink_x": 0.025,
    "inner_bbox_dense_shrink_y": 0.03
  },
  "runtime": {
    "job_id": "",
    "timeout_seconds": 1800
  }
}
```

Security note:

- request bodies may include provider/model credentials
- responses never echo raw credential values back
- job detail / diagnostics / events only expose redacted payloads
- credential presence is surfaced through `*_configured` booleans instead of plaintext secrets

Workflow contract:

- `workflow=book`: current provider-backed OCR -> Normalize -> Translate -> Render chain
- `workflow=translate`: OCR -> Normalize -> Translate; no render step
- `workflow=render`: reuse `source.artifact_job_id`; rerun render only

Endpoint boundary:

- `/api/v1/jobs` is for `book`, `translate`, and `render`
- `/api/v1/ocr/jobs` is for OCR-only jobs
- `/api/v1/translate/bundle` is the synchronous multipart helper for the same full flow; flat multipart fields remain supported here, including `provider=paddle|mineru`

Required provider fields:

- `ocr.mineru_token` when `ocr.provider=mineru`
- `ocr.paddle_token` when `ocr.provider=paddle`
- `translation.base_url`, `translation.api_key`, and `translation.model` when translation is required

Translation options:

- `translation.math_mode` is optional
- `direct_typst` is the default
- `direct_typst` is an experimental mode that asks the model to output translated prose with inline `$...$` math directly

Validation:

- `ocr.mineru_token` must not be a URL-like string
- `translation.base_url` must start with `http://` or `https://`
- `translation.api_key` must not be a URL-like string
- provider-specific upstream limits apply only to the selected OCR provider, not to the shared `workflow=book` protocol itself
- Rust API no longer supplies default OCR provider / LLM credentials for `create_job`
- legacy flat JSON fields such as `upload_id`, `model`, and `api_key` are rejected by `/api/v1/jobs`; flat field mapping only remains in selected multipart helper endpoints

Response redaction rules:

- `request_payload.ocr.mineru_token`, `request_payload.ocr.paddle_token`, and `request_payload.translation.api_key` are always returned as empty strings
- `request_payload.ocr.mineru_token_configured`, `request_payload.ocr.paddle_token_configured`, and `request_payload.translation.api_key_configured` indicate whether the backend received those credentials
- `error`, `log_tail`, `events[*].message`, `events[*].payload`, translation diagnostics payloads, translation debug item payloads, and replay payloads are redacted before leaving Rust API

Glossary v1 contract:

- `translation.glossary_id`: optional named glossary resource ID
- `translation.glossary_entries`: optional inline glossary array; each item is `{source, target, note}`
- if both are provided, the backend loads the named glossary first and then overlays inline entries by normalized `source`
- inline entries override resource entries with the same `source`
- glossary usage is prompt/guidance only in v1; the pipeline does not force a post-translation find/replace pass
- frontend should parse Excel itself and send JSON entries, or send CSV text to the helper parse endpoint below; backend does not add Excel parsing
- translation outputs now include glossary usage summary in `translation-manifest.json`, diagnostics, and pipeline summary when glossary is enabled

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260327190500-ef3456",
    "status": "queued",
    "workflow": "book",
    "links": {
      "self_path": "/api/v1/jobs/20260327190500-ef3456",
      "self_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456",
      "artifacts_path": "/api/v1/jobs/20260327190500-ef3456/artifacts",
      "artifacts_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts",
      "artifacts_manifest_path": "/api/v1/jobs/20260327190500-ef3456/artifacts-manifest",
      "artifacts_manifest_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts-manifest",
      "events_path": "/api/v1/jobs/20260327190500-ef3456/events",
      "events_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/events",
      "cancel_path": "/api/v1/jobs/20260327190500-ef3456/cancel",
      "cancel_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"
    },
    "actions": {
      "open_job": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"},
      "open_artifacts": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/artifacts", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts"},
      "cancel": {"enabled": true, "method": "POST", "path": "/api/v1/jobs/20260327190500-ef3456/cancel", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"},
      "download_pdf": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/pdf", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf"},
      "open_markdown": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown"},
      "open_markdown_raw": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true"},
      "download_bundle": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/download", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download"}
    }
  }
}
```

Execution model for `/api/v1/jobs`:

1. create parent translation job
2. create OCR child job `{job_id}-ocr`
3. OCR child completes provider transport + normalization
4. parent job reuses:
   - `normalized_document_json`
   - `normalization_report_json`
   - `layout_json`
   - `provider_raw_dir`
   - `provider_zip`
   - `provider_summary_json`
5. parent job enters translation/render

## 2.1 Glossary Resources

Named glossary endpoints:

- `POST /api/v1/glossaries`
- `GET /api/v1/glossaries`
- `GET /api/v1/glossaries/{glossary_id}`
- `PUT /api/v1/glossaries/{glossary_id}`
- `DELETE /api/v1/glossaries/{glossary_id}`
- `POST /api/v1/glossaries/parse-csv`

Create / update request body:

```json
{
  "name": "semiconductor",
  "entries": [
    {"source": "band gap", "target": "band gap", "note": "materials"},
    {"source": "density of states", "target": "density of states", "note": ""}
  ]
}
```

List item / detail fields:

- `glossary_id`
- `name`
- `entry_count`
- `entries`
- `created_at`
- `updated_at`

CSV parse helper request:

```json
{
  "csv_text": "source,target,note\nband gap,band gap,materials\n"
}
```

CSV parse helper response returns normalized `entries` and `entry_count`. It accepts plain CSV text only; Excel files should be converted by the frontend first.

## 3. Get Job Detail

`GET /api/v1/jobs/{job_id}`

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260327190500-ef3456",
    "workflow": "book",
    "status": "running",
    "stage": "translating",
    "stage_detail": "Translating, batch 3/12",
    "progress": {
      "current": 3,
      "total": 12,
      "percent": 25.0
    },
    "timestamps": {
      "created_at": "2026-03-27T11:05:00Z",
      "updated_at": "2026-03-27T11:05:30Z",
      "started_at": "2026-03-27T11:05:01Z",
      "finished_at": null,
      "duration_seconds": null
    },
    "links": {
      "self_path": "/api/v1/jobs/20260327190500-ef3456",
      "self_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456",
      "artifacts_path": "/api/v1/jobs/20260327190500-ef3456/artifacts",
      "artifacts_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts",
      "cancel_path": "/api/v1/jobs/20260327190500-ef3456/cancel",
      "cancel_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"
    },
    "actions": {
      "open_job": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"},
      "open_artifacts": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/artifacts", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts"},
      "cancel": {"enabled": true, "method": "POST", "path": "/api/v1/jobs/20260327190500-ef3456/cancel", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"},
      "download_pdf": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/pdf", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf"},
      "open_markdown": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown"},
      "open_markdown_raw": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true"},
      "download_bundle": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/download", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download"}
    },
    "artifacts": {
      "pdf_ready": false,
      "markdown_ready": false,
      "bundle_ready": false,
      "pdf_url": "/api/v1/jobs/20260327190500-ef3456/pdf",
      "markdown_url": "/api/v1/jobs/20260327190500-ef3456/markdown",
      "markdown_images_base_url": "/api/v1/jobs/20260327190500-ef3456/markdown/images/",
      "bundle_url": "/api/v1/jobs/20260327190500-ef3456/download",
      "normalized_document_url": "/api/v1/jobs/20260327190500-ef3456/normalized-document",
      "normalization_report_url": "/api/v1/jobs/20260327190500-ef3456/normalization-report",
      "actions": {
        "open_job": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"},
        "open_artifacts": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/artifacts", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts"},
        "cancel": {"enabled": true, "method": "POST", "path": "/api/v1/jobs/20260327190500-ef3456/cancel", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"},
        "download_pdf": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/pdf", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf"},
        "open_markdown": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown"},
        "open_markdown_raw": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true"},
        "download_bundle": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/download", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download"}
      },
      "normalized_document": {
        "ready": true,
        "path": "/api/v1/jobs/20260327190500-ef3456/normalized-document",
        "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/normalized-document",
        "method": "GET",
        "content_type": "application/json",
        "file_name": "document.v1.json",
        "size_bytes": 182341
      },
      "normalization_report": {
        "ready": true,
        "path": "/api/v1/jobs/20260327190500-ef3456/normalization-report",
        "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/normalization-report",
        "method": "GET",
        "content_type": "application/json",
        "file_name": "document.v1.report.json",
        "size_bytes": 1248
      },
      "pdf": {
        "ready": false,
        "path": "/api/v1/jobs/20260327190500-ef3456/pdf",
        "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf",
        "method": "GET",
        "content_type": "application/pdf",
        "file_name": "paper-translated.pdf",
        "size_bytes": null
      },
      "markdown": {
        "ready": false,
        "json_path": "/api/v1/jobs/20260327190500-ef3456/markdown",
        "json_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown",
        "raw_path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
        "raw_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
        "images_base_path": "/api/v1/jobs/20260327190500-ef3456/markdown/images/",
        "images_base_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown/images/",
        "file_name": "full.md",
        "size_bytes": null
      },
      "bundle": {
        "ready": false,
        "path": "/api/v1/jobs/20260327190500-ef3456/download",
        "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download",
        "method": "GET",
        "content_type": "application/zip",
        "file_name": "20260327190500-ef3456.zip",
        "size_bytes": null
      }
    },
    "normalization_summary": {
      "provider": "mineru",
      "detected_provider": "mineru",
      "provider_was_explicit": true,
      "pages_seen": 12,
      "blocks_seen": 428,
      "document_defaults": 0,
      "page_defaults": 0,
      "block_defaults": 0,
      "schema": "normalized_document_v1",
      "schema_version": "1.1",
      "page_count": 12,
      "block_count": 428
    },
    "glossary_summary": {
      "enabled": true,
      "glossary_id": "glossary-20260411-abc123",
      "glossary_name": "semiconductor",
      "entry_count": 12,
      "resource_entry_count": 10,
      "inline_entry_count": 3,
      "overridden_entry_count": 1,
      "source_hit_entry_count": 7,
      "target_hit_entry_count": 6,
      "unused_entry_count": 5,
      "unapplied_source_hit_entry_count": 1
    },
    "invocation": {
      "stage": "provider",
      "input_protocol": "stage_spec",
      "stage_spec_schema_version": "provider.stage.v1"
    },
    "log_tail": [
      "batch 123: state=done",
      "layout json: output/..."
    ]
  }
}
```

Failure contract:

- `data.failure` is the formal failure object when a job has entered structured failure classification
- formal failure fields include:
  - `failed_stage`
  - `failure_code`
  - `failure_category`
  - `provider`
  - `provider_stage`
  - `provider_code`
  - `summary`
  - `root_cause`
  - `retryable`
  - `upstream_host`
  - `suggestion`
  - `last_log_line`
  - `raw_excerpt`
- `data.failure_diagnostic` is kept as a compatibility projection for older clients and is derived from `data.failure` when formal fields are present

Main job detail now also includes OCR-child-facing fields in `artifacts` / detail payload:

- `ocr_job`
- `normalized_document`
- `normalization_report`
- `provider_raw_dir`
- `provider_zip`
- `provider_summary_json`
- `schema_version`

`normalization_summary` is a lightweight view derived from `document.v1.report.json`.
If a client needs the full adapter / defaults / validation report, it should download `artifacts.normalization_report`.

`glossary_summary` is loaded from `translation-manifest.json` when present, and falls back to the pipeline summary artifact.

`invocation` is loaded from `translation-manifest.json` when present, and falls back to the pipeline summary artifact.
Current workers are spec-driven, so new tasks should report:

- `input_protocol=stage_spec`
- `stage_spec_schema_version`: the concrete stage schema version
This means render-only jobs can still expose the original translation glossary summary as long as the translation artifacts are preserved.

## 4. List Jobs

`GET /api/v1/jobs?limit=20`

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "job_id": "20260327190500-ef3456",
        "workflow": "book",
        "status": "running",
        "stage": "translating",
        "invocation": {
          "stage": "provider",
          "input_protocol": "stage_spec",
          "stage_spec_schema_version": "provider.stage.v1"
        },
        "created_at": "2026-03-27T11:05:00Z",
        "updated_at": "2026-03-27T11:05:30Z",
        "detail_path": "/api/v1/jobs/20260327190500-ef3456",
        "detail_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"
      }
    ],
    "invocation_summary": {
      "stage_spec_count": 12,
      "unknown_count": 0
    }
  }
}
```

## 5. Artifact JSON

`GET /api/v1/jobs/{job_id}/artifacts`

Purpose:

- frontend consumes structured URLs only
- no local absolute path leakage

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "pdf_ready": true,
    "markdown_ready": true,
    "bundle_ready": true,
    "pdf_url": "/api/v1/jobs/20260327190500-ef3456/pdf",
    "markdown_url": "/api/v1/jobs/20260327190500-ef3456/markdown",
    "markdown_images_base_url": "/api/v1/jobs/20260327190500-ef3456/markdown/images/",
    "bundle_url": "/api/v1/jobs/20260327190500-ef3456/download",
    "actions": {
      "open_job": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"},
      "open_artifacts": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/artifacts", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts"},
      "cancel": {"enabled": false, "method": "POST", "path": "/api/v1/jobs/20260327190500-ef3456/cancel", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"},
      "download_pdf": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/pdf", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf"},
      "open_markdown": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown"},
      "open_markdown_raw": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true"},
      "download_bundle": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/download", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download"}
    },
    "pdf": {
      "ready": true,
      "path": "/api/v1/jobs/20260327190500-ef3456/pdf",
      "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf",
      "method": "GET",
      "content_type": "application/pdf",
      "file_name": "paper-translated.pdf",
      "size_bytes": 1048576
    },
    "markdown": {
      "ready": true,
      "json_path": "/api/v1/jobs/20260327190500-ef3456/markdown",
      "json_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown",
      "raw_path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
      "raw_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
      "images_base_path": "/api/v1/jobs/20260327190500-ef3456/markdown/images/",
      "images_base_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown/images/",
      "file_name": "full.md",
      "size_bytes": 18234
    },
    "bundle": {
      "ready": true,
      "path": "/api/v1/jobs/20260327190500-ef3456/download",
      "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download",
      "method": "GET",
      "content_type": "application/zip",
      "file_name": "20260327190500-ef3456.zip",
      "size_bytes": null
    }
  }
}
```

## 6. Final PDF

`GET /api/v1/jobs/{job_id}/pdf`

Response:

- raw `application/pdf`

## 7. Translation Diagnostics

These endpoints are for fast item-level debugging. They expose the translation diagnostics artifact, the per-item debug index, the saved item payload, and a replay hook that reruns the current translation code on a single item without mutating job artifacts.

Security:

- responses are redacted before returning to clients
- structured secret fields such as `api_key`, `mineru_token`, and `paddle_token` are blanked
- inline secret substrings are replaced with `[REDACTED]`

All four endpoints are job-local and currently read from:

- `DATA_ROOT/jobs/<job_id>/artifacts/translation_diagnostics.json`
- `DATA_ROOT/jobs/<job_id>/artifacts/translation_debug_index.json`
- `DATA_ROOT/jobs/<job_id>/translated/translation-manifest.json`

### 7.1 Translation Diagnostics Summary

`GET /api/v1/jobs/{job_id}/translation/diagnostics`

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260416034152-d12925",
    "summary": {
      "schema": "translation_diagnostics_v1",
      "counts": {
        "translated": 412,
        "kept_origin": 18,
        "skipped": 97
      },
      "provider_family": "deepseek",
      "final_status_counts": {
        "translated": 412,
        "kept_origin": 18,
        "skipped": 97
      }
    }
  }
}
```

### 7.2 Translation Item Index

`GET /api/v1/jobs/{job_id}/translation/items`

Query parameters:

- `limit`
- `offset`
- `page`
- `final_status`
- `error_type`
- `route`
- `q`

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "item_id": "p006-b014",
        "page_idx": 5,
        "page_number": 6,
        "block_idx": 14,
        "block_type": "text",
        "math_mode": "direct_typst",
        "continuation_group": "",
        "classification_label": "body",
        "should_translate": true,
        "skip_reason": "",
        "final_status": "kept_origin",
        "source_preview": "Formation of heterocycle 9 improves hyperconjugation...",
        "translated_preview": "",
        "route_path": ["direct_typst", "single_item"],
        "fallback_to": "sentence_level",
        "degradation_reason": "transport_error",
        "error_types": ["TranslationProtocolError"]
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

### 7.3 Raw Translation Item

`GET /api/v1/jobs/{job_id}/translation/items/{item_id}`

Response:

- same payload shape as the saved translated item
- sensitive fields and inline secrets are redacted

### 7.4 Replay Translation Item

`POST /api/v1/jobs/{job_id}/translation/items/{item_id}/replay`

Response:

- replay output is returned as JSON payload
- replay payload is redacted with the same rules as diagnostics/item endpoints

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260416034152-d12925",
    "item_id": "p006-b014",
    "page_idx": 5,
    "page_number": 6,
    "page_path": "page-006.json",
    "item": {
      "item_id": "p006-b014",
      "source_text": "Formation of heterocycle 9 improves hyperconjugation...",
      "translated_text": "",
      "classification_label": "body",
      "should_translate": true,
      "final_status": "kept_origin",
      "translation_diagnostics": {
        "route_path": ["direct_typst", "single_item"],
        "fallback_to": "sentence_level",
        "degradation_reason": "transport_error"
      }
    }
  }
}
```

### 7.4 Replay One Item

`POST /api/v1/jobs/{job_id}/translation/items/{item_id}/replay`

Behavior:

- launches `backend/scripts/devtools/replay_translation_item.py`
- re-applies current policy to the saved item payload
- if the item still qualifies for translation, reruns `translate_batch([item])`
- never writes back to the original job directory

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260416034152-d12925",
    "item_id": "p006-b014",
    "payload": {
      "job_id": "20260416034152-d12925",
      "item_id": "p006-b014",
      "page_idx": 5,
      "policy_before": {
        "should_translate": true,
        "final_status": "kept_origin"
      },
      "policy_after": {
        "should_translate": true,
        "final_status": "translated"
      },
      "replay_result": {
        "translated_text": "The formation of heterocycle 9 enhances hyperconjugation..."
      },
      "replay_error": null
    }
  }
}
```

These endpoints are intended for local debugging and automated regression fixtures. They are not yet optimized for bulk export or high-throughput replay.

## 8. Markdown

`GET /api/v1/jobs/{job_id}/markdown`

Default response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260327190500-ef3456",
    "content": "# title",
    "raw_path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
    "raw_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true",
    "images_base_path": "/api/v1/jobs/20260327190500-ef3456/markdown/images/",
    "images_base_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown/images/"
  }
}
```

`GET /api/v1/jobs/{job_id}/markdown?raw=1`

Response:

- raw `text/markdown; charset=utf-8`

## 9. Markdown Images

`GET /api/v1/jobs/{job_id}/markdown/images/{path}`

Response:

- raw image file stream

## 10. Download Bundle

`GET /api/v1/jobs/{job_id}/download`

Bundle contents:

- final translated PDF
- `markdown/full.md` if present
- `markdown/images/**` if present

Response:

- raw `application/zip`

## 11. Cancel Job

`POST /api/v1/jobs/{job_id}/cancel`

Current intent:

- best-effort kill of the running Python worker process
- mark job as `canceled`

Response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260327190500-ef3456",
    "status": "canceled",
    "workflow": "book",
    "links": {
      "self_path": "/api/v1/jobs/20260327190500-ef3456",
      "self_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456",
      "artifacts_path": "/api/v1/jobs/20260327190500-ef3456/artifacts",
      "artifacts_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts",
      "cancel_path": "/api/v1/jobs/20260327190500-ef3456/cancel",
      "cancel_url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"
    },
    "actions": {
      "open_job": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456"},
      "open_artifacts": {"enabled": true, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/artifacts", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/artifacts"},
      "cancel": {"enabled": false, "method": "POST", "path": "/api/v1/jobs/20260327190500-ef3456/cancel", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/cancel"},
      "download_pdf": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/pdf", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/pdf"},
      "open_markdown": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown"},
      "open_markdown_raw": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/markdown?raw=true", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/markdown?raw=true"},
      "download_bundle": {"enabled": false, "method": "GET", "path": "/api/v1/jobs/20260327190500-ef3456/download", "url": "http://127.0.0.1:41000/api/v1/jobs/20260327190500-ef3456/download"}
    }
  }
}
```

## Error Shape

Example:

```json
{
  "code": 40004,
  "message": "job not found: 20260327190500-ef3456"
}
```

Suggested code ranges:

- `400xx` request errors
- `404xx` not found
- `409xx` state conflict
- `500xx` internal error

## Storage Layout

Rust API layer stores:

- uploads in `DATA_ROOT/uploads/`
- downloads in `DATA_ROOT/downloads/`
- metadata in `DATA_ROOT/db/jobs.db`
- SQLite logical split:
  - `jobs` table for core job state
  - `artifacts` table for artifact index payload
  - `events` table for structured timeline
- job workspaces in `DATA_ROOT/jobs/<job_id>/`

Current standard job workspace layout:

- `DATA_ROOT/jobs/<job_id>/source`
- `DATA_ROOT/jobs/<job_id>/ocr`
- `DATA_ROOT/jobs/<job_id>/translated`
- `DATA_ROOT/jobs/<job_id>/rendered`
- `DATA_ROOT/jobs/<job_id>/artifacts`
- `DATA_ROOT/jobs/<job_id>/logs`

Legacy jobs using `originPDF/jsonPDF/transPDF/typstPDF` or absolute-path artifact storage are no longer supported by detail and download endpoints and must be rerun.

## Implementation Notes

- Rust API should not parse or manipulate PDF internals
- Rust only orchestrates jobs and exposes resources
- Python worker remains the single execution implementation, driven by stage spec files
- later migration to dedicated Python worker service is straightforward because the API contract is already stable
- `workflow = "book"` is the current protocol identifier for the full document flow
- it is kept for API stability and does not imply user-facing entrypoint names must expose the provider
