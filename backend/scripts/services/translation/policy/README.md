# Policy Overview

`scripts/services/translation/policy/` is the formal implementation directory for the translation policy layer.

It mainly includes:

- `config.py`
  Mode configuration, skip strategy, and domain inference entry point.
- `flow.py`
  The workflow entry point that actually applies policy to payload.
- `body_text_filter.py`
  Body text noise and narrow block filtering logic.
- `metadata_filter.py`
  Metadata fragment filtering logic for author lines, copyright lines, editorial information, etc.

## Design Principles

- New code should uniformly import from `services.translation.policy.*`.
- The policy layer only handles payload-level decisions; it does not directly touch PDF or rendering.
