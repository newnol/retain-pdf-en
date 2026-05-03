# Artifact Inventory and Downloads

First, understand the boundaries:

- `provider raw`
- `normalized`
- `published artifact`
- `download API`

This document mainly covers the latter two layers:

- `published artifact`
- `download API`

For the Rust-side responsibility description of the first two layers, see:

- [10-Rust-Side Artifact Boundary.md](/home/wxyhgk/tmp/Code/doc/rust_api/10-Rust-Side%20Artifact%20Boundary.md)

## 1. Why an Artifact Inventory is Needed

The task directory is an internal backend implementation detail that may continue to change in the future.

Therefore, the frontend or external callers should not depend on:

- What is definitely under `rendered/`
- What is definitely under `md/`
- Whether `ocr/unpacked/` will not change

The formal external source of truth is the stable artifact inventory in the database, exposed through the API.

## 2. Main Endpoints

Main task:

`GET /api/v1/jobs/{job_id}/artifacts-manifest`

OCR sub-task:

`GET /api/v1/ocr/jobs/{job_id}/artifacts-manifest`

## 3. What It Returns

It returns the artifact entries currently registered for this task; each entry has:

- `artifact_key`
- `artifact_group`
- `artifact_kind`
- `ready`
- `file_name`
- `content_type`
- `size_bytes`
- `relative_path`
- `checksum`
- `source_stage`
- `updated_at`
- `resource_path`
- `resource_url`

The fields the frontend should actually use are:

- `artifact_key`
- `ready`
- `resource_path` / `resource_url`

The `artifacts` in the details endpoint is suitable for quick button state checks; for complete machine-readable access, use `artifacts-manifest` as the source of truth.

## 4. Common artifact_key Values

Currently common ones include:

- `source_pdf`
  - If the request set `ocr.page_ranges` and used local upload, this points to the subset PDF generated within the task
- `translated_pdf`
- `typst_source`
- `typst_render_pdf`
- `markdown_raw`
- `markdown_images_dir`
- `markdown_bundle_zip`
- `normalized_document_json`
- `normalization_report_json`
- `layout_json`
- `translation_manifest_json`
- `provider_bundle_zip`
- `provider_result_json`
- `pipeline_summary`
- `events_jsonl`
  - Corresponds to the exported event stream persisted during the task runtime; suitable for debug downloads

The semantics should be distinguished:

- `provider_result_json` / `provider_bundle_zip`
  Belongs to `provider raw`
- `normalized_document_json` / `normalization_report_json`
  Belongs to `normalized`
- `markdown_raw` / `markdown_bundle_zip` / `translated_pdf`
  Belongs to `published artifact`

And `/pdf`, `/normalized-document`, `/artifacts/{artifact_key}` endpoints belong to `download API`

## 5. Recommended Reading Method

The frontend or scripts should no longer guess file locations based on directory structure; instead:

1. First request `artifacts-manifest`
2. Find the target `artifact_key`
3. Check `ready`
4. Use `resource_path` or `resource_url`

Among these, `markdown_bundle_zip` is the most suitable Markdown package for direct frontend download:

- Only contains `markdown/full.md`
- Only contains `markdown/images/**`
- Does not contain the original PDF
- Does not contain the translated PDF
- Does not contain the provider bundle
- Does not contain other debug JSON

If you want the extracted ZIP directory to include the job ID, you can add the following when doing direct downloads:

`?include_job_dir=true`

In this case, the root directory will change from the default `markdown/` to:

`{job_id}-markdown/`

If you want to download the original event stream of a task, you can also directly look up:

- `artifact_key = events_jsonl`

Its semantics are:

- A stable debug artifact
- Content comes from `events.jsonl` in the task log directory
- Suitable for troubleshooting, export, and archiving

But note:

- The frontend main page's "event stream" tab should still prioritize reading the `/events` endpoint
- The frontend should not treat `events_jsonl` as the primary display source of truth

## 6. Relationship with Legacy Endpoints

Legacy endpoints are still retained, such as:

- `/pdf`
- `/markdown`
- `/normalized-document`

But internally, they are already converging toward "first check the artifact inventory, then locate the actual file."

You can understand it as:

- Legacy endpoints are stable download entry points
- `artifacts-manifest` is the stable discovery entry point
- The `artifacts.pdf` / `artifacts.markdown` / `artifacts.bundle` in details are recommended page state fields
- Sibling fields like `pdf_url` / `markdown_url` / `bundle_url` are compatibility aliases; not recommended for new code to continue relying on

But note one boundary:

- The "legacy endpoints" here refer to stable resource entry points in the current API
- They do not refer to compatibility with old task directory layouts

If the task itself still comes from the `originPDF/jsonPDF/transPDF/typstPDF` old layout, or if artifacts are still stored with absolute paths, these download entry points will also directly reject the request; the task must be re-run.

## 7. Why This Approach Is More Stable

Because even if in the future the backend moves files from:

- `rendered/...`

To:

- `outputs/render/...`

As long as the backend updates the database registration logic, the external endpoints do not need to change.

This is exactly the purpose of this refactoring: to separate the "directory structure" from the public contract.
