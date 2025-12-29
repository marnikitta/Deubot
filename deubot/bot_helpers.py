from dataclasses import dataclass


def format_level(repetition: int) -> str:
    """Map repetition count to human-readable level string."""
    if repetition == 0:
        return "New"
    elif repetition < 3:
        return "Learning"
    elif repetition < 6:
        return "Familiar"
    return "Mastered"


QUALITY_NAMES = {
    1: "Nochmal / Again",
    2: "Schwer / Hard",
    3: "Gut / Good",
    4: "Leicht / Easy",
}


def get_quality_name(quality: int) -> str:
    """Map quality rating (1-4) to display string."""
    return QUALITY_NAMES.get(quality, "")


@dataclass
class CallbackData:
    action: str
    phrase_id: str
    quality: int | None = None


def parse_callback_data(data: str) -> CallbackData | None:
    """Parse callback data from Telegram button clicks.

    Formats:
        - "reveal_{phrase_id}" -> CallbackData("reveal", phrase_id, None)
        - "quality_{phrase_id}_{quality}" -> CallbackData("quality", phrase_id, quality)
        - Invalid format -> None
    """
    if data.startswith("reveal_"):
        parts = data.split("_", 1)
        if len(parts) == 2:
            return CallbackData(action="reveal", phrase_id=parts[1])
    elif data.startswith("quality_"):
        parts = data.split("_")
        if len(parts) == 3:
            try:
                quality = int(parts[2])
                return CallbackData(action="quality", phrase_id=parts[1], quality=quality)
            except ValueError:
                return None
    return None
