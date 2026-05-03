import json
import sys
import tempfile
from pathlib import Path


REPO_SCRIPTS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))


from services.translation.item_reader import item_layout_role
from services.translation.item_reader import item_is_algorithm_like
from services.translation.item_reader import item_is_reference_heading_like
from services.translation.item_reader import item_policy_translate
from services.translation.item_reader import item_semantic_role
from services.translation.item_reader import item_structure_role
from services.translation.ocr.models import TextItem
from services.translation.payload.translations import ensure_translation_template
from services.translation.payload.translations import export_translation_template
from services.translation.payload.translations import load_translations


def test_item_reader_prefers_top_level_contract_fields_over_metadata() -> None:
    item = {
        "layout_role": "paragraph",
        "semantic_role": "body",
        "structure_role": "body",
        "policy_translate": True,
        "metadata": {
            "layout_role": "caption",
            "semantic_role": "reference",
            "structure_role": "reference_entry",
            "policy_translate": False,
        },
    }

    assert item_layout_role(item) == "paragraph"
    assert item_semantic_role(item) == "body"
    assert item_structure_role(item) == "body"
    assert item_policy_translate(item) is True


def test_item_reader_contract_helpers_prefer_top_level_fields() -> None:
    item = {
        "layout_role": "heading",
        "semantic_role": "reference",
        "structure_role": "reference_heading",
        "block_type": "text",
        "block_kind": "text",
        "normalized_sub_type": "algorithm",
        "metadata": {
            "layout_role": "paragraph",
            "semantic_role": "",
            "structure_role": "body",
            "normalized_sub_type": "",
        },
    }

    assert item_is_reference_heading_like(item) is True
    assert item_is_algorithm_like(item) is True


def test_export_translation_template_promotes_contract_fields_to_top_level() -> None:
    item = TextItem(
        item_id="p001-b001",
        page_idx=0,
        block_idx=1,
        block_type="text",
        bbox=[0, 0, 10, 10],
        text="Body paragraph",
        segments=[],
        lines=[],
        metadata={
            "layout_role": "paragraph",
            "semantic_role": "body",
            "structure_role": "body",
            "policy_translate": True,
        },
        block_kind="text",
        layout_role="paragraph",
        semantic_role="body",
        structure_role="body",
        policy_translate=True,
        reading_order=7,
        raw_block_type="paragraph",
        normalized_sub_type="body",
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "page-001-deepseek.json"
        export_translation_template([item], path, page_idx=0, math_mode="direct_typst")
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload[0]["block_kind"] == "text"
    assert payload[0]["layout_role"] == "paragraph"
    assert payload[0]["semantic_role"] == "body"
    assert payload[0]["structure_role"] == "body"
    assert payload[0]["policy_translate"] is True
    assert payload[0]["reading_order"] == 7
    assert payload[0]["raw_block_type"] == "paragraph"
    assert payload[0]["normalized_sub_type"] == "body"


def test_ensure_translation_template_backfills_contract_fields_without_metadata_roles() -> None:
    item = TextItem(
        item_id="p001-b001",
        page_idx=0,
        block_idx=1,
        block_type="text",
        bbox=[0, 0, 10, 10],
        text="Body paragraph",
        segments=[],
        lines=[],
        metadata={},
        block_kind="text",
        layout_role="paragraph",
        semantic_role="body",
        structure_role="body",
        policy_translate=True,
        reading_order=7,
        raw_block_type="paragraph",
        normalized_sub_type="body",
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "page-001-deepseek.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "item_id": "p001-b001",
                        "page_idx": 0,
                        "block_idx": 1,
                        "block_type": "text",
                        "bbox": [0, 0, 10, 10],
                        "source_text": "Body paragraph",
                        "protected_source_text": "Body paragraph",
                        "formula_map": [],
                        "protected_map": [],
                        "protected_translated_text": "",
                        "translated_text": "",
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        ensure_translation_template([item], path, page_idx=0, math_mode="direct_typst")
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload[0]["block_kind"] == "text"
    assert payload[0]["layout_role"] == "paragraph"
    assert payload[0]["semantic_role"] == "body"
    assert payload[0]["structure_role"] == "body"
    assert payload[0]["policy_translate"] is True
    assert payload[0]["should_translate"] is True


def test_ensure_translation_template_rebuilds_legacy_payload_instead_of_upgrading_in_place() -> None:
    item = TextItem(
        item_id="p001-b001",
        page_idx=0,
        block_idx=1,
        block_type="text",
        bbox=[0, 0, 10, 10],
        text="Body paragraph",
        segments=[],
        lines=[],
        metadata={},
        block_kind="text",
        layout_role="paragraph",
        semantic_role="body",
        structure_role="body",
        policy_translate=True,
        reading_order=7,
        raw_block_type="paragraph",
        normalized_sub_type="body",
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "page-001-deepseek.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "item_id": "legacy-item",
                        "translated_text": "legacy text",
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        ensure_translation_template([item], path, page_idx=0, math_mode="direct_typst")
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload[0]["item_id"] == "p001-b001"
    assert payload[0]["block_kind"] == "text"
    assert payload[0]["raw_block_type"] == "paragraph"
    assert payload[0]["normalized_sub_type"] == "body"


def test_load_translations_rejects_payload_missing_strict_contract_fields(tmp_path) -> None:
    path = tmp_path / "page-001-deepseek.json"
    path.write_text(
        json.dumps(
            [
                {
                    "item_id": "p001-b001",
                    "translated_text": "Translation",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        load_translations(path)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected strict contract validation failure")

    assert "missing strict contract fields" in message
