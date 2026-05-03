import sys
from pathlib import Path


REPO_SCRIPTS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))


from services.translation.diagnostics.io import aggregate_payload_diagnostics


def test_aggregate_payload_diagnostics_keeps_items_with_final_status_only() -> None:
    translated_pages_map = {
        4: [
            {
                "item_id": "p004-b030",
                "final_status": "translated",
                "translated_text": "Translation",
            }
        ]
    }

    item_diagnostics, summary = aggregate_payload_diagnostics(translated_pages_map)

    assert len(item_diagnostics) == 1
    assert item_diagnostics[0]["item_id"] == "p004-b030"
    assert item_diagnostics[0]["page_idx"] == 4
    assert item_diagnostics[0]["final_status"] == "translated"
    assert summary["status_summary"]["translated"] == 1
