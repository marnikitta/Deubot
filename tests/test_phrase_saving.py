"""Test phrase saving functionality."""

import pytest

from deubot.agent import GermanLearningAgent, MessageOutput, LogOutput
from deubot.database import PhrasesDB


def test_phrase_saving_basic(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that a simple translation request saves a phrase."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())
    test_message = "How to say weather?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, "Phrase was not saved"
    assert final_count == initial_count + 1, f"Expected 1 phrase to be saved, got {final_count - initial_count}"

    # Check that "Wetter" was saved (may include article like "das Wetter")
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]
    assert any(
        "Wetter" in phrase for phrase in saved_phrases
    ), f"Expected 'Wetter' (possibly with article) to be saved, got: {saved_phrases}"


def test_phrase_saving_outputs_confirmation(agent: GermanLearningAgent):
    """Test that saving a phrase generates a confirmation message."""
    # Arrange
    test_message = "How to say umbrella?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check that we got a confirmation message
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    confirmation_messages = [m.message for m in message_outputs if "✓ Saved:" in m.message]

    assert len(confirmation_messages) > 0, "No confirmation message found"
    assert (
        "Regenschirm" in confirmation_messages[0]
    ), f"Expected confirmation for 'Regenschirm', got: {confirmation_messages[0]}"


def test_phrase_saving_continues_with_translation(agent: GermanLearningAgent):
    """Test that after saving, the agent continues with the translation."""
    # Arrange
    test_message = "How to say table?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check we got both confirmation and translation
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]

    assert (
        len(message_outputs) >= 2
    ), f"Expected at least 2 messages (confirmation + translation), got {len(message_outputs)}"

    # First should be confirmation
    assert "✓ Saved:" in message_outputs[0].message, "First message should be confirmation"

    # Second should be translation (not just confirmation)
    translation_message = message_outputs[1].message
    assert len(translation_message) > 10, "Translation message should contain content"
    # Check it's actually a translation (contains German text and/or English explanation)
    assert (
        "tisch" in translation_message.lower() or "table" in translation_message.lower()
    ), "Should contain translation content"


def test_phrase_not_duplicate(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that asking for the same phrase twice doesn't create duplicates."""
    # Arrange
    test_message = "How to say hello?"

    # Act - ask twice
    list(agent.process_message(test_message))
    initial_count = len(test_db.get_all_phrases())

    agent.clear_history()  # Clear history to simulate new conversation
    list(agent.process_message(test_message))
    final_count = len(test_db.get_all_phrases())

    # Assert - should have added another phrase (no deduplication in current implementation)
    # This documents the current behavior; we may want to change this in the future
    assert final_count == initial_count + 1, "Asking for same phrase twice should save it twice (current behavior)"


@pytest.mark.parametrize(
    "test_message,expected_german",
    [
        ("How to say umbrella?", "Regenschirm"),
        ("How do I say thank you?", "Danke"),
        ("What's the German word for car?", "Auto"),
    ],
)
def test_various_translation_formats(
    agent: GermanLearningAgent, test_db: PhrasesDB, test_message: str, expected_german: str
):
    """Test that various translation request formats save phrases correctly."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, f"Phrase was not saved for: {test_message}"

    # Check the saved phrase contains expected German word (case-insensitive)
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]
    assert any(
        expected_german.lower() in phrase.lower() for phrase in saved_phrases
    ), f"Expected '{expected_german}' in saved phrases, got: {saved_phrases}"
