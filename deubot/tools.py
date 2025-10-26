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
            "name": "save_phrase",
            "description": """Save a new German phrase to the learning database for spaced repetition review.

Usage Pattern:
- Call this immediately after providing a translation or explaining a German word/phrase
- Save the German text exactly as you explained it to the user
- Do NOT call this for grammar questions, general explanations, or questions about language concepts
- Do NOT call this when user explicitly asks not to save

When to Use:
✓ User asks "How do you say umbrella?" → After translating, save "Regenschirm"
✓ User asks "What does Krankenhaus mean?" → After explaining, save "Krankenhaus"
✓ User provides German text "Guten Abend" → After translating, save "Guten Abend"
✓ User asks "Translate 'the book' to German" → After translating, save "das Buch"

When NOT to Use:
✗ User asks "What is the dative case?" → Grammar concept, don't save
✗ User asks "What's the difference between der/die/das?" → Grammar explanation, don't save
✗ User asks about conjugation rules → General concept, don't save
✗ User says "just explain, don't save" → Respect user preference

Important Notes:
- Save phrases in their natural form (with articles for nouns: "der Tisch", not "Tisch")
- Include context when relevant (e.g., "Guten Morgen" instead of just "Morgen")
- After saving, the user receives a confirmation message "✓ Saved: <phrase>"
""",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "german": {
                        "type": "string",
                        "description": "The German word or phrase to be saved, exactly as you explained it to the user. Include articles for nouns (e.g., 'der Hund', not 'Hund').",
                    }
                },
                "required": ["german"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_next_due_phrases",
            "description": """Retrieve the next batch of German phrases that need spaced repetition review.

Usage Pattern:
- Call this at the START of a review session when user asks to review/practice
- Fetch batches of 30 phrases at a time (default)
- Cache the results in memory - do NOT call again until the entire batch is shown
- Each phrase includes: ID (for tracking), German text (to display)

When to Use:
✓ User says "/review" or "start review" → Call immediately with limit=30
✓ User asks "let's practice" or "time to review" → Call immediately
✓ Current batch is exhausted → Fetch next batch with limit=30
✓ User asks "how many phrases need review?" → Call with appropriate limit to check

When NOT to Use:
✗ In the MIDDLE of showing review cards from current batch → Use cached batch instead
✗ After showing just 1-2 cards from a batch of 30 → Continue with remaining cached cards
✗ User asks to see vocabulary → Use get_vocabulary instead
✗ User asks about specific phrase stats → Use get_vocabulary with appropriate sort

Flow Example:
1. User: "/review"
2. Call get_next_due_phrases(limit=30) → Returns 30 phrases
3. Show card 1 via show_review
4. User rates card 1
5. Show card 2 via show_review ← DO NOT call get_next_due_phrases again!
6. Continue through all 30 cards
7. After card 30, call get_next_due_phrases(limit=30) again

Return Format:
Returns a list of phrases with structure: "- ID: {id}, German: {german}"
Example: "- ID: 42, German: Guten Morgen"

Performance Notes:
- Default limit of 30 is optimal for a review session
- Maximum limit is 100 (enforced)
- If no phrases are due, returns earliest scheduled phrases
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

CRITICAL: This is a TERMINAL tool - after calling it, you MUST wait for user input. Do not continue conversation.

Card Interaction Flow:
1. Card shows German phrase with a "Reveal" button
2. User clicks "Reveal" to see explanation
3. User rates their recall: Again (1), Hard (2), Good (3), Easy (4)
4. You receive the rating as a message: "REVIEWED: {phrase} as {rating}"
5. THEN you show the next card from your cached batch

Usage Pattern:
- Call this once per review turn
- Only show ONE card at a time
- Prepare a comprehensive explanation before calling
- Wait for user rating before showing next card

When to Use:
✓ User started a review session and you have phrases from get_next_due_phrases
✓ User just rated a card and you have more cards in your cached batch
✓ You've prepared a detailed explanation for the phrase

When NOT to Use:
✗ User hasn't started a review session
✗ You already showed a card this turn (limit: 1 per turn)
✗ User is asking questions or having a conversation
✗ You don't have the phrase_id from get_next_due_phrases

Explanation Format:
Create a comprehensive explanation including:

**Translation**: Clear English translation
**Context**: When/how it's used
**Examples**: 2-3 usage examples with translations
**Grammar**: Relevant grammatical notes
**Similar phrases**: Related expressions (if relevant)

Example Explanation Template:
<b>Good morning</b>

A common morning greeting used until roughly 11 AM.

Examples:
• Guten Morgen, wie geht's? - Good morning, how are you?
• Guten Morgen, Herr Schmidt - Good morning, Mr. Schmidt

Grammar: "Guten" is the accusative form of "gut", used in this fixed expression.

Similar: Guten Tag (Good day), Guten Abend (Good evening)

Parameters:
- phrase_id: The ID from get_next_due_phrases (e.g., "42")
- german: The German phrase exactly as stored (e.g., "Guten Morgen")
- explanation: Rich HTML-formatted explanation with <b>, <i> tags

Terminal Behavior:
After calling show_review, you CANNOT:
- Show another review card in the same turn
- Continue with conversational response
- Call other tools

The review card is displayed, user interacts with it, and sends you their rating as the next message.
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
                        "description": "Comprehensive English explanation in HTML format. Include: <b>translation</b>, context, 2-3 examples with translations, grammar notes, and similar phrases. Use HTML tags: <b> for bold, <i> for italic. Example: '<b>Good morning</b>\\n\\nA common morning greeting used until roughly 11 AM.\\n\\nExamples:\\n• Guten Morgen, wie geht\\'s?...'",
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

When to Use (Call Immediately):
✓ "Estimate my language level" → get_vocabulary(limit=2000, sort_by="mastery", ascending=False)
✓ "What's my vocabulary like?" → get_vocabulary(limit=100, sort_by="mastery", ascending=False)
✓ "Show me my saved phrases" → get_vocabulary(limit=100, sort_by="id", ascending=True)
✓ "Create a sentence with my words" → get_vocabulary(limit=50, sort_by="mastery", ascending=False)
✓ "What are my newest words?" → get_vocabulary(limit=20, sort_by="id", ascending=False)
✓ "Which phrases do I know best?" → get_vocabulary(limit=30, sort_by="mastery", ascending=False)
✓ "List phrases alphabetically" → get_vocabulary(limit=100, sort_by="alphabetical", ascending=True)

When NOT to Use:
✗ User wants to start a review → Use get_next_due_phrases instead
✗ User asks about phrases due NOW → Use get_next_due_phrases instead

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
After retrieving vocabulary:
1. Count total phrases
2. Look at variety and complexity
3. Identify CEFR level indicators (A1: Hallo, Danke; A2: einkaufen, gestern; B1: obwohl, trotzdem; etc.)
4. Assess grammar coverage (cases, tenses, conjunctions)
5. Provide level estimate with specific evidence

Example Analysis Flow:
User: "Estimate my language level"
1. Call get_vocabulary(limit=2000, sort_by="mastery", ascending=False)
2. Analyze the 2000 phrases returned
3. Identify level markers: "I see 234 phrases including A1 basics (Hallo, Danke), A2 vocabulary (einkaufen, gestern), and some B1 phrases (obwohl, trotzdem)"
4. Estimate: "Based on your 234 phrases with solid A2 coverage and emerging B1, you're around A2-B1 level"
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
