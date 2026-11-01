"""Ayudas de dibujo del Boceto 3D (BOC-47, BOC-74, BOC-77, BOC-78). Núcleo puro (`restricciones/inferencia3d.py`): lo que
es de la geometría (medio, cruce, pie, tangente, sobre la curva) engancha en el espacio y deja su restricción; lo que es
del plano activo de la tríada (alineaciones, horizontal/vertical) se resuelve proyectando a ese plano."""
import math

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.restricciones import boceto3d as b3
from omnicad.restricciones.inferencia3d import ayudas, proyectar, uniones

PLANO = geo.Plano("XY")
X, Y, Z = np.array([1.0, 0, 0]), np.array([0.0, 1, 0]), np.array([0.0, 0, 1])


def proy(b, origen=(0, 0, 0), u=X, v=Y):
    return proyectar(b, PLANO, np.array(origen, float), u, v)


def mejor(p, cursor, tol=1.0, **kw):
    r = ayudas(p, np.array(cursor, float), tol, **kw)
    return r[0] if r else None


def test_punto_medio_de_una_linea_en_el_plano():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    a = mejor(proy(b), (10.2, 0.3, 0))
    assert a.tipo == "punto_medio" and a.etiqueta == "Punto medio" and np.allclose(a.punto, (10, 0, 0))


def test_el_medio_de_una_linea_fuera_del_plano_es_ese_punto_3d():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 7), (20, 10, 7))                  # a 7 mm del plano z = 0
    a = mejor(proy(b), (10.1, 5.2, 0))
    assert a.tipo == "punto_medio" and np.allclose(a.punto, (10, 5, 7))


def test_interseccion_de_dos_lineas_proyectadas():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (20, 20, 0))
    b3.agregar_linea(b, (0, 20, 5), (20, 0, 5))                   # se cruzan al verlas desde arriba
    a = mejor(proy(b), (10.3, 10.2, 0))
    assert a.tipo == "interseccion" and a.etiqueta == "Intersección" and np.allclose(a.punto, (10, 10, 0))


def test_alineacion_con_un_punto_existente_da_la_guia_y_la_etiqueta():
    b = Boceto()
    b3.agregar_punto(b, (30, 12, 4), unir=False)
    a = mejor(proy(b), (30.3, 40, 0))
    assert a.tipo == "alineado_v" and np.allclose(a.punto, (30, 40, 0)) and len(a.guias) == 1
    assert "un punto" in a.etiqueta and "misma X" in a.etiqueta
    assert np.allclose(a.guias[0][0], (30, 12, 0)) and np.allclose(a.guias[0][1], (30, 40, 0))


def test_horizontal_desde_el_punto_anterior_usa_el_eje_de_la_triada():
    b = Boceto()
    a = mejor(proy(b), (25, 0.2, 0), base=np.array([5.0, 0, 0]))
    assert a.tipo == "horizontal" and np.allclose(a.punto, (25, 0, 0)) and "eje X de la tríada" in a.etiqueta


def test_la_triada_girada_cambia_las_direcciones_de_la_ayuda():
    b = Boceto()
    u, v = np.array([0.0, 1, 0]), np.array([-1.0, 0, 0])         # tríada girada 90° sobre Z
    a = mejor(proy(b, u=u, v=v), (0.2, 25, 0), base=np.array([0.0, 5, 0]))
    assert a.tipo == "horizontal" and np.allclose(a.punto, (0, 25, 0))     # «horizontal» = a lo largo de u = +Y


def test_tangente_desde_el_punto_anterior_a_un_circulo_paralelo_al_plano():
    b = Boceto()
    b3.agregar_circulo(b, (20, 0, 0), 5, (0, 0, 1))
    a = mejor(proy(b), (18.75, 4.84, 0), tol=0.3, base=np.array([0.0, 0, 0]))
    assert a is not None and a.tipo == "tangente" and a.etiqueta == "Tangente a la curva"
    # el punto de tangencia: la distancia al centro es el radio y el radio es perpendicular a la visual
    r = a.punto - np.array([20.0, 0, 0])
    assert np.linalg.norm(r) == pytest.approx(5, abs=1e-6) and abs(float(r @ (a.punto - np.zeros(3)))) < 1e-6


