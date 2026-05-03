"""Top-level one-command OCR-provider entry for local use.

This is the generic local entrypoint name for the current provider-backed
full workflow. The provider implementation is intentionally hidden behind
this neutral name so callers depend on the workflow contract, not the
current provider choice.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.ocr_provider.provider_pipeline import main


if __name__ == "__main__":
    main()
