from __future__ import annotations

import time
from pathlib import Path

from runtime.pipeline.book_translation_batches import translate_pending_units
from runtime.pipeline.book_translation_pages import load_page_payloads
from runtime.pipeline.book_translation_pages import save_pages
from runtime.pipeline.book_translation_policies import apply_page_policies
from runtime.pipeline.book_translation_policies import build_page_summaries
from runtime.pipeline.book_translation_policies import finalize_page_payloads
from runtime.pipeline.book_translation_policies import review_and_apply_continuations
from services.translation.diagnostics import TranslationRunDiagnostics
from services.translation.postprocess import reconstruct_garbled_page_payloads
from services.translation.orchestration.document_orchestrator import finalize_orchestration_metadata_by_page
from services.translation.llm.shared.control_context import TranslationControlContext
from services.translation.policy import TranslationPolicyConfig
from services.translation.payload import load_translations
from services.pipeline_shared.events import emit_stage_progress
from services.pipeline_shared.events import emit_stage_transition


def _format_translation_progress_message(current: int, total: int, touched_pages: set[int]) -> str:
    if touched_pages:
        sorted_pages = sorted(page_idx + 1 for page_idx in touched_pages)
        if len(sorted_pages) == 1:
            page_suffix = f"(Recent page: {sorted_pages[0]}）"
        else:
            preview = ",".join(str(page) for page in sorted_pages[:4])
            if len(sorted_pages) > 4:
                preview = f"{preview}..."
            page_suffix = f"(Recent page: {preview}）"
    else:
        page_suffix = ""
    return f"Completed batch {current}/{total} of translation{page_suffix}"


