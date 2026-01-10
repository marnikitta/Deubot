"""Tests for targeted review with phrase_ids parameter."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput, ShowReviewBatchOutput, MessageOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def test_default_review_behavior_unchanged(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that default review (no phrase_ids) still works as before."""
    test_db.add_phrase("der Hund", "the dog")
    test_db.add_phrase("die Katze", "the cat")

    outputs = list(agent.process_message("/review"))

    # start_review was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    start_review_calls = [log.message for log in log_outputs if "Tool call: start_review" in log.message]
    assert len(start_review_calls) > 0

    # Got review batch with both phrases
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1
    assert len(batch_outputs[0].reviews) == 2


def test_review_with_specific_phrase_ids(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that explicit phrase IDs limit review to those specific phrases."""
    test_db.add_phrase("der Hund", "the dog")  # ID: 1
    test_db.add_phrase("die Katze", "the cat")  # ID: 2
    test_db.add_phrase("das Pferd", "the horse")  # ID: 3

    outputs = list(agent.process_message("Review only phrases 1 and 3"))

    # Got review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1

    # Only phrases 1 and 3 are in the batch
    reviews = batch_outputs[0].reviews
    review_ids = {r.phrase_id for r in reviews}
    assert review_ids == {"1", "3"}, f"Expected phrases 1 and 3, got {review_ids}"


def test_targeted_review_workflow_hardest_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test workflow: user asks for hardest phrases, agent uses get_vocabulary then start_review."""
    # Add phrases with varying proficiency
    id1, _, _ = test_db.add_phrase("der Hund", "the dog")
    id2, _, _ = test_db.add_phrase("die Katze", "the cat")
    id3, _, _ = test_db.add_phrase("das Pferd", "the horse")

    # Make phrases have different proficiency by simulating reviews
    test_db.update_review(id1, quality=4)  # Easy - high proficiency
    test_db.update_review(id1, quality=4)
    test_db.update_review(id2, quality=4)  # Easy
    test_db.update_review(id2, quality=4)
    test_db.update_review(id3, quality=1)  # Hard - low proficiency (reset)

    outputs = list(agent.process_message("Practice my hardest phrases"))

    # get_vocabulary was called (for analysis)
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    vocab_calls = [log.message for log in log_outputs if "Tool call: get_vocabulary" in log.message]
    assert len(vocab_calls) > 0, "Expected get_vocabulary for analyzing vocabulary"

    # start_review was called
    review_calls = [log.message for log in log_outputs if "Tool call: start_review" in log.message]
    assert len(review_calls) > 0, "Expected start_review with selected phrases"

    # Got review batch
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1


def test_review_nonexistent_ids_graceful_handling(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that requesting nonexistent phrase IDs is handled gracefully."""
    test_db.add_phrase("der Hund", "the dog")  # ID: 1

    outputs = list(agent.process_message("Review phrase 999"))

    # No review batch (phrase doesn't exist)
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 0

    # Got a message response (agent informs about the issue)
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0


def test_review_mixed_existing_and_nonexistent_ids(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test review with mix of valid and invalid IDs proceeds with valid ones."""
    test_db.add_phrase("der Hund", "the dog")  # ID: 1
    test_db.add_phrase("die Katze", "the cat")  # ID: 2

    outputs = list(agent.process_message("Review phrases 1 and 999"))

    # Got review batch with phrase 1 only
    batch_outputs = [o for o in outputs if isinstance(o, ShowReviewBatchOutput)]
    assert len(batch_outputs) == 1

    reviews = batch_outputs[0].reviews
    assert len(reviews) == 1
    assert reviews[0].phrase_id == "1"
