#!/usr/bin/env python3
"""Test script to debug phrase saving issue."""

import os
import sys
from pathlib import Path
from deubot.dotenv import load_dotenv
from deubot.database import PhrasesDB
from deubot.agent import GermanLearningAgent

def main():
    load_dotenv(Path(".env"))

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    # Use a temporary test database
    test_db_path = "./data/test_phrases.json"

    print("=" * 60)
    print("TEST: Phrase Saving with 'How to say weather?'")
    print("=" * 60)

    # Create agent with logging enabled
    db = PhrasesDB(test_db_path)
    agent = GermanLearningAgent(
        api_key=openai_api_key,
        model=openai_model,
        db=db,
        enable_logs=True
    )

    # Initial phrase count
    initial_count = len(db.get_all_phrases())
    print(f"\nInitial phrase count: {initial_count}")

    # Test message
    test_message = "How to say weather?"
    print(f"\nTest message: '{test_message}'")
    print("\n" + "-" * 60)
    print("Agent output:")
    print("-" * 60)

    # Process the message and collect outputs
    outputs = list(agent.process_message(test_message))

    for output in outputs:
        print(f"\n[{type(output).__name__}]")
        if hasattr(output, 'message'):
            print(output.message)
        else:
            print(output)

    print("\n" + "-" * 60)

    # Check final phrase count
    final_count = len(db.get_all_phrases())
    print(f"\nFinal phrase count: {final_count}")
    print(f"Phrases added: {final_count - initial_count}")

    # Show all phrases
    all_phrases = db.get_all_phrases()
    if all_phrases:
        print("\nAll phrases in database:")
        for phrase in all_phrases:
            print(f"  - ID={phrase['id']}: {phrase['german']}")
    else:
        print("\nNo phrases in database!")

    print("\n" + "=" * 60)
    if final_count > initial_count:
        print("✓ SUCCESS: Phrase was saved!")
    else:
        print("✗ FAILURE: Phrase was NOT saved!")
    print("=" * 60)

if __name__ == "__main__":
    main()
