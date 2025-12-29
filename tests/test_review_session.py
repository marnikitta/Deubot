"""Tests for ReviewSession state machine."""

import pytest

from deubot.agent import ShowReviewOutput, ShowReviewBatchOutput
from deubot.database import PhrasesDB
from deubot.review_session import ReviewSession
from deubot.translations import ReviewDirection

pytestmark = pytest.mark.unit


def test_start_batch_returns_first_card(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("2", "Zwei", "two", "Two", 1, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("3", "Drei", "three", "Three", 2, ReviewDirection.GERMAN_TO_ENGLISH),
        ]
    )

    first = session.start_batch(batch)

    assert first is not None
    assert first.phrase_id == "1"
    assert first.german == "Eins"
    assert first.explanation == "One"


def test_batch_presentation_order(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("2", "Zwei", "two", "Two", 1, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("3", "Drei", "three", "Three", 2, ReviewDirection.GERMAN_TO_ENGLISH),
        ]
    )

    first = session.start_batch(batch)
    assert first is not None
    assert first.german == "Eins"

    second = session.advance()
    assert second is not None
    assert second.german == "Zwei"

    third = session.advance()
    assert third is not None
    assert third.german == "Drei"

    fourth = session.advance()
    assert fourth is None


def test_empty_batch_returns_none(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(reviews=[])

    first = session.start_batch(batch)

    assert first is None
    assert not session.is_active


def test_is_active_with_current_card(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH)]
    )

    assert not session.is_active

    session.start_batch(batch)
    assert session.is_active

    session.advance()
    assert not session.is_active


def test_is_active_with_pending_cards(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("2", "Zwei", "two", "Two", 1, ReviewDirection.GERMAN_TO_ENGLISH),
        ]
    )

    session.start_batch(batch)
    assert session.is_active
    assert len(session.pending_cards) == 1


def test_record_quality_updates_database(test_db: PhrasesDB):
    test_db.add_phrase("Guten Morgen", "good morning")
    initial_phrase = test_db.get_all_phrases()[0]
    initial_interval = initial_phrase["interval_days"]

    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Guten Morgen", "good morning", "Good morning", 0, ReviewDirection.GERMAN_TO_ENGLISH)
        ]
    )
    session.start_batch(batch)

    result = session.record_quality("1", quality=3)

    assert result is True
    updated_phrase = test_db.get_all_phrases()[0]
    assert updated_phrase["interval_days"] > initial_interval


def test_record_quality_wrong_phrase_id_rejected(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH)]
    )
    session.start_batch(batch)

    result = session.record_quality("999", quality=3)

    assert result is False


def test_record_quality_no_current_card_rejected(test_db: PhrasesDB):
    session = ReviewSession(test_db)

    result = session.record_quality("1", quality=3)

    assert result is False


def test_interrupt_clears_session(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("2", "Zwei", "two", "Two", 1, ReviewDirection.GERMAN_TO_ENGLISH),
        ]
    )
    session.start_batch(batch)
    assert session.is_active

    session.interrupt()

    assert session.current_card is None
    assert session.pending_cards == []
    assert not session.is_active


def test_start_new_batch_replaces_old(test_db: PhrasesDB):
    session = ReviewSession(test_db)
    batch1 = ShowReviewBatchOutput(
        reviews=[
            ShowReviewOutput("1", "Eins", "one", "One", 0, ReviewDirection.GERMAN_TO_ENGLISH),
            ShowReviewOutput("2", "Zwei", "two", "Two", 1, ReviewDirection.GERMAN_TO_ENGLISH),
        ]
    )
    batch2 = ShowReviewBatchOutput(
        reviews=[ShowReviewOutput("3", "Drei", "three", "Three", 2, ReviewDirection.GERMAN_TO_ENGLISH)]
    )

    session.start_batch(batch1)
    assert session.current_card is not None
    assert session.current_card.german == "Eins"

    first = session.start_batch(batch2)
    assert first is not None
    assert first.german == "Drei"
    assert len(session.pending_cards) == 0
