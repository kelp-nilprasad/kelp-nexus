# Production Deployment Guide — Kelp Nexus

## 1. Prerequisites

- Kubernetes cluster (AKS recommended) with an nginx ingress + cert-manager.
- **Azure Database for PostgreSQL Flexible Server** with the `vector` extension
  enabled (`CREATE EXTENSION vector;`).
- **Azure Storage account** with a private container `reports`.
- **Azure AD app registration** for SSO (redirect URI
  `https://<host>/api/v1/auth/callback`, scopes `openid email profile`).
- A container registry (GHCR is wired in CI) and `kubectl` access.

## 2. Configure secrets

Edit `infra/k8s/01-config.yaml` (or better, manage with External Secrets / Sealed
Secrets). Required values:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://<user>:<pw>@<pg-host>:5432/kelp_nexus` |
| `JWT_SECRET` | strong random string (e.g. `openssl rand -hex 32`) |
| `AZURE_STORAGE_CONNECTION_STRING` | storage account connection string |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | from app registration |
| `ANTHROPIC_API_KEY` | only if `ENABLE_AI=true` |

In `kelp-config`, set `CORS_ORIGINS` and the ingress `host` to your real domain and
keep `DEV_LOGIN=false`.

## 3. Build & push images

CI does this on merge to `main`. Manually:

```bash
docker build -f infra/docker/Dockerfile.api -t ghcr.io/<org>/kelp-nexus-api:latest .
docker build -f infra/docker/Dockerfile.web -t ghcr.io/<org>/kelp-nexus-web:latest .
docker push ghcr.io/<org>/kelp-nexus-api:latest
docker push ghcr.io/<org>/kelp-nexus-web:latest
```

## 4. Deploy

```bash
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl apply -f infra/k8s/01-config.yaml
# Using managed Postgres? skip 02-postgres.yaml and point DATABASE_URL at it.
kubectl apply -f infra/k8s/02-postgres.yaml
kubectl apply -f infra/k8s/03-migrate-job.yaml      # alembic upgrade head
kubectl wait --for=condition=complete job/kelp-migrate -n kelp-nexus --timeout=120s
kubectl apply -f infra/k8s/04-api.yaml
kubectl apply -f infra/k8s/05-web.yaml
kubectl apply -f infra/k8s/06-ingress.yaml
```

Verify:

```bash
kubectl -n kelp-nexus get pods
curl -fsS https://<host>/api/v1/../health   # API health via ingress
```

## 5. First-run data

The migrate Job only runs migrations. Seed reference data (categories) via the
admin UI, or run the seed once against a fresh DB:

```bash
kubectl -n kelp-nexus run seed --rm -it --restart=Never \
  --image=ghcr.io/<org>/kelp-nexus-api:latest \
  --env-from=... -- python -m app.db.seed
```

Skip seeding in production if you don't want demo content.

## 6. Operations

- **Migrations**: every release runs the migrate Job (wire as a Helm/Argo
  pre-upgrade hook) before new API pods roll.
- **Scaling**: HPAs scale API (2→10) and web (2→6) on CPU. Tune thresholds.
- **Backups**: rely on managed Postgres PITR; Azure Blob is durable + versioned.
- **Observability**: scrape `/health`; ship structured logs; alert on 5xx and
  search latency.
- **Secrets rotation**: rotate `JWT_SECRET` (invalidates sessions) and storage
  keys on schedule.

## 7. Security checklist

- [ ] `DEV_LOGIN=false` in production.
- [ ] Strong `JWT_SECRET`; cookies `Secure` (auto when `ENVIRONMENT!=development`).
- [ ] Storage container private; downloads via short-lived SAS.
- [ ] Ingress enforces TLS; HSTS at the edge.
- [ ] RBAC verified (viewer cannot mutate; admin routes gated).
- [ ] HTML render endpoint returns CSP + nosniff; viewer iframe sandboxed.
- [ ] Network policy restricting pod egress to PG + Storage + AAD + AI only.
```
