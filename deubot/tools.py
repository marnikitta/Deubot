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
            "description": """Save German phrases with English translations to the learning database.

ALWAYS call this tool BEFORE responding when translating German phrase(s). Examples:
- "How to say hello?" → save_phrases([{"german": "Hallo", "english": "hello"}])
- "What does Tisch mean?" → save_phrases([{"german": "der Tisch", "english": "the table"}])
- "Guten Morgen" → save_phrases([{"german": "Guten Morgen", "english": "good morning"}])

REQUIRED FIELDS:
Each phrase must have both 'german' and 'english' fields:
- german: The German phrase (with article for nouns)
- english: Short English translation (2-5 words)

ENGLISH TRANSLATION GUIDELINES:
- Nouns: include article ("the dog", "a house")
- Verbs: use infinitive ("to run", "to eat")
- Phrases: natural equivalent ("good morning")

ARTICLE HANDLING:
- "Hund" → save as "der Hund" (add article)
- "der Tisch" → save as-is (already has article)
- "Guten Morgen" → save as-is (greeting, no article needed)
When unsure, add the article.

BATCH SAVING:
- Single: save_phrases([{"german": "der Hund", "english": "the dog"}])
- Multiple: save_phrases([{"german": "der Hund", "english": "the dog"}, {"german": "die Katze", "english": "the cat"}])

When NOT to Use:
- Grammar questions without concrete phrases ("What is the dative case?")
- User explicitly asks not to save

ONE FORM PER CONCEPT:
Save canonical form only:
- Nouns: "der Arzt" not both "der Arzt" and "die Ärztin"
- Verbs: infinitive only. "schwimme" → save "schwimmen" (not "schwimmen, ich schwimme")

VOCABULARY TYPE EXAMPLES:

Nouns (always with article):
- {"german": "der Tisch", "english": "the table"}
- {"german": "die Katze", "english": "the cat"}

Verbs (infinitive only):
- {"german": "fahren", "english": "to drive"}
- User says "ich fahre" → save as "fahren"

Chunks (fixed phrases, use ... for slots):
- {"german": "Ich möchte...", "english": "I would like..."}
- {"german": "Kann ich ... haben?", "english": "Can I have...?"}
- {"german": "Es gibt...", "english": "There is/are..."}

Prepositions (just the word):
- {"german": "mit", "english": "with"}
- {"german": "für", "english": "for"}

Sentence Templates (full example):
- {"german": "Ich fahre morgen mit dem Bus nach Berlin", "english": "I'm going to Berlin by bus tomorrow"}

TYPO HANDLING:
Auto-correct obvious typos ("Krankenhuas" → "das Krankenhaus"). Ask if ambiguous.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phrases": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "german": {"type": "string", "description": "German phrase with article for nouns"},
                                "english": {"type": "string", "description": "Short English translation (2-5 words)"},
                            },
                            "required": ["german", "english"],
                            "additionalProperties": False,
                        },
                        "description": "Array of phrase objects with german and english fields.",
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

Direction parameter:
- "english_to_german" (default): Show English word, produce German word
- "german_to_english": Show German word, recall English meaning
- "mixed": Randomly mix German→English and English→German cards

Phrase selection:
- Default (phrase_ids=null): Fetches up to 40 phrases due for review via SM-2 algorithm
- With phrase_ids: Reviews exactly those phrases, regardless of due date

Examples:
- "review" → start_review(direction="english_to_german") (default, due phrases)
- "quiz me on German" → start_review(direction="english_to_german")
- "practice translating to English" → start_review(direction="german_to_english")
- "mixed review" → start_review(direction="mixed")

Targeted review workflow (for requests like "review my hardest words", "practice nouns"):
1. get_vocabulary(...) to analyze/filter vocabulary (e.g., sort_by="proficiency", ascending=True for hardest)
2. start_review(phrase_ids=[...]) with selected IDs from step 1

Targeted examples:
- "Review my hardest words" → get_vocabulary(sort_by="proficiency", ascending=True, limit=20) → start_review(phrase_ids=[IDs])
- "Practice newest 10 words" → get_vocabulary(sort_by="id", ascending=False, limit=10) → start_review(phrase_ids=[IDs])

Behavior:
1. If phrase_ids provided: fetches those specific phrases
   If phrase_ids omitted: fetches up to 40 phrases due for review
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
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["german_to_english", "english_to_german", "mixed"],
                        "description": "Review direction. 'english_to_german' shows English and tests German production (default). 'german_to_english' shows German and tests English recall. 'mixed' randomly alternates between directions.",
                    },
                    "phrase_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Phrase IDs to review. Null = use SM-2 scheduling (default).",
                    },
                },
                "required": ["direction", "phrase_ids"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_vocabulary",
            "description": """Retrieve user's vocabulary with sorting and filtering for analysis, level estimation, or sentence creation.

