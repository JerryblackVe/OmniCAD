"""Matriz de la auditoría de restricciones (fase A): cada restricción y cota del boceto 2D, sin ventana.

Por caso: (a) la relación se cumple con números después de resolver; (b) `desde_dict(a_dict())` la conserva y vuelve a
resolver igual; (c) `grados_de_libertad` baja lo que quita la ecuación. Inventario: docs/auditorias/restricciones_inventario_2026-11-06.md.
"""
import math

import pytest

from omnicad.restricciones.boceto import TIPOS_COTA, TIPOS_RESTRICCION, Boceto, ErrorBoceto, validar_valor_cota
from omnicad.restricciones.solver import grados_de_libertad, resolver


def _largo(b, linea):
    return math.dist(*(b.coords(q) for q in b.curvas[linea].extremos()))


def _dir(b, linea):
    (x1, y1), (x2, y2) = (b.coords(q) for q in b.curvas[linea].extremos())
    n = math.hypot(x2 - x1, y2 - y1)
    return (x2 - x1) / n, (y2 - y1) / n


def _cruz(b, l1, l2):
    (a, c), (d, e) = _dir(b, l1), _dir(b, l2)
    return a * e - c * d


def _dist_punto_recta(b, p, linea):
    return _dist_xy_recta(b, b.coords(p), linea)


def _dist_xy_recta(b, xy, linea):
    (x1, y1), (x2, y2) = (b.coords(q) for q in b.curvas[linea].extremos())
    x, y = xy
    return abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


def _simetria(b, p, q, eje):
    """Cero si q es el reflejo de p respecto del eje (que también se mueve): el medio cae en el eje y p→q es normal a él."""
    (x1, y1), (x2, y2) = b.coords(p), b.coords(q)
    dx, dy = _dir(b, eje)
    return _dist_xy_recta(b, ((x1 + x2) / 2, (y1 + y2) / 2), eje) + abs((x2 - x1) * dx + (y2 - y1) * dy)


def _radio(b, c):
    return b.curvas[c].radio


def _centro(b, c):
    return b.coords(b.curvas[c].centro)


# Cada caso: armar(b, con) -> (ids, valores_cotas) y medir(b, ids) -> (medido, esperado); `quita` = GDL que saca.
def _coincidente_pp(b, con):
    p, q = b.agregar_punto(0, 0), b.agregar_punto(10, 5)
    if con:
        b.agregar_restriccion("coincidente", [p, q])
    return (p, q), {}


def _coincidente_pl(b, con):
    p, ln = b.agregar_punto(5, 5), b.agregar_linea((0, 0), (10, 0))
    if con:
        b.agregar_restriccion("coincidente", [p, ln])
    return (p, ln), {}


def _coincidente_pc(b, con):
    p, c = b.agregar_punto(15, 0), b.agregar_circulo((0, 0), 10)
    if con:
        b.agregar_restriccion("coincidente", [p, c])
    return (p, c), {}


def _una_linea(tipo):
    def armar(b, con):
        ln = b.agregar_linea((0, 0), (10, 3))
        if con:
            b.agregar_restriccion(tipo, [ln])
        return (ln,), {}
    return armar


def _dos_lineas(tipo):
    def armar(b, con):
        l1, l2 = b.agregar_linea((0, 0), (10, 1)), b.agregar_linea((0, 5), (8, 9))
        if con:
            b.agregar_restriccion(tipo, [l1, l2])
        return (l1, l2), {}
    return armar


def _horizontal_pp(b, con):
    p, q = b.agregar_punto(0, 0), b.agregar_punto(10, 3)
    if con:
        b.agregar_restriccion("horizontal", [p, q])
    return (p, q), {}


def _igual_circulos(b, con):
    c1, c2 = b.agregar_circulo((0, 0), 5), b.agregar_circulo((20, 0), 8)
    if con:
        b.agregar_restriccion("igual", [c1, c2])
    return (c1, c2), {}


def _tangente_lc(b, con):
    ln, c = b.agregar_linea((0, 0), (10, 0)), b.agregar_circulo((5, 5), 3)
    if con:
        b.agregar_restriccion("tangente", [ln, c])
    return (ln, c), {}


def _concentrica(b, con):
    c1, c2 = b.agregar_circulo((0, 0), 5), b.agregar_circulo((3, 2), 8)
    if con:
        b.agregar_restriccion("concentrica", [c1, c2])
    return (c1, c2), {}


