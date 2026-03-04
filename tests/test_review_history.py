"""Test that review flow context injected into agent history enables follow-up questions."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput, MessageOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def _inject_review_history(agent: GermanLearningAgent, phrases: list[tuple[str, str, str]]) -> None:
    """Simulate a review session by injecting history for given (id, german, quality_name) tuples."""
    for phrase_id, german, quality_name in phrases:
        agent.add_history("assistant", f"Showing review card: {german} (id: {phrase_id})")
        agent.add_history("user", f"Rated '{german}' as {quality_name}")


def test_agent_knows_last_reviewed_card(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Agent should be able to tell which card was just reviewed."""
    pid, _, _ = test_db.add_phrase("der Hund", "the dog")
    _inject_review_history(agent, [(pid, "der Hund", "Good")])

    outputs = list(agent.process_message("What was the last card I reviewed?"))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    response = " ".join(o.message for o in message_outputs).lower()
    assert "hund" in response, f"Agent should mention 'Hund' in response: {response}"


def test_agent_can_delete_reviewed_card(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Agent should remove a phrase the user refers to from review context."""
    pid, _, _ = test_db.add_phrase("die Katze", "the cat")
    _inject_review_history(agent, [(pid, "die Katze", "Easy")])

    outputs = list(agent.process_message("Delete the card I just reviewed"))

    assert len(test_db.get_all_phrases()) == 0, "Phrase should be removed from database"

    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: remove_phrases" in log.message]
    assert len(tool_calls) > 0, "Expected remove_phrases tool to be called"


def test_agent_identifies_card_by_rating(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Agent should identify which card got a specific rating from review history."""
    pid1, _, _ = test_db.add_phrase("der Tisch", "the table")
    pid2, _, _ = test_db.add_phrase("der Stuhl", "the chair")

    _inject_review_history(
        agent,
        [
            (pid1, "der Tisch", "Easy"),
            (pid2, "der Stuhl", "Again"),
        ],
    )

    outputs = list(agent.process_message("Which card did I rate as Again?"))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    response = " ".join(o.message for o in message_outputs).lower()
    assert "stuhl" in response, f"Agent should mention 'Stuhl' (rated Again): {response}"
