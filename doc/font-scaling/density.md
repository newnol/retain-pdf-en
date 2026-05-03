# How Is Density Actually Determined?

If you imagine a text box as a cardboard box, then "density" is really answering one question:

**Based on the current font size and line spacing, how does this translated content fit in the box — loose, just right, or already overloaded?**

This question seems intuitive, but when it comes to implementing it in code, you usually can't rely on a single metric. Because "how cramped it is" has at least two layers of meaning:

- Whether the content itself has gotten longer
- Whether the box itself has the capacity to hold that content

So in the current implementation, density is not a single constant, but is determined by several groups of functions working together.

---

## 1. Let's Start with the Conclusion: We're Actually Looking at Two Types of Density

In the current implementation, the most relevant metrics for "density" are not a single function, but two lines:

1. **Length Density**
   - Looks at whether the translated content has "expanded" relative to the original
   - Corresponding function: `translation_density_ratio(...)`

2. **Layout Density**
   - Looks at whether the content would appear too cramped in the box at the current font size and line spacing
   - Corresponding function: `layout_density_ratio(...)`

In [fit.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/fit.py), these two metrics are used together for judgment:

```python
length_density_ratio = translation_density_ratio(item, protected_text)
layout_density = layout_density_ratio(box, protected_text, font_size_pt=font_size_pt, line_step_pt=line_step)
is_dense_block = length_density_ratio >= COMPACT_TRIGGER_RATIO or layout_density >= LAYOUT_COMPACT_TRIGGER_RATIO
```

In other words, the system doesn't just ask "has the translation gotten longer" or "is the box nearly full" — it asks both.

---

## 2. Layer One: Has the Content Obviously Expanded

The most straightforward idea is: if the original text has only a few words, but the translation becomes a long paragraph, it's probably harder to lay out.

This layer is handled by `translation_density_ratio(...)` in [text_common.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/text_common.py):

```python
def translation_density_ratio(item: dict, protected_text: str) -> float:
    source_words = source_word_count(item)
    if source_words <= 0:
        return 0.0
    zh_chars = translated_zh_char_count(protected_text)
    if zh_chars <= 0:
        return 0.0
    return zh_chars / source_words
```

What this function does is very simple:

- First count approximately how many English words the original has: `source_word_count(item)`
- Then count how many Chinese characters the translation has: `translated_zh_char_count(protected_text)`
- Use "Chinese character count / original word count" to get a ratio

Its purpose is not "precise typesetting calculation" but a quick assessment:

**After translation, is this segment more likely to become visually crowded compared to the original?**

### Example

Suppose an original text block:

- Original word count: 20
- Translated Chinese characters: 18

Then:

`translation_density_ratio = 18 / 20 = 0.9`

This indicates it's already at a tight edge.

If another block:

- Original word count: 20
- Translated Chinese characters: 24

Then:

`translation_density_ratio = 24 / 20 = 1.2`

This type of block is "obviously expanded" and usually needs to be treated more conservatively going forward.

The current thresholds are also defined in the same file:

- `COMPACT_TRIGGER_RATIO = 0.9`
- `HEAVY_COMPACT_RATIO = 1.0`

In plain terms:

- `>= 0.9`: Starting to get tight
- `>= 1.0`: Already a heavily compact block

---

## 3. Layer Two: At the Current Font Size, Will This Box Really Be Filled Up

The previous layer can only tell "whether the content has gotten longer," but it doesn't look at the box.

Two paragraphs with the same `ratio = 1.0`:

- Placed in a body text box 400pt wide, may be perfectly fine
- Placed in a caption box 160pt wide, may immediately overflow

So the second layer must look at "the box's capacity."

This step is handled by `layout_density_ratio(...)` in [text_common.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/text_common.py):

```python
def layout_density_ratio(
    inner: list[float],
    protected_text: str,
    *,
    font_size_pt: float,
    line_step_pt: float,
) -> float:
    width = max(8.0, inner[2] - inner[0])
    height = max(8.0, inner[3] - inner[1])
    zh_chars = translated_zh_char_count(protected_text)
    approx_char_width = max(font_size_pt * 0.92, 1.0)
    chars_per_line = max(4.0, width / approx_char_width)
    required_lines = max(1.0, zh_chars / chars_per_line)
    occupied_height = required_lines * line_step_pt
    return occupied_height / height
```

The logic of this function can be described in plain language:

