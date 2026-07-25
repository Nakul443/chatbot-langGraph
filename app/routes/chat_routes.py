from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.controllers.chat_controller import handle_chat_stream

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    thread_id: str

# POST: /chat/stream
@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    HTTP route endpoint for streaming chat responses.
    Delegates business logic and graph execution to the chat controller.
    """
    return await handle_chat_stream(request.message, request.thread_id)