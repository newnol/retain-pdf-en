#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "backend" / "scripts"

PIPELINE_ROOT = SCRIPTS_ROOT / "runtime" / "pipeline"
ENTRYPOINTS_ROOT = SCRIPTS_ROOT / "entrypoints"
OCR_PROVIDER_ROOT = SCRIPTS_ROOT / "services" / "ocr_provider"
TRANSLATION_ROOT = SCRIPTS_ROOT / "services" / "translation"
RENDERING_ROOT = SCRIPTS_ROOT / "services" / "rendering"

PROVIDER_PRIVATE_IMPORT_PATTERNS = (
    "from services.ocr_provider",
    "import services.ocr_provider",
    "from services.mineru",
    "import services.mineru",
)
PROVIDER_RAW_TOKENS = (
    "layoutParsingResults",
    "prunedResult",
    "content_list",
)
PROVIDER_ADAPTER_IMPORT_PATTERNS = (
    "from services.document_schema.provider_adapters",
    "import services.document_schema.provider_adapters",
)
OCR_PROVIDER_FORBIDDEN_IMPORT_PATTERNS = (
    "from runtime.pipeline",
    "import runtime.pipeline",
    "from services.translation",
    "import services.translation",
    "from services.rendering",
    "import services.rendering",
)
OCR_PROVIDER_STABLE_ENTRYPOINT = SCRIPTS_ROOT / "services" / "ocr_provider" / "provider_pipeline.py"
OCR_PROVIDER_PACKAGE_INIT = SCRIPTS_ROOT / "services" / "ocr_provider" / "__init__.py"
OCR_PROVIDER_COMPAT_SYMBOLS = (
    "adapt_path_to_document_v1_with_report",
    "validate_saved_document_path",
    "build_paddle_lines",
    "tighten_paddle_text_bbox",
    "save_normalized_document_for_paddle",
)
TRANSLATE_ONLY_ENTRYPOINT = SCRIPTS_ROOT / "services" / "translation" / "translate_only_pipeline.py"
FROM_OCR_ENTRYPOINT = SCRIPTS_ROOT / "services" / "translation" / "from_ocr_pipeline.py"

ENTRYPOINT_IMPORT_ALLOWLIST: dict[Path, tuple[str, ...]] = {
    Path("build_book.py"): ("from runtime.pipeline.book_pipeline import",),
    Path("build_page.py"): (
        "from services.translation.ocr.json_extractor import",
        "from services.rendering.api.pdf_overlay import",
        "from services.rendering.api.typst_page_renderer import",
        "from services.translation.payload import",
    ),
    Path("diagnose_failure_with_ai.py"): (
        "from services.translation.llm.shared.provider_runtime import",
        "from services.translation.llm.shared.response_parsing import",
    ),
    Path("run_book.py"): ("from services.translation.from_ocr_pipeline import main",),
    Path("run_document_flow.py"): (
        "from runtime.pipeline.book_pipeline import",
        "from services.translation.llm.shared.provider_runtime import",
    ),
    Path("run_normalize_ocr.py"): ("from services.document_schema.normalize_pipeline import main",),
    Path("run_provider_case.py"): ("from services.ocr_provider.provider_pipeline import main",),
    Path("run_provider_ocr.py"): ("from services.ocr_provider.provider_pipeline import main",),
    Path("run_render_only.py"): ("from services.rendering.render_only_pipeline import main",),
    Path("run_translate_from_ocr.py"): ("from services.translation.from_ocr_pipeline import main",),
    Path("run_translate_only.py"): ("from services.translation.translate_only_pipeline import main",),
    Path("translate_book.py"): ("from services.translation.translate_only_pipeline import main",),
    Path("translate_page.py"): (
        "from services.translation.ocr.json_extractor import",
        "from services.translation.llm.shared.provider_runtime import",
        "from services.translation.workflow import",
    ),
    Path("validate_document_schema.py"): ("from services.document_schema import",),
}


def scan_py_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if "__pycache__" in rel_parts or ".ipynb_checkpoints" in rel_parts:
            continue
        paths.append(path)
    return sorted(paths)


def rel(path: Path) -> Path:
    return path.relative_to(SCRIPTS_ROOT)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_pipeline_provider_leaks(errors: list[str]) -> None:
    for path in scan_py_files(PIPELINE_ROOT):
        text = read_text(path)
        rel_path = rel(path)
        for pattern in PROVIDER_PRIVATE_IMPORT_PATTERNS:
            if pattern in text:
                errors.append(
                    f"{rel_path}: runtime/pipeline must not import provider-specific services directly"
                )
                break
        for token in PROVIDER_RAW_TOKENS:
            if token in text:
                errors.append(
                    f"{rel_path}: runtime/pipeline must not understand provider raw token '{token}'"
                )
        for pattern in PROVIDER_ADAPTER_IMPORT_PATTERNS:
            if pattern in text:
                errors.append(
                    f"{rel_path}: runtime/pipeline must not depend on document_schema provider adapters directly"
                )
                break