1. First look at how wide and tall the box is
2. Estimate how wide a character approximately is at the current font size
3. Calculate roughly how many characters can fit per line
4. Then estimate how many lines the translated text will need
5. Finally calculate how much height those lines will occupy
6. Then divide the occupied height by the box height

The result is a very intuitive ratio:

- `< 1.0`: Theoretically still fits
- `≈ 1.0`: Already very tight
- `> 1.0`: Theoretically already overflowing

### Example

Suppose a box:

- Width: 180pt
- Height: 90pt
- Current font size: 9pt
- Current line spacing: 12pt
- Translated Chinese characters: 72

Rough estimate:

- Character width is approximately `9 × 0.92 = 8.28pt`
- Each line can fit approximately `180 / 8.28 ≈ 21.7` characters
- 72 characters need approximately `72 / 21.7 ≈ 3.3` lines
- Occupied height is approximately `3.3 × 12 = 39.6pt`
- Layout density is approximately `39.6 / 90 = 0.44`

This shows that this block is not actually cramped.

If the same content is placed in another box:

- Width: 110pt
- Height: 48pt

Then:

- Each line can only fit approximately `110 / 8.28 ≈ 13.3` characters
- 72 characters need `72 / 13.3 ≈ 5.4` lines
- Occupied height is approximately `5.4 × 12 = 64.8pt`
- Layout density is approximately `64.8 / 48 = 1.35`

This is a typical high-density block — the current font size is definitely too large.

---

## 4. Layer Three: How Is the Box's "True Capacity" Actually Calculated

The `layout_density_ratio(...)` above is a quick estimate — it's lightweight and suitable for initial density assessment.

The calculation that more closely approximates "how much content this box can actually hold" is in [capacity.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/capacity.py).

The most core function is `box_capacity_units(...)`:

```python
def box_capacity_units(
    inner: list[float],
    font_size_pt: float,
    leading_em: float,
    visual_lines: int | None = None,
) -> float:
    width = max(8.0, inner[2] - inner[0])
    height = max(8.0, inner[3] - inner[1])
    line_step = max(font_size_pt * 1.02, font_size_pt * (1.0 + leading_em))
    lines = max(1, int(height / line_step))
    if visual_lines and visual_lines > 1:
        lines = min(lines, max(1, visual_lines + 1))
    chars_per_line = max(4.0, width / max(font_size_pt * 0.92, 1.0))
    return lines * chars_per_line * 0.98
```

It does three things:

1. Calculate how many lines can fit based on font size and line spacing
2. Estimate how much content can fit per line based on box width
3. Multiply the two to get the total capacity of the box

There's one very important detail here:

`visual_lines`

This means it doesn't fully trust "how many lines the box height can hold," but instead references the OCR / layout structure's estimate of the original block's visual line count, to avoid overestimating the capacity.

---

## 5. Layer Four: Content Demand Is Not Simply Counting Characters

If capacity is calculated, then how is "demand" calculated?

This is handled by `text_demand_units(...)` in the same file:

```python
def text_demand_units(protected_text: str, formula_map: list[dict]) -> float:
    formula_lookup = {entry["placeholder"]: entry["formula_text"] for entry in formula_map}
    return sum(token_units(token, formula_lookup) for token in tokenize_protected_text(protected_text))
```

What it means:

- First tokenize the text
- Regular text counts as regular units
- Formula placeholders are not counted as 1 character each, but rather calculated in a way that more closely approximates true visual cost

This step is important because if you just look at character count, you'll underestimate the pressure from formulas.

### Example

The following two text segments may have similar character counts:

1. `This method significantly improves material performance.`
2. `This method significantly improves material performance under [[FORMULA_1]] conditions.`

But the second segment, because it contains a formula, actually has more typesetting pressure.

So the system won't treat them as having the same demand, but instead gives formulas a higher visual cost through `token_units(...)`.

---

## 6. Layer Five: Why Introduce Visual Line Count

There's a problem that's easy to overlook:

**Sometimes the "line count" given by OCR is unreliable.**

For example, a paragraph that was actually 4 lines may have been glued into 1 line by OCR. If you only look at the raw `lines`, you'll seriously overestimate the usable typesetting space in this box.

So [measurement.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/typography/measurement.py) has a dedicated set of functions to correct this:

- `plain_text_chars_per_line(...)`
- `_predicted_wrapped_line_count(...)`
- `visual_line_count(...)`
- `is_tall_single_line_glue(...)`

The idea behind `visual_line_count(...)` is:

