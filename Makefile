.PHONY: venv test lint

venv:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/python -m pytest -v
