import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from deubot.database import PhrasesDB

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db.gz", delete=False) as f:
        db_path = f.name
    db = PhrasesDB(db_path=db_path)
    yield db
    Path(db_path).unlink(missing_ok=True)


def test_get_due_phrases_empty_database(temp_db):
    """Empty database should return empty list, not crash."""
    assert temp_db.get_due_phrases() == []


def test_get_due_phrases_fallback_when_none_due(temp_db):
    """When no phrases are due, should return phrases anyway (fallback behavior)."""
    temp_db.add_phrase("der Hund", "the dog")
    temp_db.add_phrase("die Katze", "the cat")

    # Set all to future
    future = (datetime.now() + timedelta(days=30)).isoformat()
    for phrase in temp_db.phrases.values():
        phrase.next_review = future

    # Should still return phrases (fallback)
    result = temp_db.get_due_phrases()
    assert len(result) == 2


def test_update_review_nonexistent_phrase(temp_db):
    """update_review with unknown phrase_id should not crash."""
    temp_db.add_phrase("der Hund", "the dog")
    temp_db.update_review("nonexistent_id", quality=4)
    assert len(temp_db.phrases) == 1


def test_in_memory_db_works():
    """Database with db_path=None should work without file operations."""
    db = PhrasesDB(db_path=None)
    phrase_id, is_new, _ = db.add_phrase("der Hund", "the dog")
    assert is_new
    db.update_review(phrase_id, quality=4)
    assert db.phrases[phrase_id].repetition == 1


def test_update_phrase_preserves_sm2_stats(temp_db):
    """update_phrase should preserve SM-2 statistics when updating text."""
    phrase_id, _, _ = temp_db.add_phrase("der Hund", "the dog")

    # Build up some review history
    temp_db.update_review(phrase_id, quality=4)
    temp_db.update_review(phrase_id, quality=4)
    original_ease = temp_db.phrases[phrase_id].ease_factor
    original_interval = temp_db.phrases[phrase_id].interval_days
    original_repetition = temp_db.phrases[phrase_id].repetition
    original_next_review = temp_db.phrases[phrase_id].next_review

    # Update the phrase
    result = temp_db.update_phrase(phrase_id, german="der große Hund", english="the big dog")

    # Verify update succeeded
    assert result is True
    assert temp_db.phrases[phrase_id].german == "der große Hund"
    assert temp_db.phrases[phrase_id].english == "the big dog"

    # Verify SM-2 stats preserved
    assert temp_db.phrases[phrase_id].ease_factor == original_ease
    assert temp_db.phrases[phrase_id].interval_days == original_interval
    assert temp_db.phrases[phrase_id].repetition == original_repetition
    assert temp_db.phrases[phrase_id].next_review == original_next_review


def test_update_phrase_german_only(temp_db):
    """update_phrase with only german should preserve english."""
    phrase_id, _, _ = temp_db.add_phrase("der Hund", "the dog")

    result = temp_db.update_phrase(phrase_id, german="der große Hund")

    assert result is True
    assert temp_db.phrases[phrase_id].german == "der große Hund"
    assert temp_db.phrases[phrase_id].english == "the dog"


def test_update_phrase_english_only(temp_db):
    """update_phrase with only english should preserve german."""
    phrase_id, _, _ = temp_db.add_phrase("der Hund", "the dog")

    result = temp_db.update_phrase(phrase_id, english="the big dog")

    assert result is True
    assert temp_db.phrases[phrase_id].german == "der Hund"
    assert temp_db.phrases[phrase_id].english == "the big dog"


def test_update_phrase_nonexistent(temp_db):
    """update_phrase with unknown phrase_id should return False."""
    temp_db.add_phrase("der Hund", "the dog")

    result = temp_db.update_phrase("nonexistent_id", german="der Katze")

    assert result is False
    assert len(temp_db.phrases) == 1
