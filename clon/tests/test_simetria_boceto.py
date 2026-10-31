# -*- coding: utf-8 -*-
"""Simetría (Mirror) del boceto: el reflejo exacto sobre cualquier eje, lo que no se copia, la restricción de simetría,
el flujo del panel SIMETRÍA en el Lienzo (objetos, eje, vista previa, Aceptar / Cancelar / Enter / Esc) y el caso del
video de Fusion: A(-50, 0), B(0, 0), C(0, 70) con la vertical BC como eje da A'(50, 0)."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo.perfiles import detectar
from omnicad.restricciones import Boceto, ErrorBoceto, puntos_primitiva, resolver
from omnicad.restricciones.boceto import ArcoElipse, Texto, distancia_primitiva
from omnicad.timeline.parametros import TablaParametros

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _reflejo(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)
    return 2 * (a[0] + t * dx) - q[0], 2 * (a[1] + t * dy) - q[1]


def _es_el_reflejo(b, original, copia, a, bb, tol=1e-6):
    """La copia pasa por el reflejo de cada punto muestreado de la original (distancia a la curva exacta: no depende de
    dónde caen las muestras)."""
    prims = b.primitivas(copia)
    return all(min(distancia_primitiva(c, _reflejo(q, a, bb)) for c in prims) < tol
               for prim in b.primitivas(original) for q in puntos_primitiva(prim, 64))


def _triangulo():
    """El del video: AB, BC y CA con los extremos compartidos."""
    b = Boceto()
    pa, pb, pc = b.agregar_punto(-50, 0), b.agregar_punto(0, 0), b.agregar_punto(0, 70)
    return (b, b.agregar_linea(pa, pb), b.agregar_linea(pb, pc), b.agregar_linea(pc, pa))


# ---------------------------------------------------------------- el motor
def test_triangulo_del_video_da_el_isosceles_sin_duplicar_el_eje():
    b, ab, bc, ca = _triangulo()
    nuevos = b.simetria([ab, bc, ca], bc)              # el eje va entre los objetos, como en Fusion: se ignora
    assert len(nuevos) == 2 and len(b.curvas) == 5
    usados = {p for c in b.curvas.values() for p in c.puntos()}
    xy = sorted((round(b.puntos[p].x, 9), round(b.puntos[p].y, 9)) for p in usados)
    assert xy == [(-50, 0), (0, 0), (0, 70), (50, 0)]            # B y C se comparten, A' = (50, 0)
    assert sum(r.tipo == "simetrica" for r in b.restricciones.values()) == 1 and resolver(b, {}).ok
    assert len(detectar(b.geometria(), PLANO)) == 2               # las dos mitades, cerradas
    assert sorted(round(p.area, 6) for p in detectar(b.geometria(), PLANO)) == [1750, 1750]


TIPOS = {"línea": lambda b: b.agregar_linea((12, 7), (30, 2)),
         "círculo": lambda b: b.agregar_circulo((14, 9.5), 5),
         "arco": lambda b: b.agregar_arco_3_puntos((10, 2), (16, 9), (25, 4)),
         "elipse": lambda b: b.agregar_elipse((14, 9.5), (24, 12), 4),
         "spline de ajuste": lambda b: b.agregar_spline([(8, 2), (14, 11), (22, 4), (30, 12)], "ajuste"),
         "spline de control": lambda b: b.agregar_spline([(8, 2), (14, 11), (22, 4), (30, 12)], "control", 3),
         "cónica": lambda b: b.agregar_conica((8, 2), (20, 20), (32, 4), 0.4)}
EJES = [((0, -10), (0, 40)), ((-20, 5), (60, 5)), ((10, 5), (30, 25)), ((-15, 40), (25, -10)), ((3, 3), (3.0001, 1000))]


@pytest.mark.parametrize("a, bb", EJES)
@pytest.mark.parametrize("tipo", TIPOS)
def test_el_reflejo_de_cada_curva_es_exacto_con_ejes_verticales_horizontales_e_inclinados(tipo, a, bb):
    b = Boceto()
    eje = b.agregar_linea(a, bb, True)                       # de construcción
    cid = TIPOS[tipo](b)
    nuevo = b.simetria([cid], eje)[0]
    assert _es_el_reflejo(b, cid, nuevo, a, bb) and _es_el_reflejo(b, nuevo, cid, a, bb)
    r = resolver(b, {})
    assert r.ok and _es_el_reflejo(b, cid, nuevo, a, bb)      # el solver no lo mueve
    assert nuevo != cid and b.curvas[nuevo].construccion == b.curvas[cid].construccion


def test_la_copia_sigue_al_original_al_mover_un_punto():
    b = Boceto()
    eje = b.agregar_linea((10, 5), (30, 25), True)
    ln = b.agregar_linea((12, 7), (30, 2))
    copia = b.simetria([ln], eje)[0]
    b.agregar_restriccion("fijo", [b.curvas[eje].p1])
    b.agregar_restriccion("fijo", [b.curvas[eje].p2])
    b.puntos[b.curvas[ln].p2].x, b.puntos[b.curvas[ln].p2].y = 33.0, 4.0
    assert resolver(b, {}, arrastrado=b.curvas[ln].p2).ok
    assert _es_el_reflejo(b, ln, copia, (10, 5), (30, 25))


def test_los_arcos_invierten_el_sentido_y_siguen_siendo_antihorarios():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10), True)
    arco = b.agregar_arco_3_puntos((4, 1), (6, 3), (8, 1))
    copia = b.curvas[b.simetria([arco], eje)[0]]
    c0 = b.curvas[arco]
    assert b.coords(copia.inicio) == pytest.approx(_reflejo(b.coords(c0.fin), (0, -10), (0, 10)))      # inicio ↔ fin
    assert b.coords(copia.fin) == pytest.approx(_reflejo(b.coords(c0.inicio), (0, -10), (0, 10)))
    assert _es_el_reflejo(b, arco, copia.id, (0, -10), (0, 10)) and _es_el_reflejo(b, copia.id, arco, (0, -10), (0, 10))


@pytest.mark.parametrize("que", ["línea", "círculo", "arco", "elipse", "arco de elipse"])
def test_lo_que_ya_es_su_propio_reflejo_no_se_copia_encima(que):
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10))
    propio = {"línea": lambda: b.agregar_linea((0, 2), (0, 6)),
              "círculo": lambda: b.agregar_circulo((0, 3), 2),
              "arco": lambda: b.agregar_arco_centro((0, 0), (3, 4), (-3, 4)),      # centrado en el eje, extremos espejados
              "elipse": lambda: b.agregar_elipse((0, 3), (0, 8), 2),               # eje mayor sobre el eje
              "arco de elipse": lambda: _arco_de_elipse(b, (2, 3), (-2, 3))}[que]()   # la mitad de arriba: extremos espejados
    antes, vinculos = len(b.curvas), len(b.restricciones)
    with pytest.raises(ErrorBoceto, match="ya está sobre"):
        b.simetria([propio], eje)
    assert len(b.curvas) == antes and len(b.restricciones) == vinculos
    suelta = b.agregar_linea((2, 0), (6, 3))
    nuevos = b.simetria([propio, suelta], eje)                # mezclado con otra cosa: solo se copia la otra
    assert len(nuevos) == 1 and len(b.curvas) == antes + 2


def _arco_de_elipse(b, inicio, fin):
    """Arco antihorario de la elipse de centro (0, 3), eje mayor vertical de 5 y radio menor 2 (centrada en el eje x = 0)."""
    return b._agregar_curva(ArcoElipse(b._nuevo_id(), b._punto((0, 3)), b._punto((0, 8)), 2, b._punto(inicio), b._punto(fin)))


def test_un_arco_de_elipse_con_los_extremos_sin_espejar_si_se_copia():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10))
    cuarto = _arco_de_elipse(b, (2, 3), (0, 8))              # el cuarto de la derecha: su reflejo es el de la izquierda
    nuevos = b.simetria([cuarto], eje)
    assert len(nuevos) == 1 and isinstance(b.curvas[nuevos[0]], ArcoElipse)
    assert _es_el_reflejo(b, cuarto, nuevos[0], (0, -10), (0, 10))


def test_una_elipse_con_el_eje_mayor_oblicuo_al_eje_si_se_copia():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10))
    e = b.agregar_elipse((0, 3), (5, 8), 2)                  # centrada en el eje pero girada 45°: su reflejo es otra
    assert len(b.simetria([e], eje)) == 1


def test_un_punto_a_menos_de_un_nanometro_del_eje_se_comparte():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10))
    ln = b.agregar_linea((2e-7, 0), (5, 5))
    b.simetria([ln], eje)
    assert len(b.puntos) == 5                                 # 2 del eje, 2 de la línea y 1 reflejado (no 6)


def test_errores_claros_del_motor():
    b = Boceto()
    c = b.agregar_circulo((5, 5), 2)
    ln = b.agregar_linea((0, 0), (10, 0))
    otra = b.agregar_linea((3, 3), (4, 4))
    with pytest.raises(ErrorBoceto, match="tiene que ser una línea"):
        b.simetria([ln], c)
    with pytest.raises(ErrorBoceto, match="Seleccioná la geometría"):
        b.simetria([], ln)
    with pytest.raises(ErrorBoceto, match="Seleccioná la geometría"):
        b.simetria([ln], ln)                                   # solo el eje: no queda nada que reflejar
    cero = b.agregar_linea((20, 20), (25, 25))
    b.puntos[b.curvas[cero].p2].x = b.puntos[b.curvas[cero].p1].x
    b.puntos[b.curvas[cero].p2].y = b.puntos[b.curvas[cero].p1].y
    with pytest.raises(ErrorBoceto, match="largo cero"):
        b.simetria([otra], cero)


def test_los_textos_no_se_copian_y_si_solo_hay_textos_avisa():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10))
    t = b.agregar_texto((3, 0), "A", 5)
    assert isinstance(b.curvas[t], Texto)
    with pytest.raises(ErrorBoceto, match="Seleccioná la geometría"):
        b.simetria([t], eje)


@pytest.mark.parametrize("k", [0.05, -0.08])
def test_la_curvatura_de_las_manijas_de_una_spline_cambia_de_signo_al_reflejar(k):
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 40), True)
    sid = b.agregar_spline([(8, 2), (14, 11), (22, 4), (30, 12)], "ajuste")
    b.activar_manija(sid, b.curvas[sid].pts[1], angulo=20.0, largo=6.0, curvatura=k)
    copia = b.simetria([sid], eje)[0]
    assert b.curvas[copia].manijas[0][2] == -k
    assert _es_el_reflejo(b, sid, copia, (0, -10), (0, 40)) and _es_el_reflejo(b, copia, sid, (0, -10), (0, 40))


def test_espejar_en_el_lugar_tambien_invierte_la_curvatura_de_las_manijas():
    b = Boceto()
    sid = b.agregar_spline([(8, 2), (14, 11), (22, 4), (30, 12)], "ajuste")
    b.activar_manija(sid, b.curvas[sid].pts[1], angulo=20.0, largo=6.0, curvatura=0.05)
    antes = [q for prim in b.primitivas(sid) for q in puntos_primitiva(prim, 64)]
    b.reflejar([sid], (0, 0), horizontal=True)
    assert b.curvas[sid].manijas[0][2] == -0.05
    despues = b.primitivas(sid)
    assert all(min(distancia_primitiva(c, (-q[0], q[1])) for c in despues) < 1e-6 for q in antes)


def test_escalar_ajusta_la_curvatura_de_las_manijas_de_una_spline():
    """Gemelo del defecto anterior: la curvatura (1/mm) de una manija baja al agrandar la figura."""
    b = Boceto()
    sid = b.agregar_spline([(8, 2), (14, 11), (22, 4), (30, 12)], "ajuste")
    b.activar_manija(sid, b.curvas[sid].pts[1], angulo=20.0, largo=6.0, curvatura=0.05)
    antes = [q for prim in b.primitivas(sid) for q in puntos_primitiva(prim, 64)]
    b.escalar([sid], (0.0, 0.0), 2.0)
    assert b.curvas[sid].manijas[0][2] == pytest.approx(0.025)
    despues = b.primitivas(sid)
    assert all(min(distancia_primitiva(c, (2 * q[0], 2 * q[1])) for c in despues) < 1e-6 for q in antes)


# ---------------------------------------------------------------- la herramienta mirror_sketch (la misma para agentes)
def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _sesion_del_video():
    s = api.Sesion()
    llamar(s, "create_sketch", name="S", plane="XY")
    ids = [llamar(s, "draw_line", sketch="S", **d)["entities"][0]["id"] for d in (
        {"start_x": -50, "start_y": 0, "end_x": 0, "end_y": 0}, {"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 70},
        {"start_x": 0, "start_y": 70, "end_x": -50, "end_y": 0})]
    return s, ids


def test_mirror_sketch_del_video_perfiles_extrusion_deshacer_guardar_y_reabrir(tmp_path):
    s, ids = _sesion_del_video()
    r = llamar(s, "mirror_sketch", sketch="S", entities=ids, axis=ids[1])
    assert len(r["entities"]) == 2 and r["points"] and r["profiles"] == 2 and r["constraints"][0]["type"] == "symmetry"
    sk = llamar(s, "get_sketch", sketch="S")
    assert sorted((p["x"], p["y"]) for p in sk["points"]) == [(-50, 0), (0, 0), (0, 70), (50, 0)]   # A' = (50, 0)
    assert [p["area"] for p in sk["profiles"]] == [1750, 1750]
    llamar(s, "extrude", sketch="S", profile="all", distance=10)
    total = llamar(s, "get_physical_properties")["total"]
    assert total["volume"] == pytest.approx(35000) and total["bounding_box"]["min"] == [-50, 0, 0] \
        and total["bounding_box"]["max"] == [50, 70, 10]
    llamar(s, "undo")                                          # la extrusión
    llamar(s, "undo")                                          # la simetría entera de una vez
    assert len(llamar(s, "get_sketch", sketch="S")["entities"]) == 3
    llamar(s, "redo")
    assert len(llamar(s, "get_sketch", sketch="S")["entities"]) == 5
    ruta = str(tmp_path / "simetria.omnicad")
    llamar(s, "save_document", path=ruta)
    s2 = api.Sesion()
    llamar(s2, "open_document", path=ruta)
    sk2 = llamar(s2, "get_sketch", sketch="S")
    assert sorted((p["x"], p["y"]) for p in sk2["points"]) == [(-50, 0), (0, 0), (0, 70), (50, 0)]
    assert [c["type"] for c in sk2["constraints"]].count("symmetry") == 1


def test_mirror_sketch_conserva_la_simetria_al_cambiar_una_cota():
    s, ids = _sesion_del_video()
    llamar(s, "mirror_sketch", sketch="S", entities=ids, axis=ids[1])
    llamar(s, "add_constraint", sketch="S", type="fix", entities=[ids[1]])       # el eje queda quieto
    d = llamar(s, "add_dimension", sketch="S", type="distance", entities=[ids[0]], value=50)["dimension"]["id"]
    llamar(s, "edit_dimension", dimension=d, value=60)
    xs = sorted(p["x"] for p in llamar(s, "get_sketch", sketch="S")["points"])
    assert xs[0] == pytest.approx(-60) and xs[-1] == pytest.approx(60)


def test_mirror_sketch_con_eje_inclinado_y_geometria_fuera_del_origen():
    s = api.Sesion()
    llamar(s, "create_sketch", name="S", plane="XY")
    eje = llamar(s, "draw_line", sketch="S", start_x=-15, start_y=40, end_x=25, end_y=-10, construction=True)["entities"][0]["id"]
    ln = llamar(s, "draw_line", sketch="S", start_x=12, start_y=7, end_x=30, end_y=2)["entities"][0]["id"]
    r = llamar(s, "mirror_sketch", sketch="S", entities=[ln], axis=eje)
    sk = llamar(s, "get_sketch", sketch="S")
    copia = next(e for e in sk["entities"] if e["id"] == r["entities"][0]["id"])
    esperado = [_reflejo(q, (-15, 40), (25, -10)) for q in ((12, 7), (30, 2))]
    assert math.dist(copia["start"], esperado[0]) < 1e-3 and math.dist(copia["end"], esperado[1]) < 1e-3      # get_sketch redondea a 4 decimales


def test_mirror_sketch_lo_ya_simetrico_y_el_eje_de_largo_cero_fallan_con_mensaje_claro():
    s = api.Sesion()
    llamar(s, "create_sketch", name="S", plane="XY")
    eje = llamar(s, "draw_line", sketch="S", start_x=0, start_y=-10, end_x=0, end_y=10)["entities"][0]["id"]
    sobre = llamar(s, "draw_line", sketch="S", start_x=0, start_y=2, end_x=0, end_y=6)["entities"][0]["id"]
    antes = len(llamar(s, "get_sketch", sketch="S")["entities"])
    r = api.llamar(s, "mirror_sketch", {"sketch": "S", "entities": [sobre], "axis": eje})
    assert not r["ok"] and r["error_kind"] == "INVALID_GEOMETRY" and "ya está sobre" in r["mensaje"]
    assert len(llamar(s, "get_sketch", sketch="S")["entities"]) == antes


# ---------------------------------------------------------------- el panel SIMETRÍA en el Lienzo
def _lienzo(app_qt):
    from omnicad.ui.editor_boceto import Lienzo
    b, ab, bc, ca = _triangulo()
    b.agregar_circulo((-120, -60), 12)
    lz = Lienzo(b, TablaParametros().evaluar, plano=PLANO)
    lz.ajustar_grilla = False
    lz.resize(900, 700)
    estados = []
    lz.simetria_estado.connect(estados.append)
    return lz, (ab, bc, ca), estados


def _tecla(lz, k):
    from PySide6.QtTest import QTest
    QTest.keyClick(lz, k)


def test_el_panel_arranca_pidiendo_la_geometria_y_aceptar_esta_deshabilitado(app_qt):
    lz, _, estados = _lienzo(app_qt)
    lz.set_herramienta("simetria")
    e = estados[-1]
    assert e == {"objetos": 0, "eje": False, "campo": "seleccion", "valido": False, "previa": True,
                 "guia": "Elegí la geometría a reflejar: clic en cada curva o arrastrá una ventana.", "error": ""}


def test_elegir_objetos_y_eje_muestra_la_previa_sin_tocar_el_boceto_y_aceptar_la_crea(app_qt):
    lz, (ab, bc, ca), estados = _lienzo(app_qt)
    antes = len(lz.b.curvas)
    lz.set_herramienta("simetria")
    lz.seleccion = [ab, bc, ca]
    lz._emitir_simetria()
    assert estados[-1]["objetos"] == 3 and not estados[-1]["valido"] and "Enter" in estados[-1]["guia"]
    lz.elegir_campo_simetria("eje")
    lz.agregar_pick(bc, (0, 35))                              # el eje es uno de los objetos: se ignora al reflejar
    e = estados[-1]
    assert e["eje"] and e["valido"] and e["campo"] == "eje" and e["error"] == "" and lz._eje_simetria == bc
    polis, error = lz._calcular_simetria()
    assert not error and any(math.dist(q, (50, 0)) < 1e-9 for poli in polis for q in poli)
    assert len(lz.b.curvas) == antes                           # la previa no es parte del boceto
    assert lz.aceptar_simetria() and lz.herramienta == "seleccionar" and lz.seleccion == []
    assert len(lz.b.curvas) == antes + 2 and lz.resultado.ok
    assert sum(r.tipo == "simetrica" for r in lz.b.restricciones.values()) == 1
    lz.deshacer()                                              # un solo paso de deshacer
    assert len(lz.b.curvas) == antes and not any(r.tipo == "simetrica" for r in lz.b.restricciones.values())
    lz.rehacer()
    assert len(lz.b.curvas) == antes + 2


def test_esc_cancela_sin_modificar_el_boceto_desde_cualquier_campo(app_qt):
    from PySide6.QtCore import Qt
    lz, (ab, bc, ca), _ = _lienzo(app_qt)
    for campo in ("seleccion", "eje"):
        antes = (len(lz.b.curvas), len(lz.b.puntos), len(lz.b.restricciones))
        lz.set_herramienta("simetria")
        lz.seleccion = [ab, ca]
        lz.elegir_campo_simetria(campo)
        if campo == "eje":
            lz.agregar_pick(bc, (0, 35))
        _tecla(lz, Qt.Key_Escape)
        assert lz.herramienta == "seleccionar" and lz._eje_simetria is None
        assert (len(lz.b.curvas), len(lz.b.puntos), len(lz.b.restricciones)) == antes


def test_enter_pasa_al_eje_y_acepta_y_sin_eje_no_hace_nada(app_qt):
    from PySide6.QtCore import Qt
    lz, (ab, bc, ca), _ = _lienzo(app_qt)
    antes = len(lz.b.curvas)
    lz.set_herramienta("simetria")
    _tecla(lz, Qt.Key_Return)                                  # sin nada elegido
    assert lz.fase == "seleccion" and len(lz.b.curvas) == antes
    lz.seleccion = [ab, ca]
    _tecla(lz, Qt.Key_Return)
    assert lz.fase == "eje"
    _tecla(lz, Qt.Key_Return)                                  # sin línea de simetría
    assert lz.herramienta == "simetria" and len(lz.b.curvas) == antes
    lz.agregar_pick(bc, (0, 35))
    _tecla(lz, Qt.Key_Return)
    assert lz.herramienta == "seleccionar" and len(lz.b.curvas) == antes + 2


def test_clic_en_el_vacio_o_en_una_curva_como_eje_dice_por_que_no(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    lz, (ab, bc, ca), estados = _lienzo(app_qt)
    lz.show()
    lz.centro, lz.escala = [-60.0, 0.0], 4.0
    lz.set_herramienta("simetria")
    lz.seleccion = [ab]
    lz.elegir_campo_simetria("eje")
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(-60, 60).toPoint())
    assert "no hay ninguna línea" in estados[-1]["error"] and lz._eje_simetria is None
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(-120, -48).toPoint())        # el círculo
    assert "recta" in estados[-1]["error"] and lz._eje_simetria is None
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(-25, 0).toPoint())          # AB, que es el único objeto
    assert lz._eje_simetria == ab and "Además de la línea" in estados[-1]["error"] and not estados[-1]["valido"]
    lz.hide()


def test_la_casilla_vista_previa_y_las_x_de_cada_campo(app_qt):
    lz, (ab, bc, ca), estados = _lienzo(app_qt)
    lz.set_herramienta("simetria")
    lz.seleccion = [ab, ca]
    lz.elegir_campo_simetria("eje")
    lz.agregar_pick(bc, (0, 35))
    lz.set_previa_simetria(False)
    assert estados[-1]["previa"] is False and not lz.previa_simetria
    lz.limpiar_campo_simetria("eje")
    assert lz._eje_simetria is None and estados[-1]["eje"] is False and estados[-1]["campo"] == "eje" and not estados[-1]["valido"]
    lz.limpiar_campo_simetria("seleccion")
    assert lz.seleccion == [] and estados[-1]["objetos"] == 0 and estados[-1]["campo"] == "seleccion"


def test_con_objetos_ya_elegidos_la_herramienta_arranca_pidiendo_el_eje(app_qt):
    lz, (ab, bc, ca), estados = _lienzo(app_qt)
    lz.seleccion = [ab, ca]                                    # Fusion: la herramienta puede tomar lo preseleccionado
    lz.set_herramienta("simetria")
    assert lz.fase == "eje" and estados[-1]["objetos"] == 2 and estados[-1]["campo"] == "eje"


# ---------------------------------------------------------------- el widget del panel
def test_el_widget_pinta_el_estado_y_emite_sus_senales(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton
    from omnicad.ui.panel_simetria import PanelSimetria
    p = PanelSimetria()
    recibido = []
    p.campo.connect(lambda c: recibido.append(("campo", c)))
    p.limpiar.connect(lambda c: recibido.append(("limpiar", c)))
    p.previa.connect(lambda x: recibido.append(("previa", x)))
    p.aceptado.connect(lambda: recibido.append("aceptado"))
    p.cancelado.connect(lambda: recibido.append("cancelado"))
    assert not p.boton_ok.isEnabled() and p.filas["seleccion"].boton.text() == "Seleccionar"
    p.mostrar({"objetos": 3, "eje": True, "campo": "eje", "valido": True, "previa": True, "guia": "Listo", "error": ""})
    assert p.boton_ok.isEnabled() and p.filas["seleccion"].boton.text() == "3 seleccionados"
    assert p.filas["eje"].boton.text() == "1 seleccionado" and p.filas["eje"].boton.property("activa") is True
    assert p.guia.text() == "Listo" and p.mensaje.text() == ""
    p.mostrar({"objetos": 1, "eje": True, "campo": "eje", "valido": False, "previa": False, "guia": "", "error": "Mal"})
    assert not p.boton_ok.isEnabled() and p.mensaje.text() == "Mal" and not p.casilla.isChecked()
    p.show()
    QTest.mouseClick(p.filas["seleccion"].boton, Qt.LeftButton)
    QTest.mouseClick(p.filas["eje"].borrar, Qt.LeftButton)
    p.casilla.setChecked(True)
    QTest.mouseClick(next(b for b in p.findChildren(QPushButton) if b.text() == "Cancelar"), Qt.LeftButton)
    p.mostrar({"objetos": 1, "eje": True, "campo": "eje", "valido": True, "previa": True, "guia": "", "error": ""})
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    p.hide()
    assert ("campo", "seleccion") in recibido and ("limpiar", "eje") in recibido and ("previa", True) in recibido
    assert "cancelado" in recibido and "aceptado" in recibido
    assert all(b.focusPolicy() == Qt.NoFocus for b in p.findChildren(QPushButton))       # Enter y Esc siguen siendo del lienzo
