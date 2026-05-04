from __future__ import annotations

from services.translation.llm.shared.orchestration.metadata import keep_origin_result_with_metadata


def keep_origin_payload_for_empty_translation(item: dict) -> dict[str, dict[str, str]]:
    return keep_origin_result_with_metadata(
        item=item,
        degradation_reason="empty_translation_non_body_label",
        error_taxonomy="validation",
        route_path=["block_level", "keep_origin"],
        error_trace=[{"type": "validation", "code": "EMPTY_TRANSLATION"}],
        final_status="kept_origin",
        fallback_to="keep_origin",
    )


def keep_origin_payload_for_repeated_empty_translation(item: dict) -> dict[str, dict[str, str]]:
    return keep_origin_result_with_metadata(
        item=item,
        degradation_reason="empty_translation_repeated",
        error_taxonomy="validation",
        route_path=["block_level", "keep_origin"],
        error_trace=[{"type": "validation", "code": "EMPTY_TRANSLATION"}],
        final_status="kept_origin",
        fallback_to="keep_origin",
    )


def keep_origin_payload_for_transport_error(
    item: dict,
    *,
    context=None,
    route_path: list[str] | None = None,
    degradation_reason: str = "transport_timeout_budget_exceeded",
    error_code: str = "TRANSPORT_ERROR",
    final_status: str = "kept_origin",
    fallback_to: str = "keep_origin",
    dead_letter: bool = False,
) -> dict[str, dict[str, str]]:
    return keep_origin_result_with_metadata(
        item=item,
        degradation_reason=degradation_reason,
        error_taxonomy="transport",
        route_path=route_path or ["block_level", "keep_origin"],
        error_trace=[{"type": "transport", "code": error_code}],
        final_status=final_status,
        fallback_to=fallback_to,
        context=context,
        dead_letter=dead_letter,
    )


def keep_origin_results_for_batch_transport(
    batch: list[dict],
    *,
    context,
    degradation_reason: str = "batch_transport_timeout_budget_exceeded",
) -> dict[str, dict[str, str]]:
    degraded: dict[str, dict[str, str]] = {}
    for item in batch:
        degraded.update(
            keep_origin_payload_for_transport_error(
                item,
                context=context,
                route_path=["block_level", "batched_plain", "keep_origin"],
                degradation_reason=degradation_reason,
                error_code="BATCH_TRANSPORT_ERROR",
            )
        )
    return degraded


def keep_origin_payload_for_direct_typst_validation_failure(
    item: dict,
    *,
    context,
    route_path: list[str],
    degradation_reason: str,
    error_code: str,
) -> dict[str, dict[str, str]]:
    return keep_origin_result_with_metadata(
        item=item,
        degradation_reason=degradation_reason,
        error_taxonomy="validation",
        route_path=route_path,
        error_trace=[{"type": "validation", "code": error_code}],
        final_status="kept_origin",
        fallback_to="keep_origin",
        context=context,
    )


def keep_origin_payload_for_validation(
    item: dict,
    *,
    context,
    route_path: list[str],
    degradation_reason: str,
    error_code: str = "",
) -> dict[str, dict[str, str]]:
    trace = [{"type": "validation"}]
    if error_code:
        trace[0]["code"] = error_code
    return keep_origin_result_with_metadata(
        item=item,
        degradation_reason=degradation_reason,
        error_taxonomy="validation",
        route_path=route_path,
        error_trace=trace,
        final_status="kept_origin",
        fallback_to="keep_origin",
        context=context,
    )
