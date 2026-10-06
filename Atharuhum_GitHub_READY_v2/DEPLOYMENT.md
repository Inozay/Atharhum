# Atharuhum deployment

## Recommended: one-service deployment on Render

Atharuhum is packaged as a single Docker web service: FastAPI serves both the API and the frontend. This avoids separate frontend/API configuration and makes the QR verification URL use the same public domain.

1. Push the repository to a **public** GitHub repository.
2. In Render, choose **New → Web Service** and connect the repository.
3. Select **Docker** runtime. Render will use the root `Dockerfile`.
4. Add environment variable:
   - `PUBLIC_BASE_URL` = the final public URL of the Render service (for example `https://atharuhum.onrender.com`).
5. Health check: `/api/health`.
6. Deploy.
7. Open the public URL and test:
   - dashboard
   - Verify Content
   - QR code
   - AI demo questions
   - Learning Journey
   - live impact events

### Important
SQLite is used for a lightweight hackathon demonstration. For production scale, replace it with PostgreSQL and add authentication/RBAC, durable object storage, rate limiting, audit logs, monitoring, backups, and a curated production source registry.

## Local

```bash
docker compose up --build
```
Open `http://localhost:8000`.
