from __future__ import annotations

import re

from services.translation.item_reader import item_block_kind
from services.translation.item_reader import item_is_bodylike
from services.translation.item_reader import item_is_reference_like
from services.translation.item_reader import item_normalized_sub_type
from services.translation.item_reader import item_raw_block_type
from services.translation.policy.literal_block_rules import shared_literal_block_label
from services.translation.policy.metadata_filter import find_metadata_fragment_item_ids
from services.translation.policy.soft_hints import natural_word_count
from services.translation.policy.mixed_literal_splitter import split_mixed_literal_items

from .common import clear_translation_fields


_CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
_EN_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
_PROSE_CUE_RE = re.compile(
    r"\b(if|when|then|thus|are|is|was|were|seen|rules?|vertices?|order|bump|more|governed)\b",
    re.I,
)
_NUMBERED_SUMMARY_RE = re.compile(r"^\s*\d+\.\s+[A-Z]")
_REFERENCE_ENTRY_RE = re.compile(r"^\s*(?:\[\d+]|[A-Z][^,]{0,40},\s+[A-Z])")
_NUMBERED_REFERENCE_ENTRY_RE = re.compile(
    r"^\s*\d+\.\s+(?:[A-Z][A-Za-z'`-]+,\s+[A-Z]|[A-Z][A-Za-z'`-]+(?:\s+[A-Z]\.){1,3}(?:\s+[A-Z][A-Za-z'`-]+)?)"
)


def _mark_item_skipped(item: dict, label: str) -> None:
    item["classification_label"] = label
    item["should_translate"] = False
    item["skip_reason"] = label
    clear_translation_fields(item)
    item["final_status"] = "kept_origin"


def _preserve_source_as_translation(item: dict) -> None:
    source_text = str(item.get("source_text", "") or "").strip()
    protected_source_text = str(item.get("protected_source_text", "") or source_text).strip()
    item["translation_unit_protected_translated_text"] = protected_source_text
    item["translation_unit_translated_text"] = source_text
    item["protected_translated_text"] = protected_source_text
    item["translated_text"] = source_text


def _is_ref_text_like(item: dict) -> bool:
    if item_is_reference_like(item) or item_raw_block_type(item) == "ref_text":
        return True
    return item_normalized_sub_type(item) == "ref_text"


def _should_force_translate_mixed_literal_item(item: dict) -> bool:
    if item_block_kind(item) != "text":
        return False
    if not item_is_bodylike(item):
        return False
    text = str(
        item.get("mixed_original_protected_source_text")
        or item.get("translation_unit_protected_source_text")
        or item.get("protected_source_text")
        or item.get("source_text")
        or ""
    )
    compact = " ".join(text.split())
    if len(compact) < 48:
        return False
    english_words = _EN_WORD_RE.findall(compact)
    if len(english_words) < 8:
        return False
    long_words = sum(1 for word in english_words if len(word) >= 4)
    if long_words < 5:
        return False
    prose_cues = len(_PROSE_CUE_RE.findall(compact))
    symbol_chars = sum(1 for ch in compact if ch in "=<>+-*/()[]{}")
    alpha_chars = sum(1 for ch in compact if ch.isalpha())
    if alpha_chars <= 0:
        return False
    symbol_ratio = symbol_chars / max(1, len(compact))
    return prose_cues >= 2 and symbol_ratio < 0.28 and natural_word_count(compact) >= 8


def looks_like_cjk_dominant_body_text(item: dict) -> bool:
    if item_block_kind(item) != "text":
        return False
    if not item_is_bodylike(item):
        return False
    source_text = str(
        item.get("translation_unit_protected_source_text")
        or item.get("protected_source_text")
        or item.get("source_text")
        or ""
    )
    compact = " ".join(source_text.split())
    if len(compact) < 16:
        return False
    cjk_chars = len(_CJK_CHAR_RE.findall(compact))
    if cjk_chars < 10:
        return False
    latin_chars = len(_LATIN_CHAR_RE.findall(compact))
    english_words = len(_EN_WORD_RE.findall(compact))
    return cjk_chars >= max(10, latin_chars * 2, english_words * 2)


def apply_cjk_source_keep_origin(payload: list[dict]) -> int:
    skipped = 0
    for item in payload:
        if not item.get("should_translate", True):
            continue
        if not looks_like_cjk_dominant_body_text(item):
            continue
        item["classification_label"] = "skip_cjk_source_body"
        item["should_translate"] = False
        item["skip_reason"] = "skip_cjk_source_body"
        clear_translation_fields(item)
        _preserve_source_as_translation(item)
        item["final_status"] = "kept_origin"
        skipped += 1
    return skipped


def apply_shared_literal_block_policy(payload: list[dict]) -> dict[str, int]:
    code_skipped = 0
    translate_forced = 0
    for item in payload:
        if not item.get("should_translate", True):
            continue
        label = shared_literal_block_label(item)
        if label == "code":
            _mark_item_skipped(item, "code")
            code_skipped += 1
            continue
        if label == "translate_literal":
            item["classification_label"] = "translate_literal"
            item["should_translate"] = True
            item["skip_reason"] = ""
            translate_forced += 1
    return {
        "shared_literal_code_skipped": code_skipped,
        "shared_literal_code_region_skipped": 0,
        "shared_literal_image_region_skipped": 0,
        "shared_literal_translate_forced": translate_forced,
    }


