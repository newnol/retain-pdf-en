# OCR-only API Documentation

This document only describes the OCR-only microservice interface.

Notes:

- This is an OCR-only specific document. For the main entry point, see [README](/home/wxyhgk/tmp/Code/backend/rust_api/README.md), [API_SPEC](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md) and [CURRENT_API_MAP](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- Current provider selection is based on the `provider` / `ocr.provider` field in the request; the actual supported set depends on the health check and `OCR_PROVIDER_CONTRACT.md`

Its objective is clear:

- Only perform OCR parsing
- Only perform raw OCR -> `document.v1.json` / `document.v1.report.json` normalization
- No translation
- No Typst
- No PDF rendering

This set of interfaces is currently mounted within the existing `rust_api` service, but logically forms an independent OCR microservice interface family:

- `/api/v1/ocr/jobs`
- `/api/v1/ocr/jobs/{job_id}`
- `/api/v1/ocr/jobs/{job_id}/artifacts`
- `/api/v1/ocr/jobs/{job_id}/normalized-document`
- `/api/v1/ocr/jobs/{job_id}/normalization-report`
- `/api/v1/ocr/jobs/{job_id}/cancel`

Current examples still use `mineru` as the primary provider, but this is only a provider example and does not mean the OCR-only protocol is bound to MinerU by default.

The position of this OCR-only flow in the overall system is:

1. The OCR API is responsible for consolidating provider raw results into `document.v1`
2. The complete translation chain then continues consumption through the upper-level `normalize -> translate -> render` main flow
3. The OCR API is not a test script, nor a translation/rendering entry point; it is the first half of normalization in the formal production pipeline

The formal consumption contract when passing `document.v1` downstream is:

- `geometry`
- `content`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy`
- `provenance`

Compatibility fields `type/sub_type/bbox/text/lines/segments` may still be present, but should no longer be used by downstream as the primary semantic entry point.

Internal implementation notes:

- `app/router.rs` is responsible for mounting `/api/v1/ocr/jobs*` routes
- `routes/jobs/create.rs` handles the OCR `multipart/form-data` entry point
- `routes/jobs/query.rs` / `routes/jobs/control.rs` / `routes/jobs/download.rs` handle querying, cancellation, and artifact downloads
- `routes/job_requests.rs` handles OCR form parsing
- `routes/jobs/common.rs` / `routes/job_helpers.rs` handle OCR / common job response and download helper logic
- `services/jobs/facade.rs` provides the stable service entry point
- `services/jobs/creation.rs` and `services/jobs/creation/bundle.rs` handle OCR job construction
- `services/job_validation.rs` handles provider parameter validation
- `services/job_snapshot_factory.rs` handles snapshot / command assembly
- `services/job_launcher.rs` handles execution launch

If you are debugging interface behavior, refer to these split module responsibilities rather than the old centralized file structure.

## 1. Basic Information

- Service port: `41000`
- Base prefix: `/api/v1`
- Health check: `GET /health`
- Authentication: Request header `X-API-Key`
- Response format: Returns JSON by default, except for download endpoints

Request header example:

```http
X-API-Key: your-rust-api-key
```

Unified response envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Notes:

- `code=0` means success
- Non-zero means failure
- `message` can be directly displayed to the frontend

## 2. OCR Task Status

Task overall status:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

Common stages:

- `queued`
- `mineru_upload`
- `mineru_processing`
- `normalizing`
- `finished`
- `failed`
- `canceled`

Additional notes:

- `queued`: Enqueued, waiting for execution slot
- `mineru_upload`: File uploaded to MinerU, waiting for processing
- `mineru_processing`: MinerU is parsing
- `normalizing`: Generating `document.v1`
- `finished`: OCR + normalization complete

## 3. Health Check

`GET /health`

Response example:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "up",
    "db": "ok",
    "queue_depth": 0,
    "running_jobs": 0,
    "provider_backends": ["mineru", "paddle"],
    "time": "2026-03-31T03:33:44Z"
  }
}
```

Field descriptions:

- `status`: `up` or `degraded`
- `db`: Whether SQLite is available
- `queue_depth`: Number of currently queued tasks
- `running_jobs`: Number of currently running tasks
- `provider_backends`: Currently connected OCR providers

## 4. Create OCR Task

`POST /api/v1/ocr/jobs`

This is a `multipart/form-data` endpoint.

Implementation notes:

- Form field parsing is in `routes/job_requests.rs`
- Creation entry point is in `routes/jobs/create.rs`
- Facade consolidation is in `services/jobs/facade.rs`
- Pre-creation provider / token / URL / timeout validation is in `services/job_validation.rs`
- OCR job snapshot construction and launch is collaboratively handled by `services/jobs/creation.rs`, `services/job_snapshot_factory.rs`, and `services/job_launcher.rs`

Supports two submission methods, choose one:

- Upload local PDF: `file`
- Submit remote PDF: `source_url`

### Required Fields

- `provider`
  Common current value: `mineru`; other providers depend on the current deployment configuration
- `mineru_token`
  Required when `provider=mineru`
- `timeout_seconds`
  Total timeout in seconds for the OCR task

### Common Optional Fields

- `file`
- `source_url`
- `model_version`
- `is_ocr`
- `disable_formula`
- `disable_table`
- `language`
- `page_ranges`
- `data_id`
- `no_cache`
- `cache_tolerance`
- `extra_formats`
- `poll_interval`
- `poll_timeout`
- `job_id`

### Local File Example

```bash
curl -X POST "http://127.0.0.1:41000/api/v1/ocr/jobs" \
  -H "X-API-Key: your-rust-api-key" \
  -F "provider=mineru" \
  -F "mineru_token=your-mineru-token" \
  -F "timeout_seconds=1800" \
  -F "model_version=vlm" \
  -F "file=@/path/to/paper.pdf"
```

### Remote URL Example

```bash
curl -X POST "http://127.0.0.1:41000/api/v1/ocr/jobs" \
  -H "X-API-Key: your-rust-api-key" \
  -F "provider=mineru" \
  -F "mineru_token=your-mineru-token" \
  -F "timeout_seconds=1800" \
  -F "source_url=https://example.com/paper.pdf"
```

### Response Example

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "20260331033736-c2bcda",
    "status": "queued",
    "workflow": "ocr",
    "links": {
      "self_path": "/api/v1/ocr/jobs/20260331033736-c2bcda",
      "self_url": "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda",
      "artifacts_path": "/api/v1/ocr/jobs/20260331033736-c2bcda/artifacts",
      "artifacts_url": "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda/artifacts",
      "cancel_path": "/api/v1/ocr/jobs/20260331033736-c2bcda/cancel",
      "cancel_url": "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda/cancel"
    }
  }
}
```

### Validation Rules

- `provider` must be a currently supported OCR provider
- When `provider=mineru`, `mineru_token` cannot be empty
- When `mineru_token` is provided, it must not be a URL
- `source_url` if provided must start with `http://` or `https://`
- `timeout_seconds` must be greater than `0`

