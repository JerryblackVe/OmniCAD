"""Auditoría de restricciones, fase E: escenarios combinados, sin ventana (informe final en docs/auditoria_restricciones.md).

Cada escenario arma un boceto con `Boceto` (o por la API cuando es de MCP o del timeline), resuelve y comprueba con
números. Los escenarios 15 (proyecciones) y 17 (SVG/DXF importados) ya tienen sus tests propios fuera de esta auditoría.
"""
import math
import time

import pytest

from omnicad import api
from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import grados_de_libertad, resolver

O = Boceto.ORIGEN


def _pts(b, linea):
    return [b.coords(q) for q in b.curvas[linea].extremos()]


def _largo(b, linea):
    return math.dist(*_pts(b, linea))


def _dist_recta(b, xy, linea):
    (x1, y1), (x2, y2) = _pts(b, linea)
    return abs((x2 - x1) * (y1 - xy[1]) - (x1 - xy[0]) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


def _es_rectangulo(b, lineas):
    """Lados 0 y 2 horizontales, 1 y 3 verticales."""
    for i, linea in enumerate(lineas):
        (x1, y1), (x2, y2) = _pts(b, linea)
        assert (y2 - y1 if i % 2 == 0 else x2 - x1) == pytest.approx(0, abs=1e-6)


def _al_origen(b, punto):
    b.asegurar_referencias([O])
    b.agregar_restriccion("coincidente", [punto, O])


def _esquina(b, lineas):
    return b.curvas[lineas[0]].p1


def _rect_acotado(b, x=0.0, y=0.0, ancho=40.0, alto=20.0, anclar=True):
    """Rectángulo con su esquina en el origen (o fija) y cotas de ancho y alto: GDL 0."""
    lineas = b.agregar_rectangulo((x + 3, y + 2) if anclar else (x, y), (x + ancho - 5, y + alto + 4))
    if anclar:
        _al_origen(b, _esquina(b, lineas))
    else:
        b.agregar_restriccion("fijo", [_esquina(b, lineas)])
    ca = b.agregar_cota("distancia", [lineas[0]], str(ancho))
    cb = b.agregar_cota("distancia", [lineas[1]], str(alto))
    return lineas, {ca: ancho, cb: alto}


def test_1_rectangulo_parcial_con_el_origen():
    b = Boceto()
    lineas = b.agregar_rectangulo((5, 5), (25, 15))
    _al_origen(b, _esquina(b, lineas))
    assert resolver(b).ok
    assert b.coords(_esquina(b, lineas)) == pytest.approx((0, 0), abs=1e-6)
    _es_rectangulo(b, lineas)
    assert grados_de_libertad(b) == 2                     # quedan el ancho y el alto


def test_2_rectangulo_con_cotas_y_origen_queda_en_gdl_0():
    b = Boceto()
    lineas, valores = _rect_acotado(b)
    r = resolver(b, valores)
    assert r.ok and r.gdl == 0 and grados_de_libertad(b, valores) == 0
    _es_rectangulo(b, lineas)
    assert (_largo(b, lineas[0]), _largo(b, lineas[1])) == pytest.approx((40, 20), abs=1e-6)


def test_3_triangulo_con_largo_angulo_y_coincidencias():
    b = Boceto()
    a, c = b.agregar_linea((0, 0), (28, 2)), b.agregar_linea((1, 1), (14, 22))
    d = b.agregar_linea((15, 21), (27, 3))
    b.agregar_restriccion("coincidente", [b.curvas[a].p1, b.curvas[c].p1])
    b.agregar_restriccion("coincidente", [b.curvas[c].p2, b.curvas[d].p1])
    b.agregar_restriccion("coincidente", [b.curvas[d].p2, b.curvas[a].p2])
    b.agregar_restriccion("horizontal", [a])
    k1 = b.agregar_cota("distancia", [a], "30")
    k2 = b.agregar_cota("angulo", [a, c], "60")
    k3 = b.agregar_cota("distancia", [c], "30")
    assert resolver(b, {k1: 30, k2: 60, k3: 30}).ok
    assert [_largo(b, x) for x in (a, c, d)] == pytest.approx([30, 30, 30], abs=1e-6)   # equilátero
    assert b.coords(b.curvas[c].p2) == b.coords(b.curvas[d].p1)


def test_4_circulos_concentricos_con_radios():
    b = Boceto()
    c1, c2 = b.agregar_circulo((0, 0), 5), b.agregar_circulo((3, 1), 12)
    b.agregar_restriccion("concentrica", [c1, c2])
    k1, k2 = b.agregar_cota("radio", [c1], "6"), b.agregar_cota("diametro", [c2], "20")
    assert resolver(b, {k1: 6, k2: 20}).ok
    assert b.coords(b.curvas[c1].centro) == pytest.approx(b.coords(b.curvas[c2].centro), abs=1e-6)
    assert (b.curvas[c1].radio, b.curvas[c2].radio) == pytest.approx((6, 10), abs=1e-6)


def test_5_ranura_arcos_tangentes_a_las_lineas():
    b = Boceto()
    ids = b.agregar_ranura("centro", [(0, 0), (30, 0)], 10)
    assert resolver(b).ok
    lineas = [i for i in ids if b.curvas[i].tipo == "linea" and not b.curvas[i].construccion]   # sin el eje
    arcos = [i for i in ids if b.curvas[i].tipo == "arco"]
    assert len(lineas) == 2 and len(arcos) == 2
    for arco in arcos:
        centro = b.coords(b.curvas[arco].centro)
        radio = math.dist(centro, b.coords(b.curvas[arco].inicio))
        assert radio == pytest.approx(5, abs=1e-6)
        assert math.dist(centro, b.coords(b.curvas[arco].fin)) == pytest.approx(radio, abs=1e-6)
        for linea in lineas:
            assert _dist_recta(b, centro, linea) == pytest.approx(radio, abs=1e-6)    # tangente
    extremos_lineas = {tuple(round(v, 6) for v in xy) for ln in lineas for xy in _pts(b, ln)}
    extremos_arcos = {tuple(round(v, 6) for v in b.coords(q)) for a in arcos for q in b.curvas[a].extremos()}
    assert extremos_lineas == extremos_arcos                                          # contorno cerrado


def test_6_cadena_de_lineas_con_coincidencias():
    b = Boceto()
    lineas = [b.agregar_linea((i * 10 + 0.5, i), (i * 10 + 9, i + 2)) for i in range(5)]
    for x, y in zip(lineas, lineas[1:], strict=False):
        b.agregar_restriccion("coincidente", [b.curvas[x].p2, b.curvas[y].p1])
    _al_origen(b, b.curvas[lineas[0]].p1)
    assert resolver(b).ok
    for x, y in zip(lineas, lineas[1:], strict=False):
        assert b.coords(b.curvas[x].p2) == pytest.approx(b.coords(b.curvas[y].p1), abs=1e-6)
    assert grados_de_libertad(b) == 4 * 5 - 2 * 4 - 2


def _perfil_l(b):
    """Perfil en L de 6 lados, cerrado, totalmente restringido."""
    xy = [(0, 0), (50, 0), (50, 10), (10, 10), (10, 40), (0, 40)]
    ruido = [(1, 2), (52, -1), (49, 12), (11, 8), (12, 41), (-2, 39)]
    pts = [b.agregar_punto(*p) for p in ruido]
    lineas = [b.agregar_linea(pts[i], pts[(i + 1) % 6]) for i in range(6)]
    for i, linea in enumerate(lineas):
        b.agregar_restriccion("horizontal" if i % 2 == 0 else "vertical", [linea])
    _al_origen(b, pts[0])
    valores = {}
    for linea, largo in zip(lineas[:4], (50, 10, 40, 30), strict=True):
        valores[b.agregar_cota("distancia", [linea], str(largo))] = largo
    return pts, lineas, valores, xy


def test_7_perfil_cerrado_con_varias_restricciones_gdl_0():
    b = Boceto()
    pts, _lineas, valores, xy = _perfil_l(b)
    r = resolver(b, valores)
    assert r.ok and r.gdl == 0
    assert [b.coords(p) for p in pts] == [pytest.approx(p, abs=1e-6) for p in xy]


def test_8_lo_fijo_no_se_mueve_y_lo_libre_si():
    b = Boceto()
    fija = b.agregar_linea((0, 0), (10, 3))
    b.agregar_restriccion("fijo", [fija])
    libre = b.agregar_linea((20, 20), (25, 30))
    b.agregar_restriccion("coincidente", [b.curvas[libre].p1, b.curvas[fija].p2])
    b.agregar_restriccion("perpendicular", [fija, libre])
    antes = _pts(b, fija)
    assert resolver(b).ok
    assert _pts(b, fija) == [pytest.approx(p, abs=1e-12) for p in antes]
    assert b.coords(b.curvas[libre].p1) == pytest.approx((10, 3), abs=1e-6)


def test_9_simetria_respecto_de_un_eje():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10), construccion=True)
    b.agregar_restriccion("fijo", [eje])
    c1, c2 = b.agregar_circulo((-8, 3), 2), b.agregar_circulo((7, 5), 4)
    b.agregar_restriccion("simetrica", [b.curvas[c1].centro, b.curvas[c2].centro, eje])
    b.agregar_restriccion("igual", [c1, c2])
    k = b.agregar_cota("radio", [c1], "3")
    assert resolver(b, {k: 3}).ok
    (x1, y1), (x2, y2) = b.coords(b.curvas[c1].centro), b.coords(b.curvas[c2].centro)
    assert (x1 + x2, y1 - y2) == pytest.approx((0, 0), abs=1e-6)
    assert (b.curvas[c1].radio, b.curvas[c2].radio) == pytest.approx((3, 3), abs=1e-6)


