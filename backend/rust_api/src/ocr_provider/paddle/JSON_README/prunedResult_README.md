# prunedResult Structure and normalized_document_v1 Value Mapping

This README is written for the output of `layoutParsingResults[*].prunedResult` in `rust_api/src/ocr_provider/paddle/json_full.json`, to help adapter implementers quickly locate key fields, understand semantics and normalization mapping approaches; it also indicates which fields are suitable for trace/debug retention.

## JSON Hierarchy

- `layoutParsingResults` represents the multiple sets of layout results that Paddle OCR may produce on the same input (usually several `split`/`merge` versions)
- Each entry contains `prunedResult` (our normalization starting point) and the source's `markdown`/`outputImages`/`inputImage` and other debug fragments
- `prunedResult` directly contains:
  - `page_count` (total pages)
  - `width`, `height` (canvas dimensions corresponding to this layout parsing, in px)
  - `model_settings` (switches used for this inference round, for reproduction/troubleshooting)
  - `parsing_res_list` (Paddle native block structure list)
  - `layout_det_res` (underlying layout detector's box output, for tracing to specific detection results)

## Key Field Descriptions

### `page_count` / `width` / `height`
- Directly provides document-level page count and canvas dimensions; recommend mapping to `document.page_count` and each page's default `page.width/page.height` in the normalized document for overflow/scaling decisions.

### `model_settings`
- Contains switch fields for this parsing round, field names and actual values are:
  - `use_doc_preprocessor`: Whether to use document preprocessing
  - `use_layout_detection`: Whether layout detector is enabled
  - `use_chart_recognition`: Whether to attempt chart recognition
  - `use_seal_recognition`: Whether seal recognition is enabled
  - `use_ocr_for_image_block`: Whether to re-OCR image blocks
  - `format_block_content`: Whether to format text content (e.g., trim)
  - `merge_layout_blocks`: Whether to merge adjacent blocks in layout
  - `markdown_ignore_labels`: Block labels to ignore during markdown generation, e.g., `number/footnote/header/...`
  - `return_layout_polygon_points`: Whether to attach polygon information to each block
- Recommend treating this structure as adapter trace metadata (written to the normalized document's `meta.ocr_settings` or similar field) for subsequent issue tracking or alignment with the Rust layer's `normalization_report`.

### `parsing_res_list`
- Core block list, the primary input for normalized_document. Each item's fields:
  - `block_label`: Paddle predicted label (e.g., `header/paragraph_title/text/table/figure_title/footer`), can be mapped to normalized block's `type`/`sub_type` or `tags`
  - `block_content`: Text content, directly fills normalized block's `text_content` or `lines` fields
  - `block_bbox`: `[x0,y0,x1,y1]`, corresponds to block's axis-aligned bounding box
  - `block_polygon_points`: Same as `block_bbox` but supports polygons (each point is `[x,y]`), suitable for normalized block's `polygon` field
  - `block_id`, `group_id`: Local block/group IDs, can be used to generate normalized block's `provider_id` or `group_id`
  - `global_block_id`, `global_group_id`: IDs with global offsets, unique across multiple layout versions/pages; recommend using as `meta.global_id` in normalized document for tracking
  - `block_order`: Paddle inferred reading order (some values are `null` in this example), can be used to fill `normalized_document.pages[].items[].order`
- Recommend adapter follows this approach:
  1. Partition `parsing_res_list` by `block_order` or `block_id` into pages (if `group_id` exists, can serve as `group` dimension for `Page.blocks`)
  2. Use `block_label` to distinguish categories (`header`/`paragraph_title`/`text` etc.), determine normalized block's `type/sub_type` (e.g., `text` for core content, `paragraph_title` can be treated as `title` type)
  3. `block_content` directly assigned as normalized block's `text`, and preserve `block_polygon_points` as `geometry.polygon`
  4. `block_bbox` also fills normalized block's `bounding_box` for frontend/rendering reuse

### `layout_det_res`
- Contains layout detector raw boxes, current structure is:
  - `boxes`: list of objects
  - Each box has `cls_id` (classifier ID), `label` (category name), `score` (confidence), `coordinate` (`[x0,y0,x1,y1]`), `order` (predicted reading order, can be `null`), `polygon_points`
- Recommend adapter treat `layout_det_res` as raw detection trace:
  - Can preserve `boxes` in normalized document's `meta.raw_traces.layout_det_res` for label and score traceability
  - `coordinate` / `polygon_points` correspond to `parsing_res_list` geometry, can be used to verify consistency between the two (e.g., differences when `merge_layout_blocks` is enabled)
  - `score` is suitable for writing to trace rather than normalized block's core fields, maintaining `document.normalization_trace` for troubleshooting missed/incorrect detections

## Adaptation Recommendations

1. Adapter first reads `page_count`/`width`/`height` as normalized document's basic page information; `layout_det_res.boxes` can simultaneously provide `page_count` upstream/downstream consistency verification.
2. Each `parsing_res_list` item generates a normalized block; `block_label` determines `type` (e.g., `table`, `image`, `text`), `block_content` becomes main text content, `block_order`/`group_id` used to build block reading order/grouping.
3. All polygon/bbox/cursor related fields (`block_bbox` + `block_polygon_points` + `layout_det_res.boxes coordinate/polygon_points`) should be simultaneously attached to normalized block's geometry and trace, avoiding coordinate understanding divergence across different entry points.
4. `model_settings` and `layout_det_res` directly write a debug trace (e.g., `normalized_document.meta.provider_trace.paddle.pruned_result`) for field reproduction in `normalization_report`; only `parsing_res_list`'s `block_content`/`label`/`geometry` need to actually map to normalized document main chain.
5. If going with `normalized_document_v1` schema later, recommend preserving original `block_id/global_block_id` and `group_id/global_group_id` in `blocks[].meta` for alignment with different providers' IDs.

## Trace-Retained Fields

- `model_settings`: Preserve completely for alignment with experiment parameters and `normalization_summary`
- `layout_det_res.boxes`: As `debug.traces.layout_detector`, preserve `label/score/coordinate/order`
- `block_polygon_points` and `block_id` in `parsing_res_list` are the foundation for subsequent block location during troubleshooting
- Others like `global_block_id/global_group_id` can be directly written to `blocks[].meta.source_ids`

Maintaining these conventions allows the adapter to generate normalized documents without losing Paddle's fine-grained semantics, while also fully reproducing the detection process in traces for subsequent rendering, debugging, and schema regression.
