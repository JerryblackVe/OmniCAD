"""infer_sketch_snap y las preferencias de ayudas de dibujo, por la API (la misma que usan MCP y CLI)."""
import pytest

from omnicad import api


def llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def s():
    sesion = api.Sesion()
    llamar(sesion, "create_sketch", name="Base")
    for a, b in (((-75, 0), (0, 0)), ((0, 0), (0, 75)), ((0, 75), (-75, 0))):
        llamar(sesion, "draw_line", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
    return sesion


def test_alineacion_solo_guia_sin_restriccion(s):
    r = llamar(s, "infer_sketch_snap", x=40, y=75.1)
    sel = r["selected"]
    assert sel["type"] == "aligned_horizontal" and sel["constraint"] is None
    assert (sel["x"], sel["y"]) == (40, 75)
    assert sel["guides"] == [[0, 75, 40, 75]]
    assert r["count"] == len(r["candidates"]) >= 1


def test_punto_medio_dice_la_restriccion_que_dejaria(s):
    sel = llamar(s, "infer_sketch_snap", x=-37.6, y=37.4)["selected"]
    assert sel["type"] == "midpoint" and sel["constraint"]["type"] == "midpoint"
    assert (sel["x"], sel["y"]) == (-37.5, 37.5)
    shift = llamar(s, "infer_sketch_snap", x=-37.6, y=37.4, shift=True)["selected"]
    assert shift["constraint"]["type"] == "coincident"


def test_tipos_y_alternativa(s):
    solo = llamar(s, "infer_sketch_snap", x=40, y=75.1, types=["midpoint"])
    assert solo["selected"] is None and solo["candidates"] == []
    r = llamar(s, "infer_sketch_snap", x=-37.6, y=37.4, tolerance=1)
    otra = llamar(s, "infer_sketch_snap", x=-37.6, y=37.4, tolerance=1, alternative=len(r["candidates"]))
    assert otra["selected"] == r["selected"]                      # da la vuelta


def test_horizontal_desde_la_base_con_alineacion_cruzada(s):
    sel = llamar(s, "infer_sketch_snap", x=20.2, y=40.3, base_x=-30, base_y=40, types=["horizontal", "alignment"])
    assert sel["selected"]["type"] == "horizontal" and sel["selected"]["constraint"]["type"] == "horizontal"


def test_la_consulta_no_modifica_el_documento(s):
    antes = s.doc.a_dict()
    llamar(s, "infer_sketch_snap", x=40, y=75.1)
    assert s.doc.a_dict() == antes
    assert not s.doc._deshacer or s.doc.a_dict() == antes


@pytest.mark.parametrize("args", [dict(x=float("nan"), y=0), dict(x=0, y=0, tolerance=0), dict(x=0, y=0, base_x=1),
                                  dict(x=0, y=0, types=["nada"]), dict(x=0, y=0, alternative=-1)])
def test_argumentos_invalidos(s, args):
    r = api.llamar(s, "infer_sketch_snap", args)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_preferencias_de_ayudas_se_leen_y_se_cambian(s, tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "ajustes.ini"))
    lista = llamar(s, "get_preferences", keys=["boceto/inferencias", "boceto/sensibilidad_px", "boceto/inf_alineacion"])
    assert [p["value"] for p in lista["preferences"]] == [True, 8, True]
    llamar(s, "set_preference", key="boceto/inf_alineacion", value=False)
    llamar(s, "set_preference", key="boceto/sensibilidad_px", value=12)
    nuevo = llamar(s, "get_preferences", keys=["boceto/inf_alineacion", "boceto/sensibilidad_px"])
    assert [p["value"] for p in nuevo["preferences"]] == [False, 12]
    malo = api.llamar(s, "set_preference", {"key": "boceto/sensibilidad_px", "value": 99})
    assert not malo["ok"]
