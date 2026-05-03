# Job Lifecycle

## 1. Currently Supported Workflows

The Rust API currently supports 4 types of workflows:

1. `book`
   The current complete main pipeline identifier: OCR -> Normalize -> Translate -> Render
2. `ocr`
   Only runs OCR/Normalize, producing `document.v1.json`
3. `translate`
   OCR -> Normalize -> Translate, stops at translation output, does not enter rendering
4. `render`
   Reuses existing job artifacts, only re-runs rendering

## 2. Main Pipelines

### 2.1 `book`

Here `book` is the workflow identifier in the current API protocol, meaning "complete main pipeline".
It is a stable enum; it does not require the frontend or local entry point to continue exposing the provider name to users.

1. Upload PDF
2. Create main task
3. Main task internally creates an OCR sub-task
4. OCR provider upload, poll, download results
5. Normalize to `document.v1`
6. Translate
7. Render
8. Output PDF / ZIP / other artifacts

### 2.2 `translate`

1. Upload PDF
2. Create translation task
3. Translation task internally creates an OCR sub-task
4. OCR provider upload, poll, download results
5. Normalize to `document.v1`
6. Translate
7. Output translation payload, `translation-manifest.json`, diagnostic information

Additional notes:

- When `translation.math_mode=placeholder`, the translation stage uses the legacy formula protection pipeline
- When `translation.math_mode=direct_typst`, the translation stage uses the experimental "direct formula output" branch
- Neither changes the task endpoint or rendering entry; they only affect the formula processing strategy in the translation stage

### 2.3 `render`

1. Create render task
2. The request points to an existing job via `source.artifact_job_id`
3. Backend reuses `source_pdf` and `translations_dir` from that job
4. Only executes rendering
5. Outputs new PDF / Typst / render artifacts

## 3. Why OCR Sub-Tasks Exist

Both `book` and `translate` main tasks do not do everything at once; instead, they create an OCR sub-task, typically named:

`{job_id}-ocr`

This has two benefits:

- OCR transport and the main translation/render pipeline can be observed separately
- OCR provider diagnostics can be attached independently in the details

## 4. Common Stage Names

Stage names change as the pipeline progresses; common ones include:

- `queued`
- `ocr_submitting`
- `ocr_upload`
- `mineru_upload`
- `mineru_processing`
- `translation_prepare`
- `normalizing`
- `translating`
- `domain_inference`
- `page_policies`
- `rendering`
- `finished`
- `failed`

Additional notes:

- `translate` typically stops at `translating -> finished`
- `render` typically enters `rendering` directly
- `ocr` does not enter `translating` or `rendering`

Not every task goes through exactly the same stages, but the overall logic is consistent.

## 5. How to Differentiate on the Request Side

Two things are most critical:

1. `workflow`
   Determines whether this is a complete task, OCR-only, Translate-only, or Render-only
2. `source`
   - `upload_id`: Used for `book` / `translate`
   - `artifact_job_id`: Used for `render`

Current conventions:

- `workflow=translate` still creates an OCR sub-task but does not enter rendering
- `workflow=render` does not re-run OCR or translation; it reuses existing job artifacts
- `workflow=ocr` uses the dedicated `/api/v1/ocr/jobs` entry point, not mixed into `/api/v1/jobs`
- The JSON request body for `/api/v1/jobs` uses `source / ocr / translation / render / runtime` grouped structure as the formal contract
- Legacy flat fields are only preserved in a few multipart helper endpoints, no longer promoted as the main JSON contract

## 6. How Frontend Should Understand Stages

It is recommended to distinguish three layers:

- `status`: Whether the task has ended
- `stage`: Which stage the task is currently in
- `stage_detail`: Human-readable description of the current stage

For example:

- `status = running`
- `stage = translating`
- `stage_detail = Completed batch 18/55 translation`

This means:

- The task has not ended
- The current stage is translation
- Current batch progress is at 18/55

## 7. When Download Buttons Become Clickable

The frontend should not assemble its own rules; instead, it should directly check the details endpoint for:

- `actions.*.enabled`
- `artifacts.*.ready`

For example:

- PDF download button: check `actions.download_pdf.enabled`
- ZIP download button: check `actions.download_bundle.enabled`

Additional notes:

- After a `translate` task succeeds, typically only the translation directory and bundle are ready; PDF may not be ready
- After a `render` task succeeds, PDF should be ready, but there may not be OCR-related downloadables

## 8. What to Look at When a Task Fails

For failed tasks, prioritize looking at:

- `failure.category`
- `failure.summary`
- `failure.root_cause`
- `failure.retryable`
- `failure.suggestion`

If that is not enough, then check:

- `runtime.final_failure_category`
- `runtime.final_failure_summary`
- `log_tail`
- `/events`

## 9. Division of Responsibilities Between Timeline and Event Stream

This division is very important:

- `runtime.stage_history` answers "how long did each stage take in the full process"
- `/events` answers "what specific events occurred during the process"
- `failure` answers "what category this failure was classified as, whether it is retryable, and what action is suggested"
- `failure_diagnostic` is only a simplified view for backward-compatible frontends

The former is suitable for overview; the latter is suitable for troubleshooting.
