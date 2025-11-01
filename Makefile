host := deubot
deploy_files := .python-version deubot.service deubot pyproject.toml uv.lock Makefile
package := deubot
remote_path := ~/deubot
service_name := deubot.service

run:
	uv run python -m $(package).main

test:
	uv run pytest tests/ -n 20 -v --tb=short

lint:
	uv run mypy --check-untyped-defs $(package) tests
	uv run black --line-length 120 $(package) tests
	uv run flake8 --ignore E501,W503,E203 $(package) tests

push: lint
	ssh $(host) "mkdir -p $(remote_path)"
	rsync --delete --verbose --archive --compress --rsh=ssh $(deploy_files) $(host):$(remote_path)

install:
	mkdir -p ~/.config/systemd/user
	ln -sf $(remote_path)/$(service_name) ~/.config/systemd/user/$(service_name)
	systemctl --user daemon-reload
	systemctl --user enable $(service_name)

deploy: push
	ssh -T $(host) "systemctl --user daemon-reload && systemctl --user restart $(service_name)"
	ssh -T $(host) "journalctl --user-unit=$(service_name) --no-pager | tail -n 20"

remote-stop:
	ssh -T $(host) "systemctl --user stop $(service_name)"
	ssh -T $(host) "systemctl --user status $(service_name) --no-pager || true"


.PHONY: run test lint push install deploy remote-stop


