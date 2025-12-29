"""Translation card generation for German phrases."""

import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class ReviewDirection(str, Enum):
    GERMAN_TO_ENGLISH = "german_to_english"
    ENGLISH_TO_GERMAN = "english_to_german"
    MIXED = "mixed"


TRANSLATION_PROMPT = """Generate a comprehensive learning card for the German phrase provided by the user.

Rules:
- Use HTML tags: <b>, <i> only
- Don't include original phrase as a header. Start with translation
- Keep it dense – this is a flashcard, not a lecture
- For compound words, show the subwords
- Provide 2 example sentences with translations
- Grammar section: plural, gender forms, or other relevant notes (case usage, irregular forms, etc.). Keep it short

Follow this exact format (example for "das Handtuch"):
<b>towel</b>

<b>Pronunciation:</b>
IPA: /ˈhanttuːx/
Approx: HANT-tookh

Compound: die Hand (hand) + das Tuch (cloth). Everyday item, found in every household.

<b>Usage:</b>
- Bathroom, kitchen, beach
- "Handtuch werfen" = to throw in the towel (give up)

<b>Examples:</b>
1. Gibst du mir bitte das Handtuch? – Can you pass me the towel?
2. Die Handtücher sind im Schrank. – The towels are in the closet.

<b>Grammar:</b>
Plural: die Handtücher (umlaut a→ä)
"""


@dataclass
class TranslationCard:
    phrase_id: str
    german: str
    english: str
    explanation: str
    direction: ReviewDirection


class TranslationService:
    def __init__(self, client: OpenAI, model: str, max_workers: int = 50):
        self.client = client
        self.model = model
        self._cache: dict[str, str] = {}
        self.max_workers = max_workers

    def _get_cached_translation(self, german: str) -> str:
        if german in self._cache:
            logger.debug(f"Cache hit for phrase: {german}")
            return self._cache[german]

        logger.debug(f"Cache miss for phrase: {german}, calling LLM")

        response = self.client.responses.create(
            model=self.model,
            instructions=TRANSLATION_PROMPT,
            input=[{"role": "user", "content": german}],
            reasoning={"effort": "none"},
            text={"verbosity": "low"},
        )

        explanation = ""
        for output_item in response.output:
            if output_item.type == "message":
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        explanation += content_item.text

        self._cache[german] = explanation
        return explanation

    def get_translation_card(
        self, phrase_id: str, german: str, english: str, direction: ReviewDirection
    ) -> TranslationCard:
        explanation = self._get_cached_translation(german)
        return TranslationCard(
            phrase_id=phrase_id, german=german, english=english, explanation=explanation, direction=direction
        )

    def get_translation_cards_parallel(
        self, phrases: list[dict[str, Any]], direction: ReviewDirection = ReviewDirection.MIXED
    ) -> list[TranslationCard]:
        if not phrases:
            return []

        # Assign directions for each phrase (for mixed mode, randomly assign)
        phrase_directions: dict[str, ReviewDirection] = {}
        for p in phrases:
            if direction == ReviewDirection.MIXED:
                phrase_directions[p["id"]] = random.choice(
                    [ReviewDirection.GERMAN_TO_ENGLISH, ReviewDirection.ENGLISH_TO_GERMAN]
                )
            else:
                phrase_directions[p["id"]] = direction

        results: dict[str, TranslationCard] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_phrase = {
                executor.submit(
                    self.get_translation_card, p["id"], p["german"], p["english"], phrase_directions[p["id"]]
                ): p["id"]
                for p in phrases
            }

            for future in as_completed(future_to_phrase):
                phrase_id = future_to_phrase[future]
                try:
                    card = future.result()
                    results[phrase_id] = card
                    logger.debug(f"Generated translation card for phrase {phrase_id}")
                except Exception as e:
                    logger.error(f"Failed to get translation for phrase {phrase_id}: {e}")
                    phrase_data = next(p for p in phrases if p["id"] == phrase_id)
                    german = phrase_data["german"]
                    english = phrase_data["english"]
                    results[phrase_id] = TranslationCard(
                        phrase_id=phrase_id,
                        german=german,
                        english=english,
                        explanation=f"<b>{german}</b>\n\n<i>Translation unavailable</i>",
                        direction=phrase_directions[phrase_id],
                    )

        return [results[p["id"]] for p in phrases]

    def clear_cache(self) -> None:
        self._cache.clear()
