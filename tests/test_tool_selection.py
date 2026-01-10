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


def test_show_card_calls_get_translation_card(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'show card' after saving calls get_translation_card."""
    # Arrange - save a phrase first
    test_db.add_phrase("der Hund", "the dog")

    # Act - ask for card
    outputs = list(agent.process_message("show card for der Hund"))

    # Assert - get_translation_card was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    card_calls = [log.message for log in log_outputs if "Tool call: get_translation_card" in log.message]
    assert len(card_calls) > 0, "Expected get_translation_card tool to be called"


def test_translation_not_show_card_by_default(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that normal translation does NOT call get_translation_card."""
    # Act - normal translation request
    outputs = list(agent.process_message("How to say dog?"))

    # Assert - get_translation_card was NOT called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    card_calls = [log.message for log in log_outputs if "Tool call: get_translation_card" in log.message]
    assert len(card_calls) == 0, "get_translation_card should NOT be called for normal translations"

    # But save_phrases WAS called
    save_calls = [log.message for log in log_outputs if "Tool call: save_phrases" in log.message]
    assert len(save_calls) > 0, "save_phrases should be called for translations"


def test_update_phrase_calls_update_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'update phrase 1' calls update_phrases tool."""
    # Arrange - add a phrase
    test_db.add_phrase("der Hund", "the dog")

    # Act - ask to update
    outputs = list(agent.process_message("Update phrase 1, change German to 'der große Hund'"))

    # Assert - update_phrases was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    update_calls = [log.message for log in log_outputs if "Tool call: update_phrases" in log.message]
    assert len(update_calls) > 0, "Expected update_phrases tool to be called"

    # Assert - phrase was updated
    assert test_db.phrases["1"].german == "der große Hund"


def test_fix_phrase_calls_update_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that 'fix the English for phrase X' calls update_phrases tool."""
    # Arrange - add a phrase
    test_db.add_phrase("der Hund", "the dog")

    # Act - ask to fix
    outputs = list(agent.process_message("Fix the English for phrase 1 to 'the big dog'"))

    # Assert - update_phrases was called
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    update_calls = [log.message for log in log_outputs if "Tool call: update_phrases" in log.message]
    assert len(update_calls) > 0, "Expected update_phrases tool to be called"

    # Assert - phrase was updated
    assert test_db.phrases["1"].english == "the big dog"
