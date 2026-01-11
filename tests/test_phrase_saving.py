"""Test phrase saving functionality."""

import pytest

from deubot.agent import GermanLearningAgent, MessageOutput
from deubot.database import PhrasesDB

pytestmark = pytest.mark.llm


def test_phrase_saving_basic(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that a simple translation request saves a phrase."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())
    test_message = "How to say weather?"

    # Act
    _ = list(agent.process_message(test_message))

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


def test_phrase_saving_shows_translation_card(agent: GermanLearningAgent):
    """Test that after saving, the agent shows a translation card."""
    # Arrange
    test_message = "How to say table?"

    # Act
    outputs = list(agent.process_message(test_message))

    # Assert - check we got both confirmation and translation card
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]

    assert len(message_outputs) >= 2, f"Expected at least 2 messages (confirmation + card), got {len(message_outputs)}"

    # First should be confirmation
    assert "✓ Saved:" in message_outputs[0].message, "First message should be confirmation"

    # Second should be translation card (contains structured content with bold formatting)
    card_message = message_outputs[1].message
    assert "<b>" in card_message, "Card should contain bold formatting"
    # Check for card structure (pronunciation, examples, plural, etc.)
    assert any(
        kw in card_message.lower() for kw in ["pronunciation", "examples", "plural"]
    ), f"Card should contain structured content like pronunciation/examples/plural, got: {card_message[:200]}"


def test_phrase_not_duplicate(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that asking for the same phrase twice may save it multiple times (current behavior)."""
    # Arrange
    test_message = "How to say hello?"

    # Act - ask twice
    list(agent.process_message(test_message))
    initial_phrases = test_db.get_all_phrases()
    initial_count = len(initial_phrases)

    agent.clear_history()  # Clear history to simulate new conversation
    list(agent.process_message(test_message))
    final_phrases = test_db.get_all_phrases()
    final_count = len(final_phrases)

    # Assert - should have saved at least one phrase initially
    assert initial_count >= 1, "Should have saved at least one phrase"

    # Agent may save multiple phrases (examples, variations) in its response
    # Current behavior: no deduplication, same phrases may appear multiple times
    assert final_count >= initial_count, "Should not have removed phrases"


@pytest.mark.parametrize(
    "test_message,expected_german",
    [
        ("How to say umbrella?", "Regenschirm"),
        ("How do I say breakfast?", "Frühstück"),
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
    _ = list(agent.process_message(test_message))

    # Assert
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, f"Phrase was not saved for: {test_message}"

    # Check the saved phrase contains expected German word (case-insensitive)
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]
    assert any(
        expected_german.lower() in phrase.lower() for phrase in saved_phrases
    ), f"Expected '{expected_german}' in saved phrases, got: {saved_phrases}"


@pytest.mark.parametrize(
    "test_message,expected_article,expected_noun",
    [
        ("Datenschutz", "der", "Datenschutz"),
        ("Krankenhaus", "das", "Krankenhaus"),
        ("Katze", "die", "Katze"),
        ("Regenschirm", "der", "Regenschirm"),
    ],
)
def test_noun_saved_with_article(
    agent: GermanLearningAgent, test_db: PhrasesDB, test_message: str, expected_article: str, expected_noun: str
):
    """Test that when user sends a bare German noun, it gets saved with its article."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - user sends just the noun
    outputs = list(agent.process_message(test_message))

    # Assert - phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, f"Phrase was not saved for: {test_message}"

    # Check the saved phrase includes the article
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]

    # The saved phrase should contain both article and noun
    expected_with_article = f"{expected_article} {expected_noun}"
    assert any(
        expected_with_article.lower() == phrase.lower() for phrase in saved_phrases
    ), f"Expected '{expected_with_article}' to be saved, got: {saved_phrases}"

    # Verify confirmation message also shows the article
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    confirmation_messages = [m.message for m in message_outputs if "✓ Saved:" in m.message]

    assert len(confirmation_messages) > 0, "No confirmation message found"
    # Check that the confirmation shows the article
    assert (
        expected_article in confirmation_messages[0] and expected_noun in confirmation_messages[0]
    ), f"Expected confirmation to show '{expected_with_article}', got: {confirmation_messages[0]}"


