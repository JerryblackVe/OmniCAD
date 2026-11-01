"""B-70: un agujero pasante solo abarca sus cuerpos objetivo."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def test_pasante_roscado_no_se_alarga_por_un_cuerpo_ajeno(monkeypatch):
    sesion = api.Sesion()

    def llamar(nombre, **argumentos):
        respuesta = api.llamar(sesion, nombre, argumentos)
        assert respuesta["ok"], respuesta
        return respuesta["result"]

    # Repro reducida del gato: el eje ajeno se reduce a una caja larga; queda la tuerca hexagonal.
    llamar("create_box", length=240, width=12, height=12, name="Ajeno")
    llamar("create_sketch", plane="YZ", name="Tuerca")
    llamar("create_polygon", sketch="Tuerca", sides=6, radius=11, center_y=60, kind="circumscribed")
    cuerpo = llamar("extrude", sketch="Tuerca", profile=0, distance=10, direction="symmetric")["bodies_created"][0]["id"]
    original = sc._surco_rosca
    largos = []

    def medir(origen, eje, diametro, paso, z0, largo, *args, **kwargs):
        largos.append(largo)
        assert largo == pytest.approx(11), "Un cuerpo ajeno no puede alargar la rosca de una tuerca de 10 mm."
        return original(origen, eje, diametro, paso, z0, largo, *args, **kwargs)

    monkeypatch.setattr(sc, "_surco_rosca", medir)
    llamar("create_hole", body=cuerpo, face="+X", hole_tap="modeled", thread="Tr12x3",
           through_all=True, print_clearance=0.15)
    assert largos
    forma = sesion.doc.estado_final.cuerpos[cuerpo].forma
    assert geo.es_valida(forma)
    # thread_class="auto" da la 7H de Fusion: Ø flancos 10,65 y Ø menor 9,1575 (básica: 10,5 y 9). Con la holgura de 0,15,
    # agujero r = 4,72875 y flancos corridos 0,225: el hueco mide 95,6635 mm² en cualquier corte, por 10 mm de tuerca.
    # La losa da esa cuenta; el total, un poco menos: GProp integra 0,001 % corto sobre la hélice entera.
    losa = geo.booleano(forma, geo.caja(1, 60, 60, origen=(-4.5, -30, 30)), "intersecar")
    assert geo.volumen(losa) == pytest.approx(2 * math.sqrt(3) * 11 ** 2 - 95.6635, abs=0.001)
    assert geo.volumen(forma) == pytest.approx(3234.8859, abs=0.01)
    assert geo.volumen(sesion.doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(34560)
