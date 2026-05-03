# Python Pipeline Directory Map

This document answers one question:

**When modifying `backend/scripts`, which directory should I enter first.**

## Most Common Entry Points

- Modify manual execution entry points:
  [`entrypoints/`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints)
- Modify stage orchestration bus:
  [`runtime/pipeline/`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline)
- Modify OCR provider integration:
  [`services/ocr_provider/`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider)
- Modify unified OCR contract:
  [`services/document_schema/`](/home/wxyhgk/tmp/Code/backend/scripts/services/document_schema)
- Modify translation main chain:
  [`services/translation/`](/home/wxyhgk/tmp/Code/backend/scripts/services/translation)
- Modify rendering main chain:
  [`services/rendering/`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering)

## Understand the Main Chain at a Glance

### Provider-backed Full Flow

```text
entrypoints/run_provider_case.py
  -> services/ocr_provider/provider_pipeline.py
     -> services/mineru/* or services/ocr_provider/paddle_api.py
     -> services/document_schema/*
     -> runtime/pipeline/book_pipeline.py
        -> runtime/pipeline/translation_stage.py
           -> services/translation/*
        -> runtime/pipeline/render_stage.py
           -> services/rendering/*
```

### Normalized OCR -> Translate -> Render

```text
entrypoints/run_book.py
  -> services/translation/from_ocr_pipeline.py
     -> runtime/pipeline/book_pipeline.py
        -> translation_stage.py
        -> render_stage.py
```

### Translate-only

```text
entrypoints/run_translate_only.py
  -> services/translation/translate_only_pipeline.py
     -> runtime/pipeline/translation_stage.py
        -> services/translation/*
```

### Render-only

```text
entrypoints/run_render_only.py
  -> services/rendering/render_only_pipeline.py
     -> runtime/pipeline/render_stage.py
        -> services/rendering/*
```

## Top-level Directory Map

### `entrypoints/`

- Purpose:
  Outermost entry layer; only handles parameter reception, exception wrapping, and routing calls to stable entry points.
- What it should NOT do:
  Should not assemble provider flows itself, and should not directly touch translation/rendering deep implementations.
- Typical files:
  - [`run_provider_case.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_provider_case.py)
    Provider-backed full flow main entry point.
  - [`run_book.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_book.py)
    Normalized OCR -> translate -> render main entry point.
  - [`run_translate_only.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_translate_only.py)
    Translation-only entry point.
  - [`run_render_only.py`](/home/wxyhgk/tmp/Code/backend/scripts/entrypoints/run_render_only.py)
    Render-only entry point.

### `runtime/pipeline/`

- Purpose:
  Stage orchestration bus; only responsible for organizing order, stage input/output, and aggregating results.
- What it should NOT do:
  Should not understand provider raw JSON, should not absorb translation strategy details, and should not implement low-level PDF rendering.
- Key files:
  - [`book_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/book_pipeline.py)
    Top-level `translate -> render` orchestration.
  - [`translation_stage.py`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/translation_stage.py)
    Translation-only stage entry point.
  - [`render_stage.py`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/render_stage.py)
    Render-only stage entry point.
  - [`translation_loader.py`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/translation_loader.py)
    Reads `translation-manifest.json` and per-page payloads.
  - [`render_inputs.py`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/render_inputs.py)
    Render-only input protocol consolidation.

### `services/document_schema/`

- Purpose:
  Unified OCR intermediate contract layer.
- When to enter:
  Enter here when modifying raw OCR -> `document.v1.json` adaptation, field defaults, or schema validation.
