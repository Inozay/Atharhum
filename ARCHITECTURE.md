# ARCHITECTURE

## Backend modules
organizations
content
sources
rights
passports
verification
provenance
collaboration
learning
ai
impact
audit

## Data model
Organization 1—N Content
Content 1—N Versions
Content N—1 Source
Content 1—1 Passport
Content N—N Provenance edges
Content 1—N Learning journeys
Content 1—N Impact events
Organization N—N Collaboration requests

## Production evolution
Current local persistence: SQLite.
Production: PostgreSQL + pgvector, object storage, Redis/background jobs, RBAC/SSO, API keys, immutable audit stream.
