"""Seed the database with demo users, taxonomy, and reports.

Run after migrations:  python -m app.db.seed
Idempotent: skips creation when the admin user already exists.
"""
from __future__ import annotations

from slugify import slugify
from sqlalchemy import select

from app.core.config import settings
from app.db.models.report import (
    Category,
    Report,
    ReportStatus,
    ReportVersion,
    Visibility,
)
from app.db.models.user import Role, User
from app.db.session import SessionLocal
from app.services.html_sanitize import extract_text, sanitize_html
from app.services.taxonomy import upsert_tags, upsert_technologies

SAMPLE_HTML = """<!doctype html><html><head><meta charset='utf-8'>
<style>body{{font-family:system-ui;line-height:1.6;max-width:800px;margin:2rem auto}}
h1{{color:#0f766e}} code{{background:#f1f5f9;padding:2px 4px;border-radius:4px}}</style></head>
<body><h1>{title}</h1><p>{intro}</p>
<h2>Approach</h2><p>We benchmarked three configurations under production-like load.</p>
<pre><code>throughput = requests / second</code></pre>
<h2>Results</h2><table><thead><tr><th>Config</th><th>p99 (ms)</th></tr></thead>
<tbody><tr><td>baseline</td><td>120</td></tr><tr><td>tuned</td><td>38</td></tr></tbody></table>
<h2>Conclusion</h2><p>{conclusion}</p></body></html>"""

USERS = [
    ("admin@kelp.dev", "Ada Admin", Role.admin, "Platform", "Engineering"),
    ("editor@kelp.dev", "Eve Editor", Role.editor, "Platform", "Engineering"),
    ("priya@kelp.dev", "Priya Rao", Role.author, "Search", "Engineering"),
    ("liam@kelp.dev", "Liam Chen", Role.author, "Infra", "Engineering"),
    ("viewer@kelp.dev", "Val Viewer", Role.viewer, "Product", "Product"),
]

CATEGORIES = ["Benchmarks", "Architecture", "RFC", "POC", "Research"]

REPORTS = [
    {
        "title": "Postgres FTS vs. Elasticsearch for Internal Search",
        "category": "Benchmarks", "author": "priya@kelp.dev", "project": "Knowledge Portal",
        "tags": ["search", "benchmark", "latency"],
        "tech": ["PostgreSQL", "Elasticsearch", "Python"],
        "intro": "Comparing Postgres full-text search against Elasticsearch for our corpus size.",
        "conclusion": "Postgres FTS is sufficient up to ~100k docs; revisit ES beyond that.",
    },
    {
        "title": "Event-Driven Architecture RFC",
        "category": "RFC", "author": "liam@kelp.dev", "project": "Platform 2.0",
        "tags": ["events", "kafka", "architecture"],
        "tech": ["Kafka", "Go", "Kubernetes"],
        "intro": "Proposal to move core services to an event-driven model.",
        "conclusion": "Adopt outbox pattern + Kafka; phased rollout over two quarters.",
    },
    {
        "title": "pgvector Semantic Search POC",
        "category": "POC", "author": "priya@kelp.dev", "project": "Knowledge Portal",
        "tags": ["embeddings", "semantic-search", "ai"],
        "tech": ["PostgreSQL", "pgvector", "Python"],
        "intro": "Prototype of semantic retrieval over engineering reports using pgvector.",
        "conclusion": "Recall improved markedly on paraphrased queries; ship behind a flag.",
    },
    {
        "title": "Kubernetes Cost Optimization Study",
        "category": "Research", "author": "liam@kelp.dev", "project": "FinOps",
        "tags": ["cost", "kubernetes", "autoscaling"],
        "tech": ["Kubernetes", "Prometheus", "Terraform"],
        "intro": "Where our cluster spend goes and how to cut it without hurting reliability.",
        "conclusion": "Right-sizing + spot for batch saves ~32% monthly.",
    },
]


def run() -> None:
    # Opt-in only. Without SEED_DEMO_DATA=true this is a no-op, so a production
    # boot can never (re)create the demo users/reports — even if the deletion
    # of prior demo data removed the admin@kelp.dev idempotency marker below.
    if not settings.seed_demo_data:
        print("SEED_DEMO_DATA is not set; skipping demo seed.")
        return

    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "admin@kelp.dev")):
            print("Seed already applied; skipping.")
            return

        users: dict[str, User] = {}
        for email, name, role, team, dept in USERS:
            # Author records only — sign-in is Microsoft SSO (no local passwords).
            u = User(
                email=email, name=name, role=role, team=team, department=dept,
                title="Engineer", bio=f"{name} works on the {team} team.",
            )
            db.add(u)
            users[email] = u
        db.flush()

        cats = {name: Category(name=name, slug=slugify(name)) for name in CATEGORIES}
        for c in cats.values():
            db.add(c)
        db.flush()

        for spec in REPORTS:
            author = users[spec["author"]]
            report = Report(
                title=spec["title"], slug=slugify(spec["title"]),
                description=spec["intro"],
                summary=spec["conclusion"],
                author_id=author.id, team=author.team, department=author.department,
                category_id=cats[spec["category"]].id, project=spec["project"],
                status=ReportStatus.published, visibility=Visibility.internal,
                current_version=1, github_repo="https://github.com/kelp/example",
                view_count=0,
            )
            db.add(report)
            db.flush()
            report.tags = upsert_tags(db, spec["tags"])
            report.technologies = upsert_technologies(db, spec["tech"])
            db.flush()

            html = SAMPLE_HTML.format(
                title=spec["title"], intro=spec["intro"], conclusion=spec["conclusion"]
            )
            clean = sanitize_html(html)
            report.content_text = extract_text(clean)
            # Seed metadata + searchable text only; no asset is uploaded to
            # SharePoint (keeps seeding offline and the library clean). Upload a
            # real version via the API to get a viewable asset.
            db.add(ReportVersion(
                report_id=report.id, version=1,
                extracted_text=report.content_text, changelog="Initial version",
                created_by=author.id,
            ))

        db.commit()
        print(f"Seeded {len(USERS)} users, {len(CATEGORIES)} categories, {len(REPORTS)} reports.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
