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
- Keep it dense – flashcard, not lecture
- For compound nouns, show subword breakdown (e.g., Krankenhaus = krank + Haus)
- 4-5 example sentences with translations. Vary grammar: use accusative (Akk), dative (Dat), and Perfekt (past tense) where natural
- A1 level: simple vocabulary, common situations
- Noun plurals: dictionary-style suffix (-e), (-¨e), (-er), (-¨er), (-n), (-en), (-s), (-). Use ¨ when stem vowel gets umlaut (Apfel→Äpfel = -¨)
- Add one or more <b>💡</b> lines: short memory tips tailored to the specific word. For nouns, ALWAYS include a gender tip (suffix rule like "-ung → die", "-er → der", "-chen → das"; or a vivid image linking the noun to its gender). Add more tips if helpful (cognate, sound image, conjugation trick, etc.). Usually 1-2 tips, but more are fine when the word genuinely needs them.
- End every card with a <b>See also:</b> line — one dense line listing 3-5 related words with translations. For nouns: semantically related words. For days/months/ordinals: the full set in order. For verbs: related verbs or antonyms. For prepositions: other prepositions with same case.

---
NOUN:

<b>[der/die/das + Word]</b> (-plural)

<b>[English]</b>

<b>Pronunciation:</b> /IPA/ (approx)

💡 [gender tip]
💡 [more tips if helpful, e.g. meaning tip]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]
3. [German] - [English] (Akk/Dat/Perfekt)
4. [German] - [English]

<b>See also:</b> [3-5 related words with translations]

Example for "der Tisch":
<b>der Tisch</b> (-e)

<b>table</b>

<b>Pronunciation:</b> /tɪʃ/ (TISH)

💡 Most single-syllable nouns are der — der Tisch, der Stuhl, der Hund.
💡 Sounds like English "dish" — a dish sits on a Tisch.

<b>Examples:</b>
1. Der Tisch ist groß. - The table is big.
2. Ich sehe den Tisch. - I see the table. (Akk)
3. Das Buch liegt auf dem Tisch. - The book is on the table. (Dat)
4. Ich habe den Tisch gekauft. - I bought the table. (Perfekt)
5. Stell die Tasse auf den Tisch! - Put the cup on the table! (Akk)

<b>See also:</b> der Stuhl - chair, das Regal - shelf, die Lampe - lamp, der Schrank - cabinet

---
VERB - show conjugation for irregular/stem-changing, examples for regular:

<b>[infinitive]</b>

<b>[English translation]</b>

<b>Pronunciation:</b> /IPA/ (approx)

[For irregular: ich [form], du [form], er/sie/es [form], wir [form], ihr [form], sie/Sie [form] + note about stem change]
[For regular: Regular conjugation + skip explicit forms]

<b>Partizip II:</b> [past participle] ([auxiliary: haben/sein])

💡 [memory tip/tips]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]
3. [German] - [English] (Perfekt/case variation)
4. [German] - [English]

<b>See also:</b> [3-5 related verbs or antonyms with translations]

Example for "fahren" (irregular):
<b>fahren</b>

<b>to drive, to go (by vehicle)</b>

<b>Pronunciation:</b> /ˈfaːʁən/ (FAH-ren)

ich fahre, du f<b>ä</b>hrst, er/sie/es f<b>ä</b>hrt, wir fahren, ihr fahrt, sie/Sie fahren
(stem change: a → ä in du/er/sie/es)

<b>Partizip II:</b> gefahren (sein)

💡 Sounds like "far" — you fahren to go far.

<b>Examples:</b>
1. Ich fahre mit dem Bus. - I go by bus.
2. Er fährt nach Berlin. - He drives to Berlin.
3. Wir sind gestern gefahren. - We drove yesterday. (Perfekt)
4. Fährst du mit dem Zug? - Are you going by train?
5. Sie ist nach Hause gefahren. - She went home. (Perfekt)

<b>See also:</b> laufen - to walk, fliegen - to fly, reisen - to travel, ankommen - to arrive

Example for "spielen" (regular):
<b>spielen</b>

<b>to play</b>

<b>Pronunciation:</b> /ˈʃpiːlən/ (SHPEE-len)

Regular: -e, -st, -t, -en, -t, -en

<b>Partizip II:</b> gespielt (haben)

💡 "Spiel" sounds like "spiel" in English (a speech/play).

<b>Examples:</b>
1. Die Kinder spielen im Garten. - The children play in the garden.
2. Spielst du Fußball? - Do you play soccer?
3. Ich habe gestern Klavier gespielt. - I played piano yesterday. (Perfekt)
4. Er spielt mit dem Hund. - He plays with the dog. (Dat)
5. Wir haben zusammen gespielt. - We played together. (Perfekt)

<b>See also:</b> üben - to practice, gewinnen - to win, verlieren - to lose, trainieren - to train

