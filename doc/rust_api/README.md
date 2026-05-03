# Rust API Documentation

These documents are for frontend integration testing, backend maintenance, and troubleshooting.

If you just want to quickly know "which field to read," follow this order:

1. [01-Response Wrapper.md](/home/wxyhgk/tmp/Code/doc/rust_api/01-Response%20Wrapper.md)
2. [02-Job Details and Timeline.md](/home/wxyhgk/tmp/Code/doc/rust_api/02-Job%20Details%20and%20Timeline.md)
3. [03-Event Stream API.md](/home/wxyhgk/tmp/Code/doc/rust_api/03-Event%20Stream%20API.md)
4. [04-Job Lifecycle.md](/home/wxyhgk/tmp/Code/doc/rust_api/04-Job%20Lifecycle.md)
5. [05-Integration Debugging.md](/home/wxyhgk/tmp/Code/doc/rust_api/05-Integration%20Debugging.md)
6. [06-Artifact Inventory and Downloads.md](/home/wxyhgk/tmp/Code/doc/rust_api/06-Artifact%20Inventory%20and%20Downloads.md)
7. [07-Job List API.md](/home/wxyhgk/tmp/Code/doc/rust_api/07-Job%20List%20API.md)
8. [08-Provider Validation API.md](/home/wxyhgk/tmp/Code/doc/rust_api/08-Provider%20Validation%20API.md)
9. [09-Collaborative Development Conventions.md](/home/wxyhgk/tmp/Code/doc/rust_api/09-Collaborative%20Development%20Conventions.md)
10. [10-Rust-Side Artifact Boundary.md](/home/wxyhgk/tmp/Code/doc/rust_api/10-Rust-Side%20Artifact%20Boundary.md)

Current key conclusions:

- All successful responses use the `code/message/data` three-layer wrapper
- The task details page should use `GET /api/v1/jobs/{job_id}` as the main endpoint
- The "process timeline" must read `runtime.stage_history`
- The "event stream" tab reads `GET /api/v1/jobs/{job_id}/events`
- File downloads and artifact discovery should prioritize `GET /api/v1/jobs/{job_id}/artifacts-manifest`
- Rust-side artifact boundary has four layers: `provider raw -> normalized -> published artifact -> download API`
- The `translation.math_mode` parameter is available, defaulting to `direct_typst`
- The Python worker for new tasks has been unified to `--spec` driven; `invocation` in details/list shows `input_protocol=stage_spec`
- `normalization_summary` now reads a simplified view of `document.v1.report.json`; default consolidation fields have been unified to `document_defaults/page_defaults/block_defaults`
- The event stream endpoint returns `items` in `data.items`, not at the top level
- Historical old tasks may show `runtime = null`; this is missing historical data, not a current endpoint failure
- Old tasks that still use `originPDF/jsonPDF/transPDF/typstPDF` directory layout, or have absolute-path artifact storage in the database, will be directly rejected by details and download endpoints; they must be re-run

There are also two code boundary conventions:

- `routes/*` only does HTTP adapter work; not responsible for aggregating views or directly assembling job commands
- Jobs-related dependency assembly has been moved up to [`backend/rust_api/src/app/jobs.rs`](/home/wxyhgk/tmp/Code/backend/rust_api/src/app/jobs.rs); routes no longer directly know how `job_runner` is launched
- `services/jobs/creation`, `services/job_snapshot_factory`, and `services/job_launcher` have now been split into "pure assembly" and "execution launch" layers; pure assembly logic by default only depends on `Db`, `AppConfig`, and explicit parameters, and should not continue passing through the entire `AppState`
- When collaborating, new code by default follows the landing and dependency rules in [09-Collaborative Development Conventions.md](/home/wxyhgk/tmp/Code/doc/rust_api/09-Collaborative%20Development%20Conventions.md)

`AppState` is currently allowed in the following main locations:

- Route entry points
- Job lifecycle / process runner layers that truly need runtime resource coordination

`AppState` should NOT be further passed down to:

- Command building
- Job snapshot assembly
- Read-only view aggregation
- Upload validation and pure input assembly
