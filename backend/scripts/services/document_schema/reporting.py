from __future__ import annotations

import json
from pathlib import Path


def load_normalization_report(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sum_default_hits(payload: dict | None) -> int:
    data = payload or {}
    return sum(int(value or 0) for value in data.values())


def build_normalization_summary(report: dict | None) -> dict:
    data = report or {}
    defaults = data.get("defaults", {}) or {}
    validation = data.get("validation", {}) or {}
    detection = data.get("detection", {}) or {}
    document_defaults = defaults.get("document_defaults", {}) or {}
    page_defaults = defaults.get("page_defaults", {}) or {}
    block_defaults = defaults.get("block_defaults", {}) or {}
    return {
        "provider": str(data.get("provider", "") or ""),
        "detected_provider": str(data.get("detected_provider", "") or ""),
        "provider_was_explicit": bool(data.get("provider_was_explicit", False)),
        "pages_observed": int(defaults.get("pages_seen", 0) or 0),
        "blocks_observed": int(defaults.get("blocks_seen", 0) or 0),
        "defaulted_document_fields": _sum_default_hits(document_defaults),
        "defaulted_page_fields": _sum_default_hits(page_defaults),
        "defaulted_block_fields": _sum_default_hits(block_defaults),
        "any_defaults_applied": bool(document_defaults or page_defaults or block_defaults),
        "valid": bool(validation.get("valid", False)),
        "page_count": int(validation.get("page_count", 0) or 0),
        "block_count": int(validation.get("block_count", 0) or 0),
        "detection_matched": bool(detection.get("matched", False)),
        "detection_attempts": len(detection.get("attempts", []) or []),
    }
