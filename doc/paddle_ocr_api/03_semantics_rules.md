# 03 Semantics Rules

## General Principle

When adapting Paddle, first determine which category a field belongs to:

1. Stable structure
2. Stable semantics
3. Raw trace for troubleshooting only

## What Goes into the Core Structure Layer

Only content that is likely to remain stable across providers is allowed into the core structure layer:

- `type`
- `sub_type`
- `bbox`
- `text`
- `lines`
- `segments`
- `tags`
- `derived`
- `continuation_hint`

## What Goes into `tags`

`tags` is suitable for lightweight, composable structural hints that downstream may use.

Current Paddle examples in use:

- `title`
- `abstract`
- `heading`
- `caption`
- `image_caption`
- `table_caption`
- `reference_zone`
- `skip_translation`
- `image`
- `table`
- `formula`

## What Goes into `derived`

`derived` is suitable for stronger semantic conclusions, with attribution of who made the conclusion.

Current format:

```json
{
  "role": "title",
  "by": "provider_rule",
  "confidence": 0.98
}
```

Examples suitable for `derived`:

- title
- abstract
- reference_entry
- formula_number
- header/footer
- caption/footnote and similar roles that the provider has clearly identified

## What Stays Only in `metadata/source`

Paddle private fields should by default remain in the trace layer first:

- `raw_group_id`
- `raw_global_group_id`
- `raw_global_block_id`
- `raw_block_order`
- `raw_polygon`
- `layout_det_*`
- `model_settings`
- `markdown.images`

Only when multiple providers stably produce the same data and downstream truly needs it should promotion be considered.

## Current Trace Layering

Current Paddle trace layering recommendations:

1. Core structure layer
2. Common trace layer
3. Provider raw trace layer

Where:

- `content_format / asset_* / markdown_match_*` lean more toward "common trace layer"
- `layout_det_* / model_settings / original group id` lean more toward "provider raw trace layer"

## Rule Change Requirements

If changes are made to `block_label -> type/sub_type/tags/derived`, all of the following must be updated simultaneously:

1. This directory's documentation
2. Related fixtures
3. Regression check
4. If necessary, translation extractor smoke test
