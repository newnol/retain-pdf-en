# Translation LLM Orchestration

This layer is responsible for only one thing:
orchestrating "translation requests for a single block / a single batch of items" into a stable, fallback-capable, diagnosable provider call flow.

It is not responsible for:

- Provider-specific HTTP details
- OCR payload extraction
- Page payload backfill and persistence
- PDF rendering

## New Contributors Start Here

- To see the main entry point:
  `retrying_translator.py`
- To see the plain-text single-item degradation main chain:
  `fallbacks.py`
- To see formula segment routing:
  `segment_routing.py`
- To see the direct-typst special path:
  `direct_typst.py`
- To see batch/cache/tail retry:
  `batched_plain.py`

## Current Boundaries

- `retrying_translator.py`
  Shared orchestration aggregation entry point.
  Responsible for connecting workflow-side requests to the plain-text / segment / provider runtime main chains.

- `fallbacks.py`
  Plain-text single-item orchestration facade.
  Responsible for:
  - Selecting the direct-typst / segmented / plain-text main path
  - Tagged placeholder first decision
  - Single-item plain-text attempt loop
  - Sentence-level fallback integration
  - Retaining compatibility shims to avoid breaking external call sites and tests

- `batched_plain.py`
  Batched plain-text orchestration.
  Responsible for:
  - Cache hit / cache drop
  - Low-risk batch decisions
  - Batch partial accept + retry split
  - Transport tail retry pass

- `direct_typst.py`
  Direct-typst main retry loop.
  Responsible for:
  - Attempt loop for direct-typst plain/raw two paths
  - Final closure after validation failure
  - Sentence fallback / transport degradation integration

- `direct_typst_long_text.py`
  Direct-typst long-text pre-splitting.
  Only responsible for splitting into chunks and reassembling at the chunk level; does not handle provider transport.

- `direct_typst_salvage.py`
  Direct-typst protocol/json shell salvage.
  Only responsible for extracting acceptable translations from anomalous text and performing partial accept.

- `heavy_formula.py`
  Heavy formula block pre-splitting.
  Only responsible for:
  - Whether heavy split is needed
  - How to split by placeholder density
  - Chunk-level retry followed by reassembly

- `plain_text_validation.py`
  Closure logic after plain-text validation failure.
  Only responsible for:
  - Protocol shell salvage
  - English residue partial salvage
  - Final degradation decision after repeated validation failures

- `sentence_level.py`
  Sentence-level fallback.
  Only responsible for sentence-level splitting, per-sentence requests, and partial success reassembly.

- `transport.py`
  Transport tail retry / DLQ shared logic.

- `keep_origin.py`
  Keep-origin payload constructor.
  Unifies the format of all degrade payloads.

- `metadata.py`
  translation_diagnostics / formula diagnostics / runtime term restore.

- `common.py`
  Pure judgment utilities for text length, continuation, CJK, placeholder count, etc.

## Call Chains

The most common call chain is:

`retrying_translator.py`
-> `fallbacks.py`
-> `direct_typst.py` / `segment_routing.py` / plain-text provider runtime
-> `keep_origin.py` / `plain_text_validation.py` / `sentence_level.py`

The batch path is:

`retrying_translator.py`
-> `batched_plain.py`
-> `fallbacks.py`

## Future Conventions

- New degradation strategies should be placed in their corresponding responsibility module; do not pile them back into `fallbacks.py`
- `fallbacks.py` should maintain its "thin facade + main loop" positioning; do not stuff pure utility functions into it
- Provider-specific logic should not enter here; keep it uniformly in provider implementations after `shared/provider_runtime.py`
- If a module again exceeds 400-500 lines, prioritize splitting by responsibility, not by mechanical code block
