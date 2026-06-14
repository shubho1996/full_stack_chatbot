# Execution Plan — Full-Stack Production-Ready Agentic Chatbot

Each stage is independently testable. Complete and verify a stage before moving to the next.

> **Note:** This is the full multi-user, production-scale plan. For the single-user baseline first, follow `simple_plan.md` and graduate here once everything is validated.

---

## Stage 1 — Project Scaffolding & Local Dev Setup

**Goal:** Establish the monorepo structure, tooling, and basic connectivity between services.

### Tasks
- [ ] Create monorepo layout:
  ```
  /
  ├── backend/             # Python FastAPI
  ├── frontend/            # React
  ├── mcp_servers/
  │   └── calculator/      # Custom MCP server
  ├── load_balancer/       # Python load balancer
  ├── docker/              # Dockerfiles
  ├── docker-compose.yml
  ├── .env.example
  ├── simple_plan.md
  └── plan.md
  ```
- [ ] Initialize backend: FastAPI + `pyproject.toml` / `requirements.txt`
- [ ] Initialize frontend: Vite + React
- [ ] Set up PostgreSQL locally (via Docker Compose dev profile)
- [ ] Add `.env` with `DATABASE_URL`, `OPENAI_API_KEY`, etc.
- [ ] Backend health-check endpoint: `GET /health → { status: "ok" }`
- [ ] Frontend renders a placeholder page and calls `/health` on load

### Test Criteria
- `docker-compose up` starts PostgreSQL
- Backend server starts and returns 200 on `GET /health`
- Frontend loads in browser and displays a success ping from backend

---

## Stage 2 — User Authentication & Session Management

**Goal:** Multi-user support with registration, login, and JWT-based sessions.

### Tasks
- [ ] PostgreSQL schema: `users` table (`id`, `email`, `hashed_password`, `created_at`)
- [ ] `POST /auth/register` — create user, hash password with bcrypt
- [ ] `POST /auth/login` — verify credentials, return JWT access token
- [ ] JWT middleware: protect all non-auth routes
- [ ] Frontend: Register page, Login page, token stored in `httpOnly` cookie
- [ ] Frontend: Redirect unauthenticated users to login

### Test Criteria
- Can register a new user via API
- Can log in and receive a valid JWT
- Protected routes return 401 without token
- Frontend registration and login flows work end-to-end

---

## Stage 3 — Chat Thread Management (No Agent Yet)

**Goal:** New chat and resume chat backed by PostgreSQL, per-user isolated.

### Tasks
- [ ] PostgreSQL schema:
  - `threads (id UUID PK, user_id UUID FK, title TEXT, created_at, updated_at)`
  - `messages (id UUID PK, thread_id UUID FK, role TEXT, content TEXT, media_refs JSONB, created_at)`
- [ ] `POST /threads` — create a new thread (scoped to authenticated user)
- [ ] `GET /threads` — list threads for authenticated user only
- [ ] `GET /threads/:id/messages` — load full message history (auth check: must own thread)
- [ ] `POST /threads/:id/messages` — save a user message, echo a placeholder assistant reply
- [ ] Frontend: sidebar with thread list, new chat button, chat window with message history
- [ ] Frontend: resume chat by clicking a thread from the sidebar

### Test Criteria
- Create a new thread, send messages, refresh — history persists
- Multiple users have completely isolated thread lists
- Resuming a thread restores full message history
- User A cannot access User B's threads (403 response)

---

## Stage 4 — LLM Integration & Real-Time Streaming

**Goal:** Replace the echo backend with `gpt-5.4-nano` responses streamed token-by-token to the UI.

### Tasks
- [ ] Install OpenAI Python SDK
- [ ] `POST /threads/:id/chat` — streaming endpoint using **Server-Sent Events (SSE)**
  - Calls `gpt-5.4-nano` with the thread's message history as context
  - Streams each token as an SSE event: `data: {"token": "..."}`
  - On completion, persists the full assistant message to PostgreSQL
