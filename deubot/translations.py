"""Translation card generation for German phrases."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


TRANSLATION_PROMPT = """Generate a comprehensive learning card for the German phrase provided by the user.

Output format (HTML):
<b>[English translation]</b>

<b>Pronunciation:</b>
IPA: [formal IPA transcription]
Approx: [English approximation, e.g., "GOO-ten MOR-gen"]

One-two sentences of clear context and usage.

<b>Usage:</b>
- Bullet points for where/when to use

<b>Examples:</b>
1. [German] – [English]
2. [German] – [English]

<b>Grammar note:</b>
One short, definitive point if relevant.

Rules:
- Use HTML tags: <b>, <i> only
- Keep explanation concise but comprehensive
- Include IPA pronunciation
- Provide 2 example sentences with translations
- Grammar note only if relevant to this phrase
- Do not include the input phrase as a header
"""


@dataclass
class TranslationCard:
    phrase_id: str
    german: str
    explanation: str


class TranslationService:
    def __init__(self, client: OpenAI, model: str, num_workers: int = 10):
        self.client = client
        self.model = model
        self._cache: dict[str, str] = {}
        self.num_workers = num_workers

    def _get_cached_translation(self, german: str) -> str:
        if german in self._cache:
            logger.debug(f"Cache hit for phrase: {german}")
            return self._cache[german]

        logger.debug(f"Cache miss for phrase: {german}, calling LLM")

        response = self.client.responses.create(
            model=self.model,
            instructions=TRANSLATION_PROMPT,
            input=[{"role": "user", "content": german}],
            reasoning={"effort": "minimal"},
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

    def get_translation_card(self, phrase_id: str, german: str) -> TranslationCard:
        explanation = self._get_cached_translation(german)
        return TranslationCard(phrase_id=phrase_id, german=german, explanation=explanation)

    def get_translation_cards_parallel(self, phrases: list[dict[str, Any]]) -> list[TranslationCard]:
        if not phrases:
            return []

        results: dict[str, TranslationCard] = {}

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_phrase = {
                executor.submit(self.get_translation_card, p["id"], p["german"]): p["id"] for p in phrases
            }

            for future in as_completed(future_to_phrase):
                phrase_id = future_to_phrase[future]
                try:
                    card = future.result()
                    results[phrase_id] = card
                    logger.debug(f"Generated translation card for phrase {phrase_id}")
                except Exception as e:
                    logger.error(f"Failed to get translation for phrase {phrase_id}: {e}")
                    german = next(p["german"] for p in phrases if p["id"] == phrase_id)
                    results[phrase_id] = TranslationCard(
                        phrase_id=phrase_id,
                        german=german,
                        explanation=f"<b>{german}</b>\n\n<i>Translation unavailable</i>",
                    )

        return [results[p["id"]] for p in phrases]

    def clear_cache(self) -> None:
        self._cache.clear()
