"""Ayudas de dibujo nuevas: Igual (BOC-45), intersección aparente (BOC-46), tangencia círculo-círculo (BOC-33) y
paralela/perpendicular/colineal en la línea de punto medio y el rectángulo 3p (BOC-48)."""
import math

import pytest

from test_boceto_fase5_ui import _clic, _mover
from test_boceto_fase5_ui import lienzo as lienzo

from omnicad.restricciones import Boceto
from omnicad.restricciones.inferencia import inferencias


def _solo(lz, *tipos):
    lz.ajustes_inf = {**lz.ajustes_inf, "tipos": tipos}


def _con_restriccion(lz, tipo, a, b):
    return any(r.tipo == tipo and set(r.entidades) == {a, b} for r in lz.b.restricciones.values())


# ---------------------------------------------------------------- motor (BOC-45, 46, 33)
def test_igual_de_largo_engancha_la_medida_y_deja_igual():
    b = Boceto()
    otra = b.agregar_linea((0, 0), (30, 0))
    (r, *_) = inferencias(b, (30.3, 10.2), 0.5, base=(0, 10), tipos={"igual"})
    assert r.tipo == "igual" and r.restriccion == ("igual", otra) and r.clase == 8
    assert math.dist(r.xy, (0, 10)) == pytest.approx(30, abs=1e-9)
    assert r.xy[1] == pytest.approx(10 + 0.2 * 30 / math.hypot(30.3, 0.2), abs=1e-9)       # sigue el rayo del cursor
    assert r.distancia == pytest.approx(abs(math.hypot(30.3, 0.2) - 30), abs=1e-9)


def test_igual_no_aparece_fuera_de_tolerancia_ni_con_la_misma_linea_excluida():
    b = Boceto()
    otra = b.agregar_linea((0, 0), (30, 0))
    assert inferencias(b, (31.5, 10), 0.5, base=(0, 10), tipos={"igual"}) == []
    assert inferencias(b, (30.1, 10), 0.5, base=(0, 10), tipos={"igual"}, excluir=[otra]) == []
    assert inferencias(b, (30.1, 10), 0.5, tipos={"igual"}) == []                      # sin base no hay medida


def test_igual_de_radio_compara_con_circulos_y_arcos_en_modo_centro():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 10)
    (r, *_) = inferencias(b, (27.2, 7.2), 0.5, base=(20, 0), tipos={"igual"}, centro=True)
    assert r.tipo == "igual" and r.restriccion == ("igual", c)
    assert math.dist(r.xy, (20, 0)) == pytest.approx(10, abs=1e-9)
    assert inferencias(b, (27.2, 7.2), 0.5, base=(20, 0), tipos={"igual"}) == []        # sin modo centro: no hay línea


@pytest.mark.parametrize("base,cursor,radio,caso", [
    ((40, 0), (10.2, 0.1), 30, "fuera"),           # distancia entre centros = r1 + r2
    ((3, 0), (-4.1, 0.2), 7, "dentro"),            # el nuevo queda dentro: |r1 - r2|
    ((3, 0), (16.1, 0.1), 13, "envuelve"),         # el nuevo envuelve al existente: d + r1
])
def test_tangente_circulo_propone_el_radio_que_deja_tangente(base, cursor, radio, caso):
    b = Boceto()
    c = b.agregar_circulo((0, 0), 10)
    (r, *_) = inferencias(b, cursor, 0.5, base=base, tipos={"tangente"}, centro=True)
    assert r.tipo == "tangente_circulo" and r.restriccion == ("tangente", c) and r.referencias == (c, caso)
    assert math.dist(r.xy, base) == pytest.approx(radio, abs=1e-9)
    assert len(r.guias) == 2


def test_tangente_circulo_no_propone_desde_el_mismo_centro_ni_con_el_arco_sin_ese_contacto():
    b = Boceto()
    b.agregar_circulo((0, 0), 10)
    assert inferencias(b, (5, 5), 0.5, base=(0, 0), tipos={"tangente"}, centro=True) == []     # concéntricos
    arco = Boceto()
    arco.agregar_arco_centro((0, 0), (10, 0), (0, 10))                                       # solo el cuarto de 0° a 90°
    assert inferencias(arco, (-9.9, 0), 0.5, base=(-40, 0), tipos={"tangente"}, centro=True) == []   # contacto a 180°
    assert inferencias(arco, (10.1, 0), 0.5, base=(40, 0), tipos={"tangente"}, centro=True)           # contacto a 0°: sí


