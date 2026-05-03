import sys
from pathlib import Path


REPO_SCRIPTS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))


from services.translation.payload.parts.apply import apply_translated_text_map
from services.translation.payload.translations import load_translations


def test_apply_translated_text_map_unwraps_json_string_result() -> None:
    payload = [
        {
            "item_id": "demo",
            "should_translate": True,
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
        }
    ]
    translated = {
        "demo": '{"translated_text":"Repaired text"}',
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["translated_text"] == "Repaired text"
    assert payload[0]["protected_translated_text"] == "Repaired text"
    assert payload[0]["translation_unit_translated_text"] == "Repaired text"
    assert payload[0]["translation_unit_protected_translated_text"] == "Repaired text"


def test_apply_translated_text_map_unwraps_json_string_keep_origin() -> None:
    payload = [
        {
            "item_id": "demo",
            "should_translate": True,
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
        }
    ]
    translated = {
        "demo": '{"decision":"keep_origin","translated_text":"ignored"}',
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["final_status"] == "kept_origin"
    assert payload[0]["translated_text"] == ""


def test_apply_translated_text_map_unwraps_batch_json_string_result() -> None:
    payload = [
        {
            "item_id": "demo",
            "should_translate": True,
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
        }
    ]
    translated = {
        "demo": '{"translations":[{"item_id":"demo","translated_text":"Text in batch shell"}]}',
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["translated_text"] == "Text in batch shell"
    assert payload[0]["translation_unit_translated_text"] == "Text in batch shell"


def test_apply_translated_text_map_splits_group_translation_back_to_members() -> None:
    payload = [
        {
            "item_id": "p002-b001",
            "translation_unit_id": "__cg__:cg-002-002",
            "translation_unit_kind": "group",
            "should_translate": True,
            "source_text": "The advancement of complex computer programs...",
            "protected_source_text": "The advancement of complex computer programs...",
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
            "group_protected_map": [],
            "group_formula_map": [],
        },
        {
            "item_id": "p002-b002",
            "translation_unit_id": "__cg__:cg-002-002",
            "translation_unit_kind": "group",
            "should_translate": True,
            "source_text": "and energy levels; (2) revealing the surface reactivities...",
            "protected_source_text": "and energy levels; (2) revealing the surface reactivities...",
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
            "group_protected_map": [],
            "group_formula_map": [],
        },
    ]
    translated = {
        "__cg__:cg-002-002": "With the development of more powerful complex computer programs and material simulation methods, they have become important tools for materials researchers. DFT calculations play an important role in the field of photocatalysis.",
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["translation_unit_translated_text"].startswith("With the development of more powerful complex computer programs")
    assert payload[0]["translated_text"]
    assert payload[1]["translated_text"]
    assert payload[0]["translated_text"] != payload[1]["translated_text"]


def test_apply_translated_text_map_preserves_group_result_status_and_diagnostics() -> None:
    payload = [
        {
            "item_id": "p004-b030",
            "page_idx": 4,
            "translation_unit_id": "__cg__:cg-004-005",
            "translation_unit_kind": "group",
            "translation_unit_member_ids": ["p004-b030", "p004-b031"],
            "should_translate": True,
            "source_text": "Following Stewart's Gaussian expansions,",
            "protected_source_text": "Following Stewart's Gaussian expansions,",
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
            "group_protected_map": [],
            "group_formula_map": [],
        },
        {
            "item_id": "p004-b031",
            "page_idx": 5,
            "translation_unit_id": "__cg__:cg-004-005",
            "translation_unit_kind": "group",
            "translation_unit_member_ids": ["p004-b030", "p004-b031"],
            "should_translate": True,
            "source_text": "which are used to approximate a spherical Slater-type orbital.",
            "protected_source_text": "which are used to approximate a spherical Slater-type orbital.",
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
            "group_protected_map": [],
            "group_formula_map": [],
        },
    ]
    translated = {
        "__cg__:cg-004-005": {
            "translated_text": "According to Stewart's Gaussian expansion, ϕκ represents contracted Gaussian atomic orbitals, used to approximate spherical Slater-type orbitals.",
            "final_status": "partially_translated",
            "translation_diagnostics": {
                "route_path": ["block_level", "continuation_group"],
                "final_status": "partially_translated",
            },
        }
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["final_status"] == "partially_translated"
    assert payload[1]["final_status"] == "partially_translated"
    assert payload[0]["translation_diagnostics"]["item_id"] == "p004-b030"
    assert payload[1]["translation_diagnostics"]["item_id"] == "p004-b031"
    assert payload[0]["translation_diagnostics"]["page_idx"] == 4
    assert payload[1]["translation_diagnostics"]["page_idx"] == 5


def test_apply_translated_text_map_applies_single_result_without_collapsing_preserved_group() -> None:
    payload = [
        {
            "item_id": "p002-b001",
            "translation_unit_id": "__cg__:cg-stale",
            "translation_unit_kind": "group",
            "translation_unit_member_ids": ["p002-b001", "ghost"],
            "continuation_group": "cg-stale",
            "should_translate": True,
            "source_text": "Body text.",
            "protected_source_text": "Body text.",
            "protected_map": [],
            "formula_map": [],
            "translation_unit_protected_map": [],
            "translation_unit_formula_map": [],
            "group_protected_source_text": "stale",
            "group_formula_map": [{"placeholder": "<f1-a7c/>"}],
            "group_protected_map": [{"token_tag": "<f1-a7c/>"}],
            "group_protected_translated_text": "stale",
            "group_translated_text": "stale",
        }
    ]
    translated = {
        "p002-b001": "Repaired single-member text",
    }

    apply_translated_text_map(payload, translated)

    assert payload[0]["translation_unit_id"] == "__cg__:cg-stale"
    assert payload[0]["translation_unit_kind"] == "group"
    assert payload[0]["translation_unit_member_ids"] == ["p002-b001"]
    assert payload[0]["translated_text"] == "Repaired single-member text"


def test_load_translations_sanitizes_persisted_json_shell(tmp_path) -> None:
    path = tmp_path / "page-030-deepseek.json"
    path.write_text(
        """
        [
          {
            "item_id": "p030-b010",
            "translated_text": "{\\"translations\\":[{\\"item_id\\":\\"p030-b010\\",\\"translated_text\\":\\"(1) Computational efficiency, cost, and accuracy.\\"}]}",
            "protected_translated_text": "{\\"translated_text\\":\\"(1) Computational efficiency, cost, and accuracy.\\"}"
          }
        ]
        """,
        encoding="utf-8",
    )

    payload = load_translations(path, strict_contract=False)

    assert payload[0]["translated_text"] == "(1) Computational efficiency, cost, and accuracy."
    assert payload[0]["protected_translated_text"] == "(1) Computational efficiency, cost, and accuracy."
    assert "translations" not in path.read_text(encoding="utf-8")
