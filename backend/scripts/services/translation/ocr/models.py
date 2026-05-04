from dataclasses import dataclass
from dataclasses import field


@dataclass
class TextItem:
    item_id: str
    page_idx: int
    block_idx: int
    block_type: str
    bbox: list[float]
    text: str
    segments: list[dict]
    lines: list[dict]
    metadata: dict = field(default_factory=dict)
    block_kind: str = ""
    layout_role: str = ""
    semantic_role: str = ""
    structure_role: str = ""
    policy_translate: bool | None = None
    asset_id: str = ""
    reading_order: int = 0
    raw_block_type: str = ""
    normalized_sub_type: str = ""
