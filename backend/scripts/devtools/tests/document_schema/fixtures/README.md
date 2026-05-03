# Document Schema Fixtures

This directory contains minimal samples used for long-term regression testing of `document_schema`.

Recommended reading order:

1. First read `scripts/services/document_schema/README.md`
2. Then prepare minimal fixtures in this directory
3. Then write adapters and registry
4. Finally run `regression_check.py`

This directory mainly only handles fixture rules.
For more complete field placement, provider integration order, and report structure descriptions, refer to `document_schema/README.md`.

Goal:

- When integrating a new OCR provider, first add a minimal raw fixture
- After the adapter is complete, register this fixture in `registry.py`, then let `regression_check.py` consume it automatically
- Do not first modify the translation/rendering main chain to "adapt" provider raw JSON

Current convention:

1. Each provider should have at least one minimal raw fixture
2. Fixtures should be as small as possible, but able to stably trigger the detector
3. Fixture filenames should include the provider name
4. Real large samples can still reference files in `output/...`; this directory prioritizes small samples that can be committed and retained long-term

Recommended minimal coverage:

- Detector can recognize it
- Adapter can produce valid `document.v1`
- At least 1 page
- At least 1 text block

Current fixtures:

- `generic_flat_ocr.minimal.json`

## Fixture-Side Checklist

When integrating a new OCR provider, this directory only cares about the fixture side:

1. Prepare a minimal raw fixture
   - Place in this directory
   - Filename includes provider name
   - Can stably trigger the detector

2. Register the fixture in `scripts/devtools/tests/document_schema/fixtures/registry.py`
   - `name` is unique
   - `provider` matches the adapter registration name, preferentially referencing shared constants from `services/document_schema/providers.py`
   - `document_id` is stable and readable

3. Run `scripts/devtools/tests/document_schema/regression_check.py`
   - At least confirm detector, adapt, validation, and extractor smoke all pass
