# Layout-Fit Cross-Page / Cross-Column Problem Description

## Problem Description

In the PDF overlay preview of `layout-fit/html/pretext.html`, although individual box fitting looks close, cross-page and cross-column paragraphs exhibit obvious errors:

- The bottom of page 3 and the beginning of page 4 were originally the same paragraph, but were treated as two independent blocks and re-typeset.
- Some blocks display the English original text instead of the Chinese translation.
- The auto-fitted height, line count, and line-break results look "close," but are actually systematic deviations.

## Root Cause

This problem is not a single cause, but several layers of errors stacked together:

### 1. Mistaking Cross-Page Continuation Paragraphs as Independent Blocks

The upstream translation and Typst split a cross-page paragraph into two items for processing convenience.

For example:

- `p003-b0005 -> p004-b0000`
- `p005-b0005 -> p006-b0000`
- `p007-b0004 -> p008-b0000`
- `p009-b0006 -> p010-b0000`

In the Typst overlay, these are also two independent `pX_item_*`, not a naturally continuous flowing object.

But the old version of the preview still treated them as "one sample = one independent text box," so:

- The end of the previous page only laid out the first half
- The beginning of the next page started typesetting from its own text again

This causes cross-page paragraphs to fail to properly continue.

### 2. Some Continuation Blocks in Translation JSON Have No Translation

For example:

- `p003-b0005`
- `p004-b0000`

In `translated/page-003-deepseek.json` and `translated/page-004-deepseek.json`, the `translated_text` for both blocks is an empty string.

Therefore, the old logic falls back to `source_text`, and the page displays English original text.

### 3. Mixed Use of `pretext` Measurement Units and PDF Coordinate Units

`pretext`'s measurements are based on browser pixels, while PDF target boxes are in `pt`. The old implementation directly fed PDF `pt` width/height to `pretext` and then used the results as `pt` for the overlay and scoring, causing:

- Unstable line breaks
- Line height and height scoring deviations
- Appearance of "fitting doesn't look right"

## Solutions

### 1. Restore Cross-Page Blocks to Flow Groups

Cross-page continuation detection was added in [extract_block_samples.py](/home/wxyhgk/tmp/Code/experiments/layout-fit/scripts/extract_block_samples.py):

- Sequentially scan OCR text blocks
- If the previous block ends mid-English-word, and the next block starts with lowercase or continuation style, and they are adjacent across pages
- Mark them as the same `flow`

Then write `flow` information into the fixture:

- `group_id`
- `index`
- `count`
- `prev_block_id`
- `next_block_id`
- `block_ids`

This way the frontend no longer treats these blocks as independent of each other.

### 2. Frontend Changed to Multi-Box Streaming Instead of Single-Box Independent Fitting

In [pretext.html](/home/wxyhgk/tmp/Code/experiments/layout-fit/html/pretext.html):

- For multiple boxes belonging to the same `flow`, first concatenate the text into a continuous paragraph
- Use `pretext.layoutNextLine()` to consume lines box by box in order
- Remaining content that doesn't fit in the previous box continues flowing to the next box

This step fixes the fundamental cross-page, cross-column issue.

### 3. Fall Back to Typst Markdown Text When Translation Is Missing

In the same extraction script, parsing of `*_md` from the Typst overlay was added.

If a block has:

- `translated_text` is empty
- But the corresponding `markdown_text` exists in Typst

Then Typst's Chinese markdown is used as the fallback source for `translated_text / fit_text`.

This step fixes the issue of English text appearing at the bottom of page 3 and beginning of page 4.

### 4. Unify `pretext` and PDF Unit Systems

The frontend fitting was changed to:

- First convert font size, width, and line height to pixels based on the PDF page image pixel density
- Use `pretext` to typeset in that pixel coordinate system
- Then convert the results back to PDF `pt` for scoring and overlay rendering

This way line breaks and the PDF overlay are finally in the same coordinate system.

## Current Effect

After the fix:

- The bottom of page 3 and the beginning of page 4 display Chinese
- They no longer each start from the beginning, but flow continuously as the same paragraph
- The preview layer can now recognize and handle multiple cross-page continuations

Identified cross-page flows include:

- `p003-b0005 -> p004-b0000`
- `p005-b0005 -> p006-b0000`
- `p007-b0004 -> p008-b0000`
- `p009-b0006 -> p010-b0000`

## Lessons Learned

These kinds of problems cannot be solved just by tuning "font size, line height, and justification."

If the upstream translation/typography breaks paragraphs apart for engineering convenience, the preview layer must restore the "paragraph flow" semantics; otherwise, no matter how `pretext` is tuned, structural errors will appear in cross-page and cross-column scenarios.
