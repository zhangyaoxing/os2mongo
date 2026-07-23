.PHONY: venv test lint reinstall

venv:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

reinstall:
	.venv/bin/pip install -e ".[dev]" --force-reinstall --no-cache-dir

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/python -m pytest -v
