# Freelance Client Invoicing

## Objective

Develop a freelance invoicing backend that empowers an independent contractor (or a small agency's bookkeeper) to manage clients and the invoices issued to each client. Each client has a name, a contact email, a billing address, a default hourly rate in cents, and a status (active / inactive); each invoice is a record tied to a client with an invoice number, an issue date, a due date, a list-free total amount in cents, and a status (draft / sent / paid / overdue / void). The system should make it easy to onboard clients, issue and track invoices, know what's outstanding, and search the billing history through a clean RESTful API. Prioritize correctness on the money and state model — an invoice's status transitions must be valid (you cannot pay a void invoice), and a client's outstanding balance should always be derivable from the sum of their unpaid invoices. The deliverable is a containerized service that runs locally via `docker compose up` and exposes a documented REST API.

## Functional Requirements

### Client Management

- **Add New Client:**
  - Admins should be able to onboard a client by specifying their name, contact email, billing address, default hourly rate in cents, and an initial status of "active."
- **View Client Details:**
  - Provide a dashboard endpoint where admins can view all clients, their contact email, status, total invoiced amount, outstanding balance (sum of unpaid invoices), and the count of associated invoices.
- **Edit Client Information:**
  - Allow admins to update client details such as contact email, billing address, default hourly rate, or status after the initial creation.
- **Delete Client:**
  - Admins should be able to delete a client record. Implement a confirmation requirement to prevent accidental deletions. Document the policy on deleting a client with invoices (cascade vs. block, and whether paid invoices must be preserved for tax records).

### Invoice Management

- **Add Invoice:**
  - Admins should be able to issue an invoice to a client, specifying an invoice number, an issue date, a due date, a total amount in cents, and an initial status of "draft."
- **Edit Invoice:**
  - Provide functionality to update an existing invoice, such as adjusting the total, changing the due date, or advancing the status — subject to valid state transitions.
- **Delete Invoice:**
  - Implement a feature for admins to remove an invoice. Like client deletion, this should include a confirmation step. Consider whether a "paid" invoice should be deletable at all.
- **View Invoices:**
  - Admins should be able to view a list of all invoices for a client, with search and filter capabilities based on status, issue/due date range, amount range, or invoice number (partial match).
- **Mark Invoice Paid:**
  - Provide an endpoint that atomically (1) transitions an invoice's status to "paid" and records the payment date and (2) recomputes the client's outstanding balance. Reject the request if the invoice is currently "draft" or "void."

### API Design & Developer Experience

- **Consistent Error Envelopes:**
  - All errors (validation, not-found, conflict) should return a consistent JSON shape with an error code, human-readable message, and request_id.
- **Liveness and Readiness:**
  - Expose /live and /ready endpoints. /live confirms the process is up; /ready confirms downstream dependencies (the database) are reachable.
- **Structured Request Logging:**
  - Every request should emit a structured log line containing method, path, status code, duration, and correlation id. Logs should be machine-parseable JSON.
- **Filtered Listings:**
  - List endpoints should support filter + sort query parameters across common fields like client name (partial match), invoice status, issue/due date range, and amount range.

### Edge Case Handling

- **Duplicate Invoice Number:**
  - Decide how to handle issuing a second invoice with an invoice number that already exists (globally or per-client). Should the system reject it, auto-increment, or allow the duplicate? Document your choice in the README.
- **Invalid Status Transition:**
  - Decide how to handle a request that attempts an illegal status transition (e.g., "void" → "paid", or "paid" → "draft"). The system should reject illegal transitions with a clear conflict error, and the allowed transition map should be documented in the README.
- **Invalid Input at the HTTP Boundary:**
  - Pydantic should validate every request body at the boundary and return a 422 with a clear field-by-field error envelope on malformed input.
- **Concurrent Mutations:**
  - Describe what happens if two clients try to mark the same invoice paid at the same time, or delete an invoice while the outstanding balance is being computed. The expected behavior should be documented in your README.

## AI-Assisted Enrichment (Azure OpenAI) — Required

The create/update flow must call **Azure OpenAI** to enrich each record before it is persisted. The model's output is validated by Pydantic and stored on the entity — the LLM is part of your write path, not a separate endpoint.

- **Enrichment in the write path:** When a record is created (and re-run when the fields it depends on change on update), call a deployed Azure OpenAI chat model to produce structured enrichment and persist it on the record. For this theme: on invoice create/update (or when it becomes overdue), draft and store a polite payment-reminder email (subject line and body) from the client name, amount, and days overdue.
- **Schema:** Add nullable enrichment columns/fields to the entity plus an `enrichment_status` (`pending` | `complete` | `failed`). Model the enrichment payload as a dedicated Pydantic model with explicit field constraints (Literal types, confidence `ge=0,le=1`, etc.).
- **Structured Output & Grounding:** Instruct the model to return JSON matching your enrichment schema, then validate its response through that Pydantic model. Persist only validated output; on validation failure set `enrichment_status = failed` — never store raw, unvalidated model text.
- **Graceful degradation:** An Azure failure (timeout, rate limit, invalid output) must **not** fail the underlying create/update. The record is saved with `enrichment_status = failed`/`pending`; log the failure with your correlation id. The core CRUD contract stays intact.
- **Deployment & Model Selection:** Provision an Azure OpenAI resource, deploy a chat model, and configure the client via environment variables — `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — loaded with python-dotenv. Never commit keys. In your README, name the model you deployed and justify the choice by capability vs. cost.
- **Config Parameters:** Explicitly set and document `temperature`, `max_tokens`, and one of `top_p` / `response_format`. Explain in the README why your values suit a structured, low-variance enrichment task.
- **Responsible AI:** Apply and document at least two safeguards — e.g., a system prompt that constrains scope and forbids fabricating safety-critical facts (inventing legal threats, late fees, or terms not present in the contract); marking enriched fields as AI-generated so they are distinguishable from user input; handling content-filter/refusal responses gracefully; not sending unnecessary PII to the model.
- **Testability:** The Azure client must be injectable/mockable so tests can (a) assert enrichment fields populate and validate on a stubbed response, and (b) assert a create still succeeds with `enrichment_status = failed` when the client raises.

## Stretch Goals

Stretch goals are features you want to add to an application, but they aren't required. For this project, Stretch Goals are a way to go above and beyond the minimum requirements and I look forward to seeing what unique features you will add to your project. Here are some examples you might consider:

- **Rate Limiting:**
  - Add Flask-Limiter to throttle requests per client IP. Choose a sensible limit and document why in your README.
- **Second Entity Relationship:**
  - Extend the model to support an additional related entity — for example a LineItem entity breaking each invoice into billable line items (description, quantity, rate), or a Payment entity supporting partial payments against an invoice.
- **Minimal Web UI:**
  - Add a single HTML page (or React app) that consumes your API and demonstrates the primary CRUD flow.
- **Persistent Audit Log:**
  - Record every mutation (create / update / delete) into an audit table with timestamp, action, entity, and user.
- **Bulk Import:**
  - Add an endpoint that accepts a JSON array (or CSV upload — for example, a time-tracking export) and inserts many invoices in one transaction, with all-or-nothing semantics.

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
