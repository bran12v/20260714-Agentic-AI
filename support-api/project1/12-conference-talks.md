# Conference Talk Tracker

## Objective

Develop a conference talk tracking backend that empowers a conference administrator to manage talks submitted by speakers across multiple tracks and days. Each talk has a title, abstract, duration, difficulty level, and an assigned track; each speaker has profile information and may have submitted multiple talks. The system should make it easy to add speakers, log talk submissions, schedule accepted talks into time slots, and search across the schedule through a clean RESTful API. Prioritize a clean parent-child relationship between speakers and talks so that filtering ("show me all keynotes from speaker X across all years") is straightforward, and ensure that scheduling logic prevents the same speaker from being double-booked. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Talk Management

- **Add New Talk:**
  - Admins should be able to create a new talk by specifying its title, abstract, duration in minutes (typically 25, 45, or 60), difficulty level (beginner / intermediate / advanced), and the proposed track (e.g., "AI" / "Frontend" / "Infrastructure").
- **View Talk Details:**
  - Provide a dashboard endpoint where admins can view all talks, their status (submitted / accepted / rejected / scheduled), assigned speaker, scheduled time slot (if any), and acceptance/rejection date.
- **Edit Talk Information:**
  - Allow admins to update talk details such as the abstract (after speaker revisions), duration, difficulty, track, or status.
- **Delete Talk:**
  - Admins should be able to delete a talk. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting an accepted talk that was already scheduled (release the time slot or block the deletion?).

### Speaker Management

- **Add Speaker:**
  - Admins should be able to add a speaker by specifying their full name, email address, biography, optional company affiliation, and optional social handle.
- **Edit Speaker:**
  - Provide functionality to update existing speaker details, such as correcting the bio, updating affiliation after a job change, or fixing a typo in the email.
- **Delete Speaker:**
  - Implement a feature for admins to remove a speaker. Like talk deletion, this should include a confirmation step. Document the policy on deleting a speaker who has accepted talks.
- **View Speakers:**
  - Admins should be able to view a list of all speakers, with search and filter capabilities based on name (partial match), company, track of their talks, or talk count.
- **Schedule a Talk to a Time Slot:**
  - Provide an endpoint that assigns an accepted talk to a specific date and time slot. Reject the assignment if the same speaker is already scheduled in an overlapping time slot.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like track, difficulty, talk status, speaker name (partial match), and scheduled date.

### Edge Case Handling

- **Double-Booking a Speaker:**
  - Decide how to handle scheduling an accepted talk when the same speaker is already scheduled in an overlapping time slot. The natural answer is "reject with a clear conflict error" — document the exact error shape and which conflicting talk is identified in the response.
- **Accepting a Withdrawn Talk:**
  - Decide how to handle a talk whose status was previously set to "rejected" or "withdrawn" but is now being accepted (because of a last-minute opening). Should the status flip be allowed freely, require a separate "reinstate" action, or be blocked entirely? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to schedule different talks into the same time slot at the same time, or delete a speaker while a talk is being scheduled. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on talk-submission create, generate and store a structured abstract (headline, three key takeaways, target audience) from the speaker's free-form notes.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating speaker credentials or claims not present in the notes); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Track entity for managing track owners and capacity, or an Attendee entity for tracking who is registered for which talk.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many talks in one transaction, with all-or-nothing semantics.

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
