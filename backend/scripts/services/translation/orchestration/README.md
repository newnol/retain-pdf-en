# Orchestration Overview

`scripts/services/translation/orchestration` is responsible for supplementing OCR payloads with "orchestration metadata."

It neither directly translates nor directly renders; its role is to organize raw OCR blocks into an intermediate state more suitable for translation and typesetting use.

## Main Files

- `zones.py`
  Page layout analysis, identifying single-column/double-column and layout zones.
- `units.py`
  Generating and organizing standard fields such as `translation_unit_id` and `skip_reason`.
- `document_orchestrator.py`
  Chains together layout zone annotation, candidate continuation review, and metadata closure.

## Position in the Overall Flow

`ocr payload -> orchestration -> translation policy / continuation / translation unit -> translation`
