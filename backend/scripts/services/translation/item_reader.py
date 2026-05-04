from __future__ import annotations

from services.document_schema.semantics import build_role_profile

_TEXTUAL_LAYOUT_ROLES = {"title", "heading", "paragraph", "list_item", "caption"}


def _first_non_empty_str(*values: object) -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def item_bbox(item: dict | None) -> list[float]:
    bbox = list((item or {}).get("bbox", []) or [])
    if len(bbox) == 4:
        return bbox
    return [0, 0, 0, 0]


def item_source_text(item: dict | None) -> str:
    source = item or {}
    return str(
        source.get("translation_unit_protected_source_text")
        or source.get("group_protected_source_text")
        or source.get("protected_source_text")
        or source.get("source_text")
        or ""
    )


def item_raw_block_type(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(
        source.get("raw_block_type"),
        source.get("block_type"),
    ).lower()


def item_block_kind(item: dict | None) -> str:
    source = item or {}
    explicit = _first_non_empty_str(source.get("block_kind"))
    if explicit:
        return explicit.lower()
    return _first_non_empty_str(source.get("block_type")).lower() or "unknown"


def item_layout_role(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(source.get("layout_role")).lower()


def item_semantic_role(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(source.get("semantic_role")).lower()


def item_structure_role(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(source.get("structure_role")).lower()


def item_normalized_sub_type(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(source.get("normalized_sub_type")).lower()


def item_effective_role(item: dict | None) -> str:
    return _first_non_empty_str(
        item_layout_role(item),
        item_semantic_role(item),
        item_structure_role(item),
    ).lower()


def item_policy_translate(item: dict | None) -> bool | None:
    return build_role_profile(item).get("policy_translate")  # type: ignore[return-value]


def item_reading_order(item: dict | None) -> int:
    source = item or {}
    value = source.get("reading_order", source.get("block_idx", 0))
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return 0


def item_asset_id(item: dict | None) -> str:
    source = item or {}
    return _first_non_empty_str(source.get("asset_id")).strip()


def item_tags(item: dict | None) -> set[str]:
    return set()


def item_is_caption_like(item: dict | None) -> bool:
    return bool(build_role_profile(item).get("is_caption_like"))


def item_is_reference_like(item: dict | None) -> bool:
    return bool(build_role_profile(item).get("is_reference_entry"))


def item_is_reference_heading_like(item: dict | None) -> bool:
    return bool(build_role_profile(item).get("is_reference_heading"))


def item_is_algorithm_like(item: dict | None) -> bool:
    if bool(build_role_profile(item).get("is_algorithm")):
        return True
    return item_raw_block_type(item) == "algorithm"


def item_is_title_like(item: dict | None) -> bool:
    return bool(build_role_profile(item).get("is_title_like"))


def item_is_textual(item: dict | None) -> bool:
    if item_block_kind(item) == "text":
        return True
    return item_layout_role(item) in _TEXTUAL_LAYOUT_ROLES


def item_is_plain_text_block(item: dict | None) -> bool:
    return item_block_kind(item) == "text" and not (
        item_is_caption_like(item) or item_is_reference_like(item) or item_is_title_like(item)
    )


def item_is_bodylike(item: dict | None) -> bool:
    return item_is_plain_text_block(item) and bool(build_role_profile(item).get("is_bodylike"))


__all__ = [
    "item_asset_id",
    "item_bbox",
    "item_block_kind",
    "item_effective_role",
    "item_is_bodylike",
    "item_is_algorithm_like",
    "item_is_caption_like",
    "item_is_plain_text_block",
    "item_is_reference_heading_like",
    "item_is_reference_like",
    "item_is_textual",
    "item_is_title_like",
    "item_layout_role",
    "item_normalized_sub_type",
    "item_policy_translate",
    "item_raw_block_type",
    "item_reading_order",
    "item_semantic_role",
    "item_source_text",
    "item_structure_role",
    "item_tags",
]
