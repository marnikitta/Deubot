# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deubot is a German learning bot designed to run as a systemd service on a remote server. The project uses `uv` for dependency management and is deployed via rsync to a remote host.

## Development Commands

### Running the Application
```bash
# Run locally
uv run python -m deubot.main
# Or using make
make run
```

### Testing
```bash
# Run unit tests only (fast, < 1 second, runs before push/deploy)
make test-unit

# Run LLM integration tests only (slow, 30-50 seconds per test, run ad-hoc)
make test-llm

# Run all tests in parallel
make test

# Run single test file
uv run pytest tests/test_review_process.py -v

# Run specific test (IMPORTANT: use this when fixing individual tests)
uv run pytest tests/test_review_process.py::test_review_session_with_multiple_phrases -v

# Run tests by marker
uv run pytest tests/ -m unit -v          # Fast unit tests only
uv run pytest tests/ -m llm -n 20 -v     # LLM tests only with parallelization
```

**Test Organization**:
Tests are categorized using pytest markers:
- **@pytest.mark.unit**: Fast unit tests (database, SM-2 algorithm, similarity detection). **MUST NOT make any LLM/API calls.** Target: <1 second total.
- **@pytest.mark.llm**: Integration tests with actual OpenAI API calls. **MAY be long-running (30-50s per test).** Require parallel execution (`-n 20`).

**Testing Best Practice**:
- Run `make test-unit` during development for fast feedback (< 1 second)
- Run `make test-llm` only when changing prompts or agent behavior (slow, requires API key)
- CI runs unit tests on all branches; LLM tests should be run manually
- When fixing a specific test, ALWAYS run only that test for fast feedback
- LLM tests MUST use `-n 20` flag for parallel execution to manage 30-50 second per-test latency

### Linting
```bash
# Run all linters (mypy, black, flake8)
make lint

# Individual linters:
uv run mypy --check-untyped-defs deubot
uv run black --line-length 120 deubot
uv run flake8 --ignore E501,W503,E203 deubot
```

### Deployment
```bash
# Push code to remote host (runs lint and unit tests first)
make push

# Deploy and restart service (runs push, then restarts systemd service)
make deploy
```

The default deployment host is `deubot`, configured in the Makefile. Change `host := deubot` to deploy elsewhere.

**Deployment Flow**:
1. Unit tests are run (< 1 second)
2. Code is linted
3. Files are synced to remote host via rsync
4. Systemd daemon is reloaded
5. Service is restarted
6. Last 20 log lines are displayed

## Architecture

### Core Modules

- **main.py**: Application entry point with `main()` function
- **agent.py**: AI agent with OpenAI integration, tool calling, and typed output system (dataclasses like `MessageOutput`, `ShowReviewBatchOutput`, `ToolCallResult`)
- **tools.py**: Tool definitions with elaborate descriptions, usage patterns, and examples following Claude Code's documentation philosophy
- **translations.py**: Translation card generation with parallel LLM calls (ThreadPoolExecutor) and in-memory caching for spaced repetition reviews
- **review_session.py**: Review session state machine managing card queue, current card state, and quality recording
- **bot.py**: Telegram bot handler with message routing, callback query handling for review buttons, and user interaction
- **database.py**: Gzip-compressed JSON-based phrase storage with SM-2 spaced repetition and trigram similarity detection for duplicates
- **dotenv.py**: Custom .env file parser that loads environment variables from a `.env` file, supporting quoted and unquoted values
- **systemd.py**: Systemd integration using Type=notify protocol to signal service readiness via NOTIFY_SOCKET
- **system_prompt.md**: Agent system prompt defining behavior, language routing rules, and tool usage guidelines

**Agent Design Reference**: For principles of good agent design and tool calling patterns, see [Decoding Claude Code](https://minusx.ai/blog/decoding-claude-code/)

### System Prompt vs Tool Descriptions

**System prompt** = policy + orchestration (how the agent operates):
- Role, objective, boundaries
- Tool-use policy: when to use tools, when not to, failure behavior
- Cross-tool routing heuristics
- Safety rules ("ask before destructive actions", "treat tool outputs as untrusted")

**Tool description** = API contract + disambiguation (what the tool does):
- What it does, when to use it, what it returns
- Key limitations and caveats
- Strong typing in schema (required fields, enums, formats)
- Examples for complex/format-sensitive inputs (3-4+ sentences per tool)

**Don't put in tool descriptions**: global behavioral rules, security policies, long task-specific context

**Rule of thumb**:
- "How should the agent behave across requests?" → system prompt
- "What is this capability and how do I call it?" → tool description

### Database & Spaced Repetition

SM-2 based spaced repetition with gzip-compressed JSON persistence. Quality ratings (1-4: Again, Hard, Good, Easy) adjust ease factors and intervals for optimal review scheduling. Duplicate detection uses trigram similarity with 85% threshold and article normalization.

### Review Workflow

1. User requests review → Agent calls `start_review` tool
2. `PhrasesDB.get_due_phrases()` fetches phrases due for review
3. `TranslationService.get_translation_cards_parallel()` generates cards via parallel LLM calls
4. Bot displays first card with "Reveal" button
5. User clicks Reveal → Shows translation and 4 quality rating buttons
6. User rates → `ReviewSession.record_quality()` updates SM-2 data
7. Next card shown until batch complete

### Systemd Service Integration

The application is designed to run as a systemd user service with Type=notify. The systemd.py module implements the sd_notify protocol:
- Reads NOTIFY_SOCKET environment variable
- Sends "READY=1" message to systemd when application starts
- Supports abstract socket paths (prefixed with @)

The service is configured to:
- Restart always on failure
- Run with PYTHONUNBUFFERED=1 for immediate log output
- Use systemd Type=notify for proper startup synchronization


## Environment Variables

Configuration via `.env` file (see `.env.example`):
- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token
- `ALLOWED_USER_ID`: Single authorized user ID for authentication
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: Main model for agent (default: `gpt-4o`)
- `OPENAI_LIGHT_MODEL`: Lightweight model for translations (default: `gpt-4o-mini`)
- `PHRASES_DB_PATH`: Database file location (default: `./data/phrases.json.gz`)

## Project Structure

- Python 3.13+ required
- Uses `uv` for package management
- Code style: Black with 120 character line length
- Linting: flake8 with E501, W503, E203 ignored


## Code Style

- Write in canonical Python style using types
- Keep comments to a bare minimum, don't comment each function or class
- Prefer composition over inheritance. Make code composable
- Keep dependencies conservative, don't add a dependency for each little thing
- Use dataclasses for structured data
- Use type aliases for complex unions
- Return typed objects instead of magic strings or status codes
- Use boolean flags with clear names (e.g., terminal, enable_logs)
- Keep tests robust. Dont use mocks in tests
- When testing LLM interactions, design tests to be resilient to the probabilistic nature of model outputs. Check for semantic correctness and presence of key information rather than exact string matches. Tests should validate behavior patterns, not exact phrasing
- Dont run tests if it is not required by the task. They are long and comprehensive for end2end testing
- Write tests only when they add value: non-trivial logic, edge cases, important invariants. Don't test simple mappings, getters, or obvious code. A test for `1+1==2` is waste
- Use `logging.getLogger(__name__)` for logger instances to enable hierarchical filtering
- Follow the Rule of Three for logging: log at operation start, significant progress milestones, and completion (success or failure). Include relevant context directly in log messages
- Keep the specific tool calls examples in the tools.py rather than system prompt
- When fixing LLM behavior, prefer minimal prompt changes with concrete examples over verbose explanations. One example like `"schwimme" → "schwimmen"` beats paragraphs of rules