- [ ] Frontend: consume SSE stream and append tokens to the message bubble in real time
- [ ] Show a typing indicator while stream is in progress
- [ ] Handle stream errors gracefully (show error message in UI)

### Test Criteria
- Sending a message streams the response token-by-token visibly in the UI
- Full response is saved to the DB after streaming completes
- Refreshing the page shows the complete saved response
- Network interruption shows a user-friendly error

---

## Stage 5 — ReAct Agent with LangGraph

**Goal:** Replace the direct LLM call with a LangGraph-powered ReAct agent with retry logic.

### Tasks
- [ ] Install `langchain`, `langgraph`, `langchain-openai`
- [ ] Define the LangGraph agent graph:
  - Nodes: `plan`, `act` (tool call), `observe`, `respond`
  - Edges: conditional routing based on whether tool use is needed
- [ ] Implement **Planner sub-agent**:
  - Takes the user query as input
  - Outputs `{ max_retries: int, complexity: "low" | "medium" | "high" }`
  - High complexity → more retries allowed; low complexity → minimal retries
- [ ] Implement **Tool Call Deduplication**:
  - Maintain `call_log: List[{tool, params, count}]` in agent state
  - Before each tool call, check if `(tool, params)` already exists in `call_log`
  - If count ≥ 2, skip the tool call and proceed to respond with current information
  - Log a `"max_retries_reached"` event for observability
- [ ] Wire the agent into the SSE streaming endpoint
  - Intermediate steps (tool invocations, observations) emitted as SSE events
  - Final answer streamed as tokens

### Test Criteria
- Agent performs multi-step reasoning for a complex query
- Planner correctly assigns retry limits based on query complexity
- Sending the same tool call twice triggers deduplication on the third attempt
- Intermediate reasoning steps appear in the UI stream

---

## Stage 6 — Built-In Tool Integration

**Goal:** Give the agent access to File System, Google Search, and Document Ingestion tools.

### Tasks

#### 6a — File System Tool
- [ ] Tool: `read_file(path)`, `write_file(path, content)`, `list_directory(path)`
- [ ] Scope paths to a sandboxed **per-user directory** to prevent traversal attacks
- [ ] Register tool with the LangGraph agent

#### 6b — Google Search Tool
- [ ] Integrate Google Custom Search API (or SerpAPI)
- [ ] Tool: `google_search(query) → List[{title, url, snippet}]`
- [ ] Register tool with the LangGraph agent

#### 6c — Document Ingestion Tool
- [ ] `POST /documents/ingest` — accepts file upload (PDF, TXT, DOCX)
- [ ] Parsed, chunked, and embedded immediately (see Stage 9)
- [ ] Tool: `ingest_document(file_path)` — triggers ingestion pipeline and confirms success
- [ ] Register tool with the LangGraph agent

### Test Criteria
- Agent can read and write files within the per-user sandbox
- Agent can search Google and include results in its reasoning
- Agent can trigger document ingestion via tool call
- Path traversal outside sandbox is rejected with an error

---

## Stage 7 — Custom MCP Server: Calculator

**Goal:** Build a first-party MCP server from scratch as a learning exercise and connect it to the agent.

### Tasks
- [ ] Create `mcp_servers/calculator/server.py` using the MCP Python SDK (`mcp`)
- [ ] Expose the following tools over **`stdio` transport**:

  | Tool | Signature | Notes |
  |---|---|---|
  | `add` | `(a: float, b: float) → float` | |
  | `subtract` | `(a: float, b: float) → float` | |
  | `multiply` | `(a: float, b: float) → float` | |
  | `divide` | `(a: float, b: float) → float` | Returns structured error on divide-by-zero |
  | `evaluate` | `(expression: str) → float` | Safe eval via `ast` — no `exec`, no builtins |

- [ ] Add `mcp_servers/calculator/README.md` documenting tools and how to run standalone
- [ ] Start the calculator MCP server as a **subprocess** at backend startup
- [ ] Connect via `langchain-mcp-adapters`; add its tools to the agent tool registry
- [ ] Register as a **default MCP server** for all users (no manual setup required)

