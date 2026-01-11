"""Test that agent responds appropriately after review session completion."""

import pytest

from deubot.agent import GermanLearningAgent, MessageOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def test_agent_responds_to_review_completion(agent: GermanLearningAgent):
    """Test that agent responds with acknowledgment and offers more review."""
    outputs = list(agent.process_message("I just finished reviewing all the cards."))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0, "Agent should respond to review completion"

    response = " ".join([o.message for o in message_outputs]).lower()
    # Response should acknowledge completion or offer more review
    assert any(
        word in response for word in ["done", "great", "good", "well", "another", "more", "review", "session"]
    ), f"Response should acknowledge completion or offer review: {response}"


def test_agent_mentions_review_option_with_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that agent mentions review option when phrases exist."""
    test_db.add_phrase("der Hund", "the dog")
    test_db.add_phrase("die Katze", "the cat")

    outputs = list(agent.process_message("I just finished reviewing all the cards."))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    response = " ".join([o.message for o in message_outputs]).lower()

    # Should mention ability to continue/review more
    assert any(
        phrase in response for phrase in ["review", "another", "more", "continue", "session"]
    ), f"Response should mention review option: {response}"


def test_agent_handles_empty_vocabulary_after_review(agent: GermanLearningAgent):
    """Test that agent responds gracefully when no cards are due."""
    outputs = list(agent.process_message("I just finished reviewing all the cards."))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0, "Agent should respond even with no vocabulary"
