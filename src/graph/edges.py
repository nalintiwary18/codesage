from src.graph.state import GraphState

def after_load_code(state: GraphState) -> str:
    if not state.get("files"):
        return "end"
    return "chunked"
def after_chunked(state: GraphState) -> str:
    if not state.get("all_chunks"):
        return "end"
    return "index"
def after_detection(state: GraphState) -> str:
    if not state.get("raw_issues"):
        return "end"
    return "review_issues"


