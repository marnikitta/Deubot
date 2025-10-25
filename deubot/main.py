import logging
import os
import sys
from pathlib import Path
from deubot.dotenv import load_dotenv
from deubot.systemd import try_notify_systemd
from deubot.database import PhrasesDB
from deubot.agent import GermanLearningAgent
from deubot.bot import DeuBot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    load_dotenv(Path(".env"))

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_user_id_str = os.getenv("ALLOWED_USER_ID")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
    db_path = os.getenv("PHRASES_DB_PATH", "./data/phrases.json")

    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not allowed_user_id_str:
        logger.error("ALLOWED_USER_ID not set in .env")
        sys.exit(1)

    if not openai_api_key:
        logger.error("OPENAI_API_KEY not set in .env")
        sys.exit(1)

    try:
        allowed_user_id = int(allowed_user_id_str)
    except ValueError:
        logger.error("ALLOWED_USER_ID must be a valid integer")
        sys.exit(1)

    logger.info("Initializing DeuBot...")
    db = PhrasesDB(db_path)
    agent = GermanLearningAgent(api_key=openai_api_key, model=openai_model, db=db)
    bot = DeuBot(token=telegram_token, allowed_user_id=allowed_user_id, agent=agent)

    try_notify_systemd()
    logger.info("DeuBot is running...")
    bot.run()


if __name__ == "__main__":
    main()
