# Event Stream API

## 1. Endpoint URL

Main task event stream:

`GET /api/v1/jobs/{job_id}/events?limit=50&offset=0`

OCR sub-task event stream:

`GET /api/v1/ocr/jobs/{job_id}/events?limit=50&offset=0`

## 2. What This Endpoint Does

The event stream endpoint is mainly used for:

- Debugging
- Troubleshooting
- Observing retry pipelines
- Seeing what actually happened in the backend at a particular stage

It is NOT the primary source of truth for the "process timeline".

This distinction must be clear:

- Main timeline: `runtime.stage_history`
- Debug details: `/events`

## 3. Response Structure

The actual response is not a top-level `items`, but rather:

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
        "message": "Job created",
        "payload": {}
      }
    ],
    "limit": 50,
    "offset": 0
  }
}
```

So the frontend read path should be:

- `data.items`
- `data.limit`
- `data.offset`

## 4. Fields Per Event

Each event consistently contains:

- `job_id`
- `seq`
- `ts`
- `level`
- `stage`
- `event`
- `message`
- `payload`

Where:

- `seq` is a monotonically increasing sequence number within the task
- `ts` is the event timestamp
- `level` is typically `info / warn / error`
- `stage` is the stage to which the event belongs
- `event` is the machine-readable event name
- `message` is the human-readable description
- `payload` is additional details

## 5. Common Event Types

Currently the key types to identify are:

- `job_created`
- `status_changed`
- `stage_updated`
- `stage_transition`
- `stage_progress`
- `retry_scheduled`
- `failure_classified`
- `job_terminal`

When handling backward compatibility, you may also see:

- `job_error`
- `ocr_child_created`
- `ocr_child_finished`

## 6. Default Persistence

In the current implementation, the event stream is persisted by default.

It writes to two locations simultaneously:

- Database `events` table
- `DATA_ROOT/jobs/{job_id}/logs/events.jsonl`

So as long as the task was normally executed by the current backend, the event stream should generally be available.

## 7. Why the Page Might Show "Event Stream is Empty"

Common causes fall into only three categories:

1. The frontend read the wrong wrapper layer, reading top-level `items` instead of `data.items`
2. The request used the wrong `job_id` for this task
3. This is a very early historical task where event stream persistence was not yet available

For recent new tasks, if the endpoint returns `200` and `data.items` is not empty, but the frontend still shows empty, it is almost certainly category 1.

## 8. A Real Response Example

Task `20260404150516-75857c` actually returns `200 OK` with events, confirming the endpoint itself is working correctly:

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
        "message": "Job created",
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
