from typing import TypedDict, Any
from src.config.schema import CodesageConfig


class GraphState(TypedDict):
    config: CodesageConfig
    target: str
    files: list
    all_chunks: list
    index:Any
    selected: list
    llm: Any
    understanding:dict[str, Any]
    raw_issues: list
    saved_path: Any
    reviewed: list
    polished: list
    validated: list