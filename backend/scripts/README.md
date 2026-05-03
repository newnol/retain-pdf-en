# Scripts Overview

`scripts/` is the scripting engineering directory for the complete "PDF -> OCR -> Translation -> Layout-preserving Rendering" pipeline.

The top level is now divided into five layers by responsibility:

- `runtime/`
  Runtime orchestration layer; only contains pipeline.
- `services/`
  Concrete implementation layer for OCR, MinerU, translation, rendering, etc.
- `foundation/`
  Configuration, shared utilities, and prompt resources.
- `entrypoints/`
  Manual execution entry points.
- `devtools/`
  Experiments, migration, examples, test probes, and diagnostic scripts.

Within `services/`, there are now two clearly defined categories:

- Capability modules such as provider / translation / rendering
- Cross-stage shared protocol modules such as `services/pipeline_shared/`

## Main Chain

The core flow can be summarized as:

`PDF -> OCR provider -> document_schema -> services/translation -> services/rendering -> PDF`

More specifically:

1. `normalize.stage.v1`
   OCR provider raw results enter `document_schema`, producing `ocr/normalized/document.v1.json` and `document.v1.report.json`
2. `translate.stage.v1`
   The translation chain only reads `document.v1.json`, extracts body whitelist blocks, supplements continuation/orchestration metadata, and outputs `translated/`
3. `render.stage.v1`
   The rendering chain only reads translation artifacts and source PDF, and outputs `rendered/*.pdf`
4. `book.stage.v1`
   Top-level book flow; only responsible for orchestrating `normalize -> translate -> render`, no longer letting downstream directly guess provider raw structure

The current formal block-level contract is:

