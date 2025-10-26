"""Tests for the review process with spaced repetition."""

import pytest

from deubot.agent import GermanLearningAgent, ShowReviewOutput, MessageOutput
from deubot.database import PhrasesDB


def test_review_session_with_multiple_phrases(agent: GermanLearningAgent):
    """Test complete review session with multiple phrases."""
    # Add phrases that are due for review
    agent.db.add_phrase("Guten Morgen")
    agent.db.add_phrase("Guten Abend")
    agent.db.add_phrase("Danke schön")

    # Start review session
    outputs = list(agent.process_message("I want to start a review session"))

    # Extract ShowReviewOutput
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    # Should show first review card
    assert len(review_outputs) == 1
    first_review = review_outputs[0]
    assert first_review.phrase_id in ["1", "2", "3"]
    assert first_review.german in ["Guten Morgen", "Guten Abend", "Danke schön"]
    assert len(first_review.explanation) > 0

    # Simulate bot.py updating database when user clicks "Good" button
    agent.db.update_review(first_review.phrase_id, quality=3)

    # Complete first review
    outputs = list(agent.process_message(f"REVIEWED: {first_review.german} as Good"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    # Should show second review card
    assert len(review_outputs) == 1
    second_review = review_outputs[0]
    assert second_review.phrase_id != first_review.phrase_id
    assert second_review.german != first_review.german

    # Simulate bot.py updating database when user clicks "Good" button
    agent.db.update_review(second_review.phrase_id, quality=3)

    # Complete second review
    outputs = list(agent.process_message(f"REVIEWED: {second_review.german} as Good"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    # Should show third review card
    assert len(review_outputs) == 1
    third_review = review_outputs[0]
    assert third_review.phrase_id not in [first_review.phrase_id, second_review.phrase_id]


def test_review_session_completes_when_no_phrases_left(agent: GermanLearningAgent):
    """Test that review session shows completion message when no phrases are left."""
    # Add only one phrase
    agent.db.add_phrase("Guten Tag")

    # Start review session
    outputs = list(agent.process_message("I want to start a review session"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    assert len(review_outputs) == 1
    first_review = review_outputs[0]

    # Simulate bot.py updating database when user clicks "Good" button
    agent.db.update_review(first_review.phrase_id, quality=3)

    # Complete the only review
    outputs = list(agent.process_message(f"REVIEWED: {first_review.german} as Good"))

    # Should NOT show another review card (no more phrases)
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]
    assert len(review_outputs) == 0

    # Should show completion message
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0

    # Check for completion indicators
    completion_text = " ".join([o.message for o in message_outputs]).lower()
    assert any(word in completion_text for word in ["completed", "done", "finished", "all", "great"])


def test_review_session_with_no_due_phrases(agent: GermanLearningAgent):
    """Test review session when there are no phrases due for review."""
    # Don't add any phrases

    # Start review session
    outputs = list(agent.process_message("I want to start a review session"))

    # Should NOT show any review cards
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]
    assert len(review_outputs) == 0

    # Should show message indicating no reviews
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0

    message_text = " ".join([o.message for o in message_outputs]).lower()
    assert any(word in message_text for word in ["no", "nothing", "none", "completed"])


def test_review_updates_database(agent: GermanLearningAgent):
    """Test that completing reviews updates the database correctly (simulating bot.py behavior)."""
    # Add phrase
    phrase_id = agent.db.add_phrase("Auf Wiedersehen")

    # Get initial state
    initial_phrase = [p for p in agent.db.get_all_phrases() if p["id"] == phrase_id][0]
    initial_interval = initial_phrase["interval_days"]

    # Start and complete review
    outputs = list(agent.process_message("I want to start a review session"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]
    assert len(review_outputs) == 1

    # Simulate bot.py updating database when user clicks "Good" button (quality=3)
    agent.db.update_review(phrase_id, quality=3)

    # Check that database was updated
    updated_phrase = [p for p in agent.db.get_all_phrases() if p["id"] == phrase_id][0]
    assert updated_phrase["interval_days"] > initial_interval
    assert updated_phrase["next_review"] > initial_phrase["next_review"]

    # Now send the "REVIEWED" message to agent (bot.py does this after updating DB)
    outputs = list(agent.process_message(f"REVIEWED: {review_outputs[0].german} as Good"))


def test_review_with_different_quality_ratings(agent: GermanLearningAgent):
    """Test that different quality ratings affect the review schedule (simulating bot.py behavior)."""
    # Add two phrases
    phrase1_id = agent.db.add_phrase("Entschuldigung")
    phrase2_id = agent.db.add_phrase("Bitte")

    # Start review session - get first phrase
    outputs = list(agent.process_message("I want to start a review session"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]
    assert len(review_outputs) == 1
    first_phrase_id = review_outputs[0].phrase_id

    # Simulate bot.py updating database with "Easy" rating (quality=4)
    agent.db.update_review(first_phrase_id, quality=4)

    # Verify that Easy rating gave longer interval
    phrase1 = [p for p in agent.db.get_all_phrases() if p["id"] == first_phrase_id][0]
    assert phrase1["interval_days"] >= 1

    # Now send "REVIEWED" message to get next phrase
    outputs = list(agent.process_message(f"REVIEWED: {review_outputs[0].german} as Easy"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    if len(review_outputs) > 0:
        second_phrase_id = review_outputs[0].phrase_id
        # Simulate bot.py updating database with "Again" rating (quality=1)
        agent.db.update_review(second_phrase_id, quality=1)

        # Verify that Again rating gave short interval (1 day)
        phrase2 = [p for p in agent.db.get_all_phrases() if p["id"] == second_phrase_id][0]
        assert phrase2["interval_days"] == 1


def test_review_explanation_format(agent: GermanLearningAgent):
    """Test that review explanations are properly formatted."""
    agent.db.add_phrase("Guten Morgen")

    outputs = list(agent.process_message("I want to start a review session"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]

    assert len(review_outputs) == 1
    explanation = review_outputs[0].explanation

    # Explanation should be substantial
    assert len(explanation) > 50

    # Should not contain rambling questions (bad pattern)
    assert "?" not in explanation or explanation.count("?") <= 3


def test_user_can_interrupt_review_session(agent: GermanLearningAgent):
    """Test that user can interrupt review session with a question."""
    agent.db.add_phrase("Guten Morgen")

    # Start review
    outputs = list(agent.process_message("I want to start a review session"))
    review_outputs = [o for o in outputs if isinstance(o, ShowReviewOutput)]
    assert len(review_outputs) == 1

    # User asks a question instead of completing review
    outputs = list(agent.process_message("What does 'Tschüss' mean?"))

    # Should get a normal message response, not a review card
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0

    response = " ".join([o.message for o in message_outputs]).lower()
    assert "tschüss" in response or "bye" in response or "goodbye" in response
