import json

import pytest


async def test_get_index_missing(client):
    resp = await client.get("/api/v1/resources/index")
    assert resp.status_code == 200
    assert "não encontrado" in resp.json()["content"]


async def test_get_index_with_content(client, fake_dirs):
    fake_dirs["index"].write_text("# Index Content")
    resp = await client.get("/api/v1/resources/index")
    assert resp.status_code == 200
    assert resp.json()["content"] == "# Index Content"


async def test_get_projects(client):
    resp = await client.get("/api/v1/resources/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert "project-a" in data["projects"]


async def test_get_prds_empty(client):
    resp = await client.get("/api/v1/resources/prds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_get_prds_lists_files(client, fake_dirs):
    fake_dirs["prds"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["prds"] / "prd-foo.md").write_text("x")
    (fake_dirs["prds"] / "prd-bar.md").write_text("x")
    resp = await client.get("/api/v1/resources/prds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert "prd-bar.md" in data["items"]


async def test_get_specs_empty(client):
    resp = await client.get("/api/v1/resources/specs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_get_plans_empty(client):
    resp = await client.get("/api/v1/resources/plans")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_get_prd_file(client, fake_dirs):
    fake_dirs["prds"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["prds"] / "prd-foo.md").write_text("# PRD Foo")
    resp = await client.get("/api/v1/resources/prds/prd-foo.md")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "prd-foo.md"
    assert data["content"] == "# PRD Foo"


async def test_get_prd_file_missing(client):
    resp = await client.get("/api/v1/resources/prds/prd-missing.md")
    assert resp.status_code == 404


async def test_get_spec_file(client, fake_dirs):
    fake_dirs["specs"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["specs"] / "spec-foo.md").write_text("# Spec Foo")
    resp = await client.get("/api/v1/resources/specs/spec-foo.md")
    assert resp.status_code == 200
    assert resp.json()["content"] == "# Spec Foo"


async def test_get_spec_file_missing(client):
    resp = await client.get("/api/v1/resources/specs/spec-missing.md")
    assert resp.status_code == 404


async def test_get_plan_file(client, fake_dirs):
    fake_dirs["plans"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["plans"] / "plan-foo.md").write_text("# Plan Foo")
    resp = await client.get("/api/v1/resources/plans/plan-foo.md")
    assert resp.status_code == 200
    assert resp.json()["content"] == "# Plan Foo"


async def test_get_plan_file_missing(client):
    resp = await client.get("/api/v1/resources/plans/plan-missing.md")
    assert resp.status_code == 404
