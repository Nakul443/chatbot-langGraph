# a custom node that mimics the behavior of LangGraph's prebuilt ToolNode, but specifically lets us:

# Read any tool calls on the last message in state["messages"].
# For search_general or ingest_pdf, inject user_id into the tool call's arguments.
# For ingest_pdf, also inject file_base64 and filename from state["pending_upload"] (and after executing, reset pending_upload to None in the returned state dict so it doesn't linger).
# Call the underlying MCP client tools.
# Format the tool execution outputs as ToolMessages.

# It intercepts each tool call before execution and
# injects user_id (and file content, for ingest_pdf) from graph state —
# since the LLM can't be trusted to supply those itself.

from typing import Any

from langchain_core.messages import ToolMessage

from app.graph.state import State
from app.tools.mcp_tools import get_mcp_tools


async def custom_tool_executor(state: State) -> dict[str, Any]:
    """
    Custom tool executor node that acts like LangGraph's ToolNode,
    but performs parameter injection for user-scoped or file-ingestion tools.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    if not tool_calls:
        return {}

    # Get the cached tools from our MCP client
    tools = await get_mcp_tools()
    # Create a map of tool name to tool object for easy invocation
    tool_map = {tool.name: tool for tool in tools}

    tool_outputs = []
    # Track if ingest_pdf was called so we can clear pending_upload
    ingest_called = False

    for tool_call in tool_calls:
        name = tool_call["name"]
        args = dict(tool_call["args"])  # copy to avoid mutating original state in-place
        tool_id = tool_call["id"]

        # 1. Inject user_id if needed
        if name in ("search_general", "ingest_pdf"):
            args["user_id"] = state.get("user_id")

        # 2. Inject pending file uploads for ingest_pdf
        if name == "ingest_pdf":
            ingest_called = True
            pending = state.get("pending_upload")  # list of dicts
            if pending:
                requested_filename = args.get("filename")
                matched_file = None
                
                if requested_filename:
                    # 1. Exact match
                    matched_file = next((f for f in pending if f.get("filename") == requested_filename), None)
                    
                    # 2. Case-insensitive match
                    if not matched_file:
                        matched_file = next((f for f in pending if f.get("filename", "").lower() == requested_filename.lower()), None)
                        
                    # 3. Substring match
                    if not matched_file:
                        matched_file = next((f for f in pending if requested_filename.lower() in f.get("filename", "").lower() or f.get("filename", "").lower() in requested_filename.lower()), None)

                # 4. Fallback to the first/only file if there's only one pending upload and no specific filename was requested
                if not matched_file and len(pending) == 1 and not requested_filename:
                    matched_file = pending[0]
                    
                if matched_file:
                    args["file_base64"] = matched_file.get("content_b64")
                    # Ensure we use the exact filename from the uploaded file
                    args["filename"] = matched_file.get("filename")
                else:
                    available_files = ", ".join(f"'{f.get('filename')}'" for f in pending)
                    tool_outputs.append(
                        ToolMessage(
                            content=f"Error: Could not find a pending upload matching the filename '{requested_filename}'. Available uploads: {available_files}.",
                            name=name,
                            tool_call_id=tool_id,
                        )
                    )
                    continue
            else:
                # If the LLM tries to call ingest_pdf but there is no file uploaded,
                # return an error output so the LLM can explain it to the user.
                tool_outputs.append(
                    ToolMessage(
                        content="Error: No pending PDF file found to ingest. Please upload a file first.",
                        name=name,
                        tool_call_id=tool_id,
                    )
                )
                continue

        # 3. Execute the tool
        if name in tool_map:
            try:
                tool_obj = tool_map[name]
                result = await tool_obj.ainvoke(args)
                
                # result is usually a ToolMessage, or a string, or contains content.
                # We want to extract the content for our ToolMessage.
                content = getattr(result, "content", str(result))
                
                tool_outputs.append(
                    ToolMessage(
                        content=content,
                        name=name,
                        tool_call_id=tool_id,
                    )
                )
            except Exception as e:
                tool_outputs.append(
                    ToolMessage(
                        content=f"Error executing tool {name}: {e!s}",
                        name=name,
                        tool_call_id=tool_id,
                    )
                )
        else:
            tool_outputs.append(
                ToolMessage(
                    content=f"Error: Tool '{name}' not found.",
                    name=name,
                    tool_call_id=tool_id,
                )
            )

    # Compile the state updates
    state_update: dict[str, Any] = {"messages": tool_outputs}
    if ingest_called:
        # Clear the pending upload once we have processed/called the ingestion
        state_update["pending_upload"] = None

    return state_update