def test_las_curvas_aproximadas_no_dan_punto_medio_ni_alineacion_con_sus_vertices():
    b = Boceto()
    b3.agregar_elipse(b, (0, 0, 0), (20, 0, 0), 10, (0, 0, 1))
    p = proy(b)
    assert p.aprox                                               # se aproxima con tramos
    for xy in ((10, 8.66), (0.5, 9.9), (-14.1, 7.1)):             # sobre la elipse: nunca «punto medio»
        a = ayudas(p, np.array([xy[0], xy[1], 0.0]), 0.6)
        assert all(x.tipo != "punto_medio" for x in a)


def test_un_arco_inclinado_se_aproxima_y_uno_paralelo_es_exacto():
    b = Boceto()
    b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))      # paralelo a XY
    b3.agregar_arco(b, (30, 0, 0), (30, 0, 10), (30, 10, 0))     # en un plano vertical
    p = proy(b)
    a = mejor(p, (0.2, 10.1, 0), tol=1.0)
    assert a is not None and a.tipo == "punto_medio" and np.allclose(a.punto, (0, 10, 0), atol=1e-6)
    assert len(p.aprox) > 0 and len(p.b2.curvas) > 1


def test_un_texto_no_da_ayudas_ni_rompe_las_demas():
    b = Boceto()
    b3.agregar_texto(b, (0, 0, 0), "A", 10)
    b3.agregar_linea(b, (40, 0, 0), (60, 0, 0))
    p = proy(b)
    assert len(p.espacio) == 1 and mejor(p, (50.2, 0.2, 0)).tipo == "punto_medio"


def test_una_curva_de_canto_no_rompe_las_ayudas():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (0, 0, 20))                   # vertical: desde arriba es un punto
    b3.agregar_linea(b, (5, 5, 0), (25, 5, 0))
    r = ayudas(proy(b), np.array([15.0, 5.2, 0]), 1.0)
    assert r and r[0].tipo == "punto_medio"


def test_solo_ayudas_de_las_familias_pedidas():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    r = ayudas(proy(b), np.array([10.2, 0.3, 0.0]), 1.0, tipos=("alineacion",))
    assert all(x.tipo != "punto_medio" for x in r)
    assert ayudas(proy(b), np.array([10.2, 0.3, 0.0]), 1.0, tipos=("medio",))[0].tipo == "punto_medio"


def test_la_histeresis_mantiene_la_ayuda_un_poco_mas():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    p = proy(b)
    a = mejor(p, (10.2, 0.3, 0), tol=0.5)
    assert a is not None and a.tipo == "punto_medio"
    cerca = np.array([10.55, 0.3, 0.0])                          # fuera de 0,5 mm del medio pero dentro de 1,4 veces
    assert mejor(p, cerca, tol=0.5) is None or mejor(p, cerca, tol=0.5).tipo != "punto_medio"
    assert mejor(p, cerca, tol=0.5, previa=a).tipo == "punto_medio"


def test_sin_geometria_no_hay_ayudas_salvo_el_origen():
    assert mejor(proy(Boceto()), (3, 4, 0)) is None
    assert ayudas(proy(Boceto()), np.array([0.2, 40.0, 0.0]), 1.0)[0].tipo == "alineado_v"      # alineado con el origen


# ---------------------------------------------------------------- la herramienta del MCP y la CLI
def _sesion_3d():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    api.llamar(s, "draw_line_3d", {"start": [0, 0, 0], "end": [40, 0, 0]})
    api.llamar(s, "draw_line_3d", {"start": [0, 40, 7], "end": [40, 0, 7]})        # la segunda, a 7 mm del plano
    return s


