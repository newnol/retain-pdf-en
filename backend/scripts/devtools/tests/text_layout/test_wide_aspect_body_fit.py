import sys
import unittest
from pathlib import Path


REPO_SCRIPTS_ROOT = Path("/home/wxyhgk/tmp/Code/backend/scripts")
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))

from services.rendering.layout.font_fit import estimate_font_size_pt
from services.rendering.layout.font_fit import estimate_leading_em
from services.rendering.layout.font_fit import local_font_size_pt
from services.rendering.layout.payload.block_seed import _relax_wide_aspect_body_leading


def _sample_item(*, wide_aspect: bool) -> dict:
    return {
        "block_type": "text",
        "source_text": (
            "This document offers initial ideas for an industrial policy agenda to keep people first "
            "during the transition to superintelligence."
        ),
        "bbox": [40, 100, 512, 205],
        "lines": [
            {"bbox": [40, 100, 505, 113], "spans": [{"type": "text", "content": "This document offers initial ideas"}]},
            {"bbox": [40, 115, 503, 128], "spans": [{"type": "text", "content": "for an industrial policy agenda"}]},
            {"bbox": [40, 130, 506, 143], "spans": [{"type": "text", "content": "to keep people first during"}]},
            {"bbox": [40, 145, 504, 158], "spans": [{"type": "text", "content": "the transition to"}]},
            {"bbox": [40, 160, 500, 173], "spans": [{"type": "text", "content": "superintelligence."}]},
        ],
        "_is_body_text_candidate": True,
        "_wide_aspect_body_text": wide_aspect,
    }


class WideAspectBodyFitTests(unittest.TestCase):
    def test_local_font_size_uses_glyph_height_not_loose_line_pitch(self):
        item = {
            "block_type": "text",
            "source_text": "Line one with normal glyphs. Line two has very loose leading.",
            "bbox": [40, 100, 420, 160],
            "lines": [
                {"bbox": [40, 100, 410, 112], "spans": [{"type": "text", "content": "Line one with normal glyphs."}]},
                {"bbox": [40, 140, 410, 152], "spans": [{"type": "text", "content": "Line two has very loose leading."}]},
            ],
        }

        self.assertLess(local_font_size_pt(item), 12.0)

    def test_local_font_size_can_grow_for_large_source_glyphs(self):
        item = {
            "block_type": "text",
            "source_text": "Large source text should not be capped at small body defaults.",
            "bbox": [40, 100, 420, 150],
            "lines": [
                {"bbox": [40, 100, 410, 116], "spans": [{"type": "text", "content": "Large source text should not"}]},
                {"bbox": [40, 124, 410, 140], "spans": [{"type": "text", "content": "be capped at small body defaults."}]},
            ],
        }

        self.assertGreater(local_font_size_pt(item), 12.0)

    def test_wide_aspect_body_keeps_font_closer_to_local_ocr(self):
        base_item = _sample_item(wide_aspect=False)
        wide_item = _sample_item(wide_aspect=True)
        page_font_size = 11.6
        page_line_pitch = 14.0
        page_line_height = 12.6
        density_baseline = 28.0

        base_font = estimate_font_size_pt(base_item, page_font_size, page_line_pitch, page_line_height, density_baseline)
        wide_font = estimate_font_size_pt(wide_item, page_font_size, page_line_pitch, page_line_height, density_baseline)

        self.assertGreater(wide_font, base_font)

    def test_wide_aspect_body_preserves_more_ocr_line_pitch_signal(self):
        base_item = _sample_item(wide_aspect=False)
        wide_item = _sample_item(wide_aspect=True)

        base_leading = estimate_leading_em(base_item, 14.0, 10.8)
        wide_leading = estimate_leading_em(wide_item, 14.0, 10.8)

        self.assertLessEqual(wide_leading, base_leading)
        self.assertGreaterEqual(wide_leading, 0.54)

    def test_wide_aspect_body_relaxes_leading_when_vertical_slack_exists(self):
        text = (
            "This document proposes initial ideas for an industrial policy agenda, aiming to ensure a human-centered transition to superintelligence."
            "The content is divided into two parts: first, building an open economy with broad participation, inclusion, and shared prosperity;"
            "second, building a resilient society through accountability, alignment, and frontier risk management."
        )
        relaxed = _relax_wide_aspect_body_leading(
            [82.0, 337.0, 530.0, 436.0],
            text,
            [],
            11.32,
            0.60,
        )
        self.assertGreater(relaxed, 0.60)

    def test_wide_aspect_body_keeps_leading_when_height_is_tight(self):
        text = (
            "However, it is precisely these capabilities that drive progress that will also reshape entire industries at unprecedented speed and scale."
            "Some jobs will disappear, others will evolve, and as organizations learn how to deploy advanced AI,"
            "Entirely new forms of work will also emerge."
        )
        relaxed = _relax_wide_aspect_body_leading(
            [82.0, 454.0, 530.0, 493.0],
            text,
            [],
            11.32,
            0.60,
        )
        self.assertEqual(relaxed, 0.60)


if __name__ == "__main__":
    unittest.main()
