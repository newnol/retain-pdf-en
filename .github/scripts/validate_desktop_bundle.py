from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the generated desktop bundle manifest.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to desktop/app/backend/bundle-manifest.json",
    )
    parser.add_argument(
        "--min-fonts",
        type=int,
        default=3,
        help="Minimum number of bundled fonts expected in the manifest.",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    require(payload.get("rustApiBinaryBundled") is True, "bundle manifest missing Rust API binary")
    require(payload.get("pythonBundled") is True, "bundle manifest missing bundled Python runtime")
    require(payload.get("typstBundled") is True, "bundle manifest missing Typst runtime")
    require(payload.get("typstPackagesBundled") is True, "bundle manifest missing Typst packages")
    require(bool(payload.get("bundledPythonImportCheck")), "bundle manifest missing Python import check result")
    if payload.get("targetPlatformName") == "mac":
        require(bool(payload.get("bundledPythonHome")), "mac bundle manifest missing Python framework home")

    bundled_fonts = payload.get("bundledFonts") or []
    require(
        isinstance(bundled_fonts, list) and len(bundled_fonts) >= args.min_fonts,
        "bundle manifest missing bundled fonts",
    )

    print(f"desktop bundle manifest OK: {manifest_path}")


if __name__ == "__main__":
    main()