def _punto_medio(b, con):
    p, ln = b.agregar_punto(3, 4), b.agregar_linea((0, 0), (10, 0))
    if con:
        b.agregar_restriccion("punto_medio", [p, ln])
    return (p, ln), {}


def _fijo_linea(b, con):
    ln = b.agregar_linea((0, 0), (10, 3))
    if con:
        b.agregar_restriccion("fijo", [ln])
    return (ln,), {}


def _simetrica_pp(b, con):
    p, q, eje = b.agregar_punto(1, 3), b.agregar_punto(6, 5), b.agregar_linea((0, 0), (0, 10))
    if con:
        b.agregar_restriccion("simetrica", [p, q, eje])
    return (p, q, eje), {}


def _curvatura(b, con):
    fin = b.agregar_punto(10, 5)
    sp = b.agregar_spline([(0, 0), (5, 2), fin])
    ar = b.agregar_arco_centro((20, 5), fin, (20, 15))
    if con:
        b.agregar_restriccion("curvatura", [sp, ar])
    return (sp, ar), {}


def _poligono(b, con):
    ps = [b.agregar_punto(0, 0), b.agregar_punto(10, 0), b.agregar_punto(4, 7)]
    ls = [b.agregar_linea(ps[i], ps[(i + 1) % 3]) for i in range(3)]
    if con:
        b.agregar_restriccion("poligono", ls)
    return tuple(ls), {}


def _cota(tipo, valor, armar_ents, datos=None):
    def armar(b, con):
        ids = armar_ents(b)
        if not con:
            return ids, {}
        k = b.agregar_cota(tipo, list(ids), str(valor), datos)
        return ids, {k: float(valor)}
    return armar


_PP = lambda b: (b.agregar_punto(0, 0), b.agregar_punto(6, 8))          # noqa: E731
_L = lambda b: (b.agregar_linea((0, 0), (6, 8)),)                         # noqa: E731
_PL = lambda b: (b.agregar_punto(3, 4), b.agregar_linea((0, 0), (10, 0)))  # noqa: E731
_C = lambda b: (b.agregar_circulo((0, 0), 4),)                            # noqa: E731
_LL = lambda b: (b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((0, 1), (10, 5)))  # noqa: E731

CASOS = [
    ("coincidente punto-punto", _coincidente_pp, lambda b, i: (math.dist(b.coords(i[0]), b.coords(i[1])), 0), 2),
    ("coincidente punto-línea", _coincidente_pl, lambda b, i: (_dist_punto_recta(b, *i), 0), 1),
    ("coincidente punto-círculo", _coincidente_pc,
     lambda b, i: (math.dist(b.coords(i[0]), _centro(b, i[1])), _radio(b, i[1])), 1),
    ("horizontal línea", _una_linea("horizontal"), lambda b, i: (_dir(b, i[0])[1], 0), 1),
    ("horizontal dos puntos", _horizontal_pp, lambda b, i: (b.coords(i[0])[1] - b.coords(i[1])[1], 0), 1),
    ("vertical línea", _una_linea("vertical"), lambda b, i: (_dir(b, i[0])[0], 0), 1),
    ("paralela", _dos_lineas("paralela"), lambda b, i: (_cruz(b, *i), 0), 1),
    ("perpendicular", _dos_lineas("perpendicular"),
     lambda b, i: (sum(a * c for a, c in zip(_dir(b, i[0]), _dir(b, i[1]), strict=True)), 0), 1),
    ("igual líneas", _dos_lineas("igual"), lambda b, i: (_largo(b, i[0]) - _largo(b, i[1]), 0), 1),
    ("igual círculos", _igual_circulos, lambda b, i: (_radio(b, i[0]) - _radio(b, i[1]), 0), 1),
    ("tangente línea-círculo", _tangente_lc, lambda b, i: (_dist_punto_recta(b, b.curvas[i[1]].centro, i[0]),
                                                           _radio(b, i[1])), 1),
    ("concéntrica", _concentrica, lambda b, i: (math.dist(_centro(b, i[0]), _centro(b, i[1])), 0), 2),
    ("punto medio", _punto_medio, lambda b, i: (math.dist(b.coords(i[0]), tuple(
        (b.coords(b.curvas[i[1]].p1)[k] + b.coords(b.curvas[i[1]].p2)[k]) / 2 for k in (0, 1))), 0), 2),
    ("fijo línea", _fijo_linea, lambda b, i: (_largo(b, i[0]), math.hypot(10, 3)), 4),
    ("colineal", _dos_lineas("colineal"), lambda b, i: (abs(_cruz(b, *i)) + _dist_punto_recta(
        b, b.curvas[i[1]].p1, i[0]), 0), 2),
    ("simetría de dos puntos", _simetrica_pp, lambda b, i: (_simetria(b, *i), 0), 2),
    ("curvatura spline-arco", _curvatura, lambda b, i: (0, 0), 2),     # solo GDL y persistencia: la G2 la mide fase7
    ("polígono regular", _poligono, lambda b, i: (max(_largo(b, x) for x in i) - min(_largo(b, x) for x in i), 0), 2),
    ("cota distancia punto-punto", _cota("distancia", 10, _PP), lambda b, i: (math.dist(*map(b.coords, i)), 10), 1),
    ("cota largo de línea", _cota("distancia", 10, _L), lambda b, i: (_largo(b, i[0]), 10), 1),
    ("cota distancia punto-línea", _cota("distancia", 7, _PL), lambda b, i: (_dist_punto_recta(b, *i), 7), 1),
    ("cota distancia horizontal", _cota("distancia_h", 10, _PP),
     lambda b, i: (abs(b.coords(i[1])[0] - b.coords(i[0])[0]), 10), 1),
    ("cota distancia vertical", _cota("distancia_v", 10, _PP),
     lambda b, i: (abs(b.coords(i[1])[1] - b.coords(i[0])[1]), 10), 1),
    ("cota radio", _cota("radio", 10, _C), lambda b, i: (_radio(b, i[0]), 10), 1),
    ("cota diámetro", _cota("diametro", 10, _C), lambda b, i: (2 * _radio(b, i[0]), 10), 1),
    ("cota ángulo", _cota("angulo", 60, _LL), lambda b, i: (math.degrees(math.acos(abs(sum(
        a * c for a, c in zip(_dir(b, i[0]), _dir(b, i[1]), strict=True))))), 60), 1),
]


