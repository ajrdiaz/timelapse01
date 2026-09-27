import copy
import json

import pytest
from fastapi.testclient import TestClient

from engine.brand import apply_brand, load_brand, locked_paths
from engine.schema import Scene

IDEA = {"titulo": "T", "gancho": "CONSTRUÍ UNA PISCINA", "proyecto": "piscina", "revelacion": "spa",
        "tono": "divertido", "por_que_funciona": "x", "estilo_visual": "corte_lateral"}


def restyled(d: dict) -> dict:
    """Escena con el estilo cambiado como podría hacerlo Claude."""
    d = copy.deepcopy(d)
    d["tipografia"]["fuente"] = "DejaVu"
    d["tipografia"]["tamanos"]["titulo"] = 140
    d["cta"]["final"]["color_fondo"] = "#00FF00"
    d["cta"]["final"]["posicion"] = "abajo"
    d["audio"]["bpm"] = 135
    d["audio"]["estilo_drop"] = "chiptune"
    d["general"]["resolucion"] = "720x1280"
    d["gancho"]["lineas"] = [{"texto": "A", "color": "#123456"}, {"texto": "B", "color": "#654321"},
                             {"texto": "C", "color": "#ABCDEF"}]
    return d


def test_brand_file_matches_defaults_and_reference(example_dict):
    d = Scene().model_dump()
    assert apply_brand(d) == d
    assert apply_brand(example_dict) == example_dict


def test_apply_brand_restores_style_and_keeps_content(example_dict):
    d = restyled(example_dict)
    d["revelacion"]["tipo_interior"] = "spa"
    d["revelacion"]["callouts"] = []
    d["revelacion"]["color_acento"] = "#00AA88"
    d["etapas"][0]["titulo"] = "OTRO TÍTULO"
    out = apply_brand(d)
    for path in ("tipografia", "cta", "audio.bpm", "audio.estilo_drop", "general.resolucion"):
        a, b = out, example_dict
        for k in path.split("."):
            a, b = a[k], b[k]
        assert a == b, path
    assert [ln["color"] for ln in out["gancho"]["lineas"]] == ["#FFFFFF", "#FFD400", "#FFFFFF"]
    assert [ln["texto"] for ln in out["gancho"]["lineas"]] == ["A", "B", "C"]
    # el contenido no se toca
    assert out["revelacion"]["tipo_interior"] == "spa"
    assert out["revelacion"]["color_acento"] == "#00AA88"
    assert out["etapas"][0]["titulo"] == "OTRO TÍTULO"
    Scene.model_validate(out)


def test_locked_paths():
    paths = locked_paths()
    assert "tipografia.fuente" in paths and "gancho.lineas.*.color" in paths
    assert not any(p.startswith(("etapas", "revelacion.tipo_interior", "revelacion.callouts")) for p in paths)


def test_missing_or_invalid_brand_file(tmp_path, monkeypatch, example_dict):
    monkeypatch.setenv("TF_BRAND_FILE", str(tmp_path / "no_existe.json"))
    d = restyled(example_dict)
    assert apply_brand(d) == d and locked_paths() == []
    bad = tmp_path / "brand.json"
    bad.write_text(json.dumps({"tipografia": {"tamaño": 3}}), encoding="utf-8")
    monkeypatch.setenv("TF_BRAND_FILE", str(bad))
    with pytest.raises(ValueError):
        load_brand()


@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend.app import config

    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
    from backend.app.main import app

    return TestClient(app)


def test_api_saves_with_brand(client, example_dict):
    assert "tipografia.fuente" in client.get("/api/brand").json()["campos"]
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    r = client.put(f"/api/projects/{pid}/scene", json={"scene": restyled(example_dict)})
    assert r.status_code == 200
    saved = client.get(f"/api/projects/{pid}").json()["scene"]
    assert saved["tipografia"]["fuente"] == "Anton" and saved["cta"]["final"]["color_fondo"] == "#FF2D55"


def test_llm_scene_gets_brand(client, monkeypatch, example_dict):
    from backend.app import llm

    prompts = []

    async def fake(system, prompt, schema, model):
        prompts.append((system, prompt))
        return {"descripcion_md": "# x", "scene": restyled(example_dict)}

    monkeypatch.setattr(llm, "_query_json", fake)
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    r = client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62})
    assert r.status_code == 200, r.text
    s = r.json()["scene"]
    assert s["tipografia"]["tamanos"]["titulo"] == 92 and s["audio"]["bpm"] == 112
    assert s["general"]["resolucion"] == "1080x1920" and s["gancho"]["lineas"][0]["color"] == "#FFFFFF"
    assert "tipografia.fuente" in prompts[0][0]

    # la siguiente tanda de ideas recibe la idea ya usada
    async def fake_ideas(system, prompt, schema, model):
        prompts.append((system, prompt))
        return {"ideas": [IDEA] * 5}

    monkeypatch.setattr(llm, "_query_json", fake_ideas)
    assert client.post("/api/ideas", json={"tema": ""}).status_code == 200
    assert "CONSTRUÍ UNA PISCINA" in prompts[-1][1]
