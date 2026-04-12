# CodeSage

CodeSage is a Python CLI for AI-assisted codebase analysis. It scans a target repository, chunks and prioritizes source files, runs multi-stage issue detection with LLM providers, validates findings against real file locations, and writes a structured Markdown report.

## Project Overview

CodeSage is designed to produce review output that is:

- Structured: findings are normalized into a consistent issue schema.
- Traceable: issues are tied to chunk IDs and resolved to file/line ranges.
- Filtered: raw LLM output is reviewed, semantically checked, and quality-filtered.
- Reportable: final output is generated as a Markdown report suitable for human review.

The CLI entrypoint is defined in `pyproject.toml` as:

- `codesage = "src.main:cli"`

Primary commands:

- `codesage run` — run analysis and generate a report.
- `codesage init` — create `.codesage.yml` configuration for a project.
- `codesage doctor` — diagnose local environment and dependencies.

## Core Workflow

The analysis flow is orchestrated in `src/graph/builder.py` and follows this sequence:

1. Load files from target directory (`src/analyzer/loader/file_loader.py`)
2. Detect language by extension (`src/analyzer/loader/language_detector.py`)
3. Chunk source files (`src/analyzer/chunking/chunker.py`)
4. Build and score index (`src/analyzer/indexing/code_index.py`, `src/retrieval/selector.py`)
5. Connect to LLM provider (`src/agents/llm/client.py`)
6. Generate codebase understanding (`src/agents/tasks/understanding_agent.py`)
7. Detect issues (`src/agents/tasks/detection_agent.py`)
8. Review and polish issues (`src/agents/tasks/reviewer_agent.py`, `src/agents/tasks/writer_agent.py`)
9. Validate structure and semantics (`src/validation/structural.py`, `src/validation/semantic.py`, `src/validation/scoring.py`)
10. Write Markdown report (`src/report/markdown.py`, `src/storage/filesystem.py`)

## Requirements

- Python 3.11+
- pip

Optional but recommended for development:

- virtualenv or venv
- Ruff
- pytest

## Installation

### Standard installation

```bash
pip install -e .
```

### Development installation

```bash
pip install -e ".[dev]"
```

If you prefer Make targets:

```bash
make install
make dev
```

## Configuration

CodeSage merges configuration from multiple sources in this priority order:

1. CLI flags
2. Environment variables
3. `.codesage.yml`
4. built-in defaults

### Project config file

Run:

```bash
codesage init .
```

This creates `.codesage.yml` in your target directory.

### Environment variables

Provider keys are read from:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`

Optional config environment variables:

- `CODESAGE_PROVIDER`
- `CODESAGE_MODEL`
- `CODESAGE_LOG_LEVEL`

## Usage

### Analyze current directory

```bash
codesage run
```

### Analyze a specific target directory

```bash
codesage run /path/to/project
```

### Skip wizard and set provider/model/output

```bash
codesage run /path/to/project --no-wizard --provider openai --model gpt-4o-mini --output report.md
```

### Increase selected chunk budget

```bash
codesage run /path/to/project --max-chunks 100
```

### Run via module entrypoint

```bash
python -m src.main run .
```

## Command Reference

### `codesage run [TARGET]`

Main analysis command.

Options from `src/cli/options.py`:

- `--provider, -p` (`openai|gemini|anthropic|groq|ollama`)
- `--model, -m`
- `--output, -o`
- `--verbose, -v`
- `--no-cache`
- `--no-wizard`
- `--max-chunks`

### `codesage init [TARGET]`

Creates `.codesage.yml` using an interactive setup flow.

### `codesage doctor`

Checks Python version, key dependencies, provider SDKs, API key presence, and local configuration files.

## Running Tests and Quality Checks

Based on current project files, use:

```bash
make lint
make test
```

Equivalent direct commands:

```bash
ruff check src/ tests/
python -m pytest tests/ -v
```

## Output

By default, reports are written to:

- directory: `./reports`
- filename: `report.md`

If the same report filename already exists, CodeSage writes a timestamped file instead of overwriting.

## Project Structure

Current repository layout:

```text
src/
├── agents/
│   ├── llm/
│   │   ├── client.py
│   │   └── providers/
│   └── tasks/
├── analyzer/
│   ├── chunking/
│   ├── indexing/
│   ├── loader/
│   └── parsing/
├── cli/
│   ├── commands/
│   └── options.py
├── config/
├── core/
├── graph/
│   └── nodes/
├── issues/
├── report/
├── retrieval/
├── storage/
├── utils/
├── validation/
└── main.py

tests/
pyproject.toml
requirements.txt
Makefile
```

## Development Notes

- Logging is configured with Rich in `src/utils/logger.py`.
- Progress/status output is handled in `src/utils/spinner.py`.
- Structural validation resolves issue line numbers through `ChunkMapper` to avoid unverified line references.

## License

MIT (see `LICENSE`).
