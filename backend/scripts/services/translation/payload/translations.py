from __future__ import annotations
import json
from pathlib import Path

from services.translation.ocr.models import TextItem
from services.translation.payload.parts.translation_units import refresh_payload_translation_units

from .template_contract import sanitize_loaded_translation_record
from .template_contract import validate_translation_payload_contract
from .template_records import build_translation_record
from .template_sync import append_missing_translation_records
from .template_sync import sync_translation_record


def export_translation_template(
    items: list[TextItem],
    output_path: Path,
    page_idx: int,
    *,
    math_mode: str = "placeholder",
) -> None:
    del page_idx
    payload = [build_translation_record(item, math_mode=math_mode) for item in items]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_translations(translation_path: Path, *, strict_contract: bool = True) -> list[dict]:
    with translation_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    changed = False
    for record in payload:
        if isinstance(record, dict):
            changed = sanitize_loaded_translation_record(record) or changed
    if refresh_payload_translation_units(payload):
        changed = True
    if changed:
        save_translations(translation_path, payload)
    if strict_contract:
        validate_translation_payload_contract(payload, translation_path=translation_path)
    return payload


def save_translations(translation_path: Path, payload: list[dict]) -> None:
    with translation_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def ensure_translation_template(
    items: list[TextItem],
    output_path: Path,
    page_idx: int,
    *,
    math_mode: str = "placeholder",
) -> Path:
    if not output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export_translation_template(items, output_path, page_idx=page_idx, math_mode=math_mode)
        return output_path

    try:
        payload = load_translations(output_path)
    except RuntimeError as exc:
        if "missing strict contract fields" not in str(exc):
            raise
        export_translation_template(items, output_path, page_idx=page_idx, math_mode=math_mode)
        return output_path
    item_map = {item.item_id: item for item in items}
    existing_item_ids = {
        str(record.get("item_id", "") or "")
        for record in payload
        if isinstance(record, dict)
    }
    changed = False
    for record in payload:
        item = item_map.get(record.get("item_id"))
        if not item:
            continue
        changed = sync_translation_record(record, item, math_mode=math_mode) or changed
    changed = append_missing_translation_records(
        payload,
        items=items,
        existing_item_ids=existing_item_ids,
        math_mode=math_mode,
    ) or changed
    if refresh_payload_translation_units(payload):
        changed = True
    if changed:
        save_translations(output_path, payload)
    return output_path
