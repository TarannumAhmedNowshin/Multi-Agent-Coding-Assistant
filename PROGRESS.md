# Agentic Developer Environment - Progress Tracker

**Last Updated:** March 25, 2026  
**Current Phase:** Phase 1 Complete ✅ → Ready for Phase 2

---

## Project Overview

**Goal:** Build a multi-agent AI coding assistant that takes developer tasks, plans them, generates code, reviews it, and executes tests—all orchestrated by LangGraph.

**Core Value Proposition:**
- Developer gives a task: "Add JWT authentication to the user service"
- System breaks it into steps, generates code, reviews for security/quality, runs tests
- All agent interactions traced in LangSmith for observability
- RAG-powered context retrieval from indexed codebases via FAISS

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Orchestration** | LangGraph (agent workflow state machine) |
| **API Framework** | FastAPI (async, with WebSocket support) |
| **LLM Provider** | Azure OpenAI (GPT-4o + text-embedding-3-small) |
| **Vector Store** | FAISS (code similarity search) |
| **Database** | PostgreSQL 16 (async SQLAlchemy + Alembic) |
| **Cache** | Redis 7 (LLM response caching) |
| **Observability** | LangSmith (traces, metrics, debugging) |
| **CLI** | Typer + Rich (developer interface) |
| **Frontend** | Next.js 14+ (App Router, TypeScript, Tailwind) |
| **Containerization** | Docker Compose (PostgreSQL + Redis) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ User Input: CLI / REST API / Next.js Frontend                  │
│ Task: "Add authentication to user service"                      │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ LangGraph State Machine (backend/graph/workflow.py)           │
│ - Manages agent orchestration                                 │
│ - Maintains shared state (task, steps, context, code, errors) │
│ - Conditional routing (retry on failure, max 3 attempts)      │
└────────────────────────────┬───────────────────────────────────┘
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
   ┌──────────────────────┐    ┌─────────────────────┐
   │ Context/RAG Agent    │←───│ FAISS Vector Store  │
   │ (context_agent.py)   │    │ (vectordb/)         │
   │ Retrieves relevant   │    │ - Indexed codebase  │
   │ code chunks          │    │ - Similarity search │
   └──────────┬───────────┘    └─────────────────────┘
              ↓
   ┌──────────────────────────────────────────────────┐
   │ Planner Agent (planner_agent.py)                 │
   │ Decomposes task into ordered steps with deps     │
   │ Output: [Step 1, Step 2, Step 3, ...]           │
   └──────────┬───────────────────────────────────────┘
              ↓ (for each step, iterate)
   ┌──────────────────────────────────────────────────┐
   │ Codegen Agent (codegen_agent.py)                 │
   │ Generates code for current step                  │
   │ Input: step description + context + prior steps  │
   └──────────┬───────────────────────────────────────┘
              ↓
   ┌──────────────────────────────────────────────────┐
   │ Review Agent (review_agent.py)                   │
   │ Reviews for: correctness, security, style        │
   │ Output: PASS → continue | FAIL → retry codegen   │
   └──────────┬───────────────────────────────────────┘
              ↓ (if PASS)
   ┌──────────────────────────────────────────────────┐
   │ Execution Agent (execution_agent.py)             │
   │ Runs code/tests via subprocess                   │
   │ Output: SUCCESS → next step | FAIL → retry       │
   └──────────┬───────────────────────────────────────┘
              ↓
   ┌──────────────────────────────────────────────────┐
   │ Result Storage                                   │
   │ - PostgreSQL: tasks, steps, code_artifacts, logs │
   │ - LangSmith: full trace with tokens/latency      │
   │ - CLI/API: formatted output to user              │
   └──────────────────────────────────────────────────┘
```

---

## Database Schema (ORM Models)

```sql
projects
  ├─ id (UUID, PK)
  ├─ name (varchar)
  ├─ root_path (varchar)
  ├─ description (text, nullable)
  ├─ indexed_at (timestamp, nullable)
  └─ created_at (timestamp)

tasks
  ├─ id (UUID, PK)
  ├─ project_id (UUID, FK → projects.id, nullable)
  ├─ description (text)
  ├─ status (enum: pending, planning, in_progress, reviewing, completed, failed, cancelled)
  ├─ result_summary (text, nullable)
  ├─ total_tokens (integer)
  ├─ created_at (timestamp)
  └─ updated_at (timestamp)

steps
  ├─ id (UUID, PK)
  ├─ task_id (UUID, FK → tasks.id)
  ├─ order (integer)
  ├─ title (varchar)
  ├─ description (text)
  ├─ status (enum: pending, generating, reviewing, executing, passed, failed, skipped)
  ├─ retry_count (integer)
  └─ created_at (timestamp)

