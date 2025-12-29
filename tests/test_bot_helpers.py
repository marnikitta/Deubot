import pytest

from deubot.bot_helpers import parse_callback_data, CallbackData

pytestmark = pytest.mark.unit


class TestParseCallbackData:
    """Test callback parsing - the only non-trivial logic extracted from bot.py."""

    def test_reveal(self):
        result = parse_callback_data("reveal_123")
        assert result == CallbackData(action="reveal", phrase_id="123", quality=None)

    def test_quality(self):
        result = parse_callback_data("quality_123_4")
        assert result == CallbackData(action="quality", phrase_id="123", quality=4)

    def test_invalid_returns_none(self):
        assert parse_callback_data("") is None
        assert parse_callback_data("unknown_123") is None
        assert parse_callback_data("quality_123_abc") is None
        assert parse_callback_data("quality_123") is None