def test_infer_sketch_snap_3d_da_punto_medio_en_el_plano_y_no_modifica_nada():
    from omnicad import api
    s = _sesion_3d()
    antes = api.llamar(s, "get_sketch", {"sketch": "U"})["result"]
    r = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [20.2, 0.3, 5], "sketch": "U"})
    assert r["ok"], r
    sel = r["result"]["selected"]
    assert sel["type"] == "midpoint" and sel["point"] == [20.0, 0.0, 0.0] and sel["label"] == "Punto medio"
    assert api.llamar(s, "get_sketch", {"sketch": "U"})["result"] == antes


def test_infer_sketch_snap_3d_dice_que_restricciones_dejaria_el_clic():
    from omnicad import api
    s = _sesion_3d()
    ids = {c["id"]: c["type"] for c in api.llamar(s, "get_sketch", {"sketch": "U"})["result"]["entities_3d"]}
    linea_en_el_plano = min(i for i, t in ids.items() if t == "line")
    sel = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [20.2, 0.3, 5]})["result"]["selected"]
    assert sel["constraints"] == [{"type": "midpoint", "entity": linea_en_el_plano, "applies_to": "point"}]
    sel = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [25.0, 0.2, 0], "base": [5, 0, 0]})["result"]["selected"]
    assert sel["type"] == "horizontal" and sel["constraints"] == [{"type": "axis", "entity": None, "applies_to": "line", "axis": "x"}]
    sel = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [60.0, 3.0, 0], "types": ["alignment"]})["result"]
    assert all(c["constraints"] == [] for c in sel["candidates"])               # una alineación es solo posición


def test_infer_sketch_snap_3d_intersecta_lo_que_se_cruza_visto_desde_el_plano():
    from omnicad import api
    s = _sesion_3d()
    api.llamar(s, "draw_line_3d", {"start": [0, 0, 0], "end": [40, 40, 0]})          # cruza la de z = 7 al verla desde arriba
    r = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [20.0, 20.1, 0], "types": ["intersection"]})["result"]
    assert r["selected"]["type"] == "intersection" and r["selected"]["point"] == [20.0, 20.0, 0.0]


def test_infer_sketch_snap_3d_filtra_por_familias_y_rechaza_lo_que_no_sirve():
    from omnicad import api
    s = _sesion_3d()
    r = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [20.2, 0.3, 0], "types": ["alignment"]})["result"]
    assert r["count"] > 0 and all(c["type"].startswith("aligned") for c in r["candidates"])
    for args in ({"cursor": [1, 2]}, {"cursor": [0, 0, float("nan")]}, {"cursor": [0, 0, 0], "types": ["mitad"]},
                 {"cursor": [0, 0, 0], "tolerance": 0}, {"cursor": [0, 0, 0], "alternative": -1},
                 {"cursor": [0, 0, 0], "base": [1, 2]}):
        e = api.llamar(s, "infer_sketch_snap_3d", args)
        assert not e["ok"] and e["error_kind"] == "INVALID_ARGUMENTS", (args, e)


def test_infer_sketch_snap_3d_la_triada_en_otro_plano_cambia_las_direcciones():
    from omnicad import api
    s = _sesion_3d()
    r = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [0, 20, 7.2], "plane": "yz", "origin": [0, 0, 0]})["result"]
    assert r["selected"]["point"] == [0.0, 20.0, 7.0] or r["selected"]["point"][1] == 20.0      # la línea a z = 7 en yz


# ---------------------------------------------------------------- lo que deja la ayuda (BOC-74)
def _punto_y_linea_nueva(b, base, cursor, **kw):
    """La mejor ayuda en `cursor` y lo que queda de dibujar una línea de `base` a su punto: (ayuda, uniones, id de la línea)."""
    p = proy(b)
    a = mejor(p, cursor, base=np.array(base, float), **kw)
    return a, uniones(p, a), b3.agregar_linea(b, base, tuple(a.punto))