- First check how many lines OCR reports
- Then based on text length, box width, and single-line character capacity, estimate "if normally wrapped, how many lines should there be"
- If the predicted line count is significantly higher than the OCR line count, use the more conservative count

The purpose of this step is not to calculate font size, but to prevent density assessment from being skewed by false data.

### A Typical Example

Suppose a block:

- OCR only reports 1 line
- But the box is tall, and the text length is 140 characters
- Geometrically, one line clearly cannot hold that much content

At this point, `visual_line_count(...)` would determine:

"This is very likely not 1 line of body text, but rather OCR has glued a multi-line paragraph into a single line."

So the system would use the predicted value to correct subsequent capacity calculations. This way, the calculated density more closely approximates reality.

---

## 7. How Density Ultimately Affects Font Size

The functions above don't directly produce the "final font size." Their role is more like providing judgment criteria for the typesetter.

The most direct application is in [fit.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/fit.py)'s `fit_translated_block_metrics(...)`:

```python
capacity = box_capacity_units(box, font_size_pt, leading_em, visual_lines=visual_lines)
if capacity <= 0 or (demand <= capacity * 0.96 and layout_density < LAYOUT_DENSITY_SAFE_MAX):
    return font_size_pt, leading_em
```

The logic here is critical:

- If demand is not approaching capacity
- And layout density is not too high

Then the current font size can be preserved.

Conversely, if:

- `demand > capacity`
- Or `layout_density` is already too high

Then the process of reducing font size and tightening line spacing begins.

In other words, density doesn't directly output "9.2pt" or "8.8pt" — it decides:

- Whether to shrink
- How many steps to shrink
- Whether to only shrink font size, or also compress line spacing

---

## 8. You Can Think of It as a Very Simple Judgment Chain

If you compress all the functions into one sentence, it's roughly this chain:

1. **First check if the translated content has obviously gotten longer**
   - `translation_density_ratio(...)`

2. **Then check how much height the content would occupy in this box at the current font size**
   - `layout_density_ratio(...)`

3. **More rigorously estimate how many units of content this box can truly hold**
   - `box_capacity_units(...)`

4. **At the same time, don't fully trust the OCR line count — use `visual_line_count(...)` for correction**

5. **Finally, use "demand vs capacity" to decide whether to reduce font size**
   - `text_demand_units(...)` vs `box_capacity_units(...)`

---

## 9. A Complete Example

Suppose a translation block has these conditions:

- Box width: 145pt
- Box height: 62pt
- Initial font size: 9.4pt
- Line spacing: 0.58em
- Original word count: 18
- Translated Chinese characters: 22
- Contains 2 formulas

The system would evaluate it like this:

### Step 1: Has the Content Expanded

`translation_density_ratio = 22 / 18 ≈ 1.22`

This is already a heavily compact block.

### Step 2: Is the Layout Too Tight at the Current Font Size

Estimated by `layout_density_ratio(...)`:

- This box is relatively narrow
- At 9.4pt, the number of characters per line is limited
- With formulas, the real wrapping pressure is even greater

The calculated layout density may be close to or even exceed `1.0`

### Step 3: Then Look at Capacity and Demand

- `box_capacity_units(...)` will find the box's total capacity is relatively small
- `text_demand_units(...)` will increase the demand due to formulas

The conclusion becomes:

**This is a high-density block, and the current font size is not safe.**

### Step 4: Enter Shrinkage

`fit_translated_block_metrics(...)` will start trying:

- First reduce the font size by a small amount each time
- If still not enough, compress the leading a bit
- Keep trying until demand no longer clearly exceeds capacity

This is the complete process of "how density assessment actually affects font size."

---

## 10. Final Summary

The so-called "box density" is essentially not asking:

"How many characters are in this box?"

But rather:

**At the current font size and line spacing, how much gap remains between this box's available capacity and the actual demand of this translated content?**

In the current implementation, this question is answered jointly by the following groups of functions:

- Page and original line information correction:
  - [measurement.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/typography/measurement.py)
- Text length and layout density estimation:
  - [text_common.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/text_common.py)
- Capacity and demand calculation:
  - [capacity.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/capacity.py)
- Final font size shrinkage decision:
  - [fit.py](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/layout/payload/fit.py)

If you keep tracing back, "why did the font size end up smaller," the answer usually comes back to this:

**Because the content demand of the current block has approached or exceeded the capacity of the current box at this font size.**