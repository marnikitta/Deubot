"""
Tool definitions for the German Learning Agent.

This module contains comprehensive tool descriptions with usage patterns, examples,
and guidance for when to use each tool. Following Claude Code's philosophy:
"Help the poor model out, will ya?"
"""

from typing import Any


def get_tools() -> list[dict[str, Any]]:
    """
    Returns the list of tools available to the German Learning Agent.

    Each tool has elaborate documentation including:
    - Clear purpose and usage patterns
    - Concrete examples of when to use
    - Parameter guidance and defaults
    - Edge cases and special considerations
    """
    return [
        {
            "type": "function",
            "name": "save_phrases",
            "description": """Save one or more German phrases to the learning database for spaced repetition review.

Call this tool immediately when the user provides or asks about concrete German phrase(s), then provide your response. Do not announce your intent to save before calling the tool.

Usage Pattern:
1. Detect if concrete German phrase(s) will be produced or interpreted
2. Call save_phrases with list of German texts (even if just one phrase)
3. Add articles (der/die/das) to all nouns - this is critical for German learning
4. Then provide your response per language policy

DO NOT call for grammar questions, general explanations, or language concepts.
DO NOT call when user explicitly asks not to save.

Article Handling:
German nouns need their articles to be useful for learning. When saving:
- User sends "Gleis" → save as "das Gleis" (add the article)
- User sends "Hund" → save as "der Hund" (add the article)
- User sends "Katze" → save as "die Katze" (add the article)
- User sends "der Tisch" → save as "der Tisch" (article already present)
- Non-nouns like "Hallo", "Guten Morgen" → save as-is (no article needed)

BATCH SAVING:
Always pass phrases as an array, even for a single phrase. This tool is optimized for batch operations.

Single Phrase Examples:
- User: "How do you say umbrella?" → save_phrases(["der Regenschirm"]) then respond
- User: "What does Krankenhaus mean?" → save_phrases(["Krankenhaus"]) then explain
- User: "Guten Abend" → save_phrases(["Guten Abend"]) then translate
- User: "Translate 'the book' to German" → save_phrases(["das Buch"]) then respond

Batch Examples (Multiple Phrases):
- User: "Translate: hello, goodbye, thank you" → save_phrases(["Hallo", "Auf Wiedersehen", "Danke"]) then respond
- User: "What are Tisch, Stuhl, Lampe?" → save_phrases(["der Tisch", "der Stuhl", "die Lampe"]) then translate
- User: "Save 5 different common domestic animals" → save_phrases(["der Hund", "die Katze", "das Pferd", "der Hamster", "der Fisch"]) then list them
- User: "Give me 10 fruits in German" → save_phrases([all 10 fruit words with articles]) then provide list
- User provides list of 100 words to learn → save_phrases([all 100 phrases]) then respond

Large Batch Examples:
- Vocabulary list import: save_phrases([hundreds or thousands of phrases]) - no limit on array size
- Topic vocabulary: save_phrases([all relevant phrases for the topic])
- User: "Save common phrases for traveling" → save_phrases([20-30 travel phrases])

When NOT to Use:
- User: "What is the dative case?" → Grammar concept only (no concrete phrases)
- User: "What's the difference between der/die/das?" → Grammar explanation only
- User asks about conjugation rules → General concept only
- User: "just explain, don't save" → Respect user preference

Tool Calling Pattern:

RIGHT - Call tool immediately:
User: Notruf
Assistant: [calls save_phrases(["Notruf"])]
Assistant: <b>Emergency call</b>

Notruf refers to an emergency phone call...

WRONG - Announcing intent first:
User: Notruf
Assistant: Calling save_phrases for the German phrase and then explaining per policy...
[This creates unnecessary back-and-forth - user sees this message before the actual content]

Important Notes:
- ALWAYS pass an array, even for single phrases: ["der Hund"] not "der Hund"
- Save phrases with articles for nouns: "der Tisch" not "Tisch"
- Include context when relevant: "Guten Morgen" not just "Morgen"
- Array can contain any number of phrases: 1, 10, 100, 1000+
- Tool handles duplicates automatically (won't save the same phrase twice)
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phrases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of German phrases to save. Each phrase should include articles for nouns (e.g., 'der Hund', not 'Hund'). Examples: ['der Hund'], ['Hallo', 'Tschüss', 'Danke'], or even 1000+ phrases.",
                    }
                },
                "required": ["phrases"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_next_due_phrases",
            "description": """Retrieve the next batch of German phrases that need spaced repetition review.

CRITICAL BATCHING RULE: Call ONLY when starting a review session OR when current batch is exhausted.
DO NOT call again until all cards from current batch have been shown via show_review.

Usage Pattern:
- Fetch batches of 30 phrases (default) and cache in memory
- Each phrase includes: ID (for tracking), German text (to display)
- Return format: "- ID: {id}, German: {german}"

When to Use:
- User starts review: "/review", "let's practice", "time to review"
- Current batch exhausted: all cached cards shown, need more
- Checking due count: user asks "how many phrases need review?"

When NOT to Use:
- Mid-batch: showing cards 1-29 of a 30-card batch
- User asks to see vocabulary → use get_vocabulary instead
- User asks about phrase stats → use get_vocabulary with sort

Technical Notes:
- Default limit: 30 (optimal for one session)
- Maximum limit: 100 (enforced)
- Returns earliest scheduled phrases if none currently due
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of phrases to return. Default: 30 (optimal for one session). Maximum: 100 (enforced). Use 30 unless user explicitly requests different amount.",
                    }
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "show_review",
            "description": """Display an interactive review card to the user with a German phrase for spaced repetition testing.

CRITICAL: After calling this tool, STOP and WAIT for user's rating. DO NOT send text or call other tools.

Usage:
- Call ONCE per turn with ONE card
- Prepare comprehensive explanation before calling
- User rates card and you receive: "REVIEWED: {phrase} as {rating}"
- In next turn, show next card from cached batch

When to Use:
- During active review session with phrases from get_next_due_phrases
- After user rated previous card and more cards remain in cached batch
- You have prepared detailed explanation for the phrase

When NOT to Use:
- User hasn't started review session
- Already showed card this turn (LIMIT: 1 per turn)
- User asking questions or conversing
- Missing phrase_id from get_next_due_phrases

Explanation Format (use this structure):
<b>[English translation]</b>

<b>Pronunciation:</b>
IPA: [formal IPA transcription]
Approx: [English approximation, e.g., "KROH-ah-sahnt"]

One-two sentences of clear context and usage.

<b>Usage:</b>
- Bullet points for where/when to use

<b>Examples:</b>
1. [German] – [English]
2. [German] – [English]

<b>Grammar note:</b>
One short, definitive point if relevant.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phrase_id": {
                        "type": "string",
                        "description": "The ID of the phrase being reviewed, obtained from get_next_due_phrases. Example: '42'",
                    },
                    "german": {
                        "type": "string",
                        "description": "The German phrase to display on the card, exactly as stored in database. Example: 'Guten Morgen'",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Comprehensive English explanation in HTML format. Include: <b>translation</b>, <b>Pronunciation</b> (IPA and English approximation), context, usage points, 2-3 examples with translations, and grammar notes. Use HTML tags: <b> for bold, <i> for italic. Example: '<b>Good morning</b>\\n\\n<b>Pronunciation:</b>\\nIPA: [ˈɡuːtn̩ ˈmɔʁɡn̩]\\nApprox: GOO-ten MOR-gen\\n\\nA common morning greeting used until roughly 11 AM.\\n\\n<b>Usage:</b>\\n• Used from waking up until around 11 AM...'",
                    },
                },
                "required": ["phrase_id", "german", "explanation"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_vocabulary",
            "description": """Retrieve user's vocabulary with flexible sorting and filtering for analysis, level estimation, or sentence creation.

This is your window into the user's complete learning progress. Use it to understand what they know and tailor your responses accordingly.

Usage Pattern:
- Call this IMMEDIATELY when user wants to analyze their vocabulary
- Choose appropriate sort_by based on user's goal
- Adjust limit based on task (small for sentences, large for analysis)

When to Use:
- "Estimate my language level" → limit=2000, sort_by="mastery", ascending=False
- "What's my vocabulary like?" → limit=100, sort_by="mastery", ascending=False
- "Show me my saved phrases" → limit=100, sort_by="id", ascending=True
- "Create a sentence with my words" → limit=50, sort_by="mastery", ascending=False
- "What are my newest words?" → limit=20, sort_by="id", ascending=False
- "Which phrases do I know best?" → limit=30, sort_by="mastery", ascending=False
- "List phrases alphabetically" → limit=100, sort_by="alphabetical", ascending=True

When NOT to Use:
- User wants to start a review → use get_next_due_phrases instead
- User asks about phrases due NOW → use get_next_due_phrases instead

Sorting Strategies:

**sort_by="mastery"** (Mastery Level)
- Calculated as: ease_factor × interval_days
- ascending=False → Best known phrases first
- ascending=True → Weakest phrases first
Use for: Level estimation, creating sentences, finding words to focus on

**sort_by="alphabetical"** (A-Z by German text)
- ascending=True → A to Z
- ascending=False → Z to A
Use for: Browsing, finding specific words, organized lists

**sort_by="id"** (Addition Order)
- ascending=True → Oldest first
- ascending=False → Newest first
Use for: Seeing learning progression, finding recent additions

Limit Guidelines:
- Level estimation: 2000 (get everything)
- Vocabulary review: 100-200
- Sentence creation: 30-50 (most mastered)
- Quick check: 10-20
- Maximum allowed: 2000

Return Format:
Returns list of phrases with German text only:
"- Guten Morgen"
"- das Buch"
"- Krankenhaus"

Analysis Approach:
Count phrases, assess variety/complexity, identify CEFR level indicators (A1: Hallo, Danke; A2: einkaufen, gestern; B1: obwohl, trotzdem), assess grammar coverage, provide level estimate with evidence.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of phrases to return. Default: 100. Maximum: 2000. Use 2000 for full analysis, 30-50 for sentence creation, 100 for general viewing.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["alphabetical", "mastery", "id"],
                        "description": "Sort order. 'alphabetical': A-Z by German text. 'mastery': by ease_factor × interval_days (best known phrases). 'id': by addition order (oldest/newest). Choose based on user goal.",
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "Sort direction. True: ascending order. False: descending order. For mastery, False=best phrases first. For id, False=newest first.",
                    },
                },
                "required": ["limit", "sort_by", "ascending"],
                "additionalProperties": False,
            },
        },
    ]
