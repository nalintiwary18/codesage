from src.graph.state import GraphState
from src.agents.llm.client import create_client
from src.utils.spinner import spinner, print_success


def connect_to_llm(state: GraphState) -> GraphState:
    with spinner("Connecting to LLM..."):
        state['llm'] = create_client(
            state['config'].provider,
            state['config'].model,
            state['config'].api_key
        )
    print_success(f"Connected to {state['config'].provider} ({state['config'].model})")
    return state