def test_10_restriccion_redundante_no_rompe_nada():
    b = Boceto()
    lineas, valores = _rect_acotado(b)
    assert resolver(b, valores).ok
    antes = {p: b.coords(p) for p in b.puntos}
    b.agregar_restriccion("horizontal", [lineas[0]])           # ya la tenía: el modelo la acepta y el GDL no baja
    r = resolver(b, valores)
    assert r.ok and r.gdl == 0
    assert {p: b.coords(p) for p in b.puntos} == {p: pytest.approx(xy, abs=1e-6) for p, xy in antes.items()}


def test_10_la_api_rechaza_la_restriccion_redundante_sin_tocar_el_boceto():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    abajo = _llamar(s, "draw_rectangle", x1=3, y1=2, x2=35, y2=24)["entities"][0]["id"]
    antes = _llamar(s, "get_sketch", sketch="B")
    r = api.llamar(s, "add_constraint", {"sketch": "B", "type": "horizontal", "entities": [abajo]})
    assert r["error_kind"] == "SKETCH_OVERCONSTRAINED"
    assert _llamar(s, "get_sketch", sketch="B") == antes


def test_11_restricciones_contradictorias_dan_ok_false_sin_corromper():
    b = Boceto()
    p, q = b.agregar_punto(0, 0), b.agregar_punto(10, 0)
    b.agregar_restriccion("fijo", [p])
    b.agregar_restriccion("fijo", [q])
    k = b.agregar_cota("distancia", [p, q], "20")
    r = resolver(b, {k: 20})
    assert not r.ok
    assert all(math.isfinite(v) for pid in b.puntos for v in b.coords(pid))
    assert (b.coords(p), b.coords(q)) == ((0, 0), (10, 0))


