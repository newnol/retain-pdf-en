# Pretext PoC Results

Date:

- 2026-04-07

Environment:

- Local static server: `python3 -m http.server 4173`
- Browser: `chromium --headless --disable-gpu --no-sandbox`
- Dependency installation: `npm install --registry=https://registry.npmmirror.com`

## Verified Pages

- `html/index.html`
- `html/pretext.html`

Both pages support URL parameter auto-run:

- `?autoload=1`
- `&sample=<sample_id>`
- `&autorun=1`

For example:

- `http://127.0.0.1:4173/html/index.html?autoload=1&sample=20260407033349-ffe2e4:p002-b0002&autorun=1`
- `http://127.0.0.1:4173/html/pretext.html?autoload=1&sample=20260407033349-ffe2e4:p002-b0002&autorun=1`

## First Browser-Side Comparison Result

Sample:

- `20260407033349-ffe2e4:p002-b0002`

Input parameters:

- Width: `447.45pt`
- Font size: `11.06pt`
- Line height: approximately `6.64pt`
  This uses the current page's approximation of "font size multiplied by Typst's `max_leading_em`," serving only as first-round PoC comparison input.

Results:

- DOM height: `53.16pt`
- Pretext height: `53.12pt`
- height diff: `0.04pt`
- DOM lineCount: `8`
- Pretext lineCount: `8`
- DOM maxLineWidth: `597pt`
- Pretext maxLineWidth: `442.03pt`

## Current Conclusions

Three things can be confirmed first:

1. `@chenglou/pretext` can be installed locally in this experiment directory and imported by the browser page.
2. On the same batch of `fixtures`, DOM and `pretext` block-level height and line count can be directly compared automatically.
3. At least on sample `p002-b0002`, `pretext` and DOM height and line count are very close.

At the same time, an important issue is exposed:

- The current DOM page reads `maxLineWidth` as `scrollWidth`, which reflects the scroll width of the entire block box, not necessarily the actual width of "the widest line of text."
- `pretext`'s `maxLineWidth` is calculated line by line as text width, so the two are not currently on the same basis.

This means the next step should prioritize unifying the "widest line" metric basis before expanding to more samples.

## Recommended Next Steps

- Change the DOM baseline page's width metric from `scrollWidth` to per-line basis, aligning with `pretext`.
- Run the current 5 samples through a full DOM / `pretext` comparison, recording height differences, line count differences, and widest line differences.
- Then introduce Typst comparison to determine whether DOM or `pretext` is closer to Typst results.
