# BugBountyHQ Production Task List

This backlog is based on the current Flask + SQLite MVP in `app.py` and the existing templates. IDs start at `BUGBT-01` and are ordered roughly by delivery dependency and risk reduction.

## Execution Tracker

| Task ID | Status | Owner | Notes |
|---|---|---|---|
| BUGBT-01 | Done | Worker Team / Main | Refactored into `bugbountyhq/` package with app factory, blueprints, config, DB helpers, and `wsgi.py`. Verified import and 16-route surface. |
| BUGBT-02 | Done | Worker Team / Main | Added SQLAlchemy models/sessions, Alembic scaffolding, initial migration, and route migration off raw `sqlite3`. Verified route smoke tests and submission detail fix. |
| BUGBT-03 | Done | Worker Team / Main | Production config now fails fast on missing/unsafe secrets and documents required env vars while preserving local development defaults. |
| BUGBT-04 | Done | Worker Team / Main | Added `pyproject.toml`, `.python-version`, pinned constraints workflow, and updated install instructions. |
| BUGBT-05 | Pending | Unassigned | |
| BUGBT-06 | Pending | Unassigned | |
| BUGBT-07 | Pending | Unassigned | |
| BUGBT-08 | Pending | Unassigned | |
| BUGBT-09 | Pending | Unassigned | |
| BUGBT-10 | Pending | Unassigned | |
| BUGBT-11 | Pending | Unassigned | |
| BUGBT-12 | Pending | Unassigned | |
| BUGBT-13 | Pending | Unassigned | |
| BUGBT-14 | Pending | Unassigned | |
| BUGBT-15 | Pending | Unassigned | |
| BUGBT-16 | Pending | Unassigned | |
| BUGBT-17 | Pending | Unassigned | |
| BUGBT-18 | Pending | Unassigned | |
| BUGBT-19 | Pending | Unassigned | |
| BUGBT-20 | Pending | Unassigned | |
| BUGBT-21 | Pending | Unassigned | |
| BUGBT-22 | Pending | Unassigned | |
| BUGBT-23 | Pending | Unassigned | |
| BUGBT-24 | Pending | Unassigned | |
| BUGBT-25 | Pending | Unassigned | |
| BUGBT-26 | Pending | Unassigned | |
| BUGBT-27 | Pending | Unassigned | |
| BUGBT-28 | Pending | Unassigned | |
| BUGBT-29 | Pending | Unassigned | |
| BUGBT-30 | Pending | Unassigned | |
| BUGBT-31 | Pending | Unassigned | |
| BUGBT-32 | Pending | Unassigned | |
| BUGBT-33 | Pending | Unassigned | |
| BUGBT-34 | Pending | Unassigned | |
| BUGBT-35 | Pending | Unassigned | |
| BUGBT-36 | Pending | Unassigned | |
| BUGBT-37 | Pending | Unassigned | |
| BUGBT-38 | Pending | Unassigned | |
| BUGBT-39 | Pending | Unassigned | |
| BUGBT-40 | Pending | Unassigned | |
| BUGBT-41 | Pending | Unassigned | |
| BUGBT-42 | Pending | Unassigned | |
| BUGBT-43 | Pending | Unassigned | |

## Foundation

### BUGBT-01: Restructure the app into a production-ready package
- Split `app.py` into modules for app factory, config, models/data access, routes, services, and utilities.
- Add a clear package layout such as `bugbountyhq/` with blueprints for web, API, admin, and integrations.
- Introduce environment-specific configuration classes for development, test, staging, and production.
- Define dependency boundaries so UI handlers do not talk directly to raw SQL in every route.
- Add a proper WSGI/ASGI entrypoint for deployment.

### BUGBT-02: Replace raw SQLite usage with a supported production database layer
- Move from SQLite to PostgreSQL for concurrent production workloads.
- Add SQLAlchemy or another maintained ORM/query layer plus migration tooling.
- Define versioned schema migrations for all current tables and future changes.
- Add connection pooling, retry behavior, and transaction management.
- Create seed scripts for demo and local development environments.

