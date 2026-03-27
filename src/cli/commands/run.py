"""
`codesage run` command — executes the full analysis pipeline.

The 10-step pipeline:
  1. Load files (respecting .gitignore and binary/size exclusions)
  2. Chunk code (AST for Python, regex for others; large blocks split)
  3. Build index and select top-N chunks by importance score
  4. Connect to LLM provider
  5. Generate codebase understanding (context for detection)
  6. Detect issues (chunk_id + relative lines only)
  7. Review/filter detected issues (false-positive removal)
  8. Polish issue text (descriptions and fixes)
  9. Structural + semantic validation (resolve lines, reject hallucinations)
  10. Generate and save Markdown report

Wizard questions are presented before the pipeline when --no-wizard is not set.
"""

import click
import questionary
from pathlib import Path

from src.cli.options import common_options
from src.config.defaults import PROVIDER_MODELS, SUPPORTED_LANGUAGES
from src.config.loader import load_config
from src.config.schema import CodesageConfig
from src.utils.logger import setup_logger, get_logger
from src.utils.spinner import spinner, print_success, print_error, print_header, print_info


@click.command("run")
@click.argument("target", default=".", type=click.Path(exists=True))
@common_options
def run_command(
    target: str,
    provider: str | None,
    model: str | None,
    output: str | None,
    verbose: bool,
    no_cache: bool,
    no_wizard: bool,
    max_chunks: int | None,
) -> None:
    """
    Analyze a codebase and write a Markdown report.
    TARGET is the path to the project directory (defaults to current directory).
    """
    setup_logger("DEBUG" if verbose else "INFO")

    print_header("Welcome to CodeSage!")

    # Collect CLI overrides — omit None values so defaults are not overwritten
    cli_overrides: dict = {k: v for k, v in {
        "provider": provider,
        "model": model,
        "output_filename": output,
        "cache_enabled": False if no_cache else None,
        "max_chunks": max_chunks,
        "no_wizard": no_wizard or False,
    }.items() if v is not None}

    config = load_config(target_path=target, cli_overrides=cli_overrides)

    if not config.no_wizard:
        wizard_answers = _run_wizard(config)
        config = load_config(target_path=target, cli_overrides={**cli_overrides, **wizard_answers})

    try:
        _execute_pipeline(config, target)
    except Exception as e:
        print_error(f"Analysis failed: {e}")
        get_logger(__name__).exception("Pipeline error")
        raise click.Abort()


def _run_wizard(config: CodesageConfig) -> dict:
    """
    Prompt the user for configuration choices interactively.
    Raises click.Abort if the user presses Ctrl+C at any prompt.
    """
    print_info("Quick setup — answer a few questions to get started.\n")
    answers: dict = {}

    language = questionary.select(
        "Which language is your codebase?",
        choices=SUPPORTED_LANGUAGES,
        default="Python",
    ).ask()
    if language is None:
        raise click.Abort()
    answers["language"] = language.lower().split("/")[0].strip()

    provider = questionary.select(
        "Which LLM provider?",
        choices=[
            questionary.Choice("OpenAI", value="openai"),
            questionary.Choice("Gemini", value="gemini"),
            questionary.Choice("Anthropic", value="anthropic"),
            questionary.Choice("Groq", value="groq"),
            questionary.Choice("Ollama (local)", value="ollama"),
        ],
        default="openai",
    ).ask()
    if provider is None:
        raise click.Abort()
    answers["provider"] = provider

    if provider != "ollama":
        api_key = questionary.password("Enter your API key:").ask()
        if api_key is None:
            raise click.Abort()
        if api_key.strip():
            answers["api_key"] = api_key.strip()

    available_models = PROVIDER_MODELS.get(provider, ["default"])
    model = questionary.select(
        "Select model:",
        choices=[*available_models, "custom"],
        default=available_models[0],
    ).ask()
    if model is None:
        raise click.Abort()
    if model == "custom":
        model = questionary.text("Enter custom model name:").ask()
        if model is None:
            raise click.Abort()
    answers["model"] = model

    output_name = questionary.text("Output file name?", default="report.md").ask()
    if output_name is None:
        raise click.Abort()
    answers["output_filename"] = output_name.strip()

    print()
    print_success("Setup complete! Starting analysis...")
    print()

    return answers


