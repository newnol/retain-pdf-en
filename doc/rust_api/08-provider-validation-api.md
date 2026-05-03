# Provider Validation API

## 1. MinerU Token Validation

Endpoint:

`POST /api/v1/providers/mineru/validate-token`

Purpose:

- Before the user saves or submits OCR configuration, the frontend first checks whether `mineru_token` is usable
- Avoids discovering that the token is invalid or expired only after an OCR task is actually created at runtime

## 2. Request Body

```json
{
  "mineru_token": "mineru-xxxx",
  "base_url": "https://mineru.net",
  "model_version": "vlm"
}
```

Field descriptions:

- `mineru_token`
  - Required, the MinerU token to validate
- `base_url`
  - Optional, defaults to `https://mineru.net`
- `model_version`
  - Optional, defaults to `vlm`

## 3. Response Structure

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "ok": false,
    "status": "expired",
    "summary": "MinerU token has expired",
    "retryable": false,
    "provider_code": "A0211",
    "provider_message": "token expired",
    "operator_hint": "Replace with a new token",
    "trace_id": "trace-1",
    "base_url": "https://mineru.net",
    "checked_at": "2026-04-06T08:30:00Z"
  }
}
```

## 4. Fixed `status` Values

- `valid`
  - Token is usable
- `unauthorized`
  - Token is invalid
- `expired`
  - Token has expired
- `network_error`
  - Connectivity probe from the current machine to MinerU failed
- `provider_error`
  - MinerU returned another error that did not fall into the previous categories

## 5. How the Frontend Should Use It

Recommended flow:

1. User inputs or updates the MinerU token
2. Frontend calls this endpoint
3. Based on `data.status`, provide an immediate prompt
4. Only proceed to submit OCR or translation tasks when `status=valid`

Recommended display:

- Success: `summary`
- Failure: `summary + operator_hint`
- Debug mode: supplement with `provider_code / provider_message / trace_id`

## 6. Implementation Conventions

- This endpoint calls MinerU's lightweight probe request to validate the Authorization
- It does not actually create an OCR task
- It does not upload PDFs
- Its goal is only to detect in advance:
  - Invalid token
  - Expired token
  - Current network cannot reach MinerU

## 7. Relationship with Runtime Failure Diagnostics

This endpoint is a "pre-validation check."

If MinerU authentication issues still occur at runtime, the backend task failure diagnostics will continue to identify them:

- `A0202` -> Invalid token
- `A0211` -> Token expired

So the two layers are complementary:

- Before submission: use this endpoint to catch issues early
- During runtime: rely on failure diagnostics to attribute root causes
