"""Opacidad y búsqueda del navegador disponibles para MCP y CLI."""
import pytest

from omnicad import api
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


@pytest.fixture
def sesion():
    doc = Documento()
    for i in range(2):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), f"Pieza {i}", forma="caja", ancho=10, largo=10, alto=10))
    return api.Sesion(doc)


def test_opacidad_por_nombre_y_raiz_es_atomica_y_se_guarda(sesion):
    ids = list(sesion.doc.estado_final.cuerpos)
    nombre = sesion.nombre_cuerpo(sesion.cuerpo(ids[0]))
    r = api.llamar(sesion, "set_body_opacity", {"bodies": [nombre, ids[0]], "opacity": 50})
    assert r["ok"] and r["result"] == {"bodies": [ids[0]], "opacity": 50}
    assert sesion.doc.propiedad(ids[0], "opacidad") == 0.5
    assert sesion.doc.propiedad(ids[1], "opacidad") is None
    assert api.llamar(sesion, "set_body_opacity", {"opacity": 30})["ok"]
    assert all(sesion.doc.propiedad(cid, "opacidad") == 0.3 for cid in ids)
    assert Documento.desde_dict(sesion.doc.a_dict()).propiedad(ids[1], "opacidad") == 0.3
    sesion.doc.deshacer()
    assert sesion.doc.propiedad(ids[0], "opacidad") == 0.5
    assert sesion.doc.propiedad(ids[1], "opacidad") is None
    assert api.llamar(sesion, "set_body_opacity", {"opacity": 100})["ok"]
    assert all(sesion.doc.propiedad(cid, "opacidad") is None for cid in ids)


@pytest.mark.parametrize("args", [{"opacity": -1}, {"opacity": 101}, {"opacity": "mitad"},
                                 {"opacity": 50, "bodies": ["op1.c1", "inexistente"]}])
def test_opacidad_invalida_no_cambia_documento(sesion, args):
    antes = sesion.doc.a_dict()
    assert not api.llamar(sesion, "set_body_opacity", args)["ok"]
    assert sesion.doc.a_dict() == antes


def test_opacidad_sin_cuerpos_y_busqueda_sin_ventana_fallan():
    s = api.Sesion()
    assert api.llamar(s, "set_body_opacity", {"opacity": 50})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "find_in_window", {})["error_kind"] == "APP_NOT_RUNNING"


def test_busqueda_resuelve_nombres_y_valida_antes_de_llamar(sesion):
    ids = list(sesion.doc.estado_final.cuerpos)
    llamados = []
    sesion.buscar_en_ventana = lambda cuerpos: llamados.append(cuerpos) or {"bodies": cuerpos}
    assert api.llamar(sesion, "find_in_window", {})["result"] == {"bodies": ids}
    nombre = sesion.nombre_cuerpo(sesion.cuerpo(ids[0]))
    assert api.llamar(sesion, "find_in_window", {"bodies": [nombre, ids[0]]})["result"] == {"bodies": [ids[0]]}
    assert not api.llamar(sesion, "find_in_window", {"bodies": [ids[1], "inexistente"]})["ok"]
    assert llamados == [ids, [ids[0]]]