### Test Criteria
- `python mcp_servers/calculator/server.py` starts cleanly and responds to MCP tool calls
- `divide(5, 0)` returns a structured error, not a crash or exception
- `evaluate("2 ** 10 + 5 * 3")` returns `1039.0`
- `evaluate("__import__('os').system('ls')")` is rejected (no code injection)
- Ask agent "what is 1234 × 5678?" → agent calls `multiply` via MCP and returns the correct answer
- Ask agent "what is (100 / 4) + 37?" → agent calls `evaluate` via MCP

---

## Stage 8 — Dynamic MCP Server Registration (Per-User)

**Goal:** Each user can register any MCP-compatible server; the agent loads its tools automatically at session start.

### Tasks
- [ ] PostgreSQL schema:
  ```sql
  mcp_servers (
    id          UUID PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    name        TEXT NOT NULL,
    transport   TEXT NOT NULL,   -- 'stdio' or 'sse'
    config      JSONB NOT NULL,  -- {"command": "...", "args": [...]} or {"url": "..."}
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP
  )
  ```
- [ ] `POST /mcp-servers` — register a new MCP server for the authenticated user
- [ ] `GET /mcp-servers` — list the user's registered servers
- [ ] `PATCH /mcp-servers/:id` — enable or disable a server
- [ ] `DELETE /mcp-servers/:id` — remove a server
- [ ] At agent session start: load all **enabled** MCP servers for the user from DB, connect to each, discover tools, merge into the agent's tool registry dynamically
- [ ] MCP server connections are cached per session and torn down on session end
- [ ] Frontend: **MCP Servers** settings panel
  - List registered servers with enabled/disabled toggle
  - "Add Server" form: name, transport type, command+args (stdio) or URL (sse)
  - Delete button per entry

### Test Criteria
- Register a new MCP server via the UI
- Start a new chat — agent lists the new server's tools as available
- Disable the server — new chats no longer include its tools
- Delete the server — removed from list; not loaded in subsequent sessions
- User A's MCP servers are not visible or loadable by User B
- Registering an unreachable server config returns a clear validation error at connection time

---

## Stage 9 — Document Ingestion & RAG

**Goal:** Per-user vector store with semantic search as a callable agent tool.

### Tasks
- [ ] Install `sentence-transformers`, vector store library (pgvector or ChromaDB)
- [ ] Embedding model: load `all-MiniLM-L6-v2` locally at startup
- [ ] Ingestion pipeline:
  - Parse document (PyMuPDF for PDF, python-docx for DOCX, etc.)
  - Split into chunks (512 tokens, 50-token overlap)
  - Embed each chunk with `all-MiniLM-L6-v2`
  - Store vectors in the **user's namespace**: `{ user_id, chunk_text, embedding, doc_id, metadata }`
- [ ] PostgreSQL schema: `documents (id, user_id, filename, status, created_at)`
- [ ] RAG Tool: `rag_query(query, user_id) → List[{chunk, score, source}]`
  - Embed the query
  - Top-K semantic search scoped to `user_id` namespace
  - Return ranked chunks to the agent for synthesis
- [ ] Register RAG tool with the LangGraph agent
- [ ] Frontend: document upload UI with per-document ingestion status

### Test Criteria
- Upload a PDF; status transitions `processing → ready`
- RAG query returns relevant chunks from the uploaded document
- User A cannot retrieve documents belonging to User B
- Agent uses RAG tool to answer a question grounded in an uploaded document

---

## Stage 10 — Memory (Short-Term & Long-Term)

**Goal:** The agent remembers within a session and across sessions, per user.

### Tasks

#### 10a — Short-Term Memory (In-Session)
- [ ] Use **LangGraph PostgreSQL checkpointer** to persist full agent state per `thread_id`
- [ ] On each turn, restore the graph state from the checkpointer before running the agent
- [ ] Agent has access to full current-session message history in its context

