import copy

import pytest
from pydantic import ValidationError

from engine.schema import Scene, chain_starts, coherence_errors, llm_schema, rescale_times


def test_example_valid(example_dict):
    s = Scene.model_validate(example_dict)
    assert s.general.duracion_seg == 62
    assert s.etapas[-1].fin_seg == pytest.approx(62)


def test_defaults_valid():
    s = Scene()
    assert coherence_errors(s) == []


@pytest.mark.parametrize(
    "path,value",
    [
        (("general", "duracion_seg"), 10),  # < 15
        (("general", "fps"), 25),
        (("gancho", "lineas"), []),
        (("revelacion", "tipo_interior"), "castillo"),
        (("cta", "final", "color_fondo"), "rojo"),
        (("revelacion", "remate_2"), "X" * 80),  # demasiado largo
        (("audio", "bpm"), 200),
    ],
)
def test_invalid_fields(example_dict, path, value):
    d = copy.deepcopy(example_dict)
    node = d
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    with pytest.raises(ValidationError):
        Scene.model_validate(d)


def test_overlap_detected(example_dict):
    d = copy.deepcopy(example_dict)
    d["etapas"][3]["inicio_seg"] -= 1.0
    with pytest.raises(ValidationError, match="solapa"):
        Scene.model_validate(d)


def test_gap_detected(example_dict):
    d = copy.deepcopy(example_dict)
    d["etapas"][3]["inicio_seg"] += 1.0
    d["etapas"][3]["duracion_seg"] -= 1.0
    with pytest.raises(ValidationError, match="hueco"):
        Scene.model_validate(d)


def test_days_must_increase(example_dict):
    d = copy.deepcopy(example_dict)
    d["etapas"][4]["dia_inicio"] = 1
    with pytest.raises(ValidationError, match="retrocede"):
        Scene.model_validate(d)


def test_times_fit_duration(example_dict):
    d = copy.deepcopy(example_dict)
    d["cta"]["final"]["aparicion_seg"] = 70
    with pytest.raises(ValidationError, match="supera la duración"):
        Scene.model_validate(d)


def test_callout_object_must_exist(example_dict):
    d = copy.deepcopy(example_dict)
    d["revelacion"]["callouts"][0]["objeto"] = "jacuzzi"
    with pytest.raises(ValidationError, match="no existe"):
        Scene.model_validate(d)


def test_extra_field_rejected(example_dict):
    d = copy.deepcopy(example_dict)
    d["general"]["foo"] = 1
    with pytest.raises(ValidationError):
        Scene.model_validate(d)


def test_llm_schema_is_closed():
    sch = llm_schema(Scene)
    assert sch["additionalProperties"] is False
    assert "general" in sch["required"]
