# أَثَرُهُم — Trusted Knowledge Infrastructure

**A source-to-impact workflow for Islamic knowledge in the AI era.** Atharhum is not another content feed: it gives a knowledge asset an identity, provenance record, rights and review disclosure, version history, verification URL/QR, learning journey, reuse attribution, collaboration request, and privacy-conscious impact events.

## Product journey

1. **Discover** a source-linked public asset in the knowledge registry.
2. **Verify** the source link, content identity/hash, review/AI disclosures, current version and divergence flag. A traceability indicator is not a truth score or religious authority.
3. **Inspect the Content Passport**: source, evidence URL, rights, review state, AI disclosure, parent lineage for derivatives, QR and version history.
4. **Ask the Evidence Assistant**. The current assistant is deliberately a deterministic, record-grounded helper for fields present in the passport. It refuses to invent unsupported answers. It is not an LLM, RAG system, or fatwa engine.
5. **Learn** through a three-step journey. Progress is stored in the database against a user/session key, not only browser local storage.
6. **Reuse** with generated attribution that includes source, Atharhum ID and version.
7. **Report divergence / correct / review**. Each lifecycle change creates a new version and content hash. Institutional assets remain private until a reviewer approves them.
8. **Create a source or asset**, request a translation/summary/audience adaptation workflow, record human approval, or submit an institutional collaboration request.
9. **Measure impact** through recorded views, verification, source opens, AI questions, learning, reuse, collaboration and corrections.

## Included functionality

- Arabic RTL responsive UI and guided public/Institution journey.
- Public registry seeded with **source metadata and examples**, not a claim of partnership or permission to redistribute third-party works.
- Knowledge Passport, source/evidence links, rights disclosure, review and AI disclosure, version history, QR verification.
- SHA-256 content record fingerprint and a hash-linked audit event chain. These detect mismatches/tampering within this database; they are **not** a qualified digital signature or external immutable ledger.
- Institutional login, server-side sessions, basic login rate limiting, private-by-default new assets, public publishing after human approval, organization association, and anonymous access to public assets.
- Source registration, asset registration, review/approval, derivative/adaptation workflow with parent lineage, divergence/correction workflow, reuse attribution, collaboration requests, learning progress and event metrics.
- SQLite for local development and automated tests; PostgreSQL support via `DATABASE_URL` for hosted use.

## Run locally

Python 3.11+ is required.

```bash
python -m pip install -r requirements.txt
python -m py_compile server.py
python tests/test_e2e.py
python server.py
```

Open `http://localhost:8080` (or your configured `PORT`).

Demo institution credentials for local evaluation only (local default only; production Blueprint disables demo seeding):

- Email: `demo@atharhum.org`
- Password: `Atharhum2026!`

Do not use the demo account on a publicly accessible deployment. Replace it with a real organization provisioning/SSO flow before external users are invited.

## Deploy to Render

**Choose Python runtime / Blueprint, not Docker.** The `render.yaml` defines a Python Web Service and a managed PostgreSQL database. No Dockerfile is expected or required.

1. Extract this archive.
2. Upload the **contents** of the extracted folder to the root of the GitHub repository; `server.py`, `render.yaml`, `requirements.txt`, `static/`, `qr/`, and `tests/` must be visible at the root.
3. In Render, create a Blueprint from that repository, review the managed PostgreSQL resource and service, then apply it. Do not reuse a service explicitly configured as Docker.
4. Build command: `pip install -r requirements.txt && python -m py_compile server.py`
5. Start command: `python server.py`
6. Health check: `/health`
7. Confirm `PUBLIC_BASE_URL` matches the final public service URL; QR codes are regenerated on startup from this setting.
8. After deploy, test `/health`, `/`, `/verify/ATH-TANZIL-001`, the login flow, and one full institutional asset/review journey.

If the PostgreSQL resource is unavailable in the chosen Render plan/region, configure a supported managed PostgreSQL database and set its connection string as `DATABASE_URL`. Never commit database credentials.

## Environment variables

- `DATABASE_URL`: PostgreSQL connection string. If absent, local SQLite is used.
- `ATHARHUM_SECRET`: random secret (at least 32 characters in production); required in production.
- `PUBLIC_BASE_URL`: canonical public URL used for QR generation.
- `PORT`: web server port supplied by hosting platform.
- `ATHARHUM_DB_PATH`: optional SQLite path for local testing only.

## Tests

`python tests/test_e2e.py` starts an isolated local server and checks health, home page, source registry, verification, unsupported-question refusal, authenticated and unauthorized access, private asset isolation, URL validation, asset/source creation, attribution, collaboration, divergence and correction, event metrics, persistent journey progress, audit-chain integrity, version history, adaptation lineage, human approval/publication, dynamic QR, logout, and database persistence after restart.

## Real-data and rights note

Seed records are grounded in public source metadata and link out to the source. This does not imply that Quran Foundation, Tanzil, Yaqeen Institute, IIIT, or C2PA partners with Atharhum. It also does not imply all linked works can be copied or redistributed. Each asset needs a rights decision specific to the publisher, edition, translation, and intended use. Quran Foundation API access requires approved credentials and its current terms. No live API credentials or third-party content scraping are included in this package.

## Honest production boundary

This is a tested production-oriented foundation, **not yet a fully enterprise-certified SaaS**. Before a broad institutional launch, finish and independently review: SSO/MFA and password reset, invitation/provisioning flows, complete organization/role/permission policies across every query, PostgreSQL deployment smoke test with actual Render credentials, managed backups/restore drill, external monitoring/alerting, formal privacy/retention policy, legal review of publisher rights, true RAG/LLM integration with approved source retrieval and human-reviewed translation, cryptographic signing/C2PA manifests, comprehensive browser E2E/CI and load/security testing. The bundled Evidence Assistant does not call an external model.