### BUGBT-03: Build a settings and secret-management strategy
- Remove insecure default secrets such as the hardcoded Flask secret fallback.
- Require all sensitive configuration via environment variables or secret manager integration.
- Document required env vars and safe defaults in `.env.example`.
- Add startup validation so the app fails fast when critical configuration is missing.

### BUGBT-04: Introduce consistent dependency and runtime management
- Pin and review all Python dependencies beyond just `Flask`.
- Add a reproducible environment flow using `venv`, `pip-tools`, `uv`, or Poetry.
- Define supported Python versions and enforce them in CI.
- Add dependency vulnerability scanning and scheduled upgrade cadence.

## Security

### BUGBT-05: Implement authentication and session management
- Add user accounts for platform admins, program owners, triagers, and researchers.
- Support secure login, logout, password reset, session expiry, and optional SSO.
- Store passwords with a strong hashing algorithm and enforce password policy.
- Prevent session fixation and protect session cookies with secure flags.

### BUGBT-06: Add authorization and role-based access control
- Define permissions for organization admins, program managers, analysts, and researchers.
- Restrict access to dashboard, program management, submission updates, and API actions.
- Ensure researchers only see allowed programs and their own submissions where applicable.
- Add server-side authorization checks to every route and API endpoint.

### BUGBT-07: Add request validation and safe error handling
- Validate JSON and form input using a schema layer.
- Return structured API validation errors instead of generic 500 responses.
- Replace blanket exception handling with explicit error mapping and logging.
- Serve HTML error pages for browser routes and JSON errors for API routes.
- Sanitize user-controlled content before rendering or storing where required.

### BUGBT-08: Add CSRF, security headers, and baseline web hardening
- Protect all state-changing HTML forms with CSRF tokens.
- Add standard headers including CSP, HSTS, X-Frame-Options, and X-Content-Type-Options.
- Enforce HTTPS in production and secure cookie settings.
- Review template rendering for XSS exposure and unsafe inline script patterns.

### BUGBT-09: Add abuse prevention and rate limiting
- Apply rate limits to login, public APIs, submission creation, and webhook endpoints.
- Add bot and spam controls for researcher-submitted findings.
- Introduce audit trails for privilege-sensitive actions.
- Add alerting for repeated failed auth and anomalous API behavior.

### BUGBT-10: Build a webhook verification and signing framework
- Verify webhook signatures for HackerOne, Bugcrowd, and future integrations.
- Add replay protection, request idempotency, and dead-letter handling.
- Log inbound events with traceable status for debugging and compliance.
- Reject malformed or unsigned integration traffic by default.

## Data Model and Domain Logic

### BUGBT-11: Redesign the data model around organizations and multi-tenancy
- Add organizations, users, memberships, and program ownership relationships.
- Scope all records by tenant to avoid cross-customer data exposure.
- Support multiple programs per organization with per-program settings and visibility.
- Plan tenant-aware indexes and uniqueness constraints.

### BUGBT-12: Normalize submissions into a complete vulnerability workflow model
- Add fields for state transitions, triage notes, asset, weakness/CWE, CVSS, duplicates, attachments, and remediation data.
- Track reporter communication, assignees, SLA dates, resolution timestamps, and bounty decision history.
- Support duplicate, informative, spam, and out-of-scope outcomes.
- Preserve immutable event history for every workflow transition.

### BUGBT-13: Build researcher profile and reputation logic
- Replace the static researchers table with user-linked researcher profiles.
- Track invitations, trust level, payout eligibility, tax status, and disclosure preferences.
- Calculate reputation from accepted findings, severity, duplicates, and response quality.
- Support researcher leaderboard data without relying on manual updates.

### BUGBT-14: Create a configurable bounty rules engine
- Store reward bands per severity, asset criticality, and program type.
- Support minimum, maximum, discretionary, and non-monetary rewards.
- Track approved payout amounts separately from suggested bounty values.
- Add reviewable decision logs for bounty changes and overrides.

### BUGBT-15: Add file attachments and evidence management
- Support secure upload of screenshots, PoCs, logs, and exploit artifacts.
- Store files in object storage with signed access URLs.
- Scan uploads for malware and enforce type and size limits.
- Associate attachments with submissions, comments, and remediation records.

## Product Workflows

