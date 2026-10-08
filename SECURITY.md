# Production security checklist

Before inviting external organizations:

1. Set `ATHARHUM_SECRET` to a unique random value.
2. Run behind HTTPS.
3. Keep the database on persistent storage.
4. Replace the demo password and seed account with your organization's SSO/identity provider.
5. Add rate limiting/WAF at the edge.
6. Move from SQLite to PostgreSQL for multi-instance/high-concurrency deployments.
7. Keep Quran Foundation credentials server-side only if integration is enabled.
8. Review each publisher's rights before copying or redistributing protected material.
9. Do not present the traceability indicator as a truth score.
