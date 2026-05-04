from __future__ import annotations

from services.translation.diagnostics import TranslationDiagnosticsCollector
from services.translation.llm.placeholder_guard import EmptyTranslationError
from services.translation.llm.placeholder_guard import result_entry
from services.translation.llm.shared.orchestration.common import chunk_source_text_fallback
from services.translation.llm.shared.orchestration.common import formula_placeholder_count
from services.translation.llm.shared.orchestration.common import SENTENCE_SPLIT_RE
from services.translation.llm.shared.orchestration.metadata import formula_route_diagnostics


HEAVY_FORMULA_CHUNK_PLACEHOLDERS = 8
HEAVY_FORMULA_CHUNK_CHARS = 900


def heavy_formula_split_reason(item: dict, *, context) -> str:
    source_text = str(item.get("translation_unit_protected_source_text") or item.get("protected_source_text") or "")
    placeholder_count = formula_placeholder_count(source_text)
    if placeholder_count < context.segmentation_policy.max_formula_segment_count:
        return ""
    if len(source_text) < 1200 and placeholder_count < 24:
        return ""
    return "heavy_formula_density"


def split_heavy_formula_block(source_text: str) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(source_text) if part.strip()]
    if len(sentences) <= 1:
        sentences = chunk_source_text_fallback(source_text, words_per_chunk=40)
    if len(sentences) <= 1:
        return [str(source_text or "").strip()] if str(source_text or "").strip() else []

    chunks: list[str] = []
    current: list[str] = []
    current_placeholders = 0
    current_chars = 0
    for sentence in sentences:
        sentence_placeholders = formula_placeholder_count(sentence)
        sentence_chars = len(sentence)
        would_overflow = bool(current) and (
            current_placeholders + sentence_placeholders > HEAVY_FORMULA_CHUNK_PLACEHOLDERS
            or current_chars + sentence_chars > HEAVY_FORMULA_CHUNK_CHARS
        )
        if would_overflow:
            chunks.append(" ".join(current).strip())
            current = []
            current_placeholders = 0
            current_chars = 0
        current.append(sentence)
        current_placeholders += sentence_placeholders
        current_chars += sentence_chars
    if current:
        chunks.append(" ".join(current).strip())
    return [chunk for chunk in chunks if chunk.strip()]


def translate_heavy_formula_block(
    item: dict,
    *,
    api_key: str,
    model: str,
    base_url: str,
    request_label: str,
    context,
    diagnostics: TranslationDiagnosticsCollector | None,
    split_reason: str,
    translate_single_item_fn,
    deferred_transport_retry_type,
) -> dict[str, dict[str, str]] | None:
    source_text = str(item.get("translation_unit_protected_source_text") or item.get("protected_source_text") or "")
    chunks = split_heavy_formula_block(source_text)
    if len(chunks) <= 1:
        return None

    translated_parts: list[str] = []
    degraded_chunks = 0
    for index, chunk in enumerate(chunks):
        chunk_item = dict(item)
        chunk_item["_heavy_formula_split_applied"] = True
        chunk_item["translation_unit_protected_source_text"] = chunk
        chunk_item["protected_source_text"] = chunk
        chunk_item["continuation_prev_text"] = chunks[index - 1] if index > 0 else str(item.get("continuation_prev_text", "") or "")
        chunk_item["continuation_next_text"] = chunks[index + 1] if index < len(chunks) - 1 else str(item.get("continuation_next_text", "") or "")
        try:
            chunk_result = translate_single_item_fn(
                chunk_item,
                api_key=api_key,
                model=model,
                base_url=base_url,
                request_label=f"{request_label} split#{index + 1}" if request_label else "",
                context=context,
                diagnostics=diagnostics,
            )
            translated = str(chunk_result.get(item["item_id"], {}).get("translated_text", "") or "").strip()
        except (EmptyTranslationError, deferred_transport_retry_type):
            translated = ""
        if not translated:
            degraded_chunks += 1
            translated = chunk.strip()
            if request_label:
                print(
                    f"{request_label} split#{index + 1}: empty translation chunk degraded to keep_origin chunk",
                    flush=True,
                )
        translated_parts.append(translated)

    payload = result_entry("translate", " ".join(translated_parts).strip())
    payload["translation_diagnostics"] = {
        "item_id": item.get("item_id", ""),
        "page_idx": item.get("page_idx"),
        "route_path": ["block_level", "heavy_formula_split"],
        "output_mode_path": ["plain_text"],
        "fallback_to": "keep_origin" if degraded_chunks else "",
        "degradation_reason": f"{split_reason}_chunk_keep_origin" if degraded_chunks else split_reason,
        "final_status": "partially_translated" if degraded_chunks else "translated",
        "segment_stats": {
            "expected": len(chunks),
            "received": len(chunks),
            "missing_ids": [],
        },
        "degraded_chunk_count": degraded_chunks,
        **formula_route_diagnostics(item, context=context),
    }
    return {item["item_id"]: payload}
