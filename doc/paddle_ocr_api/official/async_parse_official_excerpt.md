# PaddleOCR-VL Official Service-Oriented Documentation Excerpt

Sources:

- GitHub official documentation:
  <https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.md>
- Current repository early excerpt:
  `backend/rust_api/src/ocr_provider/paddle/AsyncParse.md`

This excerpt only retains content directly relevant to the current repository's provider integration; it does not reproduce the entire official tutorial.

## 1. Official Response Contains Markdown

The official service-oriented example clearly demonstrates the following usage:

- Iterating through `result["layoutParsingResults"]`
- Reading `res["markdown"]["text"]`
- Reading `res["markdown"]["images"]`

That is, the Paddle official response not only has structured `prunedResult` but can also directly provide Markdown text and Markdown image mappings.

## 2. Key Response Structure

The structure most directly relevant to this repository's integration is:

```json
{
  "result": {
    "layoutParsingResults": [
      {
        "prunedResult": {},
        "markdown": {
          "text": "...",
          "images": {}
        },
        "outputImages": {},
        "inputImage": "..."
      }
    ]
  }
}
```

Field meanings:

- `prunedResult`: Structured page parsing result
- `markdown.text`: Page-level Markdown text
- `markdown.images`: Mapping of Markdown image relative paths to image content/URLs
- `outputImages`: Visualization or intermediate image results
- `inputImage`: Input page image

Special attention needed here:

- The keys in `markdown.images` are not "suggested values" but the actual relative paths referenced in the Markdown/HTML body text
- If the body text contains `<img src="imgs/xxx.jpg">`, then the key in `images` should be `imgs/xxx.jpg`
- Integrators must not arbitrarily rewrite this provider-returned relative path to conform to another directory convention; only minimal, reversible wrapping is allowed during the publishing phase

## 3. Request Parameters Directly Relevant to This Repository's Current Main Pipeline

- `restructurePages`
  Used for multi-page PDF restructuring; affects cross-page table and paragraph heading level recognition.
- `mergeTables`
  Cross-page table merging.
- `relevelTitles`
  Paragraph heading level recognition.
- `showFormulaNumber`
  Controls whether the Markdown includes formula numbers.
- `prettifyMarkdown`
  Controls whether to output beautified Markdown.
- `visualize`
  Controls whether to return image results.

## 4. Implications for Our System

The conclusion is straightforward:

1. `markdown_ready = false` can no longer be attributed to Paddle officially not supporting Markdown.
2. If the task raw has already obtained `markdown.text` / `markdown.images`, it should be exported as a job markdown artifact in our artifact layer.
3. The provider adapter / pipeline needs to clearly distinguish:
   - Structured document normalization
   - Markdown artifact persistence
   - Markdown image persistence
4. Markdown image paths should follow provider return values; if page prefixes are added for multi-page task conflict prevention, only this kind of outer scope wrapping can be done; the internal relative path pattern must not be hardcoded.

## 5. Update Principles

When continuing to supplement Paddle documentation in the future, prioritize this location:

- Official entry points
- Fields and parameters strongly related to the current repository
- Mapping to the current repository's artifact / normalized document / provider adapter

Do NOT copy the entire official deployment tutorial verbatim.
