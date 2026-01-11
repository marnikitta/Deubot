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


TRANSLATION_PROMPT = """Generate a learning card for the German phrase. First detect the vocabulary type, then use the matching template.

TYPE DETECTION:
- NOUN: Starts with der/die/das, OR single capitalized German word
- VERB: Infinitive ending -en/-ern/-eln (lowercase)
- CHUNK: Contains ... placeholder OR multi-word phrase like "Ich möchte", "Es gibt"
- PREPOSITION: Single short word: mit, für, bei, nach, von, zu, an, auf, in, aus, etc.
- SENTENCE: Complete sentence with subject + conjugated verb

RULES:
- Use HTML tags: <b>, <i> only
- Start with translation, not original phrase
- Keep it dense – flashcard, not lecture
- For compound nouns, show subword breakdown (e.g., Krankenhaus = krank + Haus)
- 2 example sentences with translations
- A1 level: simple vocabulary, common situations

---
NOUN (der/die/das + word):

<b>[English]</b>

<b>Pronunciation:</b> /IPA/ (approx)

<b>Plural:</b> die [plural form]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]

Example for "der Tisch":
<b>table</b>

<b>Pronunciation:</b> /tɪʃ/ (TISH)

<b>Plural:</b> die Tische

<b>Examples:</b>
1. Der Tisch ist groß. - The table is big.
2. Ich sitze am Tisch. - I sit at the table.

---
VERB - show conjugation for irregular/stem-changing, examples for regular:

<b>[English translation]</b>

<b>Pronunciation:</b> /IPA/ (approx)

[For irregular: ich [form], du [form], er [form] + note about stem change]
[For regular: Regular conjugation + skip explicit forms]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]

Example for "fahren" (irregular):
<b>to drive, to go (by vehicle)</b>

<b>Pronunciation:</b> /ˈfaːʁən/ (FAH-ren)

ich fahre, du f<b>ä</b>hrst, er f<b>ä</b>hrt
(stem change: a → ä)

<b>Examples:</b>
1. Ich fahre mit dem Bus. - I go by bus.
2. Er fährt nach Berlin. - He drives to Berlin.

Example for "spielen" (regular):
<b>to play</b>

<b>Pronunciation:</b> /ˈʃpiːlən/ (SHPEE-len)

Regular: -e, -st, -t, -en, -t, -en

<b>Examples:</b>
1. Die Kinder spielen im Garten. - The children play in the garden.
2. Spielst du Fußball? - Do you play soccer?

---
CHUNK (fixed phrase with ... or grammar baked in):

<b>[English equivalent]</b>

<b>Word-by-word:</b>
- [word1] - [translation] ([grammar note if relevant])
- [word2] - [translation]

<b>Usage:</b> [when/how to use, 1-2 sentences]

<b>Variations:</b>
- [variation 1] - [meaning]
- [variation 2] - [meaning]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]

Example for "Tut mir leid":
<b>I'm sorry</b>

<b>Word-by-word:</b>
- Tut - does (from "tun")
- mir - to me (dative of "ich")
- leid - sorrow/sorry

<b>Usage:</b> Apology or expressing regret. Common in everyday speech.

<b>Variations:</b>
- Es tut mir leid - I'm sorry (full form)
- Tut mir sehr leid - I'm very sorry

<b>Examples:</b>
1. Tut mir leid, ich bin spät. - I'm sorry, I'm late.
2. Das tut mir leid. - I'm sorry about that.

---
PREPOSITION:

<b>[English]</b>

<b>Case:</b> + [Dativ/Akkusativ]

<b>Uses:</b>
- [common use 1]: [example phrase]
- [common use 2]: [example phrase]

<b>Examples:</b>
1. [German with article showing case] - [English]
2. [German with article showing case] - [English]

Example for "mit":
<b>with</b>

<b>Case:</b> + Dativ

<b>Uses:</b>
- accompaniment: mit meinem Freund (with my friend)
- transport: mit dem Bus (by bus)

<b>Examples:</b>
1. Ich gehe mit <b>dem</b> Hund. - I go with the dog. (der→dem)
2. Ich fahre mit <b>der</b> Bahn. - I go by train. (die→der)

---
SENTENCE TEMPLATE:

<b>[English translation]</b>

<b>Pattern:</b> [word order rule name]
[1-line explanation of the pattern]

<b>Structure:</b>
[Break down: Subject + Verb + TIME + MANNER + PLACE or similar]

<b>Variations:</b>
1. [German variation] - [English]
2. [German variation] - [English]

Example for "Ich fahre morgen mit dem Bus nach Berlin":
<b>I'm going to Berlin by bus tomorrow</b>

<b>Pattern:</b> Time-Manner-Place
German puts WHEN before HOW before WHERE (unlike English).

<b>Structure:</b>
Ich fahre + morgen (when) + mit dem Bus (how) + nach Berlin (where)

<b>Variations:</b>
1. Morgen fahre ich nach Berlin. - Tomorrow I go to Berlin. (verb stays 2nd)
2. Ich fahre heute mit dem Zug nach München. - I go to Munich by train today.
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
