import gzip
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Phrase:
    id: str
    german: str
    ease_factor: float = 2.5
    interval_days: int = 0
    next_review: str | None = None


class PhrasesDB:
    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path) if db_path else None
        self.phrases: dict[str, Phrase] = {}
        self._load()

    def _load(self) -> None:
        if self.db_path and self.db_path.exists():
            with gzip.open(self.db_path, "rt", encoding="utf-8") as f:
                for line in f:
                    phrase_data = json.loads(line.strip())
                    # Convert _id to id for dataclass
                    if "_id" in phrase_data:
                        phrase_data["id"] = phrase_data.pop("_id")
                    phrase = Phrase(**phrase_data)
                    self.phrases[phrase.id] = phrase

    def _save(self) -> None:
        if not self.db_path:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.db_path, "wt", encoding="utf-8") as f:
            for phrase in self.phrases.values():
                phrase_dict = asdict(phrase)
                # Convert id to _id for JSON
                phrase_dict["_id"] = phrase_dict.pop("id")
                f.write(json.dumps(phrase_dict, ensure_ascii=False) + "\n")

    def add_phrase(self, german: str) -> str:
        phrase_id = f"{len(self.phrases) + 1}"
        now = datetime.now().isoformat()
        phrase = Phrase(
            id=phrase_id,
            german=german,
            next_review=now,
        )
        self.phrases[phrase_id] = phrase
        self._save()
        return phrase_id

    def update_review(self, phrase_id: str, quality: int) -> None:
        if phrase_id not in self.phrases:
            return

        phrase = self.phrases[phrase_id]

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

    def get_due_phrases(self, limit: int | None = None) -> list[dict[str, Any]]:
        now = datetime.now().isoformat()
        due_phrases = [
            asdict(phrase) for phrase in self.phrases.values() if phrase.next_review and phrase.next_review <= now
        ]

        # If no phrases are due but database has phrases, return earliest phrases
        if not due_phrases and self.phrases:
            sorted_phrases = sorted(self.phrases.values(), key=lambda p: p.next_review if p.next_review else "")
            due_phrases = [asdict(phrase) for phrase in sorted_phrases]

        if limit is not None:
            return due_phrases[:limit]
        return due_phrases
