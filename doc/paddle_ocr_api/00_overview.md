# 00 Overview

## Goal

The goal of the Paddle OCR integration layer is:

- Input: Paddle OCR raw JSON
- Output: `normalized_document_v1` conforming to the current main contract

That is:

`Paddle raw payload -> provider adapter -> document.v1 -> translation/rendering`

## Current Recognition Convention

The current code recognizes the following payload as Paddle:

- Top level is `dict`
- `layoutParsingResults` exists
- `dataInfo` exists

Code location:

- `backend/scripts/services/document_schema/provider_adapters/paddle/adapter.py`
- `backend/scripts/services/document_schema/adapters.py`

## Current Directory Responsibilities

`provider_adapters/paddle/` is currently split by responsibility into these parts:

- `adapter.py`
  Paddle provider main entry point
- `payload_reader.py`
  Reads top-level payload and constructs page specs per page
- `page_reader.py`
  Constructs page context / page spec
- `block_reader.py`
  Constructs block context / block spec
- `block_labels.py`
  `block_label -> type/sub_type/tags` mapping
- `trace.py`
  Constructs `metadata/source/derived`
- `continuation.py`
  Maps Paddle's group information to `continuation_hint`
- `page_trace.py`
  Page-level trace and layout_det matching
- `rich_content.py` and related files
  Rich content trace aggregation

## Adapter Developer's Task Boundary

The person adapting Paddle is only responsible for these layers:

1. Paddle raw field interpretation
2. Field placement rules
3. `block_label` semantic mapping
4. `continuation_hint` mapping
5. Fixtures and regression

Do NOT mix these into the task:

1. Translation prompts
2. Layout overrides
3. PDF write-back
4. Frontend display logic

## Acceptance Criteria

At minimum, the following must be satisfied:

1. `adapt_path_to_document_v1()` can convert Paddle raw JSON to `document.v1`
2. `validate_document_payload()` passes
3. `extract_text_items()` smoke test passes
4. Fixtures are registered in regression
5. Documentation has been updated
