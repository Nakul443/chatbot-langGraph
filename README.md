# LangGraph MCP Chatbot

A full-stack, multi-user AI chatbot. **Next.js** frontend + **FastAPI / LangGraph** backend, with durable conversations in **PostgreSQL**, **JWT auth**, and tool use over **MCP** (web search + a separate legal/general RAG pipeline). Answers stream token-by-token over **SSE**.

```
chatbot-langGraph/
├── backend/    FastAPI + LangGraph + Postgres + MCP client/server
└── frontend/   Next.js (App Router) Gemini-style chat UI
```

Per-folder docs: [`backend/README.md`](./backend/README.md) · [`frontend/README.md`](./frontend/README.md)

---

## Features

- Token-by-token streaming chat (SSE end to end)
- Email/password signup + login, JWT-secured API, httpOnly cookie on the web side
- Persistent threads: conversations survive restarts (LangGraph Postgres checkpointer) and reload from history
- Per-user isolation: threads and uploaded documents are scoped to the owner
- Tool calling via MCP: `web_search`, `search_legal_rag`, `search_general`, `ingest_pdf`
- Multi-PDF upload mid-conversation, indexed into the RAG pipeline per user
- Sidebar with thread list, new chat, settings/logout

---

## 1. Tech stack: what, why, where

### Backend (`backend/`)

| Tech | Why | Where |
|---|---|---|
| **FastAPI** + Uvicorn | Async API, native streaming responses, auto docs at `/docs` | `app/main.py`, `app/routes/` |
| **LangGraph** | Models the agent loop (LLM ⇄ tools) as an explicit graph with state | `app/graph/` |
| **LangChain + `langchain-google-genai`** | Gemini (`gemini-2.5-flash`) chat model with tools bound | `app/graph/nodes.py` |
| **PostgreSQL** + `langgraph-checkpoint-postgres` + `psycopg` pool | Durable per-thread state; also stores the `users` table | `app/persistence/db.py` |
| **PyJWT + bcrypt** | Stateless auth, hashed passwords | `app/auth/security.py`, `app/middleware/auth_middleware.py` |
| **FastMCP** + `langchain-mcp-adapters` | Tools exposed/consumed over MCP (streamable HTTP), auto-discovered at startup | `app/tools/` |
| **Tavily** (via `WEB_SEARCH_API_KEY`) | Backing API for the `web_search` tool | `app/tools/server.py` |
| **Docker / docker-compose** | api + MCP server + Postgres | `Dockerfile`, `docker-compose.yml` |

### Frontend (`frontend/`)

| Tech | Why | Where |
|---|---|---|
| **Next.js 16** (App Router) + **React 19** | Routing, server route handlers used as a backend proxy | `src/app/` |
| **TypeScript** | Type-safe components and API shapes | `src/types/` |
| **Tailwind CSS v4** | Styling (dark, Gemini-style UI) | `globals.css`, components |
| **Zustand** | Small global stores for auth + chat state | `src/store/authStore.ts` |
| **react-markdown + remark-gfm** | Render assistant replies as Markdown | `components/chat/MessageBubble.tsx` |
| **lucide-react, clsx, date-fns** | Icons, class merging, date formatting | components |

### Where things live

**Backend (`backend/app/`)**

| Path | Responsibility |
|---|---|
| `main.py` | App entrypoint: opens DB pool, sets up checkpoint + users tables, registers middleware and routers |
| `routes/` | HTTP endpoints (`auth_routes.py`, `chat_routes.py`) |
| `controllers/` | Business logic: signup/login, streaming a chat turn, upload → graph, threads, history |
| `middleware/` | `auth_middleware.py` (JWT → `request.state.user_id`), `logging_middleware.py` |
| `auth/` | Pydantic schemas, password hashing, JWT creation |
| `graph/` | `state.py`, `nodes.py` (LLM node), `tool_executor.py` (custom tool node), `builder.py` (wiring) |
| `tools/` | `server.py` (own MCP server, `web_search`), `mcp_tools.py` (client for both MCP servers) |
| `persistence/db.py` | Connection pool, checkpointer factory, `users` table |
| `tests/` | Unit tests for tool injection, graph build, threads/history |

**Frontend (`frontend/src/`)**

| Path | Responsibility |
|---|---|
| `app/(auth)/login`, `register` | Auth pages |
| `app/(chat)/` | Chat shell (`layout.tsx`), new chat (`page.tsx`), and a thread view (`[threadId]/page.tsx`) |
| `app/api/auth/route.ts` | Proxy for login/signup/logout; sets/clears the `auth_token` cookie |
| `app/api/chat/route.ts` | Proxy for threads, history, streaming chat, and uploads |
| `middleware.ts` | Route guard: no cookie → `/login`; cookie on auth pages → `/` |
| `services/api.ts` | Thin client wrapper around the two proxy routes |
| `hooks/` | `useAuth`, `useThreads`, `useChatStream` (SSE reader) |
| `store/authStore.ts` | Zustand `useAuthStore` and `useChatStore` |
| `components/` | `chat/` (input, bubbles, file upload), `sidebar/`, `settings/`, `ui/` |

