# Integration Testing and Troubleshooting

## 1. Three Most Common Misjudgments

### 1.1 Backend Didn't Return, or Frontend Didn't Read Correctly

First, use curl to check the raw response directly; don't guess.

For example:

```bash
curl -s http://127.0.0.1:41000/api/v1/jobs/<job_id> \
  -H 'X-API-Key: your-key'
```

And:

```bash
curl -s 'http://127.0.0.1:41000/api/v1/jobs/<job_id>/events?limit=50&offset=0' \
  -H 'X-API-Key: your-key'
```

If the raw response has values but the page does not, first check the frontend's unpacking path.

### 1.2 "Backend Did Not Return runtime.stage_history"

This statement has two completely different situations:

First, the current task is a historical old task:

- `runtime = null`
- This means the backend had not yet persisted the runtime timeline at that time

Second, the current task is a new task but the backend truly did not write it:

- This is the anomaly that needs to be investigated

Do not conflate these two situations into one problem.

### 1.3 "Details or Download Directly Reports Old Task Not Supported"

This is a different type of problem; do not confuse it with `runtime = null`.

If the task still uses:

- `originPDF/jsonPDF/transPDF/typstPDF` old directory layout
- Legacy absolute-path artifact storage

Then the current backend will directly reject the details/download path and require a re-run.

This is not a transient failure, nor a frontend parsing issue; the current main pipeline has stopped supporting old task layouts.

### 1.4 "Event Stream is Empty"

First check:

1. Whether the endpoint returned `200`
2. Whether `data.items` is not empty
3. Whether the frontend incorrectly read the top-level `items`

## 2. Recommended Value Lookup Table for Task Details Page

- Current status: `data.status`
- Current stage: `data.runtime.current_stage`, fallback to `data.stage`
- Current stage description: `data.stage_detail`
- Process timeline: `data.runtime.stage_history`
- Current stage elapsed time: `data.runtime.active_stage_elapsed_ms`
- Total elapsed time: `data.runtime.total_elapsed_ms`
- Failure summary: `data.failure.summary`
- Failure category: `data.failure.category`
- Formula translation mode: `data.request_payload.translation.math_mode`
- Execution protocol: `data.invocation`
- Normalization summary: `data.normalization_summary`
- Glossary summary: `data.glossary_summary`
- Download buttons: `data.actions.*.enabled`

## 3. Recommended Value Lookup Table for Event Stream Tab

- Event array: `data.items`
- Pagination limit: `data.limit`
- Pagination offset: `data.offset`

Each item should prominently display:

- `seq`
- `ts`
- `level`
- `stage`
- `event`
- `message`

`payload` is recommended as an expandable section; do not display it all by default.

## 4. How to Check on Disk

The task root directory is typically at:

`DATA_ROOT/jobs/{job_id}/`

Common troubleshooting locations:

- `specs/`
- `logs/events.jsonl`
- `artifacts/pipeline_summary.json`
- `ocr/`
- `translated/`
- `rendered/`

If the task failed and you need more detailed diagnostics, key additional locations:

- `logs/failure-ai-diagnosis.request.json`
- `logs/failure-ai-diagnosis.response.json`

Notes:

- These two files will only appear when the main failure category is still `unknown` and the backend successfully triggered an AI supplementary diagnosis
- The absence of these two files does not mean failure classification is broken; many tasks can be classified directly through rules
- The stage spec in the `specs/` directory is the input protocol actually executed by the current worker; if it doesn't exist but you think it's a new task, first check whether the task is an old artifact or a half-finished directory

## 5. A Real Case

Task `20260404150516-75857c`:

- Details endpoint shows `runtime = null`
- So the "process timeline" cannot be displayed
- But the `/events` endpoint has data
- On disk there is also `logs/events.jsonl`

This indicates:

- This task belongs to the historical period before runtime timeline persistence went live
- The event stream is not broken
- The frontend timeline tab did not fail to render on its own

