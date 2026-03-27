# Mein shortcut commands deta hoon — developers ko lamba command yaad nahi rakhna padega

.PHONY: install dev test lint run doctor clean

# Project install karo production mode mein
install:
	pip install -e .

# Dev dependencies ke saath install karo
dev:
	pip install -e ".[dev]"

# Saare tests run karo
test:
	python -m pytest tests/ -v

# Code quality check karo ruff se
lint:
	ruff check src/ tests/

# Lint fix bhi karo automatically
fix:
	ruff check src/ tests/ --fix

# CodeSage run karo current directory pe
run:
	python -m src.main run .

# Doctor command — environment check karo
doctor:
	python -m src.main doctor

# Cache aur generated reports saaf karo
clean:
	rm -rf .codesage_cache/
	rm -rf reports/
	find . -type d -name __pycache__ -exec rm -rf {} +
