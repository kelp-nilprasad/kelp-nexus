# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Kelp Nexus — an internal Engineering Knowledge Portal (Medium + GitHub + Confluence for
engineering): a searchable home for technical research, POCs, benchmarks, RFCs, and HTML
reports. Monorepo with two independently-run apps under `apps/`: a Next.js frontend
(`apps/web`) and a FastAPI backend (`apps/api`). There is **no root package manager /
workspace runner** — each app is built and run on its own.

## Commands

### Backend (`apps/api`, Python ≥3.11)
```bash
cd apps/api
pip install -e ".[dev]"
alembic upgrade head            # run migrations
python -m app.db.seed           # seed demo data + users
uvicorn app.main:app --reload   # serve on :8000  (Swagger at /docs)

pytest                          # full suite
pytest tests/test_security.py             # one file
pytest tests/test_reports_api.py::test_x  # one test
ruff check app                  # lint
mypy app                        # type check
```
DB-backed tests **auto-skip** when Postgres is unreachable, so `pytest` always runs the
pure-unit suite (sanitization, JWT) anywhere. Tests create tables directly from
`Base.metadata` against the configured DB (not via Alembic).

### Frontend (`apps/web`, Node)
```bash
cd apps/web
npm install
npm run dev        # :3000
npm run typecheck  # tsc --noEmit
npm run lint       # next lint
npm run test       # vitest run
```
**Never run `npm run build` while `next dev` is live** — it corrupts `.next/` and the dev
server starts returning 500s. If that happens: stop dev, `rm -rf .next`, restart.

### Full stack (Docker)
```bash
docker compose up --build       # web :3000, api :8000; API auto-migrates + seeds on boot
```

## Architecture (the non-obvious parts)

**Config / DB URL** (`apps/api/app/core/config.py`): a single `Settings` (pydantic-settings,
reads `apps/api/.env`). Either set `DATABASE_URL` directly **or** the discrete `DB_*` parts,
which a `model_validator` assembles into a `postgresql+psycopg://` URL. Several env aliases
exist for the user's naming: `AZURE_ACCOUNT`→`azure_account_name`,
`AZURE_CONTAINER_PATH`→`azure_blob_endpoint`. `settings` is a module-level `lru_cache`
singleton.

**pgvector is optional.** Local/dev Postgres often lacks the `vector` extension. Both the
initial migration (`0001_initial.py`) and the test `conftest.py` probe
`pg_available_extensions` and **skip the `embeddings` table** when absent. Do not assume
pgvector exists; keep new vector-dependent code behind the same guard.

**Migrations are idempotent.** Because the SQLAlchemy models all join `Base.metadata`, a
stray `create_all` (e.g. in tests/seed) can create tables ahead of Alembic. Migrations
0002/0003 guard with an `inspect(...).get_table_names()` early-return. Follow this pattern
when adding migrations that might race with model metadata.

**Auth** (`core/deps.py`, `core/security.py`, `routers/auth.py`): app-issued JWT carried as
an httpOnly `access_token` cookie *or* `Authorization: Bearer`. RBAC via
`require_role(Role.x)` against a `viewer<author<editor<admin` rank table. Two front doors:
MSAL/Entra ID SSO (`core/msal_client.py`, active only when `MSAL_CLIENT_ID`+`MSAL_TENANT_ID`
set) and a dev-login fallback (`DEV_LOGIN=true`) with seeded accounts. Passwords use `bcrypt`
**directly** (input truncated to 72 bytes) — passlib was removed due to a bcrypt 4.x
incompatibility; don't reintroduce it.

**HTML safety is defense-in-depth.** On upload (`routers/reports.py::upload_version`) HTML is
sanitized server-side (`services/html_sanitize.py`: BeautifulSoup `decompose()` of dangerous
tags *then* `bleach.clean`) and only the sanitized copy is stored in SharePoint. On read, the
`/reports/{id}/render` endpoint serves it with a locked-down CSP, and the **web app loads it
into a sandboxed `<iframe>`** (no `allow-scripts`/`allow-same-origin`). Never inject report
HTML into the React tree directly.

**Storage** (`services/sharepoint.py`): report assets (HTML/PDF/video) live in a **SharePoint**
document library, accessed over Microsoft Graph with an **app-only** token
(`core/msal_client.py::acquire_app_graph_token` — client credentials, the app's own identity,
so any signed-in user incl. dev-login can upload/view; no per-user Graph token). Requires the
Entra app to hold the **application** permission `Sites.ReadWrite.All` (admin-consented).
Layout: `{sharepoint_root_folder}/{report_id}/v{n}/asset.{ext}` under the site's default (or
named) drive. The DB stores only the Graph **drive-item id** as the asset path + extracted text.
There is no Azure Blob backend — storage is SharePoint-only.

**Search** (`services/search.py`): Postgres FTS over a maintained `search_vector` tsvector
(GIN-indexed, populated by a DB trigger fed from title/summary/description/project and
`content_text`). Keyword queries rank via `websearch_to_tsquery`/`ts_rank`; empty query falls
back to filtered recency. Semantic/pgvector search is stubbed for a later phase.

**Reports are addressed by slug OR uuid** — helpers (`_get_or_404`) try `uuid.UUID(...)` then
fall back to slug. Routers eager-load relations via shared `selectinload` tuples to avoid N+1.

**Frontend is Next.js 14.2.5 (App Router).** Critical: in 14.2 the `params` prop on dynamic
pages is a **plain object** — destructure it directly (`const { slug } = params`). Do **not**
use the Next 15 `use(params)` Promise pattern; it throws "unsupported type passed to use()".
Data layer is React Query + a thin fetch client in `lib/api.ts` (sends cookies; on 401 it
redirects to `/login`). Collections are self-referential (nested folders via `parent_id`),
rendered as a recursive tree in `components/collection-tree.tsx`.

## Local environment notes

- The user's local Postgres listens on **5433** with `postgres` / `2001` (host already
  occupies 5432). See memory: `kelp-nexus-local-db-port`. For Docker-compose Postgres, set
  `KELP_DB_PORT` if 5432/5433 are taken.
- `apps/api/.env` is gitignored and user-managed; `apps/api/.env.example` documents the keys.
  SharePoint needs `SHAREPOINT_SITE` + the MSAL app credentials (`MSAL_CLIENT_ID/TENANT_ID/
  CLIENT_SECRET`); the real client secret lives only in the local `.env` — never commit it.
- AI features (`services/ai.py`, Claude) are off by default (`ENABLE_AI=false`) and degrade
  gracefully without `ANTHROPIC_API_KEY`. Default model id: `claude-opus-4-8`.

## Backend layout

`app/routers/` HTTP endpoints · `app/services/` business logic (storage, search, html_sanitize,
ai, taxonomy) · `app/db/models/` SQLAlchemy models · `app/schemas/` Pydantic I/O ·
`app/core/` config, security, deps/RBAC, MSAL. All routers mounted under `settings.api_v1_prefix`
(`/api/v1`); `/health` is unprefixed. `docs/` holds the PRD/TDD/architecture; `infra/` holds
Dockerfiles + K8s manifests.
