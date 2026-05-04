from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbbreviationEntry:
    source: str
    target: str = ""
    expansion: str = ""
    strategy: str = "keep"


def build_abbreviation_guidance(entries: list[AbbreviationEntry]) -> str:
    if not entries:
        return ""
    lines = ["Abbreviation preferences:"]
    for entry in entries:
        summary = f"- {entry.source}: strategy={entry.strategy}"
        if entry.target.strip():
            summary = f"{summary}, target={entry.target.strip()}"
        if entry.expansion.strip():
            summary = f"{summary}, expansion={entry.expansion.strip()}"
        lines.append(summary)
    return "\n".join(lines)