def translate_book_with_global_continuations(
    *,
    data: dict,
    output_dir: Path,
    page_indices: range,
    api_key: str,
    batch_size: int,
    workers: int,
    model: str,
    base_url: str,
    mode: str,
    classify_batch_size: int,
    skip_title_translation: bool,
    sci_cutoff_page_idx: int | None,
    sci_cutoff_block_idx: int | None,
    policy_config: TranslationPolicyConfig | None = None,
    domain_guidance: str = "",
    translation_context: TranslationControlContext | None = None,
    run_diagnostics: TranslationRunDiagnostics | None = None,
) -> tuple[dict[int, list[dict]], list[dict]]:
    if translation_context is not None:
        domain_guidance = translation_context.merged_guidance
    elif not domain_guidance and policy_config is not None:
        domain_guidance = policy_config.domain_guidance

    translation_paths, page_payloads = load_page_payloads(
        data=data,
        output_dir=output_dir,
        page_indices=page_indices,
        math_mode=(policy_config.math_mode if policy_config is not None else "placeholder"),
    )
    stage_started = time.perf_counter()
    finalize_page_payloads(
        page_payloads=page_payloads,
        translation_paths=translation_paths,
    )
    emit_stage_progress(
        stage="continuation_review",
        message="Initial continuous segment consolidation completed",
        elapsed_ms=int((time.perf_counter() - stage_started) * 1000),
        payload={"page_count": len(page_payloads)},
    )
    print(f"book: initial continuation pass in {time.perf_counter() - stage_started:.2f}s", flush=True)
    if policy_config is None or policy_config.enable_candidate_continuation_review:
        review_started = time.perf_counter()
        emit_stage_transition(
            stage="continuation_review",
            message="Starting cross-column/cross-page continuous segment review",
            progress_current=0,
            progress_total=len(page_payloads),
        )
        if run_diagnostics is not None:
            run_diagnostics.mark_phase_start("continuation_review")
        review_and_apply_continuations(
            page_payloads=page_payloads,
            translation_paths=translation_paths,
            api_key=api_key,
            model=model,
            base_url=base_url,
            workers=workers,
        )
        if run_diagnostics is not None:
            run_diagnostics.mark_phase_end("continuation_review")
        emit_stage_progress(
            stage="continuation_review",
            message="Cross-column/cross-page continuous segment review completed",
            progress_current=len(page_payloads),
            progress_total=len(page_payloads),
            elapsed_ms=int((time.perf_counter() - review_started) * 1000),
        )
        print(f"book: continuation review in {time.perf_counter() - review_started:.2f}s", flush=True)

    policy_started = time.perf_counter()
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_start("page_policies")
    emit_stage_transition(
        stage="page_policies",
        message="Starting page strategy and block classification",
        progress_current=0,
        progress_total=len(page_payloads),
    )
    print("book: page policies start", flush=True)
    print(f"book: page policies mode={mode} total_pages={len(page_payloads)}", flush=True)
    classified_items = apply_page_policies(
        page_payloads=page_payloads,
        mode=mode,
        classify_batch_size=max(1, classify_batch_size),
        workers=max(1, workers),
        api_key=api_key,
        model=model,
        base_url=base_url,
        skip_title_translation=skip_title_translation,
        sci_cutoff_page_idx=sci_cutoff_page_idx,
        sci_cutoff_block_idx=sci_cutoff_block_idx,
        policy_config=policy_config,
    )
    if classified_items:
        print(f"book: classified {classified_items} items", flush=True)
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_end("page_policies")
    emit_stage_progress(
        stage="page_policies",
        message="Page strategy and block classification completed",
        progress_current=len(page_payloads),
        progress_total=len(page_payloads),
        elapsed_ms=int((time.perf_counter() - policy_started) * 1000),
        payload={"classified_items": classified_items},
    )
    print(f"book: page policies in {time.perf_counter() - policy_started:.2f}s", flush=True)
    finalize_orchestration_metadata_by_page(page_payloads)
    save_pages(page_payloads, translation_paths)

    translate_started = time.perf_counter()
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_start("translation_batches")
    emit_stage_transition(
        stage="translating",
        message="Starting batch translation",
    )
    batch_summary = translate_pending_units(
        page_payloads=page_payloads,
        translation_paths=translation_paths,
        batch_size=batch_size,
        workers=max(1, workers),
        api_key=api_key,
        model=model,
        base_url=base_url,
        domain_guidance=domain_guidance,
        mode=mode,
        translation_context=translation_context,
        progress_callback=lambda current, total, touched_pages: emit_stage_progress(
            stage="translating",
            message=_format_translation_progress_message(current, total, touched_pages),
            progress_current=current,
            progress_total=total,
            payload={
                "touched_page_indexes": sorted(touched_pages),
                "touched_page_numbers": [page_idx + 1 for page_idx in sorted(touched_pages)],
            },
        ),
    )
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_end("translation_batches")
        run_diagnostics.set_effective_translation_batch_size(batch_summary["effective_batch_size"])
        run_diagnostics.set_workload(
            pending_items=batch_summary["pending_items"],
            total_batches=batch_summary["total_batches"],
        )
    emit_stage_progress(
        stage="translating",
        message="Translation batch completed",
        progress_current=batch_summary["total_batches"],
        progress_total=batch_summary["total_batches"],
        elapsed_ms=int((time.perf_counter() - translate_started) * 1000),
        payload={
            "pending_items": batch_summary["pending_items"],
            "effective_batch_size": batch_summary["effective_batch_size"],
        },
    )
    print(f"book: translation batches in {time.perf_counter() - translate_started:.2f}s", flush=True)

    reconstruct_started = time.perf_counter()
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_start("garbled_reconstruction")
    emit_stage_transition(
        stage="translating",
        message="Starting garbled candidate segment repair",
    )
    summary = reconstruct_garbled_page_payloads(
        page_payloads,
        api_key=api_key,
        model=model,
        base_url=base_url,
        workers=workers,
    )
    if run_diagnostics is not None:
        run_diagnostics.mark_phase_end("garbled_reconstruction")
    reconstructed_items = int(summary["garbled_reconstructed"])
    garbled_candidates = int(summary["garbled_candidates"])
    dirty_pages = {int(page_idx) for page_idx in summary.get("dirty_pages", [])}
    if dirty_pages:
        save_pages(page_payloads, translation_paths, dirty_pages)
    emit_stage_progress(
        stage="translating",
        message="Garbled candidate segment repair completed",
        elapsed_ms=int((time.perf_counter() - reconstruct_started) * 1000),
        payload={
            "garbled_candidates": garbled_candidates,
            "garbled_reconstructed": reconstructed_items,
            "dirty_pages": sorted(dirty_pages),
        },
    )
    print(
        f"book: garbled reconstruction candidates={garbled_candidates} reconstructed={reconstructed_items} "
        f"in {time.perf_counter() - reconstruct_started:.2f}s",
        flush=True,
    )

    translated_pages_map = {page_idx: load_translations(translation_paths[page_idx]) for page_idx in sorted(page_payloads)}
    summaries = build_page_summaries(
        translated_pages_map=translated_pages_map,
        translation_paths=translation_paths,
    )
    return translated_pages_map, summaries
