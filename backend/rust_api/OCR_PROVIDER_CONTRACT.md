# OCR Provider Contract

This document answers one question:

**In `rust_api`, what does the OCR provider layer actually responsible for, and what it is not responsible for.**

Related documents:

- Overall architecture boundaries:
  [`RUST_API_ARCHITECTURE.md`](/home/wxyhgk/tmp/Code/backend/rust_api/RUST_API_ARCHITECTURE.md)
- Current running main chain:
  [`CURRENT_API_MAP.md`](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)
- Stage runtime contract:
  [`STAGE_EXECUTION_CONTRACT.md`](/home/wxyhgk/tmp/Code/backend/rust_api/STAGE_EXECUTION_CONTRACT.md)
- Paddle OCR API summary:
  [`src/ocr_provider/paddle/API_SUMMARY.md`](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle/API_SUMMARY.md)

## 1. Goal

The goal of the `ocr_provider` layer is not to run the complete OCR pipeline, but to provide:

- Provider identity identification
- Provider capability declaration
- Provider transport client
- Provider state mapping
- Provider error classification

In other words:

- "Who is this provider"
- "What does it support"
- "What do its returned states mean"
- "How to classify its failures"

## 2. Current Directory

- [src/ocr_provider/mod.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/mod.rs)
- [src/ocr_provider/types.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/types.rs)
- [src/ocr_provider/catalog.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/catalog.rs)
- [src/ocr_provider/mineru](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/mineru)
- [src/ocr_provider/paddle](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/paddle)

## 3. Responsibilities

### 3.1 `types.rs`

Responsible for provider shared data structures:

- `OcrProviderKind`
- `OcrProviderCapabilities`
- `OcrProviderDiagnostics`
- `OcrTaskStatus`
- `OcrProviderErrorInfo`

Rules:

- Shared contracts go here
- Provider-specific transport logic does not go here

### 3.2 `catalog.rs`

Responsible for provider metadata registration:

- `provider_definition`
- `provider_capabilities`
- `is_supported_provider`
- `ensure_provider_diagnostics`

Rules:

- When adding a new provider, register it here first
- The single aggregation point for `capabilities` must be here
- `diagnostics` initialization logic should not be scattered across the runner

### 3.3 `<provider>/client.rs`

Responsible for provider communication:

- Construct requests
- Call external APIs
- Parse responses

Not responsible for:

- Job lifecycle
- Route responses
- Translation/render decisions

### 3.4 `<provider>/status.rs`

Responsible for mapping provider raw states to unified states.

For example:

- provider raw state -> `OcrTaskState`
- provider raw message -> stage/detail

### 3.5 `<provider>/errors.rs`

Responsible for mapping provider errors to unified error classifications.

For example:

- invalid token
- expired token
- upload failed
- poll timeout

## 4. Dependency Direction

Allowed:

```text
job_runner -> ocr_provider
ocr_provider/catalog -> ocr_provider/<provider>
ocr_provider/<provider> -> ocr_provider/types
```

Prohibited:

```text
ocr_provider -> routes
ocr_provider -> services/jobs/presentation
ocr_provider -> translation/render logic
```

## 5. Current Runtime Contract

The `job_runner` side should now only consume provider metadata through these unified entry points:

- `parse_provider_kind`
- `require_supported_provider`
- `provider_definition`
- `provider_capabilities`
- `ensure_provider_diagnostics`

Specifically:

- `OcrProviderDiagnostics` initialization should not be hand-written in multiple modules
- It has been unified into `ensure_provider_diagnostics`

## 6. Minimum Steps to Add a New Provider

If a third provider is added in the future, the minimum steps should be:

1. Create `src/ocr_provider/<provider>/`
2. Implement:
   - `client.rs`
   - `status.rs`
   - `errors.rs`
3. Register in `catalog.rs`:
   - `kind`
   - `key`
   - `capabilities`
4. Expose the provider module in `mod.rs`
5. Connect transport dispatch in `job_runner/ocr_flow`

Things that should not be done:

- Do not add provider-specific checks in `routes`
- Do not add provider-specific checks in `services/jobs/facade`
- Do not add provider initialization logic in `process_runner`

## 6.1 Boundary with `job_runner/ocr_flow`

`ocr_provider` and `job_runner/ocr_flow` now have the following division of labor:

- `ocr_provider`
  Responsible for provider client, state mapping, error classification, capability declaration
- `job_runner/ocr_flow`
  Responsible for OCR subtask runtime orchestration, workspace, provider raw/result persistence, normalize handoff

Further:

- `ocr_flow/mod.rs`
  Is the sole orchestrator for the OCR sub-pipeline
- Provider client construction and local/remote transport branch selection
  Must also be centralized in `ocr_flow/mod.rs`
- Other sub-modules of `ocr_flow/*` cannot grow into a second orchestrator
- Understanding of provider raw tokens should be consolidated in dedicated helpers
  For example, Paddle Markdown artifact helper

## 7. Boundary Red Lines

### Red Line 1

The provider layer does not do complete job orchestration.

### Red Line 2

The provider layer does not decide translation strategy.

### Red Line 3

The provider layer does not return HTTP view models.

### Red Line 4

Provider capability declarations can only have one registration point, not scattered `match kind` everywhere.

The current registration point is:

- [catalog.rs](/home/wxyhgk/tmp/Code/backend/rust_api/src/ocr_provider/catalog.rs)