def test_interseccion_aparente_es_solo_guia_con_tramos_hacia_el_cruce():
    b = Boceto()
    a = b.agregar_linea((0, 0), (10, 10))
    c = b.agregar_linea((0, 40), (10, 30))
    (r,) = inferencias(b, (20.2, 19.8), 0.5, tipos={"interseccion"})
    assert r.tipo == "interseccion_aparente" and r.restriccion is None and r.xy == pytest.approx((20, 20), abs=1e-9)
    assert sorted(r.referencias) == sorted((a, c)) and r.clase == 4
    assert sorted(g[0] for g in r.guias) == [(10.0, 10.0), (10.0, 30.0)] and all(g[1] == r.xy for g in r.guias)
    assert inferencias(b, (21, 21), 0.5, tipos={"interseccion"}) == []                          # lejos del cruce


def test_interseccion_aparente_cede_ante_la_real_y_no_cruza_paralelas():
    b = Boceto()
    b.agregar_linea((0, 0), (40, 40))
    b.agregar_linea((0, 40), (40, 0))
    assert [r.tipo for r in inferencias(b, (20, 20), 0.5, tipos={"interseccion"})] == ["interseccion"]
    p = Boceto()
    p.agregar_linea((0, 0), (10, 0))
    p.agregar_linea((0, 5), (10, 5))
    assert inferencias(p, (20, 2.5), 5, tipos={"interseccion"}) == []


# ---------------------------------------------------------------- ventana (BOC-45, 46, 33, 48)
def _linea_fija(lz, p1, p2):
    cid = lz.b.agregar_linea(p1, p2)
    lz.b.agregar_restriccion("fijo", [cid])
    lz.resolver()
    return cid


def test_linea_con_igual_al_hacer_clic_deja_el_largo_igual_a_la_otra(lienzo):
    lz = lienzo
    otra = _linea_fija(lz, (11, 20), (52, 20))                      # 41 de largo
    lz.set_herramienta("linea")
    _solo(lz, "igual")
    _clic(lz, 20, 50)
    _mover(lz, 49.2, 20.9)
    assert lz.inf_actual.tipo == "igual" and "Igual" in lz.inf_actual.etiqueta
    _clic(lz, 49.2, 20.9)
    nueva = lz.b.curvas[max(lz.b.curvas)]
    assert _con_restriccion(lz, "igual", nueva.id, otra)
    a, b = lz.b._extremos_linea(nueva.id)
    assert math.dist(a, b) == pytest.approx(41, abs=1e-6) and lz.resultado.ok


def test_circulo_con_igual_deja_el_mismo_radio(lienzo):
    lz = lienzo
    cid = lz.b.agregar_circulo((20, 20), 10)
    lz.b.agregar_restriccion("fijo", [cid])
    lz.resolver()
    lz.set_herramienta("circulo")
    _solo(lz, "igual")
    _clic(lz, 60, 20)
    _mover(lz, 70.2, 20.1)
    assert lz.inf_actual.tipo == "igual"
    _clic(lz, 70.2, 20.1)
    nuevo = lz.b.curvas[max(lz.b.curvas)]
    assert _con_restriccion(lz, "igual", nuevo.id, cid)
    assert lz.b.radio(nuevo.id) == pytest.approx(10, abs=1e-6) and lz.resultado.ok


@pytest.mark.parametrize("herramienta", ["circulo", "arco_centro"])
def test_circulo_y_arco_tangentes_a_otro_circulo(lienzo, herramienta):
    lz = lienzo
    cid = lz.b.agregar_circulo((20, 20), 10)
    lz.b.agregar_restriccion("fijo", [cid])
    lz.resolver()
    lz.set_herramienta(herramienta)
    _solo(lz, "tangente")
    _clic(lz, 60, 20)                                               # centro: el radio tangente por fuera es 30
    _mover(lz, 29.8, 20.1)
    assert lz.inf_actual.tipo == "tangente_circulo"
    _clic(lz, 29.8, 20.1)
    if herramienta == "arco_centro":
        _clic(lz, 60, 50)                                           # fin del arco
    nuevo = lz.b.curvas[max(lz.b.curvas)]
    assert _con_restriccion(lz, "tangente", nuevo.id, cid)
    assert lz.b.radio(nuevo.id) == pytest.approx(30, abs=1e-6)
    assert lz.resultado.ok
    assert math.dist(lz.b.coords(nuevo.centro), (20, 20)) == pytest.approx(40, abs=1e-6)


def test_tangente_circulo_se_apaga_con_las_restricciones_automaticas_apagadas(lienzo):
    lz = lienzo
    lz.b.agregar_circulo((20, 20), 10)
    lz.set_herramienta("circulo")
    _solo(lz, "tangente")
    lz.ajustes_inf = {**lz.ajustes_inf, "restricciones_auto": False}
    _clic(lz, 60, 20)
    _clic(lz, 29.8, 20.1)
    nuevo = lz.b.curvas[max(lz.b.curvas)]
    assert not any(nuevo.id in r.entidades for r in lz.b.restricciones.values())
    assert lz.b.radio(nuevo.id) == pytest.approx(30, abs=1e-6)       # el ajuste del cursor sí vale


