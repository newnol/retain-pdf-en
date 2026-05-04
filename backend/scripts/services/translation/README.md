# Translation Overview

This layer does only one thing: turn the OCR payload into a translatable, persistable, backfillable, and renderable translation result.

It is not responsible for PDF reading/writing, nor for MinerU unpacking.

## Stage Boundary

The formal input and output of the Translation stage are fixed as:

- Input:
  `document.v1.json`, translation policy parameters, translation output directory
- Output:
  Per-page translation payload, translation summary, translation diagnostics

Things it is explicitly not responsible for:

- Does not directly consume provider raw JSON, zip, or unpacked directories
- Does not handle source PDF page writing, layout overlay, or final PDF delivery
- Does not handle OCR provider upload, polling, download, or normalize artifact generation

Current stable handoff points:

- The upstream OCR stage should first converge provider results into `document.v1.json`
- The downstream rendering stage should only consume the translation artifacts persisted here, and should not go back to understand OCR provider private fields

Current default translation artifact protocol:

- `translation-manifest.json`
  Records the stable mapping from page index to translation payload file, prioritized for consumption by the rendering stage.
  Also carries lightweight metadata such as glossary summary, diagnostics summary, and the `invocation` field.
  The current formal path is uniformly marked as `stage_spec`
- Per-page translation payload
  Currently still persisted as one JSON per page; the manifest is responsible for declaring how these files should be discovered by the rendering stage
- Stage spec
  The `translate-only` entry point already supports `job_root/specs/translate.spec.json` (`translate.stage.v1`)
- Debug artifacts
  - `artifacts/translation_diagnostics.json`
  - `artifacts/translation_debug_index.json`

## Translation Payload Scope

Per-page translation payload is now split into two layers:

1. Top-level contract fields
2. `metadata` debug/bridge fields

Top-level contract fields include:

- `block_kind`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy_translate`
- `asset_id`
- `reading_order`
- `raw_block_type`
- `normalized_sub_type`

Current conventions:

- Translation classification, style hints, policy, payload backfill, and the main diagnostics chain should prioritize reading only these top-level contract fields
- `metadata` can be retained, but its responsibility is limited to debug, provider trace, and bridging `continuation_hint/provider warning`
- New logic should no longer treat `metadata.layout_role`, `metadata.semantic_role`, `metadata.structure_role` as formal semantic entry points
- If block semantics change in the future, prioritize modifying only the `document.v1 -> TextItem -> payload` contract projection; downstream modules should not independently dig through `metadata`

Compatibility conventions:

- New job directories should generate `translation-manifest.json`
- The translation artifact protocol is fixed as `translation-manifest.json` + per-page payload; the rendering stage no longer supports the legacy per-page JSON direct-scan mode
- The default loading scope is now strict contract; payloads missing the above top-level fields will raise an error directly
- The `translate-only` worker called by the Rust main workflow now requires `--spec`
- `scripts/entrypoints/translate_book.py` is now also a spec-only wrapper entry point
- API credentials no longer need to be written into the stage spec; specs use `credential_ref`, and the runtime environment injects the real key

## Debug Loop

There is now a minimal reproducible chain for locating "why a specific item was not translated / degraded / kept in original":

1. First check debug artifacts
   - `translation_diagnostics.json` for global statistics
   - `translation_debug_index.json` for item-level index
2. Then check individual items
   - `backend/scripts/devtools/replay_translation_item.py`
3. For batch regression, connect promptfoo
   - `backend/scripts/devtools/promptfoo/`
   - Use `scan_drift.py` to find saved vs replay drift items, then use `capture_case.py` to solidify into case artifacts

The Rust API exposes the corresponding endpoints:

- `GET /api/v1/jobs/{job_id}/translation/diagnostics`
- `GET /api/v1/jobs/{job_id}/translation/items`
- `GET /api/v1/jobs/{job_id}/translation/items/{item_id}`
- `POST /api/v1/jobs/{job_id}/translation/items/{item_id}/replay`

## Subdirectories

- `ocr/`
  OCR JSON reading and data extraction. The main path prioritizes reading `normalized_document_v1`; raw provider JSON is first processed through adapter, defaults, and schema validation at the entry point before entering here.
- `orchestration/`
  Layout zones, continuation, translation unit metadata.
- `classification/`
  Suspicious block classification under `precise` mode.
- `continuation/`
  Paragraph continuity detection, candidate pair export, and review.
- `diagnostics/`
  Structured translation diagnostics model, handling placeholder anomalies, window degradation, and keep-origin degradation events.
- `policy/`
  Translation policy configuration and explicit contract consumption. The default main chain no longer relies on local rules to second-guess OCR semantics.
- `llm/`
  Model requests, caching, retries, placeholder guarding, segment routing, and control context.
  New contributors should first read `llm/README.md`, which separately explains the provider layer, shared layer, orchestration layer, compatibility shims, and key call chains.
- `payload/`
  Payload protocol, formula placeholders, translation JSON read/write.
- `terms/`
  Glossary normalization, prompt injection, and term hit statistics.
- `workflow/`
  Single-page translation workflow entry point.

## Main Flow

1. `ocr/` reads the unified intermediate layer `document.v1.json` and extracts page blocks
2. If the entry point receives provider raw JSON, `document_schema/adapters.py` first converts it to `document.v1`
3. `workflow/translation_workflow.py` generates per-page translation templates and loads payload
4. `orchestration` fills in layout zones and orchestration metadata
5. `continuation` first consumes upstream `continuation_hint`, then uses rules as fallback to merge consecutive paragraphs into a unified translation unit
6. `policy` determines which blocks to skip based on mode
7. `llm` calls the model for batch translation, caching, and retries, and uniformly handles placeholder/segment/fallback control
8. `payload` backfills translation results into page payload and saves the final JSON

Supplementary conventions:

- The translation main chain should not directly understand any OCR provider's raw JSON structure
- The translation main chain's current default persisted result is "per-page translation payload + translation-manifest.json"; this layer is responsible for artifact content and mapping protocol, not for final PDF filename or rendering mode
- Any block in `document.v1` that already carries a `skip_translation` tag must be blocked at the `ocr/json_extractor.py` extraction stage and must not leak into translation candidates
- Body text extended semantics like `abstract` can continue into translation; blocks explicitly marked for skipping by the provider such as `reference_entry` and `formula_number` should not enter the payload
- The extraction stage prioritizes reading explicit `content.kind / layout_role / semantic_role / structure_role / policy.translate`; the default main chain no longer infers body text from `derived.role / sub_type / raw_type / tags`
- The extraction stage expands the `continuation_hint` on blocks into `ocr_continuation_*` fields in the payload
- Continuation currently uses a provider-first strategy: prioritizes consuming same-page `intra_page` provider hints; cross-page `cross_page` hints are only consumed under controlled conditions ("adjacent pages + unambiguous ordering + layout_zone hits page-end/page-start reading boundary + sufficient text length"), otherwise retained but not directly driving concatenation
- If you only want to troubleshoot whether OCR normalization has issues, prioritize checking `document.v1.report.json`
- When reading report summaries on the Python side, prioritize going through `document_schema/reporting.py`

The default body text whitelist is now fixed as:

- `content.kind == "text"`
- AND `policy.translate == true`

This means:

- Whether body text enters the translation chain should be decided at the normalize / adapter stage
- The translation default main chain no longer re-infers `footer/header/page_number/table/image/code/reference_content`
- Legacy local skip/rewrite rules such as `ref_text`, `mixed_literal`, `metadata_fragment` have been removed from the default main chain

## Glossary v1

The current glossary chain is split into two input layers:

- Named glossary resources: first persisted by the Rust API, then referenced via `glossary_id`
- Inline terms within a task: passed in directly with the task as `glossary_entries`

Before entering Python, the Rust side first completes:

- Glossary entry normalization
- Deduplication
- Merging of named glossary and inline terms
- Coverage statistics for identical `source` entries

The Translation stage currently does only two things:

- Injects the merged glossary into the LLM control context as a translation preference hint
- After translation completes, tallies term hit statistics and writes them into `translation-manifest.json`, diagnostics files, and pipeline summary

Things it explicitly does not do:

- Does not perform post-translation forced replacement
- Does not guarantee every term will be hit
- Does not directly parse Excel files

## Mode Descriptions

- `fast`
  Classifier not enabled.
- `sci`
  Oriented toward academic papers and technical documents; also performs domain inference.
- `precise`
  Enables the LLM classifier; only performs additional judgment on suspicious OCR blocks.

## Policy Config Compatibility Notes

`build_translation_policy_config()` in `policy/config.py` still retains several legacy fields, but they no longer belong to the default main chain semantics:

- `enable_narrow_body_noise_skip`
- `enable_metadata_fragment_skip`
- `metadata_fragment_max_page_idx`
- `enable_reference_zone_skip`
- `enable_reference_tail_skip`

The current convention is:

- The default main chain will not consume these fields to reconstruct legacy skip logic
- They are currently retained only as a deprecated compatibility surface, mainly to prevent old tests/callers from immediately breaking
- New code should not design behavior based on these fields

Note:

- This is an internal Python translation policy contract, not an external HTTP API contract
- The real "whether to translate" decision should still come from the explicit block policy in `document.v1`

## Collaboration Guidelines

If the translation module is maintained by a separate person, this layer is only responsible for "turning `document.v1.json` into stable translation artifacts."

- Allowed to modify here: policy, concurrency, glossary, LLM scheduling, payload persistence, and translation diagnostics
- Do not directly handle provider raw OCR structures here, and do not stuff source PDF rendering logic back in
- The current formal output protocol is "per-page translation payload + `translation-manifest.json`"; the rendering layer should only consume this protocol
- If you modify payload structure, manifest field semantics, or default file discovery, you must synchronize updates to `runtime/pipeline`, `rendering`, README, and tests
- The glossary is currently a translation prompt constraint, not a rendering layer rule, nor an OCR layer rule; do not spread glossary logic to other modules
