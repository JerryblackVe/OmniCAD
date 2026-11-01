"""Desfase del boceto: elegir un perfil (BOC-70), la elipse que da otra elipse (BOC-71) y la restricción de desfase de
las curvas libres, que sobrevive a su cota (BOC-72)."""
import json
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from test_boceto_fase5_ui import _clic, _mover  # noqa: E402
from test_boceto_fase5_ui import lienzo as lienzo  # noqa: E402,F401

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto, grados_de_libertad, resolver  # noqa: E402
from omnicad.restricciones.boceto import dominio, evaluar_primitiva, mas_cercano  # noqa: E402


def _caja(b, ids):
    xs, ys = [], []
    for k in ids:
        for prim in b.primitivas(k):
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                t0, t1, _ = dominio(prim)
                x, y = evaluar_primitiva(prim, t0 + t * (t1 - t0))[0]
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _cuadrado(b, x0=0, y0=0, lado=40):
    pts = [b.agregar_punto(x0, y0), b.agregar_punto(x0 + lado, y0), b.agregar_punto(x0 + lado, y0 + lado),
           b.agregar_punto(x0, y0 + lado)]
    return [b.agregar_linea(pts[i], pts[(i + 1) % 4]) for i in range(4)]       # puntos compartidos: una cadena cerrada


# ---------------------------------------------------------------- BOC-70: un perfil entero
def test_desfasar_perfil_crece_afuera_y_achica_el_hueco():
    b = Boceto()
    lados = _cuadrado(b)
    hueco = b.agregar_circulo((20, 20), 8)
    nuevos, _ = b.desfasar_perfil(frozenset(lados + [hueco]), 3)
    cuadrado_nuevo = [k for k in nuevos if b.curvas[k].tipo == "linea"]
    assert len(cuadrado_nuevo) == 4 and _caja(b, cuadrado_nuevo) == pytest.approx((-3, -3, 43, 43), abs=1e-6)
    (circulo,) = [k for k in nuevos if b.curvas[k].tipo == "circulo"]
    assert b.radio(circulo) == pytest.approx(5, abs=1e-9)                # la región crece: el hueco se achica
    assert len([k for k in b.cotas.values() if k.tipo == "desfase"]) == 2


def test_desfasar_perfil_invertir_y_signo_dan_el_otro_lado():
    b = Boceto()
    lados = _cuadrado(b)
    nuevos, _ = b.desfasar_perfil(frozenset(lados), -5)
    assert _caja(b, nuevos) == pytest.approx((5, 5, 35, 35), abs=1e-6)
    c = Boceto()
    nuevos, _ = c.desfasar_perfil(frozenset(_cuadrado(c)), 5, invertir=True)
    assert _caja(c, nuevos) == pytest.approx((5, 5, 35, 35), abs=1e-6)


def test_desfasar_perfil_de_una_figura_pegada_a_otra_no_se_corta_en_la_union():
    b = Boceto()
    P = {k: b.agregar_punto(*xy) for k, xy in dict(a=(0, 0), b=(40, 0), c=(80, 0), d=(80, 40), e=(40, 40), f=(0, 40)).items()}
    izq = [b.agregar_linea(P[x], P[y]) for x, y in (("a", "b"), ("b", "e"), ("e", "f"), ("f", "a"))]
    der = [b.agregar_linea(P[x], P[y]) for x, y in (("b", "c"), ("c", "d"), ("d", "e"))]
    nuevos, _ = b.desfasar_perfil(frozenset(der + [izq[1]]), 3)          # el cuadrado derecho comparte su lado con el izquierdo
    assert len(nuevos) == 4 and _caja(b, nuevos) == pytest.approx((37, -3, 83, 43), abs=1e-6)
    assert resolver(b, {k.id: 3 for k in b.cotas.values()}).ok


def test_la_restriccion_de_desfase_libre_solo_acepta_curvas_que_el_solver_entiende():
    b = Boceto()
    spline = b.agregar_spline([(0, 0), (10, 5), (20, 0)])
    elipse = b.agregar_elipse((50, 50), (60, 50), 5, ejes=False)
    with pytest.raises(Exception, match="no aplica"):
        b.agregar_restriccion("desfase", [spline, elipse])


def test_desfasar_perfil_sin_curvas_falla_claro():
    with pytest.raises(Exception, match="no tiene contornos"):
        Boceto().desfasar_perfil(frozenset({99}), 1)


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def s():
    sesion = api.Sesion()
    _llamar(sesion, "create_sketch", name="B")
    return sesion


def test_api_offset_de_un_perfil(s):
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=40, y2=40)
    _llamar(s, "offset_sketch_curves", distance=3, profile=0)
    lineas = [e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "line"]
    xs = [v for e in lineas for v in (e["start"][0], e["end"][0])]
    assert min(xs) == pytest.approx(-3) and max(xs) == pytest.approx(43) and len(lineas) == 8


