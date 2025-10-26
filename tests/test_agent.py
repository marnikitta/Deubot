"""Tests for the GermanLearningAgent."""

import pytest

from deubot.agent import GermanLearningAgent
from deubot.database import PhrasesDB


def test_simple_translation(agent: GermanLearningAgent):
    """Test basic translation functionality."""
    outputs = list(agent.process_message("Translate to German: Hello"))

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, "message") and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert "hallo" in response_text


def test_save_phrases_with_agent(agent: GermanLearningAgent):
    """Test that phrases are saved when requested."""
    initial_count = len(agent.db.get_all_phrases())

    outputs = list(agent.process_message("Please save the phrase 'Guten Morgen' for me to practice"))

    # save_phrases should be called
    assert len(outputs) >= 0

    phrases = agent.db.get_all_phrases()
    assert len(phrases) == initial_count + 1

    saved_phrase = [p for p in phrases if "morgen" in p["german"].lower()]
    assert len(saved_phrase) > 0


def test_translation_and_context(agent: GermanLearningAgent):
    """Test that translations include context and explanation."""
    outputs = list(agent.process_message("What does 'Danke schön' mean? Provide translation and context."))

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, "message") and o.message]
    response_text = " ".join(text_outputs)

    assert len(outputs) > 0
    assert len(response_text) > 10


def test_get_phrases_when_database_populated(agent: GermanLearningAgent):
    """Test that agent can reference saved phrases."""
    agent.db.add_phrase("Danke")
    agent.db.add_phrase("Bitte")
    agent.db.add_phrase("Entschuldigung")

    outputs = list(agent.process_message("Show me all my saved phrases"))

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, "message") and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert len(response_text) > 10

    # Check that at least one of the saved phrases appears in response
    all_phrases = agent.db.get_all_phrases()
    assert len(all_phrases) == 3
    phrase_texts = [p["german"].lower() for p in all_phrases]
    assert any(
        phrase in response_text for phrase in phrase_texts
    ), f"No saved phrases found in response: {response_text}"


def test_conversation_continuation(agent: GermanLearningAgent):
    """Test that agent maintains conversation context."""
    # Simulate conversation history
    agent.messages.append({"role": "user", "content": "Translate: Good morning"})
    agent.messages.append({"role": "assistant", "content": "Guten Morgen\n_Good morning_"})

    # Now send the follow-up message
    outputs = list(agent.process_message("And how do I say good evening?"))

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, "message") and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert "abend" in response_text


def test_in_memory_db_persistence():
    """Test that in-memory database persists phrases correctly."""
    db = PhrasesDB()

    phrase_id_1 = db.add_phrase("Guten Tag")
    phrase_id_2 = db.add_phrase("Auf Wiedersehen")

    all_phrases = db.get_all_phrases()
    assert len(all_phrases) == 2
    assert all_phrases[0]["german"] == "Guten Tag"
    assert all_phrases[1]["german"] == "Auf Wiedersehen"

    db.update_review(phrase_id_1, quality=3)

    updated_phrase = [p for p in db.get_all_phrases() if p["id"] == phrase_id_1][0]
    assert updated_phrase["interval_days"] == 1
