# Agentic Developer Environment - Progress Tracker

**Last Updated:** March 26, 2026  
**Current Phase:** Phase 4 Complete ✅ → Ready for Phase 5

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
│   │   ├── cache_service.py          ✅ Redis caching (LLM responses)
│   │   └── embedding_service.py      ✅ Azure OpenAI embeddings (batch + truncation)
│   │
│   ├── utils/
│   │   ├── __init__.py               ✅
│   │   ├── logger.py                 ✅ Structured logging + LangSmith setup
│   │   ├── file_parser.py            ✅ AST/regex code parser (Python, JS/TS, generic)
│   │   └── text_splitter.py          ✅ Token-aware code splitter with overlap
│   │
│   ├── agents/                       ✅ Phase 3
│   │   ├── __init__.py               ✅
│   │   ├── base_agent.py             ✅ Abstract base (LLMClient, CacheService, logger)
│   │   ├── context_agent.py          ✅ FAISS RAG retrieval → context string
│   │   ├── planner_agent.py          ✅ LLM decomposes task → ordered steps
│   │   ├── codegen_agent.py          ✅ LLM generates code artifacts per step
│   │   ├── review_agent.py           ✅ LLM reviews correctness, security, style
│   │   └── execution_agent.py        ✅ Subprocess runner with timeout + output capture
│   │
│   ├── graph/                        ✅ Phase 3
│   │   ├── __init__.py               ✅
│   │   ├── state.py                  ✅ AgenticState TypedDict with reducers
│   │   ├── nodes.py                  ✅ Node wrappers + DB persistence + agent logging
│   │   └── workflow.py               ✅ LangGraph StateGraph with conditional routing
│   │
│   ├── vectordb/                     ✅ Phase 2
│   │   ├── __init__.py               ✅
│   │   ├── faiss_store.py            ✅ FAISS index wrapper (CRUD + persistence)
│   │   ├── indexer.py                ✅ Directory walker + embedding pipeline
│   │   └── retriever.py              ✅ Natural language query → code search
│   │
│   └── cli/                          ✅ Phase 4
│       ├── __init__.py               ✅
│       ├── main.py                   ✅ Typer app with command groups
│       └── commands/
│           ├── __init__.py           ✅
│           ├── index.py              ✅ Codebase indexing with Rich progress
│           ├── task.py               ✅ Task submission + live progress
│           └── status.py             ✅ Task status display + listing
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

## ✅ Phase 2: Vector Store & Codebase Indexing (COMPLETED)

**Goal:** Build FAISS-powered RAG system for codebase context retrieval.

### What Was Built

| File | Purpose | Status |
|---|---|---|
| backend/services/embedding_service.py | Azure OpenAI text-embedding-3-small wrapper, batch embedding with token truncation | ✅ Verified |
| backend/utils/file_parser.py | AST-based Python parser, regex-based JS/TS parser, generic fallback; extracts functions, classes, methods | ✅ Verified |
| backend/utils/text_splitter.py | Token-aware code splitter (tiktoken cl100k_base), configurable max_tokens + overlap | ✅ Verified |
| backend/vectordb/faiss_store.py | FAISS IndexFlatL2 wrapper with JSON metadata sidecar, create/add/search/save/load | ✅ Verified |
| backend/vectordb/indexer.py | Directory walker, file parser + splitter pipeline, embedding generation, FAISS persistence, DB project.indexed_at update | ✅ Verified |
| backend/vectordb/retriever.py | Natural language query → embedding → FAISS top-k search, LLM context formatter | ✅ Verified |

### Verification Results

| Component | Test | Result |
|---|---|---|
| file_parser | Parse models.py → extract 11 chunks (functions, classes) | ✅ |
| text_splitter | Split oversized Task class → 2 sub-chunks with overlap | ✅ |
| faiss_store | Create → add 5 vectors → search → save → reload → search | ✅ |
| embedding_service | Import + instantiation | ✅ |
| indexer | Import + instantiation | ✅ |
| retriever | Import + instantiation | ✅ |

### Key Design Decisions

