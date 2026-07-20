# Pet Adoption Platform

## Objective

Develop a pet adoption backend that empowers a shelter administrator to manage a catalog of adoptable pets and the applications submitted by potential adopters. Each pet has profile information (name, species, age, intake date, health notes), and each application captures the applicant's contact info, household details, and the specific pet they're requesting. The system should make it easy to add pets to the catalog, track incoming applications, mark pets as adopted, and search the catalog and application queue through a clean RESTful API. Prioritize a clear lifecycle on the pet (available → application pending → adopted) so that the shelter never accidentally double-promises a pet. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Pet Management

- **Add New Pet:**
  - Admins should be able to create a new pet record by specifying the name, species (dog / cat / rabbit / other), age in years, intake date, and any health notes.
- **View Pet Details:**
  - Provide a dashboard endpoint where admins can view all pets, their species, age, intake date, current status (available / pending / adopted), and the number of open applications.
- **Edit Pet Information:**
  - Allow admins to update pet details such as health notes, age (annual updates), or the adoption status.
- **Delete Pet:**
  - Admins should be able to delete a pet record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a pet that has historical applications (cascade vs preserve for audit).

### Application Management

- **Add Application:**
  - Admins should be able to log an application from a potential adopter, specifying the applicant's name, contact email, household description, and the pet being requested.
- **Edit Application:**
  - Provide functionality to update existing application details, such as correcting the applicant's contact info or changing the application status (pending / approved / rejected / withdrawn).
- **Delete Application:**
  - Implement a feature for admins to remove an application from the queue. Like pet deletion, this should include a confirmation step.
- **View Applications:**
  - Admins should be able to view a list of all applications, with search and filter capabilities based on applicant name, application status, pet species, or date submitted.
- **Match an Application to a Pet:**
  - Provide an endpoint that approves an application and atomically marks the pet as adopted. All other open applications for the same pet should be automatically transitioned to a documented status (rejected / waitlisted).

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like species, age range, adoption status, application status, and date submitted.

### Edge Case Handling

- **Application for an Already-Adopted Pet:**
  - Decide how to handle a new application submitted for a pet whose status is already "adopted." Should the system reject the application, accept it with a warning, or accept it silently (the user may be checking if there are similar pets available)? Document your choice in the README.
- **Multiple Pending Applications for the Same Pet:**
  - Decide how the system handles many pending applications for one pet at the same time. When one is approved, what happens to the others? Are they auto-rejected, moved to a waitlist for similar pets, or left for the admin to handle manually? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to approve different applications for the same pet at the same time, or delete a pet while an application is being submitted. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on adoption-application create, rank the available pets against the applicant's stated preferences and store the ranked matches with a one-sentence reason for each.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating a pet's temperament, medical history, or suitability for a household); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Foster Home entity for tracking which pets are placed in temporary care, or a Veterinary Visit entity for medical history.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many pets in one transaction, with all-or-nothing semantics.

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
