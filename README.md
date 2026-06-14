# Full-Stack Agentic Chatbot

A production-grade agentic chatbot built on the ReAct (Reasoning + Acting) framework. It supports tool use, RAG-based document querying, short and long-term memory, observability, guardrails, and real-time streaming.

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangChain + LangGraph (ReAct) |
| LLM | `gpt-5.4-nano` (OpenAI) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers, local) |
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| Database | PostgreSQL 16 |
| Vector Store | ChromaDB (local) |
| Observability | Arize Phoenix |
| Containerization | Docker |

## Project Structure

```
full_stack_chatbot/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLAlchemy engine + session + Base
│   ├── models.py            # ORM models (Thread, Message)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── requirements.txt
│   ├── routers/
│   │   └── threads.py       # Thread & message CRUD + /chat SSE endpoint
│   └── agent/               # LangGraph — isolated from FastAPI
│       ├── state.py         # AgentState TypedDict
│       ├── tools.py         # TOOLS registry (empty until Stage 5)
│       ├── nodes.py         # planner_node, agent_node, tools_node
│       └── graph.py         # Compiled graph singleton
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js       # Dev proxy → backend
│   └── src/
│       ├── main.jsx
│       ├── index.css
│       └── App.jsx          # Chat UI (sidebar + message panel)
├── mcp_servers/
│   └── calculator/
│       └── server.py        # Custom MCP server (Stage 6)
├── docker-compose.yml       # PostgreSQL service
├── .env                     # Secrets (never commit)
├── .env.example             # Template for .env
├── simple_plan.md           # Active build plan (single-user path)
├── plan.md                  # Full multi-user plan (future)
└── README.md
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Stage | Description |
|---|---|---|
| `OPENAI_API_KEY` | 1 | OpenAI API key |
| `DATABASE_URL` | 1 | PostgreSQL connection string |
| `SERPAPI_KEY` | 5 | SerpAPI key for Google Search tool |
| `WORKSPACE_DIR` | 5 | Sandboxed directory for File System tool |
| `MEDIA_DIR` | 10 | Local path for uploaded images |
| `CHROMA_DIR` | 8 | Local path for ChromaDB persistence |
| `PHOENIX_HOST` | 12 | Arize Phoenix host (default: `localhost`) |
| `PHOENIX_PORT` | 12 | Arize Phoenix port (default: `6006`) |

---

## Running Locally

### Prerequisites

1. **Python 3.11+**
2. **Node.js 18+**
3. **Docker Desktop** — for PostgreSQL
   - Download from https://www.docker.com/products/docker-desktop

### Start the App

**Terminal 1 — PostgreSQL**
```bash
docker-compose up
```

**Terminal 2 — Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### Troubleshooting

**`[Errno 48] Address already in use` — port 8000 (backend)**

Another process is already holding port 8000. Kill it and restart uvicorn:
```bash
lsof -ti :8000 | xargs kill -9 2>/dev/null && echo "Port 8000 freed" || echo "Nothing on port 8000"
```

**`EADDRINUSE` — port 5173 (frontend)**

Same issue for the Vite dev server:
```bash
lsof -ti :5173 | xargs kill -9 2>/dev/null && echo "Port 5173 freed" || echo "Nothing on port 5173"
```

After freeing the port, re-run the relevant `uvicorn` or `npm run dev` command.

---

## What's Built (Current State)

### Stage 1 — Scaffolding ✅
- FastAPI backend with `GET /health → { status: "ok" }`
- React + Vite frontend calling `/health` on load
- PostgreSQL running via Docker Compose with a persistent named volume
- `.env` wired for `DATABASE_URL` and `OPENAI_API_KEY`

### Stage 2 — Chat Thread Management ✅
- **PostgreSQL schema** — `threads` and `messages` tables, created automatically on backend startup
- **`POST /threads`** — creates a new thread; auto-titles it from the first message sent
- **`GET /threads`** — lists all threads, most recently active first
- **`GET /threads/:id/messages`** — returns full message history for a thread
- **`POST /threads/:id/messages`** — saves the user message and an echo reply, updates `updated_at` on the thread
- **Frontend chat UI**:
  - Dark-themed sidebar with all threads + "New Chat" button
  - Chat panel with message bubbles (user right, assistant left)
  - Optimistic UI — message appears instantly before the server responds
  - Typing indicator while waiting for reply
  - Enter to send, Shift+Enter for newline
  - Clicking any thread in the sidebar resumes it with full history

### Stage 3 — LLM Integration & Real-Time Streaming ✅
- **`POST /threads/:id/chat`** — streaming endpoint using Server-Sent Events (SSE)
  - Loads full thread history from PostgreSQL as conversation context
  - Calls `gpt-5.4-nano` with `stream=True`
  - Emits `{"user_message_id"}` first, then `{"token": "..."}` per token, then `{"done": true, "message_id": "..."}` on completion
  - Errors emitted as `{"error": "..."}` — no crash, no unhandled exception
  - Both user and assistant messages persisted to PostgreSQL after streaming ends
- **Frontend streaming UI**:
  - Uses `fetch` + `ReadableStream` (EventSource doesn't support POST)
  - Assistant bubble appears immediately and fills in token-by-token
  - Blinking cursor `▌` shown via CSS animation while streaming
  - Input and Send button locked during streaming
  - Full conversation context sent to the LLM on every turn

### Stage 5 — Built-In Tools (File System + Google Search) ✅
All tools live in `backend/agent/tools.py` and are auto-bound to the agent at startup.

**File System tools** — sandboxed to `<project_root>/workspace/` (auto-created):
- `read_file(path)` — reads a file; returns content or a clear error
- `write_file(path, content)` — writes a file; creates parent dirs automatically
- `list_directory(path)` — lists entries as `FILE name` / `DIR name` rows
- Sandbox uses `Path.relative_to()` for traversal detection — `../../etc/passwd` is blocked before any I/O

**Google Search tool** — calls SerpAPI, returns top-5 results (title + URL + snippet):
- Set `SERPAPI_KEY` in `.env` to enable; tool degrades gracefully with a descriptive error if unset

**Planner improvement** — prompt rewritten to explicitly count tool calls and map to tiers (0-1 → low, 2 → medium, 3+ → high) so multi-step tasks get sufficient retry budget.

### Stage 4 — ReAct Agent with LangGraph ✅
All LangGraph code lives in `backend/agent/` — isolated from FastAPI routers so it can be read and extended independently.

| File | Purpose |
|---|---|
| `agent/state.py` | `AgentState` TypedDict — messages, complexity, max_retries, retry_count, call_log |
| `agent/tools.py` | `TOOLS = []` registry — Stage 5 appends real tools here |
| `agent/nodes.py` | `planner_node`, `agent_node`, `tools_node` — lazy `ChatOpenAI` singletons |
| `agent/graph.py` | Graph wiring + module-level `graph` singleton |

**Graph flow:** `START → planner → agent → [tools → agent]* → END`

- **Planner node** classifies query complexity (`low/medium/high`) and sets `max_retries` (1/2/3) using structured output
- **Agent node** calls `ChatOpenAI` with the full message history + system prompt; uses `streaming=True` so tokens surface via `astream_events`
- **Tools node** executes tool calls with deduplication: same `(tool, params)` called ≥ 2 times is skipped with a synthetic ToolMessage
- **Router** (`_route_after_agent`) sends the agent back to tools if there are tool calls and `retry_count < max_retries`, otherwise exits to END
- FastAPI `/chat` endpoint drives `graph.astream_events()` and translates events into SSE frames
- Frontend shows a collapsible **Reasoning** section with planner output, tool calls, and tool results above the final answer bubble

---

## API Reference

### Threads

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/threads` | Create a new thread |
| `GET` | `/threads` | List all threads (newest first) |
| `GET` | `/threads/:id/messages` | Get full message history |
| `POST` | `/threads/:id/messages` | Send a message, get an echo reply (Stage 2 only) |
| `POST` | `/threads/:id/chat` | Send a message, stream LLM response via SSE |

