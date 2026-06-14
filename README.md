# Full-Stack Agentic Chatbot

A production-grade agentic chatbot built on the ReAct (Reasoning + Acting) framework. It supports tool use, RAG-based document querying, short and long-term memory, observability, guardrails, and real-time streaming.

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | LangChain + LangGraph (ReAct) |
| LLM | `gpt-4o-mini` (OpenAI) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers, local) |
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Vector Store | ChromaDB (local) |
| Observability | Arize Phoenix |
| Containerization | Docker |

## Project Structure

```
full_stack_chatbot/
├── backend/
│   ├── main.py              # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       └── App.jsx
├── mcp_servers/
│   └── calculator/
│       └── server.py        # Custom MCP server (Stage 6)
├── docker-compose.yml       # PostgreSQL service
├── .env                     # Secrets (never commit)
├── .env.example             # Template for .env
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

## Stage 1 — Running Locally

### Prerequisites

1. **Node.js** — needed for the frontend
   ```bash
   brew install node
   # or download from https://nodejs.org
   ```

2. **Docker Desktop** — needed for PostgreSQL
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

Open [http://localhost:5173](http://localhost:5173) — you should see **Backend status: ok**.

---

## Build Stages

| Stage | Feature |
|---|---|
| 1 | Project scaffolding & local dev setup |
| 2 | Chat thread management (PostgreSQL) |
| 3 | LLM integration & real-time streaming |
| 4 | ReAct agent with LangGraph |
| 5 | Built-in tools (File System + Google Search) |
| 6 | Custom MCP server (Calculator) |
| 7 | Dynamic MCP server registration |
| 8 | Document ingestion & RAG |
| 9 | Memory (short-term & long-term) |
| 10 | Image input |
| 11 | Guardrails (moderation + PII filtering) |
| 12 | Observability with Arize Phoenix |
| 13 | Docker (full single-instance deployment) |