## 6. Documentation-Level Conclusion

If the frontend only needs stable display:

- Timeline: only look at `runtime.stage_history`
- Event stream: only look at `/events`
- Execution protocol: only look at `invocation`
- Normalization overview: only look at `normalization_summary`
- Do not cross-fill between them, do not mix them, and do not reverse-engineer the main timeline from the event stream

## 7. How to Read Failure Attribution Now

After a task fails, it is recommended to check in this order:

1. `data.failure.summary`
2. `data.failure.root_cause`
3. `data.failure.suggestion`
4. `data.failure.raw_diagnostic`
5. `data.failure.ai_diagnostic`

Judgment principles:

- `failure` is the primary source of truth
- `failure.raw_diagnostic` answers "what was the original exception"
- `failure.ai_diagnostic` answers "if the rules didn't identify it, what does the AI think the most likely cause is"
- `failure_diagnostic` is only a legacy field for backward compatibility; do not continue treating it as the primary source of truth

Current backend failure diagnosis pipeline:

1. Python top-level entry point first outputs structured failure JSON
2. Rust prioritizes parsing this structured failure and classifying it
3. If it is still `unknown`, it tries to append an AI supplementary diagnosis
4. The final result is persisted to task details and the event stream

## 8. Key Events Related to Failure Diagnostics in the Event Stream

Commonly checked events:

- `failure_classified`
- `failure_ai_diagnosed`
- `job_terminal`

Meanings:

- `failure_classified`: The backend has derived a structured failure classification
- `failure_ai_diagnosed`: Only appears for `unknown` failures; indicates AI has supplemented the diagnosis
- `job_terminal`: The task has entered its final terminal state; suitable for reading the final summary

## 9. OCR Page Range Integration Testing Key Points

If you want to restrict the OCR page range in `POST /api/v1/jobs`, the field location is:

```json
{
  "ocr": {
    "page_ranges": "1-5"
  }
}
```

Current backend behavior:

- `ocr.page_ranges` will be persisted into the task's `request_payload`
- When `provider=mineru`:
  - The `source.upload_id` upload PDF path will first extract a subset PDF, then upload that subset
  - The `source.source_url` remote URL path will also pass through
- An empty string means no page range restriction

If `source.upload_id + ocr.page_ranges` is already in effect, then the `source_pdf` in the task directory, subsequent translation pages, and final rendered PDF should all cover only this subset; you should not see a result where "only some pages from the entire PDF were translated."

If you suspect the page range did not take effect, check these three layers first rather than guessing the frontend:

1. Whether `request_payload.ocr.page_ranges` is non-empty in the request details
2. Whether `$.ocr.page_ranges` is non-empty in the database `jobs.request_json`
3. Then check the provider execution logs, rather than first suspecting the page form

## 11. `math_mode` Integration Testing Key Points

If you are troubleshooting "why formula blocks are slow" or "why there are no placeholders":

1. First check `request_payload.translation.math_mode`
2. `placeholder` means the current task is still using the legacy formula protection pipeline
3. `direct_typst` means the current task is using the experimental direct formula output branch

Judgment principles:

- Under `placeholder`, the appearance of placeholder validation, formula segmentation, and windowed formula is all expected
- Under `direct_typst`, placeholder stability should no longer be treated as the main issue; focus should be on model direct output quality, English residuals, and rendering compatibility

## 10. How to Troubleshoot When Old Tasks Are Rejected

If the details or download endpoint returns "old task not supported, re-run required," confirm in the following order:

1. Check whether the task directory still uses `originPDF/jsonPDF/transPDF/typstPDF`
2. Check whether the database artifact storage still uses absolute paths
3. Check whether the task predates the current spec-only and new artifact layout transition

Conclusion:

- These tasks will not be automatically migrated
- Writing temporary compatibility code to support them is not recommended
- The correct approach is to re-run the task
