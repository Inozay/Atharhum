# Product Specification — Atharhum v3

## Product DNA

**SOURCE → PROVENANCE → TRUST → INTELLIGENCE → LEARNING → IMPACT → NEXT GENERATION**

## Core proposition

The problem is not that trusted knowledge is unavailable. The problem is that digital copies can lose the story behind the knowledge: origin, context, version and review.

Atharhum gives each knowledge item a digital identity and makes its journey visible, then uses that trusted context for grounded intelligence, learning and impact measurement.

## End-to-end user journey

1. **Discover** — search and filter knowledge records.
2. **Passport** — inspect identity, source, review, version and lineage.
3. **Verify** — query the verification engine.
4. **Trace** — inspect provenance and the knowledge graph.
5. **Ask** — use source-grounded AI modes: Ask, Explain, Trace, Translate, Compare.
6. **Learn** — complete a four-step personalized journey.
7. **Impact** — inspect the aggregated journey funnel and generate additional usage signals.

## Product modules

### 1. Knowledge Registry

A small, explicit record model for the current product nucleus. Each record contains identity, source, version, review, summary, evidence, provenance and learning steps.

### 2. Content Passport

The primary trust object. It is the place where the product makes provenance visible instead of hiding it in backend metadata.

### 3. Verification Engine

A real API lookup that returns identity, status, version, source, review and verification checks.

### 4. Provenance + Knowledge Graph

The timeline shows the linear history. The graph shows the broader relationship between source, content, review, AI, learning and impact.

### 5. Source-grounded Assistant

The current implementation intentionally works without an external API key. It retrieves from the local trusted registry and returns the source records used. The contract is ready for production RAG later.

### 6. Learning Journey

A four-step progression tied to the selected content. Progress persists per anonymous session.

### 7. Impact Intelligence

Events are recorded and aggregated into a funnel. The product distinguishes operational demonstration data from empirical impact claims.

## What is intentionally not claimed

- The current records are not presented as authenticated scholarly sources.
- The seeded impact numbers are not research results.
- The local assistant is not presented as a production-scale LLM.

These boundaries increase trust instead of weakening the product.

## Production expansion

The next architecture layer can add:

- PostgreSQL
- object storage for source documents
- document ingestion and chunking
- embeddings + vector retrieval
- graph database / RDF or property graph
- LLM provider
- citation verification/evaluation harness
- authentication and RBAC
- institutional workspaces
- human review workflows
- signed/immutable provenance records
- privacy and consent controls