def apply_ref_text_skip(payload: list[dict]) -> int:
    def _should_preserve_ref_text_for_translation(item: dict) -> bool:
        source_text = str(item.get("protected_source_text") or item.get("source_text") or "").strip()
        if not source_text:
            return False
        if _REFERENCE_ENTRY_RE.match(source_text):
            return False
        if _NUMBERED_REFERENCE_ENTRY_RE.match(source_text):
            return False
        if source_text.lower().startswith(("references", "bibliography")):
            return False
        if " et al." in source_text or re.search(r"\b\d{4}\b", source_text):
            return False
        word_count = len(_EN_WORD_RE.findall(source_text))
        if word_count < 12:
            return False
        if _NUMBERED_SUMMARY_RE.match(source_text):
            return bool(_PROSE_CUE_RE.search(source_text))
        if source_text.endswith((".", "。", "!", "?", ";", "；", ":")) and natural_word_count(source_text) >= 12:
            return True
        return False

    skipped = 0
    for item in payload:
        if not _is_ref_text_like(item):
            continue
        if not item.get("should_translate", True):
            continue
        if _should_preserve_ref_text_for_translation(item):
            continue
        _mark_item_skipped(item, "skip_ref_text")
        skipped += 1
    return skipped


def apply_mixed_literal_split_policy(
    payload: list[dict],
    *,
    api_key: str,
    model: str,
    base_url: str,
    workers: int,
    rule_guidance: str = "",
) -> dict[str, int]:
    candidates = [
        item
        for item in payload
        if item.get("should_translate", True)
        and str(item.get("classification_label", "") or "") == "translate_literal"
    ]
    if not candidates:
        return {
            "mixed_keep_all": 0,
            "mixed_translate_all": 0,
            "mixed_translate_tail": 0,
        }

    decisions = split_mixed_literal_items(
        candidates,
        api_key=api_key,
        model=model,
        base_url=base_url,
        workers=workers,
        rule_guidance=rule_guidance,
    )
    keep_all = 0
    translate_all = 0
    translate_tail = 0
    for item in candidates:
        item_id = str(item.get("item_id", "") or "")
        action, prefix = decisions.get(item_id, ("translate_all", ""))
        if action == "keep_all" and _should_force_translate_mixed_literal_item(item):
            action, prefix = "translate_all", ""
        item["mixed_literal_action"] = action
        item["mixed_literal_prefix"] = prefix
        original_protected = str(
            item.get("mixed_original_protected_source_text", "") or item.get("protected_source_text", "") or ""
        )
        item["mixed_original_protected_source_text"] = original_protected
        if action == "keep_all":
            _mark_item_skipped(item, "skip_mixed_keep_all")
            keep_all += 1
            continue
        if action == "translate_tail":
            protected_text = str(item.get("protected_source_text", "") or "")
            tail_protected = (
                protected_text[len(prefix) :].strip()
                if protected_text.startswith(prefix)
                else original_protected[len(prefix) :].strip()
                if original_protected.startswith(prefix)
                else protected_text
            )
            if not tail_protected:
                if _should_force_translate_mixed_literal_item(item):
                    item["classification_label"] = "translate_mixed_all"
                    item["should_translate"] = True
                    item["skip_reason"] = ""
                    item["mixed_literal_action"] = "translate_all"
                    item["mixed_literal_prefix"] = ""
                    translate_all += 1
                    continue
                _mark_item_skipped(item, "skip_mixed_keep_all")
                keep_all += 1
                continue
            item["protected_source_text"] = tail_protected
            if item.get("translation_unit_kind") == "single":
                item["translation_unit_protected_source_text"] = tail_protected
            item["classification_label"] = "translate_mixed_tail"
            item["should_translate"] = True
            item["skip_reason"] = ""
            translate_tail += 1
            continue
        item["classification_label"] = "translate_mixed_all"
        item["should_translate"] = True
        item["skip_reason"] = ""
        translate_all += 1
    return {
        "mixed_keep_all": keep_all,
        "mixed_translate_all": translate_all,
        "mixed_translate_tail": translate_tail,
    }


def apply_metadata_fragment_skip(payload: list[dict], *, page_idx: int, max_page_idx: int) -> int:
    if page_idx > max_page_idx:
        return 0
    skip_ids = find_metadata_fragment_item_ids(payload)
    if not skip_ids:
        return 0
    skipped = 0
    for item in payload:
        item_id = item.get("item_id", "")
        if item_id not in skip_ids:
            continue
        if not item.get("should_translate", True):
            continue
        _mark_item_skipped(item, "skip_metadata_fragment")
        skipped += 1
    return skipped


__all__ = [
    "apply_cjk_source_keep_origin",
    "apply_metadata_fragment_skip",
    "apply_mixed_literal_split_policy",
    "apply_ref_text_skip",
    "apply_shared_literal_block_policy",
    "looks_like_cjk_dominant_body_text",
]