---

## 2. How everything is connected

```
┌──────────────┐   /api/auth, /api/chat    ┌────────────────────┐
│   Browser    │ ────────────────────────► │ Next.js (:3000)    │
│  React + UI  │ ◄──── SSE stream ──────── │ route handlers     │
└──────────────┘      (cookie only)        │ (reads auth_token  │
                                           │  cookie → Bearer)  │
                                           └─────────┬──────────┘
                                                     │ Authorization: Bearer <jwt>
                                                     ▼
                                           ┌────────────────────┐
                                           │ FastAPI (:8000)    │
                                           │ AuthMiddleware     │──► user_id
                                           └─────────┬──────────┘
                                                     ▼
                         ┌────────────────────────────────────────────────┐
                         │ LangGraph:  START → chatbot ⇄ tools → END      │
                         │ chatbot = Gemini w/ MCP tools bound            │
                         │ tools   = custom executor (injects user_id,    │
                         │           file bytes for ingest_pdf)           │
                         └───────┬─────────────────────────┬──────────────┘
                                 │ checkpoints              │ MCP (streamable HTTP)
                                 ▼                          ▼
                         ┌──────────────┐        ┌───────────────────────┐
                         │ PostgreSQL   │        │ project MCP  (:8002)  │ web_search
                         │ checkpoints  │        │ legal RAG MCP (:8003) │ search_legal_rag,
                         │ + users      │        │ (separate repo)       │ search_general,
                         └──────────────┘        └───────────────────────┘ ingest_pdf
```

**Request lifecycle**

1. **Login.** The browser posts to Next.js `/api/auth`, which calls FastAPI `/auth/login` (or `/auth/signup`). The returned JWT is stored in an **httpOnly `auth_token` cookie**, so client-side JS never touches it.
2. **Route guard.** Next.js `middleware.ts` redirects based on whether that cookie exists.
3. **Chat.** The UI posts `{message, thread_id}` to Next.js `/api/chat`. The handler adds `Authorization: Bearer <jwt>` and forwards to FastAPI `POST /chat/stream`, then pipes the SSE body straight back to the browser. Because the browser only talks to Next.js, **no CORS setup is needed**.
4. **Auth + scoping.** `AuthMiddleware` verifies the JWT and sets `request.state.user_id`. The controller namespaces the thread as `"{user_id}:{thread_id}"` before touching the checkpointer, so users can't read each other's threads.
5. **Graph loop.** The `chatbot` node calls Gemini with all MCP tools bound. If the reply has tool calls, `tools` runs them and loops back to `chatbot`; otherwise the graph ends. Only tokens from the `chatbot` node are streamed as `data: …` events, ending with `data: [DONE]`.
6. **Why a custom tool node.** For `search_general` and `ingest_pdf`, the executor **injects `user_id` from state** (the LLM is never trusted to supply it). For `ingest_pdf` it also injects the base64 file bytes from `pending_upload`, so raw files never pass through the model's context.
7. **Persistence.** Every graph step is checkpointed to Postgres, so a `thread_id` resumes with full history. The sidebar reads `GET /chat/threads`, and opening a thread reads `GET /chat/history/{thread_id}`.

**Two MCP servers, one tool list**

| Server | Runs at | Tools | Auth env var |
|---|---|---|---|
| `project_server` | this repo, `backend/app/tools/server.py`, `:8002` | `web_search` | `MCP_AUTH_TOKEN` |
| `legal_rag_server` | separate RAG pipeline repo, `:8003` | `search_legal_rag`, `search_general`, `ingest_pdf` | `LEGAL_RAG_AUTH_TOKEN` |

Both are probed at startup; an unreachable server is skipped with a warning and the app still boots with the tools that are available. Tools are cached for the process lifetime.

**PDF upload flow:** the UI sends multipart `files` + `thread_id` (+ optional `message`) → backend base64-encodes the files into `pending_upload` and adds a synthetic user message → the LLM decides to call `ingest_pdf` → the executor fills in `user_id`, filename and bytes → the RAG server indexes them per user → later `search_general` calls only see that user's documents.

---

## 3. API reference (backend)

All routes except the public ones require `Authorization: Bearer <jwt>`. Public: `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/auth/signup`, `/auth/login`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Create user, returns token |
| POST | `/auth/login` | Returns token |
| POST | `/chat/stream` | `{message, thread_id}` → SSE token stream |
| POST | `/chat/upload` | multipart `files[]`, `thread_id`, optional `message` → SSE stream |
| GET | `/chat/threads` | List the user's threads, newest first |
| GET | `/chat/history/{thread_id}` | Full `{role, content}` history (404 if not found) |
| GET | `/health` | Health check |

Interactive docs: `http://localhost:8000/docs`

---

## 4. Getting started

### Prerequisites

