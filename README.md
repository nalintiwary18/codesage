I serve as the central landing page. I explain exactly what the `agent-report` does, why it exists, and precisely how to get started using it for any codebase.
# CodeSage — AI-Powered Codebase Analyzer

**CodeSage** is a developer-first CLI tool that analyzes your codebase and generates a structured, line-referenced Markdown report. It uses AI to identify issues, suggest improvements, and provide actionable insights while maintaining transparency through a verification layer that cross-checks findings against your actual source code.

## 🚀 Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```bash
# Analyze the current directory
codesage run

# Analyze a specific directory
codesage run /path/to/your/codebase

# Generate a report with custom settings
codesage run --output report.md --model gpt-4o --max-tokens 4096
```

### Configuration

Create a `.codesage.toml` file in your project root:

```toml
[general]
model = "gpt-4o"
max_tokens = 4096

[analysis]
include_patterns = ["src/**/*.py", "lib/**/*.js"]
exclude_patterns = ["node_modules", "dist", "build"]
```

## 📋 Features

### 🔍 AI-Powered Analysis
- **Code Quality**: Identifies anti-patterns, complexity issues, and maintainability problems
- **Security**: Detects vulnerabilities, insecure patterns, and potential risks
- **Documentation**: Checks for missing docstrings, comments, and type hints
- **Best Practices**: Ensures adherence to language-specific conventions and standards

### 📝 Structured Markdown Reports
- **Line-Referenced Issues**: Every finding includes exact line numbers and code snippets
- **Severity Levels**: Categorizes issues as Critical, Warning, or Info
- **Actionable Recommendations**: Provides concrete steps to resolve issues
- **Contextual Explanations**: AI-generated insights for each finding

### 🛡️ Verification Layer
- **Cross-Checked Findings**: All issues are verified against actual source code
- **False Positive Reduction**: Automated checks to minimize inaccurate reports
- **Transparency**: Clear evidence trail for every finding

### ⚙️ Flexible Configuration
- **TOML Configuration**: Easy-to-use configuration file
- **Pattern Matching**: Include/exclude files using glob patterns
- **Model Selection**: Choose between different AI models
- **Token Management**: Control analysis depth with max tokens

## 🛠️ Development

### Project Structure

```
src/
├── cli/              # CLI command definitions
│   ├── commands/     # Individual command modules
│   └── utils/        # Utility functions
├── core/             # Core analysis logic
│   ├── analyzer.py   # Main analysis engine
│   ├── verifier.py   # Verification layer
│   └── models.py     # Data models
├── services/         # External service integrations
│   └── openai_service.py
├── utils/            # General utilities
└── main.py           # Application entry point
```

### Adding a New Command

1. Create a new command module in `src/cli/commands/`:

```python
# src/cli/commands/new_command.py
import click

@click.command()
def new_command():
    """Description of the new command."""
    click.echo("New command executed!")
```

2. Register the command in `src/main.py`:

```python
# src/main.py
from src.cli.commands.new_command import new_command

cli.add_command(new_command)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## 🚀 Getting Started with CodeSage

### Step 1: Install CodeSage

```bash
pip install -e .
```

### Step 2: Configure Your Project

Create a `.codesage.toml` file in your project root:

```toml
[general]
model = "gpt-4o"
max_tokens = 4096

[analysis]
include_patterns = ["src/**/*.py", "lib/**/*.js"]
exclude_patterns = ["node_modules", "dist", "build"]
```

### Step 3: Run the Analysis

```bash
# Analyze current directory
codesage run

# Analyze specific directory
codesage run /path/to/your/codebase

# Save report to file
codesage run --output report.md
```

### Step 4: Review the Report

Open the generated `report.md` file and review the findings:

```markdown
# CodeSage Analysis Report

## Project Overview
- **Path**: /path/to/codebase
- **Language**: Python
- **Files Analyzed**: 152
- **Issues Found**: 23

## Critical Issues
### [CRITICAL] Hardcoded API Key
**File**: src/api/client.py
**Line**: 45

```python
API_KEY = "sk-proj-1234567890"
```

**Recommendation**: Use environment variables or a secrets manager to store sensitive credentials.

## Warning Issues
### [WARNING] Missing Docstring
**File**: src/utils/helpers.py
**Line**: 12

```python
def calculate_checksum(data: bytes) -> str:
    # Missing docstring
    return hashlib.sha256(data).hexdigest()
```

**Recommendation**: Add a docstring explaining the function's purpose, parameters, and return value.

## Info Issues
### [INFO] Complex Function
**File**: src/core/processor.py
**Line**: 89

```python
def process_data(data: dict) -> dict:
    # Cyclomatic complexity: 18
    # Consider breaking this function into smaller, more manageable functions
    # ...
```

**Recommendation**: Refactor this function to improve readability and maintainability.
```
