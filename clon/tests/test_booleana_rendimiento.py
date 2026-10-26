"""Unir una extrusión a un cuerpo grande tiene que costar lo que la booleana, no diez veces más.

Medido en `scripts/bench_booleana.py` (evidencias/booleanas_2026-10-26): al editar «Cuerpo nuevo» → «Unir»,
`aplicar_resultado` pagaba el volumen con malla (`geo.volumen` en un cuerpo con caras B-spline: 20 s de 25), el
`BRepCheck` de todo el resultado (11 s en una placa de 3000 agujeros) y las cajas exactas de cada cara en `se_tocan`."""
import math
import time

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepTools import BRepTools
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo

AGUJEROS = 120


def _placa_con_agujeros_bspline(n):
    """Placa 400×200×20 con `n` agujeros de caras B-spline en la mitad x < 0 (la otra queda libre para la extrusión)."""
    columnas = max(1, int(math.sqrt(n * 185 / 190)))
    filas = math.ceil(n / columnas)
    paso_x, paso_y = 185.0 / columnas, 190.0 / filas
    cortes = []
    for k in range(n):
        x, y = -195 + paso_x * (k % columnas + 0.5), -95 + paso_y * (k // columnas + 0.5)
        cortes.append(geo.BRepBuilderAPI_NurbsConvert(geo.cilindro(min(paso_x, paso_y) * 0.3, 30, (x, y, -5)), True).Shape())
    return geo.booleano(geo.caja(400, 200, 20, (-200, -100, 0)), geo.unir_todos(cortes), "cortar")


@pytest.fixture(scope="module")
def sesion_con_extrusion(tmp_path_factory):
    placa = _placa_con_agujeros_bspline(AGUJEROS)
    ruta = tmp_path_factory.mktemp("placa") / "placa.brep"
    BRepTools.Write_s(placa, str(ruta))
    s = api.Sesion()

    def llamar(herramienta, **a):
        r = api.llamar(s, herramienta, a)
        assert r["ok"], r
        return r["result"]
    llamar("open_document", path=str(ruta))
    boceto = llamar("create_sketch", plane=">Z")["sketch"]["id"]
    llamar("draw_rectangle", x1=100, y1=-10, x2=120, y2=10)
    paso = llamar("extrude", sketch=boceto, profile=0, distance=5, operation="new_body")["feature"]["id"]
    return s, placa, paso


def test_unir_conserva_el_resultado_y_cuesta_lo_que_la_booleana(sesion_con_extrusion):
    s, placa, paso = sesion_con_extrusion
    herramienta = geo.caja(20, 20, 5, (100, -10, 20))
    t = time.perf_counter()
    geo._booleana(placa, herramienta, "unir")
    pura = time.perf_counter() - t
    t = time.perf_counter()
    r = api.llamar(s, "edit_feature", {"feature": paso, "params": {"operacion": "unir"}})
    unir = time.perf_counter() - t
    assert r["ok"], r
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    forma = cuerpos[0].forma
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    # `volumen` (con control por malla): la integración exacta de caras B-spline recortadas se desvía unas décimas de %
    assert geo.volumen(forma) == pytest.approx(geo.volumen(placa) + 20 * 20 * 5, rel=1e-3)
    p0, p1 = geo.caja_envolvente(forma)
    assert (p1[2] - p0[2]) == pytest.approx(25.0, abs=1e-6)
    assert unir < 8 * pura + 0.5, f"unir {unir:.2f} s contra {pura:.2f} s de la booleana sola"


def test_validez_tras_booleana_revisa_solo_lo_cambiado():
    caja = geo.caja(10, 10, 10)
    cara_mala = _cara_con_contorno_cruzado()
    assert not geo.es_valida(cara_mala)              # la cara de prueba es de verdad inválida
    assert geo._es_valida_tras_booleana(caja, (caja,))
    assert not geo._es_valida_tras_booleana(cara_mala, (caja,))
    assert geo._es_valida_tras_booleana(cara_mala, (cara_mala,))      # una cara de las entradas no se vuelve a revisar


def _cara_con_contorno_cruzado():
    """Cara cuyo contorno se cruza a sí mismo (moño): BRepCheck la marca inválida."""
    poligono = BRepBuilderAPI_MakePolygon()
    for x, y in ((0, 0), (10, 10), (10, 0), (0, 10)):
        poligono.Add(gp_Pnt(x, y, 0))
    poligono.Close()
    return BRepBuilderAPI_MakeFace(poligono.Wire()).Face()
