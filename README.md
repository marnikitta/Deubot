# DeuBot

**Primary goal**: Explore capabilities and limitations of coding with AI coding assistants (Claude Code, Cursor, etc.) rather than build production-ready software.

*This README was written by an AI coding assistant.*

![DeuBot Demo](demo.png)

## What It Is

A German learning Telegram bot with spaced repetition. Built iteratively with Claude Code to test agent-driven development workflows. The bot itself is an AI agent (OpenAI) that uses tool calling for translation, phrase storage, and spaced repetition reviews—showing buttons in Telegram UI through tools, not hardcoded commands.

## Architecture

**Agent loop**: OpenAI tool-calling agent that iterates up to 10x per user message. Each tool returns `needs_llm_followup` to signal whether the agent should continue reasoning. Typed outputs (`MessageOutput`, `ShowReviewBatchOutput`, `TypingOutput`, `LogOutput`, `ToolCallResult`) instead of magic strings.

**Dual-model strategy**: Main model (`OPENAI_MODEL`, default `gpt-4o`) for the agent, light model (`OPENAI_LIGHT_MODEL`, default `gpt-4o-mini`) for translation card generation.

**Translation cards**: Type-specific templates (NOUN/VERB/CHUNK/PREPOSITION/SENTENCE) with 4-5 example sentences varying grammar cases (accusative, dative, Perfekt) and "See also" sections linking related words. Cards are generated via parallel LLM calls (ThreadPoolExecutor, 50 workers) with in-memory caching.

**Spaced repetition**: SM-2 algorithm with gzip-compressed JSON persistence. Quality ratings (1-4: Again, Hard, Good, Easy) adjust ease factors and intervals. Duplicate detection uses trigram similarity with 85% threshold and article normalization.

**Review workflow**:
1. User requests review → Agent calls `start_review` tool
2. `PhrasesDB.get_due_phrases()` fetches phrases due for review
3. Translation cards generated via parallel LLM calls
4. Bot displays card with "Reveal" button → Shows translation + 4 quality rating buttons
5. User rates → SM-2 data updated → Next card until batch complete

**Deployment**: Systemd user service with Type=notify protocol (`sd_notify` via NOTIFY_SOCKET). Deployed via rsync to remote host.

**Design reference**: For principles of good agent design and tool calling patterns, see [Decoding Claude Code](https://minusx.ai/blog/decoding-claude-code/).

## Project Structure

```
deubot/
├── main.py              # Entry point — wires PhrasesDB → GermanLearningAgent → DeuBot
├── agent.py             # Agentic loop with OpenAI tool calling
├── tools.py             # Tool definitions with detailed descriptions and examples
├── translations.py      # Translation card generation with type-specific templates
├── review_session.py    # Review session state machine
├── bot.py               # Telegram handler with callback queries for reviews
├── bot_helpers.py       # UI formatting utilities
├── message.py           # UserMessage dataclass for multimodal input (text + JPEG)
├── database.py          # SM-2 spaced repetition storage with duplicate detection
├── system_prompt.md     # Agent system prompt
├── dotenv.py            # Custom .env file parser
└── systemd.py           # Type=notify service integration
```

## Development

**Stack**: Python 3.13+, `uv` for dependencies, Telegram Bot API, OpenAI GPT.

```bash
make run          # Run locally
make lint         # Run all linters (mypy, black, flake8)
make test-unit    # Fast unit tests (< 1 second)
make test-llm     # LLM integration tests (slow, parallel with -n 20)
make test         # All tests in parallel
make push         # Lint + unit tests + rsync to remote
make deploy       # Push + restart systemd service
```

**Tests** use pytest markers:
- `@pytest.mark.unit` — Fast tests for SM-2, database, similarity detection. No API calls. Target: <1 second.
- `@pytest.mark.llm` — Integration tests with actual OpenAI API. 30-50s per test, run with `-n 20`.

LLM tests validate behavior patterns and semantic correctness, not exact string matches.

## Configuration

Via `.env` file (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token | — |
| `ALLOWED_USER_ID` | Authorized user ID | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | Main agent model | `gpt-4o` |
| `OPENAI_LIGHT_MODEL` | Translation card model | `gpt-4o-mini` |
| `PHRASES_DB_PATH` | Database file location | `./data/phrases.json.gz` |