---
CHUNK (fixed phrase with ... or grammar baked in):

<b>[German phrase]</b>

<b>[English equivalent]</b>

<b>Word-by-word:</b>
- [word1] - [translation] ([grammar note if relevant])
- [word2] - [translation]

<b>Usage:</b> [when/how to use, 1-2 sentences]

💡 [memory tip/tips]

<b>Variations:</b>
- [variation 1] - [meaning]
- [variation 2] - [meaning]

<b>Examples:</b>
1. [German] - [English]
2. [German] - [English]
3. [German] - [English]
4. [German] - [English]

<b>See also:</b> [3-5 related phrases with translations]

Example for "Tut mir leid":
<b>Tut mir leid</b>

<b>I'm sorry</b>

<b>Word-by-word:</b>
- Tut - does (from "tun")
- mir - to me (dative of "ich")
- leid - sorrow/sorry

<b>Usage:</b> Apology or expressing regret. Common in everyday speech.

💡 "Leid" sounds like "laid" — laid low with sorrow.

<b>Variations:</b>
- Es tut mir leid - I'm sorry (full form)
- Tut mir sehr leid - I'm very sorry

<b>Examples:</b>
1. Tut mir leid, ich bin spät. - I'm sorry, I'm late.
2. Das tut mir leid. - I'm sorry about that.
3. Es hat mir leidgetan. - I was sorry about it. (Perfekt)
4. Tut mir leid, das wusste ich nicht. - I'm sorry, I didn't know that.

<b>See also:</b> Entschuldigung - excuse me, Verzeihung - pardon, Macht nichts - no worries, Kein Problem - no problem

---
PREPOSITION:

<b>[preposition]</b>

<b>[English]</b>

<b>Pronunciation:</b> /IPA/ (approx)

<b>Case:</b> + [Dativ/Akkusativ]

💡 [memory tip/tips]

<b>Uses:</b>
- [common use 1]: [example phrase]
- [common use 2]: [example phrase]

<b>Examples:</b>
1. [German with article showing case] - [English]
2. [German with article showing case] - [English]
3. [German with article showing case] - [English]
4. [German with article showing case] - [English]

<b>See also:</b> [3-5 prepositions with same case + translations]

Example for "mit":
<b>mit</b>

<b>with</b>

<b>Pronunciation:</b> /mɪt/ (MIT)

<b>Case:</b> + Dativ

💡 "mit" = "with" — both short, both start with a lip sound (m/w).

<b>Uses:</b>
- accompaniment: mit meinem Freund (with my friend)
- transport: mit dem Bus (by bus)

<b>Examples:</b>
1. Ich gehe mit <b>dem</b> Hund. - I go with the dog. (der→dem)
2. Ich fahre mit <b>der</b> Bahn. - I go by train. (die→der)
3. Ich habe mit <b>dem</b> Chef gesprochen. - I spoke with the boss. (Perfekt)
4. Kommst du mit <b>uns</b>? - Are you coming with us?
5. Er schreibt mit <b>einem</b> Kugelschreiber. - He writes with a pen.

<b>See also:</b> von - from (+Dat), nach - after/to (+Dat), bei - at/near (+Dat), zu - to (+Dat)

---
SENTENCE TEMPLATE:

<b>[German sentence]</b>

<b>[English translation]</b>

<b>Pattern:</b> [word order rule name]
[1-line explanation of the pattern]

💡 [memory tip/tips]

<b>Structure:</b>
[Break down: Subject + Verb + TIME + MANNER + PLACE or similar]

<b>Variations:</b>
- [German variation] - [English]
- [German variation] - [English]
- [German variation] - [English]
- [German variation] - [English]

<b>See also:</b> [3-5 related phrases or patterns with translations]

Example for "Ich fahre morgen mit dem Bus nach Berlin":
<b>Ich fahre morgen mit dem Bus nach Berlin</b>

<b>I'm going to Berlin by bus tomorrow</b>

<b>Pattern:</b> Time-Manner-Place
German puts WHEN before HOW before WHERE (unlike English).

💡 TMP = Time-Manner-Place, like German efficiency: when, how, where.

<b>Structure:</b>
Ich fahre + morgen (when) + mit dem Bus (how) + nach Berlin (where)

<b>Variations:</b>
- Morgen fahre ich nach Berlin. - Tomorrow I go to Berlin. (verb stays 2nd)
- Ich fahre heute mit dem Zug nach München. - I go to Munich by train today.
- Ich bin gestern mit dem Bus gefahren. - I went by bus yesterday. (Perfekt)
- Wir fahren nächste Woche nach Hamburg. - We go to Hamburg next week.

<b>See also:</b> Ich gehe heute ins Kino - I'm going to the cinema today, Er kommt morgen nach Hause - He's coming home tomorrow
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
