# Full-Stack Production-Ready Agentic Chatbot

## Overview

A production-grade, multi-user agentic chatbot built on the ReAct (Reasoning + Acting) framework. It supports tool use, RAG-based document querying, short and long-term memory, observability, guardrails, and horizontal scaling via Dockerized services with an auto-scaling load balancer.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangChain + LangGraph (ReAct) |
| LLM | `gpt-5.4-nano` (OpenAI) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) |
| Frontend | React |
| Backend | Python (FastAPI or equivalent) |
| Database | PostgreSQL |
| Vector Store | Per-user vector store (e.g., pgvector or Chroma) |
| Observability | Arize Phoenix (tracing + evaluations) |
| Guardrails | Input/output safety layer |
| Containerization | Docker |
| Load Balancing | Custom Python load balancer |

---

## Core Features

### 1. Agentic ReAct Framework
- The agent reasons step-by-step using the ReAct loop: **Thought → Action → Observation → Repeat**.
- Built with LangGraph to define stateful, cyclical agent graphs.
- A **planner sub-agent** evaluates query complexity at runtime and dynamically decides the maximum number of retries allowed for the current task.

### 2. Tool Use
The agent has access to the following tools:

| Tool | Description |
|---|---|
| File System | Read/write/list local files |
| Google Search | Real-time web search for current information |
| Document Ingestion | Upload and parse documents (PDF, etc.) into the vector store |
| RAG Query | Retrieve and synthesize answers from ingested documents scoped to the user's vector store |

#### Tool Call Deduplication & Retry Policy
- Before invoking any tool, the agent checks whether the **same tool with identical parameters** was already called in the current run.
- A duplicate tool call may be retried **at most 2 times**.
- After 2 retries of the same tool call, the agent moves forward and generates a best-effort answer based on what it already has.

### 3. Document Ingestion & RAG
- When a user ingests a document, its content is chunked and embedded using `all-MiniLM-L6-v2`.
- Vectors are stored in a **per-user namespace** within the vector store, keyed by `user_id`.
- The RAG tool performs semantic retrieval scoped to the authenticated user's documents and synthesizes a grounded answer.

---

## Memory

| Type | Storage | Scope |
|---|---|---|
| Short-Term | In-session thread state (LangGraph checkpointer) | Current conversation |
| Long-Term | PostgreSQL (user-scoped memory table) | Persists across sessions |

- Both memory types are queryable by the agent during reasoning.
- Long-term memory is summarized and updated at the end of relevant sessions.

---

## Chat Management

- **New Chat**: Starts a fresh thread with a new `thread_id` stored in PostgreSQL.
- **Resume Chat**: Loads a previous thread from PostgreSQL by `thread_id`, restoring full message history and agent state.
- All threads are tied to a `user_id` for isolation and access control.

---

## User Management & Sessions

- Multi-user support with **registration and authentication**.
- Each user gets isolated: chat threads, memory, and vector store namespace.
- Session tokens manage authentication state across requests.

---

## Observability — Arize Phoenix

All LLM calls and agent steps are traced via **Arize Phoenix**.

### Metrics Tracked

| Metric | Description |
|---|---|
| Answer Accuracy | How factually correct the response is |
| Hallucination Detection | Flags responses not grounded in retrieved context |
| Groundedness | Measures how well the answer is supported by source documents |

- Evaluations run post-response and log results to Phoenix for dashboard monitoring.
- Traces capture: tool calls, retrieval steps, LLM input/output, latency, and token usage.

---

## Guardrails

A safety layer is applied at two checkpoints:

1. **Input Guardrail** — Runs after the user submits a query. Blocks prompt injection attempts, jailbreaks, and policy-violating inputs before they reach the agent.
2. **Output Guardrail** — Runs before the response is shown to the user. Filters harmful, toxic, or policy-violating content from the agent's output.

---

## Infrastructure

### Dockerization
- Both the **React frontend** and **Python backend** are containerized as separate Docker images.
- Multiple backend instances can run simultaneously to handle concurrent users.

### Python Load Balancer
- A custom Python load balancer routes incoming requests to available backend instances.
- **Auto-scaling policy**:
  - Minimum instances: **1**
  - Maximum instances: **4**
  - Scales up/down dynamically based on the active user queue length.
- Uses a round-robin or least-connections strategy across healthy instances.

---

## Frontend — React

- Clean chat UI supporting new and resumed conversations.
- Document upload interface for triggering ingestion.
- Session-aware: shows only the authenticated user's threads and history.

---

## LLM & Embedding Configuration

- **LLM**: All reasoning, generation, and tool-calling use `gpt-5.4-nano` via the OpenAI API.
- **Embeddings**: Document chunking and vector creation use `all-MiniLM-L6-v2` from `sentence-transformers` (local inference, no API cost).

---

## Real-Time Streaming

- LLM responses are streamed token-by-token to the frontend using **Server-Sent Events (SSE)**.
- The React UI renders tokens as they arrive, giving immediate feedback without waiting for the full response.
- Tool call steps and intermediate reasoning are also streamed as structured events so the user can see the agent's progress in real time.
- Streaming is scoped per `thread_id` and authenticated session to prevent cross-user leakage.

---

## Multi-Modal Inputs

- Users can upload **images** alongside text queries; the agent uses vision capabilities of `gpt-5.4-nano` to reason over image content.
- **Audio** inputs are transcribed to text via OpenAI Whisper before being passed to the agent.
- Multi-modal messages are stored as part of the thread history in PostgreSQL with references to the original media (stored in object storage or local volume).
- RAG and guardrails apply equally to content extracted from images and audio transcripts.

---

## MCP Server Integration

### Dynamic User-Added MCP Servers
- Users can register any MCP-compatible server by providing a name, transport type (`stdio` or `sse`), and connection config (command + args, or URL).
- Registered MCP servers are stored in PostgreSQL and loaded into the agent's tool registry at session start.
- The agent automatically discovers and calls tools exposed by the registered MCP server — no hardcoded tool definitions needed.
- Users can enable/disable or remove MCP servers from the UI at any time.

### Built-In Custom MCP Server — Calculator
- A first-party MCP server built for this project as a learning exercise.
- Exposes the following tools over `stdio` transport:
  - `add(a, b)` — addition
  - `subtract(a, b)` — subtraction
  - `multiply(a, b)` — multiplication
  - `divide(a, b)` — division (with divide-by-zero handling)
  - `evaluate(expression)` — evaluate a math expression string safely
- When the user asks anything involving calculation, the agent automatically routes to the calculator MCP server.
- Registered as a default MCP server for all users (no manual setup required).

---

## Out of Scope (for now)

- Fine-tuning or custom model training.
- Mobile app.
