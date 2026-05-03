# 05 Adapter Checklist

## Task Definition

When assigning someone to adapt Paddle OCR, it is recommended to deliver according to the following:

### Input

- Paddle OCR raw JSON
- At least one minimal fixture
- At least one more complete fixture

### Output

- A registerable Paddle adapter
- `document.v1` output
- Corresponding documentation
- Corresponding tests

## File Scope

Allowed to modify:

- `doc/paddle_ocr_api/*`
- `backend/scripts/services/document_schema/provider_adapters/paddle/*`
- `backend/scripts/services/document_schema/adapters.py`
- `backend/scripts/services/document_schema/providers.py`
- `backend/scripts/devtools/tests/document_schema/fixtures/*`
- `backend/scripts/devtools/tests/document_schema/regression_check.py`

Do NOT modify:

- `backend/scripts/services/translation/*`
- `backend/scripts/services/rendering/*`
- `backend/scripts/runtime/pipeline/*`

Exception:

- Only when the main contract truly needs a new stable field should a proposal be made first, followed by modifying `document_schema`

## Onboarding Order

1. Confirm the Paddle raw response format
2. Catalog top-level / page-level / block-level fields
3. Define field placement
4. Implement detector
5. Implement adapter
6. Implement `continuation_hint` mapping
7. Add fixtures
8. Run regression
9. Update documentation

## Acceptance Commands

```bash
PYTHONPATH=backend/scripts python backend/scripts/devtools/tests/document_schema/regression_check.py
PYTHONPATH=backend/scripts python -m pytest backend/scripts/devtools/tests/document_schema -q
PYTHONPATH=backend/scripts python -m pytest backend/scripts/devtools/tests/translation -q
```

## Mandatory Checks

- Whether provider detection is stable
- Whether `document.v1` passes schema validation
- Whether `source.provider` is correctly set to `paddle`
- Whether `type/sub_type/tags/derived` conforms to the current contract
- Whether `metadata/source` retains necessary traces
- Whether `continuation_hint` is only written when reliable
- Whether `skip_translation` marking is only given to blocks that should be skipped

## Delivery Notes Template

When submitting, the adapter developer should at minimum explain:

1. Which Paddle API response format is supported
2. Which fixtures were used
3. Which field mappings were added or modified
4. Which Paddle fields were intentionally not connected
5. Whether `continuation_hint` was written
6. Test commands and results
