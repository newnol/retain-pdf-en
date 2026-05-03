# Collaborative Development Conventions

This document is not an API specification; it is a boundary convention for backend collaborative development.

There is only one goal:

- When multiple people develop `rust_api` simultaneously, each person works on their own part without stepping on each other's responsibilities and without further scrambling the structure

## 1. Module Responsibilities

Current default collaboration boundaries:

- `routes/*`
  - Only does HTTP adapter work
  - Responsible for request parsing, post-authentication entry, response wrapping
  - Not responsible for business aggregation, not directly assembling job commands
- `services/jobs/*`
  - Responsible for business logic within the job domain
  - Includes query, presentation, creation, control
  - This is where most "business changes" should land first
- `services/job_snapshot_factory.rs`
  - Responsible for job snapshot / command assembly
- `services/job_launcher.rs`
  - Responsible for job persistence and execution launch
- `services/runtime_gateway.rs`
  - Responsible for encapsulating service access to runtime
- `job_runner/*`
  - Responsible for runtime execution
  - Includes queuing, cancellation, process launching, OCR sub-task bridging, render/translate execution chain
- `models/*`
  - Only holds DTOs, input/output models, persistence models
  - No new business orchestration or file system reading logic

## 2. Dependency Rules

Default dependency direction:

- `routes -> services -> job_snapshot_factory / job_launcher / runtime_gateway / db`
- `job_runner -> db / config / runtime state`
- `models` must not reverse-depend on `routes` or `services`

Default prohibitions:

- `routes` directly writing complex business logic
- `models/view.rs` regrowing file reading, failure diagnostic aggregation, etc.
- Pure assembly helpers continuing to directly consume `AppState`

## 3. AppState Usage Conventions

`AppState` is allowed in:

- Route entry points
- Lifecycle entry points
- Runtime modules that truly need to coordinate cancellation, execution slots, and process launching

Places that should prefer narrow dependencies instead:

- Command building
- Snapshot assembly
- Upload validation and storage
- Read-only view aggregation
- Helpers that only do database/event persistence

If a function only needs the following resources, do not pass `AppState`:

- `&Db`
- `&AppConfig`
- `&Path`
- `&RwLock<HashSet<String>>`
- `&Arc<Semaphore>`

## 4. New Requirement Landing Rules

When collaborating, first determine which category a requirement falls into, then place the code:

- Add query fields, detail display, artifact views
  - Prioritize modifying `services/jobs/presentation` or `services/jobs/query`
- Add creation parameters, submission flows, bundle logic
  - Prioritize modifying `services/jobs/creation`
- Add execution stages, sub-task bridging, cancellation semantics
  - Prioritize modifying `job_runner/*`
- Add common response fields or input fields
  - Modify `models/*`
- Only HTTP input/output parameter changes
  - Modify `routes/*`, but try not to leave business logic in routes

## 5. Common Anti-Patterns

The following are the easiest ways to corrupt the structure during collaboration:

- Reading DB, assembling views, assembling commands, or making file system judgments directly in routes
- Writing HTTP semantics directly in `services`
  - e.g., directly handling Headers, Multipart, Responses
- Adding new `AppState` pass-through helpers in `job_runner` sub-modules
- Adding "conveniently read disk files" aggregation logic in `models`
- Packing multiple responsibilities back into a single black-box function for convenience

## 6. Minimum Pre-Commit Checks

If modifying `rust_api`, by default at least do the relevant items from the following:

- `cargo check --quiet`
- If changing creation / job_snapshot_factory / job_launcher: add corresponding service tests
- If changing process runner / lifecycle: add corresponding runner tests
- If changing query / presentation: add corresponding query or presentation tests

If a change causes a lower-level helper to start directly depending on `AppState` again, it should be explained during review why this was necessary.
