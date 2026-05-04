from __future__ import annotations

import base64
from pathlib import Path

import requests


def job_markdown_dir(job_root: Path) -> Path:
    return job_root / "md"


def job_markdown_images_dir(job_root: Path) -> Path:
    return job_markdown_dir(job_root) / "images"


def decode_paddle_markdown_image(payload: str) -> bytes:
    value = str(payload or "").strip()
    if not value:
        raise RuntimeError("empty markdown image payload")
    if value.startswith(("http://", "https://")):
        response = requests.get(value, timeout=300)
        response.raise_for_status()
        return response.content
    if value.startswith("data:") and "," in value:
        _, encoded = value.split(",", 1)
        return base64.b64decode(encoded)
    return base64.b64decode(value)


def materialize_paddle_markdown_artifacts(*, payload: dict, job_root: Path) -> Path | None:
    layout_results = payload.get("layoutParsingResults") or []
    if not isinstance(layout_results, list) or not layout_results:
        return None

    markdown_dir = job_markdown_dir(job_root)
    images_root = job_markdown_images_dir(job_root)
    page_texts: list[str] = []
    wrote_anything = False

    for page_index, page_payload in enumerate(layout_results, start=1):
        if not isinstance(page_payload, dict):
            continue
        markdown = page_payload.get("markdown") or {}
        if not isinstance(markdown, dict):
            continue
        text = str(markdown.get("text") or "")
        images = markdown.get("images") or {}
        if not text.strip() and not images:
            continue

        remapped_text = text
        if isinstance(images, dict) and images:
            for raw_rel_path, raw_image_payload in images.items():
                rel_path = str(raw_rel_path or "").strip().lstrip("/")
                if not rel_path:
                    continue
                target_rel_path = Path(f"page-{page_index}") / rel_path
                target_path = images_root / target_rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(decode_paddle_markdown_image(str(raw_image_payload or "")))
                normalized_source = rel_path.replace("\\", "/")
                normalized_target = target_rel_path.as_posix()
                remapped_text = remapped_text.replace(normalized_source, normalized_target)
                wrote_anything = True

        if remapped_text.strip():
            page_texts.append(remapped_text.strip())
            wrote_anything = True

    if not wrote_anything:
        return None

    markdown_dir.mkdir(parents=True, exist_ok=True)
    full_md_path = markdown_dir / "full.md"
    full_md_path.write_text("\n\n".join(page_texts).strip() + "\n", encoding="utf-8")
    return full_md_path
