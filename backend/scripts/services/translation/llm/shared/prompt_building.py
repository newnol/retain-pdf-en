from __future__ import annotations

import json
import re
from typing import Any

from foundation.shared.prompt_loader import load_prompt
from services.translation.llm.decision_hints import build_decision_hints
from services.translation.llm.style_hints import structure_style_hint


_CONTEXT_PLACEHOLDER_RE = re.compile(r"<[a-z]\d+-[0-9a-z]{3}/>|@@P\d+@@|\[\[FORMULA_\d+]]")
_JSON_ONLY_INSTRUCTION = 'Return only valid JSON with the schema {"translations":[{"item_id":"...","translated_text":"..."}]}.'


def sanitize_prompt_context_text(text: str) -> str:
    sanitized = _CONTEXT_PLACEHOLDER_RE.sub(" ", str(text or ""))
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def _item_math_mode(item: dict) -> str:
    return str(item.get("math_mode", "placeholder") or "placeholder").strip() or "placeholder"


def _direct_math_guidance() -> str:
    return (
        "The direct_typst formula direct-output mode is currently enabled.\n"
        "First understand the meaning of the entire sentence, then directly output the translated text.\n"
        "For anything that semantically belongs to formulas, variables, subscripts/superscripts, mathematical expressions, chemical formulas, physical quantity symbols, or units and notations with superscripts or subscripts, proactively wrap them with `$...$`.\n"
        "Do not leave bare LaTeX-style math fragments directly in the body text.\n"
        "Do not arbitrarily place ordinary body text inside `$...$`.\n"
        "If OCR introduces obvious and localized errors in formulas — such as scrambled spaces, missing parentheses, missing braces, dropped subscripts/superscripts, or truncated commands — you may apply minimal semantic fixes before outputting so that the formula renders correctly.\n"
        "Do not fill in missing body text, do not expand the source text, and do not fabricate new scientific information.\n"
        "Do not output placeholders, JSON, tags, code blocks, or explanations — only output the final translated text.\n"
        "If you are thinking of returning {\"translated_text\": ...} or {\"translations\": [...]}, instead output only the translated body text itself."
    )


def _direct_typst_batch_user_prompt(
    batch: list[dict],
    *,
    mode: str,
) -> str:
    lines: list[str] = [
        load_prompt("translation_task.txt"),
        "",
        "Below are several paragraphs of body text to be translated.",
        "Only output the final translated text for each paragraph. Do not echo back item_id, group_id, decision, JSON, or tags.",
    ]
    for item in batch:
        lines.append("")
        lines.append(f"Source text {item['item_id']}:")
        lines.append(str(item.get("protected_source_text", "") or ""))
        style_hint = structure_style_hint(item)
        if style_hint:
            lines.append(f"Style hint: {style_hint}")
        if mode == "sci":
            decision_hints = build_decision_hints(item)
            if decision_hints:
                lines.append(f"Translation hint: {decision_hints}")
        if item.get("continuation_group"):
            lines.append("This is part of a cross-column or cross-page continuation. Understand the context and directly output the translation for this entire paragraph.")
        if item.get("continuation_prev_text"):
            context_before = sanitize_prompt_context_text(item["continuation_prev_text"])
            if context_before:
                lines.append(f"Preceding context: {context_before}")
        if item.get("continuation_next_text"):
            context_after = sanitize_prompt_context_text(item["continuation_next_text"])
            if context_after:
                lines.append(f"Following context: {context_after}")
    return "\n".join(lines).strip()


