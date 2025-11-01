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


def test_add_duplicate_phrase_returns_same_id(temp_db):
    """Adding the same phrase twice should return the same ID."""
    phrase_id_1, is_new_1, _ = temp_db.add_phrase("der Hund")
    phrase_id_2, is_new_2, existing = temp_db.add_phrase("der Hund")

    assert is_new_1
    assert not is_new_2
    assert phrase_id_1 == phrase_id_2
    assert existing == "der Hund"


def test_add_duplicate_phrase_no_count_increase(temp_db):
    """Adding duplicate phrase should not increase phrase count."""
    temp_db.add_phrase("der Hund")
    initial_count = len(temp_db.phrases)

    temp_db.add_phrase("der Hund")
    final_count = len(temp_db.phrases)

    assert initial_count == final_count == 1


def test_add_duplicate_returns_correct_flags(temp_db):
    """Verify the tuple return values are correct."""
    phrase_id_1, is_new_1, existing_1 = temp_db.add_phrase("die Katze")

    assert is_new_1 is True
    assert existing_1 is None

    phrase_id_2, is_new_2, existing_2 = temp_db.add_phrase("die Katze")

    assert is_new_2 is False
    assert existing_2 == "die Katze"
    assert phrase_id_1 == phrase_id_2


def test_similar_phrases_detected(temp_db):
    """Test that variations of phrases are detected as duplicates."""
    phrase_id_1, _, _ = temp_db.add_phrase("der Hund")

    # Test various similar formats
    variations = [
        "Der Hund",  # Different case
        "der  Hund",  # Extra space
        "  der Hund  ",  # Leading/trailing space
        "Hund",  # Without article
    ]

    for variation in variations:
        phrase_id, is_new, existing = temp_db.add_phrase(variation)
        assert not is_new, f"Failed for variation: {variation}"
        assert phrase_id == phrase_id_1, f"Failed for variation: {variation}"
        assert existing == "der Hund", f"Failed for variation: {variation}"


def test_different_phrases_not_detected(temp_db):
    """Test that different phrases get different IDs."""
    id1, is_new1, _ = temp_db.add_phrase("der Hund")
    id2, is_new2, _ = temp_db.add_phrase("die Katze")
    id3, is_new3, _ = temp_db.add_phrase("das Auto")

    assert is_new1 and is_new2 and is_new3
    assert id1 != id2
    assert id2 != id3
    assert id1 != id3


def test_persistence_of_deduplication(temp_db):
    """Test that deduplication works after loading from disk."""
    db_path = temp_db.db_path

    # Add phrase and close
    temp_db.add_phrase("der Hund")
    del temp_db

    # Reload database
    new_db = PhrasesDB(db_path=str(db_path))
    phrase_id, is_new, existing = new_db.add_phrase("der Hund")

    assert not is_new
    assert existing == "der Hund"


def test_idempotency_multiple_duplicates(temp_db):
    """Test adding the same phrase multiple times."""
    phrase_id_1, is_new_1, _ = temp_db.add_phrase("Guten Morgen")

    # Add same phrase 5 more times
    for _ in range(5):
        phrase_id, is_new, existing = temp_db.add_phrase("Guten Morgen")
        assert not is_new
        assert phrase_id == phrase_id_1
        assert existing == "Guten Morgen"

    # Database should still have only 1 phrase
    assert len(temp_db.phrases) == 1


def test_batch_add_with_duplicates(temp_db):
    """Test adding multiple phrases where some are duplicates."""
    # Add initial phrases
    temp_db.add_phrase("der Hund")
    temp_db.add_phrase("die Katze")

    # Add batch with mix of new and duplicate
    phrases_to_add = [
        "das Auto",  # new
        "der Hund",  # duplicate
        "der Baum",  # new
        "die Katze",  # duplicate
    ]

    results = [temp_db.add_phrase(phrase) for phrase in phrases_to_add]

    # Check results
    assert results[0][1] is True  # das Auto - new
    assert results[1][1] is False  # der Hund - duplicate
    assert results[2][1] is True  # der Baum - new
    assert results[3][1] is False  # die Katze - duplicate

    # Should have 4 unique phrases total
    assert len(temp_db.phrases) == 4


def test_find_similar_phrase_method(temp_db):
    """Test the find_similar_phrase method directly."""
    temp_db.add_phrase("der Hund")

    # Should find similar
    similar = temp_db.find_similar_phrase("der Hund")
    assert similar is not None
    assert similar.german == "der Hund"

    # Should find with variation
    similar = temp_db.find_similar_phrase("Der Hund")
    assert similar is not None
    assert similar.german == "der Hund"

    # Should not find different phrase
    similar = temp_db.find_similar_phrase("die Katze")
    assert similar is None


def test_normalization_preserves_original(temp_db):
    """Test that original phrase is preserved in database."""
    original = "Der Große Hund"
    phrase_id, is_new, _ = temp_db.add_phrase(original)

    # Original should be preserved
    phrase = temp_db.phrases[phrase_id]
    assert phrase.german == original

    # But should still match variations
    _, is_new_2, existing = temp_db.add_phrase("der große hund")
    assert not is_new_2
    assert existing == original
