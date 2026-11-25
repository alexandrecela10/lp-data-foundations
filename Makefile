# Trust Pack (trust_pack/). Offline, no key, no network. Synthetic data. Not investment advice.
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
RUN = PYTHONPATH=src $(PY) -m trustpack.cli

.PHONY: setup ingest eval replay page demo test

setup:
	uv venv --python 3.11 .venv && uv pip install -e ".[dev]"

ingest:
	$(RUN) ingest

eval:
	$(RUN) eval

replay:
	$(RUN) replay $(ID)

page:
	$(RUN) page

demo: ingest eval page
	@echo "Open trust_pack/site/index.html"

test:
	PYTHONPATH=src $(PY) -m pytest -q
