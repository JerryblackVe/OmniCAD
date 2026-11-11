"""B-298: la holgura negativa de impresión se informa en Rosca y Agujero por API."""

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


@pytest.fixture(params=["create_thread", "create_hole"])
def rosca(request):
    sesion = api.Sesion()
    herramienta = request.param
    radio = 5 if herramienta == "create_thread" else 10
    resultado = api.llamar(sesion, "create_cylinder", {"radius": radio, "height": 8})
    assert resultado["ok"], resultado
    argumentos = {"thread": "M10"}
    if herramienta == "create_thread":
        argumentos.update(faces="%CYLINDER", modeled=True, length=4.5)
    else:
        argumentos.update(face=">Z", hole_tap="modeled", depth=4.5)
    return sesion, herramienta, argumentos


@pytest.mark.parametrize("holgura", [-0.8, -1.2])
def test_holgura_negativa_falla_con_mensaje_claro_y_sin_cambiar_el_documento(rosca, holgura):
    sesion, herramienta, argumentos = rosca
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, herramienta, {**argumentos, "print_clearance": holgura})
    assert not resultado["ok"], resultado
    assert resultado["error_kind"] == "OPERATION_FAILED", resultado
    mensaje = resultado["mensaje"].lower()
    assert "holgura" in mensaje and "negativa" in mensaje, resultado
    assert "usá 0 o un valor positivo" in mensaje, resultado
    assert sesion.doc.a_dict() == antes


def test_holgura_cero_sigue_modelando_la_rosca(rosca):
    sesion, herramienta, argumentos = rosca
    cuerpo = next(iter(sesion.doc.estado_final.cuerpos.values()))
    volumen_inicial = geo.volumen(cuerpo.forma)
    resultado = api.llamar(sesion, herramienta, {**argumentos, "print_clearance": 0})
    assert resultado["ok"], resultado
    cuerpo = next(iter(sesion.doc.estado_final.cuerpos.values()))
    assert geo.es_valida(cuerpo.forma)
    assert 0 < geo.volumen(cuerpo.forma) < volumen_inicial - 1


@pytest.mark.parametrize("holgura", [-0.8, -1.2])
def test_diametro_de_la_previa_rapida_rechaza_holgura_negativa(holgura):
    with pytest.raises(geo.ErrorGeometria, match="holgura.*negativa"):
        sc.diametro_taladro_rosca("M10", holgura=holgura)
