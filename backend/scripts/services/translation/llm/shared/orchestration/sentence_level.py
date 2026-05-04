from __future__ import annotations

from services.translation.diagnostics import TranslationDiagnosticsCollector
from services.translation.llm.placeholder_guard import EmptyTranslationError
from services.translation.llm.placeholder_guard import EnglishResidueError
from services.translation.llm.placeholder_guard import PlaceholderInventoryError
from services.translation.llm.placeholder_guard import placeholder_sequence
from services.translation.llm.placeholder_guard import result_entry
from services.translation.llm.placeholder_guard import validate_batch_result
from services.translation.llm.shared.orchestration.common import chunk_source_text_fallback
from services.translation.llm.shared.orchestration.common import SENTENCE_SPLIT_RE
from services.translation.llm.shared.orchestration.keep_origin import keep_origin_payload_for_transport_error
from services.translation.llm.shared.orchestration.metadata import formula_route_diagnostics
from services.translation.llm.shared.orchestration.metadata import restore_runtime_term_tokens
from services.translation.llm.shared.provider_runtime import translate_single_item_plain_text
from services.translation.llm.shared.provider_runtime import translate_single_item_plain_text_unstructured


def sentence_level_fallback(
    item: dict,
    *,
    api_key: str,
    model: str,
    base_url: str,
    request_label: str,
    context,
    diagnostics: TranslationDiagnosticsCollector | None,
    translate_plain_fn=None,
    translate_unstructured_fn=None,
) -> dict[str, dict[str, str]]:
    translate_plain = translate_plain_fn or translate_single_item_plain_text
    translate_unstructured = translate_unstructured_fn or translate_single_item_plain_text_unstructured
    source_text = str(item.get("translation_unit_protected_source_text") or item.get("protected_source_text") or "")
    sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(source_text) if part.strip()]
    if len(sentences) <= 1:
        sentences = chunk_source_text_fallback(source_text)
    if len(sentences) <= 1:
        raise EmptyTranslationError(str(item.get("item_id", "") or ""))
    translated_parts: list[str] = []
    failed_indexes: list[int] = []
    translated_indexes: list[int] = []
    for index, sentence in enumerate(sentences):
        sentence_item = dict(item)
        sentence_item["translation_unit_protected_source_text"] = sentence
        sentence_item["protected_source_text"] = sentence
        try:
            sentence_result = translate_plain(
                sentence_item,
                api_key=api_key,
                model=model,
                base_url=base_url,
                request_label=f"{request_label} sent#{index + 1}" if request_label else "",
                domain_guidance=context.merged_guidance,
                mode=context.mode,
                diagnostics=diagnostics,
                timeout_s=context.timeout_policy.plain_text_seconds,
            )
            sentence_result = restore_runtime_term_tokens(sentence_result, item=item)
            translated = str(sentence_result.get(item["item_id"], {}).get("translated_text", "") or "").strip()
            if translated:
                translated_parts.append(translated)
                translated_indexes.append(index)
                continue
        except EmptyTranslationError:
            try:
                sentence_result = translate_unstructured(
                    sentence_item,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    request_label=f"{request_label} sent#{index + 1} raw" if request_label else "",
                    domain_guidance=context.merged_guidance,
                    mode=context.mode,
                    diagnostics=diagnostics,
                    timeout_s=context.timeout_policy.plain_text_seconds,
                )
                translated = str(sentence_result.get(item["item_id"], {}).get("translated_text", "") or "").strip()
                if translated:
                    translated_parts.append(translated)
                    translated_indexes.append(index)
                    continue
            except Exception:
                pass
        except EnglishResidueError:
            try:
                sentence_result = translate_unstructured(
                    sentence_item,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    request_label=f"{request_label} sent#{index + 1} raw" if request_label else "",
                    domain_guidance=context.merged_guidance,
                    mode=context.mode,
                    diagnostics=diagnostics,
                    timeout_s=context.timeout_policy.plain_text_seconds,
                )
                translated = str(sentence_result.get(item["item_id"], {}).get("translated_text", "") or "").strip()
                if translated:
                    translated_parts.append(translated)
                    translated_indexes.append(index)
                    continue
            except Exception:
                pass
        except Exception:
            pass
        translated_parts.append(sentence)
        failed_indexes.append(index)
    if not translated_indexes:
        raise PlaceholderInventoryError(
            str(item.get("item_id", "") or ""),
            placeholder_sequence(source_text),
            [],
            source_text=source_text,
            translated_text="",
        )
    payload = result_entry("translate", " ".join(translated_parts).strip())
    payload["final_status"] = "partially_translated"
    payload["translation_diagnostics"] = {
        "item_id": item.get("item_id", ""),
        "page_idx": item.get("page_idx"),
        "route_path": ["block_level", "sentence_level"],
        "error_trace": [{"type": "validation", "code": "SENTENCE_FALLBACK"}],
        "fallback_to": "sentence_level",
        "degradation_reason": "validation_failed_sentence_level_fallback",
        "final_status": "partially_translated",
        "segment_stats": {
            "expected": len(sentences),
            "received": len(translated_indexes),
            "missing_ids": [str(index + 1) for index in failed_indexes],
        },
        "latency_ms": 0,
        **formula_route_diagnostics(item, context=context),
    }
    validate_batch_result([item], {item["item_id"]: payload}, diagnostics=diagnostics)
    return {item["item_id"]: payload}


def sentence_level_fallback_or_keep_origin(
    item: dict,
    *,
    api_key: str,
    model: str,
    base_url: str,
    request_label: str,
    context,
    diagnostics: TranslationDiagnosticsCollector | None,
    route_path: list[str],
    sentence_level_fallback_fn=None,
) -> dict[str, dict[str, str]]:
    try:
        fallback_impl = sentence_level_fallback_fn or sentence_level_fallback
        return fallback_impl(
            item,
            api_key=api_key,
            model=model,
            base_url=base_url,
            request_label=request_label,
            context=context,
            diagnostics=diagnostics,
        )
    except Exception as sentence_exc:
        if request_label:
            print(
                f"{request_label}: sentence-level fallback failed, degrade to keep_origin: {type(sentence_exc).__name__}: {sentence_exc}",
                flush=True,
            )
        return keep_origin_payload_for_transport_error(
            item,
            context=context,
            route_path=route_path,
        )
