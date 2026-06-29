"""Integration tests for collections (requires Postgres)."""
from __future__ import annotations


def _make_report(client, auth_headers, title="Collected Report"):
    return client.post(
        "/api/v1/reports",
        json={"title": title, "description": "d", "summary": "s",
              "status": "published", "tags": ["x"], "technologies": ["Y"]},
        headers=auth_headers,
    ).json()


def test_create_collection_and_add_report(client, auth_headers):
    coll = client.post(
        "/api/v1/collections",
        json={"name": "My Research Folder", "description": "stuff"},
        headers=auth_headers,
    )
    assert coll.status_code == 201, coll.text
    cid = coll.json()["id"]
    assert coll.json()["slug"] == "my-research-folder"

    report = _make_report(client, auth_headers)
    add = client.put(f"/api/v1/collections/{cid}/reports/{report['id']}", headers=auth_headers)
    assert add.status_code == 204

    detail = client.get(f"/api/v1/collections/{cid}", headers=auth_headers).json()
    assert detail["report_count"] == 1
    assert detail["reports"][0]["id"] == report["id"]


def test_collection_requires_auth(client):
    resp = client.post("/api/v1/collections", json={"name": "nope"})
    assert resp.status_code == 401


def test_nested_collections(client, auth_headers):
    parent = client.post(
        "/api/v1/collections", json={"name": "Parent Folder"}, headers=auth_headers
    ).json()
    child = client.post(
        "/api/v1/collections",
        json={"name": "Child Folder", "parent_id": parent["id"]},
        headers=auth_headers,
    )
    assert child.status_code == 201, child.text
    assert child.json()["parent_id"] == parent["id"]

    # Parent detail exposes the subfolder; child breadcrumbs include both.
    pdetail = client.get(f"/api/v1/collections/{parent['id']}", headers=auth_headers).json()
    assert pdetail["subfolder_count"] == 1
    assert pdetail["children"][0]["name"] == "Child Folder"

    cdetail = client.get(f"/api/v1/collections/{child.json()['id']}", headers=auth_headers).json()
    assert [b["name"] for b in cdetail["breadcrumbs"]] == ["Parent Folder", "Child Folder"]

    # Top-level listing excludes the child.
    top = client.get("/api/v1/collections", headers=auth_headers).json()
    names = {c["name"] for c in top}
    assert "Parent Folder" in names and "Child Folder" not in names
