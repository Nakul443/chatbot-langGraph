import os
from langchain_openai import ChatOpenAI
from app.graph.state import State


model = ChatOpenAI(model="gpt-4o", temperature=0.7)

async def chatbot_node(state: State) -> dict:
    """
    - core chatbot node
    - takes the current message history from the state,
    - invokes the LLM, and returns the new response wrapped in a dictionary 
    - matching the State schema.
    """
    
    # extract the current message history from the state
    messages = state["messages"]

    response = await model.ainvoke(messages)
    
    # return the response
    # since the state uses the add_messages reducer,
    # returning this list will automatically append the AI's message to the history
    return {"messages": [response]}