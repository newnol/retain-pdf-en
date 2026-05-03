# 06 Paddle Markdown to Job Artifact Mapping and Boundaries

This document answers only one thing:

- What are the boundaries of Paddle provider output, `normalized_document`, job artifact export, and download endpoint respectively

Core conclusions first:

1. `provider raw` is OCR provider private output, only used for traceability, diagnostics, and adapter input; it is NOT the downstream main contract.
2. `normalized_document` is the formal handoff from the OCR stage to translation/rendering; the main pipeline should stably depend on it.
3. `job artifact` is the job artifact registration and export layer, responsible for exposing files as unified artifact keys; it does NOT redefine provider semantics.
4. The download endpoint is the HTTP exposure layer, only committing to "download by artifact or by stable resource"; it does NOT commit to downstream understanding of provider raw structure.

## One Diagram Showing Boundaries

```text
Paddle API JSONL / result.json
  -> provider raw boundary
  -> document_schema adapter
  -> ocr/normalized/document.v1.json
  -> normalized_document boundary
  -> translation / rendering
  -> job artifacts registry / virtual bundle
  -> artifact export boundary
  -> /api/v1/jobs/* download routes
  -> download API boundary
```

## 1. Provider Raw Boundary

The raw result file for Paddle provider in the current provider-backed flow is:

- `ocr/result.json`

Source code:

- `backend/scripts/services/ocr_provider/provider_pipeline.py`
  `run_paddle_to_job_dir()` saves the aggregated result from `download_jsonl_result()` to `job_dirs.ocr_dir / "result.json"`
- `backend/scripts/services/ocr_provider/paddle_api.py`
  `download_jsonl_result()` aggregates JSONL into:
  - `layoutParsingResults`
  - `dataInfo`
  - `_meta`

This layer's responsibilities are only:

- Preserve Paddle's original structure
- Provide input for the `document_schema` adapter
- Provide a basis for troubleshooting and provider reconciliation

Responsibilities this layer should NOT carry:

- Should not serve directly as translation input
- Should not serve directly as rendering input
- Should not require the Rust API or frontend to understand `layoutParsingResults` field details
- Should not be wrapped by the download endpoint into "unified document semantics"

That is:

- `result.json` is the provider raw snapshot
- It can change
- As long as the adapter can still stably map it to `document.v1`, downstream should not be forced to change with it

## 2. Normalized Document Boundary

The formal output after Paddle raw enters the unified contract is:

- `ocr/normalized/document.v1.json`
- `ocr/normalized/document.v1.report.json`

Source code:

- `backend/scripts/services/ocr_provider/provider_pipeline.py`
  `_save_normalized_document_for_paddle()`
- `backend/scripts/services/document_schema/README.md`

This layer is the current stable handoff point from OCR to translation/rendering.

Responsibilities:

- Isolate Paddle private fields within the adapter
- Output unified `normalized_document_v1`
- Allow translation/rendering to only work with stable structures

The main pipeline should depend on:

- `document.v1.json`

The main pipeline should NOT depend on:

- `result.json`
- `layoutParsingResults[*].prunedResult.*`
- Paddle's `markdown.images`
- Paddle's `group_id/global_group_id`

The positioning of `document.v1.report.json` should also be clear:

- It is the normalization report and validation summary
- Used for troubleshooting, default value analysis, and compatibility checks
- It is NOT the main input for translation or rendering

## 3. Where Paddle Markdown Fits in the Boundary

Markdown in the current download layer is NOT a formal contract field from Paddle raw API; it is an exportable artifact within the job directory.

Rust-side Markdown resolution location:

- `backend/rust_api/src/storage_paths.rs`
  - `resolve_markdown_path()`
  - `resolve_markdown_images_dir()`

Current resolution order:

1. Prefer reading `job_root/md/full.md`
2. Prefer reading `job_root/md/images/`
3. Only for backward-compatible old layouts, fall back to `provider_raw_dir/full.md` and `provider_raw_dir/images/`

