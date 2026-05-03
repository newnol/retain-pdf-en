# Why Font Size in PDFs Cannot Be Fixed: A "Page-Adaptive" Font Size Algorithm

Many people's first instinct when doing "layout-preserving translation" is to think of a very simple approach:

"The original is about 10pt, so after translation I'll just uniformly use 10pt too, right?"

This idea seems reasonable, but as soon as you actually try it with a few pages of a paper, you'll quickly discover the problem. Because the text blocks in a PDF are not all identical white sheets of paper. Some are in two-column layouts, some are in figure captions, some boxes are wide, some are narrow; some original sentences have only a dozen words, while some become noticeably longer when translated to Chinese.

So, **font size cannot be a global constant — it must be "a quantity that varies along with the page and block."**

This article doesn't cover specific code, only the reasoning behind it:

- Why font size cannot be fixed
- What exactly we base our judgment on for whether font size should increase or decrease
- How a reasonable dynamic algorithm should make judgments step by step
- Use specific examples to illustrate this judgment process

---

## 1. Before Rushing to Calculate Font Size, First Clarify What the Problem Really Is

Translated text needs to be placed back into the original boxes. Essentially, this is doing one thing:

**In a limited rectangular space, place text that is as natural as possible and as close as possible to the original's visual style.**

There are actually three simultaneous goals:

1. The text must fit
2. It cannot look particularly jarring
3. It should look cohesive on the same page

If you only pursue "fitting," the simplest method is to shrink all text very small. Of course it won't overflow, but the page will look ugly.

If you only pursue "looking big," then it's easy to overflow the box, overlap, push against the bottom, or crowd other elements.

So this problem is not "find a fixed font size" but:

**Dynamically find a balance between "fitting" and "looking like the original."**

---

## 2. The First Basis for Judgment: How Dense or Loose Is This Page Itself

Let's look at an intuitive example.

### Example 1: Both Are Body Text Pages, But Page Density Is Completely Different

Suppose there are two pages of a paper:

- Page A: Dense two-column body text, tight line spacing, almost no whitespace
- Page B: Only a few short paragraphs, with a large figure in the middle, the page is very empty

If both pages are forced to use the same font size:

- Page A easily can't fit, translation overflows more easily
- Page B would look too small, empty and hollow

So the first judgment must be:

**First determine whether this page overall is a "dense page" or a "loose page."**

This step doesn't need to be particularly complex. The core is to observe the blocks on the page that "look like body text" and see their typical rhythm:

- Average line height
- How tight lines are to each other
- Approximately how many characters fit at the same width
- Whether most body text blocks on the page look compact or spread out

You can understand it as:

**First find a "page-level base font size" for each page.**

This base is not the final result, but it serves as an anchor. Every subsequent block will be adjusted around this anchor.

---

## 3. The Second Basis: How Big Is This Block's Box, Especially "Width" and "Height"

Having a page-level base is not enough, because on the same page, different blocks have completely different environments.

### Example 2: Two Boxes on the Same Page

Suppose there are two text blocks on the same page:

- Block A: width 420, height 110
- Block B: width 180, height 110

They have the same height, but the width differs by more than double.

If both blocks use the same font size:

- A has less line-wrapping pressure
- B has very high line-wrapping pressure

Especially after translation to Chinese, once sentences are slightly longer, text in narrow boxes quickly accumulates into more lines.

So the second judgment is:

**The same font size has completely different effects in wide and narrow boxes.**

Therefore, the algorithm must focus on two geometric quantities:

- Box width: determines approximately how many characters fit per line
- Box height: determines how many lines can be tolerated at most

Width mainly affects "whether there will be excessive line wrapping," and height mainly affects "whether it can still fit after wrapping."

---

## 4. The Third Basis: How Much Has the Translated Text "Expanded" Compared to the Original

Just looking at the box is not enough — you also need to look at the content itself.

### Example 3: An English Sentence That Obviously Gets Longer After Translation

Original:

