import copy

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend.app import config

    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
    from backend.app.main import app

    return TestClient(app)


IDEA = {"titulo": "T", "gancho": "CONSTRUÍ UN BÚNKER", "proyecto": "búnker", "revelacion": "gamer",
        "tono": "divertido", "por_que_funciona": "x", "estilo_visual": "corte_lateral"}


def test_health_and_schema(client):
    h = client.get("/api/health").json()
    assert "ffmpeg" in h and "claude" in h
    assert "properties" in client.get("/api/schema").json()
    assert "gamer" in client.get("/api/catalog").json()["interiors"]


def test_save_validate_undo(client, example_dict):
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    assert client.put(f"/api/projects/{pid}/scene", json={"scene": example_dict}).status_code == 200
    bad = copy.deepcopy(example_dict)
    bad["etapas"][1]["duracion_seg"] += 3
    r = client.put(f"/api/projects/{pid}/scene", json={"scene": bad})
    assert r.status_code == 422 and r.json()["error"]["details"]
    assert client.post("/api/validate", json={"scene": bad}).json()["ok"] is False
    fixed = client.post("/api/rescale", json={"scene": bad}).json()["scene"]
    assert client.post("/api/validate", json={"scene": fixed}).json()["ok"] is True
    client.put(f"/api/projects/{pid}/scene", json={"scene": fixed})
    prev = client.post(f"/api/projects/{pid}/undo").json()["scene"]
    assert prev == example_dict


def test_preview(client, example_dict):
    r = client.post("/api/preview", json={"scene": example_dict, "times": [3.0], "calidad": 1})
    assert r.status_code == 200 and r.json()["frames"][0]["png"].startswith("data:image/png;base64,")


def test_llm_retry_then_success(client, monkeypatch):
    from backend.app import llm

    calls = []

    async def fake(system, prompt, schema, model):
        calls.append(prompt)
        ideas = [dict(IDEA) for _ in range(5)]
        if len(calls) == 1:
            ideas[0]["gancho"] = "UNO DOS TRES CUATRO CINCO SEIS SIETE OCHO NUEVE"
        return {"ideas": ideas}

    monkeypatch.setattr(llm, "_query_json", fake)
    r = client.post("/api/ideas", json={"tema": "x"})
    assert r.status_code == 200, r.text
    assert len(calls) == 2 and "NO pasó la validación" in calls[1]


def test_llm_fails_twice_shows_error(client, monkeypatch):
    from backend.app import llm

    async def fake(system, prompt, schema, model):
        return {"ideas": [IDEA]}  # solo 1 idea: inválido

    monkeypatch.setattr(llm, "_query_json", fake)
    r = client.post("/api/ideas", json={"tema": "x"})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "validation"
