# Rust-Side Artifact Boundary

This document answers only one question:

How does the Rust API currently view the four-layer boundary of `provider raw / normalized / published artifact / download API`.

## 1. Four-Layer Boundary

```text
provider raw
  -> normalized
  -> published artifact
  -> download API
```

The responsibilities of the four layers must be stably separated.

## 2. Provider Raw

This layer is the provider's own raw result or raw directory snapshot.

The Rust side only treats it as a "can be registered, can be downloaded, can be used for troubleshooting" provider artifact; it does not treat it as a unified document contract.

Current typical keys:

- `provider_result_json`
- `provider_bundle_zip`
- `provider_raw_dir`
- `layout_json`

This layer is allowed to:

- Preserve the provider's original structure
- Serve as a basis for troubleshooting and traceability
- Serve as input source before normalization

This layer is NOT allowed to:

- Have the download API commit to the semantics of provider private fields
- Have the artifact registry understand provider fields like `layoutParsingResults`
- Have downstream translation/rendering directly stably depend on provider raw structure

## 3. Normalized

This layer is the formal handoff from the OCR stage to downstream.

Current formal files:

- `normalized_document_json`
- `normalization_report_json`

The Rust side should treat it as:

- The stable structural boundary from OCR to translation/rendering
- A formal document resource that can be externally downloaded

The Rust side should NOT conflate provider raw and normalized into one concept.

Specifically:

- The `normalized-document` download endpoint only corresponds to `normalized_document_json`
- The `normalization-report` download endpoint only corresponds to `normalization_report_json`

## 4. Published Artifact

This layer is the Rust API's artifact registry / published artifact scope.

Its responsibilities are:

- Assign stable `artifact_key` values to files in the task directory
- Generate a unified manifest
- Provide unified resource paths
- Handle export composites like bundles

It is NOT responsible for:

- Understanding provider raw internal fields
- Defining normalization semantics
- Inferring document semantics such as body text, structure, formulas, etc.

In other words:

- `provider raw` is the "raw input snapshot"
- `normalized` is the "unified document contract"
- `published artifact` is "Rust's registration layer when publishing these files externally"

These three are not the same layer.

## 5. Download API

The download API is the outermost HTTP exposure layer.

It only commits to two types of things:

- Stable resource downloads
- Unified artifact download by `artifact_key`

It does NOT commit to:

- Provider private field structures
- Job directory physical layout
- Provider raw internal JSON semantics

Therefore:

- `/normalized-document` exposes the normalized boundary
- `/normalization-report` exposes the normalized auxiliary artifact
- `/artifacts/{artifact_key}` exposes the published artifact boundary
- Provider raw is only exposed as "raw files" when explicitly downloading the corresponding artifact key; it is NOT a "unified semantic interface"

## 6. Current Rust-Side Landing Points

The files most directly related to these four layers on the Rust side are:

- `backend/rust_api/src/storage_paths.rs`
- `backend/rust_api/src/services/artifacts/mod.rs`
- `backend/rust_api/src/routes/jobs/download.rs`

The boundary conventions for these three are:

- `storage_paths.rs`
  Responsible for path conventions, artifact keys, file parsing, and published artifact discovery
- `services/artifacts/*`
  Responsible for artifact registry, bundle construction, resource path mapping
- `routes/jobs/download.rs`
  Responsible for HTTP download endpoint adaptation

None of them should start understanding provider raw internal fields.

## 7. One-Sentence Judgment Rule

If a change requires the Rust download layer to understand field names from provider raw JSON, it has usually crossed the boundary.

The correct direction is typically:

- Provider changes: modify adapter / normalize
- Published artifact changes: modify `storage_paths.rs` / `services/artifacts/*`
- HTTP exposure changes: modify download route / facade