## 5. OCR Task List

`GET /api/v1/ocr/jobs`

Supported parameters:

- `limit`
- `offset`
- `status`
- `provider`

Example:

```bash
curl -H "X-API-Key: your-rust-api-key" \
  "http://127.0.0.1:41000/api/v1/ocr/jobs?limit=20&offset=0&status=failed&provider=mineru"
```

Response example:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "job_id": "20260331033736-c2bcda",
        "workflow": "ocr",
        "status": "succeeded",
        "trace_id": "ocr-20260331033736-c2bcda",
        "stage": "finished",
        "created_at": "2026-03-31T03:37:36Z",
        "updated_at": "2026-03-31T03:37:41Z",
        "detail_path": "/api/v1/ocr/jobs/20260331033736-c2bcda",
        "detail_url": "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda"
      }
    ]
  }
}
```

## 6. OCR Task Details

`GET /api/v1/ocr/jobs/{job_id}`

Example:

```bash
curl -H "X-API-Key: your-rust-api-key" \
  "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda"
```

Key fields to check in the details:

- `status`
- `stage`
- `stage_detail`
- `trace_id`
- `provider_trace_id`
- `ocr_provider_diagnostics`
- `artifacts`

Notes:

- `trace_id` is the internal trace ID of the OCR microservice
- `provider_trace_id` is the trace ID returned by the provider
- `ocr_provider_diagnostics` is used for troubleshooting
- `ocr_provider_diagnostics.artifacts` only contains provider transport/raw artifact and normalized artifact path summaries, without directly exposing `document.v1` internal fields

Boundary conventions:

- Provider raw state, errors, and raw bundle information are preserved in `ocr_provider_diagnostics`
- `document.v1.json` / `document.v1.report.json` remain the main downstream contract
- Provider private fields are not directly inserted into `document.v1`

## 7. Get Artifact Index

`GET /api/v1/ocr/jobs/{job_id}/artifacts`

This endpoint is one of the most important endpoints of the OCR microservice.

It returns the artifact index that downstream truly cares about.

Response highlights:

- `schema_version`
- `provider_raw_dir`
- `provider_zip`
- `provider_summary_json`
- `normalized_document`
- `normalization_report`

Real example field structure:

```json
{
  "schema_version": "document.v1",
  "provider_raw_dir": "output/20260331033736-c2bcda/ocr/unpacked",
  "provider_zip": "output/20260331033736-c2bcda/ocr/mineru_bundle.zip",
  "provider_summary_json": "output/20260331033736-c2bcda/ocr/mineru_result.json",
  "normalized_document": {
    "ready": true,
    "path": "/api/v1/ocr/jobs/20260331033736-c2bcda/normalized-document"
  },
  "normalization_report": {
    "ready": true,
    "path": "/api/v1/ocr/jobs/20260331033736-c2bcda/normalization-report"
  }
}
```

Field semantics:

- `provider_raw_dir`
  Unpacked provider raw directory
- `provider_zip`
  Provider raw zip
- `provider_summary_json`
  Provider raw return result
- `normalized_document`
  Normalized `document.v1.json`
- `normalization_report`
  Normalization report `document.v1.report.json`

Additional notes:

- `provider_summary_json` / `provider_zip` / `provider_raw_dir` are provider raw artifacts
- `normalized_document` / `normalization_report` are normalized artifacts
- Both layers need to be preserved; the former is for debugging OCR provider issues, the latter is for debugging `document_schema` adaptation issues

## 8. Download Normalized OCR Results

### Download `document.v1.json`

`GET /api/v1/ocr/jobs/{job_id}/normalized-document`

### Download `document.v1.report.json`

`GET /api/v1/ocr/jobs/{job_id}/normalization-report`

Usage:

- `document.v1.json` is directly consumed by the translation main pipeline
- `document.v1.report.json` is for troubleshooting, frontend diagnostics, and schema checks

## 9. Cancel OCR Task

`POST /api/v1/ocr/jobs/{job_id}/cancel`

Example:

```bash
curl -X POST \
  -H "X-API-Key: your-rust-api-key" \
  "http://127.0.0.1:41000/api/v1/ocr/jobs/20260331033736-c2bcda/cancel"