def _restricciones(b):
    return sorted((r["tipo"], tuple(sorted(r["entidades"]))) for r in b3.datos(b)["restricciones"].values())


def test_el_punto_medio_en_el_plano_deja_la_restriccion_y_no_mueve_nada():
    b = Boceto()
    largo = b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    a, un, nueva = _punto_y_linea_nueva(b, (10, 10, 0), (10.2, 0.3, 0))
    assert un["punto"] == [("punto_medio", largo)] and un["curva"] == []
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    antes = dict(b3.datos(b)["puntos"])
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 1
    assert _restricciones(b) == [("punto_medio", tuple(sorted((fin, largo))))] and b3.datos(b)["puntos"] == antes


def test_el_medio_de_una_linea_fuera_del_plano_deja_la_restriccion_y_no_mueve_nada():
    b = Boceto()
    largo = b3.agregar_linea(b, (0, 0, 7), (20, 0, 7))                    # su medio real está a 7 mm del plano
    a, un, nueva = _punto_y_linea_nueva(b, (10, 10, 0), (10.2, 0.3, 0))
    assert un["punto"] == [("punto_medio", largo)] and np.allclose(a.punto, (10, 0, 7))
    antes = dict(b3.datos(b)["puntos"])
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 1
    assert _restricciones(b) == [("punto_medio", tuple(sorted((fin, largo))))] and b3.datos(b)["puntos"] == antes


def test_la_interseccion_une_el_punto_con_las_dos_lineas():
    b = Boceto()
    uno = b3.agregar_linea(b, (0, 0, 0), (40, 40, 0))
    otro = b3.agregar_linea(b, (0, 40, 0), (40, 0, 0))
    a, un, nueva = _punto_y_linea_nueva(b, (20, -10, 0), (20.2, 19.8, 0))
    assert sorted(d for _t, d in un["punto"]) == sorted((uno, otro)) and {t for t, _d in un["punto"]} == {"coincidente"}
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 2


def test_perpendicular_y_horizontal_dejan_su_restriccion_sobre_la_linea_nueva():
    b = Boceto()
    pared = b3.agregar_linea(b, (0, 10, 0), (20, 10, 0))
    a, un, nueva = _punto_y_linea_nueva(b, (5, 0, 0), (5.2, 10.1, 0))
    assert a.tipo == "perpendicular" and un["curva"] == [("perpendicular", pared)] and un["punto"] == [("coincidente", pared)]
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 2
    assert ("perpendicular", tuple(sorted((nueva, pared)))) in _restricciones(b)

    b = Boceto()
    a, un, nueva = _punto_y_linea_nueva(b, (5, 0, 0), (25, 0.2, 0))
    assert a.tipo == "horizontal" and un == {"punto": [], "curva": [("eje", None)]}
    assert b3.aplicar_uniones(b, un, None, nueva, {}) == 1
    assert next(iter(b3.datos(b)["restricciones"].values())) == {"tipo": "eje", "entidades": [nueva], "eje": "x"}


def test_horizontal_con_una_triada_girada_no_es_un_eje_del_boceto_y_no_deja_restriccion():
    b = Boceto()
    u = np.array([math.cos(0.3), math.sin(0.3), 0])
    v = np.array([-math.sin(0.3), math.cos(0.3), 0])
    p = proy(b, u=u, v=v)
    base = np.zeros(3)
    a = mejor(p, 25 * u + 0.2 * v, base=base)
    nueva = b3.agregar_linea(b, base, tuple(a.punto))
    assert a.tipo == "horizontal" and b3.aplicar_uniones(b, uniones(p, a), None, nueva, {}) == 0
    assert not b3.datos(b)["restricciones"]


