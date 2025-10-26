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
# Push code to remote host (runs lint first)
make push

# Deploy and restart service (runs push, then restarts systemd service)
make deploy
```

The default deployment host is `deubot`, configured in the Makefile. Change `host := deubot` to deploy elsewhere.

## Architecture

### Core Modules

- **main.py**: Application entry point with `main()` function
- **agent.py**: AI agent with OpenAI integration, tool calling, and typed output system
- **bot.py**: Telegram bot handler with message routing and user interaction
- **database.py**: JSON-based phrase storage with spaced repetition (SM-2 algorithm)
- **dotenv.py**: Custom .env file parser that loads environment variables from a `.env` file, supporting quoted and unquoted values
- **systemd.py**: Systemd integration using Type=notify protocol to signal service readiness via NOTIFY_SOCKET

### Database & Spaced Repetition

SM-2 based spaced repetition with JSON persistence. Quality ratings adjust ease factors and intervals for optimal review scheduling.

### Systemd Service Integration

The application is designed to run as a systemd user service with Type=notify. The systemd.py module implements the sd_notify protocol:
- Reads NOTIFY_SOCKET environment variable
- Sends "READY=1" message to systemd when application starts
- Supports abstract socket paths (prefixed with @)

The service is configured to:
- Restart always on failure
- Run with PYTHONUNBUFFERED=1 for immediate log output
- Use systemd Type=notify for proper startup synchronization

### Deployment Flow

1. Code is linted locally
2. Files (deubot.service, deubot/, pyproject.toml) are synced to remote host via rsync
3. Systemd daemon is reloaded
4. Service is restarted
5. Last 20 log lines are displayed

## Project Structure

- Python 3.13+ required
- Uses `uv` for package management (not poetry, despite Makefile comment)
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
- Dont run tests if it is not required by the task. They are long and comprehensive for end2end testing
- Use `logging.getLogger(__name__)` for logger instances to enable hierarchical filtering
- Follow the Rule of Three for logging: log at operation start, significant progress milestones, and completion (success or failure). Add context with `extra` parameter when needed