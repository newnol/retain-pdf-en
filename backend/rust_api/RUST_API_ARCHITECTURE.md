# Rust API Architecture

This document only answers one question:

**What are the current team collaboration boundaries for `rust_api`, and where is the right place to make changes.**

No history, no compatibility migration — by default only look at the current mainline code.

Related documents:

- Documentation index:
  [`README.md`](/home/wxyhgk/tmp/Code/backend/rust_api/README.md)
- Directory map:
  [`RUST_API_DIRECTORY_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_DIRECTORY_MAP.md)
- Current runtime main pipeline:
  [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- OCR provider boundary:
  [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)
- Stage runtime contract:
  [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
- Rust-side artifact boundary:
  [`doc/rust_api/10-Rust-Side Artifact Boundary.md`](/home/wxyhgk/tmp/Code/doc/rust_api/10-Rust-Side%20Artifact%20Boundary.md)
- External API protocol:
  [`API_SPEC.md`](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)

## 1. Overall Layering

The current `rust_api` is split into 6 layers:

1. `app`
2. `routes`
3. Application entry points in `services`
4. Internal implementations in `services`
5. `job_runner`
6. `ocr_provider`

Dependency direction must remain unidirectional:

```text
app -> routes -> application services -> internal services -> job_runner / ocr_provider
```

Reverse dependencies are forbidden.

For example:

- `routes` should not know how Python worker commands are assembled
- `job_runner` should not know about HTTP Headers and JSON envelopes
- `ocr_provider` should not know about route-layer return structures

## 1.1 Where `AppState` Is Allowed to Appear

`AppState` is not a general dependency injection container and is currently only allowed to remain in these locations:

- `app/*`
  Responsible for assembling and holding global resources
- `axum` route entry functions
  i.e., the layer where `State(AppState)` is unpacked
- A small number of boundary-layer assembly points
  Used to compress `AppState` into narrower deps structs
- Test helper code

It is forbidden to directly pass `AppState` down to:

- The main business implementation chain in `services`
- The main runtime chain in `job_runner`
- `ocr_provider`
- Presentation / view assembly layer

If a module needs resources, the correct approach is:

1. Extract the needed fields from `AppState` at the boundary layer
2. Assemble them into an explicit deps struct
3. The business module only receives this narrower deps

Currently established common patterns:

- `routes/common.rs`
  Responsible for route-side common lightweight deps builder
- `routes/jobs/common.rs`
  Only retains jobs route-side shared deps / facade builder
- `routes/jobs/download_adapter.rs`
  Responsible for jobs file download route adapter
- `routes/jobs/query_adapter.rs`
  Responsible for jobs JSON query / debug / control route adapter
- `app/jobs.rs::build_process_runtime_deps(...)`
  Responsible for runner assembly

The runner-side rules are now fixed as:

- `job_runner` only exposes `ProcessRuntimeDeps::new(...)`
- The assembly responsibility for `AppState -> ProcessRuntimeDeps` stays in the `app/*` boundary layer
- `ProcessRuntimeDeps`
  Only retained for orchestrator-level entry use
- `JobPersistDeps`
  Responsible for the `db + data_root + output_root` persistence/event resources; leaf helpers prefer to take it directly rather than taking the entire runtime deps package
- `app/state.rs`
  Only responsible for `AppState` assembly; startup stale running job recovery has been moved down to `app/state_recovery.rs`
- `job_runner/lifecycle.rs`
  Only retains runner top-level orchestration; "queued persistence/cancellation short-circuit" and "dispatch by workflow" should continue to be small helpers rather than being stuffed back into a single large function

Do not import `AppState` directly into `job_runner`.

Do not repeatedly hand-write a local `route_deps(...)` in every route file.

## 1.2 Internal Contract vs External Contract

This boundary must be clear:

- `CreateJobInput` / `ResolvedJobSpec` / `JobSnapshot`
  are **internal runtime contracts**
- `JobDetailView` / `JobEventListView` / `TranslationDiagnosticsView`
  are **external API contracts**

Internal contracts may hold real credentials:

- `translation.api_key`
- `ocr.mineru_token`
- `ocr.paddle_token`

But these fields may only exist in:

- Runtime memory
- SQLite job records
- Worker env injection
- Stage spec `credential_ref`

They are forbidden from directly entering:

- HTTP JSON responses
- External diagnostics / replay / debug payloads
- Events API payloads

The current security adaptation layer has two types:

1. `public_request_payload(...)`
   Responsible for projecting internal `ResolvedJobSpec` into an externally returnable request payload
2. `models/redaction.rs`
   Responsible for unified redaction of arbitrary string / JSON payloads

Team collaboration rules:

- If adding a new external view, first decide whether it consumes the internal or external contract
- Any change that directly serializes an internal object to HTTP is considered an error by default
- When adding a new secret field, the redaction module must be updated simultaneously, not patched locally in the route

## 1.3 Architecture Gate

These boundaries are not only enforced by documentation but also by hard checks:

- Local command:
  `python3 backend/rust_api/scripts/check_architecture.py`
- CI workflow:
  `.github/workflows/rust-api-architecture.yml`

The current gate at minimum covers:

- `AppState` is not allowed to flow back into `services/job_runner/ocr_provider` main chain
- `routes` is not allowed to directly depend on `job_runner`
- `routes/jobs/*` is not allowed to re-define local `route_deps(...)`
- artifact / download boundary layer is not allowed to start understanding provider raw internal fields
- published markdown artifact is not allowed to re-derive from `provider_raw_dir/full.md` or `provider_raw_dir/images`

If the allowlist needs to be adjusted later, both the script and this document must be updated simultaneously — not just one of them.

## 1.4 Artifact Boundary

The Rust-side boundaries directly related to artifacts are fixed at four layers:

1. `provider raw`
2. `normalized`
3. `published artifact`
4. `download API`

Dependencies and responsibilities must remain unidirectional:

```text
provider raw -> normalized -> published artifact -> download API
```

Minimum definition of each layer:

- `provider raw`
  Provider raw result snapshot, only used for fidelity, tracing, troubleshooting, normalize input
- `normalized`
  Unified document contract from OCR to translation/rendering
- `published artifact`
  Rust's artifact key registration, discovery, and export layer for task files
- `download API`
  Outermost HTTP download exposure layer

Key Rust-side implementation points:

- [src/storage_paths.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/storage_paths.rs)
  Facade; now split into `constants / job_paths / path_ops / resolvers / registry`
- [src/services/artifacts/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/artifacts/mod.rs)
  Artifact facade; now split into `registry / bundle / response`
- [src/routes/jobs/download.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes/jobs/download.rs)
  Responsible for download HTTP adapter

Boundary rules:

- `storage_paths.rs` and `services/artifacts/*`
  Only handle files, artifact keys, stable resources; do not interpret provider raw internal JSON structure
- `db.rs`
  Now only retains the `Db` facade; row decode and schema checks have been moved down to `src/db/rows.rs` and `src/db/schema.rs`
- `routes/jobs/download.rs`
  Only exposes stable download entry points; does not promise provider private field semantics
- `normalized-document` / `normalization-report`
  Belong to the normalized boundary, not provider raw
- `provider_result_json` / `provider_raw_dir`
  Belong to the provider raw boundary; can only be downloaded as explicit artifacts, not served as a unified document interface
- published markdown materialize
  Must preserve the relative path semantics of images returned by the provider; page-scope prefixes are allowed, but internal path patterns must not be permanently rewritten into custom directory rules

Quick judgment:

- If a change requires the download layer to understand provider field names like `layoutParsingResults` or `prunedResult`, the boundary has been penetrated
- If a change only adds artifact keys, adjusts resource paths, or adjusts stable download entry points, it should typically fall in the published artifact or download API layer

## 1.4 Published Markdown Artifact Boundary

This is a boundary that has been recently tightened:

- `provider_result_json`
- `provider_raw_dir`

Belong to provider raw.

- `ocr/normalized/document.v1.json`

Belongs to the normalized unified contract.

- `md/full.md`
- `md/images/`
- `markdown_bundle_zip`

Belong to published job artifacts.

Rules:

1. `provider_raw_dir` may retain provider raw responses and debug materials.
2. `provider_raw_dir` must not be used as a fallback source for published markdown artifacts.
3. `resolve_markdown_path()` / `resolve_markdown_images_dir()` and similar external resource resolution functions may only resolve published paths like `job_root/md/*`.
4. If a provider needs to expose Markdown in the future, a new explicit publish/materialize step should be added, rather than having the download layer or storage path layer guess the provider raw layout.

Additional constraints:

- publish/materialize may do "conflict-prevention wrapping", e.g., adding `page-N/` prefix to image paths in multi-page tasks
- But it must not rewrite the internal relative path structure returned by the provider
- For example, when Paddle returns `<img src="imgs/foo.jpg">`, after publishing it can be `page-6/imgs/foo.jpg`
- It must not become our custom fixed pattern like `assets/foo.jpg` or other repository-private naming

The reason is simple:

- Provider raw changes frequently
- Published artifact is the stable external download interface
- Once the two layers are mixed, `markdown_ready` becomes inaccurate and the download interface couples with provider private structure

## 2. Module Responsibilities

### 2.1 `app/`

Files:

- [src/app/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/mod.rs)
- [src/app/state.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/state.rs)
- [src/app/router.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/router.rs)
- [src/app/server.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/server.rs)

Responsibilities:

- Assemble `AppState`
- Start HTTP server
- Mount routes
- Recover leftover running jobs at startup

What it should NOT do:

- No business validation
- No job view assembly
- No worker workflow decisions

### 2.2 `routes/`

Directory:

- [src/routes](/home/wxyhgk/tmp/Code/backend/rust_api/src/routes)

Responsibilities:

- HTTP request parsing
- Header / Query / Multipart extraction
- Forward requests to services
- Return unified JSON / file responses

What it should NOT do:

- No direct access to SQLite details
- No direct reading of artifact files
- No direct assembly of Python commands

The current `jobs` routes are now unified through:

- [src/services/jobs/facade.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade.rs)

That is:

- `routes/jobs/*` only calls `JobsFacade`
- `routes/common.rs`
  Only retains unified `ok_json(...)` HTTP envelope helper
- `routes/jobs/common.rs`
  Only retains jobs route shared deps builder
- `routes/jobs/download_adapter.rs`
  Only retains download route adapter
- `routes/jobs/query_adapter.rs`
  Only retains JSON / debug / cancel route adapter
- `routes/glossaries.rs`
  Only calls `services/glossary_api.rs`
- `routes/uploads.rs`
  Only calls `services/upload_api.rs`

Quick judgment:

- To change HTTP input/output parameters, first look at `routes/*`
- To change use case orchestration, first look at application service
- To change provider / worker / stage behavior, don't start from the route

### 2.3 Application entry points in `services/`

Directory:

- [src/services](/home/wxyhgk/tmp/Code/backend/rust_api/src/services)

Responsibilities:

- Provide stable call entry points for routes
- Handle use case orchestration and return external views
- Shield `db/config/data_root/storage` resource assembly details

Currently established application entry points:

- [src/services/jobs/facade.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade.rs)
- [src/services/glossary_api.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/glossary_api.rs)
- [src/services/upload_api.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/upload_api.rs)

Rules:

- Routes should preferably only depend on these entry points
- Don't let routes directly assemble `db + config + helper + artifact service`
- If an application service continues to grow, prefer splitting into facade sub-modules or deps sub-structures; don't revert to a single entry file plus a single deps

### 2.4 Internal implementations in `services/`

Current key divisions:

- [src/services/job_snapshot_factory.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_snapshot_factory.rs)
  Responsible for job snapshot / command assembly
- [src/services/job_launcher.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_launcher.rs)
  Responsible for job persistence and execution launch
- [src/services/runtime_gateway.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/runtime_gateway.rs)
  Responsible for services-side runtime capability consolidation
- [src/services/jobs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs)
  Responsible for jobs-related business

`services/jobs` is further split into:

- `creation`
- `control`
- `query`
- `debug`
- `facade`
- `presentation`

#### `services/jobs/facade`

Files:

- [src/services/jobs/facade.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade.rs)
- [src/services/jobs/facade/command](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade/command)
- [src/services/jobs/facade/query](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/facade/query)

Responsibilities:

- Provide unified entry point for the route layer
- Shield `db/config/data_root` and other low-level details
- Continue splitting into smaller facade sub-modules by use case, rather than stacking all entry points back into one file
- Separate command-side and query-side dependencies, avoiding a single deps that simultaneously drags create/query/debug/download to inflate together

Rules:

- New job route capabilities should preferably be added to the facade first, then called by routes
- Resources needed for creation/cancellation should preferably go into `CommandJobsDeps`
- Resources needed for query/download/debug should preferably go into `QueryJobsDeps`

#### `services/jobs/creation`

Directory:

- [src/services/jobs/creation](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/creation)

Responsibilities:

- `submit.rs`
  Only responsible for "receiving input then creating and starting a task"
- `bundle.rs`
  Only responsible for "synchronously running the complete pipeline and producing a download bundle"
- `job_builders.rs`
  Only responsible for parsing input into `JobSnapshot`
- `upload.rs`
  Only responsible for PDF upload persistence and upload record reading
- `context.rs`
  Only responsible for creation-side explicit deps

Rules:

- Don't stuff "submit task" and "synchronous bundle" back into one file
- Don't re-assemble upload storage details in facade or route
- When adding new creation use cases, first determine whether it belongs to `submit`, `bundle`, `job_builders`, or `upload`

#### `services/jobs/presentation`

Directory:

- [src/services/jobs/presentation](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/jobs/presentation)

Responsibilities:

- `views.rs`
  Responsible for API view assembly
- `summary_loaders.rs`
  Responsible for reading summary information from manifest / report / summary files
- `mod.rs`
  Responsible for presentation external boundary

Rules:

- To change JSON return structure, prefer changing `views.rs`
- To change summary fields supplemented from disk, prefer changing `summary_loaders.rs`
- Don't stuff file reading logic back into view assembly functions

### 2.5 `job_runner/`

Directory:

- [src/job_runner](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner)

Responsibilities:

- Job runtime scheduling
- Python worker startup
- stdout/stderr parsing
- Cancellation, timeout, failure attribution
- OCR child job / translate / render execution pipeline

Current split:

- `lifecycle`
  Task queuing, execution slot acquisition, workflow dispatch
- `cancel_registry`
  Cancellation request registry
- `execution_queue`
  Concurrency slot waiting
- `services/job_command_factory`
  Stage command / stage spec / worker entry command unified factory; `job_runner` no longer maintains its own command builder
- `worker_process`
  Process startup, env injection, process tree termination
- `process_runner`
  Real worker execution orchestrator
- `process_runner/completion.rs`
  Cancel / success / shutdown noise / failed completion state classification and backfill
- `process_runner/timeout_support.rs`
  Timeout text and timeout failure state recording
- `process_runner/failure_ai_diagnosis.rs`
  Failure AI diagnosis request/response and event recording
- `process_runner/io_support.rs`
  stdout/stderr consumption and stream reading strategy during cancel; only takes `JobPersistDeps + canceled_jobs`
- `runtime_state`
  Runtime snapshot changes
- `translation_flow`
  translate / book related orchestrator; only responsible for chaining OCR child -> translate -> optional render
- `translation_flow_child.rs`
  Upload source reading, parent task entering `ocr_submitting`, OCR child construction and `ocr_child_created` event
- `translation_flow_stage.rs`
  Translate stage command preparation, `ocr_child_finished` event, post-translate render stage preparation
- `translation_flow_support.rs`
  OCR final state determination, translate input extraction and similar pure rule helpers
- `render_flow`
  Render-only pipeline
- `ocr_flow`
  OCR provider execution pipeline
- `ocr_flow/support.rs`
  OCR job saving, parent OCR state mirroring, transport/source-pdf failure handling, `sync_parent_with_ocr_child(...)`
- `ocr_flow/workspace.rs`
  Only responsible for OCR workspace path and directory preparation; now only takes `&AppConfig`
- `ocr_flow/polling.rs`
  Only responsible for polling wait and cancel check; `should_stop_polling(...)` now only takes cancel handle
- `stdout_parser`
  stdout parsing facade
- `stdout_parser/labels.rs` / `state.rs` / `stage_rules.rs` / `artifact_rules.rs` / `failure.rs`
  stdout line labels, shared parsing state, stage/artifact/failure rules

#### `services/job_command_factory`

Directory:

- [src/services/job_command_factory](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory)

Responsibilities:

- `stage_specs.rs`
  Write spec files for `provider/normalize/translate/render`
- `entrypoints.rs`
  Select Python script entry point, assemble entry parameters
- `command_builder.rs`
  Only handles command line construction details
- [src/services/job_command_factory.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/services/job_command_factory.rs)
  Only retains external `build_*` facade

Rules:

- To change spec fields, modify `stage_specs.rs`
- To change worker entry scripts, modify `entrypoints.rs`
- Don't re-write JSON at the facade layer

#### `job_runner/process_runner`

Files:

- [src/job_runner/process_runner.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner.rs)
- [src/job_runner/process_runner/completion.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/completion.rs)
- [src/job_runner/process_runner/timeout_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/timeout_support.rs)
- [src/job_runner/process_runner/failure_ai_diagnosis.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/failure_ai_diagnosis.rs)
- [src/job_runner/process_runner/io_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/process_runner/io_support.rs)

Responsibilities:

- `process_runner.rs`
  Only retains worker execution orchestrator
- `completion.rs`
  Handles completion state classification beyond timeout, shutdown noise success determination, failure backfill
- `timeout_support.rs`
  Handles timeout failure state recording
- `failure_ai_diagnosis.rs`
  Handles AI-assisted failure diagnosis
- `io_support.rs`
  Handles stdout/stderr consumption and cancel special cases; leaf helpers no longer take the full `ProcessRuntimeDeps`

Rules:

- Don't write new command construction logic here
- Don't maintain cancel registry here
- Don't decide execution slot policy here
- `execute_process_job(...)`
  May keep the full `ProcessRuntimeDeps`
- `spawn_worker_process(...)` / `read_stdout(...)`
  These leaf helpers should only take the config / persist / cancel dependencies they actually need

#### `job_runner` Stop Line

The last round of decoupling should stop here:

- Orchestrator-level entry points continue to take `ProcessRuntimeDeps`
- Leaf helpers switch to `JobPersistDeps`, `&Db`, `&AppConfig`, or cancel handle
- Don't continue splitting orchestrators into more cross-file small functions
- Don't continue introducing traits / wrappers / facades just to pass 1-2 fewer fields

#### `job_runner/translation_flow_*`

Files:

- [src/job_runner/translation_flow.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/translation_flow.rs)
- [src/job_runner/translation_flow_child.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/translation_flow_child.rs)
- [src/job_runner/translation_flow_stage.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/translation_flow_stage.rs)
- [src/job_runner/translation_flow_support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/translation_flow_support.rs)

Responsibilities:

- `translation_flow.rs`
  Only retains parent translation job orchestrator
- `translation_flow_child.rs`
  Responsible for upload source reading, parent entering `ocr_submitting`, OCR child job creation and `ocr_child_created` event
- `translation_flow_stage.rs`
  Responsible for OCR child finish event, translate stage command preparation, post-translate render stage preparation
- `translation_flow_support.rs`
  Responsible for `finalize_parent_after_ocr(...)`, `translation_inputs_from_artifacts(...)` and similar pure rule helpers

Rules:

- Don't repeat OCR child construction details in the orchestrator
- Don't do persistence entry point selection in support helpers
- Translate/render command rewriting is unified in stage helpers

#### `job_runner/ocr_flow/*`

Files:

- [src/job_runner/ocr_flow/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/ocr_flow/mod.rs)
- [src/job_runner/ocr_flow/support.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/ocr_flow/support.rs)
- And `transport / polling / mineru / paddle / artifacts / provider_result / workspace / markdown_bundle / bundle_download / status / page_subset / mineru_retry / mineru_polling / paddle_markdown`

Responsibilities:

- `ocr_flow/mod.rs`
  Only retains OCR orchestrator, chaining transport -> normalize -> process runner
- `ocr_flow/support.rs`
  Responsible for OCR job saving, parent OCR state mirroring, transport/source-pdf failure handling, `sync_parent_with_ocr_child(...)`
- Other sub-files
  Each handles provider transport, polling, downloads, raw result placement, markdown materialize, workspace and state backfill

#### `job_runner/stdout_parser/*`

Files:

- [src/job_runner/stdout_parser/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/mod.rs)
- [src/job_runner/stdout_parser/labels.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/labels.rs)
- [src/job_runner/stdout_parser/state.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/state.rs)
- [src/job_runner/stdout_parser/stage_rules.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/stage_rules.rs)
- [src/job_runner/stdout_parser/artifact_rules.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/artifact_rules.rs)
- [src/job_runner/stdout_parser/failure.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/job_runner/stdout_parser/failure.rs)

Responsibilities:

- `mod.rs`
  Facade; calls artifact/stage rules per line
- `labels.rs`
  stdout contract label constants
- `state.rs`
  Artifact/provider diagnostics shared parsing state
- `stage_rules.rs`
  Stage/progress related rules
- `artifact_rules.rs`
  Artifact/metric related rules
- `failure.rs`
  Provider failure attribution and detail extraction

### 2.5 `ocr_provider/`

Directory:

- [src/ocr_provider](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider)

Responsibilities:

- Provider transport abstraction
- MinerU / Paddle clients, state mapping, error classification

Rules:

- This layer only handles provider communication and provider semantics
- It does not handle translation, rendering, or HTTP return structures

## 3. Current Main Call Chain

Main chain:

1. `POST /api/v1/jobs`
2. `routes/jobs/create.rs`
3. `services/jobs/facade.rs`
4. `services/jobs/creation.rs`
5. `services/job_snapshot_factory.rs`
6. `services/job_launcher.rs`
7. `job_runner/lifecycle.rs`
8. `services/job_command_factory.rs`
9. `job_runner/process_runner.rs`
10. Python worker

That is:

- Route only enters facade
- Facade only enters service
- Service only enters runner

## 4. Team Collaboration Red Lines

The following are hard constraints:

### Red Line 1

`routes/*` does not directly read:

- `Db`
- `job_paths`
- manifest/report JSON files
- Python worker command details

### Red Line 2

`job_runner/*` does not depend on:

- `axum`
- `HeaderMap`
- HTTP response model

### Red Line 3

`ocr_provider/*` does not do:

- Job view assembly
- Translation strategy
- Rendering strategy

### Red Line 4

If a change needs to touch:

- route
- service
- runner

Stop first and ask whether the boundary is wrong.

### Red Line 5

New file reading summary logic should preferably be placed in:

- `services/jobs/presentation/summary_loaders.rs`

Do not scatter into:

- route
- facade
- `views.rs`

## 5. Change Guide

### Scenario 1: Add a new jobs query endpoint

Change order:

1. `routes/jobs/*`
2. `services/jobs/facade.rs`
3. `services/jobs/query.rs` or `presentation/*`

Do not cross the facade directly from route to touch the underlying layer.

### Scenario 2: Add a new worker stage spec field

Change order:

1. `services/job_command_factory/stage_specs.rs`
2. Python `stage_specs` loader
3. Corresponding worker consumption logic

Do not add temporary parameters at the route/service layer.

### Scenario 3: Add a new provider

Change order:

1. `ocr_provider/<provider>/`
2. `job_runner/ocr_flow/*`
3. Python provider pipeline

Do not scatter provider logic to route or facade.

### Scenario 4: Adjust job detail return fields

Change order:

1. `services/jobs/presentation/views.rs`
2. If the field comes from disk summary, also modify `summary_loaders.rs`

## 6. Current Recommendations

If continuing to refactor, the priority recommendations are:

1. Add more explicit request/response DTO boundaries to `services/jobs`
2. Add stage execution contract documentation to `job_runner`
3. Define a unified trait / capability contract for `ocr_provider`

But the current version is already sufficient to support multi-person parallel development, provided the dependency directions and red lines above are followed.

Related supplementary documents:

- [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
- [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)
