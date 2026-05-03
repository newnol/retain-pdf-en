# Endpoint Documentation

## 1. Upload PDF

`POST /api/v1/uploads`

Form fields:

- `file`: Required, PDF file

Example:

```bash
curl -X POST http://127.0.0.1:41000/api/v1/uploads \
  -H "X-API-Key: your-rust-api-key" \
  -F "file=@/path/to/paper.pdf"
```

## 2. Create Main Task

`POST /api/v1/jobs`

The current formal JSON contract is a grouped request body; legacy flat fields are no longer accepted.

Most commonly used request body:

```json
{
  "workflow": "book",
  "source": {
    "upload_id": "20260402073151-a80618"
  },
  "ocr": {
    "provider": "mineru",
    "mineru_token": "mineru-xxxx",
    "model_version": "vlm",
    "language": "ch",
    "page_ranges": ""
  },
  "translation": {
    "mode": "sci",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-xxxx",
    "skip_title_translation": false,
    "batch_size": 1,
    "workers": 100,
    "classify_batch_size": 12,
    "rule_profile_name": "general_sci",
    "custom_rules_text": ""
  },
  "render": {
    "render_mode": "auto",
    "compile_workers": 8
  },
  "runtime": {
    "timeout_seconds": 1800
  }
}
```

Additional notes:

- `workflow=book`: OCR -> Normalize -> Translate -> Render
- `workflow=translate`: OCR -> Normalize -> Translate
- `workflow=render`: Re-run rendering based on existing artifacts; in this case `source.artifact_job_id` replaces `source.upload_id`
- `workflow=ocr` uses the dedicated endpoint `POST /api/v1/ocr/jobs`, not this endpoint
- When `ocr.provider=mineru`, `ocr.mineru_token` is required
- The translation stage requires `translation.base_url`, `translation.api_key`, `translation.model`
- `skip_title_translation=false`: Translate the title
- `skip_title_translation=true`: Skip title translation, keep the original title
- Legacy flat fields such as `upload_id`, `mineru_token`, `model`, `render_mode` are no longer the formal JSON contract for `POST /api/v1/jobs`

## 3. Query Task Details

`GET /api/v1/jobs/{job_id}`

Key response fields:

- `status`
- `stage`
- `stage_detail`
- `progress`
- `artifacts`
- `ocr_job`
- `failure_diagnostic`
- `log_tail`

## 4. Query Event Stream

`GET /api/v1/jobs/{job_id}/events`

Used for frontend progress display and debugging.

## 5. Download Artifacts

- `GET /api/v1/jobs/{job_id}/pdf`
- `GET /api/v1/jobs/{job_id}/markdown`
- `GET /api/v1/jobs/{job_id}/markdown?raw=true`
- `GET /api/v1/jobs/{job_id}/download`
- `GET /api/v1/jobs/{job_id}/normalized-document`
- `GET /api/v1/jobs/{job_id}/normalization-report`

## 6. Cancel Task

`POST /api/v1/jobs/{job_id}/cancel`

## 7. OCR Credential Validation

- `POST /api/v1/providers/mineru/validate-token`
- `POST /api/v1/providers/paddle/validate-token`

Example:

```json
{
  "paddle_token": "paddle-access-token",
  "base_url": "https://paddleocr.aistudio-app.com"
}
```

Key response fields:

- `ok`
- `status`
- `summary`
- `retryable`
- `provider_code`
- `provider_message`
- `operator_hint`
- `trace_id`

Additional notes:

- Paddle validation does not submit a real OCR task; instead, it uses a random `jobId` for an authentication-only probe
- When Paddle returns "task not found / 404", the backend considers authentication successful
- 401 / 403 are still treated as invalid token

## 8. Common Statuses

`status`:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

Common `stage` values:

- `queued`
- `ocr_submitting`
- `ocr_upload`
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