def test_con_un_circulo_la_ayuda_deja_la_tangente_y_el_contacto():
    b = Boceto()
    circulo = b3.agregar_circulo(b, (60, 0, 0), 15, (0, 0, 1))
    p = proy(b)
    d, g = math.sqrt(60 ** 2 - 15 ** 2), math.asin(15 / 60)
    a = mejor(p, (d * math.cos(g), d * math.sin(g), 0), base=np.zeros(3))      # donde la visual toca el círculo
    assert a.tipo == "tangente" and uniones(p, a) == {"punto": [("coincidente", circulo)], "curva": [("tangente", circulo)]}
    assert uniones(p, None) == {"punto": [], "curva": []}
    nueva = b3.agregar_linea(b, (0, 0, 0), tuple(a.punto))
    antes = {k: list(v) for k, v in b3.datos(b)["puntos"].items()}
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, uniones(p, a), fin, nueva, {}) == 2
    assert all(math.dist(antes[k], v) < 1e-7 for k, v in b3.datos(b)["puntos"].items())    # ya se cumplía: nada se movió
    assert {t for t, _e in _restricciones(b)} == {"coincidente", "tangente"} and b3.resolver(b, {}).ok


# ---------------------------------------------------------------- enganchar en el espacio (BOC-78)
def test_el_rayo_del_cursor_engancha_el_medio_que_la_proyeccion_al_plano_no_veria():
    b = Boceto()
    largo = b3.agregar_linea(b, (0, 0, 30), (20, 0, 30))                  # el medio real, a 30 mm del plano activo
    mira = np.array([1.0, 0.0, -1.0])                                     # vista inclinada 45°
    cursor = np.array([40.0, 0.3, 0.0])                                   # en pantalla, el medio cae justo acá
    p = proy(b)
    assert mejor(p, cursor).tipo != "punto_medio"                         # sin el rayo, lejos de su proyección
    a = mejor(p, cursor, rayo=(cursor, mira))
    assert a.tipo == "punto_medio" and np.allclose(a.punto, (10, 0, 30)) and uniones(p, a)["punto"] == [("punto_medio", largo)]


def test_un_rayo_paralelo_a_una_linea_y_una_vista_de_canto_no_rompen():
    b = Boceto()
    b3.agregar_linea(b, (5, 0, 0), (5, 0, 20))
    b3.agregar_linea(b, (0, 0, 10), (10, 0, 10))
    p = proy(b)
    a = ayudas(p, None, 1.0, rayo=(np.array([-50.0, 0.0, 10.2]), X))       # sin punto en el plano: mirando de canto
    assert a and a[0].tipo == "interseccion" and np.allclose(a[0].punto, (5, 0, 10))


def test_dos_lineas_que_se_cruzan_de_verdad_fuera_del_plano():
    b = Boceto()
    uno = b3.agregar_linea(b, (0, 0, 5), (20, 20, 5))
    otro = b3.agregar_linea(b, (0, 20, 5), (20, 0, 5))
    p = proy(b)
    a = mejor(p, (10.2, 9.9, 0))
    assert a.tipo == "interseccion" and np.allclose(a.punto, (10, 10, 5))
    assert sorted(e for _t, e in uniones(p, a)["punto"]) == sorted((uno, otro))


def test_el_pie_de_la_perpendicular_es_el_de_la_recta_en_el_espacio():
    b = Boceto()
    pared = b3.agregar_linea(b, (0, 10, 6), (20, 10, 6))
    base = (5, 0, 2)
    a, un, nueva = _punto_y_linea_nueva(b, base, (5.2, 10.1, 0))
    assert a.tipo == "perpendicular" and np.allclose(a.punto, (5, 10, 6))
    assert float((a.punto - np.array(base, float)) @ np.array([1.0, 0, 0])) == pytest.approx(0, abs=1e-9)
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 2 and ("perpendicular", tuple(sorted((nueva, pared)))) in _restricciones(b)


