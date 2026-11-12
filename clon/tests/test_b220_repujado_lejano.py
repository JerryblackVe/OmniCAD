"""B-220: envolver no debe dar otra vuelta al cilindro para alcanzar un perfil lejano."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _boceto(sesion, plano, desfase, x1, y1, x2, y2):
    _llamar(sesion, "create_construction_plane", plane=plano, offset=desfase, name="Plano del perfil")
    boceto = _llamar(sesion, "create_sketch", plane="Plano del perfil")["sketch"]["id"]
    _llamar(sesion, "draw_rectangle", sketch=boceto, x1=x1, y1=y1, x2=x2, y2=y2)
    return boceto


def test_empalme_lejano_no_recibe_material_al_envolver():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=60, width=40, height=10, anchor="corner")
    _llamar(sesion, "fillet", edges=">Z", radius=3)
    boceto = _boceto(sesion, "XY", 10, 20, 15, 30, 25)
    cara = _llamar(sesion, "find_faces", selector="%CYLINDER and <X")["faces"][0]
    assert cara["id"] == "Cuerpo1/F3" and cara["radius"] == pytest.approx(3)
    antes = geo.volumen(sesion.cuerpo("Cuerpo1").forma)

    respuesta = api.llamar(sesion, "create_emboss", {
        "sketch": boceto, "faces": cara["id"], "wrap": True, "depth": 1})

    assert not respuesta["ok"], respuesta
    assert respuesta["error_kind"] == "OPERATION_FAILED", respuesta
    assert "Los perfiles no caen sobre las caras elegidas" in respuesta["mensaje"]
    cuerpo = sesion.cuerpo("Cuerpo1").forma
    assert geo.es_valida(cuerpo)
    assert geo.volumen(cuerpo) == pytest.approx(antes, rel=0, abs=1e-6)


@pytest.mark.parametrize("agujero,aumento", [(False, 16.8), (True, 15.2)])
def test_perfil_cercano_sigue_repujando_el_cilindro(agujero, aumento):
    sesion = api.Sesion()
    if agujero:
        _llamar(sesion, "create_box", length=40, width=40, height=20)
    _llamar(sesion, "create_cylinder", radius=10, height=20, operation="cut" if agujero else "new_body")
    boceto = _boceto(sesion, "YZ", 10, -2, 8, 2, 12)
    antes = geo.volumen(sesion.cuerpo("Cuerpo1").forma)

    _llamar(sesion, "create_emboss", sketch=boceto, faces="%CYLINDER", wrap=True, depth=1)

    cuerpo = sesion.cuerpo("Cuerpo1").forma
    assert geo.es_valida(cuerpo)
    assert geo.volumen(cuerpo) - antes == pytest.approx(aumento, rel=1e-5)