- `geometry`
- `content`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy`
- `provenance`

Notes:

- `type/sub_type/bbox/text/lines/segments` are still retained but have been downgraded to compatibility fields
- The translation/rendering main chain should no longer re-infer body text based on raw OCR fields or `derived/sub_type`
- Whether to enter translation is governed by `policy.translate` as the sole formal entry point
- The formal consumption scope for translation payloads has also been fixed as a strict top-level contract, no longer relying on `metadata` mirroring

## Recommended Entry Points

For daily use, prefer these entry points:

- `scripts/entrypoints/run_book.py`
  Currently the topmost complete entry point. Chains `normalize -> translate -> render` via `book.stage.v1`; suitable for manually running the entire main chain locally.
- `scripts/entrypoints/run_provider_case.py`
  General-purpose entry name for running "provider -> normalize -> translate -> render" with a single command locally. The underlying layer determines the specific OCR implementation via provider dispatch; the entry name does not expose the provider.
- `scripts/entrypoints/run_document_flow.py`
  When you already have OCR JSON and PDF, prefer using this neutral entry name to run the complete flow.
- `scripts/entrypoints/run_normalize_ocr.py`
  Top-level normalize worker. Consolidates raw OCR JSON into `document.v1.json`.
- `scripts/entrypoints/run_provider_ocr.py`
  Local OCR-only general-purpose entry name. Only runs provider -> unpack -> normalize.
- `scripts/entrypoints/run_translate_only.py`
  Top-level translate worker. Only accepts already-normalized `document.v1.json`.
- `scripts/entrypoints/run_render_only.py`
  Top-level render worker. Only accepts translation artifacts and PDF.
- `scripts/entrypoints/translate_book.py`
  Translation only, no rendering.
- `scripts/entrypoints/build_book.py`
  Rendering only, no re-translation.
- `scripts/entrypoints/build_page.py`
  Single-page rendering debug entry point.
- `scripts/entrypoints/translate_page.py`
  Single-page translation debug entry point.
- `scripts/entrypoints/validate_document_schema.py`
  Contract troubleshooting entry point. Only for checking `document.v1` or adapter behavior; not a daily full-chain entry point.
- `scripts/devtools/tests/document_schema/regression_check.py`
  Long-term regression tool; not a main flow entry point.

Do not use test scripts as main entry points. For normal verification of the entire chain, prefer running:

1. `run_book.py --spec <job_root>/specs/book.spec.json`
2. Or submit a job via the Rust API, letting Rust drive three workers via spec

If you want to modify the translation chain, the recommended reading order is:

1. `services/translation/README.md`
2. `services/translation/llm/README.md`
3. Then proceed as needed into `services/translation/llm/providers/` or `services/translation/llm/shared/orchestration/`

## New Provider Integration Order

If you need to integrate a new OCR provider later, follow this order first; do not directly modify the translation/rendering main chain:

1. First read `scripts/services/ocr_provider/README.md`
   Clearly define the provider API layer boundary, state, and raw artifact responsibilities.
2. Then read `scripts/services/document_schema/README.md`
   Clarify which layer fields should fall into: `geometry/content/layout_role/semantic_role/structure_role/policy/provenance`.
3. Prepare a minimal raw fixture
   Place it in `scripts/devtools/tests/document_schema/fixtures/`.
4. Add provider implementation and adapter
   Connect into the unified schema via `scripts/services/document_schema/adapters.py`.
5. Register the fixture in `scripts/devtools/tests/document_schema/fixtures/registry.py`
   Do not manually modify the main chain to accommodate provider raw JSON.
6. Run `scripts/devtools/tests/document_schema/regression_check.py`
   At minimum confirm that detector, adapt, validation, and extractor smoke all pass.

## Top-level Directory Description

- `services/mineru`
  MinerU integration, downloading, unpacking, job organization.
- `services/pipeline_shared`
  Shared stage protocol, summary, and JSON IO across provider / translate / render.
- `services/translation`
  OCR payload to translation JSON.
- `services/rendering`
  Translation JSON to PDF.
- `runtime/pipeline`
  Top-level orchestration layer for translation and rendering.
- `services/README.md`
  Overall description of the concrete capability implementation layer.
- `foundation/config`
  Paths, fonts, layout, and runtime default configuration.
- `foundation/shared`
  Input parsing, job directories, environment variables, prompt loading, and other shared capabilities.
- `foundation/prompts`
  Editable prompt templates.
- `devtools/experiments`
  Experimental flows; not part of the stable main chain.
- `devtools/tests`
  Test probes and layout experiments.
- `devtools/tools`
  Example scripts, migration tools, and diagnostic scripts.

## Structured Output

Job output is uniformly placed under:

- `output/<job-id>/source`
- `output/<job-id>/ocr`
- `output/<job-id>/translated`
- `output/<job-id>/rendered`
- `output/<job-id>/artifacts`
- `output/<job-id>/logs`

Where:

- `ocr/unpacked/layout.json` retains the original MinerU OCR output
- `ocr/normalized/document.v1.json` is the unified OCR input used by the current translation/rendering main chain
- `ocr/normalized/document.v1.report.json` records adapter/provider detection, default value filling, and schema validation summary
- `translated/translations` contains intermediate translation results
- `rendered/*.pdf` is the final output PDF
- `rendered/typst/` retains Typst intermediate artifacts for debugging and tracing
- `artifacts/` holds summary, bundle index, and other download artifacts
- `logs/` holds stage logs and subsequent structured event output

Current conventions:

- The main chain preferentially consumes `document.v1.json`
- The formal consumption scope for `document.v1.json` is `geometry/content/layout_role/semantic_role/structure_role/policy/provenance`
- If the entry point provides raw `layout.json`, an explicit normalization is performed first before entering the translation main chain
- Raw MinerU structures are retained for adapters, debugging, and tracing; they are no longer the implicit data contract of the main chain
- If you are only doing troubleshooting, status display, or API output summary, prefer consuming `document.v1.report.json`
- The Python side uniformly reads reports and generates normalization summaries via `services/document_schema/reporting.py`
- `specs/` stores stage spec JSON files; currently covering:
  - `normalize.spec.json` -> `normalize.stage.v1`
  - `translate.spec.json` -> `translate.stage.v1`
  - `render.spec.json` -> `render.stage.v1`
  - `provider.spec.json` -> `provider.stage.v1`
  - `book.spec.json` -> `book.stage.v1`

## Stage Spec Conventions

The current stable protocol from Rust API to Python worker is fixed as:

`python -u <entrypoint> --spec output/<job-id>/specs/<stage>.spec.json`

Conventions are as follows:

- Spec only stores stage input, parameters, and job references; it no longer exposes Python internal implementation details to Rust
- `job.job_root` is the path derivation anchor; each stage internally derives `source/ocr/translated/rendered/artifacts/logs` via `job_dirs.py`
- Secrets are not written into the spec in plaintext
  - Translation key is passed via `credential_ref=env:RETAIN_TRANSLATION_API_KEY`
  - If the provider is `mineru`, the corresponding token is passed via `credential_ref=env:RETAIN_MINERU_API_TOKEN`
  - At runtime, Rust injects environment variables; Python reads them via `stage_specs.resolve_credential_ref(...)`
- Both the Rust main workflow and local book/translate entry points have switched to spec-only
  - `run_normalize_ocr.py`
  - `run_provider_ocr.py`
  - `run_translate_only.py`
  - `run_render_only.py`
  - `run_translate_from_ocr.py`
  - `run_document_flow.py`
  - `run_provider_case.py`
  - `run_book.py`
  - `translate_book.py`

Local development entry points have also been unified to the stage spec main path:

- `entrypoints/run_provider_case.py` -> Current provider-backed full workflow local general-purpose entry name
- `entrypoints/run_document_flow.py` -> Current normalized-document full flow local general-purpose entry name
- `entrypoints/run_provider_ocr.py` -> Current OCR-only provider flow local general-purpose entry name
- `services/document_schema/normalize_pipeline.py` -> `normalize.stage.v1`
- `services/translation/translate_only_pipeline.py` -> `translate.stage.v1`
- `services/rendering/render_only_pipeline.py` -> `render.stage.v1`
- `services/translation/from_ocr_pipeline.py` -> `book.stage.v1`
- `entrypoints/run_book.py` -> `book.stage.v1`

In other words, the current actual execution scope for the "topmost complete flow" is:

- Local: `run_book.py --spec .../book.spec.json`
- Rust API: Create a job; Rust generates `specs/*.spec.json` and sequentially starts workers
- Test scripts: Only for regression; they do not represent the main execution path

## Python Dependency Source of Truth

Current Python dependencies have converged to the repository root's [`pyproject.toml`](/home/wxyhgk/tmp/Code/pyproject.toml).

Do not directly hand-edit these requirements files:

- [`docker/requirements-app.txt`](/home/wxyhgk/tmp/Code/docker/requirements-app.txt)
- [`docker/requirements-test.txt`](/home/wxyhgk/tmp/Code/docker/requirements-test.txt)
- [`desktop/requirements-desktop-posix.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-posix.txt)
- [`desktop/requirements-desktop-windows.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-windows.txt)
- [`desktop/requirements-desktop-macos.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-macos.txt)

After modifying dependencies, uniformly execute:

```bash
python backend/scripts/devtools/sync_python_requirements.py --repo-root .
```

Check only for drift:

```bash
python backend/scripts/devtools/sync_python_requirements.py --repo-root . --check
```

Compatibility notes:

- If legacy job directories still use `originPDF/jsonPDF/transPDF/typstPDF`, the current backend will directly reject detail/download endpoints. Please re-run the job to generate the standard schema.
- The old per-page translation JSON direct-scan mode has exited the main chain; render-only must provide `translation-manifest.json`.

## Sub-directory Documentation

- [PIPELINE_DIRECTORY_MAP.md](./PIPELINE_DIRECTORY_MAP.md)
- [foundation/config/README.md](./foundation/config/README.md)
- [foundation/shared/README.md](./foundation/shared/README.md)
- [runtime/pipeline/README.md](./runtime/pipeline/README.md)
- [services/README.md](./services/README.md)
- [services/ocr_provider/README.md](./services/ocr_provider/README.md)
- [services/translation/README.md](./services/translation/README.md)
- [services/translation/orchestration/README.md](./services/translation/orchestration/README.md)
- [services/translation/continuation/README.md](./services/translation/continuation/README.md)
- [services/translation/policy/README.md](./services/translation/policy/README.md)
- [services/rendering/README.md](./services/rendering/README.md)
- [services/mineru/README.md](./services/mineru/README.md)

## Design Boundaries

- `services/translation` does not directly operate PDF
- `services/rendering` does not directly decide translation strategy
- `runtime/pipeline` is responsible for orchestration; it does not descend into implementation details
- `foundation/` does not carry specific business flows
- `entrypoints/` only serves as entry points; it does not carry core implementations
- `devtools/` must not become a reverse dependency of the main chain

## Architecture Checks

For daily changes, it is recommended to run at least these two checks:

- `python3 backend/rust_api/scripts/check_architecture.py`
- `python3 backend/scripts/devtools/check_pipeline_architecture.py`

The second one is responsible for catching the most easily regressed boundaries in the Python main chain:

- `runtime/pipeline` re-importing `services.ocr_provider` / `services.mineru` directly
- `runtime/pipeline` re-understanding provider raw tokens, e.g., `layoutParsingResults`
- `services/translation` / `services/rendering` re-touching provider raw adapters
- `entrypoints/*` bypassing stable entry points to directly connect to deep implementations
- `services/ocr_provider/__init__.py` losing explicit public exports
- `services/ocr_provider/provider_pipeline.py` losing stable compat symbols or no longer serving as the main chain handoff
- `services/ocr_provider/paddle_*` reverse-depending on `runtime/pipeline` / `services/translation` / `services/rendering`
