# Translation Promptfoo Debugging

The goal of this scaffold is not to re-run the entire book, but to converge "why a certain translation item was not translated / degraded / output is dirty" into a reproducible, comparable, and automatically regressable minimal closed loop.

The current pipeline is split into three layers:

- Rust API debug interface
  - `GET /api/v1/jobs/{job_id}/translation/diagnostics`
  - `GET /api/v1/jobs/{job_id}/translation/items`
  - `GET /api/v1/jobs/{job_id}/translation/items/{item_id}`
  - `POST /api/v1/jobs/{job_id}/translation/items/{item_id}/replay`
- Python single item replay
  - `backend/scripts/devtools/replay_translation_item.py`
- Promptfoo fixture/eval
  - `scan_drift.py`, `capture_case.py`, `run_eval.py`, `promptfooconfig*.yaml` in this directory

## 1. First Locate Specific Item

When the local API is running, you can first check:

```bash
curl -H 'X-API-Key: retain-pdf-desktop' \
  'http://127.0.0.1:41000/api/v1/jobs/<job_id>/translation/items?final_status=kept_origin&q=protocol'
```

If you don't want to write curl manually, you can directly use:

```bash
python backend/scripts/devtools/translation_debug_api.py \
  items \
  --job-id <job_id> \
  --final-status kept_origin \
  --q protocol
```

Or directly view a single item:

```bash
curl -H 'X-API-Key: retain-pdf-desktop' \
  'http://127.0.0.1:41000/api/v1/jobs/<job_id>/translation/items/<item_id>'
```

```bash
python backend/scripts/devtools/translation_debug_api.py \
  item \
  --job-id <job_id> \
  --item-id <item_id>
```

When you need to directly replay the current translation pipeline:

```bash
python backend/scripts/devtools/translation_debug_api.py \
  replay \
  --job-id <job_id> \
  --item-id <item_id>
```

## 2. First Scan Saved vs Replay Strategy Drift

```bash
python backend/scripts/devtools/promptfoo/scan_drift.py \
  --job-root 20260415003317-c856fe \
  --saved-final-status kept_origin \
  --limit 10
```

By default it will:

- First filter by saved-side `final_status=kept_origin`
- Replay candidate items one by one
- Output items with strategy drift

If you want to print all replayed candidates:

```bash
python backend/scripts/devtools/promptfoo/scan_drift.py \
  --job-root 20260415003317-c856fe \
  --saved-final-status kept_origin \
  --all
```

## 3. Record Bad Examples as Fixtures

```bash
python backend/scripts/devtools/promptfoo/capture_case.py \
  --job-root 20260416034152-d12925 \
  --item-id p006-b014 \
  --description 'page6 red-shift paragraph untranslated' \
  --expected-contains red-shift \
  --expected-contains fluorescence \
  --required-term 551\ nm
```

By default it will write to:

- `backend/scripts/devtools/promptfoo/fixtures/cases.csv`
- `backend/scripts/devtools/promptfoo/fixtures/cases/<job>--<item>.json`

This JSON case artifact will freeze the following information together:

- Saved item snapshot
- Current replay result
- policy_before / policy_after
- Drift summary

If you only want to record the saved side this time without triggering replay:

```bash
python backend/scripts/devtools/promptfoo/capture_case.py \
  --job-root 20260416034152-d12925 \
  --item-id p006-b014 \
  --description 'page6 red-shift paragraph untranslated' \
  --skip-replay
```

Multi-value fields in CSV use `||` as separator, making it easy for multiple people to edit the table directly:

- `expected_contains`
- `required_terms`
- `forbidden_substrings`

## 4. Run Promptfoo

Prerequisites:

- Python can directly use the current repository environment
- `promptfoo` requires `Node 20.20+` or `22.22+`

`run_eval.py` will preferentially use the current shell's `node`; if the current version is insufficient but `~/.nvm/versions/node` has a compatible version installed, it will automatically switch without needing manual `nvm use`.

Only evaluate current replay output:

```bash
python backend/scripts/devtools/promptfoo/run_eval.py
```

Simultaneously view "current replay" compared with "task original persisted output":

```bash
python backend/scripts/devtools/promptfoo/run_eval.py --compare
```

If you only want to verify fixtures and assertion chain without calling the model:

```bash
python backend/scripts/devtools/promptfoo/run_eval.py --saved-only
```

The underlying actually executes:

```bash
npx promptfoo@latest eval -c backend/scripts/devtools/promptfoo/promptfooconfig.yaml
```

`run_eval.py` will automatically:

- Check if fixtures are empty
- Point `PROMPTFOO_PYTHON` to the current Python
- Inject fixture path into `PROMPTFOO_TRANSLATION_FIXTURES`

## Assertion Rules

Current fixtures default to supporting several types of hard rules:

- Minimum output length
- Whether Chinese must appear
- Required translation phrases
- Required preserved terms
- Forbidden dirty output fragments
- Whether `$...$` / `$$...$$` count matches source text

These rules are in:

- `backend/scripts/devtools/promptfoo/assertions.py`

## GitHub CI

The repository can now directly connect to GitHub Actions to run `current-replay`.

Corresponding workflow:

- `.github/workflows/translation-replay.yml`

Designed in two layers:

- First run pure local unit tests
  - `test_promptfoo_case_tools.py`
  - `test_promptfoo_harness_regressions.py`
  - `test_translation_debug_tools.py`
- Then run actual promptfoo current-replay
  - `python backend/scripts/devtools/promptfoo/run_eval.py`

### Why GitHub CI Does Not Depend on `data/jobs/`

After GitHub runner checkout, it cannot access your local `data/jobs/...` working directory by default, so case artifacts now additionally freeze:

- Translate spec key parameters
- Complete translated payload of the corresponding page

This way CI on the runner can directly run the current replay path from:

- `backend/scripts/devtools/promptfoo/fixtures/cases/*.json`

even without the job directory.

### Required GitHub Secret

Must configure:

- `RETAIN_TRANSLATION_API_KEY`

Purpose:

- For current-replay provider to call the model

Fork PRs cannot access secrets by default, so the workflow will:

- Still run local unit tests
- Skip the secret-requiring current-replay eval

### Artifacts

The workflow will upload:

- Current replay promptfoo JSON results
- Current fixture CSV
- Case artifact JSON
- `~/.promptfoo/logs/*.log`

## Applicable Boundaries

This tool set prioritizes solving "translation strategy / fallback / keep-origin / prompt / provider output anomaly" problems.

It does not directly solve:

- OCR block extraction errors
- Continuation joining errors
- Typst typesetting errors

But you can use this to quickly determine: whether the problem occurs "before translation" or "after translation".
