# Rendering Notes

`scripts/services/rendering` is responsible for turning already-translated page data into the final PDF.

This module is not responsible for translation or OCR parsing — only for "how to render, how to lay out, and how to output."

## Stage Boundaries

The formal input and output of the Rendering stage are fixed as:

- Input:
  Source PDF, translation artifacts, rendering parameters
- Output:
  Final PDF, along with necessary overlay/typst/compressed intermediate artifacts

Explicitly NOT responsible for:

- Not directly consuming provider raw OCR JSON
- Not responsible for normalizing raw OCR into `document.v1.json`
- Not responsible for sending requests to translation models or generating translated text

Current stable handoff points:

- The rendering main pipeline only accepts the input set of "source PDF + translation artifacts"
- The rendering stage reads `translation-manifest.json` by default; old translation directories without a manifest no longer support direct rendering
- The Render-only call protocol is fixed as: `source_pdf_path + translations_dir` or `source_pdf_path + translation_manifest_path`
- The Render-only entry point already supports `job_root/specs/render.spec.json` (`render.stage.v1`)
- If the input doesn't satisfy the protocol, the entry point uniformly throws `Render-only input error` rather than producing vague errors in later Typst/PDF stages
- If you suspect OCR structure issues, first go back to `document.v1.json` / `document.v1.report.json` to investigate
- If you suspect translation content or terminology strategy issues, first go back to the translation payload rather than patching translation logic in the rendering layer
- API credentials are not written into the render stage spec; the spec uses `credential_ref`, with the runtime environment injecting the real keys

## Current Directory Structure

```text
scripts/services/rendering/
  __init__.py
  README.md
  api/
  background/
  compress/
  core/
  formula/
  layout/
    payload/
    typography/
  redaction/
  typst/
```

## Main Rendering Path

The current main path can be summarized as:

`translation JSON -> layout/payload -> typst -> PDF`

The upper layer typically calls this module's capabilities through [render_stage.py](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/render_stage.py).

Input boundaries:

- The rendering main pipeline consumes translated page payloads and the source PDF
- The current per-page translation payload and `translation-manifest.json` are the default deliverables from upstream; the rendering layer only reads them and is not responsible for defining OCR/translation stage protocols
- If upstream only wants to re-run rendering, it can explicitly pass `translation_manifest_path` without relying on fixed directory scanning
- OCR provider raw JSON should not flow directly into this layer
- If upstream OCR structure has issues, first go back to the `document.v1.json` / `document.v1.report.json` layer to investigate, rather than adding provider-specific workarounds in the rendering layer

## Module Breakdown

- `api/`
  Internal stable entry points.
- `layout/payload/`
  Translates translated OCR payloads into renderable blocks.
- `layout/typography/`
  Typography measurement and geometry utility layer.
- `redaction/`
  Directly operates on PDF page objects; responsible for text deletion, background covering, and write-back.
- `typst/`
  Responsible for turning render blocks into Typst source code and compiling into PDF.
- `formula/`
  Formula normalization, formula bad-case library, formula text assembly.
- `background/`
  Local background reconstruction for large background image pages.
- `compress/`
  PDF image-based compression.
- `core/`
  Shared data structures for the rendering layer.

## Recommended Entry Points

- [render_stage.py](/home/wxyhgk/tmp/Code/backend/scripts/runtime/pipeline/render_stage.py)
- [services/rendering/api](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/api)

## Formula Regression

If you add a new formula normalization rule, add the bad example directly to
the parameterized regression test in
[`devtools/tests/translation/test_formula_math_markers.py`](/home/wxyhgk/tmp/Code/backend/scripts/devtools/tests/translation/test_formula_math_markers.py).

## Collaboration Rules

If the rendering module is maintained by a separate person, this module is only responsible for "reading translation artifacts and generating the final PDF."

- You may modify overlay, Typst, background processing, compression, red box erasure, and layout fill-back here
- Do not add OCR provider-specific workarounds here, nor add translation requests or terminology replacement logic here
- The formal input boundary is `source_pdf_path + translations_dir/translation_manifest_path`
- If you modify the rendering input protocol, manifest reading method, or final artifact naming, you must synchronously update `runtime/pipeline`, calling entry points, README, and tests
- When encountering upstream OCR or translation issues, preferentially return the issue to the corresponding module to fix; do not stack cross-layer patches in the rendering layer
