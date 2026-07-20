# Film Watchlist & Reviews

## Objective

Develop a film watchlist backend that empowers a cinephile (or a small film-club administrator) to maintain a catalog of films they intend to watch or have watched, along with the reviews written after each viewing. Each film has a title, director, release year, runtime in minutes, genre, and a watch status (want_to_watch / watching / watched / abandoned); each review is a record tied to a film with a numeric rating (1–10), a one-line verdict, a longer body of free-text thoughts, the reviewer's name, and the date watched. The system should make it easy to queue films, mark them watched, capture reviews, and search the catalog through a clean RESTful API. Prioritize correctness on the relationship — reviews must be first-class records tied to a film, and a film's watch status should be consistent with whether it has any reviews. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Film Management

- **Add New Film:**
  - Admins should be able to add a film by specifying its title, director, release year, runtime in minutes, genre, and an initial watch status of "want_to_watch."
- **View Film Details:**
  - Provide a dashboard endpoint where admins can view all films, their core metadata (director, year, runtime, genre), current watch status, the count of associated reviews, and the average rating across reviews.
- **Edit Film Information:**
  - Allow admins to update film details such as a corrected title, director, genre, or watch status after the initial creation.
- **Delete Film:**
  - Admins should be able to delete a film. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a film that has reviews (cascade vs. block).

### Review Management

- **Add Review:**
  - Admins should be able to add a review to a film, specifying a rating from 1 to 10, a one-line verdict, a free-text body, the reviewer's name, and the date watched.
- **Edit Review:**
  - Provide functionality to update an existing review, such as revising the rating, verdict, or body after a rewatch.
- **Delete Review:**
  - Implement a feature for admins to remove a review from a film. Like film deletion, this should include a confirmation step.
- **View Reviews:**
  - Admins should be able to view a list of all reviews for a film, with search and filter capabilities based on rating range, reviewer name (partial match), date-watched range, or verdict/body content.
- **Mark Film Watched:**
  - Provide an endpoint that atomically (1) creates a review for the film + reviewer + rating + date watched and (2) updates the film's watch status to "watched." Reject the request if a rating outside 1–10 is supplied.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like genre, director (partial match), release year range, runtime range, watch status, and average rating.

### Edge Case Handling

- **Review on an Unwatched Film:**
  - Decide how to handle adding a review to a film whose status is "want_to_watch." Should the system reject the review, auto-advance the film to "watched," or accept the review and leave the status alone? Document your choice in the README.
- **Duplicate Review from the Same Reviewer:**
  - Decide how to handle a second review from the same reviewer on the same film. Should it be prevented, treated as an update to the existing review, or allowed as a separate rewatch entry? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to add a review to the same film at the same time, or delete a review while the average rating is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on watchlist-entry create, generate and store a recommendation signal (a reason and a predicted rating) from the genres and directors the user has rated highly.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating cast, runtime, or content-rating facts); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Person entity for directors and actors linked to many films, or a Tag/List system for grouping films into themed collections.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, an exported letterboxd list) and inserts many films in one transaction, with all-or-nothing semantics.

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