#### 10b — Long-Term Memory (Cross-Session)
- [ ] PostgreSQL schema: `memories (id, user_id, summary, created_at, updated_at)`
- [ ] At end of each session (or when history exceeds token threshold): summarize key facts with `gpt-5.4-nano` → upsert into `memories` for the user
- [ ] At the start of every new thread: fetch latest memory summary for the user and inject into the agent system prompt
- [ ] Memory update tool: agent can call `update_memory(fact)` mid-conversation to store an explicit fact

### Test Criteria
- Within a session: agent recalls earlier messages correctly
- Resume a thread: full history restores correctly
- Start a new thread: agent references facts from a previous session via long-term memory
- Explicit memory update via tool is retrievable in the next new thread

---

## Stage 11 — Guardrails

**Goal:** Block harmful inputs before they reach the agent; filter harmful outputs before they reach the user.

### Approach: Hybrid (3-layer)

| Layer | Tool | Catches | Applied To |
|---|---|---|---|
| 1 | OpenAI Moderation API | Hate, harassment, self-harm, sexual content, violence | Input + Output |
| 2 | `gpt-5.4-nano` LLM classifier | Prompt injection, jailbreaks | Input only (escalated from layer 1) |
| 3 | Regex validators | PII leakage (email, phone, SSN) | Output only |

### Tasks
- [ ] **Input Guardrail** (runs after user submits, before agent):
  - Call `openai.moderations.create()` on the user message
  - If flagged → emit SSE refusal event, do not invoke agent, log to `guardrail_logs`
  - If moderation passes but message matches injection patterns (e.g. `"ignore previous instructions"`, `"disregard your"`, `"you are now"`) → escalate to `gpt-5.4-nano` classifier
  - If classifier flags it → emit SSE refusal event, do not invoke agent, log to `guardrail_logs`
- [ ] **Output Guardrail** (runs after agent responds, before final SSE stream):
  - Call `openai.moderations.create()` on the full response
  - If flagged → replace with a safe fallback message, log to `guardrail_logs`
  - Run regex scan for PII patterns on both the user's input and the agent's output (email, phone, SSN)
  - **Delta check**: subtract PII found in the user's input from PII found in the output — only the remainder is hallucinated/leaked
  - If hallucinated PII found → redact those matches before sending to frontend, log to `guardrail_logs`; user-provided PII is left intact
- [ ] PostgreSQL schema:
  ```sql
  guardrail_logs (
    id            UUID PRIMARY KEY,
    user_id       UUID REFERENCES users(id),
    thread_id     UUID REFERENCES threads(id),
    direction     TEXT,   -- 'input' or 'output'
    layer         TEXT,   -- 'moderation', 'llm_classifier', 'regex'
    flagged_content TEXT,
    reason        TEXT,
    created_at    TIMESTAMP
  )
  ```

### Test Criteria
- Known harmful content (`"how to make a weapon"`) → blocked by Moderation API; agent not called
- Known prompt injection (`"Ignore all previous instructions..."`) → escalated to LLM classifier; blocked
- Clean message → passes through; no added latency > 200ms
- Output containing an email address → email is redacted before reaching the UI
- Guardrail log records correct `user_id`, `direction`, and `layer` for every flagged event

---

## Stage 12 — Observability with Arize Phoenix

**Goal:** Full tracing of every LLM call, tool call, and agent step; automatic quality evaluations.

### Tasks
- [ ] Install `arize-phoenix` and `opentelemetry` instrumentation
- [ ] Auto-instrument LangChain/LangGraph with Phoenix's OpenTelemetry exporter
- [ ] Each agent run produces a **trace** with spans for:
  - Planner call (complexity, max_retries assigned)
  - Each tool call — including MCP tool calls (tool name, server, inputs, outputs, latency)
  - LLM calls (prompt, completion, token count, model)
  - Guardrail checks (direction, pass/fail, latency)