### BUGBT-16: Build complete program management
- Expand programs to include type, scope targets, out-of-scope rules, disclosure policy, safe-harbor text, and reward model.
- Add draft, published, paused, archived, and private program states.
- Support editing, cloning, archiving, and deactivation workflows.
- Add validation for invalid or incomplete program configuration.

### BUGBT-17: Implement researcher onboarding and invitation flows
- Add researcher self-registration and admin invitation workflows.
- Support approval queues for private programs.
- Track acceptance of rules and legal terms before submission access.
- Add email verification and onboarding status tracking.

### BUGBT-18: Build submission intake with quality controls
- Improve the submission form with repro steps, affected asset, impact, CWE/CVSS guidance, and attachment support.
- Add duplicate detection hints and content quality checks.
- Block submissions to inactive or unauthorized programs.
- Support drafts and partially completed submissions.

### BUGBT-19: Build triage, assignment, and case management
- Add triage queues, assignee workflows, internal comments, status transitions, and priority.
- Support duplicate linking, severity review, and vendor communication states.
- Add saved filters, bulk actions, and analyst views for large volumes.
- Prevent invalid state transitions with explicit workflow rules.

### BUGBT-20: Build communication and notification workflows
- Add email notifications for submission receipt, updates, payout decisions, and comments.
- Support internal notifications for new findings and SLA breaches.
- Add notification preferences by user and role.
- Ensure outbound emails are templated, localized if needed, and auditable.

### BUGBT-21: Add payout and finance workflows
- Support payout approval, payment status, currency, and payout provider integration.
- Track bounty budgets by program and organization.
- Add finance reporting for approved, pending, and paid bounties.
- Store immutable payout ledger entries for reconciliation.

## API and Integrations

### BUGBT-22: Redesign the API as a versioned production API
- Introduce `/api/v1` namespacing and stable resource contracts.
- Add pagination, filtering, sorting, and field validation.
- Return consistent error payloads and HTTP semantics.
- Generate OpenAPI documentation and example requests.

### BUGBT-23: Add API authentication and key management
- Support scoped API tokens or OAuth for organizations and service integrations.
- Store hashed API keys and expose rotation workflows.
- Log API usage by token, organization, and endpoint.
- Add per-token permission scopes and expiration policies.

### BUGBT-24: Build outbound integrations
- Implement Jira ticket creation and sync.
- Implement Slack or Teams notifications for important events.
- Add webhooks for customer systems to consume platform updates.
- Build retryable background delivery with delivery logs and backoff.

### BUGBT-25: Complete inbound platform integrations
- Replace stub HackerOne and Bugcrowd webhook handlers with real mapping logic.
- Normalize external reports into internal submission records.
- Handle deduplication and source attribution for imported data.
- Add integration health status and sync visibility in the admin UI.

## Frontend and UX

### BUGBT-26: Refactor templates into a maintainable frontend structure
- Create a shared base layout and reusable components for nav, tables, forms, badges, and flash messages.
- Remove repeated markup across standalone templates.
- Standardize page-level metadata, title handling, and empty states.
- Add consistent server-rendered feedback for success and validation failures.

### BUGBT-27: Improve accessibility and responsive behavior
- Ensure keyboard navigation, color contrast, semantic headings, and accessible form labels.
- Add proper table responsiveness for smaller screens.
- Audit focus states, error messaging, and screen-reader support.
- Validate against WCAG 2.1 AA for core workflows.

### BUGBT-28: Build an admin-grade dashboard and reporting UI
- Add charts and filters for submission trends, severity distribution, resolution time, and payout totals.
- Show SLA status, workload by analyst, and program performance.
- Add exportable CSV and report views.
- Ensure metrics are based on explicit reporting queries, not page-level ad hoc calculations.

## Background Processing and Reliability

### BUGBT-29: Introduce background jobs and async task processing
- Add a worker system such as Celery, RQ, or Dramatiq.
- Move email sending, webhooks, imports, file scanning, and sync jobs out of request handlers.
- Add retry policies, visibility into failures, and admin requeue capability.
- Define idempotency patterns for retried work.

### BUGBT-30: Add structured logging, metrics, and tracing
- Emit JSON logs with request ids, actor ids, tenant ids, and error context.
- Add metrics for request latency, DB health, queue depth, and workflow events.
- Integrate distributed tracing or at least correlation ids across web and worker layers.
- Send logs and metrics to a production monitoring stack.