def _execute_pipeline(config: CodesageConfig, target: str) -> None:
    """Run the 10-step analysis pipeline in sequence."""
    logger = get_logger(__name__)

    # Step 1 — load files
    with spinner("Loading files..."):
        from src.analyzer.loader.file_loader import FileLoader
        from src.analyzer.loader.language_detector import detect_language

        loader = FileLoader(target)
        files = loader.load_all_files()
        for f in files:
            f.language = detect_language(f.relative_path)

    print_success(f"{len(files)} files loaded")

    if not files:
        print_error("No analyzable files found. Check the target path.")
        return

    # Step 2 — chunk
    with spinner("Chunking code..."):
        from src.analyzer.chunking.chunker import Chunker
        all_chunks = Chunker(max_chunk_lines=config.max_chunks).chunk_all_files(files)

    print_success(f"{len(all_chunks)} chunks created")

    if not all_chunks:
        print_error("No chunks produced from the loaded files.")
        return

    # Step 3 — index and select
    with spinner("Selecting important chunks..."):
        from src.analyzer.indexing.code_index import CodeIndex
        from src.retrieval.selector import ChunkSelector

        index = CodeIndex()
        index.add_chunks(all_chunks)
        selected = ChunkSelector(max_chunks=config.max_chunks).select(index)

    print_success(f"{len(selected)} chunks selected for analysis")

    # Step 4 — connect to LLM
    with spinner("Connecting to LLM..."):
        from src.agents.llm.client import create_client
        llm = create_client(config.provider, config.model, config.api_key)

    print_success(f"Connected to {config.provider} ({config.model})")

    # Step 5 — understand
    with spinner("Understanding codebase..."):
        from src.agents.tasks.understanding_agent import run_understanding_agent
        understanding = run_understanding_agent(llm, selected)

    print_success("Codebase understanding generated")

    # Step 6 — detect
    with spinner("Detecting issues..."):
        from src.agents.tasks.detection_agent import run_detection_agent
        raw_issues = run_detection_agent(llm, selected, understanding)

    print_success(f"{len(raw_issues)} raw issues detected")

    if not raw_issues:
        print_info("No issues detected — codebase looks clean!")
        return

    # Step 7 — review
    with spinner("Reviewing issues..."):
        from src.agents.tasks.reviewer_agent import run_reviewer_agent
        reviewed = run_reviewer_agent(llm, raw_issues)

    print_success(f"{len(reviewed)} issues after review")

    # Step 8 — polish
    with spinner("Polishing findings..."):
        from src.agents.tasks.writer_agent import run_writer_agent
        polished = run_writer_agent(llm, reviewed)

    # Step 9 — validate
    with spinner("Validating issues..."):
        from src.core.mapping import ChunkMapper
        from src.validation.structural import StructuralValidator
        from src.validation.semantic import validate_all_semantic
        from src.validation.scoring import apply_quality_scores, filter_by_quality
        from src.issues.scorer import score_all_issues
        from src.issues.scoring import filter_by_confidence

        mapper = ChunkMapper(all_chunks)
        validated = StructuralValidator(mapper, target).validate_all(polished)
        validated = validate_all_semantic(validated)
        validated = score_all_issues(validated)
        validated = apply_quality_scores(validated)
        validated = filter_by_quality(validated)
        validated = filter_by_confidence(validated, config.min_confidence)

    print_success(f"{len(validated)} issues after validation")

    if not validated:
        print_info("All issues were filtered out during validation — no real issues found.")
        return

    # Step 10 — report
    with spinner("Generating report..."):
        from src.report.markdown import MarkdownReportGenerator
        from src.storage.filesystem import ReportStorage

        project_name = Path(target).resolve().name
        report = MarkdownReportGenerator(project_name=project_name).generate(validated)
        saved_path = ReportStorage(config.output_dir).save_report(
            report, filename=config.output_filename
        )

    print()
    print_success(f"Report saved: {saved_path}")
    print_info(f"Total issues: {len(validated)}")
