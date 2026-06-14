# Simple Plan — Single User, Single Instance Agentic Chatbot

**Scope:** Build and validate the full feature set for a single user on a single backend instance. No auth, no load balancer, no multi-user isolation yet. Once everything works here, we layer on multi-user and scaling from `plan.md`.

---

## Stage 1 — Project Scaffolding & Local Dev Setup

**Goal:** Get the project skeleton running with both services talking to each other.

### Tasks
- [ ] Create project structure:
  ```
  /
  ├── backend/
  │   ├── main.py
  │   ├── requirements.txt
  │   └── .env
  ├── frontend/
  │   └── (React app)
  ├── mcp_servers/
  │   └── calculator/
  │       └── server.py
  ├── docker-compose.yml
  └── .env.example
  ```
- [ ] Backend: FastAPI app with `GET /health → { status: "ok" }`
- [ ] Frontend: Vite + React, calls `/health` on load, displays result
- [ ] PostgreSQL via Docker Compose (single container, persistent volume)
- [ ] `.env` with `DATABASE_URL`, `OPENAI_API_KEY`

### Test Criteria
- `docker-compose up` starts PostgreSQL
- `uvicorn main:app --reload` starts backend; `GET /health` returns 200
- Frontend loads in browser and shows a successful ping

---

## Stage 2 — Chat Thread Management (No Auth, No Agent Yet)

**Goal:** Persist conversations in PostgreSQL with new-chat and resume-chat working end-to-end.

### Tasks
- [ ] PostgreSQL schema:
  - `threads (id UUID PK, title TEXT, created_at, updated_at)`
  - `messages (id UUID PK, thread_id UUID FK, role TEXT, content TEXT, media_refs JSONB, created_at)`
- [ ] Run migrations with Alembic (or plain SQL scripts for now)
- [ ] `POST /threads` — create a new thread, return `thread_id`
- [ ] `GET /threads` — list all threads (single user, no filtering)
- [ ] `GET /threads/:id/messages` — full message history for a thread
- [ ] `POST /threads/:id/messages` — save user message, echo a placeholder assistant reply
- [ ] Frontend:
  - Sidebar: list threads + "New Chat" button
  - Main panel: message history + input box
  - Clicking a thread in sidebar loads its history (resume chat)

### Test Criteria
- Create a new thread, send a few messages, refresh — history persists
- Resume a thread from the sidebar — history loads correctly
- Placeholder echo reply is saved and displayed

---

## Stage 3 — LLM Integration & Real-Time Streaming

**Goal:** Real responses from `gpt-5.4-nano`, streamed token-by-token to the UI.

### Tasks
- [ ] Install `openai` Python SDK
- [ ] Replace echo reply with a streaming OpenAI call:
  - Build message history from PostgreSQL as the conversation context
  - Call `gpt-5.4-nano` with `stream=True`
  - Stream each token as a **Server-Sent Event**: `data: {"token": "..."}`
  - On stream end, persist the full assembled response to PostgreSQL
- [ ] Frontend:
  - Switch `POST /threads/:id/chat` to consume SSE (`EventSource`)
  - Append tokens to the assistant message bubble in real time
  - Show a blinking cursor / typing indicator while streaming
  - Handle stream errors with a user-visible error message

### Test Criteria
- Message streams token-by-token visibly in the UI (not a bulk response)
- Full response is saved to the DB; visible on thread resume
- Closing the browser mid-stream doesn't crash the backend
- A bad API key shows a friendly error in the UI

---

## Stage 4 — ReAct Agent with LangGraph

**Goal:** Replace the direct LLM call with a stateful ReAct agent that can reason and act.

### Tasks
- [ ] Install `langchain`, `langgraph`, `langchain-openai`
- [ ] Define LangGraph agent graph:
  - **Nodes:** `planner`, `agent` (think + act), `tools`, `responder`
  - **Edges:** conditional — if agent decides to call a tool → tools node → back to agent; else → responder
- [ ] Planner sub-agent:
  - Input: user query
  - Output: `{ complexity: "low"|"medium"|"high", max_retries: int }`
  - `low` → 1 retry, `medium` → 2, `high` → 3
- [ ] Tool call deduplication in agent state:
  - State tracks `call_log: list[{tool, params, count}]`
  - Before each tool call: if same `(tool, params)` already called ≥ 2 times → skip, proceed to respond
