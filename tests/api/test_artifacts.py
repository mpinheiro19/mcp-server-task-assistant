async def test_create_prd(client):
    resp = await client.post(
        "/api/v1/artifacts/prds",
        json={"feature_name": "My Feature", "content": "# PRD"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "prd-my-feature.md"
    assert "path" in data


async def test_create_prd_duplicate_returns_409(client):
    payload = {"feature_name": "Dup Feature", "content": "# PRD"}
    await client.post("/api/v1/artifacts/prds", json=payload)
    resp = await client.post("/api/v1/artifacts/prds", json=payload)
    assert resp.status_code == 409


async def test_create_spec(client):
    resp = await client.post(
        "/api/v1/artifacts/specs",
        json={
            "feature_name": "Sub Feature",
            "prd_filename": "prd-my-feature.md",
            "content": "# Spec",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "spec-my-feature-sub-feature.md"


async def test_create_spec_duplicate_returns_409(client):
    payload = {
        "feature_name": "Dup Spec",
        "prd_filename": "prd-foo.md",
        "content": "# Spec",
    }
    await client.post("/api/v1/artifacts/specs", json=payload)
    resp = await client.post("/api/v1/artifacts/specs", json=payload)
    assert resp.status_code == 409


async def test_create_plan(client):
    resp = await client.post(
        "/api/v1/artifacts/plans",
        json={"feature_name": "Deploy Pipeline", "content": "# Plan"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "plan-deploy-pipeline.prompt.md"


async def test_create_plan_duplicate_returns_409(client):
    payload = {"feature_name": "Dup Plan", "content": "# Plan"}
    await client.post("/api/v1/artifacts/plans", json=payload)
    resp = await client.post("/api/v1/artifacts/plans", json=payload)
    assert resp.status_code == 409


async def test_list_artifacts_all_empty(client):
    resp = await client.get("/api/v1/artifacts?type=all")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_artifacts_prd(client, fake_dirs):
    fake_dirs["prds"].mkdir(parents=True, exist_ok=True)
    (fake_dirs["prds"] / "prd-alpha.md").write_text("# Alpha")
    resp = await client.get("/api/v1/artifacts?type=prd")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["filename"] == "prd-alpha.md"


async def test_list_artifacts_invalid_type(client):
    resp = await client.get("/api/v1/artifacts?type=invalid")
    assert resp.status_code == 422
