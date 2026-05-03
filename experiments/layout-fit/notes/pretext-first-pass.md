# Pretext First-Layer Evaluation

Evaluation targets:

- <https://github.com/chenglou/pretext>
- <https://github.com/chenglou/pretext/blob/main/STATUS.md>

Evaluation conclusion:

`pretext` is worth adding to the `layout-fit` candidate solution list, but in the first phase it should not be directly designated as the sole measurement engine. A more prudent positioning is: run in parallel with the native HTML/DOM measurer as a more controllable, cacheable, low-reflow block-level text layout measurement solution for small-sample comparison.

## Alignment with layout-fit

The most important current problem in `layout-fit` is block-level fitting: given text, font, target width/height, and candidate layout parameters, stably compute line count, height, and width overflow, then select the parameter set closest to the target box.

`pretext`'s core direction closely aligns with this problem:

- It decomposes text layout into programmable preparation and layout steps, rather than fully relying on DOM reflow.
- It exposes fundamental entry points like `prepare()` and `layout()`, suitable for "repeatedly measuring the same text with multiple parameter sets."
- It supports finer-grained interfaces like `layoutWithLines()`, `prepareWithSegments()`, and `measureLineStats()`, suitable for obtaining per-line results and line statistics.
- It emphasizes low-allocation, low-latency text layout paths, suitable for subsequent batch sample scanning or real-time parameter tuning.

## Directly Serviceable Capabilities

First-layer reusable capabilities are mainly measurement and layout, not complete PDF restoration:

- Calculate how text wraps given a width constraint.
- Obtain layout metrics like line count, line width, and overall height.
- Support repeatedly running layout under different parameters for font size, line height, and paragraph width scanning.
- Support finer text segment inputs, providing room for later processing of mixed Chinese-English, emphasis styles, or placeholder preservation.

## Problems That Cannot Be Directly Solved

These capabilities still require `layout-fit` to build its own higher-level abstraction:

- Extracting block-level samples from `document.v1.json` and `translated/page-XXX-deepseek.json`.
- Defining the `fixtures` sample format and experiment output format.
- Mapping measurement results to Typst font size, line height, and paragraph parameters.
- Performing page-level multi-block replay, collision detection, and mixed text-and-image restoration.
- Verifying actual errors under CJK, mixed Chinese-English, inline formulas, and OCR box coordinates.
- Comparing DOM, `pretext`, and Typst line count and height differences on the same batch of samples.

## Current Risks

The main risk is not whether `pretext` has value, but whether it is close enough to our final layout goals:

- Its layout model is not equivalent to Typst; its output cannot be directly used as Typst ground truth.
- Font measurement consistency may still be affected by browser, Canvas font loading, and platform font differences.
- If we need strong control over `letter-spacing`, paragraph spacing, Chinese punctuation compression, or formula placeholder width, additional adapters may be needed.
- If samples mainly come from OCR boxes and the goal is to match original PDF block sizes, ordinary text layout metrics may not be enough; OCR/Typst comparison scoring may need to be added separately.

## Recommended Positioning

The next step should not be a single-track HTML/DOM measurer, but rather a dual-track approach:

- Track A: HTML/DOM baseline measurer.
- Track B: `pretext` candidate measurer.

Both tracks use the same batch of `fixtures` and output the same set of metrics:

- `lineCount`
- `height`
- `maxLineWidth`
- `overflowX`
- `overflowY`
- `score`

The first PoC round only needs to answer one question: on 5 to 10 real text block samples, are `pretext`'s line count, height, and overflow judgment more stable and easier to perform parameter scanning on than the DOM baseline.

If PoC results are stable, then consider packaging `pretext` as a formal measurement adapter under `scripts/` or `html/`; if results differ too much from DOM/Typst, keep it only as a reference solution.

## Current Implementation Status

`layout-fit` already has a browser-side PoC entry point:

- `html/pretext.html`
- `package.json`

Dependencies can be installed normally through the Chinese mirror:

- `npm install --registry=https://registry.npmmirror.com`

Additionally, one important fact has been confirmed:

- `@chenglou/pretext` can be imported in the current Node environment.
- But actually executing `prepare()` / `prepareWithSegments()` requires `OffscreenCanvas` or a DOM canvas context.
- Therefore, the most reasonable current PoC location is the browser side, not a pure Node CLI script.