```

Current cancellation rules:

- If the task is still queued, cancel immediately
- If the task is still in the provider stage, stop subsequent polling/execution
- If the task has entered `normalizing`, it will first complete the current normalization, then discard the normalized artifacts, and finally mark as `canceled`

## 10. Current Directory Storage Convention

Using task `20260331033736-c2bcda` as an example:

```text
output/20260331033736-c2bcda/
├── source/
│   └── font_test.pdf
└── ocr/
    ├── mineru_result.json
    ├── mineru_bundle.zip
    ├── unpacked/
    └── normalized/
        ├── document.v1.json
        └── document.v1.report.json
```

Notes:

- `source/`: Original PDF
- `ocr/unpacked/`: Provider unpacked raw content
- `ocr/normalized/`: Normalized results consumed by the main pipeline

## 11. Current Limitations and Boundaries

This set of OCR microservice interfaces can already run through `provider raw -> document.v1`.

However, note:

- Current providers are no longer limited to `mineru`, but different deployments may have different provider sets
- MinerU's submit/poll/download is still executed through the Python worker
- The Rust side is now responsible for:
  - HTTP API
  - Task status
  - Paginated lists
  - trace_id
  - Cancellation/timeout
  - Artifact index
- In the next phase, MinerU's actual HTTP calls will continue to be migrated to the Rust provider client

## 12. Recommended Integration Approach

If you want to connect the main system to this OCR microservice, it is recommended to follow this order:

1. `POST /api/v1/ocr/jobs`
2. `GET /api/v1/ocr/jobs/{job_id}`
3. `GET /api/v1/ocr/jobs/{job_id}/artifacts`
4. Download:
   - `/normalized-document`
   - `/normalization-report`

The main system should not directly read provider raw JSON.

The main system should prioritize consuming:

- `document.v1.json`
- `document.v1.report.json`
- `schema_version`
- `trace_id`
- `provider_trace_id`

This way, when replacing the OCR provider later, the translation and rendering main pipeline does not need to be changed together.
