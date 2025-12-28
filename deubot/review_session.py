from dataclasses import dataclass

from deubot.agent import ShowReviewBatchOutput
from deubot.database import PhrasesDB


@dataclass
class ReviewCard:
    phrase_id: str
    german: str
    explanation: str


class ReviewSession:
    """Manages the review card presentation state machine."""

    def __init__(self, db: PhrasesDB):
        self.db = db
        self.current_card: ReviewCard | None = None
        self.pending_cards: list[ReviewCard] = []

    @property
    def is_active(self) -> bool:
        return self.current_card is not None or len(self.pending_cards) > 0

    def start_batch(self, batch: ShowReviewBatchOutput) -> ReviewCard | None:
        """Start a batch session, return first card to show."""
        self.pending_cards = [ReviewCard(r.phrase_id, r.german, r.explanation) for r in batch.reviews]
        return self.advance()

    def advance(self) -> ReviewCard | None:
        """Advance to next card, return it or None if done."""
        if self.pending_cards:
            self.current_card = self.pending_cards.pop(0)
            return self.current_card
        self.current_card = None
        return None

    def record_quality(self, phrase_id: str, quality: int) -> bool:
        """Record quality rating. Returns False if phrase_id doesn't match current card."""
        if not self.current_card or self.current_card.phrase_id != phrase_id:
            return False
        self.db.update_review(phrase_id, quality)
        return True

    def interrupt(self) -> None:
        """Clear session when user sends a new message."""
        self.pending_cards = []
        self.current_card = None
