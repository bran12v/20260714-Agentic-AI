# Volunteer Shift Scheduler

## Objective

Develop a volunteer shift-scheduling backend that empowers a coordinator (or a nonprofit's operations manager) to manage volunteers and the shifts each volunteer signs up for. Each volunteer has a name, a contact email, a set of skills, a maximum weekly hour cap, and a status (active / inactive / on_leave); each shift is a record tied to a volunteer capturing the role, the date, the start and end times, the location, and a shift status (scheduled / confirmed / completed / no_show / cancelled). The system should make it easy to onboard volunteers, schedule and confirm shifts, track hours, and search the roster through a clean RESTful API. Prioritize correctness on scheduling integrity — a volunteer's scheduled hours in a week must not exceed their weekly cap, and two shifts for the same volunteer must not overlap in time. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Volunteer Management

- **Add New Volunteer:**
  - Admins should be able to onboard a volunteer by specifying their name, contact email, skills, maximum weekly hour cap, and an initial status of "active."
- **View Volunteer Details:**
  - Provide a dashboard endpoint where admins can view all volunteers, their contact email, status, skills, total hours scheduled and completed, and the count of associated shifts.
- **Edit Volunteer Information:**
  - Allow admins to update volunteer details such as contact email, skills, weekly hour cap, or status after the initial creation.
- **Delete Volunteer:**
  - Admins should be able to delete a volunteer record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a volunteer with scheduled or completed shifts (cascade vs. block).

### Shift Management

- **Add Shift:**
  - Admins should be able to schedule a shift for a volunteer, specifying the role, the date, start and end times, the location, and an initial status of "scheduled."
- **Edit Shift:**
  - Provide functionality to update an existing shift, such as changing the times, reassigning the role or location, or advancing the shift status.
- **Delete Shift:**
  - Implement a feature for admins to remove a shift. Like volunteer deletion, this should include a confirmation step.
- **View Shifts:**
  - Admins should be able to view a list of all shifts for a volunteer, with search and filter capabilities based on shift status, role, date range, or location (partial match).
- **Confirm Shift:**
  - Provide an endpoint that atomically (1) checks that the shift does not overlap any of the volunteer's other shifts and does not push their weekly scheduled hours over their cap, and (2) transitions the shift's status to "confirmed." Reject the confirmation on overlap or cap violation with a clear conflict error.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like role, shift status, date range, location (partial match), and volunteer name (partial match).

### Edge Case Handling

- **Overlapping Shifts:**
  - Decide how to handle scheduling a shift that overlaps an existing shift for the same volunteer. Should the system reject it, accept it and flag the conflict, or accept it silently? The chosen behavior — rejecting on confirm — should be enforced and documented in the README.
- **Exceeding the Weekly Hour Cap:**
  - Decide how to handle a shift that would push the volunteer's confirmed weekly hours over their cap. Should the system reject the confirmation, allow it with an override flag, or accept it and flag the volunteer as over capacity? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input — including rejecting a shift whose end time is not after its start time.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to confirm two overlapping shifts for the same volunteer at the same time, or delete a shift while weekly hours are being totaled. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on shift/role create, suggest and store the best-fit volunteer (recommended volunteer, match rationale, fit score) from active volunteers' skills and availability.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (exposing volunteers' personal data or fabricating qualifications or clearances); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example an Event entity that groups shifts under a single fundraiser or campaign, or a Role entity defining required skills and headcount for each type of shift.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a sign-up-sheet export) and inserts many shifts in one transaction, with all-or-nothing semantics.

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
