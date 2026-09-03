# defines conversation state schema for the graph

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    """
    Defines the structure of the graph's state.
    The 'messages' key uses the add_messages reducer to append new chat history
    rather than overwriting previous turns.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    pending_upload: list[dict] | None