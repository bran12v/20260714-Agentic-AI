# Wine Cellar

## Objective

Develop a wine cellar backend that empowers a collector (or sommelier managing a restaurant cellar) to maintain an inventory of bottles and the tasting notes recorded when bottles are opened. Each bottle has a label name, producer, varietal, vintage year, region, quantity on hand, and a purchase price per bottle in cents; each tasting note is a record tied to a bottle capturing the date tasted, a numeric score (50–100), aroma and palate free-text impressions, whether the bottle is at peak/past-peak, and the taster's name. The system should make it easy to add bottles, record consumption and tasting impressions, and search the cellar through a clean RESTful API. Prioritize correctness on inventory — the quantity on hand must never go negative, and opening a bottle for a tasting should decrement it atomically. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Bottle Management

- **Add New Bottle:**
  - Admins should be able to add a bottle by specifying its label name, producer, varietal, vintage year, region, quantity on hand, and purchase price per bottle in cents.
- **View Bottle Details:**
  - Provide a dashboard endpoint where admins can view all bottles, their producer, varietal, vintage, region, quantity on hand, average tasting score, and the count of associated tasting notes.
- **Edit Bottle Information:**
  - Allow admins to update bottle details such as a corrected producer, region, quantity on hand (a restock or correction), or purchase price after the initial creation.
- **Delete Bottle:**
  - Admins should be able to delete a bottle record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a bottle that has tasting notes (cascade vs. preserve the notes).

### Tasting Note Management

- **Add Tasting Note:**
  - Admins should be able to add a tasting note to a bottle, specifying the date tasted, a score from 50 to 100, aroma impressions, palate impressions, a peak assessment (young / peak / past_peak), and the taster's name.
- **Edit Tasting Note:**
  - Provide functionality to update an existing tasting note, such as revising the score or impressions.
- **Delete Tasting Note:**
  - Implement a feature for admins to remove a tasting note from a bottle. Like bottle deletion, this should include a confirmation step.
- **View Tasting Notes:**
  - Admins should be able to view a list of all tasting notes for a bottle, with search and filter capabilities based on score range, date-tasted range, peak assessment, taster name (partial match), or impression content.
- **Open a Bottle:**
  - Provide an endpoint that atomically (1) decrements the bottle's quantity on hand by one and (2) creates a tasting note for the bottle + taster + date + score. Reject the request if the quantity on hand is already zero.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like varietal, region (partial match), vintage year range, producer (partial match), quantity range, and average score.

### Edge Case Handling

- **Opening a Bottle That's Out of Stock:**
  - Decide how to handle opening a bottle whose quantity on hand is zero. Should the system reject the request, allow a negative quantity, or auto-restock? The chosen behavior — rejecting — should be enforced and documented in the README.
- **Tasting Note on an Out-of-Stock Bottle:**
  - Decide how to handle adding a standalone tasting note (not via the open endpoint) to a bottle with zero quantity on hand — perhaps from a bottle tasted elsewhere. Should the system allow it without touching inventory, reject it, or require a flag? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to open the last bottle at the same time, or delete a tasting note while the average score is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on bottle create/update, generate and store a food-pairing suggestion (recommended dish, a reason, and a serving-temperature suggestion) from the varietal, region, and tasting notes.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating vintage, provenance, or alcohol-content facts); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Producer/Winery entity grouping bottles by maker, or a StorageLocation entity tracking which rack/bin each bottle occupies.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a distributor's invoice) and inserts many bottles in one transaction, with all-or-nothing semantics.

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
