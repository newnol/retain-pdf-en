# Rust API Docs

This index only answers one question:

**When reading `rust_api` documentation, which document should I read first?**

## Recommended Reading Order

1. How the current system actually runs:
   [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
2. Start with the directory map to know where to make changes:
   [`RUST_API_DIRECTORY_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_DIRECTORY_MAP.md)
3. Team collaboration boundaries and layering rules:
   [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
4. Rust-side artifact four-layer boundary:
   [`doc/rust_api/10-Rust-Side Artifact Boundary.md`](/home/wxyhgk/tmp/Code/doc/rust_api/10-Rust-Side%20Artifact%20Boundary.md)
5. External HTTP API protocol:
   [`API_SPEC.md`](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)
6. Rust and Python stage spec contract:
   [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
7. Stage events and failure protocol:
   [`../doc/rust_api/11-Stage Events and Failure Protocol.md`](/home/wxyhgk/tmp/Code/doc/rust_api/11-Stage%20Events%20and%20Failure%20Protocol.md)
8. OCR provider boundary:
   [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)
9. Paddle OCR async API summary:
   [`src/ocr_provider/paddle/API_SUMMARY.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/API_SUMMARY.md)
10. Paddle Markdown / artifact boundary:
   [`../doc/paddle_ocr_api/06_job_artifact_boundary.md`](/home/wxyhgk/tmp/Code/doc/paddle_ocr_api/06_job_artifact_boundary.md)

## What Problem Each Document Solves

- [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
  Only looks at the current active runtime path, focusing on "after a request comes in, how exactly do Rust and Python connect".
- [`RUST_API_DIRECTORY_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_DIRECTORY_MAP.md)
  Only looks at current directory responsibilities, focusing on "which directory should I enter first to modify code".
- [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
  Only looks at current team collaboration boundaries, focusing on "where is the right place to make changes, which layers should not be bypassed".
-  [`doc/rust_api/10-Rust-Side Artifact Boundary.md`](/home/wxyhgk/tmp/Code/doc/rust_api/10-Rust-Side%20Artifact%20Boundary.md)
  Only looks at the Rust-side artifact boundary, focusing on "what each of the four layers (provider raw / normalized / published artifact / download API) is responsible for".
- [`API_SPEC.md`](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)
  Only looks at external HTTP behavior, focusing on "how to call the API, what it returns, which fields are formal contracts".
- [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
  Only looks at the stage worker spec protocol, focusing on "how Rust passes execution input to Python".
-  [`../doc/rust_api/11-Stage Events and Failure Protocol.md`](/home/wxyhgk/tmp/Code/doc/rust_api/11-Stage%20Events%20and%20Failure%20Protocol.md)
  Only looks at the state/failure consolidation direction, focusing on "what formal fields should frontend/backend and Rust/Python align around".
- [`OCR_PROVIDER_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/OCR_PROVIDER_CONTRACT.md)
  Only looks at the provider adapter boundary, focusing on "at which layer MinerU / Paddle are dispatched and consolidated".
- [`src/ocr_provider/paddle/API_SUMMARY.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/API_SUMMARY.md)
  Only looks at the Paddle OCR async interface protocol, focusing on "how submit / poll / result download actually work".
- [`../doc/paddle_ocr_api/06_job_artifact_boundary.md`](/home/wxyhgk/tmp/Code/doc/paddle_ocr_api/06_job_artifact_boundary.md)
  Only looks at the Markdown publishing boundary, focusing on "why provider raw cannot be directly used as job markdown artifact".

## Recommended Learning Path

- To quickly understand the system:
  `README -> RUST_API_DIRECTORY_MAP -> CURRENT_API_MAP -> RUST_API_ARCHITECTURE`
- To modify backend code:
  `RUST_API_DIRECTORY_MAP -> RUST_API_ARCHITECTURE -> 10-Rust-Side Artifact Boundary -> CURRENT_API_MAP -> corresponding source code`
- To integrate with frontend or third parties:
  `API_SPEC -> CURRENT_API_MAP`

## Architecture Gate

Backend changes should default to running at least these checks:

- `python3 backend/rust_api/scripts/check_architecture.py`
- `cargo build --manifest-path backend/rust_api/Cargo.toml`
- `cargo test --manifest-path backend/rust_api/Cargo.toml --lib job_runner::process_runner::tests::execute_process_job_injects_provider_and_translation_envs`
- `cargo test --manifest-path backend/rust_api/Cargo.toml --lib routes::jobs::query::tests::job_detail_and_events_routes_redact_secrets`

The first check catches the most easily regressed architecture issues:

- `AppState` flowing back into `services/job_runner/ocr_provider`
- `routes` directly depending on `job_runner`
- `routes/jobs/*` re-defining local `route_deps(...)`
- `ProcessRuntimeDeps::new(...)` being casually assembled outside the `app` boundary layer
- `JobPersistDeps` leaking out from the leaf helper boundary again
- `runtime_deps` struct being scattered back into multiple runner files
- `state.rs` mixing stale running job recovery back into bootstrap
- `lifecycle.rs` regressing into a single large function, losing the consolidated helper boundary
- artifact/download boundary layer starting to understand provider raw internal fields
- published markdown artifact re-deriving from `provider_raw_dir/full.md|images`