- Git
- Node.js 20+ and npm
- Python 3.12 (matches the Dockerfile)
- PostgreSQL 16 (local or via Docker)
- Docker + Docker Compose (optional, recommended for the backend)
- API keys: **Gemini** (`GEMINI_API_KEY`), **Tavily** (`WEB_SEARCH_API_KEY`)
- Optional: the separate **legal RAG pipeline** repo running its MCP server on `:8003`. Without it the app still works, just without the RAG tools.

### Clone

```bash
git clone https://github.com/<your-username>/chatbot-langGraph.git
cd chatbot-langGraph
```

### Run the backend

**Option A: Docker**

```bash
cd backend
cp .env.example .env      # fill in the values (see section 5)
docker compose up --build
```

API at `http://localhost:8000`, MCP server at `:8002`, Postgres at `:5432`.

**Option B: Local**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in the values

# terminal 1: project MCP server (web_search)
python app/tools/server.py

# terminal 2: API
uvicorn app.main:app --reload
```

Make sure Postgres is running and `DATABASE_URL` in `.env` points to it. Tables (`checkpoints*`, `users`) are created automatically on startup.

### Run the frontend

```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_BACKEND_URL=http://localhost:8000' > .env.local
npm run dev
```

Open `http://localhost:3000`, register an account, and start chatting.

### Quick API smoke test (no UI)

```bash
curl -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" -H "Authorization: Bearer <jwt>" \
  -d '{"message": "Hello", "thread_id": "demo-1"}'

curl -N -X POST http://localhost:8000/chat/upload \
  -H "Authorization: Bearer <jwt>" \
  -F "files=@notes.pdf" -F "thread_id=demo-1"
```

---

## 5. Environment variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `GEMINI_API_KEY` | Google Gemini key (`GOOGLE_API_KEY` also accepted) |
| `JWT_SECRET_KEY` | Long random string used to sign tokens |
| `JWT_ALGORITHM` | Default `HS256` |
| `JWT_EXPIRE_MINUTES` | Token lifetime (code default `1440`; `.env.example` sets `30`) |
| `MCP_SERVER_URL` | Own MCP server, e.g. `http://localhost:8002/mcp` |
| `MCP_AUTH_TOKEN` | Bearer token the own MCP server requires |
| `WEB_SEARCH_API_KEY` | Tavily key for `web_search` |
| `LEGAL_RAG_MCP_URL` | RAG repo MCP endpoint, e.g. `http://localhost:8003/mcp` |
| `LEGAL_RAG_AUTH_TOKEN` | Must match `MCP_AUTH_TOKEN` in the RAG repo's `.env` |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | FastAPI base URL (defaults to `http://localhost:8000`). Only used in Next.js server route handlers. |

Generate a good JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## 6. Testing

```bash
cd backend
pip install pytest pytest-asyncio     # not listed in requirements.txt
pytest tests/
```

Covers `web_search`, graph construction, the tool executor's `user_id` / multi-file injection (exact, case-insensitive, substring, single-file fallback, missing file), and the threads/history endpoints. Frontend: `npm run lint`.

---

## 7. Security notes

- Passwords hashed with bcrypt; never stored in plain text.
- JWT in an **httpOnly, sameSite=lax** cookie (`secure` in production); the browser never sees the backend URL's token directly.
- Threads are namespaced by `user_id`; the LLM can never choose which user's data a tool touches.
- MCP servers are protected by bearer tokens.
- Never commit `.env` files (already in `.gitignore`). Rotate any keys that were ever pushed.
- Use a long random `JWT_SECRET_KEY` and a real Postgres password outside local dev.

---

## 8. Known gotchas

- **Docker DB credentials.** `docker-compose.yml` creates Postgres with user/password/db `postgres/postgres/postgres`, while `.env.example` points at `postgres:newpassword123@localhost:5432/chatdb`. Align them. Inside the compose network, the host should be `postgres`, not `localhost`.
- **Two Postgres definitions.** If you already run Postgres locally on `5432`, the compose `postgres` service will conflict. Stop one or change the port mapping.
- **RAG server from Docker.** From inside the `api` container, `localhost:8003` is the container itself. Use `http://host.docker.internal:8003/mcp` (add `extra_hosts: ["host.docker.internal:host-gateway"]` on Linux) or put both compose projects on a shared Docker network.
- **No RAG server running?** The backend logs a warning and runs with `web_search` only.
- **Cookie vs. token lifetime.** The cookie lives 24 h, but the JWT may expire sooner (30 min with the example `.env`). An expired token produces 401s until the user logs in again.
- **Next.js version.** The frontend uses a very recent Next.js (see `frontend/AGENTS.md`); check `node_modules/next/dist/docs/` if an API behaves differently from what you expect.

---

## 9. Roadmap ideas

- Structured SSE error events with codes (errors are currently streamed as plain text)
- Auto-generated thread titles instead of "Last updated" previews
- Token refresh / sliding sessions
- Rate limiting on auth and chat endpoints
- Frontend tests (component + e2e)
- CI: lint + backend tests on every push
- Production compose profile (no source-mount volumes, secrets via env/secret store)

---

## License

Add a `LICENSE` file (MIT is a common choice) and state it here.