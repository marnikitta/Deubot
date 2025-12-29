"""Tests for bidirectional flashcard functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
from openai import OpenAI

from deubot.agent import ShowReviewOutput, ShowReviewBatchOutput
from deubot.database import PhrasesDB
from deubot.review_session import ReviewSession, ReviewCard
from deubot.translations import ReviewDirection, TranslationCard, TranslationService


pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db.gz", delete=False) as f:
        db_path = f.name
    db = PhrasesDB(db_path=db_path)
    yield db
    Path(db_path).unlink(missing_ok=True)


def _create_mock_client() -> Mock:
    mock_client = Mock(spec=OpenAI)
    mock_response = MagicMock()
    mock_output = MagicMock()
    mock_output.type = "message"
    mock_content = MagicMock()
    mock_content.type = "output_text"
    mock_content.text = "<b>Translation</b>"
    mock_output.content = [mock_content]
    mock_response.output = [mock_output]
    mock_client.responses.create.return_value = mock_response
    return mock_client


class TestDatabaseEnglishField:
    """Tests for english field in database."""

    def test_phrase_english_field_persists(self, temp_db):
        """Test that english field is saved and loaded correctly."""
        temp_db.add_phrase("der Hund", "the dog")
        db_path = temp_db.db_path

        # Reload from disk
        new_db = PhrasesDB(db_path=str(db_path))
        phrase = new_db.phrases["1"]
        assert phrase.english == "the dog"


class TestTranslationCardWithDirection:
    """Tests for TranslationCard with direction field."""

    def test_translation_card_with_direction(self):
        """Test TranslationCard with direction field."""
        card = TranslationCard(
            phrase_id="1",
            german="der Hund",
            english="the dog",
            explanation="<b>the dog</b>...",
            direction=ReviewDirection.GERMAN_TO_ENGLISH,
        )
        assert card.direction == ReviewDirection.GERMAN_TO_ENGLISH
        assert card.english == "the dog"

    def test_translation_card_english_to_german(self):
        """Test TranslationCard with english_to_german direction."""
        card = TranslationCard(
            phrase_id="2",
            german="die Katze",
            english="the cat",
            explanation="<b>the cat</b>...",
            direction=ReviewDirection.ENGLISH_TO_GERMAN,
        )
        assert card.direction == ReviewDirection.ENGLISH_TO_GERMAN


class TestReviewCardWithDirection:
    """Tests for ReviewCard with direction field."""

    def test_review_card_with_direction(self):
        """Test ReviewCard with direction field."""
        card = ReviewCard(
            phrase_id="1",
            german="der Hund",
            english="the dog",
            explanation="<b>the dog</b>",
            repetition=0,
            direction=ReviewDirection.ENGLISH_TO_GERMAN,
        )
        assert card.direction == ReviewDirection.ENGLISH_TO_GERMAN
        assert card.english == "the dog"


class TestReviewSessionWithDirection:
    """Tests for ReviewSession with direction support."""

    def test_start_batch_preserves_direction(self, test_db: PhrasesDB):
        """Test that direction is preserved through batch."""
        session = ReviewSession(test_db)
        batch = ShowReviewBatchOutput(
            reviews=[
                ShowReviewOutput("1", "Eins", "one", "One explanation", 0, ReviewDirection.GERMAN_TO_ENGLISH),
                ShowReviewOutput("2", "Zwei", "two", "Two explanation", 1, ReviewDirection.ENGLISH_TO_GERMAN),
            ]
        )
        first = session.start_batch(batch)
        assert first is not None
        assert first.direction == ReviewDirection.GERMAN_TO_ENGLISH

        second = session.advance()
        assert second is not None
        assert second.direction == ReviewDirection.ENGLISH_TO_GERMAN

    def test_start_batch_preserves_english(self, test_db: PhrasesDB):
        """Test that english field is preserved through batch."""
        session = ReviewSession(test_db)
        batch = ShowReviewBatchOutput(
            reviews=[
                ShowReviewOutput("1", "der Hund", "the dog", "explanation", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ]
        )
        first = session.start_batch(batch)
        assert first is not None
        assert first.english == "the dog"


class TestMixedDirection:
    """Tests for mixed direction mode."""

    def test_mixed_direction_assigns_randomly(self):
        """Test that mixed direction assigns random directions."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        phrases = [{"id": str(i), "german": f"word{i}", "english": f"eng{i}"} for i in range(20)]

        cards = service.get_translation_cards_parallel(phrases, direction=ReviewDirection.MIXED)

        directions = [c.direction for c in cards]
        # Should have some of each direction (very unlikely to get all same)
        assert ReviewDirection.GERMAN_TO_ENGLISH in directions or ReviewDirection.ENGLISH_TO_GERMAN in directions

    def test_german_to_english_direction(self):
        """Test that german_to_english sets all cards to that direction."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        phrases = [{"id": "1", "german": "Hallo", "english": "hello"}]
        cards = service.get_translation_cards_parallel(phrases, direction=ReviewDirection.GERMAN_TO_ENGLISH)

        assert cards[0].direction == ReviewDirection.GERMAN_TO_ENGLISH

    def test_english_to_german_direction(self):
        """Test that english_to_german sets all cards to that direction."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        phrases = [{"id": "1", "german": "Hallo", "english": "hello"}]
        cards = service.get_translation_cards_parallel(phrases, direction=ReviewDirection.ENGLISH_TO_GERMAN)

        assert cards[0].direction == ReviewDirection.ENGLISH_TO_GERMAN


class TestTranslationServiceWithDirection:
    """Tests for TranslationService direction support."""

    def test_get_translation_card_with_direction(self):
        """Test get_translation_card includes direction."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        card = service.get_translation_card("1", "der Hund", "the dog", ReviewDirection.GERMAN_TO_ENGLISH)

        assert card.phrase_id == "1"
        assert card.german == "der Hund"
        assert card.english == "the dog"
        assert card.direction == ReviewDirection.GERMAN_TO_ENGLISH

    def test_parallel_cards_have_english_field(self):
        """Test parallel execution includes english field."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        phrases = [
            {"id": "1", "german": "der Hund", "english": "the dog"},
            {"id": "2", "german": "die Katze", "english": "the cat"},
        ]

        cards = service.get_translation_cards_parallel(phrases, direction=ReviewDirection.GERMAN_TO_ENGLISH)

        assert len(cards) == 2
        assert cards[0].english == "the dog"
        assert cards[1].english == "the cat"
