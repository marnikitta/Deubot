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
    messages = [{"role": "user", "content": "Translate to German: Hello"}]
    response, should_clear = agent.process_message(messages)

    assert response
    assert len(response) > 0
    assert should_clear is False
    assert "hallo" in response.lower()


def test_save_phrase_with_agent(agent):
    initial_count = len(agent.db.get_all_phrases())

    messages = [{"role": "user", "content": "Please save the phrase 'Guten Morgen' for me to practice"}]
    response, should_clear = agent.process_message(messages)

    # save_phrase is a terminal tool, so response may be empty
    assert should_clear is False

    phrases = agent.db.get_all_phrases()
    assert len(phrases) == initial_count + 1

    saved_phrase = [p for p in phrases if "morgen" in p["german"].lower()]
    assert len(saved_phrase) > 0


def test_translation_and_context(agent):
    messages = [{"role": "user", "content": "What does 'Danke schön' mean? Provide translation and context."}]
    response, should_clear = agent.process_message(messages)

    assert response
    assert len(response) > 10
    assert should_clear is False


def test_get_phrases_when_database_populated(agent):
    agent.db.add_phrase("Danke")
    agent.db.add_phrase("Bitte")
    agent.db.add_phrase("Entschuldigung")

    messages = [{"role": "user", "content": "Show me all my saved phrases"}]
    response, should_clear = agent.process_message(messages)

    assert response
    assert len(response) > 10
    assert "phrase" in response.lower() or "wort" in response.lower()
    assert should_clear is False

    all_phrases = agent.db.get_all_phrases()
    assert len(all_phrases) == 3


def test_conversation_continuation(agent):
    messages = [
        {"role": "user", "content": "Translate: Good morning"},
        {"role": "assistant", "content": "Guten Morgen\n_Good morning_"},
        {"role": "user", "content": "And how do I say good evening?"}
    ]
    response, should_clear = agent.process_message(messages)

    assert response
    assert "abend" in response.lower()
    assert should_clear is False


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
