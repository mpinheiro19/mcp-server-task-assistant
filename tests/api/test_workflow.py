INDEX_CONTENT = """\
| PRD Origem | Spec (Arquivo) | Feature | Plan Status | Implementation |
| :--- | :--- | :--- | :--- | :--- |
| prd-foo.md | spec-foo.md | Foo Feature | 🟢 Done | ✅ Concluído |
| prd-bar.md | spec-bar.md | Bar Feature | 🟡 Pending | ❌ Todo |
"""


async def test_workflow_status_empty(client):
    resp = await client.get("/api/v1/workflow/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["features"] == []
    assert data["summary"] == {"done": 0, "in_progress": 0, "todo": 0}


async def test_workflow_status_with_index(client, fake_dirs):
    fake_dirs["index"].write_text(INDEX_CONTENT)
    resp = await client.get("/api/v1/workflow/status")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["features"]) == 2
    assert data["summary"]["done"] == 1
    assert data["summary"]["todo"] == 1


async def test_update_index_creates(client):
    resp = await client.put(
        "/api/v1/workflow/index",
        json={
            "prd_filename": "prd-new.md",
            "spec_filename": "spec-new.md",
            "feature_name": "New Feature",
            "plan_status": "🟡 Pending",
            "implementation_status": "❌ Todo",
        },
    )
    assert resp.status_code == 200
    assert "prd-new.md" in resp.json()["content"]


async def test_update_index_replaces_existing(client, fake_dirs):
    fake_dirs["index"].write_text(INDEX_CONTENT)
    resp = await client.put(
        "/api/v1/workflow/index",
        json={
            "prd_filename": "prd-foo.md",
            "spec_filename": "spec-foo.md",
            "feature_name": "Foo Feature",
            "plan_status": "🟡 Pending",
            "implementation_status": "🔄 In Progress",
        },
    )
    assert resp.status_code == 200
    content = resp.json()["content"]
    assert "🔄 In Progress" in content


async def test_advance_stage(client, fake_dirs):
    fake_dirs["index"].write_text(INDEX_CONTENT)
    resp = await client.patch(
        "/api/v1/workflow/features/Bar Feature/stage",
        json={"plan_status": "🟢 Done", "implementation_status": "✅ Concluído"},
    )
    assert resp.status_code == 200
    assert "✅ Concluído" in resp.json()["content"]


async def test_advance_stage_feature_not_found(client, fake_dirs):
    fake_dirs["index"].write_text(INDEX_CONTENT)
    resp = await client.patch(
        "/api/v1/workflow/features/Nonexistent/stage",
        json={"plan_status": "🟢 Done", "implementation_status": "✅ Concluído"},
    )
    assert resp.status_code == 409


async def test_advance_stage_index_missing(client):
    resp = await client.patch(
        "/api/v1/workflow/features/Any Feature/stage",
        json={"plan_status": "🟢 Done", "implementation_status": "✅ Concluído"},
    )
    assert resp.status_code == 404


async def test_check_duplicate_none(client):
    resp = await client.get("/api/v1/workflow/duplicates?feature_name=Nova+Feature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_duplicate"] is False
    assert data["matches"] == []


async def test_check_duplicate_found(client, fake_dirs):
    fake_dirs["prds"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["prds"] / "prd-nova-feature.md").write_text("x")
    resp = await client.get("/api/v1/workflow/duplicates?feature_name=Nova+Feature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_duplicate"] is True