def test_api_offset_pide_entity_o_profile_y_no_las_dos(s):
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=40, y2=40)
    for args in ({"distance": 3}, {"distance": 3, "entity": 1, "profile": 0},
                 {"distance": 3, "profile": 0, "side_x": 1, "side_y": 1}):
        r = api.llamar(s, "offset_sketch_curves", args)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    r = api.llamar(s, "offset_sketch_curves", {"distance": 3, "profile": 7})
    assert not r["ok"] and r["error_kind"] == "PROFILE_NOT_FOUND"


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_ventana_clic_dentro_de_un_perfil_abre_el_desfase_y_se_acepta(lienzo):
    lz = lienzo
    lados = _cuadrado(lz.b, 10, 10, 40)
    lz.resolver()
    lz.set_herramienta("desfase")
    _mover(lz, 30, 30)
    _clic(lz, 30, 30)                                                # adentro del cuadrado, lejos de cualquier curva
    assert lz._desfase_perfil == frozenset(lados) and lz.entrada is not None
    assert set(lz.seleccion) == set(lados)
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, "4")
    polis, nota, error = lz._previa_desfase()
    assert not error and nota == "Hacia afuera"
    xs = [q[0] for poli in polis for q in poli]
    assert min(xs) == pytest.approx(6, abs=1e-6) and max(xs) == pytest.approx(54, abs=1e-6)
    QTest.keyClick(campo, Qt.Key_Return)
    nuevas = [k for k in lz.b.curvas if k not in lados]
    assert len(nuevas) == 4 and _caja(lz.b, nuevas) == pytest.approx((6, 6, 54, 54), abs=1e-6)
    assert lz.entrada is None and lz.resultado.ok


def test_ventana_clic_sobre_una_curva_sigue_siendo_la_cadena_y_el_vacio_no_hace_nada(lienzo):
    lz = lienzo
    lados = _cuadrado(lz.b, 10, 10, 40)
    lz.resolver()
    lz.set_herramienta("desfase")
    _clic(lz, 70, 70)                                                # afuera del perfil
    assert lz.entrada is None and not lz.picks
    _clic(lz, 30, 10)                                                # sobre el borde: la curva, no el perfil
    assert lz.picks == [lados[0]] and lz._desfase_perfil is None
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    assert lz.entrada is None and len(lz.b.curvas) == 4


# ---------------------------------------------------------------- BOC-71: elipse real u óvalo
def _elipse_fija():
    b = Boceto()
    e = b.agregar_elipse((20, 20), (30, 20), 6, ejes=False)           # a = 10, b = 6
    b.agregar_restriccion("fijo", [e])
    return b, e


@pytest.mark.parametrize("d,a,bb", [(2, 12, 8), (-2, 8, 4)])
def test_desfase_de_elipse_da_otra_elipse_con_los_semiejes_a_mas_menos_d(d, a, bb):
    b, e = _elipse_fija()
    (nueva,), _ = b.desfasar(e, d, elipse=True)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    r = resolver(b, {cota.id: abs(d)})
    assert r.ok and r.gdl == 0
    n = b.curvas[nueva]
    assert math.dist(b.coords(n.centro), b.coords(n.mayor)) == pytest.approx(a, abs=1e-6)
    assert n.radio_menor == pytest.approx(bb, abs=1e-6) and n.centro == b.curvas[e].centro
    assert b.separacion(e, nueva) == pytest.approx(2, abs=1e-6)


def test_elipse_lejos_de_los_ejes_sigue_siendo_un_ovalo_a_distancia_constante():
    b, e = _elipse_fija()
    (nueva,), _ = b.desfasar(e, 2)
    assert b.curvas[nueva].tipo == "spline"
    distancias = [mas_cercano(b.primitivas(e)[0], b.coords(p))[1] for p in b.curvas[nueva].pts]
    assert distancias == pytest.approx([2] * len(distancias), abs=0.05)


def test_elipse_desfasada_sigue_a_la_madre_girada_y_la_distancia_se_libera_sin_la_cota():
    b = Boceto()
    e = b.agregar_elipse((20, 20), (30, 20), 6, ejes=False)
    (nueva,), _ = b.desfasar(e, 2, elipse=True)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    mayor = b.curvas[e].mayor
    b.puntos[mayor].x, b.puntos[mayor].y = 20, 32                       # la madre gira 90° y crece (a = 12)
    b.agregar_restriccion("fijo", [e])
    assert resolver(b, {cota.id: 2}).ok
    n = b.curvas[nueva]
    cx, cy = b.coords(n.centro)
    mx, my = b.coords(n.mayor)
    assert (mx - cx, my - cy) == pytest.approx((0, 14), abs=1e-5)       # sigue el giro y la medida (12 + 2)
    b.eliminar(cota.id)                                                  # BOC-72: la relación queda, la distancia es libre
    b.curvas[e].radio_menor = 9
    r = resolver(b, {})
    assert r.ok
    a2 = math.dist(b.coords(n.centro), b.coords(n.mayor))
    assert a2 - 12 == pytest.approx(n.radio_menor - 9, abs=1e-5)         # la misma distancia en los dos semiejes


