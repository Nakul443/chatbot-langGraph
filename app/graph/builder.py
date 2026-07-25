# file to build and compile the entire graph

from langgraph.graph import StateGraph, START, END
from app.graph.state import State
from app.graph.nodes import chatbot_node

def build_graph():
    """
    constructs the basic workflow graph for the chatbot
    Flow: START -> chatbot_node -> END
    """
    # 1. Initialize the StateGraph with the State schema
    workflow = StateGraph(State)

    # 2. Add the chatbot node to the graph
    workflow.add_node("chatbot", chatbot_node)

    # 3. Define the entry and exit edges
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    # 4. compile the graph without a checkpointer initially
    # the structural workflow is compiled here, but state persistence is not yet enabled
    # when the app is initialized,
    # the Postgres checkpointer will be attached to the compiled graph for state persistence across conversation threads
    return workflow.compile()

async def build_graph_with_checkpointer(checkpointer):
    """
    Constructs and compiles the graph, binding it to the provided PostgreSQL checkpointer.
    This ensures state persistence across conversation threads.
    """
    workflow = StateGraph(State)

    # Add nodes and edges
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    # Compile the graph with the checkpointer enabled
    return workflow.compile(checkpointer=checkpointer)