@pytest.mark.parametrize(("nombre", "armar", "medir", "quita"), CASOS, ids=[c[0] for c in CASOS])
def test_restriccion_se_cumple_persiste_y_quita_gdl(nombre, armar, medir, quita):
    libre = Boceto()
    armar(libre, False)
    b = Boceto()
    ids, valores = armar(b, True)
    assert grados_de_libertad(libre) - grados_de_libertad(b, valores) == quita
    assert resolver(b, valores).ok
    medido, esperado = medir(b, ids)
    assert medido == pytest.approx(esperado, abs=1e-6)
    copia = Boceto.desde_dict(b.a_dict())
    assert [r.a_dict() for r in copia.restricciones.values()] == [r.a_dict() for r in b.restricciones.values()]
    assert resolver(copia, valores).ok
    for pid in b.puntos:
        assert copia.coords(pid) == pytest.approx(b.coords(pid), abs=1e-9)


def test_la_matriz_cubre_cada_tipo():
    """Si se suma un tipo de restricción o cota, tiene que entrar a la matriz (o a la lista de excluidos con su razón)."""
    cubiertos = {n.split()[0] for n, *_ in CASOS}
    nombres = {"coincidente", "horizontal", "vertical", "paralela", "perpendicular", "igual", "tangente", "concéntrica",
               "punto", "fijo", "colineal", "simetría", "curvatura", "polígono", "cota"}
    assert nombres <= cubiertos
    # desfase y patrón se prueban con sus herramientas (tests/test_boceto_fase9_desfase.py, patrones); no son de a pares
    assert set(TIPOS_RESTRICCION) - {"desfase", "patron"} == {
        "coincidente", "horizontal", "vertical", "paralela", "perpendicular", "igual", "tangente", "concentrica",
        "punto_medio", "fijo", "colineal", "simetrica", "curvatura", "poligono"}
    assert set(TIPOS_COTA) == {"distancia", "distancia_h", "distancia_v", "radio", "diametro", "angulo", "desfase"}


def _rectangulo_con_diagonal():
    """Caso del video de B-223: rectángulo de 2 puntos (−120,0)–(−55,50) y su diagonal de construcción."""
    b = Boceto()
    lineas = b.agregar_rectangulo((-120, 0), (-55, 50))
    esquinas = [b.curvas[ln].p1 for ln in lineas]
    diagonal = b.agregar_linea(esquinas[0], esquinas[2], construccion=True)
    b.asegurar_referencias([Boceto.ORIGEN])
    return b, esquinas, diagonal


