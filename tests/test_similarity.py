import tempfile
from pathlib import Path

import pytest

from deubot.database import PhrasesDB


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db.gz", delete=False) as f:
        db_path = f.name
    db = PhrasesDB(db_path=db_path)
    yield db
    Path(db_path).unlink(missing_ok=True)


def test_exact_match(temp_db):
    """Exact same phrase should be detected as duplicate."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der Hund")

    assert not is_new
    assert existing == "der Hund"


def test_case_difference(temp_db):
    """Different case should be detected as duplicate."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("Der Hund")

    assert not is_new
    assert existing == "der Hund"


def test_article_variations(temp_db):
    """Phrase with and without article should be detected as duplicate."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("Hund")

    assert not is_new
    assert existing == "der Hund"


def test_article_variations_reverse(temp_db):
    """Adding article to existing phrase without article should match."""
    temp_db.add_phrase("Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der Hund")

    assert not is_new
    assert existing == "Hund"


def test_different_articles_same_word(temp_db):
    """Different articles for the same word should be detected as duplicate."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("die Hund")

    assert not is_new
    assert existing == "der Hund"


def test_whitespace_variations(temp_db):
    """Extra whitespace should not affect matching."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der  Hund")

    assert not is_new
    assert existing == "der Hund"


def test_unicode_normalization(temp_db):
    """Different unicode representations should match."""
    # Using a word with umlaut
    temp_db.add_phrase("über")
    phrase_id_2, is_new, existing = temp_db.add_phrase("über")  # Same visual result

    assert not is_new
    assert existing == "über"


def test_completely_different_words(temp_db):
    """Completely different words should NOT match."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("die Katze")

    assert is_new
    assert existing is None


def test_similar_but_different_words(temp_db):
    """Similar but different words should NOT match."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der Mund")

    assert is_new
    assert existing is None


def test_phrases_with_multiple_words(temp_db):
    """Multi-word phrases should match correctly."""
    temp_db.add_phrase("Guten Morgen")
    phrase_id_2, is_new, existing = temp_db.add_phrase("guten morgen")

    assert not is_new
    assert existing == "Guten Morgen"


def test_phrases_with_multiple_words_different(temp_db):
    """Different multi-word phrases should NOT match."""
    temp_db.add_phrase("Guten Morgen")
    phrase_id_2, is_new, existing = temp_db.add_phrase("Guten Abend")

    assert is_new
    assert existing is None


def test_leading_trailing_spaces(temp_db):
    """Leading and trailing spaces should be normalized."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("  der Hund  ")

    assert not is_new
    assert existing == "der Hund"


def test_no_duplicates_when_empty(temp_db):
    """First phrase should always be saved as new."""
    phrase_id, is_new, existing = temp_db.add_phrase("der Hund")

    assert is_new
    assert existing is None


def test_multiple_different_phrases(temp_db):
    """Multiple different phrases should all be saved."""
    id1, is_new1, _ = temp_db.add_phrase("der Hund")
    id2, is_new2, _ = temp_db.add_phrase("die Katze")
    id3, is_new3, _ = temp_db.add_phrase("das Auto")

    assert is_new1 and is_new2 and is_new3
    assert id1 != id2 != id3


def test_indefinite_articles(temp_db):
    """Indefinite articles should also be stripped."""
    temp_db.add_phrase("ein Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der Hund")

    assert not is_new
    assert existing == "ein Hund"


def test_similarity_threshold_edge_case(temp_db):
    """Test that words with low similarity are not matched."""
    temp_db.add_phrase("der Hund")
    phrase_id_2, is_new, existing = temp_db.add_phrase("der Hand")

    # "Hund" and "Hand" are similar but should not match (4 chars, 2 different)
    # With trigram similarity: both have 5 trigrams each, shared depends on overlap
    # This is a borderline case - adjust threshold if needed
    assert is_new
    assert existing is None
