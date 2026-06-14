# Simple Plan — Single User, Single Instance Agentic Chatbot

**Scope:** Build and validate the full feature set for a single user on a single backend instance. No auth, no load balancer, no multi-user isolation yet. Once everything works here, we layer on multi-user and scaling from `plan.md`.

> **Tracking rule:** After each stage is completed, update this file — check off all tasks and test criteria, add any implementation notes, and update `README.md` with the new functionality and instructions.

---

## Stage 1 — Project Scaffolding & Local Dev Setup

**Goal:** Get the project skeleton running with both services talking to each other.

### Tasks
- [x] Create project structure:
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
- [x] Backend: FastAPI app with `GET /health → { status: "ok" }`
- [x] Frontend: Vite + React, calls `/health` on load, displays result
- [x] PostgreSQL via Docker Compose (single container, persistent volume)
- [x] `.env` with `DATABASE_URL`, `OPENAI_API_KEY`

### Test Criteria
- [x] `docker-compose up` starts PostgreSQL
- [x] `uvicorn main:app --reload` starts backend; `GET /health` returns 200
- [x] Frontend loads in browser and shows a successful ping

---

## Stage 2 — Chat Thread Management (No Auth, No Agent Yet)

**Goal:** Persist conversations in PostgreSQL with new-chat and resume-chat working end-to-end.

### Tasks
- [x] PostgreSQL schema:
  - `threads (id UUID PK, title TEXT, created_at, updated_at)`
  - `messages (id UUID PK, thread_id UUID FK, role TEXT, content TEXT, media_refs JSONB, created_at)`
- [x] Tables created via `Base.metadata.create_all()` on backend startup (plain SQL approach)
- [x] `POST /threads` — create a new thread, return `thread_id`; auto-titles from first message
- [x] `GET /threads` — list all threads ordered by `updated_at` desc
- [x] `GET /threads/:id/messages` — full message history for a thread (404 on unknown ID)
- [x] `POST /threads/:id/messages` — save user message, echo placeholder assistant reply, update thread timestamp
- [x] Frontend:
  - Sidebar: list threads + "New Chat" button
  - Main panel: message history + input box (Enter to send, Shift+Enter for newline)
  - Clicking a thread in sidebar loads its history (resume chat)
  - Optimistic UI — user message appears instantly; typing indicator while waiting

### Test Criteria
- [x] Create a new thread, send a few messages, refresh — history persists
- [x] Resume a thread from the sidebar — history loads correctly
- [x] Placeholder echo reply is saved and displayed

---

## Stage 3 — LLM Integration & Real-Time Streaming

**Goal:** Real responses from `gpt-5.4-mini`, streamed token-by-token to the UI.

### Tasks
- [x] Install `openai>=1.0.0` Python SDK
- [x] Replace echo reply with a streaming OpenAI call via new `POST /threads/:id/chat` endpoint:
  - Build full message history from PostgreSQL as conversation context (with system prompt)
  - Call `gpt-5.4-mini` with `stream=True` using `AsyncOpenAI`
  - Stream user_message_id first, then each token as SSE: `data: {"token": "..."}`
  - On stream end, persist full assembled response to PostgreSQL; emit `data: {"done": true, "message_id": "..."}`
  - Errors caught and emitted as `data: {"error": "..."}` — agent is never invoked