def test_tangente_a_un_circulo_fuera_del_plano_activo_desde_su_plano():
    b = Boceto()
    circulo = b3.agregar_circulo(b, (60, 0, 9), 15, (0, 0, 1))
    d, g = math.sqrt(60 ** 2 - 15 ** 2), math.asin(15 / 60)
    a, un, nueva = _punto_y_linea_nueva(b, (0, 0, 9), (d * math.cos(g), d * math.sin(g), 0))
    assert a.tipo == "tangente" and a.punto[2] == pytest.approx(9) and un["curva"] == [("tangente", circulo)]
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    assert b3.aplicar_uniones(b, un, fin, nueva, {}) == 2
    assert b3.resolver(b, {}).ok


def test_desde_fuera_del_plano_del_circulo_no_hay_tangente_real_y_no_queda_restriccion():
    b = Boceto()
    b3.agregar_circulo(b, (60, 0, 0), 15, (0, 0, 1))
    d, g = math.sqrt(60 ** 2 - 15 ** 2), math.asin(15 / 60)
    a, un, nueva = _punto_y_linea_nueva(b, (0, 0, 9), (d * math.cos(g), d * math.sin(g), 0))
    assert all(t != "tangente" for t, _e in un["curva"])
    fin = b3.datos(b)["curvas"][nueva]["puntos"][1]
    b3.aplicar_uniones(b, un, fin, nueva, {})
    assert all(t != "tangente" for t, _e in _restricciones(b))


@pytest.mark.parametrize("crear, cursor", [
    (lambda b: b3.agregar_circulo(b, (0, 0, 4), 10, (0, 0, 1)), (7.2, 6.9, 0)),
    (lambda b: b3.agregar_arco(b, (10, 0, 4), (0, 10, 4), (-10, 0, 4)), (7.2, 6.9, 0)),
    (lambda b: b3.agregar_elipse(b, (0, 0, 4), (20, 0, 0), 10, (0, 0, 1)), (16.0, 6.1, 0)),
    (lambda b: b3.agregar_conica(b, (0, 0, 4), (10, 10, 4), (20, 0, 4)), (3.0, 2.3, 0)),
    (lambda b: b3.agregar_spline(b, [(0, 0, 4), (10, 5, 4), (20, 0, 4)]), (4.4, 3.2, 0)),
])
def test_sobre_la_curva_deja_coincidente_y_no_mueve_nada(crear, cursor):
    b = Boceto()
    curva = crear(b)
    p = proy(b)
    a = mejor(p, cursor)
    assert a is not None and a.tipo == "sobre_curva" and a.etiqueta == "Sobre la curva"
    assert a.punto[2] == pytest.approx(4) and uniones(p, a) == {"punto": [("coincidente", curva)], "curva": []}
    punto = b3.agregar_punto(b, tuple(a.punto), unir=False)
    antes = {k: list(v) for k, v in b3.datos(b)["puntos"].items()}
    assert b3.aplicar_uniones(b, uniones(p, a), punto, None, {}) == 1
    assert all(math.dist(antes[k], v) < 1e-7 for k, v in b3.datos(b)["puntos"].items())


def test_un_arco_no_engancha_fuera_de_su_tramo():
    b = Boceto()
    b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    assert mejor(proy(b), (0.3, -10.1, 0)) is None or mejor(proy(b), (0.3, -10.1, 0)).tipo != "sobre_curva"


def test_interseccion_de_una_linea_con_un_circulo_deja_las_dos_coincidencias():
    b = Boceto()
    circulo = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    recta = b3.agregar_linea(b, (-20, 6, 0), (20, 6, 0))
    p = proy(b)
    a = mejor(p, (8.2, 6.1, 0))
    assert a.tipo == "interseccion" and np.allclose(a.punto, (8, 6, 0))
    assert sorted(e for _t, e in uniones(p, a)["punto"]) == sorted((circulo, recta))