- Key files:
  - [`normalize_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/document_schema/normalize_pipeline.py)
    Normalize worker entry point.
  - [`adapters.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/document_schema/adapters.py)
    Raw provider -> normalized document main adapter entry.
  - [`reporting.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/document_schema/reporting.py)
    Normalization summary/report reading.

### `services/ocr_provider/`

- Purpose:
  Provider-backed OCR main entry point and provider protocol consolidation.
- When to enter:
  Enter here when modifying provider dispatch, Paddle API calls, or provider-backed worker main flow.
- Key files:
  - [`provider_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/provider_pipeline.py)
    Current provider-backed full flow stable entry point, also the compatibility surface for scripts/tests.
  - [`paddle_api.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_api.py)
    Paddle async API integration.
  - [`paddle_markdown.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_markdown.py)
    Paddle Markdown and image artifact persistence.
  - [`paddle_normalize.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/ocr_provider/paddle_normalize.py)
    Paddle normalized document geometry correction and similar pure implementations.

### `services/mineru/`

- Purpose:
  Concrete implementation of the MinerU provider.
- When to enter:
  Only enter here when modifying MinerU provider transport, downloading, unpacking, and artifact organization.
- Note:
  This is a provider implementation, not the OCR bus, and not the translation/rendering main chain.

### `services/translation/`

- Purpose:
  Transform `document.v1.json` into stable translation artifacts.
- When to enter:
  Enter here when modifying translation strategy, LLM scheduling, continuation, payload persistence, or diagnostics.
- Key files:
  - [`from_ocr_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/translation/from_ocr_pipeline.py)
    Normalized OCR -> translate -> render worker wrapper entry point.
  - [`translate_only_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/translation/translate_only_pipeline.py)
    Translate-only worker wrapper entry point.
  - [`workflow/translation_workflow.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/translation/workflow/translation_workflow.py)
    Single-page translation flow.
  - [`llm/README.md`](/home/wxyhgk/tmp/Code/backend/scripts/services/translation/llm/README.md)
    LLM directory boundary description.

### `services/rendering/`

- Purpose:
  Transform translation artifacts and source PDF into the final PDF.
- When to enter:
  Enter here when modifying overlay, Typst, background restoration, compression, or render-only protocol.
- Key files:
  - [`render_only_pipeline.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/render_only_pipeline.py)
    Render-only worker wrapper entry point.
  - [`api/`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/api)
    Stable rendering entry point.
  - [`typst/`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/typst)
    Typst main chain.

### `services/pipeline_shared/`

- Purpose:
  Shared stdout contract, summary, events, and JSON IO across provider / translate / render.
- What it should NOT do:
  Should not contain provider-private logic or translation/rendering algorithm details.

### `foundation/`

- Purpose:
  Configuration, paths, stage spec, shared utilities, and prompt loader.
- When to enter:
  Enter here when modifying cross-module shared configuration or stage spec protocol.

### `devtools/`

- Purpose:
  Debugging, regression, probing, and experimental scripts.
- What it should NOT do:
  Should not become a reverse dependency of the main chain.

## Quick Judgment

- "Is this an entry parameter or worker startup method change?"
  Look at `entrypoints/` first.
- "Is this a stage order or input/output protocol change?"
  Look at `runtime/pipeline/` first.
- "Is this a raw OCR adaptation or schema change?"
  Look at `services/document_schema/` first.
- "Is this a provider integration issue?"
  Look at `services/ocr_provider/` or `services/mineru/` first.
- "Is this a translation result issue?"
  Look at `services/translation/` first.
- "Is this a PDF rendering issue?"
  Look at `services/rendering/` first.

## Three Boundary Red Lines

- `runtime/pipeline/` does not understand provider raw JSON, nor does it directly import provider-private implementations.
- `services/translation/` and `services/rendering/` do not consume provider raw structures; they only consume stable handoff artifacts.
- `entrypoints/` only connects to stable entry points, and does not bypass `*_pipeline.py` or `runtime/pipeline/*` to directly access deep implementations.

## Newcomer Reading Order

1. [`README.md`](/home/wxyhgk/tmp/Code/backend/scripts/README.md)
   Start by understanding the overall directory and formal entry points.
2. [`PIPELINE_DIRECTORY_MAP.md`](/home/wxyhgk/tmp/Code/backend/scripts/PIPELINE_DIRECTORY_MAP.md)
   Then know where to make changes.
3. [`runtime/pipeline/README.md`](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/README.md)
   Review stage boundaries.
4. [`services/README.md`](/home/wxyhgk/tmp/Code/backend/scripts/services/README.md)
   Review the overall responsibility division of services.
5. Then proceed by module to the README files of `translation/`, `rendering/`, `ocr_provider/`.
