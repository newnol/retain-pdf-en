# MinerU Provider Rust Refactoring Task

Goal:

- Build an independent OCR provider API layer within `rust_api`
- Implement the `MinerU` provider first
- Do not continue coupling MinerU API details to the current translation/rendering workflow
- Organize provider state, errors, and raw artifact information into stable Rust structures for debugging and future integration with other OCR APIs

## Scope

Only modify `rust_api` this time.

Allowed changes:

- `rust_api/src/**`
- Supplement `rust_api/api.md` / `rust_api/API_SPEC.md` if necessary

Do not modify:

- Python translation main chain
- Python rendering main chain
- `document_schema` main contract

## Directory Goal

Add an independent provider layer under `rust_api/src/`, suggested structure:

- `ocr_provider/mod.rs`
- `ocr_provider/types.rs`
- `ocr_provider/mineru/mod.rs`
- `ocr_provider/mineru/client.rs`
- `ocr_provider/mineru/models.rs`
- `ocr_provider/mineru/status.rs`
- `ocr_provider/mineru/errors.rs`

Can be fine-tuned based on implementation, but requirements:

- MinerU API code goes in a dedicated folder
- State mapping is independent
- Error mapping is independent
- Do not continue stacking MinerU HTTP calls in `routes/` or `job_runner.rs`

## Required Goals

### 1. Define OCR provider layer base types

At least these types are needed:

- `OcrProviderKind`
- `OcrTaskState`
- `OcrTaskHandle`
- `OcrTaskStatus`
- `OcrArtifactSet`
- `OcrProviderCapabilities`

Requirements:

- `OcrTaskState` is the internal unified state, not directly exposing MinerU raw state literals
- But `OcrTaskStatus` should retain the provider raw state field for debugging

Suggested unified states should at least include:

- `Queued`
- `WaitingUpload`
- `Running`
- `Converting`
- `Succeeded`
- `Failed`
- `Unknown`

### 2. Implement MinerU raw state -> internal state mapping

Must cover states already documented in the README:

- `waiting-file`
- `pending`
- `running`
- `converting`
- `done`
- `failed`

Requirements:

- Retain raw state strings
- Provide internal unified states simultaneously
- Provide human-readable stage/detail text generation entry points

### 3. Implement MinerU raw error -> internal error classification

Must at least handle:

- HTTP status errors
- Authorization errors
- Upload link request failure
- Upload failure
- Poll timeout
- Provider returned failed
- Result download failure
- Result unpacking failure
- Provider returned structure missing fields

Requirements:

- Error types should not just be strings
- Need to retain provider raw message / code / trace_id and other context
- Should be easy for the API layer to return clear errors directly

### 4. Extract MinerU API calls into an independent client

At least organize:

- Request upload link
- Upload file
- Query batch / task status
- Download results

Requirements:

- `job_runner.rs` no longer directly handles MinerU API semantics
- Route layer only handles receiving requests and returning responses
- Provider client handles HTTP calls and response parsing

### 5. Add state and raw information output for debugging

This is the key point, not just "making it work".

Must have at least:

- Provider raw state
- Provider task_id / batch_id
- trace_id
- Raw error code / error message
- Whether full_zip_url is available
- Status of upload link request stage, upload stage, and polling stage

If appropriate, can be attached to:

- Job extended artifacts / diagnostics fields
- Or new provider diagnostics structure

Requirements:

- Can be directly consumed by frontend and debugging interfaces later
- Avoid relying on reading long logs for debugging in the future

### 6. Add minimal tests

At least add:

- State mapping tests
- Error mapping tests
- Key response parsing tests

If time permits, also add:

- Provider state text tests

## Non-Goals

Do not do the following this time:

- Do not modify Python `services/mineru/`
- Do not modify `document_schema`
- Do not move the entire workflow to Rust
- Do not start integrating a second OCR provider

## Engineering Principles

- This is only the provider API layer, not the business workflow layer
- MinerU is a provider implementation, not the system main contract
- Other OCR APIs in the future should also be able to reuse this layer's abstraction
- You are not just writing "MinerU support", you are writing "the first skeleton for multiple OCR providers"

## Delivery Requirements

Upon completion, please provide:

1. Which files were added/modified
2. What stable types the provider layer currently has
3. Which MinerU states are covered
4. Which error classifications are covered
5. Which tests / `cargo check` were run
