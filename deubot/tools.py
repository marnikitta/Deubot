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
            "description": """Save German phrases to the learning database for spaced repetition review.

Call this tool immediately when the user provides or asks about concrete German phrase(s). Do not announce intent before calling.

ARTICLE HANDLING - CRITICAL:
German nouns MUST include articles (der/die/das). Capitalized words are almost always nouns.
- "Hund" → save as "der Hund" (add article)
- "der Tisch" → save as-is (already has article)
- "Guten Morgen" → save as-is (greeting, no article needed)

When unsure if it's a noun, add the article - better to have it than not.
Only skip articles for: greetings, verbs, adjectives, adverbs, phrases.

BATCH SAVING:
Always pass phrases as an array: ["der Hund"] not "der Hund". No limit on array size.
- Single: save_phrases(["der Regenschirm"])
- Multiple: save_phrases(["der Hund", "die Katze", "das Pferd"])
- Large: save_phrases([100+ phrases]) for vocabulary imports

When NOT to Use:
- Grammar questions without concrete phrases ("What is the dative case?")
- User explicitly asks not to save

WRONG Examples:
- save_phrases(["Datenschutz"]) ← MISSING ARTICLE! Must be "der Datenschutz"
- Announcing "I'll save this phrase..." before calling ← Just call the tool immediately

ONE FORM PER CONCEPT:
Save canonical form only. "der Arzt" not both "der Arzt" and "die Ärztin".

TYPO HANDLING:
Auto-correct obvious typos ("Krankenhuas" → "das Krankenhaus"). Ask if ambiguous.
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
    ]
