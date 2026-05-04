from __future__ import annotations

"""Shared pipeline filesystem/stdout contract.

This module owns the neutral stage-level artifact names and stdout labels used
across provider, translation, and rendering workers.
"""

PIPELINE_SUMMARY_FILE_NAME = "pipeline_summary.json"
PIPELINE_EVENTS_FILE_NAME = "pipeline_events.jsonl"

STDOUT_LABEL_JOB_ROOT = "job root"
STDOUT_LABEL_SOURCE_PDF = "source pdf"
STDOUT_LABEL_LAYOUT_JSON = "layout json"
STDOUT_LABEL_NORMALIZED_DOCUMENT_JSON = "normalized document json"
STDOUT_LABEL_NORMALIZATION_REPORT_JSON = "normalization report json"
STDOUT_LABEL_SOURCE_JSON_USED = "source json used"
STDOUT_LABEL_TRANSLATIONS_DIR = "translations dir"
STDOUT_LABEL_OUTPUT_PDF = "output pdf"
STDOUT_LABEL_SUMMARY = "summary"
STDOUT_LABEL_EVENTS_JSONL = "events jsonl"


def format_stdout_kv(label: str, value: object) -> str:
    return f"{label}: {value}"