def _direct_typst_single_user_prompt(
    item: dict,
    *,
    mode: str,
) -> str:
    lines: list[str] = [
        load_prompt("translation_task.txt"),
        "",
        "Below is a paragraph of body text to be translated.",
        "Only output the final translated body text. Do not output item_id, group_id, decision, JSON, tags, code blocks, or explanations.",
        "",
        "Source text:",
        str(item.get("protected_source_text", "") or ""),
    ]
    style_hint = structure_style_hint(item)
    if style_hint:
        lines.append(f"Style hint: {style_hint}")
    if mode == "sci":
        decision_hints = build_decision_hints(item)
        if decision_hints:
            lines.append(f"Translation hint: {decision_hints}")
    if item.get("continuation_group"):
        lines.append("This is part of a cross-column or cross-page continuation. Understand the context and directly output the translation for this entire paragraph.")
    if item.get("continuation_prev_text"):
        context_before = sanitize_prompt_context_text(item["continuation_prev_text"])
        if context_before:
            lines.append(f"Preceding context: {context_before}")
    if item.get("continuation_next_text"):
        context_after = sanitize_prompt_context_text(item["continuation_next_text"])
        if context_after:
            lines.append(f"Following context: {context_after}")
    return "\n".join(lines).strip()


def _build_translation_system_prompt(
    *,
    domain_guidance: str = "",
    mode: str = "fast",
    response_style: str = "tagged",
    include_sci_decision: bool = True,
) -> str:
    system_prompt = load_prompt("translation_system.txt")
    if response_style != "json":
        system_prompt = system_prompt.replace(_JSON_ONLY_INSTRUCTION, "").strip()
    if domain_guidance.strip():
        system_prompt = f"{system_prompt}\n\nDocument-specific translation guidance:\n{domain_guidance.strip()}"
    if mode == "sci" and include_sci_decision:
        system_prompt = f"{system_prompt}\n\n{load_prompt('translation_sci_decision.txt')}"
    return system_prompt


