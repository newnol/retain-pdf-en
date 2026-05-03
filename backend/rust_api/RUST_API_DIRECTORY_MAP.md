# Rust API Directory Map

This document only answers one question:

**When modifying `rust_api`, which directory should I enter first?**

## Most Common Entry Points

- Change HTTP endpoints:
  [`src/routes`](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes)
- Change jobs use case orchestration:
  [`src/services/jobs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs)
- Change worker execution pipeline:
  [`src/job_runner`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner)
- Change OCR provider dispatch and adaptation:
  [`src/ocr_provider`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider)

## Directory Map

### `src/app`

- Purpose:
  Application startup, `AppState` assembly, router mounting, service startup.
- Entry condition:
  Only enter here when modifying global resources, startup logic, or route mounting.
- Key files:
  - [`src/app/state.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/state.rs)
    `AppState` and global resource initialization.
  - [`src/app/router.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/router.rs)
    axum route top-level mounting point.
  - [`src/app/jobs.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/jobs.rs)
    Jobs facade composition root. This is responsible for assembling `AppState` into `JobsFacade`; `routes` no longer directly touches `job_runner`.

### `src/routes`

- Purpose:
  HTTP parameter extraction, request forwarding, unified response wrapping.
- What it should NOT do:
  Does not directly touch `job_runner`, does not assemble underlying business logic itself.

#### `src/routes/jobs`

- `common.rs`
  Jobs route shared lightweight entry point; only takes existing facade, no longer assembles runtime itself.
- `download_adapter.rs`
  File download route adapter.
- `query_adapter.rs`
  JSON query / debug / cancel route adapter.
- `create.rs` / `download.rs` / `query.rs` / `control.rs` / `translation_debug.rs`
  Actual axum route entry points.

### `src/services`

- Purpose:
  Application service entry points and internal business implementation.

#### `src/services/jobs/facade`

- Purpose:
  Provide unified jobs entry point for routes.
- `command/*`
  Command-type capabilities like creation, cancellation, synchronous bundle.
- `query/*`
  Query-type capabilities like list, details, download, artifacts, translation debug.

#### `src/services/jobs/creation`

- `submit.rs`
  Create and start a task.
- `bundle.rs`
  Synchronously run the complete pipeline and produce a bundle.
- `prepare.rs`
  Input parsing, existence checks, pre-validation; only produces `Prepared*` inputs, does not generate `JobSnapshot`.
- `job_builders.rs`
  Workflow-level snapshot orchestration; only consumes `Prepared*` inputs and calls snapshot factory, no longer does pre-validation itself.
- `upload.rs`
  Upload persistence and upload record reading.
- `context.rs`
  Creation-side explicit deps.

#### `src/services/jobs/presentation`

- Purpose:
  External view assembly, summary reading, response projection.
- Entry condition:
  Enter here when changing API return structure, summary fields, or redaction display.

#### Other service entry points

- [`src/services/upload_api.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/upload_api.rs)
  Upload endpoint entry point.
- [`src/services/glossary_api.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/glossary_api.rs)
  Glossary endpoint entry point.
- [`src/services/job_snapshot_factory.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_snapshot_factory.rs)
  Job snapshot/command construction boundary.
- [`src/services/job_launcher.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_launcher.rs)
  Job persistence and launch boundary.
