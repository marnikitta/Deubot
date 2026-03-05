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


def test_get_vocabulary_offset_paging(temp_db):
    """get_vocabulary with offset should return non-overlapping pages."""
    temp_db.add_phrase("der Hund", "the dog")
    temp_db.add_phrase("die Katze", "the cat")
    temp_db.add_phrase("das Pferd", "the horse")
    temp_db.add_phrase("der Vogel", "the bird")

    page1 = temp_db.get_vocabulary(limit=2, offset=0, sort_by="id")
    page2 = temp_db.get_vocabulary(limit=2, offset=2, sort_by="id")

    assert len(page1) == 2
    assert len(page2) == 2
    page1_ids = {p["id"] for p in page1}
    page2_ids = {p["id"] for p in page2}
    assert page1_ids.isdisjoint(page2_ids)
    assert page1_ids | page2_ids == {"1", "2", "3", "4"}

    # Offset beyond total returns empty
    page3 = temp_db.get_vocabulary(limit=2, offset=10, sort_by="id")
    assert page3 == []


def test_get_phrases_by_ids_all_found(temp_db):
    """get_phrases_by_ids should return all phrases when all IDs exist."""
    temp_db.add_phrase("der Hund", "the dog")
    temp_db.add_phrase("die Katze", "the cat")

    found, not_found = temp_db.get_phrases_by_ids(["1", "2"])

    assert len(found) == 2
    assert len(not_found) == 0
    assert {p["id"] for p in found} == {"1", "2"}


def test_get_phrases_by_ids_some_not_found(temp_db):
    """get_phrases_by_ids should return found phrases and list missing IDs."""
    temp_db.add_phrase("der Hund", "the dog")

    found, not_found = temp_db.get_phrases_by_ids(["1", "999", "2"])

    assert len(found) == 1
    assert found[0]["id"] == "1"
    assert set(not_found) == {"999", "2"}


def test_get_phrases_by_ids_none_found(temp_db):
    """get_phrases_by_ids should return empty list when no IDs exist."""
    found, not_found = temp_db.get_phrases_by_ids(["1", "2", "3"])

    assert len(found) == 0
    assert set(not_found) == {"1", "2", "3"}


def test_get_phrases_by_ids_empty_list(temp_db):
    """get_phrases_by_ids with empty list should return empty results."""
    temp_db.add_phrase("der Hund", "the dog")

    found, not_found = temp_db.get_phrases_by_ids([])

    assert len(found) == 0
    assert len(not_found) == 0
