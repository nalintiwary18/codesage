from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from src.graph.edges import after_load_code, after_chunked, after_detection
from src.graph.state import GraphState
from src.graph.nodes.llm_setup import connect_to_llm
from src.graph.nodes.parser import load_code, chunked, index
from src.graph.nodes.understanding import understand
from src.graph.nodes.detection import detection
from src.graph.nodes.reviewer import review_issues
from src.graph.nodes.writer import polish, validate, report


def build_graph() -> CompiledStateGraph:
    g = StateGraph(GraphState)
    g.add_node("connect_to_llm", connect_to_llm)
    g.add_node("load_code", load_code)
    g.add_node("chunked", chunked)
    g.add_node("index", index)
    g.add_node("understand", understand)
    g.add_node("detection", detection)
    g.add_node("review_issues", review_issues)
    g.add_node("polish", polish)
    g.add_node("validate", validate)
    g.add_node("report", report)

    g.set_entry_point("load_code")
    g.add_conditional_edges("load_code", after_load_code, {
        "chunked": "chunked",
        "end": END,
    })
    g.add_conditional_edges("chunked", after_chunked, {
        "index": "index",
        "end": END,
    })
    g.add_edge("index", "connect_to_llm")
    g.add_edge("connect_to_llm", "understand")
    g.add_edge("understand", "detection")
    g.add_conditional_edges("detection", after_detection, {
        "review_issues": "review_issues",
        "end": END,
    })
    g.add_edge("review_issues", "polish")
    g.add_edge("polish", "validate")
    g.add_edge("validate", "report")
    g.add_edge("report", END)
    return g.compile()