- [x] Frontend:
  - New `sendMessage` uses `fetch` + `ReadableStream` (not `EventSource` — EventSource doesn't support POST)
  - Optimistic UI: user bubble + empty assistant bubble appear immediately
  - Tokens appended to assistant bubble in real time as they arrive
  - Blinking cursor (▌) shown via CSS animation while streaming
  - Input and Send button disabled during streaming
  - Stream errors shown in-place in the assistant bubble

### Test Criteria
- [x] Message streams token-by-token visibly in the UI (confirmed via curl SSE output)
- [x] Full response saved to DB after streaming; visible on thread resume (GET /messages confirmed)
- [x] Closing the browser mid-stream doesn't crash the backend (generator simply stops)
- [x] Stream errors caught and returned as `{"error": "..."}` event; shown in assistant bubble

---

## Stage 4 — ReAct Agent with LangGraph

**Goal:** Replace the direct LLM call with a stateful ReAct agent that can reason and act.

### Tasks
- [x] Install `langchain`, `langgraph`, `langchain-openai`
- [x] LangGraph code isolated in `backend/agent/` (separate from FastAPI routers):
  - `state.py` — `AgentState` TypedDict (messages, max_retries, retry_count, call_log)
  - `tools.py` — `TOOLS = []` registry (Stage 5 will populate)
  - `nodes.py` — `agent_node`, `tools_node` with lazy `ChatOpenAI` singleton
  - `graph.py` — `build_graph()` + module-level `graph` singleton imported by FastAPI
- [x] Graph shape: START → agent → conditional(tools → agent loop | END)
- [x] `max_retries` defaults to 5 and is passed in the initial graph input by FastAPI; no planner sub-agent
- [x] Comprehensive system prompt in `nodes.py` tells the agent what tools are available, instructs it to act before asking for clarification, and mandates source citations for web search results
- [x] Tool call deduplication in `tools_node`:
  - `call_log: list[{tool, params, count}]` tracked in AgentState
  - Same (tool, params) called ≥ 2 times → skip, return synthetic ToolMessage
  - `retry_count` incremented each round; routing checks `retry_count < max_retries`
- [x] `/threads/:id/chat` now drives `graph.astream_events()` (replaces raw `AsyncOpenAI`):
  - `on_chat_model_stream` (agent node) → `{"token": "..."}`
  - `on_tool_start` → `{"step": "tool_call", tool}`
- [x] Frontend: collapsible **Reasoning** section above the answer bubble shows all steps inline

### Test Criteria
- [x] Multi-turn context works — "multiply that by 10" correctly recalled prior answer (confirmed)
- [x] Intermediate steps (tool calls) appear in frontend Reasoning section
- [ ] Agent performs 2+ tool calls in one turn (requires Stage 5 tools — dedup logic is in place)
- [ ] Dedup: same (tool, params) called 3× → 3rd skipped (logic implemented, testable in Stage 5)

---

## Stage 5 — Built-In Tools (File System + Google Search)

**Goal:** Give the agent its first two real-world tools.

### Tasks

#### 5a — File System Tool
- [x] Tools: `read_file(path)`, `write_file(path, content)`, `list_directory(path)` in `backend/agent/tools.py`
- [x] Sandbox: `_safe_path()` uses `Path.relative_to(WORKSPACE_DIR)` — immune to prefix-collision attacks
- [x] WORKSPACE_DIR defaults to `<project_root>/workspace/`, auto-created on startup; overridable via `.env`
- [x] Registered in TOOLS list — automatically bound to agent LLM and available to `tools_node`

#### 5b — Google Search Tool
- [x] `google_search(query)` implemented using SerpAPI (`requests` to `https://serpapi.com/search`)
- [x] Returns top-5 results: title, URL, snippet
- [x] Degrades gracefully when `SERPAPI_KEY` is unset — returns descriptive error, agent informs user
- [x] `requests` added to `requirements.txt`; `SERPAPI_KEY` documented in `.env.example`

#### Planner improvement
- [x] Prompt rewritten to count tool calls explicitly and map to tiers:
  0-1 calls → low (1), 2 calls → medium (2), 3+ calls → high (3)
  Keywords like "then", "after that", "also" cue multi-step classification

### Test Criteria
- [x] `list_directory` → returned "(empty directory)" for fresh workspace ✓
- [x] Write `test.txt` then read it back → planner rated medium (2 retries), both tool calls executed, contents confirmed ✓
- [x] `../../etc/passwd` → rejected by `_safe_path()` with "Access denied" error ✓
- [ ] Google Search → requires SERPAPI_KEY; tool registered and returns clear error when key is absent ✓ (full test pending key)

---

## Stage 6 — Custom MCP Server: Calculator

**Goal:** Build our own MCP server from scratch and connect it to the agent.

### Tasks
- [x] Create `mcp_servers/calculator/server.py` using the MCP Python SDK (`mcp`)
- [x] Expose tools over `stdio` transport:
  - `add(a: float, b: float) → float`
  - `subtract(a: float, b: float) → float`
  - `multiply(a: float, b: float) → float`
  - `divide(a: float, b: float) → float` (raises error on divide-by-zero)
  - `evaluate(expression: str) → float` (safe eval via AST walker, no `exec`)
- [x] Add a `README` under `mcp_servers/calculator/` documenting the tools and how to run the server
- [x] Tools discovered at backend startup via `langchain-mcp-adapters` `MultiServerMCPClient`; subprocess managed per-call by the adapter (0.1.0+ API)
- [x] `backend/agent/mcp_client.py` — `start_mcp_client` / `stop_mcp_client` wired into FastAPI lifespan in `main.py`
- [x] `backend/agent/nodes.py` — `_agent_llm()` and `tools_node` include MCP tools via `get_mcp_tools()`
- [x] Register as a default tool — no user setup required

### Test Criteria
- [x] `python mcp_servers/calculator/server.py` — starts without errors ✓
- [x] `add(3,4)=7`, `subtract(10,3)=7`, `multiply(6,7)=42`, `divide(15,4)=3.75` ✓
- [x] `divide(5, 0)` returns structured error message, no crash ✓
- [x] `evaluate("2 ** 10 + 5 * 3")` returns `1039.0` ✓
- [x] `evaluate("(100 / 4) + 37")` returns `62.0` ✓
- [ ] Ask agent "what is 1234 * 5678?" → agent calls `multiply` via MCP (live test)
- [ ] Ask agent "what is (100 / 4) + 37?" → agent calls `evaluate` via MCP (live test)

### Implementation Notes
- Used `FastMCP` from `mcp.server.fastmcp` for the server — minimal boilerplate
- `evaluate` uses a recursive AST walker (`ast.BinOp`, `ast.UnaryOp`, `ast.Constant`) — no `exec`/`eval`
- `langchain-mcp-adapters` 0.1.0+ dropped the persistent async context manager; `get_tools()` is now `async` and each tool invocation creates its own subprocess session
- Google Search (SerpAPI) replaced by DuckDuckGo (`ddgs` package) earlier in Stage 5 — free, no API key
- `requests` and `langchain-community` removed from dependencies

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
- [ ] At end of each session (or when history exceeds a token threshold): run a summarization call to `gpt-5.4-mini` → upsert summary into `memories`
- [ ] At the start of every new thread: fetch the latest memory summary and inject into agent system prompt as: `"Here's what I know about you from previous conversations: {summary}"`
- [ ] Agent tool: `update_memory(fact: str)` — agent can explicitly store a new fact mid-conversation

### Test Criteria
- Within a session: ask agent to remember your name, ask it again 5 messages later — it remembers
- Resume a thread: full history restores correctly
- Start a brand new thread: agent references facts from the previous session
- Explicitly tell agent to remember something → it calls `update_memory`, fact appears in next session

---

## Stage 10 — Image Input

**Goal:** Accept images in the chat input and let the agent reason over them.

### Tasks
- [ ] Frontend: image attach button in chat input; thumbnail preview before send
- [ ] Backend: `POST /threads/:id/chat` accepts `multipart/form-data` with optional image
- [ ] Image saved to local `media/` directory; path stored in `messages.media_refs`
- [ ] Image passed to `gpt-5.4-mini` vision endpoint as base64 alongside the text prompt
- [ ] Guardrails applied to image content description extracted by the model

### Test Criteria
- Send an image of a chart and ask "what does this show?" — agent describes it correctly
- Image messages persist and are visible on thread resume
- Guardrail intercepts a harmful image description before it reaches the user

---

## Stage 11 — Guardrails

**Goal:** Block harmful inputs before the agent sees them; filter harmful outputs before the user sees them.

### Approach: Hybrid (3-layer)

| Layer | Tool | Catches |
|---|---|---|
| 1 | OpenAI Moderation API | Hate, harassment, self-harm, sexual content, violence |
| 2 | `gpt-5.4-mini` LLM classifier | Prompt injection, jailbreaks (escalated from layer 1 only) |
| 3 | Regex validators | PII leakage in output (email, phone, SSN) |

### Tasks
- [ ] **Input Guardrail** (runs after user submits, before agent):
  - Call `openai.moderations.create()` on the user message
  - If moderation flags it → emit SSE refusal event, do not invoke agent
  - If moderation passes but message matches injection patterns (e.g. contains `"ignore previous instructions"`, `"disregard your"`, `"you are now"`) → escalate to `gpt-5.4-mini` classifier
  - If classifier flags it → emit SSE refusal event, do not invoke agent
- [ ] **Output Guardrail** (runs after agent responds, before SSE stream):
  - Call `openai.moderations.create()` on the full response
  - If flagged → replace with a safe fallback message
  - Run regex scan for PII patterns on both the user's input and the agent's output (email: `[\w.]+@[\w.]+`, phone: `\d{3}[-.\s]\d{3}[-.\s]\d{4}`, SSN: `\d{3}-\d{2}-\d{4}`)
  - **Delta check**: subtract PII found in the user's input from PII found in the output — only the remainder is hallucinated/leaked
  - If hallucinated PII found → redact those matches before sending to frontend; user-provided PII is left intact
- [ ] PostgreSQL schema: `guardrail_logs (id, direction TEXT, layer TEXT, flagged_content TEXT, reason TEXT, created_at)`
- [ ] Log all flagged events with the layer that caught them

### Test Criteria
- Known harmful content (`"how to make a weapon"`) → blocked by Moderation API; agent not called
- Known prompt injection (`"Ignore all previous instructions..."`) → escalated to LLM classifier; blocked
- Clean message → passes through; no added latency > 200ms (Moderation API is fast)
- Output with an email address → email is redacted before reaching the UI
- Guardrail log records the layer (`moderation`, `llm_classifier`, `regex`) that triggered the block

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