When to Use:
- "Estimate my level" → limit=2000, sort_by="proficiency", ascending=False
- "Show my saved phrases" → limit=100, sort_by="id", ascending=True
- "Which phrases are hardest?" → limit=30, sort_by="proficiency", ascending=True
- "What are my newest words?" → limit=20, sort_by="id", ascending=False

When NOT to Use:
- User wants to start a review → use start_review instead

Sorting Options:
- "proficiency": ease_factor × interval_days. ascending=False for best known, True for weakest.
- "alphabetical": A-Z by German text.
- "id": Addition order. ascending=False for newest first.

Limit Guidelines: 2000 for full analysis, 100-200 for browsing, 30-50 for sentences.

Return Format: "ID: 42, German: Guten Morgen, Ease: 2.5"
Ease factor: <2.0 difficult, 2.0-2.8 average, >2.8 well-known.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of phrases to return. Default: 200. Maximum: 2000. Use 2000 for full analysis, 30-50 for sentence creation, 200 for general viewing.",
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
                    "offset": {
                        "type": "integer",
                        "description": "Number of phrases to skip before returning results. Default: 0. Use with limit for paging.",
                    },
                },
                "required": ["limit", "sort_by", "ascending", "offset"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "remove_phrases",
            "description": """Remove phrases from the learning database by ID.

Call when user explicitly asks to remove/delete specific phrases.

When to Use:
- "Remove phrase 42" → remove_phrases(["42"])
- "Delete phrases 10, 15, 20" → remove_phrases(["10", "15", "20"])
- "Remove hardest phrases" → First get_vocabulary(sort_by="proficiency", ascending=True), then remove_phrases([ids])

When NOT to Use:
- User doesn't explicitly ask to remove
- User wants to reset review schedule (this permanently deletes)

Always pass IDs as array of strings: ["42", "123"]. Removal is permanent.
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
        {
            "type": "function",
            "name": "update_phrases",
            "description": """Update German and/or English text for existing vocabulary entries.

Call when user asks to correct, fix, or modify saved phrases.

When to Use:
- "Change phrase 42 to 'der Hund'" → update_phrases([{"id": "42", "german": "der Hund", "english": null}])
- "Fix the English for phrase 15 to 'the dog'" → update_phrases([{"id": "15", "german": null, "english": "the dog"}])
- "Update phrase 10: German 'laufen', English 'to run'" → update_phrases([{"id": "10", "german": "laufen", "english": "to run"}])

Batch Updates:
- update_phrases([{"id": "1", "german": "der Hund", "english": null}, {"id": "2", "german": null, "english": "the cat"}])

When NOT to Use:
- User wants to add new phrases → use save_phrases instead
- User wants to remove phrases → use remove_phrases instead
- User doesn't know the phrase ID → use get_vocabulary first to find it

Preserves review statistics (ease factor, interval, repetition count) - only updates the text.
Pass null for fields you want to keep unchanged; at least one must be non-null.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "ID of the phrase to update"},
                                "german": {
                                    "type": ["string", "null"],
                                    "description": "New German text, or null to keep unchanged",
                                },
                                "english": {
                                    "type": ["string", "null"],
                                    "description": "New English translation, or null to keep unchanged",
                                },
                            },
                            "required": ["id", "german", "english"],
                            "additionalProperties": False,
                        },
                        "description": "Array of update objects. Each must have id and at least one non-null text field.",
                    }
                },
                "required": ["updates"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_translation_card",
            "description": """Generate and display translation cards for saved phrases.

Shows detailed cards with grammar notes, examples, and usage context.

When to Use:
- After save_phrases succeeds (pass returned IDs)
- When user asks for elaboration: "show card", "tell me more about [phrase]"

When NOT to Use:
- During review sessions (cards already shown there)

Behavior: Cards displayed directly. No further response needed.
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phrase_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of phrase IDs to generate cards for",
                    }
                },
                "required": ["phrase_ids"],
                "additionalProperties": False,
            },
        },
    ]
