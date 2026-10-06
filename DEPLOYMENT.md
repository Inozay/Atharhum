# Atharuhum — deployment

## Render

The application is a single Docker Web Service. Render currently offers a free Web Service tier and does not require payment to deploy a free service. See the official Render documentation for current limits.

1. Push this repository to a public GitHub repository.
2. In Render choose **New → Web Service**.
3. Connect the GitHub repository.
4. Choose the **Free** instance.
5. Render detects the root `Dockerfile`.
6. Add:
   - `PUBLIC_BASE_URL=https://YOUR-SERVICE.onrender.com`
   - optionally `LLM_API_KEY`
   - optionally `LLM_BASE_URL`
   - optionally `LLM_MODEL`
7. Set health check to:
   `/api/health`
8. Deploy.
9. Test:
   - `/`
   - `/api/health`
   - `/verify.html?id=ATHAR-2026-0001`
   - `/api/qr/ATHAR-2026-0001.png`

### Important free-tier behaviour

The app stores the competition event log in SQLite. Render Free services have an ephemeral filesystem, so the SQLite file can be reset when the service restarts or redeploys. This does **not** prevent the demo from working; seed content is recreated automatically.

For a persistent institutional deployment, use PostgreSQL and a durable storage service.

## Local

```bash
docker compose up --build
```

or:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Open `http://localhost:8000`.