This means:

- `md/full.md` and `md/images/` belong to the job output structure
- They are "externally downloadable Markdown artifacts"
- They are NOT the Paddle raw provider contract itself

Therefore, do not confuse:

- `markdown.text` / `markdown.images` in Paddle raw
- `md/full.md` / `md/images/` in the job

The former belongs to provider raw trace.
The latter belongs to job artifact/export scope.

The current main pipeline has consolidated around this boundary:

- Paddle provider pipeline explicitly performs a markdown materialization step
- Publishes `layoutParsingResults[*].markdown.text/images` to `job_root/md/full.md` and `job_root/md/images/`
- Rust download layer only reads this published artifact set, no longer reverse-engineers from `provider_raw_dir`

There is a very important implementation constraint here:

- The relative paths for images in Markdown cannot be generated with a fixed pattern we invent ourselves
- They must follow Paddle's `markdown.images` keys
- We currently only allow one layer of stable publish wrapping: adding a `page-N/` scope prefix per page to prevent same-named images from different pages from overwriting each other

That is, if the original Paddle Markdown contains:

```html
<img src="imgs/img_in_image_box_320_138_932_438.jpg" ... />
```

Then the published Markdown should become:

```html
<img src="page-6/imgs/img_in_image_box_320_138_932_438.jpg" ... />
```

Where:

- `imgs/img_in_image_box_320_138_932_438.jpg` this relative path comes from the provider's original response
- `page-6/` is the page scope we added for multi-page publishing

It cannot be incorrectly simplified to:

- Fixed `imgs/...`
- Fixed `assets/...`
- Fixed some image naming template
- Fixed some Markdown image syntax

Because the body text returned by Paddle may be either Markdown `![](...)` or HTML `<img src="...">`, and the relative path fragments must completely follow the provider's return values.

## 4. Job Artifact Export Boundary

The responsibility of job artifacts is to unify the mapping of files and virtual artifacts in the job directory to artifact keys.

Key code:

- `backend/rust_api/src/storage_paths.rs`
- `backend/rust_api/src/services/artifacts.rs`

The most critical thing here is not "where files are placed" but "what artifact key they are exposed as."

### Artifact Keys Directly Related to Paddle/Normalize/Markdown

| Artifact Key | Meaning | Boundary Ownership |
| --- | --- | --- |
| `provider_result_json` | Provider raw result snapshot | provider raw |
| `provider_raw_dir` | Provider raw directory | provider raw |
| `layout_json` | Legacy/compat layout result entry | provider raw or compat layer |
| `normalized_document_json` | Unified document contract | normalized_document |
| `normalization_report_json` | Normalization report | normalized_document auxiliary |
| `markdown_raw` | Job-exported Markdown file | artifact export |
| `markdown_images_dir` | Job-exported Markdown images directory | artifact export |
| `markdown_bundle_zip` | Markdown bundle dynamically packaged by API | artifact export |

### Boundary Rules Here

`services/artifacts.rs` is only responsible for:

- Finding artifacts from the registry or fallback
- Generating stable resource paths for artifacts
- Building zip bundles as needed

It is NOT responsible for:

- Interpreting Paddle raw JSON
- Defining `document.v1` semantics
- Deciding whether a block is body text

That is, the artifact layer handles:

- Whether a file exists
- Which group a file belongs to
- Which artifact key to expose it with
- Whether direct download is allowed

The artifact layer should not reverse into a provider semantics layer.

## 5. Download Endpoint Boundary

The download endpoint is the outermost HTTP exposure and should not leak internal path structures as new business contracts.

Key code:

- `backend/rust_api/src/services/jobs/facade/query/downloads.rs`
- `backend/rust_api/src/services/artifacts.rs`

### Stable Resource Endpoints

These endpoints expose "stable resource types," not provider private fields:

