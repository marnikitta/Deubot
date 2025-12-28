"""Tests for the translations module."""

import pytest
from unittest.mock import Mock, MagicMock
from openai import OpenAI

from deubot.translations import TranslationCard, TranslationService


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


class TestTranslationCardDataclass:
    """Unit tests for TranslationCard dataclass."""

    pytestmark = pytest.mark.unit

    def test_translation_card_creation(self):
        """Test TranslationCard dataclass creation."""
        card = TranslationCard(
            phrase_id="42",
            german="Guten Morgen",
            explanation="<b>Good morning</b>",
        )
        assert card.phrase_id == "42"
        assert card.german == "Guten Morgen"
        assert card.explanation == "<b>Good morning</b>"

    def test_translation_card_equality(self):
        """Test TranslationCard equality."""
        card1 = TranslationCard(phrase_id="1", german="Hallo", explanation="Hello")
        card2 = TranslationCard(phrase_id="1", german="Hallo", explanation="Hello")
        assert card1 == card2


class TestCacheBehavior:
    """Unit tests for translation cache."""

    pytestmark = pytest.mark.unit

    def test_cache_stores_translation(self):
        """Test that translations are cached."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        card1 = service.get_translation_card("1", "Guten Morgen")
        assert card1.explanation == "<b>Translation</b>"
        assert mock_client.responses.create.call_count == 1

        card2 = service.get_translation_card("2", "Guten Morgen")
        assert card2.explanation == "<b>Translation</b>"
        assert mock_client.responses.create.call_count == 1

    def test_separate_instances_have_separate_caches(self):
        """Test that different service instances have separate caches."""
        mock_client = _create_mock_client()
        service1 = TranslationService(mock_client, "gpt-4")
        service2 = TranslationService(mock_client, "gpt-4")

        service1.get_translation_card("1", "Hallo")
        assert mock_client.responses.create.call_count == 1

        service2.get_translation_card("1", "Hallo")
        assert mock_client.responses.create.call_count == 2

    def test_clear_cache(self):
        """Test that clear_cache clears the cache."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        service.get_translation_card("1", "Hallo")
        assert mock_client.responses.create.call_count == 1

        service.clear_cache()

        service.get_translation_card("1", "Hallo")
        assert mock_client.responses.create.call_count == 2


class TestParallelExecution:
    """Unit tests for parallel execution."""

    pytestmark = pytest.mark.unit

    def test_parallel_maintains_order(self):
        """Test that parallel execution returns cards in original order."""
        mock_client = _create_mock_client()
        service = TranslationService(mock_client, "gpt-4")

        phrases = [
            {"id": "1", "german": "Hallo"},
            {"id": "2", "german": "Danke"},
            {"id": "3", "german": "Bitte"},
        ]

        cards = service.get_translation_cards_parallel(phrases)

        assert len(cards) == 3
        assert cards[0].phrase_id == "1"
        assert cards[0].german == "Hallo"
        assert cards[1].phrase_id == "2"
        assert cards[1].german == "Danke"
        assert cards[2].phrase_id == "3"
        assert cards[2].german == "Bitte"

    def test_parallel_empty_list(self):
        """Test parallel execution with empty phrase list."""
        mock_client = Mock(spec=OpenAI)
        service = TranslationService(mock_client, "gpt-4")
        cards = service.get_translation_cards_parallel([])
        assert cards == []

    def test_parallel_handles_errors(self):
        """Test that failed LLM calls produce fallback cards."""
        mock_client = Mock(spec=OpenAI)
        mock_client.responses.create.side_effect = Exception("API Error")
        service = TranslationService(mock_client, "gpt-4")

        phrases = [{"id": "1", "german": "Hallo"}]

        cards = service.get_translation_cards_parallel(phrases)

        assert len(cards) == 1
        assert cards[0].phrase_id == "1"
        assert cards[0].german == "Hallo"
        assert "Translation unavailable" in cards[0].explanation


class TestLLMIntegration:
    """LLM integration tests - require OpenAI API key."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        """Create TranslationService for testing."""
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_get_translation_card_produces_valid_html(self, translation_service):
        """Test that translation cards contain expected HTML structure."""
        card = translation_service.get_translation_card("1", "Guten Morgen")

        assert card.phrase_id == "1"
        assert card.german == "Guten Morgen"
        assert "<b>" in card.explanation
        assert len(card.explanation) > 50

    def test_translation_card_contains_key_elements(self, translation_service):
        """Test that translation includes pronunciation and examples."""
        card = translation_service.get_translation_card("1", "das Krankenhaus")

        explanation_lower = card.explanation.lower()
        assert "hospital" in explanation_lower

    def test_parallel_cards_all_have_content(self, translation_service):
        """Test that parallel execution produces complete cards for all phrases."""
        phrases = [
            {"id": "1", "german": "Hallo"},
            {"id": "2", "german": "Danke"},
            {"id": "3", "german": "Bitte"},
        ]

        cards = translation_service.get_translation_cards_parallel(phrases, max_workers=3)

        assert len(cards) == 3
        for card, phrase in zip(cards, phrases):
            assert card.phrase_id == phrase["id"]
            assert card.german == phrase["german"]
            assert len(card.explanation) > 20
