# Config Layering Description

`scripts/foundation/config` is used to centrally manage configuration, avoiding the shared layer from continuing to carry all responsibilities.

## Split Results

- `paths.py`
  Only contains path-related configuration, e.g., `ROOT_DIR`, `DATA_DIR`, `OUTPUT_DIR`, `SOURCE_PDF`.
- `fonts.py`
  Only contains font and font-size related configuration, e.g., default font path, default font size, Typst default font family.
- `runtime.py`
  Only contains runtime defaults, e.g., default page number, default output name, PDF compression DPI.
- `layout.py`
  Only contains layout tuning related configuration and `apply_layout_tuning(...)`.

## Compatibility Strategy

Currently `scripts/foundation/shared/config.py` is still retained as a compatibility facade.

The common old pattern in historical code is:

```python
from foundation.config.paths import OUTPUT_DIR
from foundation.config.layout import apply_layout_tuning
```

If gradual decoupling is desired later, each module's imports can be migrated to more explicit sources:

- Path-related: prefer `foundation.config.paths`
- Font-related: prefer `foundation.config.fonts`
- Layout tuning: prefer `foundation.config.layout`
- Runtime defaults: prefer `foundation.config.runtime`
