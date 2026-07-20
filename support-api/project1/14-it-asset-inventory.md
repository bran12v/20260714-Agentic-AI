# IT Asset Inventory

## Objective

Develop an IT asset inventory backend that empowers a system administrator (or IT operations manager) to maintain a catalog of company-owned devices and the full lifecycle history of each device. Each device has an asset tag, model, manufacturer, purchase date, purchase price, and current status (in_stock / assigned / repair / retired); each maintenance log entry is a timestamped record of an event — assignment to an employee, return, repair, upgrade, or retirement — with the technician or employee involved and free-text notes. The system should make it easy to onboard new devices, track who has what, log maintenance events, and search the audit trail through a clean RESTful API. Prioritize a single source of truth for device status — the device's current status should always be derivable from (or consistent with) the most recent maintenance log entry. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Device Management

- **Add New Device:**
  - Admins should be able to onboard a new device by specifying its asset tag (a unique identifier), model, manufacturer, purchase date, purchase price in cents, and an initial status of "in_stock."
- **View Device Details:**
  - Provide a dashboard endpoint where admins can view all devices, their model, current status, currently assigned employee (if any), date of the last maintenance event, and total maintenance events recorded.
- **Edit Device Information:**
  - Allow admins to update device details such as model (a correction), manufacturer, purchase price, or current status (with the understanding that status changes should also be reflected in the maintenance log).
- **Delete Device:**
  - Admins should be able to delete a device record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a device with a maintenance history (cascade vs. preserve for audit — for IT compliance, audit history typically must be preserved).

### Maintenance Log Management

- **Add Maintenance Log Entry:**
  - Admins should be able to log an event against a device, specifying the event type (assigned / returned / repair / upgrade / retired / inventory_check), the date, the employee or technician involved, and free-text notes (e.g., "replaced battery, hard drive shows S.M.A.R.T. warnings").
- **Edit Maintenance Log Entry:**
  - Provide functionality to update existing log entry details, such as correcting the technician's name, adjusting the date, or amending notes. Editing should preserve the original record in an audit trail.
- **Delete Maintenance Log Entry:**
  - Implement a feature for admins to remove a log entry. Like device deletion, this should include a confirmation step. Note that deleting a log entry that affects the device's current status (e.g., the most recent "assigned" event) should also surface the implication in the response.
- **View Maintenance Log:**
  - Admins should be able to view a list of all log entries for a device, with search and filter capabilities based on event type, date range, employee or technician name (partial match), or notes content.
- **Assign Device to Employee:**
  - Provide an endpoint that atomically (1) creates an "assigned" maintenance log entry for the device + employee + date and (2) updates the device's current status to "assigned." Reject the assignment if the device's current status is "repair" or "retired."

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like manufacturer, model (partial match), status, purchase date range, and assigned employee (partial match).

### Edge Case Handling

- **Assigning a Device That's Already Assigned:**
  - Decide how to handle assigning a device to a new employee when the device is currently assigned to someone else. Should the system reject the request, auto-create a "returned" entry from the previous employee before logging the new assignment, or accept it silently? Document your choice in the README.
- **Retiring a Device with Open Assignment:**
  - Decide how to handle retiring a device whose current status is "assigned" (the employee still has it). Should the system block the retirement, auto-create a "returned" log entry first, or accept the retirement and surface the inconsistency? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to assign the same device to different employees at the same time, or delete a maintenance log entry while the device is being assigned. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on asset create/update, estimate and store a refresh urgency (low/medium/high/immediate), expected remaining useful life, and a one-sentence rationale from specs, age, purchase price, and maintenance history.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating warranty, end-of-life, or security-support status); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example an Employee entity for tracking each person's assigned-device history across departments, or a License entity for software licenses bound to devices.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, an asset onboarding spreadsheet) and inserts many devices in one transaction, with all-or-nothing semantics.

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