`The catalyst significantly improves conversion efficiency under mild conditions.`

Translation:

`This catalyst can significantly improve conversion efficiency under milder reaction conditions.`

Some language pairs don't change much in length, but some blocks obviously get longer, especially when:

- English abbreviations are expanded
- Technical phrases become longer when translated to Chinese
- Text around formula placeholders needs to be reorganized

At this point, what really matters is not "what was the original font size" but:

**How much does the translated content's density exceed this box's capacity?**

So a very practical judgment method is:

1. First estimate how many "text units" this box can hold at the current font size
2. Then estimate how many "text units of space" the translated content needs
3. Subtract the two to know whether it's currently loose or cramped

The "text units" here don't have to be strict character counts — they can be something closer to visual reality, such as:

- Estimated visual line count after wrapping
- Character count after removing whitespace
- Different weights for formulas, punctuation, and long words

The core idea is not a specific formula, but:

**Use "content demand" to compare against "box capacity."**

---

## 5. The Real Core: Font Size Is Not Calculated in One Shot, But Determined in Three Layers

A more stable dynamic algorithm usually doesn't "make a snap judgment in one step" but works in three layers.

### Layer 1: The Page First Provides a Base Value

Based on the overall body text density of the page, give this page a rough base.

For example:

- Dense page: base 9.2pt
- Normal page: base 9.8pt
- Loose page: base 10.4pt

This step resolves "whether this page overall should lean tight or loose."

### Layer 2: Each Block Adjusts Based on Its Own Box and Content

Then look at this block:

- Is the box particularly narrow
- Is the height very limited
- Is the translation obviously longer
- Are there many formulas with poor wrapping space

If the answer leans toward "cramped," adjust slightly below the page base.
If the answer leans toward "loose," allow adjusting slightly above.

This step resolves "compared to the page average, is this block harder or easier to fit."

### Layer 3: Right Before Actual Rendering, Do One Final Box-Fit Check

Even if the first two layers of judgment are very reasonable, errors can still occur. Because actual rendering encounters many unforeseen things:

- Certain glyphs are wider than expected
- The actual width of mixed Chinese-English text differs from estimates
- Inline formulas widen a line
- Punctuation distribution causes actual wrapping to be worse than estimated

So a truly mature solution always has a final step:

**Actually test with the current font size — if it still overflows, scale down proportionally.**

This step can be understood as a last safety net.

---

## 6. What the Algorithm Is Actually Looking At: Think of It as 5 Judgment Signals

If you compress the above reasoning into the most core judgment bases, they're basically these five types of signals:

### 1. Page Density

The denser the page overall, the smaller the base font size.
The looser the page overall, the larger the base font size.

### 2. Box Width

The narrower the box, the greater the wrapping pressure, and the more conservative the font size needs to be.
The wider the box, the more room the font size has to remain natural.

### 3. Box Height

The shorter the box, the fewer total lines it can tolerate, and the more dangerous the font size becomes.
The taller the box, the more room there is for wrapping.

### 4. Text Content Density

The longer, more compact, and harder to segment the translated content, the more the font size needs to be reduced.
When content is shorter and semantic blocks are clear, the font size is easier to maintain.

### 5. Special Content Proportion

For example, when there are many formulas, long tokens, or unsplittable fragments, these make "theoretical capacity" less reliable.

So when encountering such blocks, the algorithm usually becomes more conservative, not boldly increasing font size like it would for regular body text.

---

## 7. Walking Through a Complete Example of the Entire Judgment Process

Here's a more complete example.

### Scenario

A page is a two-column paper page, and the page overall leans dense.

The algorithm first observes:

- Most body text lines have tight line spacing
- Main body text blocks on the page are not tall
- The page has little whitespace

So it assigns a page-level base:

- **Page base font size = 9.4pt**

Now there's a target block:

- bbox width: 190
- bbox height: 96
- Translated text is relatively long
- Contains multiple formula placeholders

How does the algorithm proceed?

