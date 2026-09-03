# file to build and compile the entire graph

from app.graph.nodes import chatbot_node
from app.graph.state import State
from app.graph.tool_executor import custom_tool_executor
from app.tools.mcp_tools import get_mcp_tools
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition


async def _add_nodes_and_edges(workflow: StateGraph) -> StateGraph:
    # Warm up the real MCP tools cache (cached after first call, see mcp_tools.py)
    await get_mcp_tools()

    # Nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", custom_tool_executor)  # Custom parameter-injecting tool executor node (steps 6-8)

    # Entry point
    workflow.add_edge(START, "chatbot")

    # Router: if the last AI message has tool_calls -> "tools", else -> END (step 9)
    workflow.add_conditional_edges(
        "chatbot",
        tools_condition,
        {
            "tools": "tools",
            END: END
        },
    )

    # After running a tool, loop back to the chatbot so it can use the result
    # to produce the final answer (or call another tool)
    workflow.add_edge("tools", "chatbot")

    return workflow


async def build_graph():
    """
    Constructs the chatbot graph with MCP tool-calling support.
    Flow: START -> chatbot -> (tools -> chatbot)* -> END
    """
    workflow = StateGraph(State)
    workflow = await _add_nodes_and_edges(workflow)

    # compile the graph without a checkpointer initially
    # the structural workflow is compiled here, but state persistence is not yet enabled
    return workflow.compile()


async def build_graph_with_checkpointer(checkpointer):
    """
    Constructs and compiles the graph, binding it to the provided PostgreSQL checkpointer.
    This ensures state persistence across conversation threads.
    """
    workflow = StateGraph(State)
    workflow = await _add_nodes_and_edges(workflow)

    # Compile the graph with the checkpointer enabled
    return workflow.compile(checkpointer=checkpointer)