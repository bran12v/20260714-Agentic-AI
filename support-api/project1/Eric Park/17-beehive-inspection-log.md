# Beehive Inspection Log

## Objective

Develop a beehive management backend that empowers a beekeeper (or apiary manager) to maintain a registry of hives and the full inspection history of each one. Each hive has a name or number, a location within the apiary, the installation date, the queen's origin/breed, and a current status (active / weak / queenless / swarmed / dead); each inspection is a timestamped record of a hive visit — capturing whether the queen was seen, whether brood was present, an estimated number of populated frames, the temperament observed, and free-text notes, along with the inspector who performed it. The system should make it easy to register hives, log inspections, and search the history through a clean RESTful API. Prioritize a single source of truth for hive health — the current status should always be consistent with the most recent inspection that changed it. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Hive Management

- **Add New Hive:**
  - Admins should be able to register a hive by specifying its name or number, apiary location, installation date, queen origin/breed, and an initial status of "active."
- **View Hive Details:**
  - Provide a dashboard endpoint where admins can view all hives, their location, current status, queen origin, date of the last inspection, and total inspections recorded.
- **Edit Hive Information:**
  - Allow admins to update hive details such as name, location (after a move), queen origin (after a requeen), or current status (with the understanding that status changes should also be reflected in the inspection log).
- **Delete Hive:**
  - Admins should be able to delete a hive record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a hive with an inspection history (cascade vs. preserve for records).

### Inspection Management

- **Add Inspection:**
  - Admins should be able to log an inspection against a hive, specifying the date, the inspector, whether the queen was sighted, whether brood was present, an estimated number of populated frames, the temperament (calm / active / defensive), and free-text notes (e.g., "spotted queen cells on frame 6, possible swarm prep").
- **Edit Inspection:**
  - Provide functionality to update an existing inspection, such as correcting the inspector's name, adjusting the date, or amending notes and frame counts.
- **Delete Inspection:**
  - Implement a feature for admins to remove an inspection. Like hive deletion, this should include a confirmation step. Note that deleting the most recent inspection that set the hive's current status should surface the implication in the response.
- **View Inspections:**
  - Admins should be able to view a list of all inspections for a hive, with search and filter capabilities based on date range, inspector name (partial match), queen-sighted flag, temperament, or notes content.
- **Record Requeen:**
  - Provide an endpoint that atomically (1) creates an inspection entry noting a requeen with the new queen's origin and (2) updates the hive's queen origin and sets its status to "active." Reject the requeen if the hive's current status is "dead."

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like location, status, queen origin (partial match), installation date range, and last-inspection date range.

### Edge Case Handling

- **Inspection on a Dead Hive:**
  - Decide how to handle logging an inspection against a hive whose current status is "dead." Should the system reject it, accept it and revive the hive to "active" if the queen was sighted, or accept it and leave the status unchanged? Document your choice in the README.
- **Queenless Hive with Queen Sighted:**
  - Decide how to handle an inspection that marks the queen as sighted on a hive whose status is "queenless." Should the system auto-update the status to "active," require an explicit status change, or leave it to the beekeeper? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to requeen the same hive at the same time, or delete an inspection while the hive status is being updated. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on inspection create, estimate and store a swarm risk (low/medium/high) with a one-sentence rationale from recent inspection history (frame counts, queen-cell notes, temperament trend).
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (advice that endangers the colony or the beekeeper); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a HarvestRecord entity tracking honey yield per hive per season, or an Apiary entity grouping hives by physical site with its own climate notes.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a season's field notebook) and inserts many inspections in one transaction, with all-or-nothing semantics.

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
