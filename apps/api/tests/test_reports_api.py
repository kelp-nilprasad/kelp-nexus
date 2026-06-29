"""Integration tests for the reports + search flow (requires Postgres)."""
from __future__ import annotations


def test_create_and_get_report(client, auth_headers):
    payload = {
        "title": "Caching Strategy Benchmark",
        "description": "Comparing Redis vs in-process caches.",
        "summary": "Redis wins for shared state; in-process for hot paths.",
        "status": "published",
        "tags": ["caching", "redis"],
        "technologies": ["Redis", "Python"],
    }
    resp = client.post("/api/v1/reports", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slug"] == "caching-strategy-benchmark"
    assert {t["name"] for t in data["tags"]} == {"caching", "redis"}

    got = client.get(f"/api/v1/reports/{data['slug']}")
    assert got.status_code == 200
    assert got.json()["view_count"] == 1  # the GET tracked a view


def test_requires_auth_to_create(client):
    resp = client.post(
        "/api/v1/reports",
        json={"title": "x", "description": "d", "summary": "s", "tags": ["t"]},
    )
    assert resp.status_code == 401


def test_required_fields_enforced(client, auth_headers):
    # Missing summary + tags → 422 validation error.
    resp = client.post(
        "/api/v1/reports",
        json={"title": "Incomplete", "description": "only a description"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_full_text_search(client, auth_headers):
    client.post(
        "/api/v1/reports",
        json={"title": "Kafka Throughput Study", "description": "event streaming at scale",
              "summary": "Kafka sustains target throughput with tuned batching.",
              "status": "published", "tags": ["kafka"], "technologies": ["Kafka"]},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/search", params={"q": "kafka"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any("Kafka" in item["report"]["title"] for item in body["items"])