code_artifacts
  ├─ id (UUID, PK)
  ├─ step_id (UUID, FK → steps.id)
  ├─ file_path (varchar)
  ├─ content (text)
  ├─ language (varchar, nullable)
  ├─ version (integer)
  └─ created_at (timestamp)

agent_logs
  ├─ id (UUID, PK)
  ├─ task_id (UUID, FK → tasks.id)
  ├─ step_id (UUID, FK → steps.id, nullable)
  ├─ agent_type (enum: planner, codegen, review, execution, context)
  ├─ input_text (text, nullable)
  ├─ output_text (text, nullable)
  ├─ tokens_used (integer)
  ├─ duration_ms (integer)
  ├─ error (text, nullable)
  └─ created_at (timestamp)
```

---

## Current File Structure

```
AI_software_developer/
├── .env                              ✅ Environment variables (GITIGNORED)
├── .gitignore                        ✅ Comprehensive ignore patterns
├── .dockerignore                     ✅ Excludes secrets from Docker context
├── README.md                         ✅ Quick start guide
├── PROGRESS.md                       ✅ This file (context + progress)
├── requirements.txt                  ✅ All dependencies installed
├── docker-compose.yml                ✅ PostgreSQL + Redis services
├── alembic.ini                       ✅ Alembic configuration
│
├── backend/
│   ├── __init__.py                   ✅
│   ├── main.py                       ✅ FastAPI app with lifespan hooks
│   ├── config.py                     ✅ Pydantic Settings (loads .env)
│   │
│   ├── api/
│   │   ├── __init__.py               ✅
│   │   ├── dependencies.py           ✅ DB session, cache DI
│   │   └── routes/
│   │       ├── __init__.py           ✅
│   │       └── health.py             ✅ Health check endpoint
│   │
│   ├── database/
│   │   ├── __init__.py               ✅
│   │   ├── engine.py                 ✅ Async SQLAlchemy engine + session
│   │   ├── models.py                 ✅ 5 ORM models (Project, Task, Step, CodeArtifact, AgentLog)
│   │   └── migrations/
│   │       ├── env.py                ✅ Async Alembic environment
│   │       ├── script.py.mako        ✅ Migration template
│   │       └── versions/
│   │           └── d666bd3d40cc_initial_schema.py  ✅ Initial migration (applied)
│   │
│   ├── models/
│   │   ├── __init__.py               ✅
│   │   └── schemas.py                ✅ Pydantic request/response schemas
│   │
│   ├── services/
│   │   ├── __init__.py               ✅
│   │   ├── llm_client.py             ✅ Azure OpenAI wrapper (chat + retries)
│   │   └── cache_service.py          ✅ Redis caching (LLM responses)
│   │
│   ├── utils/
│   │   ├── __init__.py               ✅
│   │   └── logger.py                 ✅ Structured logging + LangSmith setup
│   │
│   ├── agents/                       ⏳ Phase 3
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── context_agent.py
│   │   ├── planner_agent.py
│   │   ├── codegen_agent.py
│   │   ├── review_agent.py
│   │   └── execution_agent.py
│   │
│   ├── graph/                        ⏳ Phase 3
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── workflow.py
│   │
│   ├── vectordb/                     ⏳ Phase 2
│   │   ├── __init__.py               ✅
│   │   ├── faiss_store.py
│   │   ├── indexer.py
│   │   └── retriever.py
│   │
│   └── cli/                          ⏳ Phase 4
│       ├── __init__.py
│       ├── main.py
│       └── commands/
│           ├── __init__.py
│           ├── index.py
│           ├── task.py
│           └── status.py
│
└── frontend/                         ⏳ Phase 6
    └── (Next.js app to be initialized)