@pytest.mark.parametrize("linea_primero", [True, False])
def test_b224_punto_medio_acepta_cualquier_orden(linea_primero):
    b, esquinas, diagonal = _rectangulo_con_diagonal()
    pedido = [diagonal, Boceto.ORIGEN] if linea_primero else [Boceto.ORIGEN, diagonal]
    rid = b.agregar_restriccion("punto_medio", pedido)
    assert b.restricciones[rid].entidades == [Boceto.ORIGEN, diagonal]       # se guarda en el orden de siempre
    assert resolver(b).ok
    assert b.coords(esquinas[0]) == pytest.approx((-32.5, -25.0), abs=1e-6)
    assert b.coords(esquinas[2]) == pytest.approx((32.5, 25.0), abs=1e-6)


@pytest.mark.parametrize("curva_primero", [True, False])
def test_b224_coincidente_acepta_curva_y_punto_en_cualquier_orden(curva_primero):
    b = Boceto()
    c, p = b.agregar_circulo((0, 0), 10), b.agregar_punto(30, 0)
    b.agregar_restriccion("coincidente", [c, p] if curva_primero else [p, c])
    assert resolver(b).ok
    assert math.dist(b.coords(p), _centro(b, c)) == pytest.approx(_radio(b, c), abs=1e-6)


def test_b224_tangente_guarda_la_linea_primero():
    b = Boceto()
    ln, c = b.agregar_linea((0, 0), (10, 0)), b.agregar_circulo((5, 5), 3)
    rid = b.agregar_restriccion("tangente", [c, ln])
    assert b.restricciones[rid].entidades == [ln, c]


