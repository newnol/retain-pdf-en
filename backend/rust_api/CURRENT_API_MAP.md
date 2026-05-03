# Current API Map

This document answers one question:

**How does this Rust API + Python worker system actually run right now.**

No history, no compatibility details, just the current formal main chain.

## Quick Navigation

- Document entry point:
  [`README.md`](/home/wxyhgk/tmp/Code/backend/rust_api/README.md)
- Current running main chain only:
  [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- Rust module boundaries only:
  [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
- OCR provider boundaries only:
  [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)
- Stage runtime contract only:
  [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
- External API protocol only:
  [`API_SPEC.md`](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)

## 1. Current System Layers

The backend is now split into two layers:

### Rust Layer

Responsibilities:

- External HTTP API
- Authentication
- Job creation / queuing / state machine
- SQLite persistence
- Artifact / event queries
- Starting Python workers

Code entry points:

- [`src/routes/jobs/mod.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes/jobs/mod.rs)
- [`src/services/jobs/*`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs)
- [`src/job_runner/*`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner)

### Python Layer

Responsibilities:

- OCR provider calls
- raw OCR -> normalized `document.v1.json`
- Translation
- Rendering
- PDF merge / post-processing

Code entry points:

- [`backend/scripts/entrypoints/run_provider_case.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_provider_case.py)
- [`backend/scripts/entrypoints/run_provider_ocr.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_provider_ocr.py)
- [`backend/scripts/entrypoints/run_normalize_ocr.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_normalize_ocr.py)
- [`backend/scripts/entrypoints/run_translate_only.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_translate_only.py)
- [`backend/scripts/entrypoints/run_render_only.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_render_only.py)

## 2. Current Formal Workflows

The workflows that are currently considered stable externally are:

- `book`
  Meaning: provider-backed full pipeline
  Chain: OCR -> Normalize -> Translate -> Render

- `translate`
  Meaning: OCR -> Normalize -> Translate
  No render step

- `render`
  Meaning: Reuse existing translation artifacts, only render

- `ocr`
  Meaning: OCR-only / provider-only sub-pipeline

Note:

- `book` is the formal API identifier for the complete main pipeline
- It is **not** `mineru`
- OCR provider selection is not based on workflow, but on `ocr.provider`

## 3. Current Provider Selection

Current provider dispatch:

- `workflow = book`
- `ocr.provider = mineru | paddle`

In other words:

- `workflow` determines which major pipeline to run
- `ocr.provider` determines which OCR provider to use

Key code:

- Rust writes spec:
  - [`src/services/job_command_factory.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory.rs)
- Python dispatches by provider:
  - [`backend/scripts/services/ocr_provider/provider_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/provider_pipeline.py)

## 4. Current Formal Protocol: Stage Spec

The formal protocol between Rust and Python worker is no longer long CLI arguments, but:

```bash
python -u <entrypoint> --spec <job_root>/specs/<stage>.spec.json
```

Current formal stages:

- `provider.stage.v1`
- `normalize.stage.v1`
- `translate.stage.v1`
- `render.stage.v1`
- `book.stage.v1`

Corresponding Python loader:

- [`backend/scripts/foundation/shared/stage_specs.py`](/home/wxyhgk/tmp/Code/backend/scripts/foundation/shared/stage_specs.py)

## 5. Real Execution Chain from Rust to Python

Using the most important `book` as an example:

### Step 1: Frontend / Caller sends request

Typical entry point:

- `POST /api/v1/jobs`

Rust routes:

- [`src/routes/jobs/create.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes/jobs/create.rs)
- [`src/services/jobs/facade.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade.rs)

### Step 2: Rust creates job

Responsibilities:

- Validate request
- Generate job snapshot
- Persist to DB
- Enter queue

Key code:

- [`src/services/jobs/creation`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/creation)
- [`src/services/job_snapshot_factory.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_snapshot_factory.rs)
- [`src/services/job_launcher.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_launcher.rs)

Note:

- Route layer now only does HTTP adaptation
- `jobs` related use cases now go through `JobsFacade` first
- `uploads` / `glossaries` also go through `upload_api` / `glossary_api` respectively

### Step 3: Rust assembles stage command and spec

Rust assembles commands based on workflow:

- `book` -> `run_provider_case.py`
- `ocr` -> `run_provider_ocr.py`
- `translate` -> `run_translate_only.py`
- `render` -> `run_render_only.py`

Key code:

- [`src/services/job_command_factory.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory.rs)
- [`src/services/job_command_factory/entrypoints.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory/entrypoints.rs)
- [`src/services/job_command_factory/stage_specs.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory/stage_specs.rs)

### Step 4: Rust writes stage spec

For example, `book` will write:

- `DATA_ROOT/jobs/<job_id>/specs/provider.spec.json`

It contains:

- `job`
- `source`
- `ocr`
- `translation`
- `render`

The OCR provider is in:

- `ocr.provider`

### Step 5: job_runner enters the runtime main chain

Current real entry point:

- [`src/app/jobs.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/jobs.rs)
  Compresses `AppState` into `ProcessRuntimeDeps`
- [`src/job_runner/lifecycle.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/lifecycle.rs)
  Handles queued state, execution slots, workflow dispatch

### Step 6: Rust starts Python worker

Necessary env vars are injected here:

- `RETAIN_TRANSLATION_API_KEY`
- `RETAIN_MINERU_API_TOKEN`
- `RETAIN_PADDLE_API_TOKEN`

Key code:

- [`src/job_runner/process_runner.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner.rs)
- [`src/job_runner/process_runner/startup.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/startup.rs)
- [`src/job_runner/process_runner/execution.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/execution.rs)
- [`src/job_runner/worker_process.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/worker_process.rs)

### Step 7: Python worker executes

`run_provider_case.py` -> `provider_pipeline.main()`

Then:

- Reads `provider.spec.json`
- Checks `ocr.provider`
- `mineru` goes to MinerU branch
- `paddle` goes to Paddle branch
- Produces unified normalized `document.v1.json`
- Then calls `run_book_pipeline(...)`

Key code:

- [`backend/scripts/entrypoints/run_provider_case.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_provider_case.py)
- [`backend/scripts/services/ocr_provider/provider_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/provider_pipeline.py)

## 6. Current Most Important Artifact Directories

Standard directory for each job:

- `DATA_ROOT/jobs/<job_id>/source`
- `DATA_ROOT/jobs/<job_id>/ocr`
- `DATA_ROOT/jobs/<job_id>/translated`
- `DATA_ROOT/jobs/<job_id>/rendered`
- `DATA_ROOT/jobs/<job_id>/artifacts`
- `DATA_ROOT/jobs/<job_id>/logs`
- `DATA_ROOT/jobs/<job_id>/specs`

Most important files:

- `specs/provider.spec.json`
- `ocr/result.json`
- `ocr/normalized/document.v1.json`
- `ocr/normalized/document.v1.report.json`
- `translated/translation-manifest.json`
- `artifacts/pipeline_summary.json`
- `rendered/*.pdf`

## 7. Current Most Important Data Contract

The translation / rendering main chain now depends on the normalized document.

Formal field contract:

- `geometry`
- `content`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy`
- `provenance`

Compatibility fields may still exist:

- `type`
- `sub_type`
- `bbox`
- `text`
- `lines`
- `segments`

But these are no longer the recommended main contract.

## 8. Current Entry Point Contract

Current entry points only use neutral naming:

- `run_provider_case.py`
- `run_provider_ocr.py`
- `run_document_flow.py`

Current principles:

- Main entry point: `run_provider_case.py`
- Main protocol: `provider.stage.v1`
- Main summary file: `pipeline_summary.json`

## 9. Current Event and Failure Handling

The current formal event stream is:

- Python worker writes `DATA_ROOT/jobs/<job_id>/logs/pipeline_events.jsonl`
- Rust query layer merges DB events and `pipeline_events.jsonl`
- Rust detail/list prioritizes live pipeline stage snapshot over stale DB `job.stage`

The current formal failure contract is:

- `data.failure`

Compatibility fields are still retained, but roles are now fixed:

- `data.failure_diagnostic`
  Only as a compatibility projection of `failure`
- `events[*].event`
  For backward compatibility with old clients; new clients should prefer `event_type`
- `events[*].message`
  Debug/compatibility text; formal semantics should prefer `stage_detail` + `event_type`

Stage layering rules are also fixed:

- Top-level unified stages go in `stage`
- Provider-private states go in `provider_stage`

## 10. Three Things to Remember Right Now

1. `workflow=book` is the provider-backed full pipeline, not `mineru`
2. OCR provider selection is based on `ocr.provider`, not the workflow name
3. The stable boundary between Rust and Python is `--spec <stage>.spec.json`

## 11. Which Files to Look at First When Debugging

If you want to quickly locate issues, look in this order:

### What does the API request look like

- [`API_SPEC.md`](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)

### Which Python script does Rust actually launch

- [`src/services/job_command_factory.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory.rs)

### How does the Python provider entry point dispatch

- [`backend/scripts/services/ocr_provider/provider_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/provider_pipeline.py)

### What does a stage spec look like

- [`backend/scripts/foundation/shared/stage_specs.py`](/home/wxyhgk/tmp/Code/backend/scripts/foundation/shared/stage_specs.py)

### View the final main chain result

- `DATA_ROOT/jobs/<job_id>/artifacts/pipeline_summary.json`
