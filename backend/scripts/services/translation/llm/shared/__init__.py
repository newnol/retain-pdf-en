from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "FORMULA_SEGMENT_STRATEGY_VERSION": ("services.translation.llm.shared.cache", "FORMULA_SEGMENT_STRATEGY_VERSION"),
    "PLAIN_TEXT_STRATEGY_VERSION": ("services.translation.llm.shared.cache", "PLAIN_TEXT_STRATEGY_VERSION"),
    "TRANSLATION_PROTOCOL_VERSION": ("services.translation.llm.shared.cache", "TRANSLATION_PROTOCOL_VERSION"),
    "cache_key_for_item": ("services.translation.llm.shared.cache", "cache_key_for_item"),
    "load_cached_translation": ("services.translation.llm.shared.cache", "load_cached_translation"),
    "split_cached_batch": ("services.translation.llm.shared.cache", "split_cached_batch"),
    "store_cached_batch": ("services.translation.llm.shared.cache", "store_cached_batch"),
    "store_cached_translation": ("services.translation.llm.shared.cache", "store_cached_translation"),
    "BatchPolicy": ("services.translation.llm.shared.control_context", "BatchPolicy"),
    "EngineProfile": ("services.translation.llm.shared.control_context", "EngineProfile"),
    "FallbackPolicy": ("services.translation.llm.shared.control_context", "FallbackPolicy"),
    "PlaceholderPolicy": ("services.translation.llm.shared.control_context", "PlaceholderPolicy"),
    "RetrievalEvidence": ("services.translation.llm.shared.control_context", "RetrievalEvidence"),
    "SegmentationPolicy": ("services.translation.llm.shared.control_context", "SegmentationPolicy"),
    "TimeoutPolicy": ("services.translation.llm.shared.control_context", "TimeoutPolicy"),
    "TranslationControlContext": ("services.translation.llm.shared.control_context", "TranslationControlContext"),
    "build_translation_control_context": ("services.translation.llm.shared.control_context", "build_translation_control_context"),
    "resolve_engine_profile": ("services.translation.llm.shared.control_context", "resolve_engine_profile"),
    "CONTINUATION_REVIEW_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "CONTINUATION_REVIEW_RESPONSE_SCHEMA"),
    "DOMAIN_CONTEXT_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "DOMAIN_CONTEXT_RESPONSE_SCHEMA"),
    "FORMULA_SEGMENT_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "FORMULA_SEGMENT_RESPONSE_SCHEMA"),
    "GARBLED_RECONSTRUCTION_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "GARBLED_RECONSTRUCTION_RESPONSE_SCHEMA"),
    "TRANSLATION_BATCH_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "TRANSLATION_BATCH_RESPONSE_SCHEMA"),
    "TRANSLATION_SINGLE_DECISION_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "TRANSLATION_SINGLE_DECISION_RESPONSE_SCHEMA"),
    "TRANSLATION_SINGLE_TEXT_RESPONSE_SCHEMA": ("services.translation.llm.shared.structured_models", "TRANSLATION_SINGLE_TEXT_RESPONSE_SCHEMA"),
    "extract_string_fields": ("services.translation.llm.shared.structured_output", "extract_string_fields"),
    "parse_structured_json": ("services.translation.llm.shared.structured_output", "parse_structured_json"),
    "parse_continuation_review_response": ("services.translation.llm.shared.structured_parsers", "parse_continuation_review_response"),
    "parse_domain_context_response": ("services.translation.llm.shared.structured_parsers", "parse_domain_context_response"),
    "parse_garbled_reconstruction_response": ("services.translation.llm.shared.structured_parsers", "parse_garbled_reconstruction_response"),
    "ACTIVE_PROVIDER": ("services.translation.llm.shared.provider_runtime", "ACTIVE_PROVIDER"),
    "ACTIVE_PROVIDER_FAMILY": ("services.translation.llm.shared.provider_runtime", "ACTIVE_PROVIDER_FAMILY"),
    "extract_json_text": ("services.translation.llm.shared.response_parsing", "extract_json_text"),
    "extract_single_item_translation_text": ("services.translation.llm.shared.response_parsing", "extract_single_item_translation_text"),
    "unwrap_translation_shell": ("services.translation.llm.shared.response_parsing", "unwrap_translation_shell"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
