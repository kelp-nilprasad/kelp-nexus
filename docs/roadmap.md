# Roadmap — MVP to Enterprise Scale

## Phase 0 — MVP (this codebase)
**Goal: a runnable portal teams can use today.**
- ✅ Azure AD SSO + dev-login, RBAC (admin/editor/author/viewer)
- ✅ Report CRUD, full metadata, draft/published/archived, visibility
- ✅ HTML/PDF upload to Azure Blob, versioning
- ✅ Secure HTML rendering (sanitize on ingest + sandboxed iframe + CSP)
- ✅ Postgres full-text search with facets (incl. search inside HTML content)
- ✅ Dashboard (trending/recent/most-viewed/favorites/tech-cloud/comments)
- ✅ Comments, favorites, recently-viewed, related reports, author profiles
- ✅ Admin panel + analytics + audit log
- ✅ Docker Compose, Kubernetes manifests, CI/CD

## Phase 1 — Hardening & adoption (weeks 1–4)
- Reply threading UI + comment notifications (email/Teams webhook)
- Saved searches & search history; advanced filter UI (date range, multi-tag)
- Draft autosave; report preview before publish
- Bulk import (zip of HTML reports) + migration tooling from Confluence/Drive
- E2E tests (Playwright), accessibility pass, dark mode toggle
- Rate limiting, request logging, OpenTelemetry traces

## Phase 2 — AI features (weeks 4–10)
The schema and `services/ai.py` interfaces already exist; wire real providers.
- **Auto-summaries** on upload (Claude) — populate `summary`
- **Auto-tagging** suggestions accepted by the author
- **Embeddings + semantic search** (pgvector cosine ivfflat already in schema);
  `semantic=true` toggle on `/search`, hybrid rank (FTS + vector)
- **RAG "chat with report"** — chunk → embed → retrieve → answer with citations
- **Duplicate research detection** — flag near-duplicate uploads via embeddings
- **Suggested experts** — rank authors by topical embedding similarity

## Phase 3 — Scale & enterprise (months 3–6)
- Move Postgres to managed (Azure PG Flexible) with read replicas
- If corpus > ~100k docs or latency regresses: introduce **Qdrant**/managed vector
  DB behind the existing `SemanticSearch` interface
- Fine-grained ACLs: per-team/per-space visibility, private spaces, share links
- Multi-tenant teams/workspaces with delegated admins
- SSO hardening: group→role mapping from Azure AD claims, SCIM provisioning
- Data governance: retention policies, legal hold, audit export, PII scanning
- CDN in front of blob render; signed URLs; per-report view-rate analytics
- SLOs + on-call runbooks; blue/green or canary deploys

## Phase 4 — Ecosystem
- Public REST + webhook API for integrations (CI publishes benchmark reports)
- VS Code / CLI publisher ("kelp publish ./report.html")
- Slack/Teams unfurling + slash-command search
- Recommendations feed ("reports for you") from view + embedding signals
- Knowledge graph across reports, technologies, and teams

## Guiding principles
- Keep storage/search/AI swappable behind interfaces — never hard-couple.
- Every feature must degrade gracefully if its dependency (AI, SSO) is absent.
- Security is non-negotiable: sanitize + sandbox, RBAC server-side, least privilege.
```
