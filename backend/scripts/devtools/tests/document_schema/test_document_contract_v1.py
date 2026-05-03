from pathlib import Path

import sys


REPO_SCRIPTS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))


from services.document_schema.adapters import adapt_payload_to_document_v1
from services.document_schema.providers import PROVIDER_GENERIC_FLAT_OCR
from services.document_schema.validator import validate_document_payload


def _build_generic_payload() -> dict:
    return {
        "provider": PROVIDER_GENERIC_FLAT_OCR,
        "pages": [
            {
                "width": 400.0,
                "height": 500.0,
                "unit": "pt",
                "blocks": [
                    {
                        "type": "text",
                        "sub_type": "title",
                        "bbox": [20, 20, 320, 56],
                        "text": "Document Title",
                        "lines": [],
                        "segments": [],
                        "tags": ["title"],
                        "derived": {"role": "title", "by": "", "confidence": 0.0},
                        "metadata": {},
                    },
                    {
                        "type": "text",
                        "sub_type": "abstract",
                        "bbox": [20, 70, 260, 90],
                        "text": "This is the abstract body.",
                        "lines": [],
                        "segments": [],
                        "tags": [],
                        "derived": {"role": "", "by": "", "confidence": 0.0},
                        "metadata": {},
                    },
                    {
                        "type": "image",
                        "sub_type": "figure",
                        "bbox": [40, 120, 160, 240],
                        "text": "",
                        "lines": [],
                        "segments": [],
                        "tags": ["image"],
                        "derived": {"role": "", "by": "", "confidence": 0.0},
                        "metadata": {
                            "asset_key": "img_001",
                            "asset_url": "https://example.test/img_001.png",
                            "asset_kind": "remote_image",
                        },
                    },
                ],
            }
        ],
    }


def test_document_contract_v1_fields_are_present_and_valid() -> None:
    document = adapt_payload_to_document_v1(
        payload=_build_generic_payload(),
        provider=PROVIDER_GENERIC_FLAT_OCR,
        document_id="contract-doc",
        source_json_path=Path("/tmp/contract-doc.json"),
    )

    validate_document_payload(document)

    assert document["doc_id"] == "contract-doc"
    assert document["assets"] == {
        "img_001": {
            "kind": "image",
            "uri": "https://example.test/img_001.png",
            "source": "remote_image",
        }
    }

    page = document["pages"][0]
    assert page["page"] == 1

    title_block = page["blocks"][0]
    assert title_block["reading_order"] == 0
    assert title_block["geometry"]["bbox"] == title_block["bbox"]
    assert title_block["content"] == {"kind": "text", "text": "Document Title"}
    assert title_block["layout_role"] == "title"
    assert title_block["semantic_role"] == "unknown"
    assert title_block["structure_role"] == "title"
    assert title_block["policy"] == {"translate": False, "translate_reason": "provider_non_body:title"}
    assert title_block["provenance"]["provider"] == PROVIDER_GENERIC_FLAT_OCR

    abstract_block = page["blocks"][1]
    assert abstract_block["layout_role"] == "paragraph"
    assert abstract_block["semantic_role"] == "abstract"
    assert abstract_block["structure_role"] == "body"
    assert abstract_block["policy"] == {"translate": True, "translate_reason": "provider_body_whitelist:abstract"}

    image_block = page["blocks"][2]
    assert image_block["content"] == {"kind": "image", "asset_id": "img_001", "text": ""}
    assert image_block["layout_role"] == "unknown"
    assert image_block["semantic_role"] == "unknown"
    assert image_block["structure_role"] == ""
    assert image_block["policy"] == {"translate": False, "translate_reason": "provider_non_text:image"}