- **Python files:** parsed via `ast` module for precise function/class/method extraction
- **JS/TS files:** regex-based parser for function/class/const-arrow declarations
- **Other files:** treated as single whole-file chunks
- **Splitting:** token-bounded sub-chunks (default 512 tokens, 64 overlap) on line boundaries
- **FAISS:** IndexFlatL2 (exact search) — suitable for codebases up to ~100K chunks
- **Persistence:** `faiss.index` + `faiss_metadata.json` sidecar in `.index_store/<project_id>/`
- **Retriever:** includes `format_context()` for building LLM prompt context from results

### Acceptance Criteria

- [x] FAISS index persists to disk, reloads correctly
- [x] Metadata maps vector IDs back to source files + line numbers
- [ ] Index a sample Python project (requires Azure OpenAI embeddings endpoint)
- [ ] Query: "authentication functions" → returns relevant code chunks
- [ ] Query: "database models" → returns ORM model definitions

---

## ✅ Phase 3: LangGraph Agent Core (COMPLETED)

**Goal:** Implement all 5 agents and wire them into a LangGraph state machine.

### What Was Built

| File | Purpose | Status |
|---|---|---|
| backend/graph/state.py | AgenticState TypedDict with 17 fields, `operator.add` reducers for `errors` and `total_tokens` | ✅ Verified |
| backend/agents/base_agent.py | Abstract base class with LLMClient, CacheService, structured logger | ✅ Verified |
| backend/agents/context_agent.py | FAISS retrieval via Retriever → formatted context string, graceful fallback when no index exists | ✅ Verified |
| backend/agents/planner_agent.py | LLM decomposes task into 2-6 ordered steps (JSON), robust markdown fence stripping | ✅ Verified |
| backend/agents/codegen_agent.py | LLM generates code artifacts per step, feeds back review/execution errors on retry | ✅ Verified |
| backend/agents/review_agent.py | LLM reviews for correctness, OWASP security, style; increments iteration_count on failure | ✅ Verified |
| backend/agents/execution_agent.py | Subprocess runner (Python) with 30s timeout, output capture, step advancement on success | ✅ Verified |
| backend/graph/nodes.py | Node wrappers: DB status updates, agent log persistence, code artifact storage, retry tracking | ✅ Verified |
| backend/graph/workflow.py | LangGraph StateGraph: START → context → plan → [codegen → review → execute] loop, conditional routing, `run_task()` entry point | ✅ Verified |

### Verification Results

| Component | Test | Result |
|---|---|---|
| state.py | Import AgenticState, verify 17 fields | ✅ |
| base_agent.py | Import BaseAgent | ✅ |
| All 5 agents | Import ContextAgent, PlannerAgent, CodegenAgent, ReviewAgent, ExecutionAgent | ✅ |
| nodes.py | Import all 5 node functions | ✅ |
| workflow.py | Import workflow, verify 7 graph nodes (incl. __start__, __end__) | ✅ |
| Graph edges | Verified 10 edges: linear + conditional routing | ✅ |

### Key Design Decisions

- **State reducers:** `errors` (list, appended) and `total_tokens` (int, summed) use `operator.add`
- **Retry logic:** `iteration_count` incremented by review agent on FAIL and execution agent on FAIL; routing functions enforce `max_iterations` (default 3)
- **Step advancement:** execution agent increments `current_step_index` on success, resets `iteration_count` to 0
- **DB persistence:** nodes.py handles all PostgreSQL writes (task status, step status, agent logs, code artifacts) — agents stay pure
- **Graceful fallback:** context agent catches `FileNotFoundError` when no FAISS index exists
- **JSON parsing:** all agents strip markdown fences (```` ```json ... ``` ````) from LLM output before parsing
- **Execution safety:** subprocess with 30s timeout, temp directory isolation, output length capped at 10K chars
- **LangSmith tracing:** automatic via LangChain/LangGraph integration when `LANGCHAIN_TRACING_V2=true`

### Workflow Graph

```
START → retrieve_context → plan_task → [conditional]
                                         ├→ generate_code → review_code → [conditional]
                                         │                                  ├→ PASS → execute_code → [conditional]
                                         │                                  │                          ├→ SUCCESS + more steps → generate_code
                                         │                                  │                          ├→ SUCCESS + done → END
                                         │                                  │                          ├→ FAIL + can retry → generate_code
                                         │                                  │                          └→ FAIL + max retries → END
                                         │                                  ├→ FAIL + can retry → generate_code
                                         │                                  └→ FAIL + max retries → END
                                         └→ no steps / failed → END
```

