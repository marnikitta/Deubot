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

Article Handling - CRITICAL FOR GERMAN NOUNS:
German nouns MUST be saved with their articles (der/die/das) - this is non-negotiable for effective learning.
When saving nouns:
- User sends "Gleis" → save as "das Gleis" (detect it's a noun, add the article)
- User sends "Hund" → save as "der Hund" (detect it's a noun, add the article)
- User sends "Katze" → save as "die Katze" (detect it's a noun, add the article)
- User sends "Datenschutz" → save as "der Datenschutz" (detect it's a noun, add the article)
- User sends "Krankenhaus" → save as "das Krankenhaus" (detect it's a noun, add the article)
- User sends "der Tisch" → save as "der Tisch" (article already present)
- Non-nouns like "Hallo", "Guten Morgen", "schnell" → save as-is (no article needed)

HOW TO DETECT NOUNS:
- Capitalized words in German are almost always nouns (Hund, Katze, Datenschutz, Gleis)
- Compound words with capital letters are nouns (Krankenhaus, Regenschirm, Datenschutz)
- If unsure whether it's a noun, add the article - it's better to have it than not
- Only skip articles for: greetings (Hallo, Guten Morgen), verbs, adjectives, adverbs, phrases

BATCH SAVING:
Always pass phrases as an array, even for a single phrase. This tool is optimized for batch operations.

Single Phrase Examples:
- User: "How do you say umbrella?" → save_phrases(["der Regenschirm"]) then respond
- User: "What does Krankenhaus mean?" → save_phrases(["das Krankenhaus"]) then explain (add article!)
- User: "Datenschutz" → save_phrases(["der Datenschutz"]) then translate (add article!)
- User: "Guten Abend" → save_phrases(["Guten Abend"]) then translate (greeting, no article)
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

RIGHT - Call tool immediately with article:
User: Datenschutz
Assistant: [calls save_phrases(["der Datenschutz"])]  ← ARTICLE ADDED!
Assistant: <b>Data protection / privacy</b>

Datenschutz is a masculine noun referring to...

RIGHT - Call tool for noun with article:
User: Notruf
Assistant: [calls save_phrases(["der Notruf"])]  ← ARTICLE ADDED!
Assistant: <b>Emergency call</b>

Notruf refers to an emergency phone call...

WRONG - Saving noun without article:
User: Datenschutz
Assistant: [calls save_phrases(["Datenschutz"])]  ← MISSING ARTICLE!
[This is a critical error - nouns must have articles]

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
            "name": "start_review",
            "description": """Start a spaced repetition review session.

Call this tool when the user wants to practice their vocabulary.

Triggers:
- "/review", "review", "let's practice", "practice", "quiz me"
- Any request to test or review saved vocabulary

Behavior:
1. Fetches up to 10 phrases due for review from the database
2. Generates translation cards for each phrase automatically
3. Presents cards one by one to the user
4. User rates each card; bot handles the review flow locally
5. When batch completes, user can start another session

CRITICAL: After calling this tool, STOP and WAIT.
The bot handles all review interactions locally without further agent involvement.

When NOT to Use:
- User asks to see vocabulary list → use get_vocabulary instead
- User wants to save new phrases → use save_phrases instead
- User asks about grammar → respond directly
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
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
- "Estimate my language level" → limit=2000, sort_by="proficiency", ascending=False
- "What's my vocabulary like?" → limit=100, sort_by="proficiency", ascending=False
- "Show me my saved phrases" → limit=100, sort_by="id", ascending=True
- "Create a sentence with my words" → limit=50, sort_by="proficiency", ascending=False
- "What are my newest words?" → limit=20, sort_by="id", ascending=False
- "Which phrases do I know best?" → limit=30, sort_by="proficiency", ascending=False
- "Which phrases are hardest for me?" → limit=30, sort_by="proficiency", ascending=True
- "List phrases alphabetically" → limit=100, sort_by="alphabetical", ascending=True

When NOT to Use:
- User wants to start a review → use get_next_due_phrases instead
- User asks about phrases due NOW → use get_next_due_phrases instead

Sorting Strategies:

**sort_by="proficiency"** (Proficiency Level)
- Calculated as: ease_factor × interval_days
- ascending=False → Best known phrases first (highest proficiency)
- ascending=True → Weakest phrases first (lowest proficiency, hardest for user)
Use for: Level estimation, creating sentences, finding words to focus on, identifying difficult phrases

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
- Sentence creation: 30-50 (most proficient)
- Quick check: 10-20
- Maximum allowed: 2000

Return Format:
Returns list of phrases with ID, German text, and ease_factor:
"- ID: 42, German: Guten Morgen, Ease: 2.5"
"- ID: 123, German: das Buch, Ease: 1.8"
"- ID: 456, German: Krankenhaus, Ease: 3.2"

The ease_factor indicates how well the user knows the phrase:
- Lower ease (< 2.0): Difficult phrases for the user
- Medium ease (2.0-2.8): Average proficiency
- Higher ease (> 2.8): Well-known phrases

Analysis Approach:
Count phrases, assess variety/complexity, identify CEFR level indicators (A1: Hallo, Danke; A2: einkaufen, gestern; B1: obwohl, trotzdem), assess grammar coverage, analyze ease factors to identify struggling areas, provide level estimate with evidence.
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
                        "enum": ["alphabetical", "proficiency", "id"],
                        "description": "Sort order. 'alphabetical': A-Z by German text. 'proficiency': by ease_factor × interval_days (best known phrases when descending, hardest when ascending). 'id': by addition order (oldest/newest). Choose based on user goal.",
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "Sort direction. True: ascending order. False: descending order. For proficiency, False=best phrases first, True=hardest phrases first. For id, False=newest first.",
                    },
                },
                "required": ["limit", "sort_by", "ascending"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "remove_phrases",
            "description": """Remove one or more German phrases from the learning database.

Call this tool when the user explicitly asks to remove, delete, or unlearn specific phrases.

Usage Pattern:
1. User identifies phrases to remove (by name or by asking you to list them first)
2. Call remove_phrases with list of phrase IDs
3. Tool will notify user of removed and not-found phrases
4. Then provide your response per language policy

When to Use:
- User: "Remove phrase 42" → remove_phrases([42])
- User: "Delete phrases 10, 15, and 20" → remove_phrases([10, 15, 20])
- User: "Remove the hardest phrases" → First call get_vocabulary(sort_by="proficiency", ascending=True), then remove_phrases([ids])
- User: "Delete all phrases with 'Hund'" → First find them, then remove_phrases([ids])

When NOT to Use:
- User doesn't explicitly ask to remove phrases
- User is just browsing vocabulary
- User wants to reset review schedule (this tool permanently deletes)

BATCH REMOVAL:
Always pass phrase IDs as an array, even for a single phrase. This tool is optimized for batch operations.

Single Phrase Examples:
- User: "Remove phrase 123" → remove_phrases(["123"])
- User: "Delete the word Krankenhaus" → First find ID, then remove_phrases([id])

Batch Examples (Multiple Phrases):
- User: "Delete phrases 1, 5, and 10" → remove_phrases(["1", "5", "10"])
- User: "Remove all my weakest words" → get_vocabulary first, then remove_phrases([list of IDs])
- User: "Delete the last 5 phrases I added" → get_vocabulary(sort_by="id", ascending=False, limit=5), then remove_phrases([ids])

Important Notes:
- ALWAYS pass an array of strings: ["42", "123"] not [42, 123]
- IDs must be strings, not integers
- Removal is permanent and cannot be undone
- Tool handles non-existent IDs gracefully (reports them separately)
- Removed phrases will not appear in future reviews or vocabulary lists
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phrase_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of phrase IDs (as strings) to remove. Examples: ['42'], ['1', '5', '10'], or even 100+ IDs.",
                    }
                },
                "required": ["phrase_ids"],
                "additionalProperties": False,
            },
        },
    ]
