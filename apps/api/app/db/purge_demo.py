"""Remove the seeded demo data (@kelp.dev users and the reports they authored).

Real accounts sign in via Microsoft SSO with real email addresses, so nothing
here can match production content — the target set is strictly the demo users
from ``seed.py`` and reports whose author is one of them.

Safe by default: prints what it *would* delete and exits. Pass ``--execute`` to
actually delete (inside a single transaction that rolls back on any error).

    # preview only (no writes):
    python -m app.db.purge_demo

    # actually delete:
    python -m app.db.purge_demo --execute
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.db.models.report import Report
from app.db.models.user import User
from app.db.seed import USERS
from app.db.session import SessionLocal

# The demo email addresses, taken from the seed definition so the two never drift.
DEMO_EMAILS = [email for (email, *_rest) in USERS]


def run(execute: bool = False) -> int:
    db = SessionLocal()
    try:
        users = list(db.scalars(select(User).where(User.email.in_(DEMO_EMAILS))))
        # Reports authored by any demo user (their versions/tags/etc. cascade on delete).
        user_ids = [u.id for u in users]
        reports = (
            list(db.scalars(select(Report).where(Report.author_id.in_(user_ids))))
            if user_ids
            else []
        )

        print(f"Demo users found:   {len(users)}")
        for u in users:
            print(f"  - {u.email}  ({u.name}, {u.role.value})")
        print(f"Demo reports found: {len(reports)}")
        for r in reports:
            print(f"  - {r.title}  [{r.slug}]")

        if not users and not reports:
            print("\nNothing to purge. Demo data is already gone.")
            return 0

        if not execute:
            print("\nDRY RUN — nothing deleted. Re-run with --execute to remove the above.")
            return 0

        # Delete reports first (cascades versions/associations), then the now
        # unreferenced demo users. One transaction: any error rolls it all back.
        for r in reports:
            db.delete(r)
        db.flush()
        for u in users:
            db.delete(u)
        db.commit()
        print(f"\nDeleted {len(reports)} report(s) and {len(users)} user(s).")
        return 0
    except Exception as exc:  # noqa: BLE001 — surface + rollback, don't half-delete
        db.rollback()
        print(f"\nERROR — rolled back, nothing deleted: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run(execute="--execute" in sys.argv[1:]))
