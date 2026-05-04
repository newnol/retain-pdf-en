# Formula Rendering Notes

`services/rendering/formula/` is only responsible for one thing:

Turning "translated text with formulas" into a text form usable by the rendering stage.

This module is NOT responsible for:

- OCR formula detection
- Translation model invocation
- PDF page layout
- Typst full-page compilation

It's just a small module in the rendering chain, responsible for "how formula text enters the main rendering pipeline."

## Current Design Principles

This area is currently split along two lines:

- `core/`
  Main pipeline. Contains logic that must be executed during normal rendering.
- `fallback/`
  Fallback pipeline. Contains legacy compatibility, placeholder paths, LaTeX-ish fixes, and formula PNG rendering.

Do not use semantically ambiguous directory names like `shared/` or `modes/`.

## Current Directory

```text
formula/
  README.md
  __init__.py
  mode_router.py
  core/
    __init__.py
    inline_math.py
    markdown.py
  fallback/
    __init__.py
    latex_normalizer.py
    placeholder_markdown.py
    png_renderer.py
```

## How the Main Pipeline Works

The current default approach is:

1. Upstream provides `protected_text`, `formula_map`, `math_mode`
2. `mode_router.py` decides which path to take
3. If `direct_typst`
   Go directly through `core/inline_math.py` + `core/markdown.py`
4. If `placeholder`
   Go through `fallback/placeholder_markdown.py`
5. Final output is markdown/plain-text, passed to layout/typst/redaction

In other words:

- `mode_router.py` is only responsible for routing
- `core/` handles main pipeline text processing
- `fallback/` handles old paths and fallback capabilities

## File Responsibilities

### `mode_router.py`

Sole responsibility: select the path based on `math_mode`.

It should only do:

- `item_render_math_mode`
- `is_direct_typst_math_mode`
- `build_render_markdown`
- `build_item_render_markdown`

Formula cleaning details should not be stacked here.

### `core/inline_math.py`

Handles lightweight inline math level processing.

Mainly:

- Recognize existing `$...$`
- Only perform text replacement on non-math segments
- Perform minimal compatibility cleaning in `direct_typst` mode
- Add necessary spacing for inline formulas

This should stay lightweight; do not add placeholder logic here.

### `core/markdown.py`

Handles main pipeline markdown text construction.

Mainly:

- Build renderable markdown from plain text
- Perform inline math promotion
- Handle citation-like text
- Provide plain-text construction helpers

This represents "the formula text rules the current main path truly wants to keep."

### `fallback/placeholder_markdown.py`

Handles the placeholder formula path.

Input is typically:

- `protected_text`
- `formula_map`

Responsibilities:

- Split text by token
- Backfill formulas using `formula_map`
- When necessary, restore citations to plain text
- Finally call the main pipeline's markdown text processing

If placeholders are fully removed in the future, this file will continue to shrink.

### `fallback/latex_normalizer.py`

Handles old LaTeX-ish formula fixes.

It's not a core main pipeline capability, but a compatibility layer:

- Fix common OCR noise
- Handle legacy format issues
- Provide more stable input for placeholder/PNG fallback

If a rule only serves old data, don't put it in `core/`; put it here.

### `fallback/png_renderer.py`

Handles converting individual formulas to PNG.

This capability is mainly for:

- The redaction path
- A fallback path when certain formulas cannot be rendered directly as text

It does not represent the main pipeline.

The current main pipeline still prioritizes text/direct typst rather than converting all formulas to images.

## Dependency Direction

This layer must follow the dependency direction below:

- `mode_router -> core`
- `mode_router -> fallback`
- `fallback -> core`
- `core` must NOT reverse-depend on `fallback`

In other words:

- `core` can only contain truly fundamental, stable, main-pipeline items
- `fallback` can call `core`
- `core` must not import back from `fallback`

Otherwise, even though the directories are split, they remain coupled.

## What's Exposed Externally

External modules should typically only depend on these stable interfaces:

- `services.rendering.formula.__init__`
- `services.rendering.formula.mode_router`
- `services.rendering.formula.core.markdown`
- `services.rendering.formula.core.inline_math`
- `services.rendering.formula.fallback.placeholder_markdown`
- `services.rendering.formula.fallback.latex_normalizer`
- `services.rendering.formula.fallback.png_renderer`

Do not reference deleted historical paths, such as:

- `services.rendering.formula.math_utils`
- `services.rendering.formula.normalizer`
- `services.rendering.formula.typst_formula_renderer`
- `services.rendering.formula.shared.*`
- `services.rendering.formula.modes.*`

## Modification Guidelines

If you need to modify this area in the future, use the following decision order:

1. Is this main-pipeline mandatory logic?
   If yes, preferentially place it in `core/`
2. Is this placeholder / old LaTeX / PNG fallback / legacy compatibility?
   If yes, place it in `fallback/`
3. Is this path selection?
   Place it in `mode_router.py`
4. Is this a test bad case?
   Place it in
   [`devtools/tests/translation/test_formula_math_markers.py`](/home/wxyhgk/tmp/Code/backend/scripts/devtools/tests/translation/test_formula_math_markers.py)

## Files You Should Read First

If you want to quickly understand this area, the recommended reading order is:

1. [`mode_router.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/mode_router.py)
2. [`core/markdown.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/core/markdown.py)
3. [`core/inline_math.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/core/inline_math.py)
4. [`fallback/placeholder_markdown.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/fallback/placeholder_markdown.py)
5. [`fallback/latex_normalizer.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/fallback/latex_normalizer.py)
6. [`fallback/png_renderer.py`](/home/wxyhgk/tmp/Code/backend/scripts/services/rendering/formula/fallback/png_renderer.py)

## Current Status

The completed refactoring of this area includes:

- Separated `direct_typst` main pipeline from placeholder fallback pipeline
- Removed fake boundaries like `shared/` and `modes/`
- Eliminated circular imports between `core` and `fallback`

Remaining non-logic issues:

- Directory still contains `.ipynb_checkpoints`
- Directory still contains `__pycache__`

These don't affect runtime but do affect readability; they can be cleaned up later.
