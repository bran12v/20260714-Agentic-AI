# Issue / Bug Tracker

## Objective

Develop a lightweight issue and bug tracking backend that empowers a project lead (or engineering team administrator) to manage multiple software projects and the issues filed against each project. Each project groups its own backlog of bugs, feature requests, and improvements; each issue carries a title, description, severity, status, and assignee, with a chronological log of comments documenting investigation and resolution. The system should make it easy to file issues, triage them by severity, move them through a status lifecycle (open → in progress → resolved → closed), and audit the comment trail through a clean RESTful API. Prioritize a clean parent-child relationship between issues and comments so that the full history of an issue is recoverable from the API. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Project Management

- **Add New Project:**
  - Admins should be able to create a new project by specifying its name, code repository URL, owner (a person or team name), and an optional description.
- **View Project Details:**
  - Provide a dashboard endpoint where admins can view all projects, their owner, total issue count, open issue count, and date of the last activity.
- **Edit Project Information:**
  - Allow admins to update project details such as name, repository URL, owner, or description.
- **Delete Project:**
  - Admins should be able to delete a project. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a project with open issues (cascade vs. block until issues are closed).

### Issue Management

- **Add Issue:**
  - Admins should be able to file an issue against a project, specifying the title, a Markdown-formatted description, severity (low / medium / high / critical), initial status (open), and optionally an assignee and a list of labels.
- **Edit Issue:**
  - Provide functionality to update existing issue details, such as the title, description, severity, assignee, labels, or status (open / in_progress / resolved / closed / wont_fix).
- **Delete Issue:**
  - Implement a feature for admins to remove an issue. Like project deletion, this should include a confirmation step. Document the policy on deleting an issue with comments attached.
- **View Issues:**
  - Admins should be able to view a list of all issues within a project, with search and filter capabilities based on status, severity, assignee, label, or title (partial match).
- **Add Comment to an Issue:**
  - Provide an endpoint that appends a timestamped comment (author + body) to an issue. Comments are append-only — they capture the chronological investigation trail and should not be editable after creation.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like status, severity, assignee, label, and title (partial match).

### Edge Case Handling

- **Reopening a Closed Issue:**
  - Decide how to handle moving an issue from "closed" or "wont_fix" back to "open" or "in_progress." Should the status transition be allowed freely, require a separate "reopen" action that posts an automatic comment, or be blocked entirely? Document your choice in the README.
- **Assigning an Issue to a Project's Archived State:**
  - Decide how to handle filing a new issue against (or assigning a user to) a project whose owner has marked it archived/read-only. Should the system reject the operation, accept it but flag it, or accept it silently? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same issue at the same time, or delete an issue while another request is adding a comment. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on issue create, classify the free-form report and store a suggested severity, likely component, suggested labels, and a one-sentence rationale.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (inventing CVEs, security severities, or components that do not exist); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Sprint entity that groups issues into time-boxed iterations, or a User entity for managing assignees and reporters as first-class records.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many issues in one transaction, with all-or-nothing semantics.

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
