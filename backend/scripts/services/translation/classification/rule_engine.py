from services.translation.item_reader import item_is_textual

CLASSIFY_BLOCK_TYPES = {"text", "title", "list"}


def should_include(item: dict) -> bool:
    text = item.get("source_text", "").strip()
    if not text:
        return False
    if not item.get("should_translate", True):
        return False
    label = str(item.get("classification_label", "") or "")
    if label.startswith(("translate_", "skip_", "code")):
        return False
    return item_is_textual(item)


def rule_label(item: dict) -> str:
    return "review"