def test_dos_lineas_encadenadas_no_dan_interseccion_en_su_extremo():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    b3.agregar_linea(b, (20, 0, 0), (20, 20, 0))
    assert all(a.tipo != "interseccion" for a in ayudas(proy(b), np.array([19.8, 0.2, 0.0]), 1.0))


def test_seguir_tangente_desde_el_extremo_de_un_arco_deja_la_tangente():
    b = Boceto()
    arco = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    a, un, nueva = _punto_y_linea_nueva(b, (-10, 0, 0), (-10.1, -15, 0))   # el arco llega a (−10, 0) bajando
    assert a.tipo == "tangente" and np.allclose(a.punto, (-10, -15, 0), atol=1e-6) and un == {"punto": [], "curva": [("tangente", arco)]}
    antes = {k: list(v) for k, v in b3.datos(b)["puntos"].items()}
    assert b3.aplicar_uniones(b, un, None, nueva, {}) == 1
    assert all(math.dist(antes[k], v) < 1e-7 for k, v in b3.datos(b)["puntos"].items())


def test_la_ayuda_del_espacio_tambien_tiene_histeresis():
    b = Boceto()
    b3.agregar_linea(b, (0, 0, 7), (20, 0, 7))
    p = proy(b)
    a = mejor(p, (10.2, 0.3, 0), tol=0.5)
    assert a.tipo == "punto_medio"
    assert mejor(p, (10.55, 0.3, 0), tol=0.5, previa=a).tipo == "punto_medio"


def test_infer_sketch_snap_3d_engancha_en_el_espacio_con_la_direccion_de_vista():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    api.llamar(s, "draw_line_3d", {"start": [0, 0, 30], "end": [20, 0, 30]})
    sel = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [40, 0.2, 0], "view_direction": [1, 0, -1]})["result"]["selected"]
    assert sel["type"] == "midpoint" and sel["point"] == [10.0, 0.0, 30.0]
    assert api.llamar(s, "infer_sketch_snap_3d", {"cursor": [40, 0.2, 0]})["result"]["selected"]["type"] != "midpoint"
    assert not api.llamar(s, "infer_sketch_snap_3d", {"cursor": [0, 0, 0], "view_direction": [0, 0, 0]})["ok"]
    assert not api.llamar(s, "infer_sketch_snap_3d", {"cursor": [0, 0, 0], "view_direction": [1, 2]})["ok"]


def test_infer_sketch_snap_3d_avisa_tangente_y_sobre_la_curva():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    circulo = api.llamar(s, "draw_circle_3d", {"center": [60, 0, 0], "radius": 15, "normal": [0, 0, 1]})["result"]["entity"]
    d, g = math.sqrt(60 ** 2 - 15 ** 2), math.asin(15 / 60)
    sel = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [d * math.cos(g), d * math.sin(g), 0], "base": [0, 0, 0]})["result"]["selected"]
    assert sel["type"] == "tangent" and {"type": "tangent", "entity": circulo, "applies_to": "line"} in sel["constraints"]
    assert {"type": "coincident", "entity": circulo, "applies_to": "point"} in sel["constraints"]
    r = api.llamar(s, "infer_sketch_snap_3d", {"cursor": [60, 15.1, 0], "types": ["on_curve"]})["result"]
    assert r["selected"]["type"] == "on_curve" and r["selected"]["constraints"] == [{"type": "coincident", "entity": circulo, "applies_to": "point"}]


def test_una_restriccion_que_ya_esta_o_que_no_cabe_no_se_duplica_ni_falla():
    b = Boceto()
    largo = b3.agregar_linea(b, (0, 0, 0), (20, 0, 0))
    pm = b3.agregar_punto(b, (10, 0, 0), unir=False)
    un = {"punto": [("punto_medio", largo), ("punto_medio", largo), ("coincidente", 999)], "curva": []}
    assert b3.aplicar_uniones(b, un, pm, None, {}) == 1                   # la repetida y la de un id que no existe, no
    assert len(b3.datos(b)["restricciones"]) == 1
