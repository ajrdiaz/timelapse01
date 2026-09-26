import pytest
from PIL import Image

from engine.catalog import STAGE_TYPES
from engine.frame import FrameRenderer
from engine.interiors import INTERIORS
from engine.schema import Scene
from engine.stages import REGISTRY, WorldState, make_stage


@pytest.fixture(scope="module")
def fr():
    return FrameRenderer(Scene(), size=(360, 640), ss=1)


def test_registry_complete():
    assert set(REGISTRY) == set(STAGE_TYPES)


@pytest.mark.parametrize("tipo", list(STAGE_TYPES))
@pytest.mark.parametrize("t", [0.0, 0.5, 1.0])
def test_stage_draws(fr, tipo, t):
    s = fr.scene
    etapa = s.etapas[0].model_copy(update={"tipo": tipo, "obreros": 3, "maquina": "excavadora"})
    stage = make_stage(etapa)
    canvas = fr.base_layer().copy()
    ctx = fr._ctx(canvas, 0, s.flash_time + 1 if tipo == "revelacion" else 5.0, True, WorldState())
    ctx.etapa = etapa
    stage.apply_state(ctx.state, t)
    stage.draw(canvas, t, ctx)
    stage.draw_active(canvas, t, ctx)
    for x, y, f in stage.worker_spots(ctx, t):
        assert 0 <= x <= canvas.width
    assert stage.excavator(ctx, t) is not None
    ev = stage.sfx_events(10.0, 14.0)
    assert all(10.0 <= e.t <= 14.0 + 1e-6 for e in ev)


@pytest.mark.parametrize("tipo", list(INTERIORS))
def test_interiors_draw(fr, tipo):
    s = Scene.model_validate({**Scene().model_dump(), "revelacion": {**Scene().revelacion.model_dump(), "tipo_interior": tipo, "callouts": []}})
    f = FrameRenderer(s, size=(360, 640), ss=1)
    img = f.render(s.flash_time + 2.0)
    assert img.size == (360, 640)
    for obj in INTERIORS[tipo].OBJECTS:
        INTERIORS[tipo].anchor(obj, f._ctx(Image.new("RGBA", (10, 10)), 0, 1.0, False, WorldState()))


def test_deterministic():
    s = Scene()
    a = FrameRenderer(s, size=(360, 640), ss=1).render(20.0)
    b = FrameRenderer(s, size=(360, 640), ss=1).render(20.0)
    assert a.tobytes() == b.tobytes()
