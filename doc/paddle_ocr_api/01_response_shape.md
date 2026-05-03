# 01 Response Shape

## Top-Level Structure

The top-level fields that the current Paddle adapter depends on are mainly:

- `layoutParsingResults`
  Per-page parsing result list
- `dataInfo`
  Page size and other metadata
- `preprocessedImages`
  Preprocessed image list, optional

The current minimum recognition conditions are in:

- `backend/scripts/services/document_schema/provider_adapters/paddle/adapter.py`

## Page-Level Structure

For each page, the current adapter mainly reads:

- `prunedResult`
- `prunedResult.parsing_res_list`
- `prunedResult.layout_det_res.boxes`
- `markdown.text`
- `markdown.images`

Page size priority order:

1. `dataInfo.pages[i].width / height`
2. `prunedResult.width / height`
3. Defaults to `0`

## Block-Level Structure

The current block reader mainly reads these fields:

- `block_label`
- `block_bbox`
- `block_content`
- `block_polygon_points`
- `block_id`
- `group_id`
- `global_block_id`
- `global_group_id`
- `block_order`

Notes:

- `block_label` determines the main structural mapping
- `block_content` is the primary text source
- `group_id / global_group_id / block_order` currently mainly serve `continuation_hint`

## Current Page Construction Flow

The current page adapter flow is:

1. Read one page payload from `layoutParsingResults[page_index]`
2. Construct `PaddlePageContext`
3. Construct block specs one by one from `prunedResult.parsing_res_list`
4. Add page-level `metadata`
5. Pass to common builder to generate `document.v1`

Code entry points:

- `backend/scripts/services/document_schema/provider_adapters/paddle/payload_reader.py`
- `backend/scripts/services/document_schema/provider_adapters/paddle/page_reader.py`

## Documentation Maintenance Recommendations

If the Paddle API structure changes in the future, this file should be updated first:

1. Whether top-level fields changed
2. Whether page-level field paths changed
3. Whether block-level field paths changed
4. Which fields are no longer reliable