### Request / Response Examples

**Create thread**
```bash
curl -X POST http://localhost:8000/threads \
  -H 'Content-Type: application/json' \
  -d '{"title": "New Chat"}'
```

**Send message**
```bash
curl -X POST http://localhost:8000/threads/<thread_id>/messages \
  -H 'Content-Type: application/json' \
  -d '{"content": "Hello!"}'
# Returns: { user_message: {...}, assistant_message: {...} }
```

---

## Build Stages

| Stage | Feature | Status |
|---|---|---|
| 1 | Project scaffolding & local dev setup | ✅ Done |
| 2 | Chat thread management (PostgreSQL + UI) | ✅ Done |
| 3 | LLM integration & real-time SSE streaming | ✅ Done |
| 4 | ReAct agent with LangGraph | ✅ Done |
| 5 | Built-in tools (File System + Google Search) | ✅ Done |
| 6 | Custom MCP server (Calculator) | 🔜 Next |
| 7 | Dynamic MCP server registration | — |
| 8 | Document ingestion & RAG | — |
| 9 | Memory (short-term & long-term) | — |
| 10 | Image input | — |
| 11 | Guardrails (moderation + PII filtering) | — |
| 12 | Observability with Arize Phoenix | — |
| 13 | Docker (full single-instance deployment) | — |
