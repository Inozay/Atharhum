# أَثَرُهُم — Atharhum Production

A production-shaped MVP for knowledge provenance, verification, learning journeys, reuse attribution, institutional collaboration, AI evidence guardrails, and measurable impact.

## What is included
- Arabic RTL web application + Python backend.
- SQLite persistence with WAL mode for the single-instance deployment profile.
- Public verification route: `/verify/<CONTENT_ID>` and `/?verify=<CONTENT_ID>`.
- Knowledge Passport with source, rights, review, AI disclosure, version, trace and divergence state.
- Evidence Assistant: grounded-only answers tied to a selected record; no external LLM secret is required for the demo.
- Learning journey with event-based progress.
- Reuse + attribution logging.
- Institutional login, asset registration and collaboration requests.
- Correction/version workflow.
- Impact metrics and audit event log.
- QR verification images for the seeded records.
- Render Blueprint with `/health` HTTP health check and a persistent data disk mounted at `/opt/render/project/src/data`.

## Demo account
- Email: `demo@atharhum.org`
- Password: `Atharhum2026!`

Change/remove this seed account before external institutional use.

## Local run
```bash
python server.py
```
Then open `http://localhost:8080/`.

## Render
The included `render.yaml` is configured as a Python web service with `/health` and a persistent disk for the SQLite database. Render requires web services to bind to the `PORT` environment variable; this application does so automatically.

For higher scale or multiple instances, migrate the datastore to managed PostgreSQL and add organization-level tenancy/SSO before external institutional onboarding.

## Real-source notes
The seed registry uses public source metadata from Quran Foundation, Tanzil, Yaqeen Institute, IIIT and C2PA. Public-source listing does not imply partnership or endorsement. Verify each publisher's current rights before redistribution.

Quran Foundation API credentials, if later integrated, must remain server-side. Do not expose client secrets in browser code.

## Validation completed
The final build was tested from a clean runtime with:
- Python syntax compilation.
- Browser JavaScript syntax check.
- HTTP health check and root/verification route.
- Seed/bootstrap/content retrieval for all 5 records.
- Verification for all 5 records.
- 404 behavior.
- Anonymous authorization boundary.
- Login success/failure.
- Authenticated asset creation + duplicate protection.
- Reuse/attribution.
- Collaboration.
- Event logging.
- Grounded and insufficient-evidence AI paths.
- Divergence/correction + version increment.
- Impact metrics.
- SQLite persistence across process restart.
- QR decoding for all 5 QR images.
- Render Blueprint validation.
- Chromium UI interaction checks for home, registry, passport, AI, verification, auth gate, login and learning/impact surfaces.

## Production hardening still required
Before treating this as enterprise SaaS: managed PostgreSQL, SSO/OAuth, organization isolation, rate limiting/WAF, real RAG/LLM provider with server-side secrets, cryptographic provenance for published files (e.g. C2PA), derivative-copy monitoring, object storage, observability, backups/recovery drills, automated CI/E2E tests, and institution-specific legal/rights workflows.
