# UI Wireframes — Kelp Nexus

ASCII wireframes for the core screens. The implemented pages live under
`apps/web/app/`.

## Global shell (`components/nav.tsx`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◆ Kelp Nexus   Dashboard  Reports  Search  Upload   [Admin]   (avatar)⏻│
├──────────────────────────────────────────────────────────────────────┤
│  <page content>                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

## Login (`/login`)

```
            ┌───────────────────────────┐
            │           ◆               │
            │       Kelp Nexus          │
            │  Engineering Knowledge    │
            │                           │
            │ [ Sign in with Microsoft ]│
            │ ───────── or ───────────  │
            │ [ email                 ] │
            │ [ password              ] │
            │ [        Sign in        ] │
            │ admin@kelp.dev / password │
            └───────────────────────────┘
```

## Dashboard (`/dashboard`)

```
Knowledge Dashboard
[ Quick search ........................... ]

▲ Trending this week
[card] [card] [card] [card]

⏱ Recently added
[card] [card] [card] [card]

👁 Most viewed
[card] [card] [card] [card]

┌ Categories ─────┐ ┌ Technology cloud ─┐ ┌ Recent comments ─┐
│ Benchmarks 12   │ │ PostgreSQL  Kafka │ │ "great find…"     │
│ RFC 5  POC 8    │ │ pgvector  Go  k8s │ │ Priya on FTS…     │
└─────────────────┘ └───────────────────┘ └───────────────────┘
```

## Report card (`components/report-card.tsx`)

```
┌───────────────────────────────┐
│ [Benchmarks]        [published]│
│ Postgres FTS vs Elasticsearch  │
│ Comparing FTS against ES for…  │
│ [PostgreSQL][Elasticsearch]    │
│ (a) Priya Rao    👁 42 · 3d ago│
└───────────────────────────────┘
```

## Report detail (`/reports/[slug]`)

```
[Benchmarks][published][internal][v2]
Postgres FTS vs. Elasticsearch
Comparing Postgres full-text search against ES…
(a) Priya Rao · Search · Jun 12          [ ★ Favorite ]

┌ Summary ─────────────────────────────┐   ┌ Details ────────┐
│ Postgres FTS is sufficient to ~100k… │   │ Team    Search  │
└──────────────────────────────────────┘   │ Project Portal  │
┌ HTML viewer (sandboxed iframe) ──[⛶]─┐   │ Views   42      │
│                                      │   └─────────────────┘
│     <rendered report, isolated>      │   ┌ Links ──────────┐
│                                      │   │  Repository  PR │
└──────────────────────────────────────┘   └─────────────────┘
Comments                                    ┌ Tags ───────────┐
[ add a comment …………… ] [Post]              │ search benchmark│
(a) Liam — "did you try GIN?"               └─────────────────┘
                                            ┌ Versions ───────┐
Related reports                             │ v2  HTML  3d    │
[card] [card] [card] [card]                 │ v1  HTML  9d    │
                                            └─────────────────┘
```

## Upload (`/upload`)

```
Upload a Report
┌ Metadata ────────────────────────────────────────────┐
│ Title*  [……………………………………………………………]                  │
│ Description [……………]   Summary [……………]                 │
│ Project [……]  Category [▾]                            │
│ Tags [a,b,c]  Technologies [x,y]                      │
│ GitHub [……]  Demo [……]  Status [▾]  Visibility [▾]    │
└───────────────────────────────────────────────────────┘
┌ Files ────────────────────────────────────────────────┐
│ HTML report [Choose file]   PDF [Choose file]         │
└───────────────────────────────────────────────────────┘
                                  [Cancel] [Publish report]
```

## Search (`/search`)

```
Search
[ keywords …………………………… ] [Search]
[technology: kafka] [category: RFC]
12 results
[card] [card] [card]
[card] [card] [card]
```

## Author profile (`/authors/[id]`)

```
(AVATAR)  Priya Rao
          Engineer · Search · Engineering
          [author]  priya@kelp.dev
Bio…
Reports by Priya Rao (7)
[card] [card] [card] [card]
```

## Admin (`/admin`)

```
Admin
[Reports 30][Published 24][Users 18][Views 1.2k][30d 420]
┌ Users & roles ───────────────────────────────────────┐
│ (a) Ada Admin  admin@kelp.dev   [Platform] [admin ▾]  │
│ (a) Liam Chen  liam@kelp.dev    [Infra]    [author ▾] │
└───────────────────────────────────────────────────────┘
```