def test_b224_el_mcp_acepta_la_curva_primero():
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "P"})["ok"]
    ln = api.llamar(s, "draw_line", {"sketch": "P", "start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0})["result"]
    p = api.llamar(s, "draw_point", {"sketch": "P", "x": 3, "y": 4})["result"]
    r = api.llamar(s, "add_constraint", {"sketch": "P", "type": "midpoint",
                                         "entities": [ln["entities"][0]["id"], p["points"][0]]})
    assert r["ok"], r


def test_b225_origen_sobre_la_diagonal_no_deforma_el_rectangulo():
    b, esquinas, diagonal = _rectangulo_con_diagonal()
    b.agregar_restriccion("coincidente", [Boceto.ORIGEN, diagonal])
    assert resolver(b).ok
    assert _dist_punto_recta(b, Boceto.ORIGEN, diagonal) < 1e-6
    (x0, y0), (x2, y2) = b.coords(esquinas[0]), b.coords(esquinas[2])
    assert (x2 - x0, y2 - y0) == pytest.approx((65.0, 50.0), abs=1.0)    # se corre: no cambia de tamaño ni se da vuelta


def test_b226_origen_con_la_esquina_opuesta_resuelve():
    b, esquinas, _ = _rectangulo_con_diagonal()
    b.agregar_restriccion("coincidente", [Boceto.ORIGEN, esquinas[2]])
    assert resolver(b).ok
    assert b.coords(esquinas[2]) == pytest.approx((0.0, 0.0), abs=1e-6)
    (x0, y0), (x2, y2) = b.coords(esquinas[0]), b.coords(esquinas[2])
    assert x2 - x0 > 1e-6 and y2 - y0 > 1e-6


def test_coincidente_con_otro_punto_fijo_conserva_una_linea_oblicua(monkeypatch):
    """Ni origen ni rectángulo; miles de curvas sueltas no entran a la búsqueda alternativa."""
    import scipy.optimize
    b = Boceto()
    linea = b.agregar_linea((-120, 0), (-55, 50))
    a, c = b.curvas[linea].p1, b.curvas[linea].p2
    fijo = b.agregar_punto(-120, 0)
    b.agregar_restriccion("fijo", [fijo])
    direccion = b.agregar_linea((100, 100), (165, 150))
    b.agregar_restriccion("fijo", [direccion])
    b.agregar_restriccion("paralela", [linea, direccion])
    b.agregar_restriccion("coincidente", [c, fijo])
    for i in range(3000):
        b.agregar_linea((i, 100), (i + 1, 101))
    numerico, tamanos = scipy.optimize.least_squares, []

    def contar(fun, inicio, **opciones):
        tamanos.append(len(inicio))
        return numerico(fun, inicio, **opciones)

    monkeypatch.setattr(scipy.optimize, "least_squares", contar)
    assert resolver(b).ok
    assert b.coords(c) == pytest.approx((-120, 0), abs=1e-6)
    assert b.coords(a) == pytest.approx((-185, -50), abs=1e-6)
    assert tamanos == [4, 4, 2]  # dos corridas normales y una traslación, independientemente de las 3000 curvas


@pytest.mark.parametrize("caso", ["esquina fija", "fusion", "coincidencias incompatibles"])
def test_la_alternativa_no_oculta_un_conflicto_real(caso):
    b, esquinas, _ = _rectangulo_con_diagonal()
    b.agregar_restriccion("coincidente", [Boceto.ORIGEN, esquinas[2]])
    if caso == "esquina fija":
        b.agregar_restriccion("fijo", [esquinas[0]])
    elif caso == "fusion":
        # La altura cero exige el colapso: trasladar la figura no lo puede resolver.
        b.agregar_restriccion("horizontal", [esquinas[0], esquinas[2]])
    else:
        for y in (-10, 10):
            fijo = b.agregar_punto(0, y)
            b.agregar_restriccion("fijo", [fijo])
            b.agregar_restriccion("coincidente", [esquinas[2], fijo])
    assert not resolver(b).ok


@pytest.mark.parametrize("valor", [200, -30, float("nan"), float("inf"), -float("inf"), 0, 180])
def test_b227_cota_de_angulo_fuera_de_rango_se_rechaza_en_el_modelo(valor):
    b = Boceto()
    lineas = list(_LL(b))
    antes = b.a_dict()
    mensaje = "La cota de ángulo tiene que estar entre 0 y 180 grados"
    with pytest.raises(ErrorBoceto, match=mensaje):
        b.agregar_cota("angulo", lineas, str(valor))
    assert b.a_dict() == antes
    with pytest.raises(ErrorBoceto, match=mensaje):
        validar_valor_cota("angulo", valor)  # también el valor evaluado al recalcular una expresión
    cid = b.agregar_cota("angulo", lineas, "60")
    assert resolver(b, {cid: 60.0}).ok
    assert b.medir(b.cotas[cid]) == pytest.approx(60, abs=1e-6)


@pytest.mark.parametrize("editar", [False, True], ids=["crear", "editar"])
@pytest.mark.parametrize("texto", ["200", "-30", "0", "180"])
def test_b227_la_ventana_rechaza_el_angulo_fuera_de_rango(editar, texto):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    app = QApplication.instance() or QApplication([])
    b = Boceto()
    lineas = list(_LL(b))
    lienzo = Lienzo(b, TablaParametros().evaluar)
    mensajes = []
    lienzo.mensaje.connect(mensajes.append)
    try:
        if editar:
            cid = b.agregar_cota("angulo", lineas, "60")
            lienzo.resolver()
            lienzo.editar_cota(cid, QPoint(100, 100))
        else:
            lienzo._abrir_cota("angulo", lineas, QPoint(100, 100))
        antes = b.a_dict()
        pasos = len(lienzo.historial)
        campo = lienzo.entrada.campos[0]
        campo.selectAll()
        QTest.keyClicks(campo, texto)
        QTest.keyClick(campo, Qt.Key_Return)
        assert mensajes and "entre 0 y 180 grados" in mensajes[-1]
        assert lienzo.entrada is not None
        assert b.a_dict() == antes and len(lienzo.historial) == pasos
        campo.selectAll()
        QTest.keyClicks(campo, "60")
        QTest.keyClick(campo, Qt.Key_Return)
        assert lienzo.entrada is None and lienzo.resultado.ok
        cota = next(iter(b.cotas.values()))
        assert not cota.referencia and b.medir(cota) == pytest.approx(60, abs=1e-6)
    finally:
        lienzo.close()
        lienzo.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("texto", ["200", "-30", "0", "180", "100 + 100"])
def test_b227_la_api_usa_el_mismo_error_del_modelo(texto):
    from omnicad import api

    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "P"})["ok"]
    lineas = []
    for y in (0, 5):
        r = api.llamar(s, "draw_line", {"sketch": "P", "start_x": 0, "start_y": y,
                                        "end_x": 10, "end_y": y + 3})
        assert r["ok"], r
        lineas.append(r["result"]["entities"][0]["id"])
    antes = api.llamar(s, "get_sketch", {"sketch": "P"})["result"]
    r = api.llamar(s, "add_dimension", {"sketch": "P", "type": "angle", "entities": lineas, "value": texto})
    assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r
    assert "La cota de ángulo tiene que estar entre 0 y 180 grados" in r["mensaje"]
    assert api.llamar(s, "get_sketch", {"sketch": "P"})["result"] == antes


