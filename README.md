# LangGraph MCP Chatbot

A production-style chatbot backend built with **FastAPI + LangGraph**, using **PostgreSQL** for durable conversation state (checkpointing), **JWT authentication**, and **MCP tools** for external actions — including a directly connected legal/general RAG pipeline and web search. Responses stream back to the client token-by-token over Server-Sent Events (SSE).

```
[User] → [Chatbot UI] → JWT-authenticated FastAPI (/chat/stream, /chat/upload)
                                    │
                          AuthMiddleware validates JWT → attaches user_id
                                    │
                          [LangGraph Engine] ⇄ [PostgreSQL Checkpointer]
                                    │
                          [chatbot node: LLM + tool_calls decision]
                                    │
                         tool_calls? ──No──► END (stream final answer)
                                    │Yes
                    [custom_tool_executor node]
                     - injects user_id into search_general / ingest_pdf
                     - injects pending_upload file content into ingest_pdf
                     - dispatches to whichever MCP server owns the tool
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                      ▼
     own MCP server (:8002)   RAG repo's MCP server (:8003)
     - web_search              - search_legal_rag
                                - search_general (user-scoped)
                                - ingest_pdf (user-scoped)
                                    │
                          loop back to chatbot node
                                    │
                        [SSE token stream] → [UI]
```

## 1. Folder Structure

```
chatbot-langGraph-main/
├── app/
│   ├── main.py                       # FastAPI entrypoint: DB pool, checkpointer setup, middleware, routers
│   ├── auth/
│   │   ├── schemas.py                 # Pydantic request/response models for signup/login
│   │   └── security.py                # Password hashing + JWT encode/decode helpers
│   ├── controllers/
│   │   ├── auth_controller.py         # Signup/login business logic
│   │   └── chat_controller.py         # Streams chat turns AND handles PDF upload → graph runs
│   ├── routes/
│   │   ├── auth_routes.py             # POST /auth/signup, /auth/login
│   │   └── chat_routes.py             # POST /chat/stream, POST /chat/upload
│   ├── middleware/
│   │   ├── auth_middleware.py         # JWT verification; attaches request.state.user_id
│   │   └── logging_middleware.py      # Request timing/logging
│   ├── graph/
│   │   ├── state.py                   # State: messages, user_id, pending_upload
│   │   ├── nodes.py                   # chatbot_node — LLM call with tools bound
│   │   ├── tool_executor.py           # Custom tool-dispatch node (param injection)
│   │   └── builder.py                 # Wires START → chatbot → (tools → chatbot)* → END
│   ├── tools/
│   │   ├── mcp_tools.py               # Connects to BOTH MCP servers, caches discovered tools
│   │   └── server.py                  # This repo's own FastMCP server — exposes web_search
│   └── persistence/
│       └── db.py                      # Postgres connection pool + checkpointer factory + users table
├── tests/
│   └── test_graph.py
├── Dockerfile
├── docker-compose.yml                 # api + mcp-server + postgres
├── requirements.txt
├── .env.example
└── README.md
```

## 2. How Things Are Connected

1. **Client → API**: UI sends `POST /chat/stream` `{message, thread_id}` or `POST /chat/upload` (multipart: file + thread_id), both with `Authorization: Bearer <jwt>`.
2. **AuthMiddleware**: Every path except `/health`, `/docs`, `/openapi.json`, `/redoc`, `/auth/signup`, `/auth/login` requires a valid JWT. On success it decodes the token and attaches `request.state.user_id` from the `sub` claim; on failure it returns 401 before the route handler even runs.
3. **Route → Controller**: `chat_routes.py` reads `user_id` off `request.state` and delegates to `chat_controller.handle_chat_stream` or `handle_chat_upload`.
4. **Thread scoping**: the controller prefixes `thread_id` with `user_id` (`f"{user_id}:{thread_id}"`) before handing it to the checkpointer, so one user can never read or resume another user's conversation by guessing/reusing a `thread_id`.
5. **Controller → Graph**: `builder.py` compiles a `StateGraph` bound to the checkpointer. Initial state includes `messages`, `user_id`, and (for uploads) `pending_upload: list[{filename, content_b64}]`.
6. **Graph execution**:
   - `chatbot` node invokes the LLM with all discovered MCP tools bound.
   - `tools_condition` routes to `custom_tool_executor` if the LLM produced tool calls, else to `END`.
   - `custom_tool_executor` (NOT the prebuilt `ToolNode`) reads each tool call and, for `search_general`/`ingest_pdf`, overwrites/injects `user_id` from state — and for `ingest_pdf`, matches the requested filename to inject the corresponding `file_base64`/`filename` from `state["pending_upload"]`. This exists because the LLM should never be trusted to supply a user's own ID, and should never have to carry raw base64 file bytes through its own reasoning context.
   - Every other tool call (`search_legal_rag`, `web_search`) executes unmodified.
   - After execution, the graph loops back to `chatbot` so the LLM can use the tool result to produce a final answer or call another tool. `pending_upload` is cleared back to `None` once `ingest_pdf` has run.
