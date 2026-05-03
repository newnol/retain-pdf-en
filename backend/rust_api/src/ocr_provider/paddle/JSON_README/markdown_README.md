# Markdown Layer Description

## 1. Layer Definition

`layoutParsingResults[*].markdown` is built on top of `prunedResult`, generating readable Markdown/HTML strings for quick human preview of OCR text, paragraph structure, and embedded resources. Each `layoutParsingResults` item can carry its own `markdown.text` (the entire page's Markdown content) and `markdown.images` (image assets referenced by `<img>` tags), so it is not a new OCR schema, but rather a "flattened, readable" presentation of information in `prunedResult`.

## 2. Field Structure

- `text`: A complete Markdown/HTML script. The actual content includes headings (e.g., `## 1. JSON Split Profile`), paragraphs, mixed English/Chinese text, inline formulas (`$ \lambda = 1.5 $`, `$ E = mc^{2} $`), and `<div>`/`<img>` tags — essentially a coherent narrative assembled from the page's text fragments. This string contains no coordinates or type markers; all layout/category information is discarded, leaving only order and format.
- `images`: A dictionary where keys are relative paths used in Markdown (e.g., `imgs/img_in_image_box_256_840_937_1091.jpg`) and values are directly accessible HTTP URLs (often with authorization signatures). You can treat it as the reference table for `<img>` tags in `text`: whenever `src="imgs/...jpg"` appears in Markdown, `images[key]` provides the actual image file location, facilitating embedded preview images in the rendering layer.

## 3. Relationship with `prunedResult`

`markdown` is not the raw OCR's structured output; it is a "soft format" view derived from `prunedResult`. `prunedResult` remains the canonical structure that upstream/downstream interfaces should trust, preserving page size, `parsing_res_list` (with `block_bbox`, `block_label`, `block_order`), layout/paragraph abstractions, and other metadata, while `markdown` simply strings the text content and image references into a readable document. The difference between the two means: if you need to locate a specific block, restore X/Y, or determine whether something is a heading or table, you must look at `prunedResult`, not rely on `markdown`.

## 4. Applicable and Prohibited Uses

- **Suitable for**: Quick visual confirmation of OCR output during debugging/troubleshooting; displaying page overview to frontend or document tools; using Markdown/HTML hierarchy in `text` (headings, `<img>`, formulas) as simple screenshot substitutes; verifying whether assets referenced by `images` are accessible.
- **Not suitable for**: Using as the adapter's main input; using as downstream schema (e.g., `document.v1`, normalized document); using to determine structure tags/type, paragraph boundaries, or table/figure relationships — these pieces of information in `markdown` only retain order, no longer containing original categories and coordinates.
- **Use with caution**: `markdown.images` is only a URL mapping and does not contain positioning information like `block_bbox`. If you need to reconstruct the region where an image is placed at a certain location, you still need to combine `prunedResult` + `outputImages` metadata.

## 5. Suggestions for Subsequent Adapter Integration

Newly integrated adapters or provider implementations should treat `prunedResult` (or `normalized_document`) as the main pipeline input, and `markdown.text`/`markdown.images` only as auxiliary debug views. The common flow is:

1. Use `parsing_res_list`, `block_label`, `block_bbox` and other fields in `prunedResult` to complete structured arrangement.
2. If manual confirmation of extraction results is needed, read `markdown.text` in a debug script to quickly check if headings, body text, and formulas are coherent.
3. `markdown.images` can be used for rendering preview or outputting images as `![alt](URL)` in markdown, but do not use it to determine image attribution or coordinates.

Maintaining this thread helps ensure the schema main chain does not deviate from specifications because of some "looks like a document" Markdown.
