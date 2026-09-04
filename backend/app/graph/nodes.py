# LLM processing logic

import os

from app.graph.state import State
from app.tools.mcp_tools import get_mcp_tools
from langchain_google_genai import ChatGoogleGenerativeAI

_model_with_tools = None
# this global variable will hold the tool-bound model instance, which is built once and reused across invocations.


async def _get_model():
    """
    Builds the tool-bound model once and reuses it across invocations,
    since get_mcp_tools() is now cached and the tool list is stable
    for the lifetime of the app process.
    """
    global _model_with_tools
    if _model_with_tools is None:
        tools = await get_mcp_tools()
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        _model_with_tools = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.7,
            google_api_key=api_key,
        ).bind_tools(tools)
    return _model_with_tools


async def chatbot_node(state: State) -> dict:
    """
    - core chatbot / router node
    - takes the current message history from the state,
    - invokes the LLM, and returns the new response wrapped in a dictionary
      matching the State schema.
    - the LLM itself decides (via tool_calls on the returned message) whether
      to route to the tools node or finish with a final answer.
    """

    model = await _get_model()

    # extract the current message history from the state
    messages = state["messages"]

    response = await model.ainvoke(messages)

    # return the response
    # since the state uses the add_messages reducer,
    # returning this list will automatically append the AI's message to the history
    return {"messages": [response]}