def test_api_offset_de_elipse_con_ellipse_result(s):
    _llamar(s, "draw_ellipse", major_radius=10, minor_radius=6, center_x=20, center_y=20)
    ent = [e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "ellipse"][0]["id"]
    _llamar(s, "offset_sketch_curves", entity=ent, distance=2, ellipse_result="ellipse")
    elipses = [e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "ellipse"]
    assert len(elipses) == 2 and sorted(round(e["major_radius"], 4) for e in elipses) == [10, 12]
    r = api.llamar(s, "offset_sketch_curves", {"entity": ent, "distance": 1, "ellipse_result": "banana"})
    assert not r["ok"]
    _llamar(s, "draw_circle", radius=5, center_x=80, center_y=0)
    circulo = [e for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "circle"][0]["id"]
    r = api.llamar(s, "offset_sketch_curves", {"entity": circulo, "distance": 1, "ellipse_result": "ellipse"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_ventana_elipse_cerca_del_eje_da_elipse_y_lejos_un_ovalo(lienzo):
    lz = lienzo
    e = lz.b.agregar_elipse((30, 30), (50, 30), 12, ejes=False)         # a = 20, b = 12
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.agregar_pick(e, (50, 30.2))                                        # el vértice del eje mayor
    assert lz._desfase_elipse and "Elipse" in lz._previa_desfase()[1]
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    lz.set_herramienta("desfase")
    lz.agregar_pick(e, (30 + 20 * math.cos(math.radians(45)), 30 + 12 * math.sin(math.radians(45))))
    assert not lz._desfase_elipse and "Óvalo" in lz._previa_desfase()[1]
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)


def test_ventana_aceptar_elipse_cerca_del_eje_crea_una_elipse(lienzo):
    lz = lienzo
    e = lz.b.agregar_elipse((30, 30), (50, 30), 12, ejes=False)
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.agregar_pick(e, (50, 30.2))
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, "3")
    QTest.keyClick(campo, Qt.Key_Return)
    elipses = [c for c in lz.b.curvas.values() if c.tipo == "elipse"]
    assert len(elipses) == 2 and lz.resultado.ok
    nueva = max(elipses, key=lambda c: c.id)
    assert nueva.radio_menor == pytest.approx(15, abs=1e-5)


# ---------------------------------------------------------------- BOC-72: la relación sobrevive a la cota
def _spline_con_desfase():
    b = Boceto()
    madre = b.agregar_spline([(10, 10), (20, 16), (30, 16), (40, 10)])
    b.agregar_restriccion("fijo", [madre])
    (copia,), _ = b.desfasar(madre, 1.5)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    return b, madre, copia, cota


def _distancias(b, madre, copia):
    prim = b.primitivas(madre)[0]
    return [mas_cercano(prim, b.coords(p))[1] for p in b.curvas[copia].pts]


def test_spline_desfasada_deja_restriccion_de_desfase_ademas_de_la_cota():
    b, madre, copia, cota = _spline_con_desfase()
    (r,) = [r for r in b.restricciones.values() if r.tipo == "desfase"]
    assert r.entidades == [madre, copia] and r.datos["grupo"] == r.id and cota.entidades == [madre, copia]
    gdl_con = grados_de_libertad(b, {cota.id: 1.5})
    assert resolver(b, {cota.id: 1.5}).ok and gdl_con == grados_de_libertad(b, {cota.id: 1.5})


def test_borrar_la_cota_de_la_spline_conserva_la_relacion_y_libera_la_distancia():
    b, madre, copia, cota = _spline_con_desfase()
    con_cota = grados_de_libertad(b, {cota.id: 1.5})
    b.eliminar(cota.id)
    assert grados_de_libertad(b, {}) == con_cota + 1                      # una sola incógnita: la distancia
    b.puntos[b.curvas[madre].pts[1]].y += 4                              # la madre se deforma
    b.eliminar(next(r.id for r in b.restricciones.values() if r.tipo == "fijo"))
    b.agregar_restriccion("fijo", [madre])
    assert resolver(b, {}).ok
    d = _distancias(b, madre, copia)
    assert d == pytest.approx([d[0]] * len(d), abs=1e-3) and d[0] > 0.1   # sigue a la madre a una distancia común


def test_la_restriccion_viaja_en_el_archivo_y_soltar_desfase_la_quita():
    b, madre, copia, cota = _spline_con_desfase()
    b2 = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))
    assert [r.entidades for r in b2.restricciones.values() if r.tipo == "desfase"] == [[madre, copia]]
    b2.eliminar(cota.id)
    b2.soltar_desfase(copia)
    assert not [r for r in b2.restricciones.values() if r.tipo == "desfase"] and not b2.cotas


def test_un_documento_viejo_con_solo_la_cota_se_resuelve_como_antes():
    b, madre, copia, cota = _spline_con_desfase()
    for r in [r for r in b.restricciones.values() if r.tipo == "desfase"]:
        b.eliminar(r.id)                                                   # así se guardaban: solo la cota
    b.puntos[b.curvas[madre].pts[1]].y += 3
    b.eliminar(next(r.id for r in b.restricciones.values() if r.tipo == "fijo"))
    b.agregar_restriccion("fijo", [madre])
    assert resolver(b, {cota.id: 1.5}).ok
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
