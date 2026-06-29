# Product Requirements Document — Kelp Nexus

## 1. Problem

Engineering knowledge — research, POCs, benchmarks, RFCs, architecture docs, and
HTML reports — is scattered across Slack, Teams, email, and laptops. It is lost
when people switch teams, duplicated because nobody can find prior work, and
invisible to the engineers who would benefit most.

## 2. Goal

A single, searchable, durable portal where every engineer can **upload, discover,
search, and reuse** technical work. It should feel like Medium + GitHub +
Confluence + an internal tech blog.

## 3. Target users & personas

| Persona | Needs |
|---------|-------|
| **Author** (most engineers) | Publish a report in <2 min; attach HTML/PDF; tag tech & project |
| **Researcher** | Find prior art before starting; avoid duplicate work |
| **Tech lead / Staff** | Discover experts; track what teams are producing |
| **Editor** | Curate categories/tags; fix metadata |
| **Admin** | Manage users, roles, visibility, and platform health |

## 4. Core use cases

1. Upload an HTML report with rich metadata; it renders safely and is searchable.
2. Full-text search across titles, descriptions, and **inside HTML content**, with
   filters (technology, author, tags, project, date, category).
3. Browse a dashboard of trending / recent / most-viewed / favorite reports.
4. Open a report: read summary, view the HTML in a sandboxed viewer, see metadata,
   related reports, version history, and discuss in comments.
5. Visit an author profile to see everything they've produced.
6. Admins manage roles and review analytics.

## 5. Functional requirements

- **Auth**: Azure AD SSO; dev-login fallback for local/dev. Session via httpOnly JWT.
- **RBAC**: `admin` > `editor` > `author` > `viewer`. Authors edit their own
  reports; editors/admins edit any; viewers are read-only.
- **Reports**: full metadata (see §7), draft/published/archived, visibility
  public/internal/private, versioned HTML + PDF.
- **Secure HTML rendering**: sanitized on ingest + sandboxed iframe + strict CSP.
- **Search**: Postgres FTS with weighting and facets; semantic search later.
- **Engagement**: comments (threaded), favorites, recently-viewed, view analytics.
- **Discovery**: categories, tags, technology cloud, related reports.
- **Admin**: user/role management, audit log, analytics.

## 6. Non-functional requirements

- **Scale**: thousands of reports, hundreds of users across teams.
- **Security**: no stored HTML can execute in a user's session; RBAC enforced
  server-side; least-privilege storage access via SAS where possible.
- **Performance**: dashboard < 500 ms p95; search < 800 ms p95 at MVP corpus.
- **Modularity**: storage, search, and AI are swappable behind interfaces.
- **Observability**: health checks, structured logs, audit trail.

## 7. Report metadata

Title, Description, Summary, Author, Team, Department, Category, Tags,
Technologies, Project, Status (Draft/Published/Archived), Created date, Updated
date, GitHub repository, Pull Request, Demo URL, Video URL, PDF attachment, HTML
report, Version number, Visibility (Public/Internal/Private).

## 8. Out of scope (MVP)

Real-time collaborative editing, WYSIWYG authoring, external (customer) sharing,
mobile native apps. AI features ship behind a flag in Phase 2.

## 9. Success metrics

- Time-to-publish a report < 2 minutes.
- % of searches returning a clicked result > 60%.
- Weekly active authors and reports-per-week trending up.
- Reduction in "has anyone done X?" questions in chat (qualitative survey).

## 10. Phasing

- **MVP**: auth, upload, secure render, metadata, FTS, dashboard, comments,
  favorites, profiles, admin, analytics.
- **Phase 2 (AI)**: auto-summaries, auto-tags, embeddings + semantic search, RAG
  "chat with report", duplicate detection, suggested experts.
- **Enterprise**: SSO hardening, fine-grained ACLs, multi-tenant teams, audit
  exports, data retention, search at 100k+ docs (pgvector/Qdrant).
