# DeuBot

**Primary goal**: Explore capabilities and limitations of coding with AI coding assistants (Claude Code, Cursor, etc.) rather than build production-ready software.

*This README was written by an AI coding assistant.*

## What It Is

A German learning Telegram bot with spaced repetition. Built iteratively with Claude Code to test agent-driven development workflows. The bot itself is an AI agent (OpenAI) that uses tool calling for translation, phrase storage, and spaced repetition reviews—showing buttons in Telegram UI through tools, not hardcoded commands.

## Design

**Agent architecture**: OpenAI integration with structured tool calling. Tools have elaborate descriptions following Claude Code's documentation philosophy (see [Decoding Claude Code](https://minusx.ai/blog/decoding-claude-code/)). Agent returns typed outputs using dataclasses, not magic strings.

**Spaced repetition**: SM-2 algorithm with JSON persistence. Quality ratings (1-5) adjust ease factors and intervals for optimal review scheduling.

**Deployment**: Systemd service with Type=notify protocol for proper startup signaling. Deployed via rsync to remote host.

**Stack**: Python 3.13, `uv` for dependencies, Telegram Bot API, OpenAI GPT.

## Testing & Development

Integrated into development cycle:
- **Linting**: mypy, black (120 chars), flake8
- **LLM tests**: Validate tool usage patterns and agent behavior probabilistically (semantic correctness, not exact matches)
- **Logic tests**: SM-2 algorithm correctness
- **End-to-end tests**: Resilient to LLM non-determinism

```bash
make lint   # Run all linters
make run    # Run locally
make deploy # Deploy to remote systemd service
```

## Structure

`deubot/agent.py` - AI agent with tool calling
`deubot/tools.py` - Tool definitions with detailed documentation
`deubot/bot.py` - Telegram handler
`deubot/database.py` - SM-2 spaced repetition storage
`deubot/systemd.py` - Type=notify service integration

Configuration via `.env` file (see `.env.example`).