- [ ] Wire agent into the streaming endpoint:
  - Intermediate steps (tool calls, observations) emitted as SSE events: `data: {"step": "tool_call", "tool": "...", "input": "..."}`
  - Final answer streamed as `data: {"token": "..."}`
- [ ] Frontend: display intermediate agent steps in a collapsible "Thinking..." section above the final answer

### Test Criteria
- Agent performs multi-step reasoning (at least 2 tool calls in one turn)
- Planner assigns correct retry limits for simple vs complex queries
- Triggering the same tool with identical args 3 times → 3rd call is skipped; agent responds with what it has
- Intermediate steps appear in the UI

---

## Stage 5 — Built-In Tools (File System + Google Search)

**Goal:** Give the agent its first two real-world tools.

### Tasks

#### 5a — File System Tool
- [ ] Tool functions: `read_file(path)`, `write_file(path, content)`, `list_directory(path)`
- [ ] Sandbox: all paths resolved relative to a fixed `/workspace` directory; reject `..` traversal
- [ ] Register with LangGraph agent

#### 5b — Google Search Tool
- [ ] Integrate SerpAPI or Google Custom Search API
- [ ] Tool: `google_search(query) → list[{title, url, snippet}]`
- [ ] Register with LangGraph agent
- [ ] Add `SERPAPI_KEY` (or `GOOGLE_API_KEY` + `GOOGLE_CSE_ID`) to `.env`

### Test Criteria
- Ask agent to "list files in /workspace" → returns directory contents
- Ask agent to write a file then read it back → contents match
- Path traversal attempt (`../../etc/passwd`) is blocked with an error
- Ask agent a current-events question → agent uses Google Search and cites results

---

## Stage 6 — Custom MCP Server: Calculator

**Goal:** Build our own MCP server from scratch and connect it to the agent.

### Tasks
- [ ] Create `mcp_servers/calculator/server.py` using the MCP Python SDK (`mcp`)
- [ ] Expose tools over `stdio` transport:
  - `add(a: float, b: float) → float`
  - `subtract(a: float, b: float) → float`
  - `multiply(a: float, b: float) → float`
  - `divide(a: float, b: float) → float` (raises error on divide-by-zero)
  - `evaluate(expression: str) → float` (safe eval using `ast.literal_eval` logic, no `exec`)
- [ ] Add a `README` under `mcp_servers/calculator/` documenting the tools and how to run the server
- [ ] Start the calculator MCP server as a subprocess at backend startup
- [ ] Connect to it via LangChain's MCP client (`langchain-mcp-adapters`) and add its tools to the agent
- [ ] Register as a default tool — no user setup required

### Test Criteria
- Run `python mcp_servers/calculator/server.py` — server starts without errors
- Call each tool directly via MCP client and verify correct results
- `divide(5, 0)` returns a structured error, not a crash
- `evaluate("2 ** 10 + 5 * 3")` returns `1039`
- Ask agent "what is 1234 * 5678?" → agent calls `multiply` via MCP and returns the correct answer
- Ask agent "what is (100 / 4) + 37?" → agent calls `evaluate` via MCP

---

## Stage 7 — Dynamic MCP Server Registration

**Goal:** Users can plug in any MCP server at runtime, and the agent will use its tools automatically.

### Tasks
- [ ] PostgreSQL schema: `mcp_servers (id UUID PK, name TEXT, transport TEXT, config JSONB, enabled BOOL, created_at)`
  - `config` for `stdio`: `{ "command": "python", "args": ["path/to/server.py"] }`
  - `config` for `sse`: `{ "url": "http://host:port/sse" }`
- [ ] `POST /mcp-servers` — register a new MCP server
- [ ] `GET /mcp-servers` — list registered servers
- [ ] `PATCH /mcp-servers/:id` — enable/disable a server
- [ ] `DELETE /mcp-servers/:id` — remove a server
- [ ] At agent session start: load all enabled MCP servers from DB, connect to each, discover their tools, add to agent tool registry dynamically
- [ ] Frontend: MCP Servers settings panel
  - List registered servers with enable/disable toggle
  - "Add Server" form: name, transport (stdio/sse), command+args or URL
  - Delete button per server

### Test Criteria
- Register a new MCP server via the UI
- Start a new chat — agent has the new server's tools available
- Disable the server — new chats no longer have its tools
- Delete the server — it no longer appears in the list
- Register an invalid server config — backend returns a clear validation error

