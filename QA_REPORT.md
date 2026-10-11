# Atharuhum QA Report — Clean Build

## Verification performed

- Python syntax compilation: passed.
- Frontend JavaScript syntax (`node --check`): passed.
- Render Blueprint YAML parse: passed.
- API end-to-end suite: **42/42 checks passed** against an isolated SQLite test database.
- Chromium UI smoke test: passed for home, registry, passport, Evidence Assistant, institution login, and visibility of source/asset/adaptation/review/collaboration forms; zero JavaScript page errors. UI smoke used mocked fetch responses because this execution environment blocks browser navigation to local/test origins. The API suite independently exercised the real local server.
- QR image decode: all five bundled QR codes decoded to the configured public verification URLs.
- Cross-organization access: private asset returned 404 to a different organization.
- Persistence: records survived server restart using the test SQLite database.
- Tamper checks: content hash validity and hash-linked event chain checked by API tests.

## Tested journeys and features

1. Public homepage and seeded registry.
2. Passport retrieval and source-linked verification.
3. Unknown record rejection.
4. Evidence Assistant grounding and refusal when no asset is selected.
5. Login, invalid credentials, protected audit endpoint, logout/session invalidation.
6. Source registration and source URL validation.
7. Private-by-default asset creation and duplicate ID rejection.
8. Private asset isolation from anonymous users and another organization.
9. Version history, divergence flag, correction, content hash updates.
10. Learning progress persistence and prevention of skipped prerequisite steps.
11. Attribution-bearing reuse, collaboration request, impact metrics.
12. Derived-content/adaptation workflow, parent lineage, required human review, prevention of approval while divergence is open, approval and publication.
13. QR denial for private content and dynamic QR generation for approved public content.
14. Audit chain integrity and database persistence across restart.

## Not claimed as completed

- Render has not been deployed or tested with this package in the user's account.
- PostgreSQL mode is implemented and the Render Blueprint is configured, but no live PostgreSQL server/credentials were available here for an actual connection smoke test. Automated tests use SQLite.
- The browser smoke test used mocked API responses due the environment's browser networking restriction; it was not a full browser-to-real-server E2E test.
- The Evidence Assistant is deterministic and record-grounded, not an external LLM/RAG implementation.
- No institution named in seed records is represented as an Atharuhum partner; public metadata does not imply reuse permission.
- Hashes and the database audit chain provide tamper evidence within the app; they are not a qualified digital signature, public blockchain, or C2PA manifest.
- Enterprise readiness still requires independent security review, SSO/MFA, full permission-policy audit, backup/restore drills, monitoring, load testing, CI/CD, legal review, and approved AI/RAG integration.
