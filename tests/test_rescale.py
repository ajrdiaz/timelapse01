import copy

import pytest

from engine.schema import Scene, chain_starts, rescale_times


@pytest.mark.parametrize("dur", [30, 62, 75.5, 120, 180])
def test_rescale_fills_duration(example_dict, dur):
    d = rescale_times(example_dict, dur)
    s = Scene.model_validate(d)
    assert s.general.duracion_seg == dur
    assert s.etapas[-1].fin_seg == pytest.approx(dur, abs=0.01)
    assert s.etapas[0].inicio_seg == pytest.approx(s.gancho.duracion_seg)


def test_rescale_is_proportional(example_dict):
    d = rescale_times(example_dict, 122)  # 2× el tiempo de etapas (60 → 119.5)
    a = [e["duracion_seg"] for e in example_dict["etapas"]]
    b = [e["duracion_seg"] for e in d["etapas"]]
    k = b[0] / a[0]
    for x, y in zip(a, b):
        assert y == pytest.approx(x * k, rel=0.01)


def test_rescale_fixes_broken_timeline(example_dict):
    d = copy.deepcopy(example_dict)
    d["etapas"][2]["duracion_seg"] = 20  # ahora no suma
    d = rescale_times(d)
    Scene.model_validate(d)


def test_chain_starts(example_dict):
    d = copy.deepcopy(example_dict)
    for e in d["etapas"]:
        e["inicio_seg"] = 0
    d = chain_starts(d)
    Scene.model_validate(d)
