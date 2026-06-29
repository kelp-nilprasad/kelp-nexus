# API Contract — Kelp Nexus

Base path: `/api/v1`. Auth via httpOnly `access_token` cookie (or
`Authorization: Bearer`). OpenAPI/Swagger is served live at `/docs` and
`/openapi.json`; export a static copy with:

```bash
cd apps/api && python -c "import json, app.main as m; open('../../docs/openapi.json','w').write(json.dumps(m.app.openapi()))"
```

## Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| GET  | `/auth/config` | — | Which login methods are enabled |
| POST | `/auth/dev-login` | — | Email/password → session cookie (dev only) |
| GET  | `/auth/login` | — | Begin Azure AD OIDC redirect |
| GET  | `/auth/callback` | — | OIDC redirect target; sets cookie |
| POST | `/auth/logout` | user | Clear session |
| GET  | `/auth/me` | user | Current user |

## Reports
| Method | Path | Auth | Description |
|---|---|---|---|
| GET   | `/reports` | — | Paginated list (`page`, `page_size`, `status`) |
| POST  | `/reports` | author+ | Create report (metadata) |
| GET   | `/reports/{slug_or_id}` | optional | Detail; increments view + recently-viewed |
| PATCH | `/reports/{slug_or_id}` | owner/editor/admin | Update metadata |
| DELETE| `/reports/{slug_or_id}` | owner/admin | Delete |
| POST  | `/reports/{slug_or_id}/versions` | owner/editor/admin | Upload HTML/PDF as new version (multipart) |
| GET   | `/reports/{slug_or_id}/render` | optional | Sanitized HTML (sandbox/CSP) |
| GET   | `/reports/{slug_or_id}/related` | — | Related reports |

## Search
| Method | Path | Description |
|---|---|---|
| GET | `/search` | `q` + facets: `category_id, tag, technology, author_id, project, status, visibility, date_from, date_to, page, page_size` |

## Engagement
| Method | Path | Auth | Description |
|---|---|---|---|
| GET    | `/reports/{report_id}/comments` | — | Threaded comments |
| POST   | `/reports/{report_id}/comments` | user | Add comment (`parent_id` for replies) |
| DELETE | `/comments/{comment_id}` | author/editor/admin | Delete |
| GET    | `/favorites` | user | Current user's favorites |
| PUT    | `/reports/{report_id}/favorite` | user | Add favorite |
| DELETE | `/reports/{report_id}/favorite` | user | Remove favorite |
| GET    | `/recently-viewed` | user | Last 20 viewed |

## Taxonomy
| Method | Path | Auth | Description |
|---|---|---|---|
| GET  | `/categories` | — | List |
| POST | `/categories` | editor+ | Create |
| GET  | `/tags` | — | List |
| GET  | `/technologies` | — | List |
| GET  | `/technologies/cloud` | — | Usage counts (tech cloud) |

## Users / profiles
| Method | Path | Auth | Description |
|---|---|---|---|
| GET   | `/users/{user_id}` | — | Public profile |
| GET   | `/users/{user_id}/reports` | — | Their reports |
| PATCH | `/users/me` | user | Update own profile |

## Dashboard / analytics
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard` | Trending, recent, most-viewed, comments, category counts |
| GET | `/analytics` | Totals + top authors |

## Admin
| Method | Path | Auth | Description |
|---|---|---|---|
| GET   | `/admin/users` | admin | All users |
| PATCH | `/admin/users/{id}/role` | admin | Change role |
| PATCH | `/admin/users/{id}/deactivate` | admin | Deactivate |
| GET   | `/admin/audit-log` | admin | Recent audit entries |

## Conventions

- IDs are UUIDs; reports are addressable by `id` or `slug`.
- Errors: `{ "detail": "message" }` with appropriate status (401/403/404/400).
- Pagination: `{ items, total, page, page_size }`.
