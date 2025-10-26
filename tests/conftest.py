"""Pytest configuration and shared fixtures."""

import os
from pathlib import Path
from typing import Generator

import pytest

from deubot.database import PhrasesDB
from deubot.agent import GermanLearningAgent
from deubot.dotenv import load_dotenv


@pytest.fixture(scope="session")
def openai_credentials() -> dict[str, str]:
    """Load OpenAI credentials from .env file."""
    load_dotenv(Path(".env"))

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5")

    if not api_key:
        pytest.skip("OPENAI_API_KEY not set in .env")

    return {"api_key": api_key, "model": model}


@pytest.fixture
def test_db(tmp_path: Path) -> Generator[PhrasesDB, None, None]:
    """Create a temporary test database."""
    db_path = tmp_path / "test_phrases.json"
    db = PhrasesDB(str(db_path))
    yield db


@pytest.fixture
def agent(openai_credentials: dict[str, str], test_db: PhrasesDB) -> GermanLearningAgent:
    """Create a test agent with temporary database."""
    return GermanLearningAgent(
        api_key=openai_credentials["api_key"],
        model=openai_credentials["model"],
        db=test_db,
        enable_logs=True,
    )


@pytest.fixture
def agent_no_logs(openai_credentials: dict[str, str], test_db: PhrasesDB) -> GermanLearningAgent:
    """Create a test agent without logging."""
    return GermanLearningAgent(
        api_key=openai_credentials["api_key"],
        model=openai_credentials["model"],
        db=test_db,
        enable_logs=False,
    )