@pytest.mark.parametrize("canal", ["modelo", "mcp"])
@pytest.mark.parametrize("referencia", [False, True])
@pytest.mark.parametrize("desnivel", [10, 2e-5], ids=["oblicuas", "fuera_de_tolerancia"])
def test_b228_distancia_entre_lineas_no_paralelas_se_rechaza(canal, referencia, desnivel):
    mensaje = "Usá una cota de ángulo"
    if canal == "modelo":
        b = Boceto()
        l1 = b.agregar_linea((0, 0), (10, 0))
        l2 = b.agregar_linea((0, 5), (10, 5 + desnivel))
        antes = b.a_dict()
        with pytest.raises(ErrorBoceto, match=mensaje):
            b.agregar_cota("distancia", [l1, l2], "7", referencia=referencia)
        assert b.a_dict() == antes
    else:
        from omnicad import api

        s = api.Sesion()
        assert api.llamar(s, "create_sketch", {"name": "P"})["ok"]
        lineas = []
        for y, dy in ((0, 0), (5, desnivel)):
            r = api.llamar(s, "draw_line", {"sketch": "P", "start_x": 0, "start_y": y,
                                            "end_x": 10, "end_y": y + dy})
            assert r["ok"], r
            lineas.append(r["result"]["entities"][0]["id"])
        antes = s.doc.a_dict()
        r = api.llamar(s, "add_dimension", {"sketch": "P", "type": "distance", "entities": lineas,
                                            "value": "7", "reference": referencia})
        assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r
        assert mensaje in r["mensaje"]
        assert s.doc.a_dict() == antes


@pytest.mark.parametrize("extremos", [((0, 5), (10, 5)), ((10, 5), (0, 5)), ((0, 5), (10, 5 + 5e-6))],
                         ids=["paralelas", "sentidos_opuestos", "dentro_de_tolerancia"])
def test_b228_distancia_entre_paralelas_sigue_andando(extremos):
    b = Boceto()
    l1, l2 = b.agregar_linea((0, 0), (10, 0)), b.agregar_linea(*extremos)
    b.agregar_restriccion("fijo", [l1])
    b.agregar_restriccion("paralela", [l1, l2])
    k = b.agregar_cota("distancia", [l1, l2], "7")
    assert resolver(b, {k: 7.0}).ok
    for p in b.curvas[l2].extremos():
        assert _dist_punto_recta(b, p, l1) == pytest.approx(7, abs=1e-6)


def test_b228_un_archivo_viejo_con_esa_cota_se_abre():
    b = Boceto()
    l1, l2 = b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((0, 5), (10, 5))
    k = b.agregar_cota("distancia", [l1, l2], "7")
    # La cota ya existía cuando las líneas dejaron de ser paralelas.
    b.puntos[b.curvas[l2].p2].y = 15
    datos = b.a_dict()
    copia = Boceto.desde_dict(datos)
    assert copia.a_dict() == datos
    assert copia.cotas[k].entidades == [l1, l2]
    assert resolver(copia, {k: 7.0}).ok


def test_b229_autorestringir_usa_el_origen_sin_crear_puntos():
    from omnicad.restricciones.solver import auto_restringir

    b = Boceto()
    b.agregar_rectangulo((10, 10), (40, 30))
    antes = {p: b.coords(p) for p in b.puntos}
    restricciones_antes = len(b.restricciones)
    agregado = auto_restringir(b)
    assert set(b.puntos) - antes.keys() == {Boceto.ORIGEN}
    assert not any(r.tipo == "fijo" for r in b.restricciones.values())
    posicion = [k for k in b.cotas.values() if k.tipo in ("distancia_h", "distancia_v")]
    assert {k.tipo for k in posicion} == {"distancia_h", "distancia_v"}
    assert all(Boceto.ORIGEN in k.entidades for k in posicion)
    assert len(agregado) == len(b.restricciones) - restricciones_antes + len(b.cotas)
    valores = {k.id: float(k.expresion) for k in b.cotas.values()}
    assert grados_de_libertad(b, valores) == 0
    assert resolver(b, valores).ok
    for p, xy in antes.items():
        assert b.coords(p) == pytest.approx(xy, abs=1e-6)
    copia = Boceto.desde_dict(b.a_dict())
    assert grados_de_libertad(copia, valores) == 0 and resolver(copia, valores).ok


