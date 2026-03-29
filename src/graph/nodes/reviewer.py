from src.graph.state import GraphState
from src.agents.tasks.reviewer_agent import run_reviewer_agent
from src.utils.spinner import spinner, print_success


def review_issues(state:GraphState)->GraphState:
    with spinner("Reviewing issues..."):
        state['reviewed'] = run_reviewer_agent( state["llm"], state["raw_issues"] )
        print_success(f"{len(state['reviewed'])} issues after review")
    return state
