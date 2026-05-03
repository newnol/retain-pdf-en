# Stage Execution Contract

This document only answers one question:

**How does `job_runner` currently drive each stage, and which semantics are stable contracts.**

Related documents:

- Overall architecture boundary:
  [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
- Current runtime main pipeline:
  [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- OCR provider boundary:
  [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)

## 1. Objective

`job_runner` is responsible for connecting the Rust-side job state machine with the Python worker execution chain.

It is NOT responsible for:

- HTTP request parsing
- Job view assembly
- OCR provider transport detail definition

It IS responsible for:

- Selecting the execution chain
- Writing stage specs
- Starting Python workers
- Consuming stdout/stderr
- Updating job runtime state
- Handling timeout / cancel / failure

## 2. Current Stage Families

The current runtime pipeline is split into 4 families:

1. `provider`
2. `normalize`
3. `translate`
4. `render`

Corresponding formal specs:

- `provider.stage.v1`
- `normalize.stage.v1`
- `translate.stage.v1`
- `render.stage.v1`

## 3. Workflow to Stage Chain Mapping

### 3.1 `workflow=book`

Pipeline:

```text
OCR child job
  -> provider transport
  -> normalize
parent job
  -> translate
  -> render
```

Entry code:

- [translation_flow.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/translation_flow.rs)

### 3.2 `workflow=translate`

Pipeline:

```text
OCR child job
  -> provider transport
  -> normalize
parent job
  -> translate
```

Does not enter render.

### 3.3 `workflow=render`

Pipeline:

```text
reuse source.artifact_job_id
  -> render
```

Entry code:

- [render_flow.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/render_flow.rs)

### 3.4 `workflow=ocr`

Pipeline:

```text
provider transport
  -> normalize
```

Entry code:

- [ocr_flow/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/ocr_flow/mod.rs)

Current additional constraints:

- `ocr_flow/mod.rs`
  Is the sole orchestrator of the OCR sub-pipeline
- Only it can:
  - Select local upload / remote url transport branch
  - Assemble provider client and dispatch to specific transport helper
  - Assemble normalize stage command
  - Hand the OCR sub-pipeline back to the common `process_runner`
- Other sub-modules in `ocr_flow/*` are only responsible for:
  - Provider transport
  - Workspace/path preparation
  - Provider result/raw artifact processing
  - Source PDF recovery
  - Leaf helpers for prepared upload files or remote source PDFs

## 4. Runtime Main Modules

### 4.1 `lifecycle`

File:

- [lifecycle.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/lifecycle.rs)

Responsibilities:

- Task enters queue
- Acquire execution slot
- Cancel short-circuit and queued persistence
- Dispatch by workflow to:
  - `ocr_flow`
  - `translation_flow`
  - `render_flow`

Current conventions:

- `lifecycle.rs` only retains runner top-level orchestration
- `should_skip_job_execution(...)`
  Handles cancel / canceled short-circuit
- `persist_queued_job(...)`
  Handles queued state persistence
- `dispatch_workflow(...)`
  Handles workflow -> runner flow dispatch
- `persist_failed_job(...)`
  Handles failure cleanup
- `clear_job_cancel_request(...)`
  Handles unified cancel registry cleanup

### 4.2 Stage Command Factory

Files:

- [job_command_factory.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory.rs)
- [job_command_factory/stage_specs.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory/stage_specs.rs)
- [job_command_factory/entrypoints.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory/entrypoints.rs)

Responsibilities:

- Write stage specs
- Select Python entry point
- Generate final command

### 4.3 `worker_process`

File:

- [worker_process.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/worker_process.rs)

Responsibilities:

- Start Python worker
- Inject env
- Terminate process tree

### 4.4 `process_runner`

Files:

- [process_runner.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner.rs)
- [process_runner/startup.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/startup.rs)
- [process_runner/execution.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/execution.rs)
- [process_runner/result_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/result_support.rs)
- [process_runner/timeout_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/timeout_support.rs)
- [process_runner/failure_ai_diagnosis.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/failure_ai_diagnosis.rs)
- [process_runner/io_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/io_support.rs)

Responsibilities:

- `process_runner.rs`
  Only retains orchestrator
- `startup.rs`
  Start worker, write running initial state
- `execution.rs`
  Read stdout/stderr, wait for process end, handle timeout branch
- `result_support.rs`
  Backfill `ProcessResult`
- `timeout_support.rs`
  Timeout state recording and persistence
- `failure_ai_diagnosis.rs`
  AI failure diagnosis
- `io_support.rs`
  stdout/stderr consumption strategy; leaf helpers only take `JobPersistDeps + canceled_jobs`

### 4.5 `runtime_state`

File:

- [runtime_state.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/runtime_state.rs)

Responsibilities:

- Maintain artifacts/runtime/failure runtime state changes

## 5. Runtime State Semantics

Current job status:

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`

Current common stages:

- `queued`
- `ocr_submitting`
- `ocr_upload`
- `mineru_processing`
- `normalizing`
- `translating`
- `rendering`
- `finished`
- `failed`
- `canceled`

Rules:

- `status` is the final state classification
- `stage` is the current execution phase
- `stage_detail` is a human-readable runtime description

Do not stuff business logic into the `stage` text.

## 6. stdout Contract

Python workers communicate runtime clues through stdout.

Current important labels are in:

- [stdout_parser/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/mod.rs)

For example:

- `job root`
- `source pdf`
- `layout json`
- `normalized document json`
- `normalization report json`
- `translations dir`
- `output pdf`
- `summary`

Rules:

- When adding new worker artifacts that need Rust-side consumption, prefer the stdout label contract
- Don't let route/service layers directly guess Python output directories

## 7. timeout / cancel Contract

### 7.1 cancel

Current cancel has two layers:

- cancel registry
- process termination

Modules:

- [cancel_registry.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/cancel_registry.rs)
- [worker_process.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/worker_process.rs)

Semantics:

- After a job is marked for cancel, the runner will try to terminate the process tree
- The `normalizing` stage allows limited continuation to finish up

### 7.2 timeout

Semantics:

- Timeout seconds come from `request_payload.runtime.timeout_seconds`
- After timeout, the runner is responsible for killing the worker
- Then marks the job as `failed`

Current details:

- `normalizing` -> `normalization timeout`
- Other provider transport stages -> `provider timeout`

## 8. Success and Failure Determination

`process_runner` currently classifies process results into 4 categories:

- `Canceled`
- `Succeeded`
- `SucceededWithShutdownNoise`
- `Failed`

That is:

- Process exit code is not the sole criterion
- If artifacts have been fully written, certain Python shutdown noise is treated as success

These rules are concentrated in:

- [process_runner.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner.rs)

## 9. Artifacts Contract

The core artifact fields that `job_runner` currently depends on include:

- `job_root`
- `source_pdf`
- `layout_json`
- `normalized_document_json`
- `normalization_report_json`
- `translations_dir`
- `output_pdf`
- `summary`
- `provider_raw_dir`
- `provider_zip`
- `provider_summary_json`

Rules:

- When switching stages, try to pass downstream inputs through artifacts
- Don't let downstream re-guess paths

## 10. Team Collaboration Red Lines

### Red Line 1

When adding stage fields, first modify:

- `commands/stage_specs.rs`

Don't first modify route parameters.

### Red Line 2

When adding worker entry points, first modify:

- `commands/entrypoints.rs`

Don't assemble temporary commands in `process_runner`.

### Red Line 3

When adding cancel/timeout semantics, preferably modify:

- `cancel_registry.rs`
- `worker_process.rs`
- `process_runner.rs`

Don't each add a copy in `translation_flow` / `render_flow`.

### Red Line 4

When adding artifact path semantics:

- Worker output -> stdout label contract
- Rust consumption -> `stdout_parser` + `runtime_state`

Don't directly parse Python directory structure at the route/service layer.

## 11. Recommended Change Paths

### Scenario 1: Add a new Python stage

Order:

1. `commands/stage_specs.rs`
2. `commands/entrypoints.rs`
3. Corresponding flow module
4. `stdout_parser`
5. `runtime_state`

### Scenario 2: Adjust OCR child -> parent handoff fields

Order:

1. `ocr_flow/mod.rs`
2. `translation_flow.rs`
3. `runtime_state.rs`

### Scenario 3: Adjust render-only input source

Order:

1. `render_flow.rs`
2. `storage_paths`
3. Add presentation summary if necessary

## 12. One-Sentence Constraint

The stable boundary of `job_runner` should be:

- Upstream gives it `JobRuntimeState`
- It drives Python workers through specs
- It collects runtime results through stdout/artifacts
- It updates job state back to the Rust persistence layer

Anything beyond this responsibility should not continue to be piled here.
