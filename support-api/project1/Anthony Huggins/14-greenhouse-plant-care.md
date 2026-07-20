# Greenhouse Plant Care

## Objective

Develop a greenhouse plant-care backend that empowers a horticulturist (or greenhouse manager) to maintain a catalog of living plants and the full care history of each one. Each plant has a nickname, species, acquisition date, location (a bench or zone within the greenhouse), pot size in centimeters, and a current health status (thriving / stable / struggling / dormant / dead); each care log entry is a timestamped record of an action — watering, fertilizing, repotting, pruning, pest treatment, or an observation — with the caretaker who performed it and free-text notes. The system should make it easy to onboard new plants, record daily care, and search the care history through a clean RESTful API. Prioritize a single source of truth for plant health — the current status should always be consistent with the most recent care log entry that changed it. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Plant Management

- **Add New Plant:**
  - Admins should be able to onboard a new plant by specifying its nickname, species, acquisition date, greenhouse location, pot size in centimeters, and an initial health status of "stable."
- **View Plant Details:**
  - Provide a dashboard endpoint where admins can view all plants, their species, current health status, location, date of the last care event, and total care events recorded.
- **Edit Plant Information:**
  - Allow admins to update plant details such as nickname, location (after a move), pot size (after a repot), or current health status (with the understanding that status changes should also be reflected in the care log).
- **Delete Plant:**
  - Admins should be able to delete a plant record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a plant with a care history (cascade vs. preserve the history for reference).

### Care Log Management

- **Add Care Log Entry:**
  - Admins should be able to log an action against a plant, specifying the action type (watered / fertilized / repotted / pruned / pest_treatment / observation), the date, the caretaker who performed it, and free-text notes (e.g., "leaves yellowing at the tips, applied neem oil").
- **Edit Care Log Entry:**
  - Provide functionality to update existing log entry details, such as correcting the caretaker's name, adjusting the date, or amending notes.
- **Delete Care Log Entry:**
  - Implement a feature for admins to remove a log entry. Like plant deletion, this should include a confirmation step. Note that deleting the most recent entry that set the plant's current status should surface the implication in the response.
- **View Care Log:**
  - Admins should be able to view a list of all log entries for a plant, with search and filter capabilities based on action type, date range, caretaker name (partial match), or notes content.
- **Record Repot:**
  - Provide an endpoint that atomically (1) creates a "repotted" care log entry for the plant + caretaker + date and (2) updates the plant's pot size to the new value. Reject the repot if the new pot size is not larger than the current pot size unless an `allow_downsize` flag is passed.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like species (partial match), health status, location, pot size range, and acquisition date range.

### Edge Case Handling

- **Care Event on a Dead Plant:**
  - Decide how to handle logging a care action (e.g., watering) against a plant whose current status is "dead." Should the system reject the request, accept it and auto-revive the plant to "stable," or accept it and leave the status unchanged? Document your choice in the README.
- **Future-Dated Care Entry:**
  - Decide how to handle a care log entry whose date is in the future. Should the system reject it, accept it as a scheduled task, or accept it silently? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to repot the same plant at the same time, or delete a care log entry while the plant is being updated. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on care-log create, diagnose from the plant's species, recent care history, and free-text symptom description and store the suspected issue, a recommended action, and a confidence level.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (plant toxicity or pesticide/chemical-handling advice); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Species entity holding default care requirements (ideal watering interval, light needs), or a GreenhouseZone entity for tracking climate conditions per zone.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a nursery intake spreadsheet) and inserts many plants in one transaction, with all-or-nothing semantics.

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
