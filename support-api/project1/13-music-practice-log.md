# Music Practice Log

## Objective

Develop a music practice tracking backend that helps a musician (or instrumental teacher administrator) record practice goals and the practice sessions logged against each goal. Each goal is a focused objective — "play the C major scale at 120 bpm cleanly" or "memorize the first movement of the sonata" — and each session records the date, the duration, the instrument used, and notes on progress. The system should make it easy to set goals, log sessions as they happen, review progress toward each goal, and search practice history through a clean RESTful API. Prioritize a clean parent-child relationship between goals and sessions so that "how much have I practiced toward goal X this week" is straightforward to compute. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Goal Management

- **Add New Goal:**
  - Admins should be able to create a new goal by specifying its title (the objective in plain English), the target completion date, the priority level (low / medium / high), and an optional description with success criteria.
- **View Goal Details:**
  - Provide a dashboard endpoint where admins can view all goals, their target date, priority, status (active / achieved / abandoned), total minutes practiced toward the goal, and days remaining until target.
- **Edit Goal Information:**
  - Allow admins to update goal details such as title, target date (extending or pulling forward), priority, or status (marking achieved or abandoned).
- **Delete Goal:**
  - Admins should be able to delete a goal. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a goal with logged practice sessions (cascade vs orphan the sessions).

### Practice Session Management

- **Add Practice Session:**
  - Admins should be able to log a practice session against a goal, specifying the date, the duration in minutes, the instrument used (e.g., "Acoustic Guitar" / "Piano"), and free-text notes on what was worked on.
- **Edit Practice Session:**
  - Provide functionality to update existing session details, such as correcting the duration, adjusting the date, or amending the notes.
- **Delete Practice Session:**
  - Implement a feature for admins to remove a session. Like goal deletion, this should include a confirmation step.
- **View Practice Sessions:**
  - Admins should be able to view a list of all practice sessions, with search and filter capabilities based on instrument, date range, duration range, or note content (partial match).
- **Compute Weekly Practice Summary:**
  - Provide a read endpoint that returns the total minutes practiced this week, broken down per goal, with the day-of-week distribution and a count of distinct instruments used.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like instrument, goal status, priority, date range, and goal title (partial match).

### Edge Case Handling

- **Practice Session With Zero Duration:**
  - Decide how to handle a session logged with zero or negative duration. Should the system reject it as invalid, accept it as a "no-show" marker for accountability, or treat it as a deletion of the day's entry? Document your choice in the README.
- **Logging Practice Against an Achieved or Abandoned Goal:**
  - Decide how to handle a practice session logged against a goal whose status is already "achieved" or "abandoned." Should the system reject the session, accept it but flag it, or accept it silently (musicians keep practicing even after a goal is met)? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same goal at the same time, or delete a practice session while the weekly summary endpoint is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on practice-log create, generate and store a daily practice plan (warm-up, technique, repertoire, cool-down with target minutes per block) from active goals and recent history.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (recommending practice durations or techniques that risk strain or injury); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Repertoire entity that tracks pieces being learned (separate from goals), or an Instrument entity that captures setup notes and maintenance history.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many practice sessions in one transaction, with all-or-nothing semantics.

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
