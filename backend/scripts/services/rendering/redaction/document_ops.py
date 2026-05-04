from pathlib import Path

import fitz

from services.rendering.redaction.redaction_analysis import page_has_large_background_image


EDITABLE_TEXT_MIN_WORDS = 20
PSEUDO_EDITABLE_SCAN_MIN_WORDS = 80


def save_optimized_pdf(doc: fitz.Document, output_pdf_path: Path) -> None:
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    print("save optimized pdf: subset fonts", flush=True)
    doc.subset_fonts()
    print(f"save optimized pdf: writing {output_pdf_path}", flush=True)
    doc.save(
        output_pdf_path,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        use_objstms=1,
    )
    print(f"save optimized pdf: done {output_pdf_path}", flush=True)


def strip_page_links(page: fitz.Page) -> None:
    return


def page_word_count(page: fitz.Page) -> int:
    try:
        return len(page.get_text("words"))
    except Exception:
        return 0


def page_is_pseudo_editable_scan(page: fitz.Page) -> bool:
    words = page_word_count(page)
    if words < PSEUDO_EDITABLE_SCAN_MIN_WORDS:
        return False
    return page_has_large_background_image(page)


def page_has_editable_text(page: fitz.Page) -> bool:
    words = page_word_count(page)
    if words < EDITABLE_TEXT_MIN_WORDS:
        return False
    if page_is_pseudo_editable_scan(page):
        return False
    return True


def extract_single_page_pdf(source_pdf_path: Path, output_pdf_path: Path, page_idx: int) -> None:
    source_doc = fitz.open(source_pdf_path)
    output_doc = fitz.open()
    output_doc.insert_pdf(source_doc, from_page=page_idx, to_page=page_idx)
    strip_page_links(output_doc[0])
    save_optimized_pdf(output_doc, output_pdf_path)
    output_doc.close()
    source_doc.close()
