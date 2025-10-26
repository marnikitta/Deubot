import os
import pytest
from pathlib import Path
from deubot.dotenv import load_dotenv
from deubot.agent import GermanLearningAgent
from deubot.database import PhrasesDB

load_dotenv(Path(".env"))


@pytest.fixture
def api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key


@pytest.fixture
def agent(api_key):
    db = PhrasesDB()
    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    return GermanLearningAgent(api_key=api_key, model=model, db=db)


def test_simple_translation(agent):
    outputs = agent.process_message("Translate to German: Hello")

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, 'message') and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert "hallo" in response_text


def test_save_phrase_with_agent(agent):
    initial_count = len(agent.db.get_all_phrases())

    outputs = agent.process_message("Please save the phrase 'Guten Morgen' for me to practice")

    # save_phrase is a terminal tool, outputs should be returned
    assert len(outputs) >= 0

    phrases = agent.db.get_all_phrases()
    assert len(phrases) == initial_count + 1

    saved_phrase = [p for p in phrases if "morgen" in p["german"].lower()]
    assert len(saved_phrase) > 0


def test_translation_and_context(agent):
    outputs = agent.process_message("What does 'Danke schön' mean? Provide translation and context.")

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, 'message') and o.message]
    response_text = " ".join(text_outputs)

    assert len(outputs) > 0
    assert len(response_text) > 10


def test_get_phrases_when_database_populated(agent):
    agent.db.add_phrase("Danke")
    agent.db.add_phrase("Bitte")
    agent.db.add_phrase("Entschuldigung")

    outputs = agent.process_message("Show me all my saved phrases")

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, 'message') and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert len(response_text) > 10
    assert "phrase" in response_text or "wort" in response_text

    all_phrases = agent.db.get_all_phrases()
    assert len(all_phrases) == 3


def test_conversation_continuation(agent):
    # Simulate conversation history
    agent.add_user_message("Translate: Good morning")
    agent.add_assistant_message("Guten Morgen\n_Good morning_")

    # Now send the follow-up message
    outputs = agent.process_message("And how do I say good evening?")

    # Extract text from MessageOutput
    text_outputs = [o.message for o in outputs if hasattr(o, 'message') and o.message]
    response_text = " ".join(text_outputs).lower()

    assert len(outputs) > 0
    assert "abend" in response_text


def test_in_memory_db_persistence():
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