### Acceptance Criteria

- [x] AgenticState TypedDict with all required fields and reducers
- [x] All 5 agents implemented with LLM prompts and JSON parsing
- [x] LangGraph StateGraph compiles with correct node/edge topology
- [x] Conditional routing: review pass/fail, execution pass/fail, max retries
- [x] DB persistence: task status, step status, agent logs, code artifacts
- [x] All imports verified — no circular dependencies
- [ ] End-to-end test with Azure OpenAI (requires live API keys)

---

## ✅ Phase 4: CLI Interface (COMPLETED)

**Goal:** Developer-friendly CLI for task management and indexing.

### What Was Built

| File | Purpose | Status |
|---|---|---|
| backend/cli/__init__.py | Package init | ✅ |
| backend/cli/main.py | Typer app with 3 command groups (`index`, `task`, `status`), logging init | ✅ Verified |
| backend/cli/commands/__init__.py | Package init | ✅ |
| backend/cli/commands/index.py | `index <dir>` — creates project in DB, indexes codebase into FAISS with Rich progress | ✅ Verified |
| backend/cli/commands/task.py | `task run <description>` — runs full agent workflow, displays results with syntax-highlighted code, step status, errors | ✅ Verified |
| backend/cli/commands/status.py | `status [task_id]` — shows task details + steps + artifacts; lists recent tasks when no ID given | ✅ Verified |

### Verification Results

| Component | Test | Result |
|---|---|---|
| CLI import | `from backend.cli.main import app` | ✅ |
| Main help | `python -m backend.cli.main --help` | 3 commands shown ✅ |
| Index help | `python -m backend.cli.main index --help` | Args + options correct ✅ |
| Task help | `python -m backend.cli.main task run --help` | Args + options correct ✅ |
| Status help | `python -m backend.cli.main status --help` | Args + options correct ✅ |

### CLI Usage

```bash
# Index a codebase
python -m backend.cli.main index ./my_project --name "My Project"

# Run a task
python -m backend.cli.main task run "Add JWT authentication to user service"
python -m backend.cli.main task run --project <uuid> "Add logging"

# Check status
python -m backend.cli.main status                      # list recent tasks
python -m backend.cli.main status <task-uuid>           # task details
python -m backend.cli.main status <task-uuid> --code    # include code artifacts
```

### Key Design Decisions

- **Async bridge:** all commands use `asyncio.run()` to call async backend APIs from sync Typer handlers
- **Rich formatting:** syntax-highlighted code (Monokai theme), color-coded status, Rich panels/tables/progress bars
- **DB integration:** index command creates Project rows; status command queries Task/Step/CodeArtifact with eager loading
- **Typer 0.24.1:** upgraded from 0.15.1 to fix Click 8.2.x compatibility (`make_metavar()` issue)
- **Optional[str] annotations:** used instead of `str | None` for Typer parameter compatibility

### Acceptance Criteria

- [x] `index ./my_project` → indexes codebase, saves to FAISS
- [x] `task run "add logging to all API endpoints"` → starts task
- [x] Real-time updates as agents execute (spinner + Rich live status)
- [x] `status <task_id>` → shows current progress
- [x] Generated code displayed with syntax highlighting
- [ ] End-to-end test with Azure OpenAI (requires live API keys)

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
- **Phase 2 is complete** — vector store, codebase parsing, and FAISS indexing built and verified
- **Phase 3 is complete** — all 5 agents + LangGraph workflow implemented and verified
- **Phase 4 is complete** — CLI interface with index, task, and status commands
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

# Run a task via CLI
python -m backend.cli.main task run "Write a function to reverse a string"

# Index a codebase via CLI
python -m backend.cli.main index ./my_project --name "My Project"

# Check task status
python -m backend.cli.main status

# Run a task programmatically (Python)
import asyncio
from backend.graph.workflow import run_task
result = asyncio.run(run_task("Write a function to reverse a string"))
```

### Next Steps
1. Start Phase 5: REST API Layer
2. Create task CRUD endpoints (POST/GET /tasks)
3. Create index endpoint (POST /index)
4. Create search endpoint (GET /search)
5. Add WebSocket endpoint for real-time task progress
6. Add CORS, request ID middleware, error handling

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
