import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Phrase:
    id: str
    german: str
    english: str
    context: str
    created_at: str
    review_count: int = 0
    last_reviewed: str | None = None
    ease_factor: float = 2.5
    interval_days: int = 0
    next_review: str | None = None


class PhrasesDB:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.phrases: dict[str, Phrase] = {}
        self._load()

    def _load(self) -> None:
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.phrases = {phrase_id: Phrase(**phrase_data) for phrase_id, phrase_data in data.items()}

    def _save(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            data = {phrase_id: asdict(phrase) for phrase_id, phrase in self.phrases.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_phrase(self, german: str, english: str, context: str) -> str:
        phrase_id = f"{len(self.phrases) + 1}"
        now = datetime.now().isoformat()
        phrase = Phrase(
            id=phrase_id,
            german=german,
            english=english,
            context=context,
            created_at=now,
            next_review=now,
        )
        self.phrases[phrase_id] = phrase
        self._save()
        return phrase_id

    def update_review(self, phrase_id: str, quality: int) -> None:
        if phrase_id not in self.phrases:
            return

        phrase = self.phrases[phrase_id]
        phrase.review_count += 1
        phrase.last_reviewed = datetime.now().isoformat()

        if quality >= 3:
            phrase.ease_factor = max(1.3, phrase.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            if phrase.interval_days == 0:
                phrase.interval_days = 1
            elif phrase.interval_days == 1:
                phrase.interval_days = 6
            else:
                phrase.interval_days = int(phrase.interval_days * phrase.ease_factor)
        else:
            phrase.interval_days = 1
            phrase.ease_factor = max(1.3, phrase.ease_factor - 0.2)

        next_review_date = datetime.now()
        from datetime import timedelta

        next_review_date += timedelta(days=phrase.interval_days)
        phrase.next_review = next_review_date.isoformat()

        self._save()

    def get_all_phrases(self) -> list[dict[str, Any]]:
        return [asdict(phrase) for phrase in self.phrases.values()]

    def get_due_phrases(self) -> list[dict[str, Any]]:
        now = datetime.now().isoformat()
        return [asdict(phrase) for phrase in self.phrases.values() if phrase.next_review and phrase.next_review <= now]
