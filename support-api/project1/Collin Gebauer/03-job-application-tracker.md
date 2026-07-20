# Job Application Tracker

## Objective

Develop a job-search tracking backend that empowers a job seeker (or career coach administrator) to manage their active job applications and the interview rounds associated with each. Each application captures the company name, role title, application date, current status (applied → screening → interview → offer → rejected → withdrawn), salary range, and notes; each interview round records the round number, format (phone / video / on-site), scheduled date, interviewer, and outcome. The system should make it easy to log new applications, advance them through their pipeline, log interview rounds as they happen, and search history through a clean RESTful API. Prioritize a clean lifecycle on the application status so the user can answer "what's in flight right now" at any time. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Application Management

- **Add New Application:**
  - Admins should be able to create a new application by specifying the company name, role title, application date, posting URL, salary range (min/max in a chosen currency), location (city or "remote"), and an initial status of "applied."
- **View Application Details:**
  - Provide a dashboard endpoint where admins can view all applications, their company, role, current status, date applied, total interview rounds scheduled, and days since the last status change.
- **Edit Application Information:**
  - Allow admins to update application details such as status (applied / screening / interview / offer / accepted / rejected / withdrawn), salary range (when an offer is extended), location, or notes.
- **Delete Application:**
  - Admins should be able to delete an application. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting an application with logged interview rounds (cascade vs. preserve for history).

### Interview Round Management

- **Add Interview Round:**
  - Admins should be able to add an interview round to an application, specifying the round number, scheduled date, format (phone / video / on-site / take-home), interviewer name, and an optional preparation note.
- **Edit Interview Round:**
  - Provide functionality to update existing round details, such as rescheduling the date, adding the outcome after the interview, or amending notes.
- **Delete Interview Round:**
  - Implement a feature for admins to remove an interview round. Like application deletion, this should include a confirmation step.
- **View Interview Rounds:**
  - Admins should be able to view a list of all interview rounds for an application, with search and filter capabilities based on date range, format, outcome, or interviewer name (partial match).
- **Advance Application to Next Stage:**
  - Provide an endpoint that transitions an application's status to the next logical stage (e.g., screening → interview, interview → offer) and optionally creates a new interview round in the same transaction. Reject the transition if it doesn't follow the documented status lifecycle.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like status, company (partial match), date range, salary range, and location.

### Edge Case Handling

- **Interview Round on a Rejected / Withdrawn Application:**
  - Decide how to handle adding an interview round to an application whose status is already "rejected" or "withdrawn." Should the system reject the operation, accept it with a flag (the rejection might be premature), or accept it silently? Document your choice in the README.
- **Status Lifecycle Violations:**
  - Decide how to handle status transitions that don't follow the documented order — for example moving directly from "applied" to "offer" without going through "interview." Should the system reject the transition, allow it with a warning, or accept it silently? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same application at the same time, or delete an interview round while another request is advancing the application. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on application create/update, generate and store a tailored cover-letter draft, a recommended tone, and the top three resume highlights it leaned on, derived from the pasted job description and user-provided highlights.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating experience, employers, or credentials the user never provided); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Contact entity for tracking recruiters and hiring managers across multiple applications, or a Document entity for storing resumés and cover letters submitted with each application.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many applications in one transaction, with all-or-nothing semantics.

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
