import gzip
import json
import logging
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)


@dataclass
class Phrase:
    id: str
    german: str
    ease_factor: float = 2.5
    interval_days: int = 0
    repetition: int = 0
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
            logger.info(f"Loaded {len(self.phrases)} phrases from database")

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

    def _normalize_phrase(self, phrase: str) -> str:
        normalized = unicodedata.normalize("NFC", phrase)
        normalized = normalized.lower().strip()
        normalized = " ".join(normalized.split())

        # Remove common German articles for comparison
        for article in ["der ", "die ", "das ", "ein ", "eine ", "einen ", "einem ", "einer ", "eines "]:
            if normalized.startswith(article):
                normalized = normalized[len(article) :]
                break

        return normalized

    def _calculate_similarity(self, phrase1: str, phrase2: str) -> float:
        def get_trigrams(text: str) -> set[str]:
            text = f"  {text} "
            return {text[i : i + 3] for i in range(len(text) - 2)}

        trigrams1 = get_trigrams(phrase1)
        trigrams2 = get_trigrams(phrase2)

        if not trigrams1 or not trigrams2:
            return 1.0 if phrase1 == phrase2 else 0.0

        intersection = len(trigrams1 & trigrams2)
        union = len(trigrams1 | trigrams2)
        return intersection / union if union > 0 else 0.0

    def find_similar_phrase(self, german: str, threshold: float = 0.85) -> Phrase | None:
        normalized_input = self._normalize_phrase(german)

        for phrase in self.phrases.values():
            normalized_existing = self._normalize_phrase(phrase.german)
            similarity = self._calculate_similarity(normalized_input, normalized_existing)

            if similarity >= threshold:
                return phrase

        return None

    def add_phrase(self, german: str) -> tuple[str, bool, str | None]:
        existing_phrase = self.find_similar_phrase(german)

        if existing_phrase:
            return (existing_phrase.id, False, existing_phrase.german)

        phrase_id = f"{len(self.phrases) + 1}"
        now = datetime.now().isoformat()
        phrase = Phrase(
            id=phrase_id,
            german=german,
            next_review=now,
        )
        self.phrases[phrase_id] = phrase
        self._save()
        return (phrase_id, True, None)

    def update_review(self, phrase_id: str, quality: int) -> None:
        if phrase_id not in self.phrases:
            return

        phrase = self.phrases[phrase_id]

        if quality >= 3:
            phrase.ease_factor = max(1.3, phrase.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            phrase.repetition += 1

            if phrase.repetition == 1:
                phrase.interval_days = 1
            elif phrase.repetition == 2:
                phrase.interval_days = 6
            else:
                phrase.interval_days = int(phrase.interval_days * phrase.ease_factor)
        else:
            phrase.repetition = 0
            phrase.interval_days = 1

        next_review_date = datetime.now()
        from datetime import timedelta

        next_review_date += timedelta(days=phrase.interval_days)
        phrase.next_review = next_review_date.isoformat()

        logger.info(f"Phrase {phrase_id} reviewed as quality {quality}, next review in {phrase.interval_days} days")
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

    def get_vocabulary(
        self, limit: int = 100, sort_by: Literal["alphabetical", "mastery", "id"] = "id", ascending: bool = True
    ) -> list[dict[str, Any]]:
        """Get vocabulary with custom sorting and limit.

        Args:
            limit: Maximum number of phrases to return (default: 100, max: 2000)
            sort_by: Sort order - "alphabetical", "mastery", or "id" (default: "id")
            ascending: Sort in ascending order if True, descending if False (default: True)

        Returns:
            List of phrase dictionaries
        """
        limit = min(limit, 2000)
        phrases_list = list(self.phrases.values())

        # Define sort key based on sort_by parameter
        def alphabetical_key(p: Phrase) -> str:
            return p.german.lower()

        def mastery_key(p: Phrase) -> float:
            return p.ease_factor * p.interval_days

        def id_key(p: Phrase) -> int:
            return int(p.id)

        key_func: Callable[[Phrase], Any]
        if sort_by == "alphabetical":
            key_func = alphabetical_key
        elif sort_by == "mastery":
            key_func = mastery_key
        else:
            key_func = id_key

        sorted_phrases = sorted(phrases_list, key=key_func, reverse=not ascending)
        return [asdict(phrase) for phrase in sorted_phrases[:limit]]
