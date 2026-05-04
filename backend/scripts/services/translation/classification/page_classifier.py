import re

from services.translation.classification.prompting import build_prompt
from services.translation.classification.response_parser import parse_no_trans_response
from services.translation.classification.rule_engine import rule_label
from services.translation.classification.rule_engine import should_include
from services.translation.item_reader import item_block_kind
from services.translation.item_reader import item_effective_role
from services.translation.item_reader import item_layout_role
from services.translation.item_reader import item_semantic_role
from services.translation.ocr.models import TextItem
from services.translation.llm.shared.provider_runtime import DEFAULT_BASE_URL, DEFAULT_MODEL, request_chat_content


def _count_inline_formulas(segments: list[dict]) -> int:
    return sum(1 for segment in segments if segment.get("type") == "inline_equation")


def _line_texts(lines: list[dict]) -> list[str]:
    return [" ".join(span.get("content", "") for span in line.get("spans", [])).strip() for line in lines]


def _candidate_payload(item: dict) -> dict:
    return {
        "block_type": item.get("block_type", ""),
        "block_kind": item.get("block_kind", item.get("block_type", "")),
        "layout_role": item.get("layout_role", ""),
        "semantic_role": item.get("semantic_role", ""),
        "structure_role": item.get("structure_role", ""),
        "policy_translate": item.get("policy_translate"),
        "bbox": item.get("bbox", []),
        "source_text": item.get("source_text", ""),
        "formula_map": item.get("formula_map"),
        "metadata": item.get("metadata", {}),
    }


def _candidate_record(item: dict, order: int) -> dict:
    lines = item.get("lines", [])
    payload = _candidate_payload(item)
    return {
        "order": order,
        "item_id": item["item_id"],
        "block_type": item_block_kind(payload),
        "block_kind": item_block_kind(payload),
        "layout_role": item_layout_role(payload),
        "semantic_role": item_semantic_role(payload),
        "effective_role": item_effective_role(payload),
        "bbox": item.get("bbox", []),
        "source_text": item.get("source_text", ""),
        "line_count": len(lines),
        "lines": lines,
        "line_texts": _line_texts(lines),
        "has_inline_formula": bool(item.get("formula_map")),
        "metadata": item.get("metadata", {}),
    }


def _candidate_text_item(item: TextItem, order: int) -> dict:
    payload = _candidate_payload(
        {
            "block_type": item.block_type,
            "block_kind": getattr(item, "block_kind", item.block_type),
            "layout_role": getattr(item, "layout_role", ""),
            "semantic_role": getattr(item, "semantic_role", ""),
            "structure_role": getattr(item, "structure_role", ""),
            "policy_translate": getattr(item, "policy_translate", None),
            "bbox": item.bbox,
            "source_text": item.text,
            "formula_map": item.formula_map if hasattr(item, "formula_map") else [],
            "metadata": item.metadata,
        }
    )
    return {
        "order": order,
        "item_id": item.item_id,
        "block_type": item_block_kind(payload),
        "block_kind": item_block_kind(payload),
        "layout_role": item_layout_role(payload),
        "semantic_role": item_semantic_role(payload),
        "effective_role": item_effective_role(payload),
        "bbox": item.bbox,
        "source_text": item.text,
        "line_count": len(item.lines),
        "lines": item.lines,
        "line_texts": _line_texts(item.lines),
        "has_inline_formula": _count_inline_formulas(item.segments) > 0,
        "metadata": item.metadata,
    }



def classify_payload_items(
    payload: list[dict],
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    batch_size: int = 12,
    rule_guidance: str = "",
    request_label: str = "",
) -> dict[str, str]:
    del batch_size
    page_items = [_candidate_record(item, order) for order, item in enumerate(payload, start=1)]
    filtered = [item for item in page_items if should_include(item)]
    if not filtered:
        return {}
    for item in filtered:
        item["rule_label"] = rule_label(item)
    review_items = [item for item in filtered if item["rule_label"] == "review"]
    labels = {item["item_id"]: item["rule_label"] for item in filtered if item["rule_label"] != "review"}
    if review_items:
        if request_label:
            print(f"{request_label}: review_items={len(review_items)} filtered={len(filtered)}", flush=True)
        content = request_chat_content(
            build_prompt(filtered, review_items, rule_guidance=rule_guidance),
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=0.0,
            response_format=None,
            timeout=120,
            request_label=request_label,
        )
        labels.update(parse_no_trans_response(content, review_items))
    return labels


def classify_text_items(
    items: list[TextItem],
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    batch_size: int = 12,
    rule_guidance: str = "",
    request_label: str = "",
) -> dict[str, str]:
    del batch_size
    page_items = [_candidate_text_item(item, order) for order, item in enumerate(items, start=1)]
    filtered = [item for item in page_items if should_include(item)]
    if not filtered:
        return {}
    for item in filtered:
        item["rule_label"] = rule_label(item)
    review_items = [item for item in filtered if item["rule_label"] == "review"]
    labels = {item["item_id"]: item["rule_label"] for item in filtered if item["rule_label"] != "review"}
    if review_items:
        if request_label:
            print(f"{request_label}: review_items={len(review_items)} filtered={len(filtered)}", flush=True)
        content = request_chat_content(
            build_prompt(filtered, review_items, rule_guidance=rule_guidance),
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=0.0,
            response_format=None,
            timeout=120,
            request_label=request_label,
        )
        labels.update(parse_no_trans_response(content, review_items))
    return labels
