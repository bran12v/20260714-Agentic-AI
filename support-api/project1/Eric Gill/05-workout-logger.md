# Workout Logger

## Objective

Develop a workout logging backend that helps a lifter (or personal training administrator) record workout sessions and the exercise sets performed within each session. Each session is a single training instance — "Monday morning, upper body" — and each set within a session captures the exercise name, weight, reps, and rest time. The system should make it easy to log workouts as they happen, review historical sessions, and compute simple progress metrics through a clean RESTful API. Prioritize a clean parent-child relationship between sessions and sets so that filtering ("show me all bench press sets from the last month") is straightforward. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Workout Session Management

- **Add New Workout Session:**
  - Admins should be able to create a new workout session by specifying the date, the focus area (e.g., "upper body" / "legs" / "full body"), the duration in minutes, and an optional perceived-exertion rating from 1 to 10.
- **View Workout Session Details:**
  - Provide a dashboard endpoint where admins can view all sessions, their focus area, date, duration, total number of sets, and total volume (weight × reps summed across all sets).
- **Edit Workout Session Information:**
  - Allow admins to update session details such as the date (in case of a typo), duration, focus area, or perceived-exertion rating.
- **Delete Workout Session:**
  - Admins should be able to delete a session. Implement a confirmation requirement to prevent accidental deletions. Deleting a session should cascade to its sets (and that behavior should be documented).

### Exercise Set Management

- **Add Exercise Set:**
  - Admins should be able to add a set to a session, specifying the exercise name (e.g., "Bench Press"), weight in pounds or kilograms, repetitions, and rest time in seconds before the next set.
- **Edit Exercise Set:**
  - Provide functionality to update existing set details, such as correcting the weight, reps, or rest time.
- **Delete Exercise Set:**
  - Implement a feature for admins to remove a set from a session. Like session deletion, this should include a confirmation step.
- **View Exercise Sets:**
  - Admins should be able to view a list of all sets within a session, with search and filter capabilities based on exercise name (partial match), weight range, or rep range.
- **Compute Progress for an Exercise:**
  - Provide a read endpoint that returns the highest weight ever lifted for a given exercise, the most recent weight, and a count of sets performed in the last 30 days.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like focus area, date range, exercise name (partial match), and weight range.

### Edge Case Handling

- **Zero-Weight or Zero-Rep Sets:**
  - Decide how to handle sets logged with zero weight (bodyweight exercises like push-ups) or zero reps (a failed attempt). Should both be allowed, should zero-rep sets be rejected as data-entry errors, or should there be a separate field for bodyweight vs weighted? Document your choice in the README.
- **Future-Dated Session:**
  - Decide how to handle a session logged with a date in the future. Should the system reject it, accept it but flag it, or accept it silently for users who plan workouts ahead? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same session at the same time, or delete a set while the progress endpoint is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on session-log create, generate and store a suggested next workout (focus area, recommended exercises, target rep ranges) with a one-sentence rationale, derived from recent sessions.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (unsafe load/intensity recommendations or medical/injury advice); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example an Exercise catalog (with muscle group, equipment, and demo links) so that exercise names are normalized, or a Program entity that groups multi-week training plans.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many sessions in one transaction, with all-or-nothing semantics.

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
