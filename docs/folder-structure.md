# Folder Structure — Kelp Nexus

```
kelp-nexus/
├── apps/
│   ├── api/                       # FastAPI backend
│   │   ├── app/
│   │   │   ├── core/              # config, security (JWT), deps (RBAC), azure_ad (OIDC)
│   │   │   ├── db/
│   │   │   │   ├── base.py        # Declarative Base + TimestampMixin
│   │   │   │   ├── session.py     # engine + get_db dependency
│   │   │   │   ├── models/        # user, report, engagement, ai, audit
│   │   │   │   ├── migrations/    # Alembic (env.py, versions/0001_initial.py)
│   │   │   │   └── seed.py        # demo users/categories/reports
│   │   │   ├── schemas/           # Pydantic v2 (user, report, engagement)
│   │   │   ├── services/          # storage, html_sanitize, search, ai, taxonomy
│   │   │   ├── routers/           # auth, reports, search, comments, favorites,
│   │   │   │                      #   taxonomy, users, dashboard, related, admin
│   │   │   └── main.py            # FastAPI app + router wiring
│   │   ├── tests/                 # pytest (unit + integration)
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   └── .env.example
│   └── web/                       # Next.js frontend (App Router)
│       ├── app/
│       │   ├── layout.tsx         # shell (Providers + Nav)
│       │   ├── login/             # auth page
│       │   ├── dashboard/         # dashboard
│       │   ├── reports/           # list + [slug] detail
│       │   ├── upload/            # create report + upload files
│       │   ├── search/            # search + facets
│       │   ├── authors/[id]/      # author profile
│       │   └── admin/             # admin panel
│       ├── components/
│       │   ├── ui/                # button, card, badge, input, avatar (shadcn-style)
│       │   ├── nav.tsx
│       │   ├── report-card.tsx
│       │   └── report-viewer.tsx  # sandboxed HTML iframe
│       ├── lib/                   # api client, types, auth hook, providers, utils
│       ├── __tests__/             # vitest
│       ├── middleware.ts          # auth redirect guard
│       └── package.json
├── packages/
│   └── shared-types/              # (reserved) generated TS types from OpenAPI
├── infra/
│   ├── docker/                    # Dockerfile.api, Dockerfile.web
│   └── k8s/                       # namespace, config, postgres, migrate, api, web, ingress
├── .github/workflows/ci.yml       # CI/CD pipeline
├── docs/                          # PRD, TDD, ER, API, wireframes, deploy guide, roadmap
├── docker-compose.yml
└── README.md
```
