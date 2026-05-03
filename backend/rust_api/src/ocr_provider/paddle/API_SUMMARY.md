# Paddle OCR API Summary

This document answers one question:

**What is the actual protocol of the Paddle OCR async API we are currently integrating.**

Not about `document.v1`, not about rendering/translation, only about the provider transport layer.

Related resources:

- Paddle official async API example:
  [`AsyncParse.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/AsyncParse.md)
- Rust client:
  [`client.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/client.rs)
- Python client:
  [`backend/scripts/services/ocr_provider/paddle_api.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)
- Provider boundary:
  [`PROVIDER_BOUNDARY.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/PROVIDER_BOUNDARY.md)

## 1. Which API Set We Are Currently Using

The current main connection is to Paddle OCR's async task API:

- `POST /api/v2/ocr/jobs`
- `GET /api/v2/ocr/jobs/{jobId}`
- Download `resultUrl.jsonUrl`

Default base URL:

- `https://paddleocr.aistudio-app.com`

Current code entry points:

- Rust:
  [`client.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/client.rs)
- Python:
  [`paddle_api.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)

## 2. Authentication

Request headers:

```http
Authorization: bearer <token>
Accept: application/json
```

Current code contract:

- Environment variable: `RETAIN_PADDLE_API_TOKEN`
- Local env file: `backend/scripts/.env/paddle.env`

Python read entry:

- [`get_paddle_token(...)`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)

## 3. Three-Phase Protocol

### 3.1 submit

Endpoint:

- `POST /api/v2/ocr/jobs`

Two submission methods:

1. Local file upload
2. Remote URL submission

Our current actual two call types:

- Python:
  - `submit_local_file(...)`
  - `submit_remote_url(...)`
- Rust:
  - `submit_local_file(...)`
  - `submit_remote_url(...)`

Key input parameters:

- `model`
- `optionalPayload`
- For local files, use multipart `file`
- For remote files, use JSON `fileUrl`

The most important return field on success:

- `data.jobId`

## 3.2 poll

Endpoint:

- `GET /api/v2/ocr/jobs/{jobId}`

Return fields we currently care about:

- `data.state`
- `data.extractProgress.totalPages`
- `data.extractProgress.extractedPages`
- `data.resultUrl.jsonUrl`
- `data.errorMsg`

Current unified state mapping in the system:

- `pending` -> queued
- `running` -> processing
- `done` -> succeeded
- `failed` -> failed

Corresponding implementation:

- [`status.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/status.rs)

## 3.3 download result

After completion, instead of getting structured JSON directly, we download:

- `resultUrl.jsonUrl`

This URL returns `jsonl`, not a single JSON.

The current unpacking logic aggregates from each line:

- `result.layoutParsingResults`
- `result.dataInfo`

Into a provider raw payload that the subsequent adapter can consume.

Corresponding implementation:

- Rust:
  [`client.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/client.rs)
- Python:
  [`paddle_api.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)

## 4. Key Parameters We Currently Pass

### `model`

Current default model name:

- `PaddleOCR-VL-1.5`

Compatibility normalization:

- `paddleocr-vl`
- `paddle-ocr-vl`
- `paddleocr-vl-1.5`
- `paddle-ocr-vl-1.5`

### `optionalPayload`

Current code constructs different payloads by model name:

- `PaddleOCR-VL(-1.5)` uses a set of default rich-content parameters
- `PP-StructureV3` uses another set of structured parameters

Corresponding implementation:

- [`build_optional_payload(...)`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)

## 5. Error Contract

The current transport layer mainly handles these types of errors:

- HTTP status errors
- Provider returned `errorCode != 0`
- Incomplete return structure
- Missing `jobId`
- Missing `resultUrl.jsonUrl`
- Polling timeout
- JSONL unpacking failure

Rust unified error mapping:

- [`errors.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/errors.rs)

## 6. Boundary with `document.v1`

The following fields still belong only to the provider transport layer:

- `jobId`
- `state`
- `extractProgress`
- `resultUrl.jsonUrl`
- `errorCode`
- `errorMsg`

Only after downloading and unpacking the `jsonl` do we get the actual:

- `layoutParsingResults`
- `dataInfo`

Which then enter the adapter to eventually become:

- `document.v1.json`

Do not mix provider task state fields directly into the unified document layer.

## 7. Our Currently Verified Pipeline

The current local real pipeline has been verified:

- `workflow = book`
- `ocr.provider = paddle`
- `translation.base_url = https://api.deepseek.com/v1`
- `translation.model = deepseek-v4-flash`

Can successfully run:

- Upload
- Paddle OCR submit
- Poll
- Result download
- Normalize
- Translate
- Render

This proves that the Paddle API integration in the current repository is not just a paper protocol, but is connected to the main pipeline.
