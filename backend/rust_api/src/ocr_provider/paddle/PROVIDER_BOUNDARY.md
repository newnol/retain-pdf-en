# Paddle Provider Boundary

This document explains one thing:

The Paddle OCR provider API boundary and the `document.v1` unified document boundary must be kept separate.

Related documents:

- API summary:
  [`API_SUMMARY.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/API_SUMMARY.md)
- Official async API example:
  [`AsyncParse.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/AsyncParse.md)

## 1. Three-Phase Boundary of Paddle Provider API

According to [AsyncParse.md](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/AsyncParse.md), Paddle's async API naturally splits into three phases:

### `submit`

- `POST /api/v2/ocr/jobs`
- Input:
  - `fileUrl` or multipart `file`
  - `model`
  - `optionalPayload`
- Output:
  - `jobId`

### `poll`

- `GET /api/v2/ocr/jobs/{jobId}`
- States:
  - `pending`
  - `running`
  - `done`
  - `failed`
- Available during running:
  - `extractProgress.totalPages`
  - `extractProgress.extractedPages`
- Available after completion:
  - `resultUrl.jsonUrl`

### `download_result`

- Download `jsonUrl`
- Returns `jsonl`
- After line-by-line unpacking, we get the actual:
  - `result.layoutParsingResults`
  - `result.dataInfo`

## 2. What Belongs to the Provider API Layer

The following belongs to the Paddle provider client / OCR service layer:

- `jobId`
- `state`
- `extractProgress`
- `resultUrl.jsonUrl`
- Submission parameters:
  - `model`
  - `optionalPayload`
  - `fileUrl`
  - multipart `file`

This information is used for:

- Submitting tasks
- Polling tasks
- Downloading results
- Debugging failures

It does not belong to `document.v1`.

## 3. What Enters `document.v1`

Only after `download_result`, the actual OCR page content extracted from `jsonl` enters the unified document layer:

- `layoutParsingResults`
- `dataInfo`

Then the adapter does:

1. Provider raw JSON
2. Adapter normalization
3. Generate `document.v1.json`

In other words:

- Paddle provider API layer solves "how to run tasks"
- `document.v1` layer solves "what the document ultimately looks like"

Do not mix these two layers.

## 4. Current Implementation Suggestions

If continuing to integrate Paddle in Rust or Python in the future:

- Provider client is only responsible for:
  - submit
  - poll
  - download
  - Unpacking jsonl
- Adapter is only responsible for:
  - `layoutParsingResults/dataInfo -> document.v1`
- Translation/rendering main chain only accepts:
  - `document.v1.json`

Do not put:

- `jobId`
- `state`
- `resultUrl`
- `extractProgress`

These provider API runtime fields into `document.v1`.
