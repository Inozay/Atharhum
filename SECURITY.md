# Security model and release checklist

## Implemented in this build

- Random production secret is required; the code refuses to start in production when `ATHARHUM_SECRET` is missing/too short.
- Production Blueprint disables demo account seeding. Local development alone seeds the demo account by default.
- One-time first-institution setup requires a generated `ATHARHUM_BOOTSTRAP_TOKEN`; remove the token from hosting environment after setup.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes, not plaintext. Sessions are random bearer tokens with 24-hour expiry and logout invalidation.
- Basic in-process login throttling; HTTPS is expected from the hosting platform.
- New institutional assets are private until human approval. Public QR routes do not serve private records.
- Asset reads enforce organization ownership for private records. Audit-event views are scoped to the signed-in institution/public records.
- User-provided source URLs must use HTTP(S); no URL is fetched server-side.
- JSON responses set no-store and nosniff headers; HTML includes a restrictive CSP compatible with the current inline UI.
- Content SHA-256 fingerprints and hash-linked audit events provide in-app tamper evidence, not external non-repudiation.

## Required before external institutional launch

1. Perform an independent security review and penetration test.
2. Implement SSO/OIDC, MFA, invitation/provisioning, password reset, and account recovery.
3. Audit all role/organization authorization paths, including exports, source records, collaboration records, and metrics.
4. Add persistent distributed rate limiting/WAF, alerting, structured observability, backups, and a tested restore procedure.
5. Run a live PostgreSQL/Render smoke test and load test; test migration/rollback strategy.
6. Move bearer credentials from localStorage to a hardened HttpOnly/Secure/SameSite session design where feasible.
7. Establish data retention, consent, privacy, and deletion policies for analytics.
8. Obtain legal review of every publisher/edition/license before copying, translating, or redistributing content.
9. Integrate any LLM/RAG provider only with server-side credentials, retrieval allowlists, citation validation, human approval, and explicit refusal for unsupported religious/legal conclusions.
10. Add signed provenance/C2PA manifests if cryptographic publisher identity is required; a database hash alone is not a digital signature.

Do not treat the traceability indicator as a truth score, a scholarly endorsement, or a fatwa. Public-source metadata does not imply a partnership with Atharuhum.
