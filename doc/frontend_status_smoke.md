# Frontend Status Smoke Check

The goal of this check is not to "take a screenshot of the frontend page", but to automatically verify:

- Whether upload succeeds
- Whether `/api/v1/jobs` submission succeeds
- Whether the status labels displayed by the frontend during task detail polling progress as expected

Current script location:

- `frontend/scripts/frontend-status-smoke.mjs`

Current npm entry point:

```bash
cd frontend
npm run smoke:status -- --file ../data/temPDF/test1.pdf
```

Repository-level fixed entry point:

```bash
./.github/scripts/smoke_frontend_status.sh
```

By default, the latest results are written to:

```text
doc/reports/frontend-status-smoke-latest.json
```

## Default Behavior

The script automatically retrieves configuration in the following order:

1. Command-line arguments
2. Environment variables
3. `frontend/runtime-config.local.js`
4. `backend/scripts/.env/*.env`

Default reads:

- API Base: `frontend/runtime-config.local.js` / `frontend/runtime-config.js`
- `X-API-Key`: `frontend/runtime-config.local.js`
- Paddle token: `backend/scripts/.env/paddle.env`
- MinerU token: `backend/scripts/.env/mineru.env`
- Translation API key: `backend/scripts/.env/deepseek.env`

## Common Examples

Run the full `book` workflow:

```bash
cd frontend
npm run smoke:status -- --file ../data/temPDF/test1.pdf
```

Specify Paddle:

```bash
cd frontend
npm run smoke:status -- \
  --file ../data/temPDF/test1.pdf \
  --ocr-provider paddle
```

Run directly from repository root:

```bash
./.github/scripts/smoke_frontend_status.sh data/temPDF/test1.pdf --ocr-provider paddle
```

Run translation only, no rendering:

```bash
cd frontend
npm run smoke:status -- \
  --file ../data/temPDF/test1.pdf \
  --workflow translate \
  --expect-labels "OCR in progress,Translating,Processing complete"
```

Specify endpoint URL and timeout:

```bash
cd frontend
npm run smoke:status -- \
  --file ../data/temPDF/test1.pdf \
  --api-base http://127.0.0.1:41000 \
  --max-wait-ms 3600000
```

Output JSON:

```bash
cd frontend
npm run smoke:status -- \
  --file ../data/temPDF/test1.pdf \
  --json
```

## Output Highlights

The script prints each status change, for example:

```text
2026-04-25T14:00:00.000Z | running | OCR in progress | Completed OCR for page 3/12
2026-04-25T14:00:20.000Z | running | Translating | Completed translation for batch 5/18
2026-04-25T14:01:10.000Z | running | Rendering | Completed rendering for page 9/12
2026-04-25T14:01:30.000Z | succeeded | Processing complete | Processing complete
```

At the end, a summary is provided:

- `job_id`
- `final_status`
- `observed_labels`
- `missing_labels`
- `event_count`

If expected labels are missing or the task does not end with `succeeded`, the script returns a non-zero exit code.

## Fixed Reports

The repository-level script always writes out:

- `doc/reports/frontend-status-smoke-latest.json`

The report includes:

- `jobId`
- `finalStatus`
- `observedLabels`
- `missingLabels`
- `observations`
- `eventSamples`

## Scope of Application

This smoke test primarily verifies the "frontend status mapping pipeline":

- Whether the backend produces job details
- What labels the frontend status normalization logic produces
- Whether these labels actually appear in the real workflow

It does not verify browser layout, component animations, button visibility, or other pure UI details. If those need to be covered later, Playwright should be added separately.