7. **Graph → Client**: the controller streams tokens from the `chatbot` node only (filtered by `metadata["langgraph_node"] == "chatbot"`) as SSE `data:` events, ending with `data: [DONE]`.
8. **Persistence**: every step is checkpointed to Postgres, so a `thread_id` resumes with full history on the next request.

## 3. MCP Servers — Two, Not One

This repo connects to **two separate MCP servers** simultaneously via `MultiServerMCPClient` in `mcp_tools.py`:

| Server | Where it runs | Tools exposed | Auth |
|---|---|---|---|
| `project_server` | This repo's own `app/tools/server.py`, port `8002` | `web_search` | `MCP_AUTH_TOKEN` |
| `legal_rag_server` | The separate RAG pipeline repo's `mcp_server.py`, port `8003` | `search_legal_rag`, `search_general`, `ingest_pdf` | `LEGAL_RAG_AUTH_TOKEN` |

Tools are auto-discovered from both on startup and cached for the process lifetime — the LLM sees all four tools as one flat list and decides which to call per turn. There is **no** HTTP-wrapper tool in this repo anymore (the earlier `search_rag` tool that made a plain REST call to `RAG_SERVICE_URL` has been removed in favor of connecting to the RAG repo's native MCP server directly).

**Docker networking note:** if both repos run in separate `docker-compose.yml` projects, `LEGAL_RAG_MCP_URL` cannot be `http://localhost:8003/mcp` from inside this repo's `api` container — `localhost` there means the container itself. Point it at `http://host.docker.internal:8003/mcp` (with `extra_hosts: ["host.docker.internal:host-gateway"]` added on Linux), or join both compose projects to a shared external Docker network and use the RAG repo's service name instead.

## 4. PDF Upload Flow

`POST /chat/upload` (multipart form: `files`, `thread_id`) lets a user upload multiple PDFs mid-conversation:

1. `handle_chat_upload` reads the files, base64-encodes them, and starts a graph run with `pending_upload` set in state as a list and a synthetic user message ("I've uploaded the following file(s): `<filenames>` — please index them.") so the LLM has a clear reason to call `ingest_pdf`.
2. `custom_tool_executor` automatically matches the LLM's requested filename and fills in `file_base64`, `filename`, and `user_id` on the `ingest_pdf` call — the LLM only decides *that* ingestion is needed, never handles the bytes itself.
3. Once indexed, later turns in the same or a different thread can call `search_general`, which is scoped to that `user_id` — one user's uploaded files are never visible to another user's queries.

## 5. What Each File Does

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, Postgres pool lifecycle, checkpointer + users-table setup, registers `AuthMiddleware`/`RequestLoggingMiddleware` and both routers. |
| `app/auth/security.py` | Password hashing (signup/login) and JWT encode/decode. |
| `app/middleware/auth_middleware.py` | Verifies `Authorization: Bearer <jwt>` on every non-public path; attaches `request.state.user_id`. |
| `app/routes/chat_routes.py` | `POST /chat/stream` and `POST /chat/upload`; pulls `user_id` from `request.state` (set by auth middleware). |
| `app/controllers/chat_controller.py` | Builds the graph per-request, scopes `thread_id` to `user_id`, streams SSE tokens; `handle_chat_upload` additionally base64-encodes the file and seeds `pending_upload`. |
| `app/graph/state.py` | `State` TypedDict: `messages` (with `add_messages` reducer), `user_id`, `pending_upload`. |
| `app/graph/nodes.py` | `chatbot_node` — invokes `ChatOpenAI` with all MCP tools bound via `.bind_tools`. |
| `app/graph/tool_executor.py` | Custom node replacing the prebuilt `ToolNode`; injects `user_id`/file content into user-scoped tool calls before dispatch, clears `pending_upload` after `ingest_pdf` runs. |
| `app/graph/builder.py` | `START → chatbot`, conditional edge to `tools`/`END`, `tools → chatbot` loop. |
| `app/tools/mcp_tools.py` | Connects to both `project_server` and `legal_rag_server` via `MultiServerMCPClient`; caches discovered tools. |
| `app/tools/server.py` | This repo's own FastMCP server (port 8002); exposes `web_search`, bearer-auth protected. |
| `app/persistence/db.py` | Postgres connection pool, checkpointer factory, users table setup. |
| `Dockerfile` / `docker-compose.yml` | Containerizes `api` + `mcp-server` + `postgres`. |

## 6. How to Run

### Docker (recommended)
```bash
cp .env.example .env
# fill in OPENAI_API_KEY, JWT_SECRET_KEY, WEB_SEARCH_API_KEY,
# MCP_AUTH_TOKEN, LEGAL_RAG_MCP_URL, LEGAL_RAG_AUTH_TOKEN
docker compose up --build
```
API available at `http://localhost:8000`.

### Local
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Try it
```bash
# 1. Sign up / log in to get a JWT
curl -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "..."}'

# 2. Chat (replace <jwt>)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" -H "Authorization: Bearer <jwt>" \
  -d '{"message": "What does CERC say about open access?", "thread_id": "demo-1"}'

# 3. Upload a PDF
curl -N -X POST http://localhost:8000/chat/upload \
  -H "Authorization: Bearer <jwt>" \
  -F "file=@notes.pdf" -F "thread_id=demo-1"
```

## 7. Environment Variables

```env
DATABASE_URL="postgresql://postgres:newpassword123@localhost:5432/chatdb"
OPENAI_API_KEY="sk-..."
JWT_SECRET_KEY="something-long-and-random"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_MINUTES=30

# This repo's own MCP server (web_search)
MCP_SERVER_URL="http://localhost:8002/mcp"
MCP_AUTH_TOKEN="your-secure-mcp-auth-token"
WEB_SEARCH_API_KEY="your-tavily-or-web-search-api-key"

# RAG pipeline repo's MCP server (search_legal_rag, search_general, ingest_pdf)
LEGAL_RAG_MCP_URL="http://localhost:8003/mcp"
LEGAL_RAG_AUTH_TOKEN="your-secure-legal-rag-mcp-auth-token"   # must match MCP_AUTH_TOKEN in the RAG repo's .env
```

## 8. Project Description

A backend template for stateful, multi-user, tool-using chatbots on LangGraph. Conversations persist to PostgreSQL via checkpointing, so they survive restarts and scale across workers. JWT auth scopes every conversation and every user-uploaded file to its owner. The LLM can call tools across two independently deployed MCP servers — its own (`web_search`) and a separate RAG pipeline repo's (`search_legal_rag`, `search_general`, `ingest_pdf`) — with per-user parameters injected automatically rather than trusted to the model, and results streamed back token-by-token over SSE.

## 9. Notes / Possible Next Steps

- **Error handling**: `chat_controller.py` currently swallows exceptions into an SSE error event — consider structured error codes for the frontend.
- **Testing**: Added unit tests for `custom_tool_executor`'s parameter injection, including multi-file matching and fallbacks.
- **Graph caching**: the graph is rebuilt on every request; cheap today, but cache the compiled graph at startup if overhead becomes noticeable.
- **Multi-file uploads**: Completed! `pending_upload` supports concurrent multi-file ingestion with dynamic filename matching.