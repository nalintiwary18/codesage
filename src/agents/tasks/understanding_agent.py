"""
Understanding agent — builds a high-level mental model of the codebase.

Sends selected chunks to the LLM and receives a structured JSON description of:
architecture patterns, key files, dependency relationships, and tech stack.
This context is passed downstream to the detection agent to improve accuracy.

Returns an empty fallback dict on any parse failure — the pipeline continues.
"""

import json
from typing import Any, Optional

from src.agents.llm.client import LLMProvider
from src.core.chunk import CodeChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)

UNDERSTANDING_SYSTEM_PROMPT = """You are a senior software architect analyzing a codebase.
Your task is to understand the codebase structure and patterns.

Analyze the provided code chunks and produce a JSON response with:
1. "architecture": A brief description of the overall architecture
2. "patterns": List of design patterns observed
3. "key_files": List of important file paths
4. "dependencies": Map of file dependencies (file → list of imports/dependencies)
5. "tech_stack": Technologies and frameworks used
6. "concerns": Any immediate concerns or observations

IMPORTANT:
- Only analyze the code provided
- Do not make assumptions about code you haven't seen
- Be specific and reference actual code elements
- Respond ONLY with valid JSON, no markdown formatting"""


def build_understanding_prompt(chunks: list[CodeChunk]) -> str:
    """Format chunks into a numbered prompt for the understanding agent."""
    parts = ["Here are the code chunks from the codebase:\n"]

    for i, chunk in enumerate(chunks, 1):
        parts.append(f"--- CHUNK {i} ---")
        parts.append(f"File: {chunk.file_path}")
        parts.append(f"Lines: {chunk.start_line}-{chunk.end_line}")
        parts.append(f"Type: {chunk.chunk_type or 'unknown'}")
        if chunk.symbol_name:
            parts.append(f"Symbol: {chunk.symbol_name}")
        parts.append(f"Language: {chunk.language or 'unknown'}")
        parts.append(f"\n{chunk.content}\n")

    parts.append("---")
    parts.append("\nAnalyze the above code and provide your understanding as JSON.")
    return "\n".join(parts)


def run_understanding_agent(
    llm: LLMProvider,
    chunks: list[CodeChunk],
) -> dict[str, Any]:
    """
    Invoke the LLM to produce a structured understanding of the supplied chunks.
    On parse failure, returns a minimal fallback dict so the pipeline can continue.
    """
    if not chunks:
        logger.warning("No chunks provided to understanding agent")
        return {"architecture": "No code provided", "patterns": [], "key_files": []}

    prompt = build_understanding_prompt(chunks)
    logger.info(f"Generating codebase understanding from {len(chunks)} chunks...")
    raw = llm.generate(prompt, system_prompt=UNDERSTANDING_SYSTEM_PROMPT)

    return _parse_json_response(raw, fallback={"architecture": raw[:500], "patterns": []})


def _parse_json_response(raw: str, fallback: dict) -> dict[str, Any]:
    """
    Extract and parse a JSON object from the LLM response.
    Strips markdown fences if present. Returns fallback on any error.
    """
    cleaned = _strip_markdown_fences(raw.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Understanding agent response could not be parsed as JSON — using fallback")
        return fallback


def _strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing triple-backtick fences from an LLM response."""
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    body: list[str] = []
    inside = False
    for line in lines:
        if line.strip().startswith("```") and not inside:
            inside = True
            continue
        if line.strip() == "```" and inside:
            break
        if inside:
            body.append(line)
    return "\n".join(body)