| Endpoint | Corresponding Resource | Notes |
| --- | --- | --- |
| `/api/v1/jobs/{job_id}/normalized-document` | `normalized_document_json` | Formal handoff from OCR to downstream |
| `/api/v1/jobs/{job_id}/normalization-report` | `normalization_report_json` | Normalization validation/summary |
| `/api/v1/jobs/{job_id}/markdown` | Read view of `markdown_raw` | Can return JSON wrapper or raw markdown |
| `/api/v1/jobs/{job_id}/markdown/images/{path}` | Files under `markdown_images_dir` | Direct image link |
| `/api/v1/jobs/{job_id}/artifacts/{artifact_key}` | Artifact registry entry | Generic artifact download |

### Bundle Endpoint

`bundle_response()` dynamically packages a zip based on the job's current artifacts.

Current bundle contents come from:

- `translated_pdf`
- `markdown/full.md`
- `markdown/images/*`

This means the bundle is an "export layer composite," not a new schema.

## 6. Why These Four Layers Must Be Decoupled

If the four layers are not separated, there will be repeated refactoring later.

Typical incorrect coupling patterns:

1. Having the translation pipeline directly read Paddle raw's `layoutParsingResults`
2. Having the artifact export logic understand `block_label/group_id`
3. Having the download endpoint directly commit to the provider's raw field structure
4. Treating `markdown.text` as the downstream unified contract instead of `document.v1` as the main input

The correct approach is:

1. Provider raw is responsible for "fidelity"
2. Normalized document is responsible for "unification"
3. Artifact export is responsible for "registration and export"
4. Download API is responsible for "exposing as stable resources"

This way, changes in each layer only affect that layer:

- Paddle API changed: prioritize modifying the provider adapter
- `document.v1` enhanced: modify normalize and downstream consumers
- Download method changed: modify artifact/export and route/facade

Rather than changing the entire chain at once.

## 7. Judgment Rules for Actual Development

When encountering a field or file, first ask which layer it belongs to:

### Belongs to provider raw

Typical examples:

- `result.json`
- `layoutParsingResults`
- `dataInfo`
- `markdown.images`
- `group_id`

Handling rules:

- Can be retained
- Can be used for troubleshooting
- Cannot serve as a formal main pipeline contract

One additional judgment rule for Markdown image paths:

- `markdown.images` keys are part of provider raw semantics
- The published artifact layer cannot rename its internal relative path structure
- What is allowed is only "page scope isolation," e.g., `page-6/` prefix
- What is NOT allowed is rewriting the provider's returned `imgs/...` to a custom fixed directory name internal to the repository

### Belongs to normalized_document

Typical examples:

- `document.v1.json`
- `document.v1.report.json`

Handling rules:

- This is the stable handoff layer from OCR to translation/rendering
- Semantic enhancement should be prioritized on the adapter/schema side

### Belongs to artifact export

Typical examples:

- `markdown_raw`
- `markdown_images_dir`
- `markdown_bundle_zip`
- `provider_result_json`
- `normalized_document_json`

Handling rules:

- Focus on artifact key, ready status, relative path, group, content type
- Do not invent new provider semantics here

### Belongs to download API

Typical examples:

- `/normalized-document`
- `/normalization-report`
- `/markdown`
- `/artifacts/{artifact_key}`

Handling rules:

- Focus on resource exposure format, authentication, response headers, streaming
- Do not interpret the business meaning of Paddle raw here

## 8. Documentation Main Convention

When discussing this area in the future, use the following unified terminology:

- `provider raw`: Paddle original output and original directory
- `normalized_document`: Unified document contract, formal input for translation/rendering
- `artifact export`: Job artifact registration, packaging, and export
- `download API`: External HTTP resource exposure

Do NOT continue mixing these terms:

- "Markdown is Paddle output"
- "Artifact is schema"
- "Download endpoint equals provider contract"
- "If it can be downloaded it can serve as main pipeline input"

These statements will re-couple the layers back together.
