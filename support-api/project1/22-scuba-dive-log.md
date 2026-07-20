# Scuba Dive Log

## Objective

Develop a scuba dive-log backend that empowers a diver (or a dive-shop operator) to maintain a registry of dive sites and the full log of dives performed at each one. Each dive site has a name, a body of water, a country/region, a typical depth in meters, a difficulty rating (beginner / intermediate / advanced / technical), and free-text access notes; each dive is a record tied to a site capturing the dive date, the maximum depth reached in meters, the bottom time in minutes, the water temperature in Celsius, the air/gas consumed as a percentage, the diver's name, and free-text observations. The system should make it easy to register sites, log dives, review a diver's history, and search the log through a clean RESTful API. Prioritize correctness on safety-relevant data — a dive's maximum depth should be validated against the site's typical depth range, and bottom time and depth must be physically plausible. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Dive Site Management

- **Add New Dive Site:**
  - Admins should be able to register a dive site by specifying its name, body of water, country/region, typical depth in meters, difficulty rating, and access notes.
- **View Dive Site Details:**
  - Provide a dashboard endpoint where admins can view all sites, their body of water, region, typical depth, difficulty, the date of the last logged dive, total dives recorded, and the average max depth across dives.
- **Edit Dive Site Information:**
  - Allow admins to update site details such as a corrected name, difficulty rating, typical depth, or access notes after the initial creation.
- **Delete Dive Site:**
  - Admins should be able to delete a dive site record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a site with logged dives (cascade vs. preserve the dive history).

### Dive Management

- **Add Dive:**
  - Admins should be able to log a dive at a site, specifying the dive date, maximum depth in meters, bottom time in minutes, water temperature in Celsius, air/gas consumed as a percentage, the diver's name, and free-text observations (e.g., "strong current at 18m, saw a reef shark").
- **Edit Dive:**
  - Provide functionality to update an existing dive, such as correcting the depth, bottom time, or observations.
- **Delete Dive:**
  - Implement a feature for admins to remove a logged dive. Like site deletion, this should include a confirmation step.
- **View Dives:**
  - Admins should be able to view a list of all dives at a site, with search and filter capabilities based on date range, diver name (partial match), depth range, bottom-time range, or observation content.
- **Log Dive with Safety Check:**
  - Provide an endpoint that atomically (1) creates a dive record for the site + diver + values and (2) evaluates it against safety limits (e.g., max depth vs. the site's rated depth, and a no-decompression time budget for the recorded depth). Reject the dive if the max depth exceeds a hard safety ceiling, and flag it if it exceeds recommended limits.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like body of water, region (partial match), difficulty rating, typical depth range, and last-dive date range.

### Edge Case Handling

- **Dive Deeper Than the Site's Rating:**
  - Decide how to handle logging a dive whose max depth exceeds the site's typical/rated depth. Should the system reject it, accept it and flag it as an outlier, or auto-raise the site's typical depth? Document your choice in the README.
- **Physically Implausible Dive Profile:**
  - Decide how to handle a dive with an implausible profile (e.g., 60m depth for 120 minutes of bottom time on air, or negative depth). The system should reject impossible values with a clear validation error, and the accepted ranges should be documented in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients log dives at the same site at the same time, or delete a dive while the site's average depth is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on dive/site create, generate and store a pre-dive briefing (hazards to watch for, a recommended gas plan, an experience-level recommendation) from the site difficulty, typical depth, access notes, and recent observations.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (unsafe gas-plan, depth, or decompression guidance); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Diver entity tracking each person's certification level and cumulative dive count across sites, or an Equipment entity logging the gear/tank configuration used on each dive.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, an export from a dive computer) and inserts many dives in one transaction, with all-or-nothing semantics.

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
