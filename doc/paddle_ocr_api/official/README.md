# PaddleOCR Official Documentation Archive

This contains the PaddleOCR official resource entry points most relevant to the current repository integration, unified under `doc/` so they are no longer scattered across source directories.

## Official Sources

- PaddleOCR-VL official usage documentation:
  <https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.md>
- PaddleOCR-VL official online documentation:
  <https://www.paddleocr.ai/latest/version3.x/pipeline_usage/PaddleOCR-VL.html>

## Current Repository Focus Areas

The most critical items for this project are not the entire deployment tutorial, but the following official facts:

1. `layoutParsingResults[*].markdown.text` is the official Markdown body text returned.
2. `layoutParsingResults[*].markdown.images` is the mapping of images referenced in the Markdown.
3. Multi-page PDFs can do cross-page restructuring via `restructurePages`.
4. `showFormulaNumber` and `prettifyMarkdown` directly affect the Markdown output format.

## Repository Curated Excerpts

- Service-oriented API and async call excerpts:
  [async_parse_official_excerpt.md](./async_parse_official_excerpt.md)

## Usage Conventions

1. This preserves official documentation repository entry points and curated excerpts.
2. Integration implementation should follow official field semantics, not historical compatibility logic.
3. If official documentation updates, change this first, then change provider code and internal adaptation documentation.