def test_12_borrar_una_restriccion_intermedia():
    b = Boceto()
    lineas, valores = _rect_acotado(b)
    vertical = next(rid for rid, r in b.restricciones.items() if r.tipo == "vertical" and r.entidades == [lineas[1]])
    b.eliminar(vertical)
    r = resolver(b, valores)
    assert r.ok and r.gdl == 1
    for i in (0, 2):
        (_, y1), (_, y2) = _pts(b, lineas[i])
        assert y1 == pytest.approx(y2, abs=1e-6)
    (x1, _), (x2, _) = _pts(b, lineas[3])
    assert x1 == pytest.approx(x2, abs=1e-6)
    assert (_largo(b, lineas[0]), _largo(b, lineas[1])) == pytest.approx((40, 20), abs=1e-6)


def test_13_cambiar_una_cota_despues_de_restringir():
    b = Boceto()
    lineas, valores = _rect_acotado(b)
    assert resolver(b, valores).ok
    ancho = next(k for k, c in b.cotas.items() if c.entidades == [lineas[0]])
    valores[ancho] = 55
    assert resolver(b, valores).ok
    _es_rectangulo(b, lineas)
    assert (_largo(b, lineas[0]), _largo(b, lineas[1])) == pytest.approx((55, 20), abs=1e-6)
    assert b.coords(_esquina(b, lineas)) == pytest.approx((0, 0), abs=1e-6)


