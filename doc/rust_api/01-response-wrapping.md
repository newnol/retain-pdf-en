# Rust API Response Wrapping

## 1. Top-Level Format

The Rust API currently uses a unified response wrapping scheme.

Success response:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Failure response:

```json
{
  "code": 400,
  "message": "specific error message"
}
```

The reading rules are simple:

- `code = 0` means success
- `message` is human-readable
- Business data is always in `data`

## 2. Most Common Mistakes

Many frontend blank pages, empty lists, and fields "that the backend clearly has but the frontend doesn't show" are ultimately not because the API didn't return them, but because the reading path was wrong.

Typical mistake:

```json
{
  "items": [...]
}
```

This is NOT the current Rust API structure.

The real structure is:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [...]
  }
}
```

In other words:

- You cannot read `response.items`
- Nor can you read `response.data.items` if your HTTP client has an additional outer object layer
- You should ultimately read from the `data` in the API response body

## 3. Specific Example: Event Stream API

`GET /api/v1/jobs/{job_id}/events?limit=50&offset=0`

The actual return structure is:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "job_id": "20260404150516-75857c",
        "seq": 1,
        "ts": "2026-04-04T15:05:16Z",
        "level": "info",
        "stage": "queued",
        "event": "job_created",
        "message": "Job has been created",
        "payload": {
          "stage": "queued",
          "status": "queued",
          "workflow": "book"
        }
      }
    ],
    "limit": 50,
    "offset": 0
  }
}
```

The key points here are:

- The event array is in `data.items`
- `limit` is in `data.limit`
- `offset` is in `data.offset`

## 4. Recommended Frontend Unwrapping Order

Whether for job details, lists, or event streams, it is recommended to process in this order:

1. First check the HTTP status code
2. Then check the `code` in the response body
3. When `code === 0`, read `data`
4. Never assume business fields are at the top level

## 5. Judgment Logic Suitable for Direct Frontend Implementation

- If HTTP is not `2xx`, handle as a network or service error
- If HTTP is `2xx` but `code !== 0`, handle as a business error
- If `code === 0` and `data == null`, handle as "success but no business payload"
- If a field should be in `data.xxx`, don't look for it at the top level