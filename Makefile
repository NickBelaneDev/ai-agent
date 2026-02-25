.PHONY: help install quality fix test complexity security doc

PYTHON ?= python3
PIP ?= pip3
SRC ?= src

help:
	@echo "Available targets:"
	@echo "  install      Install runtime + quality dependencies"
	@echo "  quality      Run ruff, black --check and mypy"
	@echo "  fix          Auto-fix code style with ruff + black"
	@echo "  complexity   Run xenon complexity checks"
	@echo "  security     Run bandit and pip-audit"
	@echo "  doc          Run interrogate docstring coverage"
	@echo "  test         Run pytest"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install black ruff mypy xenon pip-audit bandit interrogate

quality:
	ruff check .
	black --check .
	mypy $(SRC)

fix:
	ruff check . --fix
	black .

complexity:
	xenon --max-absolute B --max-modules B --max-average A $(SRC)

security:
	bandit -r $(SRC)
	pip-audit --progress-spinner off

doc:
	interrogate -v $(SRC)

test:
	pytest -q
