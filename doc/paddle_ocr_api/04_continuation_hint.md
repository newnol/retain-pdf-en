# 04 Continuation Hint

## Goal

If Paddle itself already knows which blocks belong to the same paragraph, the adapter should map this information into the unified contract:

- `continuation_hint`

Do not let the translation layer directly read Paddle's `group_id`, `global_group_id`, or `block_order`.

## Current Fields

Current `continuation_hint` structure:

```json
{
  "source": "provider",
  "group_id": "provider-paddle-global-xxx",
  "role": "head",
  "scope": "cross_page",
  "reading_order": 0,
  "confidence": 0.98
}
```

Field descriptions:

- `source`
  Fixed to `provider` when written by the current provider
- `group_id`
  Stable ID for the continuation group
- `role`
  `single/head/middle/tail`
- `scope`
  `intra_page` or `cross_page`
- `reading_order`
  Order within the group
- `confidence`
  Provider's confidence in this group

## Current Paddle Mapping Rules

The current code is at:

- `backend/scripts/services/document_schema/provider_adapters/paddle/continuation.py`

Current rules:

1. Prefer `raw_global_group_id`
2. When no global group exists, fall back to `page_index + raw_group_id`
3. Multi-block groups without reliable `raw_block_order` do not generate continuation hints
4. Same-page groups are marked as `intra_page`
5. Cross-page groups are marked as `cross_page`

## Downstream Consumption Convention

Translation currently adopts provider-first:

1. Same-page `intra_page` hints are directly consumed first
2. Cross-page `cross_page` hints are only consumed in a controlled manner when safety conditions are met
3. When safety conditions are not met, hints are retained but do not directly trigger concatenation

That is:

- The adapter is responsible for "accurately expressing what the provider knows"
- Translation is responsible for "deciding when it is safe to trust the provider"

## What Adapter Developers Need to Watch

1. `group_id` only requires stability within the group, not permanent invariance across versions.
2. `reading_order` must be unique and monotonically increasing within the group.
3. If a particular Paddle version has unstable group information, it is better to not write `continuation_hint` at all than to write it incorrectly.
4. Do not fabricate cross-page continuation relationships to make a specific test case pass.
