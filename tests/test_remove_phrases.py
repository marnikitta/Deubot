"""Test remove_phrases tool functionality."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def test_remove_single_phrase(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that agent can remove a single phrase by ID when explicitly requested."""
    # Arrange - add a phrase first
    phrase_id, _, _ = test_db.add_phrase("der Hund", "the dog")
    initial_count = len(test_db.get_all_phrases())
    assert initial_count == 1

    # Act - ask to remove it
    outputs = list(agent.process_message(f"Remove phrase {phrase_id}"))

    # Assert - phrase was removed
    final_count = len(test_db.get_all_phrases())
    assert final_count == 0, f"Expected phrase to be removed, but count is {final_count}"

    # Verify remove_phrases tool was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: remove_phrases" in log.message]
    assert len(tool_calls) > 0, "Expected remove_phrases tool to be called"


def test_remove_multiple_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that agent can remove multiple phrases at once when explicitly requested."""
    # Arrange - add multiple phrases
    id1, _, _ = test_db.add_phrase("der Hund", "the dog")
    id2, _, _ = test_db.add_phrase("die Katze", "the cat")
    id3, _, _ = test_db.add_phrase("das Pferd", "the horse")
    initial_count = len(test_db.get_all_phrases())
    assert initial_count == 3

    # Act - ask to remove two of them
    list(agent.process_message(f"Delete phrases {id1} and {id2}"))

    # Assert - two phrases were removed, one remains
    final_phrases = test_db.get_all_phrases()
    final_count = len(final_phrases)
    assert final_count == 1, f"Expected 1 phrase to remain, but count is {final_count}"

    # The remaining phrase should be "das Pferd"
    remaining_german = [p["german"] for p in final_phrases]
    assert "das Pferd" in remaining_german, f"Expected 'das Pferd' to remain, got: {remaining_german}"


def test_remove_phrase_requires_explicit_request(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that agent does NOT remove phrases unless user explicitly asks."""
    # Arrange - add a phrase
    test_db.add_phrase("der Hund", "the dog")
    initial_count = len(test_db.get_all_phrases())
    assert initial_count == 1

    # Act - ask about the phrase without requesting removal
    outputs = list(agent.process_message("What does 'der Hund' mean?"))

    # Assert - phrase was NOT removed
    final_count = len(test_db.get_all_phrases())
    assert final_count >= initial_count, "Phrase should not be removed without explicit request"

    # Verify remove_phrases was NOT called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    remove_calls = [log.message for log in log_outputs if "Tool call: remove_phrases" in log.message]
    assert len(remove_calls) == 0, "remove_phrases should not be called without explicit request"