def test_interseccion_aparente_en_la_ventana_no_deja_restriccion(lienzo):
    lz = lienzo
    lz.b.agregar_linea((0, 0), (10, 10))
    lz.b.agregar_linea((0, 40), (10, 30))
    antes = len(lz.b.restricciones)
    lz.set_herramienta("linea")
    _solo(lz, "interseccion")
    _mover(lz, 20.05, 19.95)
    assert lz.inf_actual.tipo == "interseccion_aparente"
    _clic(lz, 20.05, 19.95)
    _clic(lz, 30, 25)
    nueva = lz.b.curvas[max(lz.b.curvas)]
    assert lz.b.coords(nueva.p1) == pytest.approx((20, 20), abs=1e-9)
    assert len(lz.b.restricciones) == antes and lz.resultado.ok


def test_linea_de_punto_medio_paralela_a_otra(lienzo):
    lz = lienzo
    otra = _linea_fija(lz, (10, 10), (50, 50))
    lz.set_herramienta("linea_medio")
    _solo(lz, "paralela")
    _clic(lz, 40, 15)
    _mover(lz, 60.3, 35.1)
    assert lz.inf_actual.tipo == "paralela"
    _clic(lz, 60.3, 35.1)
    nueva = lz.b.curvas[max(lz.b.curvas)]
    assert _con_restriccion(lz, "paralela", nueva.id, otra)
    a, b = lz.b._extremos_linea(nueva.id)
    assert ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) == pytest.approx((40, 15), abs=1e-6)
    assert (b[1] - a[1]) == pytest.approx(b[0] - a[0], abs=1e-6) and lz.resultado.ok


def test_rectangulo_3p_primer_lado_paralelo_y_el_tercer_clic_no_ofrece_paralela(lienzo):
    lz = lienzo
    otra = _linea_fija(lz, (10, 10), (50, 50))
    lz.set_herramienta("rectangulo_3p")
    _solo(lz, "paralela")
    _clic(lz, 40, 15)
    _mover(lz, 60.3, 35.1)
    assert lz.inf_actual.tipo == "paralela"
    _clic(lz, 60.3, 35.1)
    _mover(lz, 50, 45)
    assert lz.inf_actual is None or lz.inf_actual.tipo != "paralela"      # el tercer clic fija la altura, no una dirección
    _clic(lz, 50, 45)
    lados = [c for c in lz.b.curvas.values() if c.id != otra]
    assert len(lados) == 4 and _con_restriccion(lz, "paralela", lados[0].id, otra)
    assert lz.resultado.ok


def test_rectangulo_normal_sigue_sin_paralela(lienzo):
    lz = lienzo
    _linea_fija(lz, (60, 40), (100, 70))
    lz.set_herramienta("rectangulo")
    _solo(lz, "paralela", "igual")
    _clic(lz, 60, 65)
    _mover(lz, 83, 82.9)
    assert lz.inf_actual is None or lz.inf_actual.tipo not in ("paralela", "igual")


# ---------------------------------------------------------------- API (infer_sketch_snap)
def _sesion_con(*lineas, circulos=()):
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "Base"})["ok"]
    for a, b in lineas:
        assert api.llamar(s, "draw_line", {"start_x": a[0], "start_y": a[1], "end_x": b[0], "end_y": b[1]})["ok"]
    for (x, y), radio in circulos:
        assert api.llamar(s, "draw_circle", {"center_x": x, "center_y": y, "radius": radio})["ok"]
    return s


def _snap(s, **args):
    from omnicad import api
    r = api.llamar(s, "infer_sketch_snap", args)
    assert r["ok"], r
    return r["result"]


def test_api_igual_aparente_y_tangente_de_circulo():
    s = _sesion_con(((0, 0), (30, 0)), circulos=[((100, 0), 10)])
    igual = _snap(s, x=30.3, y=10.2, base_x=0, base_y=10, types=["equal"])["selected"]
    assert igual["type"] == "equal" and igual["constraint"]["type"] == "equal" and igual["priority"] == 8
    assert math.dist((igual["x"], igual["y"]), (0, 10)) == pytest.approx(30, abs=1e-3)
    circ = _snap(s, x=110.1, y=0.2, base_x=140, base_y=0, types=["tangent"], radius_mode=True)["selected"]
    assert circ["type"] == "tangent_circle" and circ["constraint"]["type"] == "tangent"
    assert math.dist((circ["x"], circ["y"]), (140, 0)) == pytest.approx(30, abs=1e-3)


def test_api_cruce_aparente_y_errores_de_radius_mode():
    s = _sesion_con(((0, 0), (10, 10)), ((0, 40), (10, 30)))
    sel = _snap(s, x=20.1, y=19.9, types=["intersection"])["selected"]
    assert sel["type"] == "apparent_intersection" and sel["constraint"] is None and len(sel["guides"]) == 2
    from omnicad import api
    r = api.llamar(s, "infer_sketch_snap", {"x": 1, "y": 1, "radius_mode": True})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
