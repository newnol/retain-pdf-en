# Paddle block_label First Version Mapping Table

This document is based on the actual enumeration results of `layoutParsingResults[*].prunedResult.parsing_res_list[*].block_label` from [json_full.json](/home/wxyhgk/tmp/Code/rust_api/src/ocr_provider/paddle/json_full.json), with the goal of providing a first stable mapping for the subsequent `Paddle -> document.v1` adapter.

## 1. block_label Values Observed in Current Samples

Labels enumerated from the current three-page sample are as follows:

| block_label | Count | Description |
| --- | ---: | --- |
| `text` | 25 | Normal body paragraphs |
| `paragraph_title` | 12 | Paragraph titles / section headings |
| `header` | 6 | Page headers |
| `footer` | 6 | Page footers |
| `figure_title` | 4 | Figure captions or table captions |
| `table` | 2 | Table body, content is HTML table |
| `image` | 1 | Image body, content is usually `<img>` HTML |
| `algorithm` | 1 | Code/algorithm block |
| `display_formula` | 1 | Display formula |
| `vision_footnote` | 1 | Visual footnote/table note/annotation |

## 2. Actual Sample Excerpts

### `text`
- Page 1 / block 4
  Large body text with mixed Chinese and English
- Page 1 / block 6
  Normal body text with inline formulas and explanations

Recommendation:
- Use directly as the main entry point for normalized body blocks.

### `paragraph_title`
- Page 1 / block 3
  `## 1. JSON Split Profile`
- Page 1 / block 5
  `### 1.1. Structure Overview`

Recommendation:
- Treat as heading-type blocks, do not merge into regular `text`.

### `header`
- `PaddleOCR JSON Split Research`
- `March 31, 2026 · Provider: Paddle`

Recommendation:
- Default keep as structural blocks, but translation main chain should usually skip.

### `footer`
- `Confidential Draft`
- `Page page.number / pages.count`

Recommendation:
- Default keep as structural blocks, translation main chain should also usually skip.

### `figure_title`
- Figure caption
- Table caption

Note:
- This label in Paddle samples simultaneously covers "figure captions" and "table captions"; it cannot be simply equated to `image_caption`.

### `table`
- Content is a complete HTML table string

Recommendation:
- First preserve original HTML content
- Later decide whether to further split cells into structured table schema

### `image`
- Content is usually `<img src=...>` fragment

Recommendation:
- Treat as the main block for image areas; do not use `block_content` as body text

### `algorithm`
- In current samples, these are code blocks/command-line blocks

Recommendation:
- First uniformly map to `code`
- If Paddle later has actual algorithm pseudocode, then decide whether to further split into `algorithm_block`

### `display_formula`
- Content is `$$ ... $$`

Recommendation:
- Directly map to `formula`
- Preserve original LaTeX/Math strings

### `vision_footnote`
- Current sample is `Table note: Values are illustrative and do not represent real benchmark conclusions.`

Recommendation:
- First treat uniformly as footnote/caption_note type
- This type of field often appears near figures/tables; adjacency relationship clues should be preserved

## 3. First Version normalized_document_v1 Mapping Recommendations

First provide a "conservative, stable" mapping, not aiming for perfection in one pass.

| Paddle block_label | normalized type | normalized sub_type | Notes |
| --- | --- | --- | --- |
| `text` | `text` | `body` | Main body text |
| `paragraph_title` | `text` | `heading` | Can be further refined by number/level later |
| `header` | `text` | `header` | Usually skip translation |
| `footer` | `text` | `footer` | Usually skip translation |
| `figure_title` | `text` | `caption` | First use unified caption, then distinguish figure/table titles via adjacent blocks |
| `table` | `table` | `table_html` | Preserve original HTML |
| `image` | `image` | `image_body` | Do not process as text logic |
| `algorithm` | `code` | `code_block` | First unify to code block |
| `display_formula` | `formula` | `display_formula` | Display formula |
| `vision_footnote` | `text` | `footnote` | Figure notes/table notes/footnotes first unified into this category |

## 4. Which Fields Need Additional Raw Trace Preservation

Recommend each normalized block preserve the following provider trace:

- `provider = "paddle"`
- `source_page_index`
- `source_block_index`
- `source_block_label`
- `source_block_id` (if available)
- `source_group_id` (if available)
- `source_bbox`
- `source_polygon`

Reasons:
- `figure_title` needs adjacency relationships to distinguish figure titles from table titles
- `vision_footnote` may later need to be further split into `table_footnote` / `image_footnote`
- `table` is currently an HTML string; if structured table splitting is done later, traceability to the original block is needed

## 5. Three Things Most Worth Doing First

1. First write a pure mapping function from `block_label -> normalized type/sub_type`
2. First conservatively map `figure_title` and `vision_footnote` to `caption/footnote`
3. Do not immediately deep-split `table` and `image`; first stably keep them as blocks

## 6. Engineering Conclusions from Current Samples

- Paddle's `figure_title` is clearly a mixed-class label; later it must be combined with adjacent block relationships to determine "figure title/table title".
- `table` and `image` `block_content` is more like "rich text or embedded fragments"; they cannot directly go through normal body text extraction logic.
- `algorithm` currently looks more like code blocks; do not open a separate complex branch for it.
- `display_formula` has a dedicated label, which is more direct than MinerU's approach and should be prioritized.

## 7. Suggested Follow-up Files

If starting to write the adapter next, directly add:

- `paddle/block_labels.py`
  Only handles label mapping and tag determination
- `paddle/adapter.py`
  Only handles `json_full -> document.v1`
- `paddle/trace.py`
  Only handles provider raw trace placement

This way when new labels are encountered later, only `block_labels.py` needs to be changed, without polluting the main adapter.