- [ ] Async **evaluators** (run post-response, do not block the stream):

  | Evaluator | Trigger | Method |
  |---|---|---|
  | Answer Accuracy | Every turn | LLM-as-judge |
  | Hallucination Detection | RAG turns only | Claim vs. retrieved chunks |
  | Groundedness | RAG turns only | Answer vs. source overlap |

- [ ] Evaluation scores logged back to Phoenix as span attributes
- [ ] Phoenix dashboard running locally at `http://localhost:6006`

### Test Criteria
- Every chat turn produces a visible trace in the Phoenix UI
- MCP tool call spans appear under the agent trace
- RAG query traces show retrieval spans and evaluation scores
- A known hallucination scores low groundedness
- Guardrail spans show latency and pass/fail result

---

## Stage 13 — Image Input

**Goal:** Users can attach images to messages; the agent reasons over them using vision.

### Tasks
- [ ] Frontend: image attach button in chat input, thumbnail preview before send
- [ ] Backend: `POST /threads/:id/chat` accepts `multipart/form-data` with optional image
- [ ] Image saved to local volume (or object storage); path stored in `messages.media_refs`
- [ ] Image passed to `gpt-5.4-nano` vision endpoint as base64 alongside the text prompt
- [ ] Guardrails applied to image content description extracted by the model

### Test Criteria
- Upload an image with a question about it; agent answers correctly using visual content
- Image messages persist in thread history and are visible on resume
- Guardrails intercept a harmful image description before it reaches the user

---

## Stage 14 — Dockerization

**Goal:** All services run via Docker Compose with no local Python/Node dependencies needed.

### Tasks
- [ ] `docker/Dockerfile.backend` — multi-stage Python build; embeds `mcp_servers/calculator/` inside the image
- [ ] `docker/Dockerfile.frontend` — Node build stage → Nginx serve stage
- [ ] `docker-compose.yml` services:
  - `postgres` — PostgreSQL 16, persistent named volume
  - `backend` — FastAPI (multiple replicas supported via `--scale`)
  - `frontend` — React/Nginx, proxies `/api` to load balancer
  - `phoenix` — Arize Phoenix (`arizephoenix/phoenix`)
  - `vector_store` — ChromaDB (if run as separate service)
- [ ] Calculator MCP server started as a subprocess inside the backend container at startup
- [ ] Environment variables via `.env` file; no secrets baked into images
- [ ] Health checks on `backend` and `postgres`
- [ ] Named volumes for PostgreSQL data, uploaded documents, and media files

### Test Criteria
- `docker-compose up --build` starts all services cleanly
- Full chat flow works end-to-end via Docker
- Stopping and restarting preserves all data (volumes intact)
- `docker-compose up --scale backend=3` runs 3 backend instances without conflict
- Calculator MCP server starts automatically inside the backend container

---

## Stage 15 — Python Load Balancer with Auto-Scaling

**Goal:** A Python process routes requests across backend instances and auto-scales based on queue depth.

### Tasks
- [ ] Load balancer in `load_balancer/` as a standalone Python async process (e.g., `aiohttp`)
- [ ] Routing strategy: **least-connections** (route to instance with fewest active requests)
- [ ] Health-check loop: poll `/health` on each backend instance every 5 seconds; remove unhealthy instances from the rotation
- [ ] Auto-scaling logic:
  - Monitor active request queue length across all instances
  - Scale **up**: queue > threshold and instance count < 4 → `docker-compose up --scale backend=N+1`
  - Scale **down**: queue consistently low and instance count > 1 → `docker-compose up --scale backend=N-1`
  - Cooldown: 60 seconds between scaling events to prevent flapping
- [ ] `GET /lb/status` → current instance count, queue lengths, routing table
- [ ] All frontend and external traffic enters through the load balancer only

### Test Criteria
- Load balancer routes requests across 2+ backend instances (verify via instance logs)
- Killing one backend instance: stops receiving traffic within 10 seconds
- 20 simultaneous users → scale-up to ≥ 2 instances triggered
- Load drops → scales back to 1 instance after cooldown
- `GET /lb/status` reflects accurate real-time state

---

## Stage 16 — Production Hardening & End-to-End Validation

