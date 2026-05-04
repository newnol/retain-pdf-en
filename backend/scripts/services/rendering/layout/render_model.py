from __future__ import annotations

import re
from pathlib import Path

import fitz

from services.rendering.api.render_payloads import prepare_render_payloads_by_page
from services.rendering.formula.core.markdown import build_plain_text_from_text
from services.rendering.formula.mode_router import build_item_render_markdown
from services.rendering.core.models import RenderLayoutBlock
from services.rendering.core.models import RenderPageSpec
from services.rendering.layout.font_fit import estimate_font_size_pt
from services.rendering.layout.font_fit import estimate_leading_em
from services.rendering.layout.font_fit import is_body_text_candidate
from services.rendering.layout.font_fit import is_title_like_block
from services.rendering.layout.font_fit import page_baseline_font_size
from services.rendering.layout.font_fit import resolve_font_weight
from services.rendering.layout.font_fit import resolve_title_fill_max_font_size_pt
from services.rendering.layout.title_fit import apply_title_fit_budget_to_render_blocks
from services.rendering.layout.typography.geometry import cover_bbox
from services.rendering.layout.typography.geometry import inner_bbox
from services.rendering.layout.typography.measurement import bbox_width
from services.rendering.layout.payload.text_common import get_render_formula_map
from services.rendering.layout.payload.text_common import get_render_protected_text
from services.rendering.layout.payload.text_common import is_flag_like_plain_text_block
from services.rendering.layout.payload.text_common import restore_render_protected_text
from services.translation.item_reader import item_block_kind


