"""Comprehensive test suite for phrase saving across different translation scenarios."""

import pytest

from deubot.agent import GermanLearningAgent, LogOutput
from deubot.database import PhrasesDB


# Test cases: (message, should_save, description)
TRANSLATION_TEST_CASES = [
    # English to German - should save
    ("How to say umbrella?", True, "how to say format"),
    ("How to say good morning?", True, "how to say format"),
    ("How do I say thank you?", True, "how do I say format"),
    ("How would I say I love you?", True, "how would I say format"),
    ("What's the German word for car?", True, "what's the German word format"),

    # German to English - should save
    ("Was bedeutet Regenschirm?", True, "was bedeutet format"),
    ("Was bedeutet Entschuldigung?", True, "was bedeutet format"),
    ("What does Krankenhaus mean?", True, "what does X mean format"),
    ("What is Flughafen?", True, "what is X format"),

    # Direct German phrases - should save
    ("Guten Abend", True, "direct German phrase"),
    ("Wie geht es dir?", True, "direct German question"),
    ("Ich möchte ein Bier", True, "direct German sentence"),

    # Translation requests - should save
    ("Translate 'the book' to German", True, "translate format"),
    ("Give me the German for 'beautiful'", True, "give me format"),

    # Grammar questions - should NOT save
    ("What is the dative case?", False, "grammar question"),
    ("Explain German word order", False, "grammar explanation"),
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
    outputs = list(agent.process_message(test_message))

    # Get response types from log outputs
    response_types = []
    for output in outputs:
        if isinstance(output, LogOutput) and "Response types:" in output.message:
            response_types_str = output.message.split("Response types: ")[1]
            break

    # Assert
    final_count = len(test_db.get_all_phrases())
    phrases_added = final_count - initial_count

    if should_save:
        assert phrases_added > 0, (
            f"Expected phrase to be saved for '{test_message}' ({description}), "
            f"but no phrase was saved. Response types: {response_types}"
        )
    else:
        assert phrases_added == 0, (
            f"Expected NO phrase to be saved for '{test_message}' ({description}), "
            f"but {phrases_added} phrase(s) were saved"
        )


def test_comprehensive_saving_summary(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test a batch of translation requests and report statistics."""
    # Arrange
    translation_requests = [
        "How to say umbrella?",
        "Was bedeutet Entschuldigung?",
        "What does Krankenhaus mean?",
        "Guten Abend",
        "Translate 'the book' to German",
    ]

    grammar_questions = [
        "What is the dative case?",
        "Explain German word order",
        "What's the difference between der, die, das?",
    ]

    # Act - process translation requests
    translation_saved_count = 0
    for msg in translation_requests:
        initial_count = len(test_db.get_all_phrases())
        list(agent.process_message(msg))
        agent.clear_history()  # Clear history between tests
        final_count = len(test_db.get_all_phrases())
        if final_count > initial_count:
            translation_saved_count += 1

    # Act - process grammar questions
    grammar_saved_count = 0
    for msg in grammar_questions:
        initial_count = len(test_db.get_all_phrases())
        list(agent.process_message(msg))
        agent.clear_history()
        final_count = len(test_db.get_all_phrases())
        if final_count > initial_count:
            grammar_saved_count += 1

    # Assert - calculate success rate
    translation_success_rate = translation_saved_count / len(translation_requests) * 100
    grammar_correctness_rate = (len(grammar_questions) - grammar_saved_count) / len(grammar_questions) * 100

    # We expect at least 80% success rate for translations (allowing some model variability)
    assert translation_success_rate >= 80, (
        f"Translation success rate too low: {translation_success_rate:.1f}% "
        f"({translation_saved_count}/{len(translation_requests)} saved)"
    )

    # We expect 100% correctness for NOT saving grammar questions
    assert grammar_correctness_rate == 100, (
        f"Grammar questions should not be saved, but {grammar_saved_count} were saved"
    )


def test_save_phrase_tool_called(agent: GermanLearningAgent):
    """Test that save_phrase tool is actually called for translation requests."""
    # Arrange
    test_message = "How to say table?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check log outputs for tool call
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    tool_call_logs = [log.message for log in log_outputs if "Tool call: save_phrase" in log.message]

    assert len(tool_call_logs) > 0, (
        f"Expected save_phrase tool to be called for '{test_message}', "
        f"but no tool call was logged. Logs: {[l.message for l in log_outputs]}"
    )


def test_function_call_in_response_types(agent: GermanLearningAgent):
    """Test that response contains function_call type for translation requests."""
    # Arrange
    test_message = "How to say window?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check that response types include function_call
    log_outputs = [o for o in outputs if isinstance(o, LogOutput)]
    response_type_logs = [log.message for log in log_outputs if "Response types:" in log.message]

    assert len(response_type_logs) > 0, "No response types logged"

    response_types = response_type_logs[0]
    assert "function_call" in response_types, (
        f"Expected 'function_call' in response types for translation request, "
        f"got: {response_types}"
    )
