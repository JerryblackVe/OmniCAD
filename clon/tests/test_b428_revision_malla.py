"""B-428: el resumen del navegador también debe aceptar un cuerpo de malla válido."""
import pytest

from test_b428_area_superficie import _elegir, _llamar, ventana as ventana

from omnicad import api


def test_propiedades_del_navegador_aceptan_una_malla_cerrada(ventana):
    sesion = api.Sesion()
    solido = _llamar(sesion, "create_box", length=10, width=20, height=30)["bodies_created"][0]["id"]
    malla = _llamar(sesion, "tessellate", bodies=[solido])["bodies_created"][0]["id"]
    forma = sesion.cuerpo(malla).forma
    assert forma.es_cerrada()
    propiedades = _llamar(sesion, "get_physical_properties", bodies=[malla])["bodies"][0]
    assert propiedades["type"] == "mesh"
    assert propiedades["volume"] == pytest.approx(6000)
    assert propiedades["area"] == pytest.approx(2200)
    _elegir(ventana, sesion, [malla])

    ventana._propiedades(malla)

    assert "malla válida" in ventana.timeline.estado.toolTip()
