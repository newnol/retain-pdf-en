# OCR Provider API Notes

This layer specifically describes "how external OCR services are integrated," and is decoupled from the current translation and rendering workflows.

The goal is very clear:

- Treat third-party OCR APIs as replaceable providers rather than part of the main pipeline
- Let MinerU, future OCR APIs, and even local OCR all follow the same integration approach
- Thoroughly separate "calling provider APIs" from "consuming a unified schema"

## Design Boundaries

This layer is responsible for:

- Defining the capability boundaries of OCR providers
- Defining the minimum abstraction for provider API integration
- Conventions for how provider raw artifacts are persisted
- Conventions for how raw payloads enter the `document_schema` adaptation chain

This layer is NOT responsible for:

- Translation
- PDF rendering
- Typst
- Body block strategies
- Any business consumption of provider-specific JSON

## Core Principles

1. The workflow only recognizes unified schemas, not provider raw JSON
   - The main pipeline OCR input is always `document.v1.json`
   - Provider raw JSON can only exist in the provider layer, adapter layer, and debug layer

2. The provider API is a "collection layer," not a "business layer"
   - Its responsibility is to send files out, retrieve results, and persist them
   - It should not determine translation mode, rendering mode, fonts, formula protection, or block strategies

3. Raw -> normalized must explicitly go through an adapter
   - Any provider return result first enters `services/document_schema/adapters.py`
   - `translation/ocr` and `rendering/` cannot directly understand provider JSON

4. Provider capabilities are variable; the unified schema is the stable contract
   - Providers may change interfaces, fields, or return formats
   - The main pipeline should not shake along with these changes

## Recommended Abstraction

If the OCR API layer is to be truly independent in the future, it is recommended to split it into at least the following categories of interfaces.

### 1. Provider Capability Declaration

Each provider first declares its own capability boundaries, for example:

- Whether a token is required
- Whether URL parsing is supported
- Whether local file upload is supported
- Whether batch processing is supported
- Whether callbacks are supported
- Whether table/formula toggles are supported
- Maximum file size
- Maximum page count
- Supported input types
- Default output types

This part is provider metadata and should not be scattered in workflow conditionals.

### 2. Provider Task Interface

Unify into the following categories of actions:

- `submit_url_task(...)`
- `submit_file_task(...)`
- `poll_task(...)`
- `download_result(...)`
- `unpack_result(...)`

Note that this is still only provider API semantics, not main pipeline semantics.

For example:

- `submit_*` returns provider task id / batch id
- `poll_task` returns the provider's current status
- `download_result` returns zip/markdown/json/html and other raw artifacts

### 3. Provider Raw Artifact Conventions

The provider layer is only responsible for organizing raw results into a stable persistence structure, for example:

- `ocr/provider/<provider-name>/...`
- `ocr/unpacked/...`
- `ocr/provider_summary.json`

Do not assume at the provider layer that:

- `layout.json` always exists
- `full.md` always exists
- It's always a zip
- Tables and formulas are always present

These should all be provider-specific artifacts, not main pipeline prerequisites.

### 4. Raw -> Schema Adaptation Entry Point

Once provider layer artifacts are persisted, the next step does only one thing:

- Call the `document_schema` adapter to produce:
  - `document.v1.json`
  - `document.v1.report.json`

At this point the provider's responsibility ends.

## MinerU as a Provider — Conclusions

Based on the current MinerU API documentation, several points can be clarified:

1. MinerU has two types of APIs
   - Precise parsing API: token required, async, supports tables/formulas, multi-format output, supports batching
   - Agent lightweight API: no login required, async, stricter limits, only outputs Markdown

2. Neither API should be directly coupled to the main pipeline
   - They are just different provider transport/result shapes
   - They are not the OCR contract of the main pipeline

3. MinerU's outputs suitable for entering the main pipeline are only two types
   - Raw artifact files
   - `document.v1` produced through the adapter

