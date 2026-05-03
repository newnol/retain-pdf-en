from __future__ import annotations

from copy import deepcopy


_TEXT_LAYOUT_SUBTYPE_MAP = {
    "title": "title",
    "heading": "heading",
    "body": "paragraph",
    "header": "header",
    "footer": "footer",
    "page_number": "page_number",
    "footnote": "footnote",
}

_TEXT_ANCILLARY_LAYOUT_ROLES = {"header", "footer", "page_number", "footnote", "caption"}
_BODYLIKE_LAYOUT_ROLES = {"title", "heading", "paragraph", "list_item"}
_BODYLIKE_SEMANTIC_ROLES = {"body", "abstract"}
_STRUCTURE_ROLE_FROM_LAYOUT_ROLE = {
    "title": "title",
    "heading": "heading",
    "paragraph": "body",
    "list_item": "body",
    "caption": "caption",
    "footnote": "footnote",
    "header": "metadata",
    "footer": "metadata",
    "page_number": "metadata",
}


def _normalize_tags(tags: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    return {str(tag or "").strip().lower() for tag in (tags or []) if str(tag or "").strip()}


def _derived_role(payload: dict | None) -> str:
    source = payload or {}
    derived = source.get("derived", {}) or {}
    return str(derived.get("role", "") or "").strip().lower()


def _is_caption_semantic(payload: dict | None) -> bool:
    source = payload or {}
    return _derived_role(source) == "caption" or bool(
        _normalize_tags(source.get("tags", [])) & {"caption", "image_caption", "table_caption", "table_footnote", "image_footnote"}
    )


def _is_reference_entry_semantic(payload: dict | None) -> bool:
    source = payload or {}
    return _derived_role(source) == "reference_entry" or bool(
        _normalize_tags(source.get("tags", [])) & {"reference_entry", "reference_zone"}
    )


def _is_metadata_semantic(payload: dict | None) -> bool:
    source = payload or {}
    return str(source.get("sub_type", "") or "").strip().lower() == "metadata"


def _normalize_bbox(value: list[float] | None) -> list[float]:
    bbox = list(value or [])
    if len(bbox) == 4:
        return bbox
    return [0, 0, 0, 0]


def _build_layout_role(block: dict) -> str:
    explicit = str(block.get("layout_role", "") or "").strip().lower()
    if explicit and explicit != "unknown":
        return explicit

    block_type = str(block.get("type", "") or "").strip().lower()
    sub_type = str(block.get("sub_type", "") or "").strip().lower()
    if block_type == "text":
        if sub_type in _TEXT_LAYOUT_SUBTYPE_MAP:
            return _TEXT_LAYOUT_SUBTYPE_MAP[sub_type]
        if _is_caption_semantic(block) or sub_type in {"caption", "figure_caption", "image_caption", "table_caption", "code_caption"}:
            return "caption"
        return "paragraph"
    return "unknown"


def _build_semantic_role(block: dict, *, layout_role: str) -> str:
    explicit = str(block.get("semantic_role", "") or "").strip().lower()
    if explicit and explicit != "unknown":
        return explicit

    role = _derived_role(block)
    tags = _normalize_tags(block.get("tags", []))
    if role == "abstract" or "abstract" in tags:
        return "abstract"
    if role == "formula_number" or str(block.get("sub_type", "") or "").strip().lower() == "formula_number":
        return "metadata"
    if _is_reference_entry_semantic(block) or str(block.get("sub_type", "") or "").strip().lower() == "reference_entry":
        return "reference"
    if _is_metadata_semantic(block) or role == "metadata":
        return "metadata"
    if role in {"acknowledgments", "acknowledgements", "acknowledgement"}:
        return "acknowledgement"
    if role == "affiliation":
        return "affiliation"
    if layout_role in _TEXT_ANCILLARY_LAYOUT_ROLES:
        return "metadata"
    if str(block.get("type", "") or "").strip().lower() == "text" and layout_role in {"paragraph", "list_item"}:
        return "body"
    return "unknown"


def _build_structure_role(block: dict, *, layout_role: str, semantic_role: str) -> str:
    explicit = str(block.get("structure_role", "") or "").strip().lower()
    if explicit and explicit != "unknown":
        return explicit

    metadata = block.get("metadata", {}) or {}
    metadata_role = str(metadata.get("structure_role", "") or "").strip().lower()
    if metadata_role and metadata_role != "unknown":
        return metadata_role

    sub_type = str(block.get("sub_type", "") or "").strip().lower()
    if sub_type == "reference_entry" or semantic_role == "reference":
        return "reference_entry"
    if semantic_role == "abstract":
        return "body"
    if semantic_role == "metadata":
        return "metadata"
    return _STRUCTURE_ROLE_FROM_LAYOUT_ROLE.get(layout_role, "")


def _translate_policy_reason(*, kind: str, layout_role: str, semantic_role: str) -> tuple[bool, str]:
    if kind != "text":
        return False, "non_text"
    if layout_role in _TEXT_ANCILLARY_LAYOUT_ROLES:
        return False, f"layout_role={layout_role}"
    if semantic_role in {"reference", "metadata", "affiliation", "acknowledgement", "unknown"}:
        return False, f"semantic_role={semantic_role}"
    if layout_role in _BODYLIKE_LAYOUT_ROLES and semantic_role in _BODYLIKE_SEMANTIC_ROLES:
        if semantic_role == "abstract":
            return True, "semantic_role=abstract"
        return True, "main_text"
    return False, "conservative_skip"


def _build_content(block: dict, *, page_index: int, order: int) -> dict:
    existing = dict(block.get("content", {}) or {})
    kind = str(existing.get("kind", block.get("type", "unknown")) or "unknown").strip().lower()
    content: dict = {"kind": kind}
    text = str(block.get("text", "") or "")
    if text:
        content["text"] = text

    metadata = block.get("metadata", {}) or {}
    asset_key = str(metadata.get("asset_key", "") or "").strip()
    asset_url = str(metadata.get("asset_url", "") or "").strip()
    if asset_key or asset_url:
        asset_id = asset_key or f"page_{page_index + 1:03d}_asset_{order:04d}"
        content["asset_id"] = asset_id
    if existing:
        content.update({k: deepcopy(v) for k, v in existing.items() if k not in content})
    return content


def _build_policy(block: dict, *, kind: str, layout_role: str, semantic_role: str) -> dict:
    existing = block.get("policy")
    translate_reason = ""
    translate = None
    if isinstance(existing, dict):
        if isinstance(existing.get("translate"), bool):
            translate = bool(existing.get("translate"))
        translate_reason = str(existing.get("translate_reason", "") or "").strip()
        if translate_reason == "missing_contract_fields":
            translate = None
            translate_reason = ""
    if translate is None:
        translate, translate_reason = _translate_policy_reason(
            kind=kind,
            layout_role=layout_role,
            semantic_role=semantic_role,
        )
    elif not translate_reason:
        translate_reason = "explicit_policy"
    return {
        "translate": translate,
        "translate_reason": translate_reason,
    }


def _build_provenance(block: dict) -> dict:
    explicit = block.get("provenance")
    if isinstance(explicit, dict) and explicit:
        raw_bbox = _normalize_bbox(explicit.get("raw_bbox"))
        return {
            "provider": str(explicit.get("provider", "") or ""),
            "raw_label": str(explicit.get("raw_label", "") or ""),
            "raw_sub_type": str(explicit.get("raw_sub_type", "") or ""),
            "raw_bbox": raw_bbox,
            "raw_path": str(explicit.get("raw_path", "") or ""),
        }
    source = dict(block.get("source", {}) or {})
    return {
        "provider": str(source.get("provider", "") or ""),
        "raw_label": str(source.get("raw_type", source.get("raw_label", "")) or ""),
        "raw_sub_type": str(source.get("raw_sub_type", "") or ""),
        "raw_bbox": _normalize_bbox(source.get("raw_bbox", block.get("bbox"))),
        "raw_path": str(source.get("raw_path", "") or ""),
    }


def _collect_assets(pages: list[dict]) -> dict:
    assets: dict[str, dict] = {}
    for page in pages:
        for block in page.get("blocks", []) or []:
            content = dict(block.get("content", {}) or {})
            asset_id = str(content.get("asset_id", "") or "").strip()
            if not asset_id:
                continue
            metadata = dict(block.get("metadata", {}) or {})
            uri = str(metadata.get("asset_url", metadata.get("asset_path", "")) or "").strip()
            if not uri:
                continue
            if asset_id in assets:
                continue
            assets[asset_id] = {
                "kind": "image",
                "uri": uri,
                "source": str(metadata.get("asset_kind", "") or ""),
            }
    return assets


def enrich_document_contract_v1(document: dict) -> dict:
    document["doc_id"] = str(document.get("doc_id", document.get("document_id", "")) or "")
    pages = document.get("pages", []) or []
    for page_index, page in enumerate(pages):
        page["page"] = int(page.get("page", page.get("page_index", page_index) + 1) or (page_index + 1))
        for order, block in enumerate(page.get("blocks", []) or []):
            block["reading_order"] = int(block.get("reading_order", block.get("order", order)) or order)
            block["geometry"] = {
                "bbox": _normalize_bbox((block.get("geometry", {}) or {}).get("bbox", block.get("bbox"))),
            }
            content = _build_content(block, page_index=page_index, order=order)
            block["content"] = content
            layout_role = _build_layout_role(block)
            semantic_role = _build_semantic_role(block, layout_role=layout_role)
            structure_role = _build_structure_role(
                block,
                layout_role=layout_role,
                semantic_role=semantic_role,
            )
            block["layout_role"] = layout_role
            block["semantic_role"] = semantic_role
            block["structure_role"] = structure_role
            block["policy"] = _build_policy(
                block,
                kind=str(content.get("kind", "unknown") or "unknown"),
                layout_role=layout_role,
                semantic_role=semantic_role,
            )
            block["provenance"] = _build_provenance(block)
    document["assets"] = _collect_assets(pages)
    return document


__all__ = [
    "enrich_document_contract_v1",
]
