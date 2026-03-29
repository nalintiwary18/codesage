from src.graph.state import GraphState
from src.utils.spinner import spinner, print_success

from src.agents.tasks.understanding_agent import run_understanding_agent


def understand(state:GraphState)->GraphState:
    with spinner("Understanding codebase..."):
        state['understanding'] = run_understanding_agent(state['llm'],state['selected'])
    print_success("Codebase understanding generated")
    return state