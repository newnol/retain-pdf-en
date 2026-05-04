# Continuation Subpackage Overview

This subpackage specifically contains paragraph continuity related logic, i.e., determining which OCR blocks should be joined into the same translation unit.

## Responsibilities

- `rules.py`
  Text start/end features, bbox geometric relationships, join/break scoring.
- `state.py`
  First consumes provider hints, then writes rule results back to the payload, maintaining continuation groups and candidate markers.
- `pairs.py`
  Exports candidate pairs, and performs join writeback after approval.
- `review.py`
  Sends candidate pairs to a model for review.

## Current Strategy

The current continuation uses a provider-first, but not provider-only, approach:

- If the payload already carries `ocr_continuation_*` fields and they are same-page `intra_page` provider hints, `state.py` will prioritize directly building groups
- For cross-page `cross_page` provider hints, they are currently only consumed under controlled conditions ("adjacent two pages + unique reading_order + layout_zone hits page-end/page-start reading boundary + sufficient text length")
- These items are marked as `provider_joined`, and subsequent rules will not re-consume them
- Parts without available provider hints still continue to use local rule concatenation
- `cross_page` provider hints that do not meet controlled conditions are retained in the payload but do not directly drive concatenation

The purpose of this approach is clear:

- New OCR models that already perform same-page concatenation do not need to be second-guessed by local rules
- Models that cannot yet concatenate continue to reuse existing rules
- If new models appear in the future that can stably provide cross-page continuation groups, only the hint consumption strategy needs to be extended, without injecting provider-private structures into the translation main chain

## Public Interface

```python
from services.translation.continuation import annotate_continuation_context
from services.translation.continuation import candidate_continuation_pairs
```