### Step 1: Start from the Page Base

First assume this block also uses 9.4pt.

### Step 2: Check If the Box Is Hard to Fit

This box is relatively narrow, and the height isn't large either. This means:

- Not many characters fit per line
- Once wrapping increases, total height fills up quickly

So the algorithm reaches a conclusion:

**This block is harder to fit than the "page average block."**

So the font size is adjusted down slightly from 9.4pt, say to 9.0pt.

### Step 3: Check If the Content Is Problematic

The translated text is on the longer side, and there are many formulas. The trouble with formulas is:

- They don't necessarily break as easily as regular text
- Some lines will be wider than estimated due to formulas

So the algorithm continues to be conservative, perhaps adjusting from 9.0pt to 8.7pt.

### Step 4: Do the Final Box-Fit Check

At this point, it's not certain that 8.7pt is correct.
Actual rendering is tested, and the last line still slightly exceeds the box.

So the final step reduces it a bit more, say to 8.5pt.

Final result:

- Page base 9.4pt
- Block-level adjusted 8.7pt
- Final fit to 8.5pt

This is a very typical "dynamically varying with page and block" process.

---

## 8. Why This Algorithm Is More Reliable Than "Linear Scaling"

Many systems initially use a very direct approach:

"However many characters exceed, I'll proportionally shrink the font size by that amount."

This method is useful but insufficient.

Because it assumes a premise:

**Text length and real typesetting pressure have a linear relationship.**

But they don't.

For example:

- The same amount of text has completely different effects in wide and narrow boxes
- The same amount of text has completely different effects with and without formulas
- The same amount of text also has different effects on already-dense pages versus loose pages

So a more reasonable algorithm doesn't just look at "how many characters exceed" but comprehensively judges:

- Was this page tight to begin with
- Is this box hard to fit
- Is this content hard to typeset
- After actual rendering, does it still overflow

In other words:

**Font size changes should be layered judgments that gradually converge, not relying on a single linear function to do everything.**

---

## 9. What Mistakes Is This Approach Most Prone To

Although this algorithm is much better than fixed font sizes, it's also easy to fall into pitfalls.

### 1. Over-trusting OCR

If OCR misidentifies two lines as one, then you think this page has large line spacing and loose content, so the page-level base gets overestimated. The subsequent font sizes for the entire page may all be too large.

### 2. Over-relying on Character Count

Character count is just a very rough indicator. What truly determines typesetting pressure is:

- Whether it can break lines
- How many lines it becomes after breaking
- Whether certain lines have especially wide content

### 3. Fixing the Minimum Font Size

If you globally set a hard floor, say never below 9.6pt no matter what, then many extremely narrow boxes will fail.

But if the floor is too low, it will cause noticeable degradation in visual quality.

So the minimum font size should ideally not be rigid but have some dynamism:
Regular body text blocks, extremely dense blocks, and formula-heavy blocks can have different tolerance ranges.

### 4. Only Estimating, Never Doing Final Actual Testing

No matter how smart the estimation, as long as you don't do the final box-fit check, you'll always encounter situations where "the estimate was close, but actual rendering still overflows."

---

## 10. If You Compress This Algorithm into One Sentence

It can be summarized in one sentence:

**First look at the page's average rhythm, then look at the box's geometric pressure, then look at the content's density, and finally use actual rendering results to close the loop.**

This is the core idea of "font size that varies with the page."

It's not about pursuing mathematical optimality, but about getting more stable, more natural, and less overflow-prone results in real PDFs.

---

## 11. Final Summary in More Engineering-Oriented Terms

A reliable dynamic font size algorithm usually doesn't ask:

"What font size should this block use?"

Instead, it consecutively asks four questions:

1. What is the overall rhythm of this page?
2. Compared to the page average, is this block harder or easier to typeset?
3. How much does the translated content exceed this box's capacity?
4. After actual rendering, did it truly fit?

When these four questions are all answered, the font size will feel more like it was "calculated" rather than "guessed."