```

---

## ✅ Phase 1: Foundation & Infrastructure (COMPLETED)

**Goal:** Set up project scaffolding, dependencies, database, services, and verify connectivity.

### What Was Built

| File | Purpose | Status |
|---|---|---|
| requirements.txt | 30 dependencies (FastAPI, LangGraph, FAISS, SQLAlchemy, Redis, Typer, etc.) | ✅ Installed |
| .env | Azure OpenAI keys, DB credentials, Redis URL, LangSmith config | ✅ Created (gitignored) |
| .gitignore | 350+ rules (secrets, .env*, IDE files, Python/Node artifacts) | ✅ Created |
| .dockerignore | Excludes secrets from Docker build context | ✅ Created |
| docker-compose.yml | PostgreSQL 16 + Redis 7 containers (reads from .env) | ✅ Running |
| alembic.ini | Database migration configuration | ✅ Created |
| backend/config.py | Pydantic Settings (loads .env, no hardcoded secrets) | ✅ Verified |
| backend/main.py | FastAPI app with lifespan hooks (Redis connect/disconnect) | ✅ Tested |
| backend/database/engine.py | Async SQLAlchemy engine + session factory | ✅ Working |
| backend/database/models.py | 5 ORM models (projects, tasks, steps, code_artifacts, agent_logs) | ✅ Migrated to DB |
| backend/database/migrations/env.py | Alembic async environment | ✅ Working |
| backend/services/llm_client.py | Azure OpenAI wrapper (chat completions, retry logic, token tracking) | ✅ Imports OK |
| backend/services/cache_service.py | Redis cache service (get, set, flush by namespace) | ✅ Imports OK |
| backend/api/routes/health.py | Health check endpoint (tests PostgreSQL + Redis) | ✅ Created |
| backend/api/dependencies.py | FastAPI dependency injection (DB session, cache) | ✅ Created |
| backend/models/schemas.py | Pydantic schemas (TaskCreate, TaskResponse, StepResponse, etc.) | ✅ Validated |
| backend/utils/logger.py | Structured logging + LangSmith tracing setup | ✅ Working |
| README.md | Quick start guide | ✅ Created |

### Verification Results

| Component | Test Command | Result |
|---|---|---|
| Config | `python -c "from backend.config import settings; print(settings.azure_openai_model)"` | `gpt-4o` ✅ |
| Models | `python -c "from backend.database.models import Base; print([t for t in Base.metadata.tables])"` | 5 tables ✅ |
| Services | `python -c "from backend.services.llm_client import LLMClient; from backend.services.cache_service import CacheService"` | Imports OK ✅ |
| FastAPI | `python -c "from backend.main import app; print(app.title)"` | `Agentic Developer API` ✅ |
| Docker | `docker ps` | PostgreSQL + Redis healthy ✅ |
| Database | `alembic upgrade head` | Migration applied ✅ |

### Security Audit ✅

- ✅ `.env` gitignored (all variants: `.env.*`, `.env-*`, `.env_*`)
- ✅ `.dockerignore` excludes `.env` and `**/*secret*`, `**/*key*`, `**/*token*`
- ✅ No hardcoded credentials in `config.py` (removed default DB password)
- ✅ `alembic.ini` references env.py for DB URL (no hardcoded password)
- ✅ `docker-compose.yml` reads credentials from `.env` via `${POSTGRES_PASSWORD}`
- ✅ All secrets isolated to `.env` file only

---

## ⏳ Phase 2: Vector Store & Codebase Indexing (NEXT)

**Goal:** Build FAISS-powered RAG system for codebase context retrieval.

### Files to Create

1. **backend/services/embedding_service.py**
   - Batch embedding generation via Azure OpenAI text-embedding-3-small
   - Handles chunking large inputs (max tokens per request)
   - Returns numpy arrays ready for FAISS

2. **backend/utils/file_parser.py**
   - Parse Python files (extract functions, classes, docstrings)
   - Parse JS/TS files (functions, classes, exports)
   - Use AST parsing (Python) and tree-sitter (JS/TS) if available
   - Return structured code chunks with metadata (file, line range, type)

3. **backend/utils/text_splitter.py**
   - Code-aware chunking (split by function/class boundaries)
   - Token-aware (respect embedding model's context window)
   - Overlap strategy (maintain context between chunks)

4. **backend/vectordb/faiss_store.py**
   - FAISS index wrapper (IndexFlatL2 or IndexIVFFlat for larger datasets)
   - Methods: `create_index()`, `add_vectors()`, `search()`, `save()`, `load()`
   - Metadata storage (map vector IDs to file paths + line ranges)

5. **backend/vectordb/indexer.py**
   - Walk directory tree, filter by file extensions
   - Parse each file → chunks
   - Generate embeddings → add to FAISS
   - Save index + metadata to disk
   - Update `projects.indexed_at` in DB

6. **backend/vectordb/retriever.py**
   - Query interface: natural language question → embeddings → FAISS search
   - Return top-k results with similarity scores
   - Format: `[{file_path, line_range, code_snippet, similarity_score}, ...]`

### Acceptance Criteria

- [ ] Index a sample Python project (e.g., 50 files, 5000 lines)
- [ ] Query: "authentication functions" → returns relevant code chunks
- [ ] Query: "database models" → returns ORM model definitions
- [ ] FAISS index persists to disk, reloads correctly
- [ ] Metadata maps vector IDs back to source files + line numbers

---

## ⏳ Phase 3: LangGraph Agent Core

**Goal:** Implement all 5 agents and wire them into a LangGraph state machine.

### Files to Create

1. **backend/graph/state.py**
   - TypedDict: `AgenticState` with fields:
     - `task_id`, `task_description`, `project_id`
     - `context` (retrieved code chunks)
     - `steps` (list of planned steps)
     - `current_step_index`
     - `code_artifacts` (generated code)
     - `review_feedback`, `execution_results`
     - `errors`, `iteration_count`

2. **backend/agents/base_agent.py**
   - Base class with: `llm_client`, `cache_service`, `logger`
   - Method: `run(state: AgenticState) -> AgenticState`
   - LangSmith tracing decorator

3. **backend/agents/context_agent.py**
   - Uses `retriever.search(task_description)` → top 10 chunks
   - Adds to `state["context"]`

4. **backend/agents/planner_agent.py**
   - Prompt: "Break this task into ordered steps"
   - LLM response → parse into list of steps
   - Store in `state["steps"]`

5. **backend/agents/codegen_agent.py**
   - Input: current step + context + prior code artifacts
   - Prompt: "Generate code for this step"
   - Store in `state["code_artifacts"]`

6. **backend/agents/review_agent.py**
   - Input: generated code
   - Checks: syntax, security (OWASP patterns), style
   - Output: `{"pass": bool, "feedback": str}`

7. **backend/agents/execution_agent.py**
   - Runs code via subprocess (local sandbox)
   - Captures stdout, stderr, exit code
   - Output: `{"success": bool, "output": str, "error": str}`

8. **backend/graph/nodes.py**
   - Wrapper functions for each agent (convert to LangGraph node signature)

9. **backend/graph/workflow.py**
   - Define LangGraph StateGraph
   - Nodes: context → planner → (codegen → review → execution) loop
   - Conditional edges:
     - Review PASS → execution
     - Review FAIL → codegen (with feedback)
     - Execution FAIL → codegen (with error context)
     - Max retries reached → end with failure
   - Save state to PostgreSQL after each step

### Acceptance Criteria

- [ ] Submit task: "Write a function to reverse a string"
- [ ] LangGraph executes: context → planner → codegen → review → execution
- [ ] LangSmith trace shows all agent calls, tokens, latency
- [ ] Task status updates in PostgreSQL (planning → in_progress → completed)
- [ ] Code artifacts stored in DB with version tracking

---

## ⏳ Phase 4: CLI Interface

**Goal:** Developer-friendly CLI for task management and indexing.

### Files to Create

1. **backend/cli/main.py**
   - Typer app with command groups: `index`, `task`, `status`

2. **backend/cli/commands/index.py**
   - `index <directory>` — index a codebase into FAISS
   - Progress bar (Rich) showing files processed

3. **backend/cli/commands/task.py**
   - `task run <description>` — submit a task
   - `task run --project <id> <description>` — scoped to indexed project
   - Live progress updates (agent status)

4. **backend/cli/commands/status.py**
   - `status <task_id>` — show task progress
   - Display: steps completed, current step, errors

5. Rich formatting
   - Syntax-highlighted code output
   - Progress bars, spinners
   - Color-coded status (green=pass, red=fail, yellow=warning)

### Acceptance Criteria

- [ ] `index ./my_project` → indexes codebase, saves to FAISS
- [ ] `task run "add logging to all API endpoints"` → starts task
- [ ] Real-time updates as agents execute
- [ ] `status <task_id>` → shows current progress
- [ ] Generated code displayed with syntax highlighting

---

## ⏳ Phase 5: REST API Layer

**Goal:** FastAPI endpoints for programmatic access and frontend integration.

### Endpoints to Create

1. **POST /tasks** — create a new task
2. **GET /tasks/{id}** — retrieve task details + steps
3. **GET /tasks/{id}/steps** — list all steps for a task
4. **GET /tasks** — list all tasks (with pagination)
5. **POST /index** — trigger codebase indexing
6. **GET /search** — vector search query (test endpoint)
7. **POST /tasks/{id}/cancel** — cancel a running task
8. **WebSocket /ws/tasks/{id}** — stream agent progress in real-time

### Enhancements

- CORS middleware (allow frontend origin)
- Request ID middleware (for tracing)
- Error handling (consistent JSON error responses)
- Rate limiting (via slowapi)

### Acceptance Criteria

- [ ] Swagger UI at `/docs` shows all endpoints
- [ ] POST /tasks → returns task_id, starts LangGraph workflow
- [ ] WebSocket streams agent updates (context retrieved, codegen started, etc.)
- [ ] GET /tasks/{id} returns full task + steps + code artifacts

---

## ⏳ Phase 6: Next.js Frontend

**Goal:** Web UI for task management and real-time monitoring.

### Features to Build

1. **Task Submission**
   - Chat-style interface (like ChatGPT)
   - Input: task description
   - Optional: select indexed project

2. **Real-Time Progress Panel**
   - WebSocket connection to `/ws/tasks/{id}`
   - Live updates: agent status, current step, tokens used
   - Progress bar (steps completed / total steps)

3. **Code Display**
   - Monaco editor or Prism.js for syntax highlighting
   - Show generated code artifacts
   - Diff view (before/after)

4. **Task History**
   - List all tasks with status
   - Filter by status, project, date
   - Search by description

5. **Project Management**
   - List indexed projects
   - Trigger re-indexing
   - View project metadata (last indexed, file count)

### Acceptance Criteria

- [ ] Submit task from browser → see real-time agent progress
- [ ] Code artifacts displayed with syntax highlighting
- [ ] Task history searchable and filterable
- [ ] WebSocket reconnects on disconnect

---

## ⏳ Phase 7: Hardening & Production Readiness (FUTURE)

### Enhancements

1. **Docker Sandboxed Execution**
   - Replace subprocess with Docker container execution
   - Security: isolated network, read-only mounts
   - Resource limits (CPU, memory)

2. **Authentication & Authorization**
   - JWT-based auth for API
   - Rate limiting per user
   - Role-based access (admin, user)

3. **Retry & Circuit Breaker**
   - Exponential backoff for LLM calls
   - Circuit breaker pattern (fail fast on repeated errors)
   - Graceful degradation

4. **Performance Tuning**
   - Connection pooling (PostgreSQL, Redis)
   - Async everywhere (no blocking calls)
   - Batch LLM requests where possible

5. **Testing**
   - Unit tests for each agent (pytest)
   - Integration tests (full pipeline)
   - Load testing (Locust)

6. **Monitoring & Alerts**
   - Prometheus metrics (task duration, LLM latency, token usage)
   - Grafana dashboards
   - PagerDuty/Sentry for errors

---

## How to Resume Work (Context for AI Assistant)

If you're an AI assistant being given this file to resume work, here's what you need to know:

### Current State
- **Phase 1 is complete** — infrastructure is set up, tested, and working
- Docker containers (PostgreSQL + Redis) are running
- Database migrations applied, all tables created
- All Python dependencies installed in `.venv`

### Quick Start Commands
```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Start Docker services
docker compose up -d

# Run database migrations
python -m alembic upgrade head

# Start FastAPI dev server
python -m uvicorn backend.main:app --reload

# Health check
curl http://localhost:8000/health
```

### Next Steps
1. Start Phase 2: Vector Store & Codebase Indexing
2. Create the 6 files listed in Phase 2
3. Test by indexing a sample project and querying it

### Key Patterns to Follow
- All configuration from `.env` (no hardcoded secrets)
- Async everywhere (use `async def`, `await`)
- LangSmith tracing for all agent calls
- PostgreSQL for persistence (tasks, steps, logs)
- Redis for caching LLM responses (1-hour TTL)
- Type hints on all functions
- Docstrings for public APIs

### Environment Variables (.env)
- `AZURE_OPENAI_API_KEY` — Azure OpenAI key
- `AZURE_OPENAI_ENDPOINT` — Azure endpoint URL
- `EMBED_API_KEY` — Embedding model key
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `LANGSMITH_API_KEY` — LangSmith tracing key (optional)

### Project Conventions
- Use `backend/` prefix for all imports
- Database models in `backend/database/models.py`
- Pydantic schemas in `backend/models/schemas.py`
- Agent implementations in `backend/agents/`
- All agents inherit from `BaseAgent`
- LangGraph workflow in `backend/graph/workflow.py`

---

## Questions to Ask If Stuck

1. **Database connection fails?**
   - Check: `docker ps` — are containers running?
   - Check: `.env` has correct `DATABASE_URL`

2. **Import errors?**
   - Check: virtual environment activated
   - Check: `pip install -r requirements.txt` completed

3. **Azure OpenAI errors?**
   - Check: `.env` has correct `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`
   - Check: endpoint format is base URL only (not including deployment path)

4. **LangSmith not showing traces?**
   - Check: `LANGSMITH_API_KEY` is set in `.env`
   - Check: `backend/utils/logger.py` sets `LANGCHAIN_TRACING_V2=true`

---

**END OF PROGRESS FILE**

*This file is the single source of truth for project status. Update it as you complete each phase.*