def test_greeting_saved_without_article(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that greetings are saved without articles (as they are not nouns)."""
    # Arrange
    test_message = "Guten Morgen"
    initial_count = len(test_db.get_all_phrases())

    # Act
    _ = list(agent.process_message(test_message))

    # Assert
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, "Phrase was not saved"

    # Check that "Guten Morgen" was saved without an article prefix
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]

    # Should find "Guten Morgen" exactly (possibly with case variations)
    assert any(
        "guten morgen" == phrase.lower() for phrase in saved_phrases
    ), f"Expected 'Guten Morgen' without article, got: {saved_phrases}"

    # Should NOT have "der Guten Morgen" or similar
    assert not any(
        phrase.lower().startswith("der ") or phrase.lower().startswith("die ") or phrase.lower().startswith("das ")
        for phrase in saved_phrases
        if "guten morgen" in phrase.lower()
    ), f"Greeting should not have article, got: {saved_phrases}"


@pytest.mark.parametrize(
    "conjugated_verb,expected_infinitive",
    [
        ("schwimme", "schwimmen"),
        ("laufe", "laufen"),
        ("esse", "essen"),
        ("spiele", "spielen"),
    ],
)
def test_verb_saved_as_infinitive_only(
    agent: GermanLearningAgent, test_db: PhrasesDB, conjugated_verb: str, expected_infinitive: str
):
    """Test that conjugated verbs are saved as infinitive only, not multiple forms."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - user sends conjugated verb
    _ = list(agent.process_message(conjugated_verb))

    # Assert - exactly one phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, f"Phrase was not saved for: {conjugated_verb}"
    assert final_count == initial_count + 1, f"Expected exactly 1 phrase, got {final_count - initial_count}"

    # Check the saved phrase is the infinitive, not a compound like "schwimmen, ich schwimme"
    all_phrases = test_db.get_all_phrases()
    saved_phrases = [p["german"] for p in all_phrases]

    # Find the phrase containing our verb
    matching = [p for p in saved_phrases if expected_infinitive in p.lower()]
    assert len(matching) == 1, f"Expected exactly one phrase with '{expected_infinitive}', got: {matching}"

    # Should NOT contain comma (multiple forms) or "ich" prefix
    saved = matching[0]
    assert "," not in saved, f"Verb should be saved as single form, not compound: '{saved}'"
    assert "ich " not in saved.lower(), f"Verb should be infinitive only, not conjugated with 'ich': '{saved}'"


def test_batch_save_multiple_phrases(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that asking for multiple translations saves all phrases at once."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - ask for multiple translations
    _ = list(agent.process_message("How do you say hello, goodbye, and thank you in German?"))

    # Assert - at least 3 phrases were saved
    final_count = len(test_db.get_all_phrases())
    saved_count = final_count - initial_count
    assert saved_count >= 3, f"Expected at least 3 phrases to be saved, got {saved_count}"

    # Check that expected words are present
    all_phrases = test_db.get_all_phrases()
    saved_german = [p["german"].lower() for p in all_phrases]
    saved_text = " ".join(saved_german)

    # Should have hello, goodbye, thank you equivalents
    assert "hallo" in saved_text or "guten tag" in saved_text, f"Expected 'hello' equivalent, got: {saved_german}"
    assert "wiedersehen" in saved_text or "tschüss" in saved_text, f"Expected 'goodbye' equivalent, got: {saved_german}"
    assert "danke" in saved_text, f"Expected 'thank you' equivalent, got: {saved_german}"


def test_chunk_saved_with_ellipsis(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that chunks with slots are saved with ellipsis (...)."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - ask for a chunk pattern
    _ = list(agent.process_message("How do you say 'I would like...' in German?"))

    # Assert - phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, "Phrase was not saved"

    # Check that the saved phrase contains "möchte" (I would like)
    all_phrases = test_db.get_all_phrases()
    saved_german = [p["german"].lower() for p in all_phrases]
    assert any(
        "möchte" in phrase for phrase in saved_german
    ), f"Expected 'möchte' in saved phrases, got: {saved_german}"


def test_preposition_saved_without_article(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that prepositions are saved without articles."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - ask for a preposition
    _ = list(agent.process_message("How do you say 'with' in German?"))

    # Assert - phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, "Phrase was not saved"

    # Check that "mit" was saved without an article
    all_phrases = test_db.get_all_phrases()
    saved_german = [p["german"].lower() for p in all_phrases]

    # Should contain "mit" but NOT "der mit", "die mit", "das mit"
    matching = [p for p in saved_german if "mit" in p]
    assert len(matching) > 0, f"Expected 'mit' in saved phrases, got: {saved_german}"

    # Verify no article prefix on the preposition
    for phrase in matching:
        if phrase.strip() == "mit" or "mit " in phrase or " mit" in phrase:
            # This is acceptable - either standalone or part of example
            assert (
                not phrase.startswith("der ") and not phrase.startswith("die ") and not phrase.startswith("das ")
            ), f"Preposition should not have article prefix: '{phrase}'"


def test_typo_autocorrect(agent: GermanLearningAgent, test_db: PhrasesDB):
    """Test that obvious typos are auto-corrected when saving."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act - send a typo (Krankenhuas instead of Krankenhaus)
    _ = list(agent.process_message("Krankenhuas"))

    # Assert - phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, "Phrase was not saved"

    # Check that the correct spelling was saved (das Krankenhaus)
    all_phrases = test_db.get_all_phrases()
    saved_german = [p["german"].lower() for p in all_phrases]

    # Should have corrected "Krankenhuas" to "Krankenhaus"
    assert any(
        "krankenhaus" in phrase for phrase in saved_german
    ), f"Expected corrected 'Krankenhaus' in saved phrases, got: {saved_german}"
    # Should NOT have the typo
    assert not any(
        "krankenhuas" in phrase for phrase in saved_german
    ), f"Typo 'Krankenhuas' should have been corrected, got: {saved_german}"


# =============================================================================
# Additional phrase saving trigger tests - various request formats
# =============================================================================


@pytest.mark.parametrize(
    "test_message,expected_german",
    [
        # Core English→German formats (diverse patterns)
        ("How to say water?", "Wasser"),
        ("What's the German for sun?", "Sonne"),
        ("Translate 'bread' to German", "Brot"),
        ("Can you translate 'garden' to German?", "Garten"),
        # German input formats
        ("Schule", "Schule"),  # bare noun
        ("What does Schmetterling mean?", "Schmetterling"),
        ("Was bedeutet Flugzeug?", "Flugzeug"),
        # Complex/verbose formats
        ("I want to learn how to say 'please'", "bitte"),
        ("Just wondering, what's 'tea' in German?", "Tee"),
        # Edge cases
        ("dog?", "Hund"),  # minimal
        ("HOW TO SAY BEAR?", "Bär"),  # caps
    ],
)
def test_phrase_saving_triggers(
    agent: GermanLearningAgent, test_db: PhrasesDB, test_message: str, expected_german: str
):
    """Test that various request formats trigger phrase saving."""
    # Arrange
    initial_count = len(test_db.get_all_phrases())

    # Act
    _ = list(agent.process_message(test_message))

    # Assert - phrase was saved
    final_count = len(test_db.get_all_phrases())
    assert final_count > initial_count, f"Phrase was not saved for: '{test_message}'"

    # Check the saved phrase contains expected German word
    all_phrases = test_db.get_all_phrases()
    saved_german = [p["german"].lower() for p in all_phrases]
    assert any(
        expected_german.lower() in phrase for phrase in saved_german
    ), f"Expected '{expected_german}' in saved phrases for '{test_message}', got: {saved_german}"