def _compact_zh_len(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def _should_fit_wrapped_markdown(item: dict, markdown_text: str, *, font_size_pt: float, leading_em: float) -> bool:
    inner = inner_bbox(item)
    if len(inner) != 4:
        return False
    width = max(1.0, inner[2] - inner[0])
    height = max(1.0, inner[3] - inner[1])
    zh_len = _compact_zh_len(markdown_text)
    if zh_len <= 0 or font_size_pt <= 0:
        return False
    chars_per_line = max(4.0, width / max(1.0, font_size_pt * 0.92))
    estimated_lines = max(1.0, zh_len / chars_per_line)
    estimated_height = estimated_lines * font_size_pt * (1.0 + max(0.1, leading_em))
    return estimated_height > height * 0.92


VERTICAL_COLLISION_GAP_PT = 0.9
VERTICAL_COLLISION_MIN_WIDTH_OVERLAP_RATIO = 0.6
VERTICAL_COLLISION_SOURCE_GAP_TRIGGER_PT = 3.0
VERTICAL_COLLISION_TRIGGER_RATIO = 0.98
VERTICAL_COLLISION_TIGHT_SOURCE_GAP_PT = 0.5
VERTICAL_COLLISION_SAFETY_PAD_PT = 2.0
VERTICAL_COLLISION_HEIGHT_USAGE_TRIGGER_RATIO = 0.94
VERTICAL_COLLISION_CASCADE_MIN_GAP_PT = 10.0


def _estimated_markdown_height(markdown_text: str, content_rect: list[float], *, font_size_pt: float, leading_em: float) -> float:
    if len(content_rect) != 4:
        return 0.0
    width = max(1.0, content_rect[2] - content_rect[0])
    zh_len = _compact_zh_len(markdown_text)
    if zh_len <= 0 or font_size_pt <= 0:
        return 0.0
    chars_per_line = max(4.0, width / max(1.0, font_size_pt * 0.92))
    estimated_lines = max(1.0, zh_len / chars_per_line)
    return estimated_lines * font_size_pt * (1.0 + max(0.1, leading_em))


def _horizontal_overlap_ratio(current: RenderLayoutBlock, nxt: RenderLayoutBlock) -> float:
    current_left, _current_top, current_right, _current_bottom = current.content_rect
    next_left, _next_top, next_right, _next_bottom = nxt.content_rect
    overlap_width = max(0.0, min(current_right, next_right) - max(current_left, next_left))
    min_width = max(1.0, min(current_right - current_left, next_right - next_left))
    current_cover_left, _current_cover_top, current_cover_right, _current_cover_bottom = current.background_rect
    next_cover_left, _next_cover_top, next_cover_right, _next_cover_bottom = nxt.background_rect
    cover_overlap_width = max(0.0, min(current_cover_right, next_cover_right) - max(current_cover_left, next_cover_left))
    cover_min_width = max(1.0, min(current_cover_right - current_cover_left, next_cover_right - next_cover_left))
    return max(overlap_width / min_width, cover_overlap_width / cover_min_width)


def _shift_block_vertically(block: RenderLayoutBlock, delta_pt: float) -> None:
    if abs(delta_pt) <= 0.01:
        return
    block.content_rect[1] += delta_pt
    block.content_rect[3] += delta_pt
    block.background_rect[1] += delta_pt
    block.background_rect[3] += delta_pt


def _cascade_shift_column_down(ordered: list[RenderLayoutBlock], *, start_idx: int, delta_pt: float) -> None:
    if delta_pt <= 0:
        return
    anchor = ordered[start_idx]
    for idx in range(start_idx, len(ordered)):
        block = ordered[idx]
        if _horizontal_overlap_ratio(anchor, block) < VERTICAL_COLLISION_MIN_WIDTH_OVERLAP_RATIO:
            continue
        _shift_block_vertically(block, delta_pt)


def _mark_adjacent_collision_risk(blocks: list[RenderLayoutBlock]) -> None:
    ordered = sorted(blocks, key=lambda block: (block.content_rect[1], block.content_rect[0]))
    for idx, (current, nxt) in enumerate(zip(ordered, ordered[1:])):
        current_left, current_top, current_right, current_bottom = current.content_rect
        _next_left, next_top, _next_right, _next_bottom = nxt.content_rect
        _current_cover_left, _current_cover_top, _current_cover_right, current_cover_bottom = current.background_rect
        _next_cover_left, next_cover_top, _next_cover_right, _next_cover_bottom = nxt.background_rect
        if _horizontal_overlap_ratio(current, nxt) < VERTICAL_COLLISION_MIN_WIDTH_OVERLAP_RATIO:
            continue

        source_gap = next_cover_top - current_cover_bottom
        if source_gap > VERTICAL_COLLISION_SOURCE_GAP_TRIGGER_PT:
            continue

        max_height_pt = next_top - current_top - VERTICAL_COLLISION_GAP_PT
        if max_height_pt <= 0:
            continue

        estimated_height = _estimated_markdown_height(
            current.content_text,
            current.content_rect,
            font_size_pt=current.font_size_pt,
            leading_em=current.leading_em,
        )
        current_height_pt = max(1.0, current_bottom - current_top)
        tight_source_gap = source_gap <= VERTICAL_COLLISION_TIGHT_SOURCE_GAP_PT
        height_usage_ratio = current_height_pt / max(1.0, max_height_pt)
        if (
            not tight_source_gap
            and estimated_height <= max_height_pt * VERTICAL_COLLISION_TRIGGER_RATIO
            and not (current.fit_to_box and height_usage_ratio >= VERTICAL_COLLISION_HEIGHT_USAGE_TRIGGER_RATIO)
        ):
            continue

        safety_pad_pt = max(VERTICAL_COLLISION_SAFETY_PAD_PT, min(current.font_size_pt * 0.6, 6.0))
        if tight_source_gap:
            safety_pad_pt = max(
                safety_pad_pt,
                current.font_size_pt * (1.0 + current.leading_em),
                12.0,
            )
        tightened_height_pt = min(
            max_height_pt,
            max(8.0, current_height_pt - safety_pad_pt),
        )

        current.fit_to_box = True
        current.fit_max_height_pt = min(
            max(8.0, current.fit_max_height_pt or tightened_height_pt),
            tightened_height_pt,
        )
        current.skip_reason = "adjacent_collision_risk"
        if tight_source_gap:
            desired_next_cover_top = current_cover_bottom + max(
                VERTICAL_COLLISION_CASCADE_MIN_GAP_PT,
                current.font_size_pt * (1.0 + current.leading_em),
            )
            shift_delta_pt = max(0.0, desired_next_cover_top - next_cover_top)
            _cascade_shift_column_down(ordered, start_idx=idx + 1, delta_pt=shift_delta_pt)


def _layout_block_from_item(
    item: dict,
    *,
    page_index: int,
    page_font_size: float,
    page_line_pitch: float,
    page_line_height: float,
    density_baseline: float,
    page_text_width_med: float,
) -> RenderLayoutBlock | None:
    protected_text = get_render_protected_text(item)
    if not protected_text:
        return None

    formula_map = get_render_formula_map(item)
    body_candidate = is_body_text_candidate(item, page_text_width_med)
    item_with_flag = {**item, "_is_body_text_candidate": body_candidate}
    font_size_pt = estimate_font_size_pt(
        item_with_flag,
        page_font_size,
        page_line_pitch,
        page_line_height,
        density_baseline,
    )
    leading_em = estimate_leading_em(item_with_flag, page_line_pitch, font_size_pt)
    content_kind = "plain" if item.get("_force_plain_line") or is_flag_like_plain_text_block(item) else "markdown"
    markdown_text = build_item_render_markdown(item, protected_text, formula_map)
    plain_text = build_plain_text_from_text(markdown_text)
    title_like = is_title_like_block(item)
    wrapped_markdown_candidate = content_kind == "markdown" and _should_fit_wrapped_markdown(
        item,
        markdown_text,
        font_size_pt=font_size_pt,
        leading_em=leading_em,
    )
    fit_to_box = title_like or body_candidate or wrapped_markdown_candidate
    fit_single_line = bool(title_like and content_kind == "markdown")
    fit_min_font_size_pt = font_size_pt if title_like else max(7.2, round(font_size_pt - 0.8, 2))
    fit_max_font_size_pt = resolve_title_fill_max_font_size_pt(item, font_size_pt) if title_like else font_size_pt
    fit_min_leading_em = leading_em if title_like else max(0.22, round(leading_em - 0.08, 2))
    if wrapped_markdown_candidate and not body_candidate:
        fit_min_font_size_pt = max(7.2, round(font_size_pt - 2.2, 2))
        fit_min_leading_em = max(0.18, round(leading_em - 0.2, 2))

    return RenderLayoutBlock(
        block_id=f"item-{item.get('item_id', page_index)}",
        page_index=page_index,
        background_rect=list(cover_bbox(item)),
        content_rect=list(inner_bbox(item)),
        content_kind=content_kind,
        content_text=plain_text if content_kind == "plain" else markdown_text,
        plain_text=plain_text,
        math_map=list(formula_map),
        font_size_pt=font_size_pt,
        leading_em=leading_em,
        font_weight=resolve_font_weight(item),
        fit_to_box=fit_to_box,
        fit_single_line=fit_single_line,
        fit_min_font_size_pt=fit_min_font_size_pt,
        fit_max_font_size_pt=fit_max_font_size_pt,
        fit_min_leading_em=fit_min_leading_em,
        fit_max_height_pt=max(8.0, inner_bbox(item)[3] - inner_bbox(item)[1]),
    )


def _page_text_width_med(items: list[dict]) -> float:
    text_widths = [bbox_width(item) for item in items if item_block_kind(item) == "text"]
    if not text_widths:
        return 0.0
    text_widths = sorted(text_widths)
    return text_widths[len(text_widths) // 2]


def _build_layout_blocks(items: list[dict], *, page_index: int) -> list[RenderLayoutBlock]:
    page_font_size, page_line_pitch, page_line_height, density_baseline = page_baseline_font_size(items)
    page_text_width_med = _page_text_width_med(items)
    blocks: list[RenderLayoutBlock] = []
    for item in items:
        block = _layout_block_from_item(
            item,
            page_index=page_index,
            page_font_size=page_font_size,
            page_line_pitch=page_line_pitch,
            page_line_height=page_line_height,
            density_baseline=density_baseline,
            page_text_width_med=page_text_width_med,
        )
        if block is not None:
            blocks.append(block)
    _mark_adjacent_collision_risk(blocks)
    return blocks


def _with_render_fields(items: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for item in items:
        next_item = dict(item)
        next_item["render_protected_text"] = get_render_protected_text(next_item)
        next_item["render_formula_map"] = get_render_formula_map(next_item)
        prepared.append(next_item)
    return prepared


def _layout_page_spec(
    *,
    page_index: int,
    page_width_pt: float,
    page_height_pt: float,
    items: list[dict],
    background_pdf_path: Path | None,
) -> RenderPageSpec:
    blocks = _build_layout_blocks(_with_render_fields(items), page_index=page_index)
    apply_title_fit_budget_to_render_blocks(
        blocks,
        page_width=page_width_pt,
        page_height=page_height_pt,
    )
    return RenderPageSpec(
        page_index=page_index,
        page_width_pt=page_width_pt,
        page_height_pt=page_height_pt,
        background_pdf_path=background_pdf_path,
        blocks=blocks,
    )


def build_render_page_specs(
    *,
    source_pdf_path: Path,
    translated_pages: dict[int, list[dict]],
    background_pdf_path: Path | None = None,
) -> list[RenderPageSpec]:
    prepared_pages = prepare_render_payloads_by_page(translated_pages)
    source_doc = fitz.open(source_pdf_path)
    try:
        page_specs: list[RenderPageSpec] = []
        for page_index in sorted(page_idx for page_idx in prepared_pages if 0 <= page_idx < len(source_doc)):
            page = source_doc[page_index]
            page_specs.append(
                _layout_page_spec(
                    page_index=page_index,
                    page_width_pt=page.rect.width,
                    page_height_pt=page.rect.height,
                    items=prepared_pages[page_index],
                    background_pdf_path=background_pdf_path,
                )
            )
        return page_specs
    finally:
        source_doc.close()
