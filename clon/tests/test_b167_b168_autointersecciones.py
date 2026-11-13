# -*- coding: utf-8 -*-
"""B-168 y B-167: un paso que deja un cuerpo cruzado consigo mismo no puede quedar «ok» callado: avisa.

B-168 — tubo por aristas con esquinas. La ruta `Cuerpo1/E1` + `Cuerpo1/E2` de un cilindro (el círculo de la tapa y
la arista de costura) forma una esquina: el inglete del barrido pliega la sección sobre sí misma y quedan 5
autointersecciones en un cuerpo que el kernel devuelve como válido. Con la transición redondeada de OCC
(`BRepBuilderAPI_RoundCorner`) el kernel no construye el sólido, así que se avisa.

cuerpo queda con autointersecciones.
"""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rev


def _r(s, nombre, **args):
    """Llamada que tiene que salir bien: devuelve la respuesta completa (con `result` y `avisos`)."""
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r


def _autointersecciones(forma):
    """Cantidad de autointersecciones, con el mismo análisis BOPAlgo que usa el desfase de superficies."""
    return rev._autointersecciones_seguras(forma, 1, 20.0)[0]


def _cilindro(s):
    _r(s, "create_cylinder", radius=15, height=30)


def _chapa(s, ancho, alto):
    _r(s, "create_sketch")
    _r(s, "draw_rectangle", sketch="Boceto1", x1=0, y1=0, x2=ancho, y2=alto)
    return _r(s, "create_base_flange", sketch="Boceto1", thickness=0.8)["result"]["bodies_created"][0]["id"]


# ---------------------------------------------------------------- B-168 · tubo con esquinas

def test_b168_tubo_con_esquina_avisa_en_vez_de_quedar_ok():
    s = api.Sesion()
    _cilindro(s)
    r = _r(s, "create_pipe", edges=["Cuerpo1/E1", "Cuerpo1/E2"], section_size=8)
    forma = s.cuerpo(r["result"]["bodies_created"][0]["id"]).forma
    assert _autointersecciones(forma) == 5                       # el kernel sigue dejando la esquina plegada
    assert geo.volumen(forma) == pytest.approx(6245.5355, rel=1e-5)   # Linux da 6245.5387 (esquina plegada: el kernel no es idéntico entre sistemas)
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "aviso"
    aviso = " ".join(r["avisos"]).lower()
    assert "autointerseccion" in aviso and "esquina" in aviso, r["avisos"]
    assert "fusion" not in aviso, r["avisos"]                  # la ayuda de Fusion no dice que redondee esas esquinas


def test_b168_tubo_recto_normal_sigue_ok_y_con_el_mismo_volumen():
    s = api.Sesion()
    _cilindro(s)
    r = _r(s, "create_pipe", edges=["Cuerpo1/E2"], section_size=8)
    forma = s.cuerpo(r["result"]["bodies_created"][0]["id"]).forma
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"
    assert geo.volumen(forma) == pytest.approx(math.pi * 4 ** 2 * 30, rel=1e-6)     # 1507.9645 mm³, como hoy


def test_b168_cuando_no_se_pudo_contar_tambien_se_avis(monkeypatch):
    """El recuento de una forma B-spline tiene plazo y devuelve None cuando no termina: eso no puede dejar el
    paso en «ok» callado, que es justo el defecto de B-168."""
    s = api.Sesion()
    _cilindro(s)
    real = rev._autointersecciones_seguras
    monkeypatch.setattr(rev, "_autointersecciones_seguras",
                        lambda forma, limite, plazo: real(forma, limite, 0.001))    # plazo agotado a propósito
    r = _r(s, "create_pipe", edges=["Cuerpo1/E1", "Cuerpo1/E2"], section_size=8)
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "aviso"
    assert any("autointerseccion" in a.lower() for a in r["avisos"]), r["avisos"]


# ---------------------------------------------------------------- B-167 · patrón sobre chapa

def test_b167_patron_con_copias_que_se_pisan_las_funde_sin_autointersecciones():
    s = api.Sesion()
    cid = _chapa(s, 20, 15)
    r = _r(s, "create_geometric_pattern", faces=["Cuerpo1/F6"], operation="join", distance=5, size1=6, size2=6)
    forma = s.cuerpo(cid).forma
    assert _autointersecciones(forma) == 0                       # antes 24: las copias de la rejilla se pisaban
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(507.354, abs=1e-2)
    assert r["avisos"] == []


def test_b167_patron_en_las_dos_caras_de_la_chapa_corta_rapido_y_sin_cruces():
    """Caso del cazador: esferas por defecto en F5 y F6 (0,8 mm de chapa): las de una cara pisan a las de la otra.
    Antes: 117 s y «resultado imposible»; ahora segundos y 0 autointersecciones."""
    import time
    s = api.Sesion()
    cid = _chapa(s, 80, 50)
    t = time.perf_counter()
    r = _r(s, "create_geometric_pattern", faces=["Cuerpo1/F5", "Cuerpo1/F6"])
    assert time.perf_counter() - t < 60
    forma = s.cuerpo(cid).forma
    assert _autointersecciones(forma) == 0 and geo.es_valida(forma) and r["avisos"] == []
    assert geo.volumen(forma) == pytest.approx(2689.216, abs=1e-1)


def test_b167_patron_plano_normal_sigue_ok_y_con_el_mismo_volumen():
    s = api.Sesion()
    cid = _chapa(s, 40, 30)
    r = _r(s, "create_geometric_pattern", faces=["Cuerpo1/F6"], operation="cut", distance=8, size1=6, size2=6)
    forma = s.cuerpo(cid).forma
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"
    assert geo.volumen(forma) == pytest.approx(761.2503, abs=1e-3)
