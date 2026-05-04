# MinerU Integration Notes

This layer is only responsible for MinerU integration, not for translation strategy or PDF rendering.

If you're currently focused on "how external OCR APIs should be independently abstracted rather than coupled to the current workflow," read first:

- `scripts/services/ocr_provider/README.md`

`services/mineru/` is only the concrete implementation for the MinerU provider.

## Scope Boundaries

- Submit tasks to MinerU
- Query task status
- Download and unpack MinerU results
- Organize `output/<job-id>/source`, `ocr`, `translated`, `rendered`, `artifacts`, `logs`
- Retain raw `layout.json` for adapters, debugging, and traceability
- Produce the unified intermediate layer `document.v1.json`

Things NOT done here:

- No OCR post-processing
- No translation
- No PDF rendering
- No determination of `fast/sci/precise` translation strategy

## Recommended Entry Points

- `scripts/entrypoints/run_provider_case.py`
  For local manual use, prefer this generic entry point. It uses a neutral name and doesn't hardcode the provider name.
- `mineru_pipeline.py`
  The stable implementation behind `entrypoints/run_provider_case.py`.
- `mineru_job.py`
  Only handles parsing and unpacking; suitable for getting MinerU results first and then manually connecting to translation.
- `mineru_api.py`
  Lowest-level API call wrapper; only use when you need to call MinerU endpoints directly.
- `scripts/devtools/tools/mineru_api_example.py`
  Minimal example; suitable for testing endpoints and inspecting response structures.

## Directory Structure

- `output/<job-id>/source`
- `output/<job-id>/ocr`
- `output/<job-id>/translated`
- `output/<job-id>/rendered`
- `output/<job-id>/artifacts`
- `output/<job-id>/logs`

## Default Conventions

- The MinerU stage simultaneously produces:
  - `ocr/unpacked/layout.json`
  - `ocr/normalized/document.v1.json`
  - `ocr/normalized/document.v1.report.json`
- The current translation/rendering main pipeline by default requires and preferentially uses `ocr/normalized/document.v1.json`
- `ocr/unpacked/layout.json` is retained for adapters, debugging, and traceability; it is no longer an implicit fallback for the main pipeline
- `content_list_v2.json` is currently only used for experiments and adaptation, not the main path
- If you only need a provider / defaults / validation summary display, preferentially read `document.v1.report.json`

Responsibility breakdown:

- `document_v1.py`
  Only responsible for MinerU's `layout.json -> document.v1.json`
- `artifacts.py`
  Only responsible for MinerU artifact paths and internal provider file organization
- `contracts.py`
  Only responsible for MinerU provider private artifact filenames and directory names
- `job_flow.py`
  Only responsible for task orchestration, downloading/unpacking, and persistence
- `mineru_pipeline.py`
  Only responsible for feeding normalized OCR input into the translation/rendering main pipeline

Note:

- Main pipeline `pipeline_summary.json`, stdout labels, and source-json selection rules have all been consolidated into `services/pipeline_shared/`
- `services/mineru/` no longer carries any shared specification shells

This pipeline is now exposed as a unified adapter through `services/document_schema/adapters.py`,
meaning MinerU no longer leaks its raw structure directly into the translation main pipeline.

## Relationship with the Main Pipeline

The typical pipeline is:

1. `mineru_job.py` or `mineru_pipeline.py` submits a PDF to MinerU
2. Poll until the task completes
3. Download and unpack results
4. Copy the original PDF to `source`
5. Place parsing results in `ocr/unpacked`
6. Simultaneously generate `ocr/normalized/document.v1.json`
7. Subsequently, `runtime/pipeline` calls `services/translation` and `services/rendering` to complete the remaining process

The current `pipeline_summary.json` also includes a `schema_validation` entry for quickly confirming
whether the normalized document satisfies the current `document.v1` contract; it also carries a `normalization_report`
and `normalization_summary` to avoid the outer layer re-parsing raw OCR on its own.

In other words, this layer's responsibility is "turning the PDF into OCR input consumable by the main pipeline," not handling downstream business logic.

## Provider Stage Spec

The Rust API side currently drives the complete pipeline preferentially through:

`python -u scripts/entrypoints/run_provider_case.py --spec <job_root>/specs/provider.spec.json`

The corresponding schema is `provider.stage.v1`.

Current conventions:

- `source`
  Only stores `file_url` or `file_path`
- `ocr`
  Stores MinerU request parameters and `credential_ref`
- `translation`
  Stores translation parameters, glossary metadata, and translation `credential_ref`
- `render`
  Stores rendering parameters

Security conventions:

- MinerU tokens are not directly written to the spec
- The spec uses `credential_ref=env:RETAIN_MINERU_API_TOKEN`
- Translation keys likewise use `credential_ref=env:RETAIN_TRANSLATION_API_KEY`
- At runtime, Rust injects environment variables, and the Python worker resolves them

Runtime notes:

- The MinerU worker called by the Rust main workflow now requires `--spec`
- For local manual trial runs, use `scripts/entrypoints/run_provider_case.py`

Compatibility notes:

- If old task directories still use `originPDF/jsonPDF/transPDF/typstPDF`, the current backend will directly reject detail/download endpoints. Please re-run the task.

## Collaboration Rules

If OCR is maintained by a separate person, this module is only responsible for "retrieving provider results and organizing them into OCR input consumable by the main pipeline."

- You may modify provider API integration, downloading/unpacking, task directory organization, and provider-side compatibility here
- Do not add translation rules, glossary logic, or PDF rendering logic here
- If you find that downstream fields are insufficient, preferentially promote them to stable fields through `document_schema`, rather than leaking raw provider fields directly to translation/rendering
- If you change OCR artifact directory conventions, stdout labels, or main pipeline input locations, you must synchronously update `document_schema`, `runtime/pipeline`, and corresponding tests
