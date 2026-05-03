# Service Overview

This document describes the overall API structure of the current project.

## 1. Service Ports

- Frontend static pages default to running at `http://127.0.0.1:40001`
- Rust API defaults to running at `http://127.0.0.1:41000`
- Simple synchronous endpoint defaults to running at `http://127.0.0.1:42000`
- Health check: `GET /health`
- Business prefix: `/api/v1`

## 2. Main Workflow

Current main workflow:

1. Upload PDF
2. Create main task `/api/v1/jobs`
3. Main task internally spawns OCR sub-task `{job_id}-ocr`
4. After OCR completes, a normalized `document.v1` is generated
5. Enter translation and rendering
6. Download PDF / Markdown / ZIP

The JSON request body for `POST /api/v1/jobs` uses a grouped structure of `source / ocr / translation / render / runtime` as the formal contract; legacy flat fields are no longer promoted.

## 3. Unified Response Format

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

## 4. Current Main Providers

- The current production mainline uses `mineru` as the primary provider
- `paddle` has been integrated, but is more oriented toward development and debugging purposes
