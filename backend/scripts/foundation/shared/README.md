# Shared Description

`scripts/foundation/shared` contains the foundational capabilities that the entire script suite depends on.

This layer does not handle OCR, translation, or rendering business logic; its main responsibility is to centralize "shared things" to avoid path, environment variable, and default parameter duplication across multiple scripts.

## Main Files

- `config.py`
  Transitional entry point. Internal implementation has been split into `scripts/foundation/config/`; new code should directly depend on the split modules.
- `input_resolver.py`
  Responsible for resolving input directories into explicit `source_json/source_pdf`.
- `job_dirs.py`
  Responsible for parsing and validating standard job directory contracts: `source/ocr/translated/rendered/artifacts/logs`.
- `local_env.py`
  Responsible for reading keys from explicit parameters, environment variables, or `scripts/.env/`.
- `prompt_loader.py`
  Responsible for loading editable prompt templates from `scripts/foundation/prompts/`.
- `job_cleanup.py`
  Responsible for output directory cleanup related logic.
- `stage_specs.py`
  Responsible for stage spec schema constants, JSON loader, and `credential_ref` resolution.

## Position in the Overall Pipeline

`foundation/shared` is the support layer for all layers:

- Stage workers / orchestration layer use it to parse specs, credential references, and standard task directories
- OCR provider implementation layer uses it to read tokens, environment configuration, and output paths
- Translation layer uses it to load prompts and default configuration
- Rendering layer uses it to read fonts, compression, and layout parameters
- Rust/Python orchestration layer uses it to parse `job_root/specs/*.spec.json`

## An Important Convention

Currently `config.py` contains some "process-level mutable tuning parameters", for example:

- `BODY_FONT_SIZE_FACTOR`
- `BODY_LEADING_FACTOR`
- `INNER_BBOX_SHRINK_X/Y`

These parameters can be overridden at runtime through `apply_layout_tuning(...)`.

This is convenient for CLI, but also means:

- When running multiple tasks consecutively in the same process, be aware that parameters may affect each other
- If further decoupling is done later, this layer is a key area worth continuing to refine

## Stage Spec and Credential Conventions

Current stage workers have been unified to:

`python -u <entrypoint> --spec <job_root>/specs/<stage>.spec.json`

Schema versions currently maintained by `stage_specs.py` include:

- `normalize.stage.v1`
- `translate.stage.v1`
- `render.stage.v1`
- `provider.stage.v1`
- `book.stage.v1`

Additional conventions:

- Spec is the stable data contract from Rust to Python, no longer relying on long CLI flag assembly
- Keys are not directly written into spec JSON
- Spec only retains `credential_ref`
  - `env:RETAIN_TRANSLATION_API_KEY`
  - `env:RETAIN_MINERU_API_TOKEN`
- Python worker uniformly resolves real values at runtime through `resolve_credential_ref(...)`
- Workers called by the Rust main workflow now require `--spec`
- Local development entry points are also unified to drive through stage specs

## Usage Recommendations

- New code should first look at the responsibility-split configuration under `scripts/foundation/config/`.
- Upper-level scripts should not self-assemble `output/<job-id>/...` paths; prefer using `job_dirs.py`
- Python workers only consume stage specs, no longer exposing long business parameter entry points
- If it's a stage worker, prefer adding/consuming schemas in `stage_specs.py` rather than continuing to expand CLI parameters
- Key reading should not be scattered in business code; prefer using `local_env.py`
- Prompts should not be hardcoded in business modules; prefer using `prompt_loader.py`
