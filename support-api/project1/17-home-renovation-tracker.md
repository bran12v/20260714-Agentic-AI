# Home Renovation Tracker

## Objective

Develop a home renovation tracker backend that empowers a homeowner (or general contractor) to manage renovation projects and the individual tasks that make up each project. Each project has a name, the room or area being renovated, a budget in cents, a start date, a target completion date, and a status (planning / in_progress / on_hold / completed / cancelled); each task is a record tied to a project with a description, an estimated cost in cents, an actual cost in cents (once known), the trade responsible (e.g., plumbing, electrical, carpentry), and a task status (todo / in_progress / blocked / done). The system should make it easy to plan a renovation, break it into tasks, track spend against budget, and search the work through a clean RESTful API. Prioritize correctness on the money math — a project's total actual spend should always be derivable from the sum of its tasks' actual costs. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Project Management

- **Add New Project:**
  - Admins should be able to create a renovation project by specifying its name, the room or area, a budget in cents, a start date, a target completion date, and an initial status of "planning."
- **View Project Details:**
  - Provide a dashboard endpoint where admins can view all projects, their room, budget, total estimated cost and total actual cost across tasks, remaining budget, current status, and the count of associated tasks.
- **Edit Project Information:**
  - Allow admins to update project details such as name, budget, target completion date, or status after the initial creation.
- **Delete Project:**
  - Admins should be able to delete a project. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a project that still has tasks (cascade vs. block).

### Task Management

- **Add Task:**
  - Admins should be able to add a task to a project, specifying a description, an estimated cost in cents, the trade responsible, and an initial task status of "todo."
- **Edit Task:**
  - Provide functionality to update an existing task, such as revising the estimate, recording the actual cost, reassigning the trade, or advancing the task status.
- **Delete Task:**
  - Implement a feature for admins to remove a task from a project. Like project deletion, this should include a confirmation step.
- **View Tasks:**
  - Admins should be able to view a list of all tasks for a project, with search and filter capabilities based on task status, trade, estimated/actual cost range, or description content.
- **Complete Task:**
  - Provide an endpoint that atomically (1) sets a task's status to "done" and records its actual cost and (2) recomputes the project's total actual spend. Reject completion if no actual cost is supplied.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like room (partial match), status, budget range, target completion date range, and trade.

### Edge Case Handling

- **Task That Pushes a Project Over Budget:**
  - Decide how to handle recording an actual cost that makes the project's total actual spend exceed its budget. Should the system reject it, accept it and flag the project as over budget, or accept it silently? Document your choice in the README.
- **Completing a Project With Open Tasks:**
  - Decide how to handle setting a project's status to "completed" while it still has tasks that are not "done." Should the system block it, auto-close the remaining tasks, or accept it and surface the inconsistency? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to complete the same task at the same time, or delete a task while the project total is being recomputed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on renovation-project create, generate and store a suggested task breakdown (descriptions, trades, rough cost estimates) from the free-text description.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (underestimating costs or omitting permit, safety, or building-code requirements); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Contractor entity assigned to tasks across projects, or a Material entity tracking supplies purchased per task.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a contractor's estimate spreadsheet) and inserts many tasks in one transaction, with all-or-nothing semantics.

## Technical Requirements

Must be a backend solution consisting of:

- Python 3.11+
- Flask 3.x with the app-factory pattern and blueprints
- Pydantic v2 for HTTP-boundary validation
- SQLite (via the sqlite3 stdlib) for persistence, with parameterized queries
- structlog for structured JSON logging with per-request correlation IDs
- pytest with fixtures and parametrize for the test suite
- Docker multi-stage Dockerfile + docker-compose.yml for local stack
- pyproject.toml with a src/ layout and a [project.optional-dependencies] dev block
- Azure OpenAI (via the `openai` SDK's `AzureOpenAI` client) for the required AI enrichment step, configured entirely through environment variables (`.env` + python-dotenv), with the key kept out of version control
- Code should be available in a private GitHub repository, with the instructor added as a collaborator
- Possesses all required CRUD functionality
- Handles edge cases effectively

## Non-Functional Requirements

- Well-documented code (module docstrings + function docstrings on public surfaces)
- Code upholds industry best practices (SOLID / DRY / single-responsibility)
- Type hints on every function signature
- Test coverage on happy + error paths (at least 15 pytest tests)
- Structured logs (no print statements in production code paths)
- Container runnable via a single `docker compose up`
- README with one-line install and one-line run instructions
- Pydantic models have explicit field constraints (Literal types, min/max length, ge/le on numerics)
- No mutable default arguments; use field(default_factory=...) for collections
- Errors raise typed exceptions from a DomainError hierarchy, not generic Exception
- Responsible AI: document your safeguards, and validate every LLM response through a Pydantic model before returning or persisting it