def test_14_spline_con_coincidentes_en_sus_extremos():
    b = Boceto()
    a, c = b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((32, 0), (40, 0))
    s = b.agregar_spline([(12, 1), (20, 5), (30, 1)])
    ini, fin = b.curvas[s].extremos()
    b.agregar_restriccion("coincidente", [ini, b.curvas[a].p2])
    b.agregar_restriccion("coincidente", [fin, b.curvas[c].p1])
    b.agregar_restriccion("fijo", [a])
    b.agregar_restriccion("fijo", [c])
    assert resolver(b).ok
    assert b.coords(ini) == pytest.approx((10, 0), abs=1e-6)
    assert b.coords(fin) == pytest.approx((32, 0), abs=1e-6)


def test_16_guardar_y_abrir_da_el_mismo_resultado():
    b = Boceto()
    pts, _lineas, valores, xy = _perfil_l(b)
    copia = Boceto.desde_dict(b.a_dict())
    r1, r2 = resolver(b, valores), resolver(copia, valores)
    assert r1.ok and r2.ok and r1.gdl == r2.gdl == 0
    assert [copia.coords(p) for p in pts] == [pytest.approx(p, abs=1e-6) for p in xy]


def test_18_boceto_grande_resuelve_rapido():
    b = Boceto()
    valores = {}
    for i in range(200):
        _, v = _rect_acotado(b, x=(i % 20) * 50, y=(i // 20) * 30, ancho=40, alto=20, anclar=False)
        valores |= v
    inicio = time.perf_counter()
    r = resolver(b, valores)
    tiempo = time.perf_counter() - inicio
    assert r.ok and r.gdl == 0
    assert tiempo < 5, f"200 rectángulos acotados tardaron {tiempo:.2f} s"


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_19_mcp_y_boceto_dan_las_mismas_coordenadas():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    lados = [e["id"] for e in _llamar(s, "draw_rectangle", x1=3, y1=2, x2=35, y2=24)["entities"]]
    esquina = next(e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["id"] == lados[0])["points"][0]
    _llamar(s, "add_constraint", sketch="B", type="coincident", entities=[esquina, 0])
    _llamar(s, "add_dimension", sketch="B", type="distance", entities=[lados[0]], value=40)
    _llamar(s, "add_dimension", sketch="B", type="distance", entities=[lados[1]], value=20)
    por_mcp = sorted((p["x"], p["y"]) for p in _llamar(s, "get_sketch", sketch="B")["points"] if p["id"] != 0)

    b = Boceto()
    lineas = b.agregar_rectangulo((3, 2), (35, 24))
    _al_origen(b, _esquina(b, lineas))
    valores = {b.agregar_cota("distancia", [lineas[0]], "40"): 40, b.agregar_cota("distancia", [lineas[1]], "20"): 20}
    assert resolver(b, valores).ok
    por_boceto = sorted(b.coords(p) for p in b.puntos if p != O)
    assert por_mcp == [pytest.approx(xy, abs=1e-6) for xy in por_boceto]
    assert por_boceto == [pytest.approx(xy, abs=1e-6) for xy in [(0, 0), (0, 20), (40, 0), (40, 20)]]


def test_20_cambiar_la_cota_cambia_el_volumen_de_la_extrusion():
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    lados = [e["id"] for e in _llamar(s, "draw_rectangle", x1=3, y1=2, x2=35, y2=24)["entities"]]
    esquina = next(e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["id"] == lados[0])["points"][0]
    _llamar(s, "add_constraint", sketch="B", type="coincident", entities=[esquina, 0])
    d = _llamar(s, "add_dimension", sketch="B", type="distance", entities=[lados[0]], value=40)["dimension"]["id"]
    _llamar(s, "add_dimension", sketch="B", type="distance", entities=[lados[1]], value=20)
    _llamar(s, "extrude", sketch="B", profile=0, distance=10)

    def volumen():
        return next(iter(_llamar(s, "get_scene_info")["bodies"]))["volume"]

    assert volumen() == pytest.approx(40 * 20 * 10, rel=1e-6)
    _llamar(s, "edit_dimension", dimension=d, value=60)
    assert volumen() == pytest.approx(60 * 20 * 10, rel=1e-6)
    assert all(r.estado == "ok" for r in s.doc.resultados), [(r.estado, r.mensaje) for r in s.doc.resultados]


def test_b231_desfase_de_una_spline_fija_queda_totalmente_restringido():
    b = Boceto()
    s = b.agregar_spline([(0, 0), (10, 5), (20, 0), (30, 4)])
    for p in b.curvas[s].pts:
        b.agregar_restriccion("fijo", [p])
    b.desfase(s, 3)
    valores = {k: b.medir(c) for k, c in b.cotas.items()}
    assert resolver(b, valores).ok
    assert grados_de_libertad(b, valores) == 0           # antes daba 48: uno por punto de la copia


def test_b231_desfase_de_spline_sigue_a_la_madre_girada_antes_de_resolver():
    """Las fracciones guardadas no dependen de dónde quedó la copia: girar la madre 90° y resolver la deja a 3 mm."""
    from omnicad.restricciones.boceto import mas_cercano
    b = Boceto()
    s = b.agregar_spline([(0, 0), (10, 5), (20, 0), (30, 4)])
    copia, = b.desfase(s, 3)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    for p in b.curvas[s].pts:
        q = b.puntos[p]
        q.x, q.y = -q.y, q.x
        b.agregar_restriccion("fijo", [p])
    r = resolver(b, {cota.id: 3})
    assert r.ok and r.gdl == 0
    madre = b.primitivas(s)[0]
    assert [mas_cercano(madre, b.coords(p))[1] for p in b.curvas[copia].pts] == pytest.approx([3] * 48, abs=1e-6)
    assert math.dist(b.coords(b.curvas[copia].pts[0]), (0, 0)) == pytest.approx(3, abs=1e-6)


def test_b231_desfase_de_una_elipse_fija_queda_totalmente_restringido():
    b = Boceto()
    e = b.agregar_elipse((20, 20), (30, 20), 6, ejes=False)
    b.agregar_restriccion("fijo", [e])
    (copia,), _ = b.desfasar(e, 2)                                        # lejos de los ejes: un óvalo (spline)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    r = resolver(b, {cota.id: 2})
    assert b.curvas[copia].tipo == "spline" and r.ok and r.gdl == 0
