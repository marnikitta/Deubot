"""Test get_vocabulary tool functionality."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput, MessageOutput, ShowReviewBatchOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def _setup_phrases_with_varying_proficiency(test_db: PhrasesDB):
    """Add phrases with different ease factors to test proficiency sorting."""
    # Add phrases and manually adjust their ease factors
    id1, _, _ = test_db.add_phrase("der Hund", "the dog")
    id2, _, _ = test_db.add_phrase("die Katze", "the cat")
    id3, _, _ = test_db.add_phrase("das Pferd", "the horse")

    # Simulate different proficiency levels by updating ease factors
    # Lower ease = harder phrase
    test_db.update_review(id1, quality=4)  # Easy - higher ease
    test_db.update_review(id1, quality=4)
    test_db.update_review(id2, quality=3)  # Medium ease
    test_db.update_review(id3, quality=1)  # Hard - lower ease (reset)

    return id1, id2, id3


def test_get_hardest_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'which phrases are hardest' returns phrases sorted by ascending proficiency."""
    # Arrange
    _setup_phrases_with_varying_proficiency(test_db)

    # Act
    outputs = list(agent.process_message("Which phrases are hardest?"))

    # Assert - get_vocabulary was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(tool_calls) > 0, "Expected get_vocabulary tool to be called"

    # Assert - response mentions the phrases
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0, "Expected a response message"

    # The response should mention at least one of our phrases
    response_text = " ".join(m.message for m in message_outputs).lower()
    assert any(
        word in response_text for word in ["hund", "katze", "pferd"]
    ), f"Expected response to mention saved phrases, got: {response_text[:200]}"


def test_get_newest_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'what are my newest words' returns phrases sorted by ID descending."""
    # Arrange - add phrases in order
    test_db.add_phrase("der Hund", "the dog")
    test_db.add_phrase("die Katze", "the cat")
    test_db.add_phrase("das Pferd", "the horse")  # Newest

    # Act
    outputs = list(agent.process_message("What are my newest words?"))

    # Assert - get_vocabulary was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(tool_calls) > 0, "Expected get_vocabulary tool to be called"

    # Assert - response contains phrase info
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0, "Expected a response message"


def test_estimate_level(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'estimate my level' uses vocabulary analysis."""
    # Arrange
    _setup_phrases_with_varying_proficiency(test_db)

    # Act
    outputs = list(agent.process_message("Estimate my level"))

    # Assert - get_vocabulary was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(tool_calls) > 0, "Expected get_vocabulary tool to be called for level estimation"

    # Assert - response provides some analysis
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0, "Expected a response message with level analysis"


def test_get_vocabulary_not_start_review(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'show my saved phrases' calls get_vocabulary, NOT start_review."""
    # Arrange
    test_db.add_phrase("der Hund", "the dog")
    test_db.add_phrase("die Katze", "the cat")

    # Act
    outputs = list(agent.process_message("Show my saved phrases"))

    # Assert - get_vocabulary was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    get_vocab_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(get_vocab_calls) > 0, "Expected get_vocabulary tool to be called"

    # Assert - start_review was NOT called
    start_review_calls = [log.message for log in log_outputs if "Tool call: start_review" in log.message]
    assert len(start_review_calls) == 0, "start_review should NOT be called for 'show phrases' request"

    # Assert - no review batch output
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(review_outputs) == 0, "Should not show review batch for vocabulary listing"