**Goal:** Harden the system for production readiness and run a full smoke test across all features.

### Tasks
- [ ] **Structured logging**: JSON logs with `request_id`, `user_id`, `thread_id`, `duration_ms` on every request
- [ ] **Rate limiting**: per-user request rate limit on the load balancer (e.g., 60 req/min)
- [ ] **Error handling**: global exception handler returns structured `{ error, code }` responses; no stack traces in production
- [ ] **Database connection pooling**: configure `asyncpg` pool size per backend instance
- [ ] **CORS**: restrict to known frontend origin in production
- [ ] **Secrets management**: all secrets via environment variables; `.env.example` documents all required keys
- [ ] **`pytest` test suite** covering at minimum:
  - Auth endpoints (register, login, token expiry)
  - Thread create/resume with user isolation
  - Tool call deduplication logic
  - Calculator MCP server tool correctness
  - MCP server registration and dynamic tool loading
  - Guardrail pass/block behavior (input + output)
- [ ] **End-to-end smoke test**:
  1. Register two users → login as each
  2. Start new chat → send a message → verify streaming
  3. Ask a math question → verify agent calls calculator MCP server
  4. Register a third-party MCP server via UI → verify agent uses its tools
  5. Upload a document → ask a question about it → verify RAG
  6. Send an image → verify vision response
  7. Send audio → verify transcript and response
  8. Check Phoenix for traces on all of the above turns
  9. Verify long-term memory persists across a new thread
  10. Trigger guardrail with a known bad prompt → verify block
  11. Verify User A cannot access User B's threads, documents, or MCP servers
  12. Scale to 2 instances under load → verify load balancer distributes correctly

### Test Criteria
- All 12 smoke test steps pass for both users
- No unhandled exceptions under normal usage
- Phoenix shows complete traces for all steps including MCP spans
- Load balancer scales correctly under smoke test concurrency

---

## Dependency Graph (Build Order)

```
Stage 1  Scaffolding
  └── Stage 2  Auth (multi-user)
        └── Stage 3  Chat Threads (per-user isolation)
              ├── Stage 4  LLM + Streaming
              │     └── Stage 5  ReAct Agent (LangGraph + planner + dedup)
              │           ├── Stage 6  Built-In Tools (FS + Search)
              │           ├── Stage 7  Calculator MCP Server  ←─ build & test standalone first
              │           │     └── Stage 8  Dynamic MCP Registration (per-user)
              │           ├── Stage 9  Document Ingestion + RAG (per-user)
              │           ├── Stage 10 Memory (short + long term, per-user)
              │           └── Stage 11 Guardrails
              │                 └── Stage 12 Observability (Phoenix + MCP spans)
              │                       └── Stage 13 Multi-Modal (image + audio)
              │                             └── Stage 14 Docker
              │                                   └── Stage 15 Load Balancer
              │                                         └── Stage 16 Hardening
```

---

## Key Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM and Whisper calls |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Secret for signing JWT tokens |
| `GOOGLE_SEARCH_API_KEY` | Google Custom Search or SerpAPI key |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search Engine ID (if using Google CSE) |
| `PHOENIX_HOST` | Arize Phoenix server host (default: `localhost`) |
| `PHOENIX_PORT` | Arize Phoenix port (default: `6006`) |
| `VECTOR_STORE_PATH` | Local path or connection string for vector store |
| `MEDIA_STORAGE_PATH` | Local volume path for uploaded images and audio |
| `WORKSPACE_DIR` | Sandboxed root directory for the File System tool |
| `MCP_CALCULATOR_CMD` | Command to start the calculator MCP server (default: `python mcp_servers/calculator/server.py`) |
| `LB_SCALE_UP_THRESHOLD` | Queue length to trigger scale-up (default: `5`) |
| `LB_SCALE_DOWN_THRESHOLD` | Queue length to trigger scale-down (default: `1`) |
| `LB_COOLDOWN_SECONDS` | Cooldown between scaling events (default: `60`) |
