from __future__ import annotations

from services.document_schema.defaults import normalize_block_continuation_hint
from services.document_schema.provider_adapters.common.specs import NormalizedBlockSpec


def build_block_record(spec: NormalizedBlockSpec) -> dict:
    bbox = list(spec.get("bbox", [0, 0, 0, 0]) or [0, 0, 0, 0])
    text = str(spec.get("text", "") or "")
    block_type = str(spec.get("block_type", "unknown") or "unknown")
    record = {
        "block_id": str(spec.get("block_id", "") or ""),
        "page_index": int(spec.get("page_index", 0) or 0),
        "order": int(spec.get("order", 0) or 0),
        "type": block_type,
        "sub_type": str(spec.get("sub_type", "") or ""),
        "bbox": bbox,
        "text": text,
        "lines": list(spec.get("lines", []) or []),
        "segments": list(spec.get("segments", []) or []),
        "tags": list(spec.get("tags", []) or []),
        "derived": dict(spec.get("derived", {}) or {}),
        "continuation_hint": normalize_block_continuation_hint(spec.get("continuation_hint")),
        "metadata": dict(spec.get("metadata", {}) or {}),
        "source": dict(spec.get("source", {}) or {}),
    }
    record["reading_order"] = int(spec.get("reading_order", record["order"]) or record["order"])
    record["geometry"] = dict(spec.get("geometry", {}) or {"bbox": bbox})
    record["content"] = dict(spec.get("content", {}) or {"kind": block_type, "text": text})
    if "layout_role" in spec:
        record["layout_role"] = str(spec.get("layout_role", "") or "")
    if "semantic_role" in spec:
        record["semantic_role"] = str(spec.get("semantic_role", "") or "")
    if "structure_role" in spec:
        record["structure_role"] = str(spec.get("structure_role", "") or "")
    if "policy" in spec:
        record["policy"] = dict(spec.get("policy", {}) or {})
    if "provenance" in spec:
        record["provenance"] = dict(spec.get("provenance", {}) or {})
    return record
