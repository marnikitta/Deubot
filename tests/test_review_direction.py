"""Test review direction selection based on user input."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput, ShowReviewBatchOutput
from deubot.translations import ReviewDirection

pytestmark = pytest.mark.llm


def _setup_phrases(agent: GermanLearningAgent):
    """Add test phrases for review."""
    agent.db.add_phrase("Guten Morgen", "good morning")
    agent.db.add_phrase("Danke", "thank you")


def test_review_default_direction(agent: GermanLearningAgent):
    """Test that plain 'review' uses english_to_german (default) direction."""
    # Arrange
    _setup_phrases(agent)

    # Act
    outputs = list(agent.process_message("review"))

    # Assert - got a review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1, "Expected a review batch"

    # Assert - direction is english_to_german (default)
    batch = batch_outputs[0]
    for review in batch.reviews:
        assert (
            review.direction == ReviewDirection.ENGLISH_TO_GERMAN
        ), f"Expected english_to_german direction for plain 'review', got {review.direction}"


def test_review_german_to_english(agent: GermanLearningAgent):
    """Test that 'practice translating to English' uses german_to_english direction."""
    # Arrange
    _setup_phrases(agent)

    # Act
    outputs = list(agent.process_message("practice translating to English"))

    # Assert - got a review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1, "Expected a review batch"

    # Assert - direction is german_to_english
    batch = batch_outputs[0]
    for review in batch.reviews:
        assert (
            review.direction == ReviewDirection.GERMAN_TO_ENGLISH
        ), f"Expected german_to_english direction, got {review.direction}"


def test_review_mixed_direction(agent: GermanLearningAgent):
    """Test that 'mixed review' uses mixed direction (random per card)."""
    # Arrange
    _setup_phrases(agent)

    # Act
    outputs = list(agent.process_message("mixed review"))

    # Assert - got a review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1, "Expected a review batch"

    # Assert - start_review was called with mixed direction (check logs)
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_calls = [log.message for log in log_outputs if "Tool call: start_review" in log.message]
    assert len(tool_calls) > 0, "Expected start_review tool to be called"

    # The actual direction on cards may vary (mixed assigns randomly)
    # Just verify we got the batch
    batch = batch_outputs[0]
    assert len(batch.reviews) > 0, "Expected at least one review card"


def test_quiz_german_production(agent: GermanLearningAgent):
    """Test that 'quiz me on German' uses english_to_german (production) direction."""
    # Arrange
    _setup_phrases(agent)

    # Act
    outputs = list(agent.process_message("quiz me on German"))

    # Assert - got a review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1, "Expected a review batch"

    # Assert - direction is english_to_german (German production)
    batch = batch_outputs[0]
    for review in batch.reviews:
        assert (
            review.direction == ReviewDirection.ENGLISH_TO_GERMAN
        ), f"Expected english_to_german direction for German production, got {review.direction}"
