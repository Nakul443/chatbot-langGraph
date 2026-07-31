# file to build and compile the entire graph

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from app.graph.state import State
from app.graph.nodes import chatbot_node
from app.tools.mcp_tools import get_mcp_tools


def _add_nodes_and_edges(workflow: StateGraph) -> StateGraph:
    # Nodes
    workflow.add_node("chatbot", chatbot_node)
    
    # Since MCP tools are loaded dynamically at runtime via async, 
    # we initialize the ToolNode with an empty list here, and handle tool execution dynamically.
    workflow.add_node("tools", ToolNode(tools=[]))  # MCP Tool node

    # Entry point
    workflow.add_edge(START, "chatbot")

    # Router: if the last AI message has tool_calls -> "tools", else -> END
    workflow.add_conditional_edges(
        "chatbot",
        tools_condition,
        {"tools": "tools", END: END},
    )

    # After running a tool, loop back to the chatbot so it can use the result
    # to produce the final answer (or call another tool)
    workflow.add_edge("tools", "chatbot")

    return workflow


def build_graph():
    """
    Constructs the chatbot graph with MCP tool-calling support.
    Flow: START -> chatbot -> (tools -> chatbot)* -> END
    """
    workflow = StateGraph(State)
    workflow = _add_nodes_and_edges(workflow)

    # compile the graph without a checkpointer initially
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
    workflow = _add_nodes_and_edges(workflow)

    # Compile the graph with the checkpointer enabled
    return workflow.compile(checkpointer=checkpointer)