---

## Stage 8 — Document Ingestion & RAG

**Goal:** Upload a document, embed it locally, and query it via the agent.

### Tasks
- [ ] Install `sentence-transformers`, `chromadb` (local, no separate service needed)
- [ ] Load `all-MiniLM-L6-v2` at backend startup (local inference)
- [ ] PostgreSQL schema: `documents (id UUID PK, filename TEXT, status TEXT, created_at)`
- [ ] `POST /documents/ingest` — multipart file upload endpoint:
  - Parse PDF with PyMuPDF (`fitz`); TXT read directly
  - Split into chunks (512 tokens, 50-token overlap)
  - Embed each chunk with `all-MiniLM-L6-v2`
  - Store in ChromaDB collection (single collection for now — no user scoping yet)
  - Record in PostgreSQL `documents` table with status `processing` → `ready`
- [ ] RAG Tool: `rag_query(query) → list[{chunk, score, source_file}]`
  - Embed query, top-5 semantic search in ChromaDB
  - Return ranked chunks to agent for synthesis
- [ ] Register RAG tool with agent
- [ ] Frontend: file upload button in sidebar; ingestion status shown per document

### Test Criteria
- Upload a PDF; status changes to `ready`
- Ask a question answered only in that PDF — agent returns a correct, grounded answer
- Ask an unrelated question — agent does not hallucinate content from the PDF
- Upload a second PDF — both are queryable

---

## Stage 9 — Memory (Short-Term & Long-Term)

**Goal:** Agent remembers within a conversation and across conversations.

### Tasks

#### 9a — Short-Term Memory
- [ ] Use LangGraph's built-in **PostgreSQL checkpointer** to persist graph state per `thread_id`
- [ ] On each turn, agent state is restored from the checkpointer before running
- [ ] Full current-session message history is always in the agent's context window

#### 9b — Long-Term Memory
- [ ] PostgreSQL schema: `memories (id UUID PK, summary TEXT, created_at, updated_at)`
- [ ] At end of each session (or when history exceeds a token threshold): run a summarization call to `gpt-5.4-nano` → upsert summary into `memories`
- [ ] At the start of every new thread: fetch the latest memory summary and inject into agent system prompt as: `"Here's what I know about you from previous conversations: {summary}"`
- [ ] Agent tool: `update_memory(fact: str)` — agent can explicitly store a new fact mid-conversation

### Test Criteria
- Within a session: ask agent to remember your name, ask it again 5 messages later — it remembers
- Resume a thread: full history restores correctly
- Start a brand new thread: agent references facts from the previous session
- Explicitly tell agent to remember something → it calls `update_memory`, fact appears in next session

---

## Stage 10 — Multi-Modal Inputs (Image & Audio)

**Goal:** Accept images and audio in the chat input.

### Tasks

#### 10a — Image
- [ ] Frontend: image attach button; preview thumbnail before send
- [ ] Backend: `POST /threads/:id/chat` accepts `multipart/form-data` with optional image
- [ ] Image saved to local `media/` directory; path stored in `messages.media_refs`
- [ ] Image passed to `gpt-5.4-nano` vision endpoint as base64 alongside text prompt

#### 10b — Audio
- [ ] Frontend: record-audio button (browser MediaRecorder API) or file upload (MP3/WAV/M4A)
- [ ] Backend: audio uploaded, sent to **OpenAI Whisper** (`whisper-1`) for transcription
- [ ] Transcript used as the user message text; audio path stored in `messages.media_refs`
- [ ] Frontend: display `"🎤 Transcribed: <transcript>"` label above the message

### Test Criteria
- Send an image of a chart and ask "what does this show?" — agent describes it correctly
- Send an audio clip asking a question — transcript appears in UI, agent answers correctly
- Multi-modal messages persist and are visible on thread resume

---

## Stage 11 — Guardrails

**Goal:** Block harmful inputs before the agent sees them; filter harmful outputs before the user sees them.

### Tasks
- [ ] **Input Guardrail** (runs immediately after user submits):
  - Use `gpt-5.4-nano` with a classifier system prompt to detect: prompt injection, jailbreak attempts, policy violations
  - If flagged: emit an SSE event with a canned refusal; do not invoke the agent
- [ ] **Output Guardrail** (runs after agent produces a response, before final SSE token stream):
  - Detect: toxic content, PII leakage, harmful instructions
  - If flagged: replace response with a safe fallback message
