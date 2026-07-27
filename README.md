# LangGraph MCP Chatbot

A production-style chatbot backend built with **FastAPI + LangGraph**, using **PostgreSQL** for durable conversation state (checkpointing) and **MCP-style tools** for external actions. Responses stream back to the client token-by-token over Server-Sent Events (SSE).

```
[User] → [Chatbot UI] → [FastAPI /chat/stream] → [LangGraph Engine] ⇄ [PostgreSQL Checkpointer]
                                                        ↓
                                                  [Router / LLM Node] → [Tools Node] → back to Router
                                                        ↓
                                              [SSE token stream] → [UI]
```

## 1. Folder Structure

```
chatbot-langGraph-main/
├── app/
│   ├── main.py                     # FastAPI app entrypoint + lifespan (DB pool, checkpointer setup)
│   ├── controllers/
│   │   └── chat_controller.py      # Business logic: builds graph, streams tokens via SSE
│   ├── routes/
│   │   └── chat_routes.py          # HTTP route: POST /chat/stream
│   ├── middleware/
│   │   └── logging_middleware.py   # Request timing/logging middleware
│   ├── graph/
│   │   ├── state.py                # Graph State schema (messages + reducer)
│   │   ├── nodes.py                # Chatbot/router node (LLM + tool binding)
│   │   └── builder.py              # Builds & compiles the LangGraph StateGraph
│   ├── tools/
│   │   └── mcp_tools.py            # MCP-style tool definitions exposed to the LLM
│   └── persistence/
│       └── db.py                   # Postgres connection pool + checkpointer factory
├── tests/
│   └── test_graph.py                # Graph tests (stub)
├── Dockerfile                       # API service image
├── docker-compose.yml                # API + Postgres services
├── requirements.txt
├── .env.example
└── README.md
```

## 2. How Things Are Connected

1. **Client → API**: The UI sends `POST /chat/stream` with `{ message, thread_id }`.
2. **Route → Controller**: `chat_routes.py` delegates to `chat_controller.handle_chat_stream`, which owns all graph logic.
3. **Controller → Persistence**: The controller asks `db.py` for a checkpointer (`AsyncPostgresSaver`) built on the shared connection pool opened once at app startup.
4. **Controller → Graph**: `builder.py` compiles a `StateGraph` bound to that checkpointer, keyed by `thread_id`, so each conversation's history loads/saves automatically.
5. **Graph execution**:
   - `chatbot` node (in `nodes.py`) invokes the LLM (tools bound via `.bind_tools`).
   - `tools_condition` inspects the LLM's response: if it contains tool calls → route to the `tools` node (`ToolNode` running functions from `mcp_tools.py`); otherwise → `END`.
   - After a tool runs, the graph loops back to `chatbot` so the LLM can use the tool result to form a final answer (or call another tool).
6. **Graph → Client**: The controller streams the LLM's output using `stream_mode="messages"`, forwarding each token as an SSE `data:` event, terminated by `data: [DONE]`.
7. **Persistence**: On every step, LangGraph writes state to Postgres via the checkpointer, so the same `thread_id` resumes with full history on the next request.

## 3. What Each File Does

| File | Responsibility |
|---|---|
| `app/main.py` | Creates the FastAPI app, opens/closes the Postgres pool, runs checkpointer `.setup()` on startup, registers middleware and routes. |
| `app/routes/chat_routes.py` | Defines `POST /chat/stream` and the request schema (`message`, `thread_id`). |
| `app/controllers/chat_controller.py` | Core orchestration: builds the graph per-request, invokes `.astream(...)`, yields SSE chunks. |
| `app/middleware/logging_middleware.py` | Logs method, path, status, and duration for every request. |
| `app/graph/state.py` | Defines the `State` TypedDict (`messages`, using the `add_messages` reducer so history appends instead of overwriting). |
| `app/graph/nodes.py` | The `chatbot_node` — invokes `ChatOpenAI` (with tools bound) on the current message history. |
| `app/graph/builder.py` | Wires up the graph: `START → chatbot`, conditional edge to `tools` or `END`, and `tools → chatbot` loop. Compiles with/without a checkpointer. |
| `app/tools/mcp_tools.py` | Tool functions exposed to the LLM (stubbed here — swap for real MCP client calls). |
| `app/persistence/db.py` | Owns the `AsyncConnectionPool` and exposes `get_checkpointer()`. |
| `tests/test_graph.py` | Placeholder for graph/unit tests. |
| `Dockerfile` / `docker-compose.yml` | Containerize the API + spin up a local Postgres instance. |

## 4. How to Run the Project

### Option A — Docker (recommended)
```bash
cp .env.example .env
# fill in OPENAI_API_KEY in .env
docker compose up --build
```
API available at `http://localhost:8000`.

### Option B — Local
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in OPENAI_API_KEY, and point DATABASE_URL at a running Postgres instance

uvicorn app.main:app --reload
```

### Try it
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my project status?", "thread_id": "demo-1"}'
```
Reusing the same `thread_id` continues the same conversation (state loaded from Postgres).

## 5. Project Description

This project is a backend template for building **stateful, tool-using chatbots** on top of LangGraph. Instead of holding conversation memory in-process (which breaks on restarts/multiple workers), it persists every turn to PostgreSQL via LangGraph's checkpointer, so conversations survive restarts and scale across multiple API instances. The LLM node can autonomously decide to call external tools (MCP-style) mid-conversation, loop back with results, and produce a final answer — all streamed to the client token-by-token over SSE for a responsive chat UI.

## 6. Notes / Possible Next Steps

- **Auth**: no authentication/session validation currently exists — add an auth middleware or dependency (e.g. JWT/session cookie check) before trusting `thread_id`, otherwise any client can read/write any thread's history.
- **Real MCP integration**: `mcp_tools.py` currently has stub tools. Swap in `langchain-mcp-adapters` (or your MCP server's client) to call real MCP tools.
- **Graph caching**: the graph is rebuilt on every request; since it's cheap and stateless besides the checkpointer, this is fine, but you could cache the compiled graph at app startup if you want to shave off overhead.
- **Error handling**: `chat_controller.py` currently swallows exceptions into an SSE error event — consider structured error codes for the frontend.
- **Testing**: `tests/test_graph.py` is currently empty — add tests that exercise the tool-calling branch with a mocked LLM.