### BUGBT-31: Add health checks, readiness checks, and graceful failure behavior
- Separate liveness and readiness endpoints.
- Validate DB and queue connectivity in readiness checks.
- Add graceful shutdown handling for app and workers.
- Surface degraded dependency states without masking them as healthy.

### BUGBT-32: Add caching and performance optimization
- Introduce Redis for caching, rate limiting, and short-lived workflow state if needed.
- Cache expensive dashboard and reporting queries appropriately.
- Add indexes based on actual query patterns.
- Profile template rendering and database access under realistic load.

## DevEx, Testing, and Quality

### BUGBT-33: Build a real automated test suite
- Add unit tests for domain logic and validation.
- Add integration tests for routes, APIs, auth, and DB interactions.
- Add end-to-end tests for core user journeys such as program creation and submission triage.
- Add regression tests for security-sensitive behaviors and error handling.

### BUGBT-34: Add code quality gates and CI/CD
- Add linting, formatting, import checks, and type checking.
- Run tests and security scans on every pull request.
- Block deploys on failing quality gates.
- Publish build artifacts and deployment metadata from CI.

### BUGBT-35: Create reproducible local and staging environments
- Add containerized local development with app, DB, cache, and worker services.
- Define staging environments that mirror production closely enough for release validation.
- Add sample data generation for realistic QA workflows.
- Document environment bootstrapping in contributor docs.

### BUGBT-36: Add release, migration, and rollback procedures
- Define deployment runbooks and DB migration rollout process.
- Add rollback plans for code and schema changes.
- Version releases and maintain a changelog.
- Test zero-downtime or low-downtime upgrade paths where feasible.

## Compliance, Governance, and Support

### BUGBT-37: Add audit logging and immutable activity history
- Record who changed submission state, bounty amounts, program settings, and access controls.
- Make audit trails searchable and exportable for support and compliance.
- Protect audit data from tampering and accidental deletion.
- Define retention policies for activity history.

### BUGBT-38: Define data retention, privacy, and compliance controls
- Add retention settings for submissions, attachments, and account data.
- Support GDPR-style export and deletion workflows where applicable.
- Classify sensitive data and define encryption requirements at rest and in transit.
- Document privacy and data processing behavior.

### BUGBT-39: Add backup, restore, and disaster recovery processes
- Schedule automated backups for DB and file storage.
- Test restores regularly and document recovery steps.
- Define RPO and RTO targets for the service.
- Monitor backup freshness and restore success.

### BUGBT-40: Build operational admin and support tooling
- Add internal views for tenant support, integration troubleshooting, job retries, and audit review.
- Add feature flags and maintenance controls for safe rollout.
- Support impersonation or limited support access with strict audit logging.
- Create incident response and on-call documentation.

## Documentation and Go-To-Market Readiness

### BUGBT-41: Replace the current marketing/demo docs with technical product docs
- Rewrite `README.md` to describe the actual architecture, setup, and current capabilities.
- Document local setup, configuration, migrations, tests, and deployment flow.
- Remove or clearly label aspirational features that are not implemented.
- Add architecture decision records for major technical choices.

### BUGBT-42: Write customer-facing help and API documentation from implemented behavior
- Generate accurate API docs from the real contract.
- Write operator docs for program managers, triagers, and researchers.
- Add troubleshooting guides for common platform issues.
- Version the docs alongside the API and product releases.

### BUGBT-43: Define a production launch checklist
- Track launch-blocking requirements across security, observability, support, compliance, and performance.
- Add explicit signoff owners and evidence for each area.
- Include penetration testing, backup restore validation, and load testing before launch.
- Rehearse incident, rollback, and degraded-mode scenarios.

## Recommended execution order

1. `BUGBT-01` to `BUGBT-10`: stabilize architecture and eliminate obvious security failures.
2. `BUGBT-11` to `BUGBT-21`: build the real domain model and core product workflows.
3. `BUGBT-22` to `BUGBT-32`: productionize integrations, background work, and reliability.
4. `BUGBT-33` to `BUGBT-43`: enforce quality, operations, compliance, and launch readiness.