@pytest.mark.parametrize("referencias", [[Boceto.ORIGEN], [Boceto.EJE_X, Boceto.EJE_Y]])
def test_b229_origen_materializado_no_es_un_dato(referencias):
    from omnicad.restricciones.solver import auto_restringir

    b = Boceto()
    b.agregar_rectangulo((10, 10), (40, 30))
    b.asegurar_referencias(referencias)
    assert Boceto.ORIGEN in b.puntos_fijos()
    antes = set(b.puntos)
    auto_restringir(b)
    assert set(b.puntos) == antes
    assert not any(r.tipo == "fijo" for r in b.restricciones.values())
    posicion = [k for k in b.cotas.values() if k.tipo in ("distancia_h", "distancia_v")]
    assert {k.tipo for k in posicion} == {"distancia_h", "distancia_v"}
    assert all(Boceto.ORIGEN in k.entidades for k in posicion)
    valores = {k.id: float(k.expresion) for k in b.cotas.values()}
    assert grados_de_libertad(b, valores) == 0 and resolver(b, valores).ok


def test_b229_con_un_punto_en_el_origen_lo_fija():
    from omnicad.restricciones.solver import auto_restringir

    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (40, 30))
    punto = b.curvas[lineas[0]].p1
    antes = set(b.puntos)
    agregado = auto_restringir(b)
    assert set(b.puntos) == antes
    assert [r.entidades for r in b.restricciones.values() if r.tipo == "fijo"] == [[punto]]
    assert any(s.tipo == "fijo" and s.entidades == (punto,) for s in agregado)
    valores = {k.id: float(k.expresion) for k in b.cotas.values()}
    assert grados_de_libertad(b, valores) == 0 and resolver(b, valores).ok


@pytest.mark.parametrize("limite", [0, 1, 2])
def test_b229_el_limite_no_agrega_un_fijo_oculto(limite):
    from omnicad.restricciones.solver import auto_restringir

    b = Boceto()
    b.agregar_rectangulo((10, 10), (40, 30))
    restricciones_antes = len(b.restricciones)
    agregado = auto_restringir(b, limite=limite)
    assert len(agregado) == limite == len(b.cotas)
    assert len(b.restricciones) == restricciones_antes
    assert not any(r.tipo == "fijo" for r in b.restricciones.values())


def test_b229_api_sugerir_aplicar_y_excluir_usan_el_origen():
    from omnicad import api

    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "P"})["ok"]
    assert api.llamar(s, "draw_rectangle", {"x1": 10, "y1": 10, "x2": 40, "y2": 30})["ok"]
    antes = s.doc.a_dict()
    sugerido = api.llamar(s, "suggest_auto_constraints", {})
    assert sugerido["ok"], sugerido
    assert s.doc.a_dict() == antes
    completo = sugerido["result"]["results"][0]
    assert completo["dof"] == 0
    posicion = [i for i in completo["items"] if Boceto.ORIGEN in i["entities"]]
    assert len(posicion) == 2 and all(i["kind"] == "dimension" for i in posicion)
    opciones = {"exclude": [posicion[0]], "max_items": 1}
    sugerido = api.llamar(s, "suggest_auto_constraints", opciones)
    assert sugerido["ok"] and s.doc.a_dict() == antes
    aplicado = api.llamar(s, "auto_constrain", opciones)
    assert aplicado["ok"], aplicado
    r = aplicado["result"]
    assert r["points"] == [Boceto.ORIGEN]
    assert r["items"] == sugerido["result"]["results"][0]["items"]
    assert len(r["items"]) == len(r["dimensions"]) == 1 and not r["constraints"]
    assert r["items"][0]["type"] != posicion[0]["type"] or r["items"][0]["entities"] != posicion[0]["entities"]
    aplicado = api.llamar(s, "auto_constrain", {})
    assert aplicado["ok"] and aplicado["result"]["dof"] == 0, aplicado
    assert not aplicado["result"]["points"]
