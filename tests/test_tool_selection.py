"""Test that agent selects the correct tool for different requests."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput, ShowReviewBatchOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def test_show_vocabulary_not_start_review(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'show my saved phrases' calls get_vocabulary, NOT start_review."""
    # Arrange - add some phrases
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
    assert len(start_review_calls) == 0, "start_review should NOT be called for vocabulary listing"

    # Assert - no review batch output
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 0, "Should not show review batch when listing vocabulary"


def test_review_not_get_vocabulary(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that '/review' calls start_review, NOT get_vocabulary."""
    # Arrange - add some phrases
    test_db.add_phrase("der Hund", "the dog")
    test_db.add_phrase("die Katze", "the cat")

    # Act
    outputs = list(agent.process_message("/review"))

    # Assert - start_review was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    start_review_calls = [log.message for log in log_outputs if "Tool call: start_review" in log.message]
    assert len(start_review_calls) > 0, "Expected start_review tool to be called for /review"

    # Assert - get_vocabulary was NOT called
    get_vocab_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(get_vocab_calls) == 0, "get_vocabulary should NOT be called for /review command"

    # Assert - got review batch output
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1, "Should show review batch for /review command"
