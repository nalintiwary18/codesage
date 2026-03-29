from src.graph.state import GraphState
from src.utils.spinner import spinner, print_success, print_info
from src.agents.tasks.detection_agent import run_detection_agent


def detection(state:GraphState)->GraphState:
    with spinner("Detecting issues..."):
        state["raw_issues"] = run_detection_agent(state["llm"],state["selected"],state["understanding"])
        if not state["raw_issues"]:
            print_info("No issues detected — codebase looks clean!")
        else:
            print_success(f"{len(state['raw_issues'])} raw issues detected")
    return state