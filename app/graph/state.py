from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class State(TypedDict):
    """
    Defines the structure of the graph's state.
    The 'messages' key uses the add_messages reducer to append new chat history
    rather than overwriting previous turns.
    """
    messages: Annotated[list[BaseMessage], add_messages]