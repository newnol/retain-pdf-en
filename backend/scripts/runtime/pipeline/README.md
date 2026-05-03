# Pipeline Directory Description

`scripts/runtime/pipeline/` is responsible for chaining OCR normalization artifacts, translation flow, and rendering flow into a stable bus.

This location does not carry specific OCR provider parsing, translation model calls, or PDF low-level rendering details; instead, it is responsible for "how to organize these capabilities in the correct order."

## Stage Contracts

### 1. OCR / Normalize Stage

Responsibility boundary:

- Input: provider raw OCR results, source PDF, and provider metadata
- Output: unified intermediate layer `document.v1.json` and `document.v1.report.json`
- Ends here; does not continue to take on translation and final PDF rendering responsibilities

Stable handoff point:

- The translation/rendering main chain should only treat `document.v1.json` as the formal input after the OCR stage is complete
- Provider raw JSON, zip, and unpacked directories are only retained for adapters, troubleshooting, and tracing

### 2. Translation Stage

Responsibility boundary:

- Input: `document.v1.json`, translation strategy parameters, and translation output directory
- Output: per-page translation payloads, `translation-manifest.json`, translation summary, and diagnostics
- Ends here; not responsible for provider raw parsing, source PDF write-back, or final PDF delivery

Stable handoff point:

- The rendering stage should only consume the translation artifact protocol; it should not reverse-read provider raw OCR structures
- The current default translation artifact protocol consists of per-page translation payloads plus `translation-manifest.json`
- The render-only main chain now requires manifest-only; it no longer falls back to scanning old per-page JSON files
- The translation stage is allowed to read the source PDF for domain inference or strategy assistance, but it does not own source PDF rendering control
- If a glossary is enabled, the translation stage also writes the glossary summary into `translation-manifest.json`, diagnostics files, and pipeline summary; these fields are metadata and do not change the rendering input protocol
- Pipeline summary and translation manifest now also write an `invocation` field to declare the current stage schema version
- Each stage worker now also appends unified stage events to `logs/pipeline_events.jsonl`; this file is the transitional landing point for the subsequent Rust API event protocol consolidation

### 3. Rendering Stage

Responsibility boundary:

- Input: source PDF, translation artifacts, and rendering parameters
- Output: final PDF, along with necessary intermediate overlay / typst / compression artifacts
- Ends here; not responsible for OCR provider recognition or initiating translation model requests

Stable handoff point:

- The rendering main chain only accepts "source PDF + translation artifacts" as its input set
- OCR structure issues should be investigated back at `document.v1.json` / `document.v1.report.json`, rather than patching provider special cases in the rendering layer

## Module Responsibilities

- `book_pipeline.py`
  Unified orchestration entry point. Retains the most stable external calling surface, responsible for chaining the translation and rendering stages and returning summary results for the entire flow.
- `translation_stage.py`
  Only responsible for the translation stage. Takes `document.v1.json` and output directory as input, completes page range trimming, academic mode strategy assembly, and full-book translation, outputting per-page translation payloads.
- `render_stage.py`
  Only responsible for the rendering stage. Takes source PDF and translation artifacts as input, and generates the final PDF in `overlay`, `typst`, `dual`, or other modes.
- `services/pipeline_shared/`
  Does not belong to `runtime/pipeline/`, but it carries cross-stage shared stdout contract, summary, unified `pipeline_events.jsonl` event stream, and JSON IO; the pipeline should depend on this layer rather than falling back to a shared helper from some provider module.
- `render_inputs.py`
  Only responsible for validating the render-only calling protocol, normalizing `source_pdf_path + translations_dir/translation_manifest_path` into stable inputs consumable by the rendering stage.
- `render_mode.py`
  Only responsible for page range and `auto` mode determination, including whether it is more suitable to use the editable PDF path.
- `translation_loader.py`
  Only responsible for reading and filtering translation result files, organizing per-page translation JSON into data structures consumable by the rendering stage.
