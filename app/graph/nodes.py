# LLM processing logic

from langchain_openai import ChatOpenAI
from app.graph.state import State
from app.tools.mcp_tools import tools

# Bind tools so the model can decide to call them
model = ChatOpenAI(model="gpt-4o", temperature=0.7).bind_tools(tools)


async def chatbot_node(state: State) -> dict:
    """
    - core chatbot / router node
    - takes the current message history from the state,
    - invokes the LLM, and returns the new response wrapped in a dictionary
      matching the State schema.
    - the LLM itself decides (via tool_calls on the returned message) whether
      to route to the tools node or finish with a final answer.
    """

    # extract the current message history from the state
    messages = state["messages"]

    response = await model.ainvoke(messages)

    # return the response
    # since the state uses the add_messages reducer,
    # returning this list will automatically append the AI's message to the history
    return {"messages": [response]}