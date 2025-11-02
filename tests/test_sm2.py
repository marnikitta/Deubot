"""Unit tests for SM-2 spaced repetition algorithm implementation."""

from datetime import datetime, timedelta

import pytest

from deubot.database import PhrasesDB

pytestmark = pytest.mark.unit


def test_new_phrase_starts_with_correct_defaults():
    """Test that new phrases have correct initial SM-2 values."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor == 2.5
    assert phrase.interval_days == 0
    assert phrase.repetition == 0


def test_first_successful_review_sets_interval_to_one_day():
    """Test I(1) = 1 day."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)

    phrase = db.phrases[phrase_id]
    assert phrase.interval_days == 1
    assert phrase.repetition == 1


def test_second_successful_review_sets_interval_to_six_days():
    """Test I(2) = 6 days."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)

    phrase = db.phrases[phrase_id]
    assert phrase.interval_days == 6
    assert phrase.repetition == 2


def test_third_successful_review_multiplies_by_ease_factor():
    """Test I(3) = I(2) * EF."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)

    phrase = db.phrases[phrase_id]
    assert phrase.repetition == 3
    assert phrase.interval_days == int(6 * phrase.ease_factor)


def test_ease_factor_increases_with_high_quality():
    """Test that quality 5 increases ease factor."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")
    initial_ef = db.phrases[phrase_id].ease_factor

    db.update_review(phrase_id, quality=5)

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor > initial_ef


def test_ease_factor_decreases_with_low_quality():
    """Test that quality 3 decreases ease factor."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")
    initial_ef = db.phrases[phrase_id].ease_factor

    db.update_review(phrase_id, quality=3)

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor < initial_ef


def test_ease_factor_has_minimum_of_1_3():
    """Test that ease factor never goes below 1.3."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    for _ in range(10):
        db.update_review(phrase_id, quality=0)

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor >= 1.3


def test_failure_resets_repetition_to_zero():
    """Test that quality < 3 resets repetition counter."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)

    assert db.phrases[phrase_id].repetition == 3

    db.update_review(phrase_id, quality=2)

    phrase = db.phrases[phrase_id]
    assert phrase.repetition == 0
    assert phrase.interval_days == 1


def test_failure_preserves_ease_factor():
    """Test that quality < 3 does NOT modify ease factor."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=5)
    db.update_review(phrase_id, quality=5)

    ef_before_failure = db.phrases[phrase_id].ease_factor

    db.update_review(phrase_id, quality=2)

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor == ef_before_failure


def test_recovery_after_failure_follows_correct_sequence():
    """Test that after failure, successful reviews follow I(1)→I(2)→I(3)."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)
    db.update_review(phrase_id, quality=3)

    db.update_review(phrase_id, quality=1)
    assert db.phrases[phrase_id].repetition == 0

    db.update_review(phrase_id, quality=3)
    assert db.phrases[phrase_id].interval_days == 1
    assert db.phrases[phrase_id].repetition == 1

    db.update_review(phrase_id, quality=3)
    assert db.phrases[phrase_id].interval_days == 6
    assert db.phrases[phrase_id].repetition == 2


def test_multiple_failures_keep_repetition_at_zero():
    """Test that repeated failures keep repetition at 0."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    for _ in range(5):
        db.update_review(phrase_id, quality=0)
        assert db.phrases[phrase_id].repetition == 0
        assert db.phrases[phrase_id].interval_days == 1


def test_ease_factor_unchanged_for_quality_0():
    """Test that ease factor is preserved for quality 0 (failure)."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=5)
    ef_before = db.phrases[phrase_id].ease_factor

    db.update_review(phrase_id, quality=0)

    phrase = db.phrases[phrase_id]
    assert phrase.ease_factor == ef_before


def test_ease_factor_calculation_for_quality_4():
    """Test ease factor formula for quality 4."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=4)

    phrase = db.phrases[phrase_id]
    expected_ef = 2.5 + (0.1 - 1 * (0.08 + 1 * 0.02))
    assert abs(phrase.ease_factor - expected_ef) < 0.01


def test_ease_factor_calculation_for_quality_5():
    """Test ease factor formula for quality 5."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=5)

    phrase = db.phrases[phrase_id]
    expected_ef = 2.5 + (0.1 - 0 * (0.08 + 0 * 0.02))
    assert abs(phrase.ease_factor - expected_ef) < 0.01


def test_interval_progression_with_varying_ease_factors():
    """Test that different ease factors produce different interval progressions."""
    db_easy = PhrasesDB()
    db_hard = PhrasesDB()

    easy_id, _, _ = db_easy.add_phrase("Easy")
    hard_id, _, _ = db_hard.add_phrase("Hard")

    db_easy.update_review(easy_id, quality=5)
    db_easy.update_review(easy_id, quality=5)

    db_hard.update_review(hard_id, quality=3)
    db_hard.update_review(hard_id, quality=3)

    db_easy.update_review(easy_id, quality=5)
    db_hard.update_review(hard_id, quality=3)

    easy_interval = db_easy.phrases[easy_id].interval_days
    hard_interval = db_hard.phrases[hard_id].interval_days

    assert easy_interval > hard_interval


def test_next_review_date_is_set_correctly():
    """Test that next_review date is calculated from current time."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    before_review = datetime.now()
    db.update_review(phrase_id, quality=3)
    after_review = datetime.now()

    phrase = db.phrases[phrase_id]
    assert phrase.next_review is not None
    next_review = datetime.fromisoformat(phrase.next_review)

    expected_min = before_review + timedelta(days=1)
    expected_max = after_review + timedelta(days=1)

    assert expected_min <= next_review <= expected_max


def test_quality_rating_boundary_at_3():
    """Test that quality 3 is success, quality 2 is failure."""
    db = PhrasesDB()
    phrase_id, _, _ = db.add_phrase("Hallo")

    db.update_review(phrase_id, quality=3)
    assert db.phrases[phrase_id].repetition == 1

    db.update_review(phrase_id, quality=2)
    assert db.phrases[phrase_id].repetition == 0