4. Content that should NOT be coupled into the workflow
   - MinerU's task state literal values
   - MinerU's `layout.json` / `content_list_v2.json` field details
   - MinerU's zip internal file naming
   - MinerU's specific upload methods, batch semantics, callback details
   - MinerU's model version names directly participating in translation/rendering decisions

## Placement Recommendations in the Current Project

The current codebase can be understood as follows:

- `services/ocr_provider/provider_pipeline.py`
  This is the provider-backed full pipeline stable entry point; scripts, tests, and compatibility patch points all use it as a boundary
- `services/ocr_provider/paddle_api.py`
  This is Paddle transport/polling/result download
- `services/ocr_provider/paddle_markdown.py`
  This is Paddle Markdown and image artifact persistence
- `services/ocr_provider/paddle_normalize.py`
  This is Paddle normalized document geometry correction and other pure implementation
- `services/mineru/`
  This is the concrete implementation of the MinerU provider, not "the OCR master entry point"
- `services/document_schema/`
  This is the OCR unified contract layer
- `runtime/pipeline/`
  This is the business orchestration layer

If other OCR APIs are integrated in the future, the recommended evolution is:

- `services/ocr_provider/`
  Only contains provider integration specifications and shared abstractions
- `services/mineru/`
  Serves as a concrete implementation under `ocr_provider`
- `services/<other_ocr>/`
  Concrete implementations of other providers
- `services/document_schema/`
  Continues to serve as the unified normalized contract

In other words:

- Providers are replaceable
- Adapters are extensible
- The workflow doesn't need to understand provider differences

## Recommended Integration Steps

When adding a new OCR provider, the recommended order is:

1. First write the provider capability specification
2. Then write the provider API call layer
3. Stably persist provider raw artifacts
4. Write the `document_schema` adapter
5. Add fixtures and regression tests
6. Only then allow entry into the translation/rendering main pipeline

If provider raw JSON enters the main pipeline before step 4, coupling will inevitably continue.

## Engineering Conclusions from MinerU Documentation

Looking at the current MinerU API documentation, the most valuable abstract information to absorb includes:

- It uses an async task model
- It distinguishes URL submission from file upload
- It distinguishes batch from single file
- It has its own provider state machine
- Its raw artifacts come in more than one form
- Its capability limits and restrictions are very clear

These should enter the provider layer design.

The following should NOT enter the main pipeline:

- A specific HTTP path
- A specific JSON field name
- A specific file name within a zip
- A specific provider-unique model name

## Current Recommendation

In the short term, do not continue expanding `services/mineru/` into a "default OCR platform layer."

A more stable approach is:

- Explicitly downgrade it to "MinerU provider implementation"
- Add this `ocr_provider/README.md` as the overarching convention
- When new OCR APIs are added in the future, align with this convention first, then decide on directory structure and adapter

This way, switching OCR providers in the future doesn't require splitting the translation/rendering main pipeline.

## Current Implementation Constraints

To avoid repeated refactoring, the current `ocr_provider/` directory is maintained under the following rules:

- `provider_pipeline.py` is responsible for stage/provider dispatching and stable compatibility surface
- New pure implementations should preferentially be placed in independent modules, not stacked directly back into `provider_pipeline.py`
- If tests need monkeypatching, patch points should be retained in `provider_pipeline.py`
- `services/ocr_provider/__init__.py` must explicitly export `provider_pipeline`
- `paddle_api.py` does not handle normalized schema
- `paddle_markdown.py` only handles Markdown/image artifacts, not translation or rendering
- `paddle_normalize.py` only handles normalized documents and geometry correction, not provider transport

These constraints have been incorporated into:

- `backend/scripts/devtools/check_pipeline_architecture.py`

In other words, if someone later reconnects `ocr_provider` back to the translation/rendering layer or changes the stable entry point to implicit exports/deep direct connections, the local architecture check will fail immediately.
