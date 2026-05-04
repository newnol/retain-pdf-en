from __future__ import annotations

from services.document_schema.provider_adapters.common import NormalizedBlockSpec
from services.document_schema.provider_adapters.common import normalize_bbox
from services.document_schema.provider_adapters.paddle.content_extract import build_lines
from services.document_schema.provider_adapters.paddle.content_extract import build_segments
from services.document_schema.provider_adapters.paddle.content_extract import tighten_text_bbox
from services.document_schema.provider_adapters.paddle.context import PaddleBlockContext
from services.document_schema.provider_adapters.paddle.context import PaddlePageContext
from services.document_schema.provider_adapters.paddle.page_trace import attach_layout_trace
from services.document_schema.provider_adapters.paddle.rich_content import enrich_rich_content_trace
from services.document_schema.provider_adapters.paddle.trace import build_derived
from services.document_schema.provider_adapters.paddle.trace import build_metadata
from services.document_schema.provider_adapters.paddle.trace import build_source


def _paddle_layout_role(*, block_type: str, sub_type: str) -> str:
    if block_type != "text":
        return "unknown"
    return {
        "title": "title",
        "heading": "heading",
        "body": "paragraph",
        "header": "header",
        "footer": "footer",
        "page_number": "page_number",
        "footnote": "footnote",
        "figure_caption": "caption",
        "metadata": "unknown",
        "reference_entry": "unknown",
        "formula_number": "unknown",
        "table_caption": "caption",
        "image_caption": "caption",
        "caption": "caption",
    }.get(sub_type, "unknown")


def _paddle_semantic_role(*, raw_label: str, block_type: str, sub_type: str) -> str:
    label = raw_label.strip().lower()
    if block_type != "text":
        return "unknown"
    if sub_type in {"header", "footer", "footnote", "page_number", "metadata", "formula_number"}:
        return "metadata"
    if sub_type == "reference_entry":
        return "reference"
    if label == "abstract":
        return "abstract"
    if sub_type == "body":
        return "body"
    return "unknown"


def _paddle_structure_role(*, block_type: str, sub_type: str) -> str:
    if block_type != "text":
        return ""
    if sub_type == "body":
        return "body"
    if sub_type == "figure_caption":
        return "figure_caption"
    if sub_type == "heading":
        return "heading"
    if sub_type == "title":
        return "title"
    if sub_type == "reference_entry":
        return "reference_entry"
    if sub_type in {"caption", "figure_caption", "image_caption", "table_caption", "code_caption"}:
        return "caption"
    if sub_type in {"footnote", "image_footnote", "table_footnote"}:
        return "footnote"
    return ""


def _paddle_translate_policy(*, raw_label: str, block_type: str, sub_type: str) -> dict:
    label = raw_label.strip().lower()
    if block_type != "text":
        return {"translate": False, "translate_reason": f"provider_non_text:{block_type or 'unknown'}"}
    if label == "abstract":
        return {"translate": True, "translate_reason": "provider_body_whitelist:abstract"}
    if sub_type == "figure_caption":
        return {"translate": True, "translate_reason": "provider_caption_whitelist:figure_caption"}
    if sub_type == "body":
        return {"translate": True, "translate_reason": "provider_body_whitelist:body"}
    return {"translate": False, "translate_reason": f"provider_non_body:{sub_type or label or 'unknown'}"}


def _build_provenance(*, source: dict, raw_label: str) -> dict:
    return {
        "provider": str(source.get("provider", "") or ""),
        "raw_label": raw_label,
        "raw_sub_type": str(source.get("raw_sub_type", "") or ""),
        "raw_bbox": list(source.get("raw_bbox", [0, 0, 0, 0]) or [0, 0, 0, 0]),
        "raw_path": str(source.get("raw_path", "") or ""),
    }


def _apply_normalized_paddle_signals(metadata: dict) -> None:
    metadata["cross_column_merge_suspected"] = bool(metadata.get("provider_cross_column_merge_suspected"))
    metadata["reading_order_unreliable"] = bool(metadata.get("provider_reading_order_unreliable"))
    metadata["structure_unreliable"] = bool(metadata.get("provider_structure_unreliable"))
    metadata["text_missing_but_bbox_present"] = bool(metadata.get("provider_text_missing_but_bbox_present"))
    metadata["peer_block_absorbed_text"] = bool(metadata.get("provider_peer_block_absorbed_text"))
    metadata["body_repair_attempted"] = bool(metadata.get("provider_body_repair_attempted"))
    metadata["body_repair_applied"] = bool(metadata.get("provider_body_repair_applied"))
    metadata["body_repair_role"] = str(metadata.get("provider_body_repair_role", "") or "")
    metadata["body_repair_strategy"] = str(metadata.get("provider_body_repair_strategy", "") or "")
    metadata["body_repair_peer_block_id"] = str(metadata.get("provider_suspected_peer_block_id", "") or "")
    metadata["continuation_suppressed"] = bool(metadata.get("provider_continuation_suppressed"))
    metadata["continuation_suppressed_reason"] = str(metadata.get("provider_continuation_suppressed_reason", "") or "")
    metadata["column_layout_mode"] = str(metadata.get("provider_column_layout_mode", "") or "")
    metadata["column_index_guess"] = str(metadata.get("provider_column_index_guess", "") or "")


