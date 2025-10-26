host := deubot

run:
	uv run python -m deubot.main

test:
	uv run pytest tests/ -v --tb=short

lint:
	uv run mypy --check-untyped-defs deubot
	uv run black --line-length 120 deubot
	uv run flake8 --ignore E501,W503,E203 deubot

push: lint
	rsync --delete --verbose --archive --compress --rsh=ssh deubot.service deubot pyproject.toml $(host):~/deubot

test-and-push: lint test push

deploy: push
	ssh -T $(host) "systemctl --user daemon-reload && systemctl --user restart deubot.service"
	ssh -T $(host) "journalctl --user-unit=deubot.service --no-pager | tail -n 20"


.PHONY: run test lint push test-and-push deploy


