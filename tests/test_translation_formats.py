"""Tests for pronunciation and transcription formats in translation cards."""

import re

import pytest
from openai import OpenAI

from deubot.translations import ReviewDirection, TranslationService


def has_pronunciation_section(text: str) -> bool:
    """Check if text contains a proper pronunciation section with IPA and approximation.

    Expected format: <b>Pronunciation:</b> /IPA/ (approx)
    Example: <b>Pronunciation:</b> /tɪʃ/ (TISH)
    """
    # Look for pronunciation pattern: /something/ followed by (something)
    # This captures the format: /IPA/ (approx) where IPA contains phonetic chars
    # and approx is a short English approximation
    pronunciation_pattern = re.compile(
        r"pronunciation.*?/[^/]+/\s*\([A-Za-zÀ-ž][A-Za-zÀ-ž \-]*\)", re.IGNORECASE | re.DOTALL
    )
    return bool(pronunciation_pattern.search(text))


class TestNounPronunciation:
    """Test pronunciation format in noun cards."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_masculine_noun_pronunciation(self, translation_service):
        """Test pronunciation for masculine noun."""
        card = translation_service.get_translation_card(
            "1", "der Tisch", "the table", ReviewDirection.GERMAN_TO_ENGLISH
        )
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for noun, got: {card.explanation[:500]}"

    def test_feminine_noun_pronunciation(self, translation_service):
        """Test pronunciation for feminine noun."""
        card = translation_service.get_translation_card("1", "die Katze", "the cat", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for feminine noun, got: {card.explanation[:500]}"

    def test_neuter_noun_pronunciation(self, translation_service):
        """Test pronunciation for neuter noun."""
        card = translation_service.get_translation_card("1", "das Buch", "the book", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for neuter noun, got: {card.explanation[:500]}"


class TestVerbPronunciation:
    """Test pronunciation format in verb cards."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_irregular_verb_pronunciation(self, translation_service):
        """Test that irregular verb cards include pronunciation."""
        card = translation_service.get_translation_card("1", "fahren", "to drive", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for irregular verb, got: {card.explanation[:500]}"

    def test_regular_verb_pronunciation(self, translation_service):
        """Test pronunciation for regular verb."""
        card = translation_service.get_translation_card("1", "spielen", "to play", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for regular verb, got: {card.explanation[:500]}"

    def test_sein_verb_pronunciation(self, translation_service):
        """Test pronunciation for highly irregular 'sein'."""
        card = translation_service.get_translation_card("1", "sein", "to be", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for 'sein', got: {card.explanation[:500]}"


class TestPrepositionPronunciation:
    """Test pronunciation format in preposition cards."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_mit_pronunciation(self, translation_service):
        """Test pronunciation for 'mit'."""
        card = translation_service.get_translation_card("1", "mit", "with", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for 'mit', got: {card.explanation[:500]}"

    def test_fur_pronunciation(self, translation_service):
        """Test pronunciation for 'für'."""
        card = translation_service.get_translation_card("1", "für", "for", ReviewDirection.GERMAN_TO_ENGLISH)
        assert has_pronunciation_section(
            card.explanation
        ), f"Missing pronunciation for 'für', got: {card.explanation[:500]}"