def build_block_context(*, page_context: PaddlePageContext, order: int) -> PaddleBlockContext:
    block = page_context["parsing_res_list"][order]
    raw_label = str(block.get("block_label", "") or "")
    bbox = normalize_bbox(block.get("block_bbox"))
    text = str(block.get("block_content", "") or "").strip()
    return {
        "page": page_context,
        "block": block,
        "order": order,
        "resolved_kind": page_context["classified_kinds"][order],
        "raw_label": raw_label,
        "bbox": bbox,
        "text": text,
        "signal_metadata": {
            **dict((page_context["column_signals"].get("block_signals", {}) or {}).get(order, {}) or {}),
            **dict((page_context.get("repair_metadata", {}) or {}).get(order, {}) or {}),
        },
    }


def build_block_metadata(
    *,
    block_context: PaddleBlockContext,
    kind_metadata: dict,
) -> dict:
    metadata = build_metadata(block_context["block"], kind_metadata)
    metadata.update(block_context["signal_metadata"])
    attach_layout_trace(
        metadata=metadata,
        bbox=block_context["bbox"],
        layout_box_lookup=block_context["page"]["layout_box_lookup"],
    )
    enrich_rich_content_trace(
        metadata=metadata,
        raw_label=block_context["raw_label"],
        text=block_context["text"],
        markdown_images=block_context["page"]["markdown_images"],
        markdown_text=block_context["page"]["markdown_text"],
    )
    peer_order = metadata.get("provider_suspected_peer_order")
    if isinstance(peer_order, int) and peer_order >= 0:
        metadata["provider_suspected_peer_block_id"] = (
            f"p{block_context['page']['page_index'] + 1:03d}-b{peer_order:04d}"
        )
    else:
        metadata["provider_suspected_peer_block_id"] = ""
    _apply_normalized_paddle_signals(metadata)
    return metadata


def build_block_spec(
    *,
    page_context: PaddlePageContext,
    order: int,
) -> NormalizedBlockSpec:
    block_context = build_block_context(page_context=page_context, order=order)
    block_type, sub_type, tags, kind_metadata = block_context["resolved_kind"]
    bbox = tighten_text_bbox(
        bbox=block_context["bbox"],
        text=block_context["text"],
        block_type=block_type,
        sub_type=sub_type,
    )
    segments = build_segments(block_context["text"], block_context["raw_label"])
    lines = build_lines(
        bbox=bbox,
        segments=segments,
        text=block_context["text"],
        raw_label=block_context["raw_label"],
        block_type=block_type,
        sub_type=sub_type,
    )
    metadata = build_block_metadata(
        block_context=block_context,
        kind_metadata=kind_metadata,
    )
    source = build_source(
        block=block_context["block"],
        page_index=page_context["page_index"],
        raw_label=block_context["raw_label"],
        bbox=bbox,
        text=block_context["text"],
        order=order,
    )
    layout_role = _paddle_layout_role(block_type=block_type, sub_type=sub_type)
    semantic_role = _paddle_semantic_role(
        raw_label=block_context["raw_label"],
        block_type=block_type,
        sub_type=sub_type,
    )
    structure_role = _paddle_structure_role(block_type=block_type, sub_type=sub_type)
    policy = _paddle_translate_policy(
        raw_label=block_context["raw_label"],
        block_type=block_type,
        sub_type=sub_type,
    )
    metadata["structure_role"] = structure_role
    metadata["layout_role"] = layout_role
    metadata["semantic_role"] = semantic_role
    metadata["policy_translate"] = bool(policy.get("translate"))
    return {
        "block_id": f"p{page_context['page_index'] + 1:03d}-b{order:04d}",
        "page_index": page_context["page_index"],
        "order": order,
        "reading_order": order,
        "block_type": block_type,
        "sub_type": sub_type,
        "bbox": bbox,
        "geometry": {"bbox": list(bbox)},
        "content": {"kind": block_type, "text": block_context["text"]},
        "text": block_context["text"],
        "lines": lines,
        "segments": segments,
        "tags": tags,
        "layout_role": layout_role,
        "semantic_role": semantic_role,
        "structure_role": structure_role,
        "policy": policy,
        "derived": build_derived(block_context["raw_label"], sub_type=sub_type),
        "metadata": metadata,
        "source": source,
        "provenance": _build_provenance(source=source, raw_label=block_context["raw_label"]),
    }


__all__ = [
    "build_block_context",
    "build_block_spec",
]
