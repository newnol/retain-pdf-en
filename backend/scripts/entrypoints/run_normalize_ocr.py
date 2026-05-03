"""Normalize an already materialized OCR provider payload into document.v1 artifacts."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from foundation.shared.structured_errors import run_with_structured_failure
from services.document_schema.normalize_pipeline import main


if __name__ == "__main__":
    run_with_structured_failure(main, default_stage="normalization", provider="ocr")
