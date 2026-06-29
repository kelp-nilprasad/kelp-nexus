# Kelp Nexus — Engineering Knowledge Portal

A central, searchable home for technical research, POCs, benchmarks, architecture
docs, RFCs, and HTML reports. Think Medium + GitHub + Confluence for engineering.

## Stack

| Layer    | Tech |
|----------|------|
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn-style UI, React Query |
| Backend  | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Database | PostgreSQL + pgvector |
| Storage  | Azure Blob (Azurite locally) |
| Search   | Postgres full-text search (pluggable semantic search via pgvector) |
| Auth     | Azure AD / Entra OIDC SSO + local dev-login fallback |
| AI       | Claude (summaries, tags, RAG) — feature-flagged |

## Quick start (Docker)

```bash
docker compose up --build
# web → http://localhost:3000   api → http://localhost:8000/docs
# seeded login: admin@kelp.dev / password123
```

The API container runs migrations + seed automatically on first boot.

## Local development (without Docker)

```bash
# 1. Postgres (pgvector) + Azurite
docker compose up db azurite

# 2. API
cd apps/api
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload

# 3. Web
cd apps/web
npm install
npm run dev
```

## Repository layout

```
apps/web    Next.js frontend
apps/api    FastAPI backend (models, routers, services, migrations, tests)
infra       Dockerfiles, Kubernetes manifests
docs        PRD, TDD, architecture, ER, API, wireframes, deployment guide, roadmap
```

## Tests

```bash
cd apps/api && pytest          # unit (no DB) + integration (needs Postgres)
cd apps/web && npm run test    # vitest
```

See [`docs/`](docs/) for the full PRD, technical design, and roadmap.