def build_messages(
    batch: list[dict],
    domain_guidance: str = "",
    mode: str = "fast",
    response_style: str = "tagged",
) -> list[dict[str, str]]:
    direct_typst_mode = any(_item_math_mode(item) == "direct_typst" for item in batch)
    system_prompt = _build_translation_system_prompt(
        domain_guidance=domain_guidance,
        mode=mode,
        response_style=response_style,
    )
    if response_style == "json":
        system_prompt = (
            f"{system_prompt}\n\n"
            "Return only JSON matching this shape:\n"
            '{"translations":[{"item_id":"ITEM_ID","translated_text":"translated text","decision":"translate"}]}.\n'
            "Output one object for every requested item_id. Do not include markdown, code fences, or explanations."
        )
    else:
        tagged_header = "<<<ITEM item_id=ITEM_ID decision=translate>>>" if mode == "sci" else "<<<ITEM item_id=ITEM_ID>>>"
        system_prompt = (
            f"{system_prompt}\n\n"
            "Return one tagged block per item and do not return JSON or markdown.\n"
            "Use this exact format:\n"
            f"{tagged_header}\n"
            "translated text\n"
            "<<<END>>>\n"
            "Output one block for every requested item_id."
        )
    if direct_typst_mode:
        system_prompt = f"{system_prompt}\n\n{_direct_math_guidance()}"
    groups: dict[str, dict[str, Any]] = {}
    items_payload = []
    for item in batch:
        group_id = item.get("continuation_group", "")
        item_payload = {
            "item_id": item["item_id"],
            "source_text": item["protected_source_text"],
        }
        style_hint = structure_style_hint(item)
        if style_hint:
            item_payload["style_hint"] = style_hint
        if mode == "sci":
            item_payload["decision_hints"] = build_decision_hints(item)
        if group_id:
            item_payload["continuation_group"] = group_id
            if item.get("continuation_prev_text"):
                context_before = sanitize_prompt_context_text(item["continuation_prev_text"])
                if context_before:
                    item_payload["context_before"] = context_before
            if item.get("continuation_next_text"):
                context_after = sanitize_prompt_context_text(item["continuation_next_text"])
                if context_after:
                    item_payload["context_after"] = context_after
            group = groups.setdefault(group_id, {"group_id": group_id, "item_ids": [], "combined_source_text": []})
            group["item_ids"].append(item["item_id"])
            group["combined_source_text"].append(sanitize_prompt_context_text(item["protected_source_text"]))
        items_payload.append(item_payload)
    user_payload = {
        "task": load_prompt("translation_task.txt"),
        "items": items_payload,
    }
    if groups:
        user_payload["continuation_groups"] = [
            {
                "group_id": group["group_id"],
                "item_ids": group["item_ids"],
                "combined_source_text": " ".join(group["combined_source_text"]),
            }
            for group in groups.values()
        ]
    user_content = (
        _direct_typst_batch_user_prompt(batch, mode=mode)
        if direct_typst_mode
        else json.dumps(user_payload, ensure_ascii=False)
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_single_item_fallback_messages(
    item: dict,
    domain_guidance: str = "",
    mode: str = "fast",
    structured_decision: bool = False,
    response_style: str = "plain_text",
) -> list[dict[str, str]]:
    direct_typst_mode = _item_math_mode(item) == "direct_typst"
    if mode == "sci" and structured_decision:
        system_prompt = _build_translation_system_prompt(
            domain_guidance=domain_guidance,
            mode=mode,
            response_style="json" if response_style == "json" else "tagged",
        )
        if response_style == "json":
            system_prompt = (
                f"{system_prompt}\n\n"
                'Return only JSON matching {"decision":"translate","translated_text":"translated text"}. '
                "Do not include markdown, code fences, or explanations."
            )
        user_prompt = (
            _direct_typst_single_user_prompt(item, mode=mode)
            if direct_typst_mode
            else json.dumps(
                {
                    "task": load_prompt("translation_task.txt"),
                    "items": [
                        {
                            "item_id": item["item_id"],
                            "source_text": item["protected_source_text"],
                            **(
                                {"style_hint": structure_style_hint(item)}
                                if structure_style_hint(item)
                                else {}
                            ),
                            "decision_hints": build_decision_hints(item),
                        }
                    ],
                },
                ensure_ascii=False,
            )
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    system_prompt = _build_translation_system_prompt(
        domain_guidance=domain_guidance,
        mode=mode,
        response_style="json" if response_style == "json" else "plain_text",
        include_sci_decision=False,
    )
    if response_style == "json":
        fallback_system = (
            f"{system_prompt}\n"
            "You are translating exactly one item.\n"
            'Return only JSON matching {"translated_text":"translated text"}.\n'
            "Do not return markdown, code fences, labels, or explanations."
        )
    else:
        fallback_system = (
            f"{system_prompt}\n"
            "You are translating exactly one item.\n"
            "Return only the translated_text as plain text.\n"
            "Do not return JSON, markdown, code fences, labels, or explanations."
        )
    user_payload: dict[str, Any] = {
        "task": load_prompt("translation_task.txt"),
        "item": {
            "item_id": item["item_id"],
            "source_text": item["protected_source_text"],
        },
    }
    if direct_typst_mode:
        fallback_system = f"{fallback_system}\n{_direct_math_guidance()}"
    style_hint = structure_style_hint(item)
    if style_hint:
        user_payload["item"]["style_hint"] = style_hint
    if item.get("continuation_prev_text"):
        context_before = sanitize_prompt_context_text(item["continuation_prev_text"])
        if context_before:
            user_payload["item"]["context_before"] = context_before
    if item.get("continuation_next_text"):
        context_after = sanitize_prompt_context_text(item["continuation_next_text"])
        if context_after:
            user_payload["item"]["context_after"] = context_after
    if item.get("continuation_group"):
        user_payload["item"]["continuation_group"] = item["continuation_group"]
    user_prompt = (
        _direct_typst_single_user_prompt(item, mode=mode)
        if direct_typst_mode
        else json.dumps(user_payload, ensure_ascii=False)
    )
    return [
        {"role": "system", "content": fallback_system},
        {"role": "user", "content": user_prompt},
    ]
