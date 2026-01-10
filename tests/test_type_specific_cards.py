"""Tests for type-specific translation card generation."""

import pytest
from openai import OpenAI

from deubot.translations import ReviewDirection, TranslationService


class TestNounCards:
    """Test noun-specific card generation."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_noun_card_shows_plural(self, translation_service):
        """Test that noun cards include plural form."""
        card = translation_service.get_translation_card(
            "1", "der Tisch", "the table", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        assert (
            "plural" in explanation_lower or "tische" in explanation_lower
        ), f"Expected plural info for noun, got: {card.explanation[:200]}"

    def test_noun_card_shows_gender(self, translation_service):
        """Test that feminine noun cards indicate gender."""
        card = translation_service.get_translation_card("1", "die Katze", "the cat", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        assert any(
            x in explanation_lower for x in ["feminine", "die", "gender"]
        ), f"Expected gender indication for noun, got: {card.explanation[:200]}"

    def test_noun_card_with_compound_word(self, translation_service):
        """Test that compound nouns get proper treatment."""
        card = translation_service.get_translation_card(
            "1", "das Krankenhaus", "the hospital", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        # Should mention hospital and have examples
        assert "hospital" in explanation_lower
        assert len(card.explanation) > 100

    def test_compound_noun_shows_subwords(self, translation_service):
        """Test that compound nouns show breakdown into subwords."""
        card = translation_service.get_translation_card(
            "1", "das Krankenhaus", "the hospital", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        # Should show subword breakdown: krank (sick) + Haus (house)
        assert any(
            x in explanation_lower for x in ["krank", "haus", "sick", "house", "compound"]
        ), f"Expected subword breakdown for compound noun, got: {card.explanation[:400]}"


class TestVerbCards:
    """Test verb-specific card generation."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_irregular_verb_shows_stem_change(self, translation_service):
        """Test that irregular verbs show conjugation with stem change."""
        card = translation_service.get_translation_card("1", "fahren", "to drive", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        # Check for stem-changing forms or umlaut mention
        assert any(
            x in explanation_lower for x in ["fährst", "fährt", "ä", "stem", "irregular"]
        ), f"Expected stem change info for irregular verb, got: {card.explanation[:300]}"

    def test_regular_verb_shows_examples(self, translation_service):
        """Test that regular verbs show variation through examples."""
        card = translation_service.get_translation_card("1", "spielen", "to play", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        # Should contain examples with the verb
        assert "spiel" in explanation_lower, f"Expected examples with verb root, got: {card.explanation[:200]}"

    def test_sein_verb_shows_conjugation(self, translation_service):
        """Test that highly irregular verb 'sein' shows conjugation."""
        card = translation_service.get_translation_card("1", "sein", "to be", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        # Should show some conjugation forms
        assert any(
            x in explanation_lower for x in ["bin", "bist", "ist", "sind"]
        ), f"Expected conjugation for 'sein', got: {card.explanation[:300]}"


class TestChunkCards:
    """Test chunk/phrase card generation."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_chunk_explains_usage(self, translation_service):
        """Test that chunk cards explain usage."""
        card = translation_service.get_translation_card(
            "1", "Ich möchte...", "I would like...", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        assert any(
            x in explanation_lower for x in ["polite", "request", "want", "usage", "use"]
        ), f"Expected usage explanation for chunk, got: {card.explanation[:300]}"

    def test_chunk_shows_variations(self, translation_service):
        """Test that chunk cards show variations."""
        card = translation_service.get_translation_card(
            "1", "Es gibt...", "There is/are...", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        # Check for variations or examples
        assert any(
            x in explanation_lower for x in ["variation", "example", "es gibt"]
        ), f"Expected variations for chunk, got: {card.explanation[:300]}"

    def test_question_chunk(self, translation_service):
        """Test that question chunks are handled properly."""
        card = translation_service.get_translation_card(
            "1", "Kann ich ... haben?", "Can I have...?", ReviewDirection.GERMAN_TO_ENGLISH
        )
        explanation_lower = card.explanation.lower()
        assert any(
            x in explanation_lower for x in ["can", "have", "request", "ask"]
        ), f"Expected question chunk explanation, got: {card.explanation[:300]}"


class TestPrepositionCards:
    """Test preposition card generation."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_mit_shows_dative_case(self, translation_service):
        """Test that 'mit' shows dative case requirement."""
        card = translation_service.get_translation_card("1", "mit", "with", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        assert any(
            x in explanation_lower for x in ["dativ", "dative", "case"]
        ), f"Expected dative case info for 'mit', got: {card.explanation[:300]}"

    def test_fur_shows_accusative_case(self, translation_service):
        """Test that 'für' shows accusative case requirement."""
        card = translation_service.get_translation_card("1", "für", "for", ReviewDirection.GERMAN_TO_ENGLISH)
        explanation_lower = card.explanation.lower()
        assert any(
            x in explanation_lower for x in ["akkusativ", "accusative", "case"]
        ), f"Expected accusative case info for 'für', got: {card.explanation[:300]}"

    def test_preposition_shows_examples(self, translation_service):
        """Test that preposition cards include example sentences with case markers."""
        card = translation_service.get_translation_card("1", "bei", "at, near, with", ReviewDirection.GERMAN_TO_ENGLISH)
        # Should have examples
        assert (
            "bei" in card.explanation.lower() and len(card.explanation) > 100
        ), f"Expected examples for preposition, got: {card.explanation[:200]}"


class TestSentenceTemplateCards:
    """Test sentence template card generation."""

    pytestmark = pytest.mark.llm

    @pytest.fixture
    def translation_service(self, openai_credentials):
        client = OpenAI(api_key=openai_credentials["api_key"])
        return TranslationService(client, openai_credentials["light_model"])

    def test_sentence_explains_word_order(self, translation_service):
        """Test that sentence templates explain word order pattern."""
        card = translation_service.get_translation_card(
            "1",
            "Ich fahre morgen mit dem Bus nach Berlin",
            "I'm going to Berlin by bus tomorrow",
            ReviewDirection.GERMAN_TO_ENGLISH,
        )
        explanation_lower = card.explanation.lower()
        # Check for word order explanation (TMP, time, manner, place, structure, pattern)
        assert any(
            x in explanation_lower
            for x in ["time", "manner", "place", "order", "structure", "pattern", "tmp", "when", "how", "where"]
        ), f"Expected word order explanation, got: {card.explanation[:400]}"

    def test_sentence_shows_variations(self, translation_service):
        """Test that sentence cards show variations."""
        card = translation_service.get_translation_card(
            "1",
            "Ich gehe heute Abend ins Kino",
            "I'm going to the cinema tonight",
            ReviewDirection.GERMAN_TO_ENGLISH,
        )
        explanation_lower = card.explanation.lower()
        # Check for variations or structure breakdown
        assert any(
            x in explanation_lower for x in ["variation", "example", "kino", "heute"]
        ), f"Expected variations for sentence template, got: {card.explanation[:300]}"

    def test_modal_verb_sentence(self, translation_service):
        """Test sentence with modal verb explains verb-final structure."""
        card = translation_service.get_translation_card(
            "1",
            "Ich kann heute nicht kommen",
            "I can't come today",
            ReviewDirection.GERMAN_TO_ENGLISH,
        )
        explanation_lower = card.explanation.lower()
        # Should mention modal verbs or verb position
        assert any(
            x in explanation_lower for x in ["modal", "kann", "kommen", "end", "verb"]
        ), f"Expected modal verb explanation, got: {card.explanation[:300]}"
