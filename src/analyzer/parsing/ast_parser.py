"""
Python AST-based code parser.

Walks the AST of a Python source file to extract functions, methods, classes,
and filled-in module-level blocks, each with accurate start and end line numbers.

This is the preferred parser for Python files. The fallback regex parser is used
for all other languages.
"""

import ast
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedBlock:
    """
    Describes one logical unit of code within a source file.
    Used as the intermediate representation between parsing and chunking.
    """
    # "function", "class", "method", or "module_level"
    block_type: str
    # Symbol name — "__module__" for module-level blocks
    name: str
    # First line of the block, 1-indexed (includes decorators)
    start_line: int
    # Last line of the block, 1-indexed
    end_line: int
    # Set on methods to record the enclosing class name
    parent_class: Optional[str] = None
    # Decorator names collected for context
    decorators: list[str] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []


def parse_python_ast(source_code: str, file_path: str = "<unknown>") -> list[ParsedBlock]:
    """
    Parse a Python source string and return a list of ParsedBlock objects.

    Blocks cover:
    - Top-level functions and async functions
    - Classes (the class header, not individual methods)
    - Methods within classes
    - Module-level gaps (imports, globals) of >= 3 lines

    On syntax errors, an empty list is returned and a warning is logged.
    """
    try:
        tree = ast.parse(source_code, filename=file_path, type_comments=True)
    except SyntaxError as e:
        logger.warning(f"AST parse fail: {file_path}: {e}")
        return []

    total_lines = len(source_code.splitlines())

    blocks: list[ParsedBlock] = []
    _extract_blocks_from_body(tree.body, blocks, total_lines, parent_class=None)

    blocks.sort(key=lambda b: b.start_line)

    # Fill in module-level gaps that no function or class covers
    _fill_module_level_gaps(blocks, total_lines)

    return blocks


def _extract_blocks_from_body(
    body: list[ast.stmt],
    blocks: list[ParsedBlock],
    total_lines: int,
    parent_class: Optional[str] = None,
) -> None:
    """
    Recursively collect functions and classes from an AST body list.
    Recurses into class bodies to capture methods with parent_class set.
    """
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            block_type = "method" if parent_class else "function"
            decorators = [_get_decorator_name(d) for d in node.decorator_list]

            # Start from the first decorator line if any, for accurate range
            start_line = (
                node.decorator_list[0].lineno if node.decorator_list else node.lineno
            )

            blocks.append(ParsedBlock(
                block_type=block_type,
                name=node.name,
                start_line=start_line,
                end_line=node.end_lineno or node.lineno,
                parent_class=parent_class,
                decorators=decorators,
            ))

        elif isinstance(node, ast.ClassDef):
            decorators = [_get_decorator_name(d) for d in node.decorator_list]
            start_line = (
                node.decorator_list[0].lineno if node.decorator_list else node.lineno
            )

            blocks.append(ParsedBlock(
                block_type="class",
                name=node.name,
                start_line=start_line,
                end_line=node.end_lineno or node.lineno,
                decorators=decorators,
            ))

            # Recurse into the class body to capture methods
            _extract_blocks_from_body(
                node.body, blocks, total_lines, parent_class=node.name
            )


def _fill_module_level_gaps(blocks: list[ParsedBlock], total_lines: int) -> None:
    """
    Identify line ranges not covered by any top-level function or class
    and insert module_level blocks for them. Gaps smaller than 3 lines are skipped
    to avoid creating chunks for single blank lines or lone imports.
    """
    if total_lines == 0:
        return

    # Collect occupied ranges for top-level symbols only (exclude methods)
    occupied: list[tuple[int, int]] = [
        (b.start_line, b.end_line)
        for b in blocks
        if b.parent_class is None
    ]
    occupied.sort(key=lambda x: x[0])

    module_blocks: list[ParsedBlock] = []
    current_line = 1

    for start, end in occupied:
        if current_line < start and (start - current_line) >= 3:
            module_blocks.append(ParsedBlock(
                block_type="module_level",
                name="__module__",
                start_line=current_line,
                end_line=start - 1,
            ))
        current_line = end + 1

    # Check for trailing module-level code after the last symbol
    if current_line <= total_lines and (total_lines - current_line + 1) >= 3:
        module_blocks.append(ParsedBlock(
            block_type="module_level",
            name="__module__",
            start_line=current_line,
            end_line=total_lines,
        ))

    blocks.extend(module_blocks)
    blocks.sort(key=lambda b: b.start_line)


def _get_decorator_name(decorator: ast.expr) -> str:
    """
    Flatten a decorator AST node to a dotted string.
    @staticmethod → "staticmethod"
    @app.route("/") → "app.route"
    """
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return f"{_get_decorator_name(decorator.value)}.{decorator.attr}"
    elif isinstance(decorator, ast.Call):
        return _get_decorator_name(decorator.func)
    return "<unknown_decorator>"
