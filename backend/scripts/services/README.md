# Services Description

`scripts/services/` is the concrete capability implementation layer.

This is where the modules that actually perform work reside, rather than flow orchestration:

- `ocr_provider/`
  Independent contract for the OCR provider API integration layer. This only defines "how third-party OCR services connect in," without coupling provider API details into translation/rendering workflows.
- `document_schema/`
  Unified intermediate document structure version definition, adapter registry, defaults consolidation, schema validation, and normalization report.
- `mineru/`
  Concrete implementation of the MinerU provider: submission, polling, downloading, unpacking, and task artifact organization.
- `pipeline_shared/`
  Shared stage protocol, summary, unified `pipeline_events.jsonl` event stream, and JSON IO across the provider / translate / render main chains; not bound to any single provider.
- `translation/`
  OCR parsing, translation orchestration metadata, strategy filtering, LLM calls, and result backfill.
- `rendering/`
  PDF erasure, background processing, Typst generation, formula normalization, final rendering, and compression.

Design principles:

- `services/*` is responsible for making each individual capability complete
- `ocr_provider/` only defines provider integration contracts; it does not take on specific provider implementations
- `document_schema/` is responsible for defining the unified intermediate layer; it does not carry provider details
- OCR provider raw JSON must first be converted to `document.v1` via `document_schema/adapters.py`
- When troubleshooting raw -> normalized conversion, prefer looking at `document.v1.report.json` or `validate_document_schema.py --adapt`
- If you only need to consume provider / defaults / validation summaries, prefer using `document_schema/reporting.py`
- `mineru/` is a provider implementation, not the OCR overall workflow itself
- `pipeline_shared/` is a neutral shared layer; provider-private logic should not be placed here
- The `translation/ocr` main chain preferentially reads the normalized document, rather than directly depending on a specific OCR provider's raw JSON
- `runtime/pipeline/` is only responsible for chaining these capabilities together
- Upper-layer entry points should preferentially depend on `runtime/pipeline/`, and should not directly assemble flows across services
- Common configuration and shared utilities continue to be placed in `foundation/`

## Shortest Path for New OCR Provider

When integrating a new provider, the recommended shortest path is:

1. First read `ocr_provider/README.md`
2. Then read `document_schema/README.md`
3. Prepare a minimal raw fixture
4. Write the provider API integration layer and adapter
5. Add the fixture to `devtools/tests/document_schema/fixtures/registry.py`
6. Run `devtools/tests/document_schema/regression_check.py`

Only after this chain succeeds should the provider enter the translation/rendering main chain.

## Collaboration Rules

It is now possible to split responsibilities by module, but boundaries must be guarded by protocol:

- The OCR/provider owner mainly maintains `ocr_provider/`, `mineru/`, and `document_schema/`
- The translation owner mainly maintains `translation/`
- The rendering owner mainly maintains `rendering/`
- The orchestration owner mainly maintains `runtime/pipeline/`

Default principles:

- Each owner should preferentially solve problems within their own module, without spreading temporary special cases to other modules
- `document.v1.json`, `translation-manifest.json`, and the render-only input protocol are stable handoff points and cannot be unilaterally modified
- If the handoff protocol must be changed, you must simultaneously update upstream/downstream README files, calling entry points, compatibility logic, and tests
- The translation/rendering main chain is prohibited from re-depending on provider raw JSON
- The pipeline is only responsible for orchestration; it is not responsible for absorbing provider special cases, translation details, or rendering patches