- [ ] PostgreSQL schema: `guardrail_logs (id, direction TEXT, flagged_content TEXT, reason TEXT, created_at)`
- [ ] Log all flagged events to `guardrail_logs`

### Test Criteria
- Known prompt injection (`"Ignore all previous instructions..."`) → canned refusal, agent not called
- Clean message → passes through, no latency difference > 200ms
- Guardrail log shows the flagged input with reason
- Output guardrail catches a synthetic harmful response in a unit test

---

## Stage 12 — Observability with Arize Phoenix

**Goal:** Trace every agent run; evaluate quality automatically.

### Tasks
- [ ] Run Arize Phoenix locally: `pip install arize-phoenix` + `python -m phoenix.server.main`
- [ ] Instrument LangChain/LangGraph with Phoenix's OpenTelemetry exporter
- [ ] Each agent run produces a trace with spans for:
  - Planner call (input query, output complexity + max_retries)
  - Each tool call (tool name, input, output, latency)
  - Each LLM call (prompt, completion, token count, model)
  - Guardrail checks (pass/fail, latency)
- [ ] Async evaluators (run after response is sent):

  | Evaluator | Trigger | Method |
  |---|---|---|
  | Answer Accuracy | Every turn | LLM-as-judge |
  | Hallucination | RAG turns only | Check claim vs. retrieved chunks |
  | Groundedness | RAG turns only | Overlap between answer and sources |

- [ ] Evaluation scores logged as span attributes in Phoenix

### Test Criteria
- Every chat turn produces a visible trace in Phoenix UI (`http://localhost:6006`)
- RAG query trace shows retrieval spans and evaluation scores
- A known hallucination scores low on groundedness
- Planner span shows `complexity` and `max_retries` attributes

---

## Stage 13 — Docker (Single Instance)

**Goal:** The full app runs via `docker-compose up` with no local dependencies.

### Tasks
- [ ] `docker/Dockerfile.backend` — Python 3.11, install dependencies, copy app, `CMD uvicorn`
- [ ] `docker/Dockerfile.frontend` — Node build stage → Nginx serve stage
- [ ] `docker-compose.yml` services:
  - `postgres` — PostgreSQL 16, persistent volume
  - `backend` — FastAPI, depends on `postgres`
  - `frontend` — React/Nginx, proxies `/api` to `backend`
  - `phoenix` — Arize Phoenix (`arizephoenix/phoenix`)
- [ ] Embed `mcp_servers/calculator/` inside the backend image; calculator server started as a subprocess
- [ ] All secrets via `.env` file (never baked into images)
- [ ] Health checks on `backend` and `postgres`

### Test Criteria
- `docker-compose up --build` starts all services with no errors
- Full chat flow works end-to-end through Docker (no localhost port hacks)
- Upload a document → RAG query works inside Docker
- Phoenix UI accessible at `http://localhost:6006`
- Stop and restart: all data persists

---

## Build Order

```
Stage 1  Scaffolding
  └── Stage 2  Chat Threads (DB + UI)
        └── Stage 3  LLM + Streaming
              └── Stage 4  ReAct Agent (LangGraph)
                    ├── Stage 5  Built-in Tools (FS + Search)
                    ├── Stage 6  Calculator MCP Server  ←─ build & test standalone first
                    │     └── Stage 7  Dynamic MCP Registration
                    ├── Stage 8  Document Ingestion + RAG
                    ├── Stage 9  Memory
                    └── Stage 10 Multi-Modal
                          └── Stage 11 Guardrails
                                └── Stage 12 Observability
                                      └── Stage 13 Docker
```

---

## Key Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (LLM + Whisper) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SERPAPI_KEY` | SerpAPI key for Google Search tool |
| `PHOENIX_HOST` | Arize Phoenix host (default: `localhost`) |
| `PHOENIX_PORT` | Arize Phoenix port (default: `6006`) |
| `MEDIA_DIR` | Local path for uploaded images and audio files |
| `WORKSPACE_DIR` | Sandboxed directory for File System tool |
| `CHROMA_DIR` | Local path for ChromaDB persistence |

---

## What's Deferred to `plan.md` (Multi-User / Scale)

- User registration & authentication (JWT)
- Per-user thread isolation
- Per-user vector store namespacing
- Per-user MCP server registry
- Multi-instance Docker Compose scaling
- Python auto-scaling load balancer