def check_service_provider_raw_leaks(errors: list[str]) -> None:
    guarded_roots = (TRANSLATION_ROOT, RENDERING_ROOT)
    for root in guarded_roots:
        for path in scan_py_files(root):
            text = read_text(path)
            rel_path = rel(path)
            for pattern in PROVIDER_PRIVATE_IMPORT_PATTERNS + PROVIDER_ADAPTER_IMPORT_PATTERNS:
                if pattern in text:
                    errors.append(
                        f"{rel_path}: translation/rendering services must not depend on provider-specific raw adapters"
                    )
                    break
            for token in PROVIDER_RAW_TOKENS:
                if token in text:
                    errors.append(
                        f"{rel_path}: translation/rendering services must not consume provider raw token '{token}'"
                    )


def check_entrypoint_stable_imports(errors: list[str]) -> None:
    import_pattern = re.compile(r"^from\s+([A-Za-z0-9_\.]+)\s+import\s+(.+)$", re.MULTILINE)
    for path in scan_py_files(ENTRYPOINTS_ROOT):
        rel_name = path.relative_to(ENTRYPOINTS_ROOT)
        allowed_prefixes = ENTRYPOINT_IMPORT_ALLOWLIST.get(rel_name)
        if allowed_prefixes is None:
            errors.append(f"entrypoints/{rel_name}: missing explicit import allowlist entry in check_pipeline_architecture.py")
            continue
        text = read_text(path)
        for match in import_pattern.finditer(text):
            stmt = f"from {match.group(1)} import {match.group(2)}"
            if match.group(1).startswith(("foundation.", "pathlib", "__future__")):
                continue
            if any(stmt.startswith(prefix) for prefix in allowed_prefixes):
                continue
            errors.append(
                f"entrypoints/{rel_name}: entrypoint should import only its stable top-level pipeline/service entry, found '{stmt}'"
            )


def check_ocr_provider_boundaries(errors: list[str]) -> None:
    for path in scan_py_files(OCR_PROVIDER_ROOT):
        text = read_text(path)
        rel_path = rel(path)
        if path != OCR_PROVIDER_STABLE_ENTRYPOINT:
            for pattern in OCR_PROVIDER_FORBIDDEN_IMPORT_PATTERNS:
                if pattern in text:
                    errors.append(
                        f"{rel_path}: provider implementation modules must not depend on runtime/translation/rendering layers"
                    )
                    break

    init_text = read_text(OCR_PROVIDER_PACKAGE_INIT)
    if "from . import provider_pipeline" not in init_text:
        errors.append(
            "services/ocr_provider/__init__.py: package must explicitly re-export provider_pipeline"
        )
    if '__all__ = ["provider_pipeline"]' not in init_text:
        errors.append(
            "services/ocr_provider/__init__.py: package must pin provider_pipeline as explicit public surface"
        )

    entry_text = read_text(OCR_PROVIDER_STABLE_ENTRYPOINT)
    if "from runtime.pipeline.book_pipeline import run_book_pipeline" not in entry_text:
        errors.append(
            "services/ocr_provider/provider_pipeline.py: stable provider entry must own the handoff to run_book_pipeline"
        )
    for symbol in OCR_PROVIDER_COMPAT_SYMBOLS:
        if f"{symbol}" not in entry_text:
            errors.append(
                f"services/ocr_provider/provider_pipeline.py: stable provider entry must preserve compat symbol '{symbol}'"
            )


def check_translation_worker_protocol(errors: list[str]) -> None:
    translate_only_text = read_text(TRANSLATE_ONLY_ENTRYPOINT)
    if "PipelineEventWriter(" not in translate_only_text:
        errors.append(
            "services/translation/translate_only_pipeline.py: translate-only worker must initialize PipelineEventWriter"
        )
    if "STDOUT_LABEL_EVENTS_JSONL" not in translate_only_text:
        errors.append(
            "services/translation/translate_only_pipeline.py: translate-only worker must publish pipeline_events.jsonl via stdout contract"
        )
    if 'artifact_key="pipeline_events_jsonl"' not in translate_only_text:
        errors.append(
            "services/translation/translate_only_pipeline.py: translate-only worker must publish pipeline_events_jsonl artifact"
        )
    if 'artifact_key="translation_diagnostics_json"' not in translate_only_text:
        errors.append(
            "services/translation/translate_only_pipeline.py: translate-only worker must publish translation_diagnostics_json artifact"
        )
    if '"translation_diagnostics.json"' not in translate_only_text:
        errors.append(
            "services/translation/translate_only_pipeline.py: translate-only worker must keep translation_diagnostics.json as stable diagnostics output"
        )

    from_ocr_text = read_text(FROM_OCR_ENTRYPOINT)
    if "PipelineEventWriter(" not in from_ocr_text:
        errors.append(
            "services/translation/from_ocr_pipeline.py: translate-from-ocr worker must initialize PipelineEventWriter"
        )
    if "STDOUT_LABEL_EVENTS_JSONL" not in from_ocr_text:
        errors.append(
            "services/translation/from_ocr_pipeline.py: translate-from-ocr worker must publish pipeline_events.jsonl via stdout contract"
        )
    if 'artifact_key="pipeline_events_jsonl"' not in from_ocr_text:
        errors.append(
            "services/translation/from_ocr_pipeline.py: translate-from-ocr worker must publish pipeline_events_jsonl artifact"
        )


def main() -> int:
    errors: list[str] = []
    check_pipeline_provider_leaks(errors)
    check_service_provider_raw_leaks(errors)
    check_entrypoint_stable_imports(errors)
    check_ocr_provider_boundaries(errors)
    check_translation_worker_protocol(errors)
    if errors:
        print("pipeline architecture check failed:", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("pipeline architecture check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
