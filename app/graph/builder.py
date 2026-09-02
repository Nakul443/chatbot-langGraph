# file to build and compile the entire graph

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.nodes import chatbot_node
from app.graph.state import State
from app.tools.mcp_tools import get_mcp_tools


async def _add_nodes_and_edges(workflow: StateGraph) -> StateGraph:
    # Fetch the real MCP tools (cached after first call, see mcp_tools.py) so
    # the ToolNode actually has tools to execute. Previously this was
    # ToolNode(tools=[]), so any tool_call the LLM made could never resolve.
    tools = await get_mcp_tools()

    # Nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", ToolNode(tools=tools))  # MCP Tool node (steps 6-8)

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