"""Comprehensive test suite for phrase saving across different translation scenarios."""

import pytest

from deubot.agent import GermanLearningAgent
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


# Test cases: (message, should_save, description)
# Reduced to key scenarios to speed up tests
TRANSLATION_TEST_CASES = [
    # English to German formats
    ("How to say umbrella?", True, "how to say format"),
    ("What's the German word for car?", True, "what's the German word format"),
    # German to English formats
    ("Was bedeutet Regenschirm?", True, "was bedeutet format"),
    ("What does Krankenhaus mean?", True, "what does X mean format"),
    # Direct German phrase
    ("Guten Abend", True, "direct German phrase"),
    # Translation request
    ("Translate 'the book' to German", True, "translate format"),
    # Grammar questions - should NOT save
    ("What is the dative case?", False, "grammar question"),
    ("What's the difference between der, die, das?", False, "grammar comparison"),
]


@pytest.mark.parametrize("test_message,should_save,description", TRANSLATION_TEST_CASES)
def test_translation_request_saving(
    agent: GermanLearningAgent,
    test_db: PhrasesDB,
    test_message: str,
    should_save: bool,
    description: str,
):
    """Test that translation requests save phrases correctly."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act
    _ = list(agent.process_message(test_message))

    # Assert
    final_count = len(test_db.get_all_phrases())
    phrases_added = final_count - initial_count

    if should_save:
        assert phrases_added > 0, (
            f"Expected phrase to be saved for '{test_message}' ({description}), " f"but no phrase was saved."
        )
    else:
        assert phrases_added == 0, (
            f"Expected NO phrase to be saved for '{test_message}' ({description}), "
            f"but {phrases_added} phrase(s) were saved"
        )


# Removed test_comprehensive_saving_summary - redundant with parameterized tests and too slow


def test_save_phrases_tool_called(agent: GermanLearningAgent):
    """Test that save_phrases tool is actually called for translation requests."""
    # Arrange
    test_message = "How to say table?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check log outputs for tool call
    from deubot.agent import LogOutput

    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_call_logs = [log.message for log in log_outputs if "Tool call: save_phrases" in log.message]

    assert len(tool_call_logs) > 0, (
        f"Expected save_phrases tool to be called for '{test_message}', "
        f"but no tool call was logged. Logs: {[log_msg.message for log_msg in log_outputs]}"
    )


def test_function_call_in_response_types(agent: GermanLearningAgent):
    """Test that save_phrases is called for translation requests."""
    # Arrange
    test_message = "How to say window?"

    # Act
    _ = list(agent.process_message(test_message))

    # Assert - verify the phrase was actually saved to the database
    phrases = agent.db.get_all_phrases()
    assert len(phrases) > 0, "Expected phrase to be saved for translation request"
