import pytest
from fastapi.testclient import TestClient

IDEA = {"titulo": "T", "gancho": "CONSTRUÍ UNA PISCINA", "proyecto": "piscina", "revelacion": "spa",
        "tono": "divertido", "por_que_funciona": "x", "estilo_visual": "corte_lateral"}
POST = {"descripcion": "Nadie sabe qué hay bajo mi patio 👀 ¿Qué le pondrías tú?",
        "hashtags": ["#timelapse", "construccion", "#Mi Patio", "#bunker", "#spa", "#timelapse"],
        "etiqueta_ia": True, "nota_etiqueta_ia": "Es una animación generada por computadora."}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend.app import config

    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
    from backend.app.main import app

    return TestClient(app)


def _fake_llm(monkeypatch, example_dict, with_post: bool):
    from backend.app import llm

    calls = []

    async def fake(system, prompt, schema, model):
        calls.append(system)
        if "community manager" in system:
            return POST
        out = {"descripcion_md": "# x", "scene": example_dict}
        if with_post:
            out["publicacion"] = POST
        return out

    monkeypatch.setattr(llm, "_query_json", fake)
    return calls


def test_scene_includes_ready_to_paste_post(client, monkeypatch, example_dict):
    calls = _fake_llm(monkeypatch, example_dict, with_post=True)
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    r = client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62}).json()
    assert len(calls) == 1  # una sola llamada: guion + publicación
    assert r["publicacion"]["hashtags"] == ["#timelapse", "#construccion", "#MiPatio", "#bunker", "#spa"]
    assert client.get(f"/api/projects/{pid}").json()["publicacion"] == r["publicacion"]
    txt = client.get(f"/api/projects/{pid}/files/publicacion.txt").text
    assert txt == f"{POST['descripcion']}\n\n#timelapse #construccion #MiPatio #bunker #spa\n"


def test_scene_without_post_asks_separately(client, monkeypatch, example_dict):
    calls = _fake_llm(monkeypatch, example_dict, with_post=False)
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    r = client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62}).json()
    assert len(calls) == 2 and r["publicacion"]["descripcion"] == POST["descripcion"]


def test_post_hook_keeps_existing_post(client, monkeypatch, example_dict):
    from backend.app import main, projects

    calls = _fake_llm(monkeypatch, example_dict, with_post=True)
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62})
    p = projects.get(pid)
    p.save_publicacion({**p.publicacion(), "descripcion": "editada"})

    class Job:
        project_id = pid

    main._post_hook(Job)
    assert len(calls) == 1 and p.publicacion()["descripcion"] == "editada"
    # «Regenerar» sí la reescribe
    assert client.post(f"/api/projects/{pid}/post-text").json()["descripcion"] == POST["descripcion"]


def test_regenerate_from_scratch_resets_history(client, monkeypatch, example_dict):
    import copy

    _fake_llm(monkeypatch, example_dict, with_post=True)
    pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
    assert len(client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62}).json()["history"]) == 1
    edited = copy.deepcopy(client.get(f"/api/projects/{pid}").json()["scene"])
    edited["etapas"][0]["titulo"] = "EDITADO"
    assert client.put(f"/api/projects/{pid}/scene", json={"scene": edited}).json()["version"] == 2
    # el mismo guion otra vez: aunque la escena no cambie respecto a la v1, el historial queda en 1 versión
    r = client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62}).json()
    assert [h["version"] for h in r["history"]] == [1]
    assert client.post(f"/api/projects/{pid}/undo").status_code == 409


def test_new_scene_gets_random_music(client, monkeypatch, example_dict):
    _fake_llm(monkeypatch, example_dict, with_post=True)
    progs, seeds = [], set()
    for _ in range(3):
        pid = client.post("/api/projects", json={"titulo": "x"}).json()["id"]
        s = client.post("/api/scene", json={"project_id": pid, "idea": IDEA, "duracion_seg": 62}).json()["scene"]
        seeds.add(s["general"]["seed"])
        progs.append(s["audio"]["progresion"])
    assert len(seeds) == 3  # Claude devolvió siempre seed 7; el backend la reemplaza
    assert len(set(progs)) == 3  # no se repite la progresión de los videos anteriores


def test_hashtags_capped_at_tiktok_limit():
    from backend.app.prompts import PostText

    tags = ["#a", "#b", "c", "#d", "#e", "#f", "#g", "#h"]
    p = PostText(descripcion="x", hashtags=tags, etiqueta_ia=True, nota_etiqueta_ia="n")
    assert p.hashtags == ["#a", "#b", "#c", "#d", "#e"]
    with pytest.raises(ValueError):
        PostText(descripcion="x", hashtags=["#a", "#A", "a"], etiqueta_ia=True, nota_etiqueta_ia="n")
