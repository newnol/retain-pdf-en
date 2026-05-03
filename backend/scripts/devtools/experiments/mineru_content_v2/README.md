# MinerU `content_list_v2` Adaptation Experiment

This experimental route converts MinerU's `content_list_v2.json` into a more structured intermediate JSON,
facilitating subsequent translation and rendering research.

It is deliberately isolated from the stable main pipeline and is not directly used as the default entry point.

Current recommendation:

- Main pipeline preferably uses `ocr/normalized/document.v1.json`
- `ocr/unpacked/layout.json` is only retained for adapter, debugging, and rollback
- `content_list_v2.json` is only used for finer-grained text/formula structure experiments

## Input

- `output/<job-id>/ocr/unpacked/content_list_v2.json`

## Output

Output is a structured JSON, mainly containing:

- Page list
- Normalized block structures
- Flattened text blocks with their `segments`
- Non-text blocks retain original MinerU payload

## How to Run

```bash
python scripts/devtools/experiments/mineru_content_v2/adapt_content_list_v2.py \
  --input output/<job-id>/ocr/unpacked/content_list_v2.json \
  --output output/<job-id>/ocr/mineru_content_v2_adapted.json
```

## Current Coverage

- Supports `title`, `paragraph`, `list`, `page_header`, `page_footer`, `page_number`
- `image`, `table`, `equation_interline` are retained as non-translatable blocks
- MinerU's list items are expanded into independent normalized blocks

## Known Limitations

- Does not yet do per-line geometry reconstruction
- List items reuse the parent list's bbox, as MinerU input does not have per-item bbox
- Currently not recommended as the default MinerU integration route
