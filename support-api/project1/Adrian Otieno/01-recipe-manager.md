# Recipe Manager

## Objective

Develop a recipe management backend that empowers a home cook (or test kitchen administrator) to maintain a structured catalog of recipes and the ingredients that compose them. The system should make it easy to add, edit, search, and remove recipes through a clean RESTful API, with strong validation on inputs and clear feedback when something goes wrong. Prioritize correctness on the data layer — recipe ingredients must be modeled as first-class records, not free text — so that the catalog supports future capabilities like meal planning, shopping list generation, or nutrition analysis. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Recipe Management

- **Add New Recipe:**
  - Admins should be able to create a new recipe by specifying its name, serving size, total cook time in minutes, difficulty level, and step-by-step instructions.
- **View Recipe Details:**
  - Provide a dashboard endpoint where admins can view all recipes, their core metadata (servings, time, difficulty), and the count of associated ingredients.
- **Edit Recipe Information:**
  - Allow admins to update recipe details such as instructions, serving size, total time, or difficulty rating after the initial creation.
- **Delete Recipe:**
  - Admins should be able to delete a recipe. Implement a confirmation requirement (such as requiring the recipe id in the request body) to prevent accidental deletions.

### Ingredient Management

- **Add Ingredient:**
  - Admins should be able to add ingredients to a recipe, specifying the ingredient name, quantity, unit of measurement, and whether the ingredient is optional.
- **Edit Ingredient:**
  - Provide functionality to update existing ingredient details, such as adjusting quantity, switching units, or toggling optional status.
- **Delete Ingredient:**
  - Implement a feature for admins to remove ingredients from a recipe. Like recipe deletion, this should include a confirmation step.
- **View Ingredients:**
  - Admins should be able to view a list of all ingredients within a recipe, with search and filter capabilities based on ingredient name, unit type, or optional/required status.
- **Attach Ingredient to Recipe:**
  - Enable adding existing ingredients (or creating new ones inline) to recipes with a specified quantity and unit. Ensure that quantity and unit are validated together (you cannot have 3 ounces of "two cloves of garlic").

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like difficulty, total_time_minutes, and recipe name (partial match).

### Edge Case Handling

- **Recipe With No Ingredients:**
  - Decide how to handle a recipe created with no ingredients attached. Should the recipe be rejected at creation time, accepted with a "draft" flag, or accepted silently? Document your choice in the README.
- **Duplicate Ingredient on a Recipe:**
  - Decide how to handle attaching the same ingredient (by name) to a recipe twice. Should the action be prevented, should the quantities be summed, or should both entries coexist? Document your choice in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to modify the same recipe at the same time, or delete an ingredient while another request is reading it. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on recipe create/update, generate and store auto-tags (cuisine, dietary flags), a one-line summary, and an estimated difficulty level derived from the ingredients and instructions.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (allergen or dietary-safety claims); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a Cookbook entity that groups recipes, or a Tag system for categorizing recipes by cuisine.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload) and inserts many recipes in one transaction, with all-or-nothing semantics.

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
