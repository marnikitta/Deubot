#!/usr/bin/env python3
"""Comprehensive test suite for phrase saving behavior."""

import os
import sys
from pathlib import Path
from deubot.dotenv import load_dotenv
from deubot.database import PhrasesDB
from deubot.agent import GermanLearningAgent

# Test cases covering various translation scenarios
TEST_CASES = [
    # English to German - "How to say" format
    "How to say umbrella?",
    "How to say good morning?",
    "How do I say thank you?",
    "How would I say I love you?",
    "What's the German word for car?",

    # German to English - "Was bedeutet" format
    "Was bedeutet Regenschirm?",
    "Was bedeutet Entschuldigung?",
    "What does Krankenhaus mean?",
    "What is Flughafen?",

    # Direct German phrases
    "Guten Abend",
    "Wie geht es dir?",
    "Ich möchte ein Bier",

    # Questions about German
    "Translate 'the book' to German",
    "Give me the German for 'beautiful'",

    # Should NOT save (grammar questions)
    "What is the dative case?",
    "Explain German word order",
    "What's the difference between der, die, das?",
]


def run_single_test(agent: GermanLearningAgent, db: PhrasesDB, test_message: str, test_num: int) -> dict:
    """Run a single test and return results."""
    print(f"\n{'='*70}")
    print(f"TEST {test_num}: {test_message}")
    print('='*70)

    initial_count = len(db.get_all_phrases())

    # Process the message
    outputs = list(agent.process_message(test_message))

    # Analyze outputs
    has_function_call = False
    has_save_phrase = False
    response_types = []
    tool_calls = []

    for output in outputs:
        output_type = type(output).__name__
        if output_type == "LogOutput":
            msg = output.message
            print(f"[LOG] {msg}")

            # Check if this is the response types log
            if "Response types:" in msg:
                response_types = msg.split("Response types: ")[1]

            # Check if this is a tool call log
            if "Tool call: save_phrase" in msg:
                has_save_phrase = True
                tool_calls.append(msg)
        elif output_type == "MessageOutput":
            # Check if it's the "Saved" confirmation
            if "✓ Saved:" in output.message:
                print(f"[CONFIRMATION] {output.message}")
            else:
                print(f"[RESPONSE] {output.message[:100]}...")

    final_count = len(db.get_all_phrases())
    phrases_added = final_count - initial_count

    result = {
        "test_message": test_message,
        "response_types": response_types,
        "has_function_call": "function_call" in response_types if response_types else False,
        "has_save_phrase": has_save_phrase,
        "phrases_added": phrases_added,
        "success": phrases_added > 0
    }

    print(f"\nRESULT:")
    print(f"  Response types: {response_types}")
    print(f"  Had function_call: {result['has_function_call']}")
    print(f"  Called save_phrase: {result['has_save_phrase']}")
    print(f"  Phrases added: {phrases_added}")
    print(f"  Status: {'✓ SAVED' if result['success'] else '✗ NOT SAVED'}")

    return result


def main():
    load_dotenv(Path(".env"))

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    # Use a temporary test database
    test_db_path = "./data/test_comprehensive.json"

    # Remove old test database
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()

    print("=" * 70)
    print("COMPREHENSIVE PHRASE SAVING TEST SUITE")
    print("=" * 70)
    print(f"Total test cases: {len(TEST_CASES)}")
    print(f"Database: {test_db_path}")

    # Create agent with logging enabled
    db = PhrasesDB(test_db_path)
    agent = GermanLearningAgent(
        api_key=openai_api_key,
        model=openai_model,
        db=db,
        enable_logs=True
    )

    results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        result = run_single_test(agent, db, test_case, i)
        results.append(result)

        # Clear history between tests to avoid context pollution
        agent.clear_history()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    saved_count = sum(1 for r in results if r["success"])
    not_saved_count = len(results) - saved_count

    print(f"\nTotal tests: {len(results)}")
    print(f"Saved: {saved_count}")
    print(f"Not saved: {not_saved_count}")

    print("\n" + "-" * 70)
    print("TESTS THAT SAVED:")
    print("-" * 70)
    for r in results:
        if r["success"]:
            print(f"  ✓ {r['test_message']}")

    print("\n" + "-" * 70)
    print("TESTS THAT DID NOT SAVE:")
    print("-" * 70)
    for r in results:
        if not r["success"]:
            print(f"  ✗ {r['test_message']}")
            print(f"     Response types: {r['response_types']}")

    print("\n" + "=" * 70)
    print(f"Final database count: {len(db.get_all_phrases())} phrases")
    print("=" * 70)


if __name__ == "__main__":
    main()
