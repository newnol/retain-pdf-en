# Paddle OCR Integration Documentation

This documentation set serves only one purpose:

- Stably converge Paddle OCR raw results into `normalized_document_v1`

Do not turn this into a translation rules document, and do not stuff rendering strategies in here.

## Integration Boundary

The person adapting Paddle OCR is only responsible for:

1. Understanding Paddle's raw API and JSON structure
2. Implementing provider detection and the adapter
3. Mapping Paddle private fields to `document.v1`
4. Adding fixtures, regression tests, and documentation

Explicitly NOT responsible for:

1. Not modifying the translation layer `services/translation/*`
2. Not modifying the rendering layer `services/rendering/*`
3. Not writing Paddle-specific special cases in `runtime/pipeline/*`
4. Not letting downstream directly read Paddle raw JSON

## Current Code Entry Points

- Provider registration entry:
  `backend/scripts/services/document_schema/adapters.py`
- Provider constants:
  `backend/scripts/services/document_schema/providers.py`
- Paddle adapter entry:
  `backend/scripts/services/document_schema/provider_adapters/paddle/adapter.py`
- Paddle page reader:
  `backend/scripts/services/document_schema/provider_adapters/paddle/page_reader.py`
- Paddle block reader:
  `backend/scripts/services/document_schema/provider_adapters/paddle/block_reader.py`
- Common contract documentation:
  `backend/scripts/services/document_schema/README.md`

## Reading Order

1. [00_overview.md](./00_overview.md)
2. [01_response_shape.md](./01_response_shape.md)
3. [02_field_mapping.md](./02_field_mapping.md)
4. [03_semantics_rules.md](./03_semantics_rules.md)
5. [04_continuation_hint.md](./04_continuation_hint.md)
6. [05_adapter_checklist.md](./05_adapter_checklist.md)
7. [06_job_artifact_boundary.md](./06_job_artifact_boundary.md)
8. [official/README.md](./official/README.md)

## Integration Principles

1. Paddle private fields are only allowed in the adapter layer and trace layer.
2. The downstream main pipeline only consumes `document.v1.json`.
3. If Paddle has identified continuation paragraph groups, write `continuation_hint`; do not directly leak private fields like `group_id` to translation.
4. First ensure schema correctness, then do semantic enhancement; do not start by piling on rules.
5. `provider raw -> normalized_document -> artifact export -> download API` are four-layer boundaries; do not mix them.
