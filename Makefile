.PHONY: venv test

venv:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/python -m pytest -v