- `book_translation_flow.py`
  Responsible for the internal orchestration of full-book translation, including continuation, strategy application, batch translation, result backfill, and persistence.

## Collaboration Pattern

The standard flow is:

`OCR JSON -> translation_stage -> translation JSON -> translation_loader/render_stage -> final PDF`

Here `OCR JSON` refers to `document.v1.json` by default.

The Rust API's complete provider-backed workflow also chains along this boundary:

- The OCR child task first generates `document.v1.json`
- The translate-only entry point only generates per-page translation payloads and `translation-manifest.json`
- The render-only entry point then consumes the source PDF and translation artifacts to generate the final PDF

Supplementary conventions:

- If the entry point receives raw provider JSON, it should be explicitly normalized outside the pipeline or at the translation entry point
- The pipeline is not responsible for understanding provider-private raw structures
- If you only want to review provider detection, default value filling, or schema validation summary, prefer reading `document.v1.report.json`
- A complete task can chain three stages, but the input/output boundaries of the three stages must remain independent; they cannot be implicitly coupled via private in-memory objects
- If you only re-run rendering, reuse the existing job's `source_pdf` and `translations_dir`; do not re-enter the OCR or translation stages

## Stable External Entry Points

The following entry points are currently recommended for priority use:

- `run_book_pipeline(...)`
- `translate_book_pipeline(...)`
- `build_book_pipeline(...)`
- `build_book_from_translations(...)`
- `run_render_stage(...)`
- `resolve_page_range(...)`
- `is_editable_pdf(...)`

Supplementary conventions:

- Stage entry points have been fixed to the `--spec <stage-spec.json>` protocol
- Normalize stage corresponds to `normalize.stage.v1`
- Translate-only stage corresponds to `translate.stage.v1`
- Render-only stage corresponds to `render.stage.v1`
- Provider-backed full flow currently corresponds to `provider.stage.v1`
  This is a current implementation detail, not a top-level flow naming requirement
- The full-chain entry point based on already-normalized OCR corresponds to `book.stage.v1`
- Worker entry points called by the Rust main workflow now require `--spec`
- Local development entry points have also been unified to drive via stage spec

## Calling Recommendations

- CLI, API, and integration layers should preferentially only depend on `book_pipeline.py`
- Enter `runtime/pipeline/` only after the OCR stage is complete; do not stuff provider raw processing logic back here
- For translation-only calls, use `translate_book_pipeline(...)`
- For rendering-only calls, use `build_book_pipeline(...)` or `run_render_stage(...)`
  When calling, you must provide `source_pdf_path`, along with one of the following two translation inputs:
  - `translations_dir`
  - `translation_manifest_path`
- If neither is provided, or the directory does not contain `translation-manifest.json`, the entry point will directly throw a fixed `Render-only input error`
- The rendering stage will no longer "guess" old job directories or old page file naming conventions on its own
- It is not recommended for upper layers to assemble page ranges, mode determination, and translation directory reading themselves

## Decoupling Regression

Current targeted regression coverage:

- Python: manifest-only translation artifact loading, render-only input protocol
- Rust: OCR-only job snapshot, translate workflow, render workflow, complete task entry point, artifact manifest discovery

Common check commands:

```bash
PYTHONPATH=backend/scripts python -m pytest backend/scripts/devtools/tests -q
cd backend/rust_api && cargo test -q
```

## Collaboration Rules

`runtime/pipeline/` is suitable for sole maintenance by an "orchestration owner," but responsibilities must be tightly scoped to stage organization itself.

- This location is only responsible for stage ordering, entry protocols, job directories, and cross-stage result aggregation
- Do not stuff provider-private adaptation logic into the pipeline
- Do not roll back translation strategy details or rendering implementation details into the pipeline
- If modifying stage input/output contracts, you must simultaneously update upstream module README, downstream module README, CLI/API entry points, and regression tests
- If it is just a module-internal bug, prioritize fixing it within the module; the pipeline should only retain the necessary orchestration adaptation layer