- [`src/services/runtime_gateway.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/runtime_gateway.rs)
  Services-side access to runtime capabilities consolidation layer.

### `src/job_runner`

- Purpose:
  Task queuing, worker startup, stdout/stderr consumption, failure attribution, cancellation, timeout.
- Quick judgment:
  Enter here when changing stage execution order, concurrency slots, process control, or runtime state synchronization.
- Current directory map:
  - `mod.rs`
    Runner facade, common deps, external exports; `ProcessRuntimeDeps` here is only for orchestrator use, `JobPersistDeps` is the persistence resource boundary for leaf helpers.
  - `lifecycle.rs`
    Task queuing, execution slot, workflow dispatch.
  - `process_runner.rs` + `process_runner/*`
    Real worker executor; `process_runner.rs` only retains orchestrator, `completion.rs` handles completion state classification and shutdown-noise determination, `timeout_support.rs` handles timeout state recording, `failure_ai_diagnosis.rs` handles failure AI diagnosis, `io_support.rs` handles stdout/stderr consumption and only depends on `JobPersistDeps + canceled_jobs`.
  - `translation_flow.rs` + `translation_flow_*.rs`
    Post-OCR translation/rendering parent task orchestration; `translation_flow.rs` retains orchestrator, `translation_flow_child.rs` handles upload source reading, parent entering `ocr_submitting`, OCR child creation, `translation_flow_stage.rs` handles translate/render stage preparation and `ocr_child_finished` event, `translation_flow_support.rs` handles OCR final state determination and translation input extraction.
  - `ocr_flow/*`
    OCR child job execution pipeline, provider polling/download/markdown materialize; `ocr_flow/mod.rs` is orchestrator, `ocr_flow/support.rs` handles OCR job saving, parent OCR state mirroring, transport/source-pdf failure handling and `sync_parent_with_ocr_child(...)`, `workspace.rs` only handles paths and directories, `polling.rs` only handles polling wait and cancel check.
  - `stdout_parser/*`
    stdout line-level rule parsing; `mod.rs` is facade, `labels.rs` manages stdout label constants, `state.rs` manages shared parsing state, `stage_rules.rs` / `artifact_rules.rs` manage line-level rules, `failure.rs` manages provider failure attribution.
  - `runtime_state.rs`
    Runtime snapshot / failure / artifact unified update utility.
  - `worker_process.rs`
    Child process startup, env injection, process tree termination; now only takes `&AppConfig + job`, no longer depends on full runtime deps.

### `src/ocr_provider`

- Purpose:
  OCR provider dispatch, provider-specific protocol conversion, provider output consolidation.
- Quick judgment:
  Enter here when changing MinerU / Paddle integration details.

### `src/storage_paths.rs` + `src/storage_paths/*`

- Purpose:
  Artifact keys, path normalization, path resolution, artifact registry collection.
- Current sub-boundaries:
  - `constants.rs`
    Artifact key / group / kind constants.
  - `job_paths.rs`
    `JobPaths` and task directory creation.
  - `path_ops.rs`
    Relative path normalization, storage normalization, legacy determination.
  - `resolvers.rs`
    Various published artifact path resolvers.
  - `registry.rs`
    Project task files into artifact entry lists.

### `src/db.rs` + `src/db/*`

- Purpose:
  SQLite persistence entry point.
- Current sub-boundaries:
  - `rows.rs`
    SQLite row -> domain model decoding.
  - `schema.rs`
    Schema checking and startup migration protection.
  - `db.rs`
    Main `Db` facade and concrete read/write use cases.

## Three Quick Judgments

- "Is this an HTTP behavior change?"
  First look at `src/routes`
- "Is this a jobs use case orchestration change?"
  First look at `src/services/jobs/facade` and `src/services/jobs/creation`
- "Is this a worker / Python execution change?"
  First look at `src/job_runner`

## A More Intuitive Directory Map

Currently recommended to understand the backend along this line:

1. `src/routes`
   HTTP adaptation layer, only does parameter extraction and response wrapping.
2. `src/services/jobs/facade`
   Jobs use case top-level entry point; routes only talk to facade.
3. `src/services/jobs/creation` / `src/services/jobs/presentation`
   The former handles creation and submission, the latter handles detail/list/events external projection.
4. `src/job_runner`
   Runtime orchestration, subprocess, OCR flow, translation/render flow.
5. `src/ocr_provider`
   Provider protocol and provider output normalization.

Newcomers who just want to quickly locate the modification entry point can first ask themselves whether they are modifying:

- HTTP adaptation
- Use case orchestration
- Display projection
- Runtime execution
- Provider protocol

Then enter the corresponding directory; don't start by modifying across `routes -> services -> job_runner` multiple layers simultaneously.

## Recommended Reading Order for Newcomers

If this is your first time entering this backend, it is recommended to read in this order:

1. [`src/app/router.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/router.rs)
   First know what HTTP endpoints exist.
2. [`src/app/jobs.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/jobs.rs)
   Then see how jobs-related dependencies are assembled.
3. [`src/routes/jobs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes/jobs)
   See how routes only forward requests.
4. [`src/services/jobs/facade`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade)
   See command/query use case entry points.
5. [`src/services/jobs/creation`](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/creation)
   See the creation pipeline's preparation, snapshot, submission, bundle.
6. [`src/job_runner`](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner)
   Finally enter the runtime execution layer.
