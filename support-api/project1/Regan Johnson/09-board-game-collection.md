# Board Game Collection

## Objective

Develop a board game collection backend that empowers a hobbyist (or game cafe administrator) to maintain a catalog of games and a play-history log of every session that's been played. Each game has metadata (name, designer, min/max players, average play time, complexity rating), and each play session records the date, the players, the duration, and an optional winner. The system should make it easy to add games, log plays as they happen, and query the catalog and history through a clean RESTful API. Prioritize a clean separation between the game (a stable record) and a play session (a time-stamped event) so that statistics like "most-played game this year" come naturally. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Game Management

- **Add New Game:**
  - Admins should be able to create a new game by specifying its name, designer, minimum and maximum player counts, average play time in minutes, and a complexity rating from 1.0 to 5.0.
- **View Game Details:**
  - Provide a dashboard endpoint where admins can view all games, their player range, average play time, complexity, and the count of play sessions recorded.
- **Edit Game Information:**
  - Allow admins to update game details such as name (corrections), play time (revised after experience), or complexity rating.
- **Delete Game:**
  - Admins should be able to delete a game record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a game with play history (cascade vs preserve for audit).

### Play Session Management

- **Add Play Session:**
  - Admins should be able to log a play session for a game, specifying the date played, the list of player names, the actual duration in minutes, an optional winner's name, and optional notes.
- **Edit Play Session:**
  - Provide functionality to update existing play session details, such as correcting the date, adding a player who was missed, or recording the winner if it wasn't entered initially.
- **Delete Play Session:**
  - Implement a feature for admins to remove a play session. Like game deletion, this should include a confirmation step.
- **View Play Sessions:**
  - Admins should be able to view a list of all play sessions, with search and filter capabilities based on game name, date range, player name, or duration range.
- **Compute Statistics for a Game:**
  - Provide a read endpoint that returns the total play count, the average actual play time, the most frequent winner, and the date of the last session for a given game.

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like complexity range, player count, date range, and game name (partial match).

### Edge Case Handling

- **Play Session With Player Count Outside Game's Range:**
  - Decide how to handle a play session logged with more or fewer players than the game's stated min/max. Should the system reject the session, accept it with a warning (some games are playable outside the box-stated range), or accept it silently? Document your choice in the README.
- **Winner Not in the Player List:**
  - Decide how to handle a play session whose recorded winner is not present in the player list for that session (typo or intentional "house won"). Should the system reject the session, accept it with a flag, or accept it silently? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same game at the same time, or delete a play session while the statistics endpoint is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on game create/update, generate and store a suggested-fit summary (ideal group size, mood category, one-sentence rationale).
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (fabricating player counts, playtime, or age ratings); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Player entity for tracking individual players' stats across all games, or a Mechanic entity for tagging games by their core mechanics (worker placement, deck building, etc.).
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many games in one transaction, with all-or-nothing semantics.

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
