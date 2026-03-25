# Agentic Developer Environment

AI-powered multi-agent coding assistant that plans tasks, generates code, reviews it, and executes tests.

## Architecture

**Agents** (orchestrated via LangGraph):
- **Context/RAG Agent** — retrieves relevant codebase context from FAISS
- **Planner Agent** — decomposes tasks into ordered steps
- **Codegen Agent** — generates code for each step
- **Review Agent** — reviews code for correctness, security, and style
- **Execution Agent** — runs generated code and tests locally

**Stack**: Python · FastAPI · LangGraph · Azure OpenAI · FAISS · PostgreSQL · Redis · LangSmith · Next.js

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for PostgreSQL + Redis)

### Setup

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start infrastructure
docker compose up -d

# 4. Run database migrations
alembic upgrade head

# 5. Start the API server
uvicorn backend.main:app --reload
```

### Verify
- Health check: `GET http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`

## Project Structure

```
backend/
  main.py              → FastAPI entry point
  config.py            → Pydantic Settings (.env loader)
  api/                 → Routes and dependencies
  database/            → SQLAlchemy models, engine, Alembic migrations
  models/              → Pydantic schemas
  services/            → LLM client, cache, embeddings
  agents/              → LangGraph agent implementations
  graph/               → LangGraph workflow definition
  vectordb/            → FAISS index management
  cli/                 → Typer CLI commands
  utils/               → Logging, parsing, sandbox
frontend/              → Next.js web UI (Phase 6)
```
