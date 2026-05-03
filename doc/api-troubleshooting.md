# Troubleshooting

## 1. Fields to Check First

When troubleshooting task failures, check the following in order:

1. `stage`
2. `stage_detail`
3. `error`
4. `failure_diagnostic`
5. `log_tail`
6. `/api/v1/jobs/{job_id}/events`

## 2. Current Error Preservation Capabilities

The backend has enhanced error preservation when OCR providers fail:

- `jobs.error` saves the complete error chain
- `log_tail` writes `ERROR:` and `CAUSE[n]:`
- If identifiable, the provider's `trace_id` is preserved

For example, previously you would only see:

```text
MinerU apply upload url failed
```

Now it tries to preserve as much as:

```text
MinerU apply upload url failed
Caused by:
- POST https://mineru.net/api/v4/file-urls/batch failed
- ...
```

## 3. Common Troubleshooting Paths

### 3.1 Check the Endpoint First

```bash
curl http://127.0.0.1:41000/health
curl -H "X-API-Key: your-key" http://127.0.0.1:41000/api/v1/jobs/{job_id}
curl -H "X-API-Key: your-key" http://127.0.0.1:41000/api/v1/jobs/{job_id}/events
```

### 3.2 Then Check the Task Directory

Key directories:

- `data/jobs/{job_id}/logs/`
- `data/jobs/{job_id}/ocr/`
- `data/jobs/{job_id}/translated/`
- `data/jobs/{job_id}/rendered/`

### 3.3 MinerU-type Errors

If the failure occurs at the OCR transport layer:

- Check `provider_trace_id`
- Check `failure_diagnostic`
- Check `CAUSE[n]` in `log_tail`
- If necessary, cross-reference with the MinerU upstream API response
