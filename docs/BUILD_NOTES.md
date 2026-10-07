# Build Notes — Atharhum v3

## لماذا هذه النسخة مختلفة؟

الهدف ليس إنتاج واجهة جميلة فقط. كل مسار رئيسي في المنتج ينفذ وظيفة حقيقية أو يقرأ/يكتب حالة حقيقية.

### Product loop

`Discover → Passport → Verify → Trace → Ask → Learn → Impact`

### Backend

FastAPI serves the UI and API from one Docker service. SQLite provides a zero-configuration persistence layer for events and learning progress. The interfaces are intentionally small so the storage and retrieval layers can later be replaced by PostgreSQL, a vector database and a graph database.

### Trust layer

- Content identity
- Source
- Version
- Review record
- Provenance timeline
- Dynamic QR verification
- Knowledge graph

### Intelligence layer

The current assistant is source-grounded local retrieval. It supports multiple interaction modes and returns source records. Unsupported questions receive an explicit boundary response.

### Learning layer

Learning progress is stored per anonymous session and content item. Completing a step records a corresponding event.

### Impact layer

Events are persisted in SQLite. The funnel is calculated from the event log and includes seeded operational demonstration data. The UI explicitly avoids presenting these numbers as research findings.

### Deployment correction

The previous Dockerfile referenced a non-existent `data` directory. v3 removes that invalid copy step and keeps all runtime state in the application storage layer.
