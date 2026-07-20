# Course Enrollment System

## Objective

Develop a course enrollment backend that empowers a registrar (or department administrator) to manage a catalog of courses offered each term and the students enrolled in each course. Each course captures the course code, title, instructor, schedule, semester, and a maximum capacity; each enrollment records which student is in which course, when they enrolled, their current status (enrolled / waitlisted / dropped / completed), and their final grade if applicable. The system should make it easy to publish courses, manage enrollments and the waitlist as students drop or add, and review historical enrollment data through a clean RESTful API. Prioritize correct capacity arithmetic — a course should never have more "enrolled" students than its capacity — and ensure that waitlist promotion happens atomically when a seat opens up. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Course Management

- **Add New Course:**
  - Admins should be able to create a new course by specifying its course code (e.g., "CS-301"), title, instructor name, semester (e.g., "Fall 2026"), meeting schedule (free-text or structured), and maximum enrollment capacity.
- **View Course Details:**
  - Provide a dashboard endpoint where admins can view all courses, their instructor, semester, capacity, current enrolled count, current waitlist length, and percent full.
- **Edit Course Information:**
  - Allow admins to update course details such as the title (a typo correction), instructor (a swap mid-term), schedule, or capacity (which may free up seats or push enrolled students into a waitlist state).
- **Delete Course:**
  - Admins should be able to delete a course. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a course with active enrollments (cascade vs. block until enrollments are dropped).

### Enrollment Management

- **Add Enrollment:**
  - Admins should be able to enroll a student into a course, specifying the student name, student id, and the enrollment date. The status should default to "enrolled" if the course has capacity, or "waitlisted" if it's full.
- **Edit Enrollment:**
  - Provide functionality to update existing enrollment details, such as the status (enrolled / waitlisted / dropped / completed) or the final grade once the course is over.
- **Delete Enrollment:**
  - Implement a feature for admins to remove an enrollment. Like course deletion, this should include a confirmation step. Document the policy on whether removing an enrollment is the same as marking it "dropped" (for audit history) or an actual record removal.
- **View Enrollments:**
  - Admins should be able to view a list of all enrollments for a course, with search and filter capabilities based on status, student name (partial match), enrollment date, or grade range.
- **Process Waitlist Promotion:**
  - Provide an endpoint that, when a student drops or is removed from an enrolled course, atomically promotes the next waitlisted student into the enrolled state (FIFO order, or by a documented priority rule). The promotion must not exceed the course's capacity under any concurrent-request scenario.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like semester, instructor, course code (partial match), capacity range, and percent-full threshold.

### Edge Case Handling

- **Enrollment Beyond Capacity:**
  - Decide how to handle an enrollment request when the course is already at capacity. The natural answer is "place into the waitlist with status `waitlisted`" — document the exact response shape (does it return success-with-waitlist, or a soft-error indicating the enrollment was queued?).
- **Dropping After the Drop Deadline:**
  - Decide how to handle dropping a student after a configurable drop deadline has passed. Should the system block the drop, accept it with a "late_drop" status that is distinct from a normal drop, or accept it silently? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to enroll different students into the last seat of a course at the same time. Capacity arithmetic is especially sensitive to race conditions; document how you prevent double-enrollment beyond capacity. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on course create/update, generate and store a catalog blurb (one-paragraph overview, three learning outcomes, target audience) from the instructor-provided learning objectives.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating accreditation, prerequisites, or outcomes not backed by the objectives); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Student entity that tracks each student across multiple enrollments and semesters, or a Prerequisite entity that enforces course-prerequisite chains at enrollment time.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many enrollments in one transaction, with all-or-nothing semantics.

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
