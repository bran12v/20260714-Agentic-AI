# Aquarium Water Quality

## Objective

Develop an aquarium water-quality backend that empowers a hobbyist (or an aquarium-store technician) to maintain a registry of tanks and the full history of water-test readings for each one. Each tank has a name, volume in liters, water type (freshwater / saltwater / brackish), the date it was set up, and a current health status (healthy / watch / critical / cycling); each reading is a timestamped record of a water test — capturing temperature in Celsius, pH, ammonia in ppm, nitrite in ppm, nitrate in ppm, and free-text notes, along with the tester who took it. The system should make it easy to register tanks, log readings, spot dangerous parameters, and search the history through a clean RESTful API. Prioritize a single source of truth for tank health — the current status should always be consistent with the most recent reading evaluated against safe thresholds. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Tank Management

- **Add New Tank:**
  - Admins should be able to register a tank by specifying its name, volume in liters, water type, setup date, and an initial status of "cycling."
- **View Tank Details:**
  - Provide a dashboard endpoint where admins can view all tanks, their volume, water type, current status, the values from the last reading, the date of the last reading, and total readings recorded.
- **Edit Tank Information:**
  - Allow admins to update tank details such as name, volume (a correction), water type, or current status (with the understanding that status changes should also be reflected by the reading history).
- **Delete Tank:**
  - Admins should be able to delete a tank record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a tank with a reading history (cascade vs. preserve the readings).

### Reading Management

- **Add Reading:**
  - Admins should be able to log a water-test reading against a tank, specifying the date, the tester, temperature in Celsius, pH, ammonia, nitrite, and nitrate in ppm, and free-text notes (e.g., "cloudy water after feeding, did a 20% water change").
- **Edit Reading:**
  - Provide functionality to update an existing reading, such as correcting the tester's name, adjusting a mistyped value, or amending notes.
- **Delete Reading:**
  - Implement a feature for admins to remove a reading. Like tank deletion, this should include a confirmation step. Note that deleting the most recent reading that set the tank's current status should surface the implication in the response.
- **View Readings:**
  - Admins should be able to view a list of all readings for a tank, with search and filter capabilities based on date range, tester name (partial match), value ranges (e.g., ammonia above a threshold), or notes content.
- **Log Reading and Evaluate:**
  - Provide an endpoint that atomically (1) creates a reading for the tank + tester + values and (2) evaluates the values against safe thresholds and updates the tank's status accordingly (e.g., any ammonia or nitrite above zero → "critical"). Reject the request if any parameter is physically impossible (e.g., pH outside 0–14).

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like water type, status, volume range, setup date range, and last-reading date range.

### Edge Case Handling

- **Reading on a Cycling Tank:**
  - Decide how to handle a reading on a tank whose status is "cycling" — where high ammonia/nitrite is expected. Should the evaluation still flag it "critical," suppress the alert during cycling, or auto-graduate the tank to "healthy" once parameters are safe? Document your choice in the README.
- **Out-of-Range Chemistry Values:**
  - Decide how to handle values that are outside physically plausible ranges (negative ppm, pH of 20, temperature of 500°C). The system should reject impossible values with a clear validation error, and the accepted ranges should be documented in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients log readings for the same tank at the same time, or delete a reading while the tank status is being re-evaluated. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on reading create, diagnose from the tank's recent readings and a symptom description and store the suspected cause, a recommended corrective action, and an urgency level.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (unsafe chemical-dosing recommendations); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example an Inhabitant entity tracking the fish and invertebrates in each tank (with species and stocking date), or a Threshold profile entity holding per-water-type safe ranges.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, an export from a test-strip reader app) and inserts many readings in one transaction, with all-or-nothing semantics.

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
