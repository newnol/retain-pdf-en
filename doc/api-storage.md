# Storage Structure

The current system uniformly uses `DATA_ROOT` as the runtime root directory.

## 1. Main Paths

- `DATA_ROOT/uploads/`: Uploaded files
- `DATA_ROOT/jobs/{job_id}/`: Per-task working directory
- `DATA_ROOT/downloads/`: Download cache
- `DATA_ROOT/db/jobs.db`: SQLite

## 2. Task Directory Structure

```text
jobs/{job_id}/
├── source/
├── ocr/
├── translated/
├── rendered/
├── artifacts/
└── logs/
```

## 3. Event Files

Task events are simultaneously written to:

- `DATA_ROOT/jobs/{job_id}/logs/events.jsonl`

## 4. Current Design Conventions

- `DATA_ROOT` is the sole runtime storage root
- Rust is responsible for allocating task directories
- Python workers only consume paths passed in by Rust
- SQLite currently handles three types of persistent information: `jobs / events / artifacts`
