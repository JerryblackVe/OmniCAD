"""Boceto 3D: tangente con arcos, círculos y elipses y punto sobre cualquier curva (BOC-77). Se mide aparte del solver, con
la geometría que queda: la línea en el plano de la curva, la distancia al centro, las direcciones en el contacto."""
import math

import numpy as np
import pytest

from omnicad.nucleo import curvas3d
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.restricciones import boceto3d as b3
from omnicad.restricciones.boceto import ErrorBoceto

TOL = 1e-6
PLANO = geo.Plano("XY")


def _p(b, pid):
    return np.array(b3.datos(b)["puntos"][pid], float)


def _extremos(b, cid):
    return [_p(b, p) for p in b3.datos(b)["curvas"][cid]["puntos"]]


def _dist_recta(q, a, c):
    return float(np.linalg.norm(np.cross(q - a, (c - a) / np.linalg.norm(c - a))))


def _resolver(b, *ids):
    b3.agregar_restriccion(b, "tangente", list(ids))
    r = b3.resolver(b, {})
    assert r.ok, r.mensaje
    return r


def _uno():
    return np.array([-30.0, 14, 3]), np.array([30.0, 12, 2])


def test_linea_y_circulo_quedan_en_el_mismo_plano_a_la_distancia_del_radio():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    l = b3.agregar_linea(b, *_uno())
    r = _resolver(b, l, k)
    a, c = _extremos(b, l)
    centro = _p(b, b3.datos(b)["curvas"][k]["puntos"][0])
    assert a[2] == pytest.approx(centro[2], abs=TOL) and c[2] == pytest.approx(centro[2], abs=TOL)
    assert _dist_recta(centro, a, c) == pytest.approx(10, abs=TOL)
    assert r.gdl == 6                                      # 3 del centro + 6 de la línea − 2 del plano − 1 de la distancia


def test_un_circulo_inclinado_arrastra_la_linea_a_su_plano():
    b = Boceto()
    n = np.array([0.0, 1, 1]) / math.sqrt(2)
    k = b3.agregar_circulo(b, (5, 5, 5), 8, n)
    b3.agregar_restriccion(b, "fijo", [k])
    l = b3.agregar_linea(b, (-20, 20, 0), (20, 15, 2))
    _resolver(b, l, k)
    a, c = _extremos(b, l)
    assert float((a - (5, 5, 5)) @ n) == pytest.approx(0, abs=TOL) and float((c - (5, 5, 5)) @ n) == pytest.approx(0, abs=TOL)
    assert _dist_recta(np.array([5.0, 5, 5]), a, c) == pytest.approx(8, abs=TOL)


def test_linea_y_arco_miden_contra_su_circulo():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, *_uno())
    _resolver(b, l, k)
    a, c = _extremos(b, l)
    ia, im, ic = _extremos(b, k)
    centro = b3.centro(b, k)
    n = np.cross(im - ia, ic - ia)
    assert float((a - centro) @ n) == pytest.approx(0, abs=1e-4) and float((c - centro) @ n) == pytest.approx(0, abs=1e-4)
    assert _dist_recta(centro, a, c) == pytest.approx(float(np.linalg.norm(ia - centro)), abs=TOL)
    assert b3.tangencias_fuera_del_arco(b) == []


def test_arco_con_el_contacto_fuera_del_tramo_se_avisa():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    b3.agregar_restriccion(b, "fijo", [k])
    l = b3.agregar_linea(b, (-30, -12, 0), (30, -13, 0))   # queda abajo: la mitad del círculo que no está dibujada
    _resolver(b, l, k)
    assert b3.tangencias_fuera_del_arco(b) == [[l, k]]


@pytest.mark.parametrize("giro", [k * 0.157 for k in range(40)])
def test_el_contacto_justo_en_el_inicio_del_arco_no_avisa(giro):
    """Sin extremo común: el parámetro del contacto sale ±1e-12 alrededor de 0 y no puede leerse como casi una vuelta."""
    b = Boceto()
    q = lambda t: (10 * math.cos(giro + t), 10 * math.sin(giro + t), 0)  # noqa: E731
    k = b3.agregar_arco(b, q(0), q(1), q(2))
    u = np.array([-math.sin(giro), math.cos(giro), 0])
    l = b3.agregar_linea(b, tuple(np.array(q(0)) - 20 * u), tuple(np.array(q(0)) + 20 * u))
    b3.agregar_restriccion(b, "fijo", [k, l])
    _resolver(b, l, k)
    assert b3.tangencias_fuera_del_arco(b) == []


def test_elipse_toca_por_su_funcion_de_apoyo():
    b = Boceto()
    k = b3.agregar_elipse(b, (0, 0, 0), (20, 0, 0), 10, (0, 0, 1))
    b3.agregar_restriccion(b, "fijo", [k])
    l = b3.agregar_linea(b, *_uno())
    _resolver(b, l, k)
    a, c = _extremos(b, l)
    assert a[2] == pytest.approx(0, abs=TOL) and c[2] == pytest.approx(0, abs=TOL)
    u = (c - a) / np.linalg.norm(c - a)
    normal = np.array([-u[1], u[0], 0.0])
    assert abs(float(a @ normal)) == pytest.approx(math.hypot(20 * normal[0], 10 * normal[1]), abs=TOL)


def test_dos_circulos_quedan_a_la_suma_de_sus_radios_y_coplanares():
    b = Boceto()
    c1 = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    c2 = b3.agregar_circulo(b, (25, 2, 1), 8, (0, 0, 1))
    r = _resolver(b, c1, c2)
    p, q = _extremos(b, c1)[0], _extremos(b, c2)[0]
    assert float(np.linalg.norm(p - q)) == pytest.approx(18, abs=TOL) and p[2] == pytest.approx(q[2], abs=TOL) and r.gdl == 4


def test_circulo_chico_dentro_de_otro_toca_por_dentro():
    b = Boceto()
    c1 = b3.agregar_circulo(b, (0, 0, 0), 20, (0, 0, 1))
    c2 = b3.agregar_circulo(b, (5, 3, 0), 6, (0, 0, 1))
    _resolver(b, c1, c2)
    assert float(np.linalg.norm(_extremos(b, c1)[0] - _extremos(b, c2)[0])) == pytest.approx(14, abs=TOL)


def test_linea_que_arranca_en_el_extremo_de_un_arco_sigue_su_direccion():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    b3.agregar_restriccion(b, "fijo", [k])
    l = b3.agregar_linea(b, (-10, 0, 0), (-12, -20, 4))
    _resolver(b, l, k)
    a, c = _extremos(b, l)
    assert np.allclose(a, (-10, 0, 0), atol=TOL)           # sigue compartiendo el punto
    assert float((c - a) @ (a - b3.centro(b, k))) == pytest.approx(0, abs=1e-5)     # perpendicular al radio
    assert float(c[2]) == pytest.approx(0, abs=1e-5)       # y en el plano del arco


def test_dos_arcos_encadenados_son_tangentes_en_la_union():
    b = Boceto()
    k1 = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    b3.agregar_restriccion(b, "fijo", [k1])
    k2 = b3.agregar_arco(b, (-10, 0, 0), (-14, -5, 1), (-20, 0, 2))
    _resolver(b, k1, k2)
    union, paso, fin = _extremos(b, k2)
    radio = union - b3.centro(b, k2)
    normal = np.cross(paso - union, fin - union)
    assert np.allclose(union, (-10, 0, 0), atol=TOL)                     # k1 baja por −Y al llegar a la unión:
    assert float(radio @ (0, 1, 0)) == pytest.approx(0, abs=1e-5)         # el radio de k2 y su normal son
    assert float(normal @ (0, 1, 0)) == pytest.approx(0, abs=1e-4)        # perpendiculares a esa dirección


def test_una_spline_que_termina_en_un_arco_toma_su_direccion():
    b = Boceto()
    s = b3.agregar_spline(b, [(-10, 0, 0), (-10, -5, 3), (-20, -10, 4)])
    a = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    _resolver(b, s, a)
    t = b3._tangentes(b, s, b3._P(b))[0]
    assert np.allclose(t / np.linalg.norm(t), (0, -1, 0), atol=1e-9)    # el arco llega a (−10, 0) bajando
    pts = curvas3d.muestrear(b3.arista(b, s, PLANO), 400)
    assert np.allclose((pts[1] - pts[0]) / np.linalg.norm(pts[1] - pts[0]), (0, -1, 0), atol=1e-2)


def test_una_spline_toca_un_circulo_tangente_sin_extremo_comun():
    b = Boceto()
    s = b3.agregar_spline(b, [(-20, 3, 0), (0, 13, 0), (20, 2, 0)])
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    b3.agregar_restriccion(b, "fijo", [k])
    _resolver(b, s, k)
    pts = curvas3d.muestrear(b3.arista(b, s, PLANO), 4000)
    assert float(np.min(np.linalg.norm(pts - (0, 0, 0), axis=1))) == pytest.approx(10, abs=1e-3)


def test_una_conica_tangente_a_una_linea():
    b = Boceto()
    k = b3.agregar_conica(b, (0, 0, 0), (10, 10, 0), (20, 0, 0))
    b3.agregar_restriccion(b, "fijo", [k])
    l = b3.agregar_linea(b, (-5, 8, 1), (25, 7, 1))
    _resolver(b, l, k)
    a, c = _extremos(b, l)
    assert a[2] == pytest.approx(0, abs=TOL) and c[2] == pytest.approx(0, abs=TOL)
    pts = curvas3d.muestrear(b3.arista(b, k, PLANO), 4000).astype(float)
    u = (c - a) / np.linalg.norm(c - a)
    lado = (pts[:, 0] - a[0]) * -u[1] + (pts[:, 1] - a[1]) * u[0]        # con signo: toca sin cruzar
    assert abs(float(lado.max())) < 1e-3


def test_la_conica_parametrica_coincide_con_la_de_opencascade():
    b = Boceto()
    k = b3.agregar_conica(b, (0, 0, 0), (10, 10, 3), (20, 0, 5), 0.3)
    pts = curvas3d.muestrear(b3.arista(b, k, PLANO), 8)
    c = b3.curva_parametrica(b, k)
    mias = np.array([c.f(t)[0] for t in np.linspace(0, 1, 201)])
    assert max(float(np.min(np.linalg.norm(mias - p, axis=1))) for p in pts) < 0.1
    d = (c.f(0.5 + 1e-6)[0] - c.f(0.5 - 1e-6)[0]) / 2e-6
    assert np.allclose(d, c.f(0.5)[1], atol=1e-4)


@pytest.mark.parametrize("crear", [
    lambda b: b3.agregar_circulo(b, (0, 0, 0), 12, (0, 0, 1)),
    lambda b: b3.agregar_arco(b, (12, 0, 0), (0, 12, 0), (-12, 0, 0)),
    lambda b: b3.agregar_elipse(b, (0, 0, 0), (20, 0, 0), 10, (0, 0, 1)),
    lambda b: b3.agregar_conica(b, (0, 0, 0), (10, 10, 0), (20, 0, 0)),
    lambda b: b3.agregar_spline(b, [(0, 0, 0), (10, 5, 2), (20, 0, 5)]),
])
def test_un_punto_queda_sobre_la_curva(crear):
    b = Boceto()
    c = crear(b)
    p = b3.agregar_punto(b, (9, 9, 3), unir=False)
    b3.agregar_restriccion(b, "fijo", [c])
    b3.agregar_restriccion(b, "coincidente", [p, c])
    r = b3.resolver(b, {})
    assert r.ok, r.mensaje
    pts = curvas3d.muestrear(b3.arista(b, c, PLANO), 4000)
    assert float(np.min(np.linalg.norm(pts - _p(b, p), axis=1))) < 0.05


def test_el_punto_sobre_un_circulo_resta_dos_grados_de_libertad():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 12, (0, 0, 1))
    b3.agregar_restriccion(b, "fijo", [k])
    p = b3.agregar_punto(b, (20, 0, 3), unir=False)
    assert b3.resolver(b, {}).gdl == 3
    b3.agregar_restriccion(b, "coincidente", [p, k])
    assert b3.resolver(b, {}).gdl == 1


def test_lo_que_ya_se_cumple_no_se_mueve():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    l = b3.agregar_linea(b, (-20, 10, 0), (20, 10, 0))
    p = b3.agregar_punto(b, (6, 8, 0), unir=False)
    antes = {i: list(v) for i, v in b3.datos(b)["puntos"].items()}
    assert b3.agregar_si_cumple(b, "tangente", [l, k], {}) is not None
    assert b3.agregar_si_cumple(b, "coincidente", [p, k], {}) is not None
    assert all(math.dist(antes[i], v) < 1e-7 for i, v in b3.datos(b)["puntos"].items())


def test_con_todo_fijo_una_tangencia_imposible_es_conflicto():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    l = b3.agregar_linea(b, (-20, 30, 0), (20, 30, 0))
    b3.agregar_restriccion(b, "fijo", [k, l])
    b3.agregar_restriccion(b, "tangente", [l, k])
    assert not b3.resolver(b, {}).ok


def test_con_todo_fijo_y_ya_tangentes_no_hay_conflicto_ni_grados_de_libertad():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    l = b3.agregar_linea(b, (-20, 10, 0), (20, 10, 0))
    b3.agregar_restriccion(b, "fijo", [k, l])
    b3.agregar_restriccion(b, "tangente", [l, k])
    r = b3.resolver(b, {})
    assert r.ok and r.gdl == 0


def test_mover_el_centro_con_la_tangente_puesta_lleva_la_linea():
    """Lo que hace la ventana al arrastrar: mueve los puntos y vuelve a resolver."""
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    l = b3.agregar_linea(b, (-20, 10, 0), (20, 10, 0))
    _resolver(b, l, k)
    centro = b3.datos(b)["curvas"][k]["puntos"][0]
    b3.datos(b)["puntos"][centro] = [0.0, 3.0, 2.0]
    assert b3.resolver(b, {}).ok
    a, c = _extremos(b, l)
    assert a[2] == pytest.approx(_p(b, centro)[2], abs=TOL) and _dist_recta(_p(b, centro), a, c) == pytest.approx(10, abs=TOL)


def test_guardar_y_reabrir_conserva_la_tangente_y_el_resultado():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, *_uno())
    p = b3.agregar_punto(b, (0, -12, 0), unir=False)
    c = b3.agregar_circulo(b, (40, 0, 0), 5, (0, 0, 1))
    b3.agregar_restriccion(b, "coincidente", [p, c])
    _resolver(b, l, k)
    otra = Boceto()
    otra.geo3d = b3.desde_dict(b3.a_dict(b.geo3d))
    assert b3.resolver(otra, {}).ok
    assert all(math.dist(b.geo3d["puntos"][i], v) < 1e-5 for i, v in otra.geo3d["puntos"].items())


def test_dos_lineas_no_son_tangentes_y_un_texto_no_tiene_contacto():
    b = Boceto()
    l1, l2 = b3.agregar_linea(b, (0, 0, 0), (10, 0, 0)), b3.agregar_linea(b, (0, 5, 0), (10, 5, 0))
    with pytest.raises(ErrorBoceto, match="dos curvas"):
        b3.agregar_restriccion(b, "tangente", [l1, l2])
    t = b3.agregar_texto(b, (0, 0, 0), "A", 5)
    p = b3.agregar_punto(b, (1, 1, 1), unir=False)
    with pytest.raises(ErrorBoceto, match="un punto y una curva"):
        b3.agregar_restriccion(b, "coincidente", [p, t])


def test_linea_y_spline_sin_extremo_comun_sigue_pidiendolo():
    b = Boceto()
    l = b3.agregar_linea(b, (0, 0, 0), (10, 0, 0))
    s = b3.agregar_spline(b, [(20, 0, 0), (30, 5, 0)])
    with pytest.raises(ErrorBoceto, match="empezar o terminar"):
        b3.agregar_restriccion(b, "tangente", [l, s])


def test_un_centro_compartido_con_una_spline_no_es_un_extremo():
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    s = b3.agregar_spline(b, [(0, 0, 0), (0, 13, 0), (20, 2, 0)])         # arranca en el centro del círculo
    assert b3.datos(b)["curvas"][k]["puntos"][0] == b3.datos(b)["curvas"][s]["puntos"][0]
    b3.agregar_restriccion(b, "fijo", [k])
    r = _resolver(b, s, k)
    assert r.ok and 0 not in b3._tangentes(b, s, b3._P(b))


def _comando(b, *ids):
    """Lo que hacen add_constraint_3d y el paso del boceto al recalcular."""
    b3.agregar_restriccion(b, "tangente", list(ids))
    b3.acomodar_tangente(b, ids, {})
    r = b3.resolver(b, {})
    assert r.ok, r.mensaje
    return r


def _radio(b, k):
    return float(np.linalg.norm(_extremos(b, k)[0] - b3.centro(b, k)))


@pytest.mark.parametrize("p, q", [((-30, 14, 3), (30, 12, 2)),             # afuera y sobre el plano
                                  ((-30, 3, 0), (30, 3, 0)),               # corta el círculo
                                  ((-30, 14, -20), (30, 12, 25)),          # muy inclinada
                                  ((20, 3, -15), (20, 3, 15)),             # perpendicular al plano
                                  ((-50, 40, 10), (50, 42, 8))])           # lejos
@pytest.mark.parametrize("arco", [True, False])
def test_con_el_comando_el_arco_queda_igual_y_la_linea_conserva_su_largo(arco, p, q):
    """BOC-81: la figura de la ayuda de Fusion en 3D. Sin el comando el radio pasaba de 12 a 25,3 con la línea perpendicular."""
    b = Boceto()
    k = b3.agregar_arco(b, (12, 0, 0), (0, 12, 0), (-12, 0, 0)) if arco else b3.agregar_circulo(b, (0, 0, 0), 12)
    l = b3.agregar_linea(b, p, q)
    _comando(b, l, k)
    a, c = _extremos(b, l)
    assert np.allclose(b3.centro(b, k), (0, 0, 0), atol=1e-9)
    assert not arco or _radio(b, k) == pytest.approx(12, abs=1e-9)
    assert math.dist(a, c) == pytest.approx(math.dist(p, q), abs=TOL)
    assert a[2] == pytest.approx(0, abs=TOL) and c[2] == pytest.approx(0, abs=TOL)
    assert _dist_recta(np.zeros(3), a, c) == pytest.approx(12, abs=TOL)


def test_una_linea_encadenada_gira_sobre_el_extremo_y_el_arco_no_cambia():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, (-10, 0, 0), (-12, -20, 4))                       # sin el comando: radio 10,257
    largo = math.dist((-10, 0, 0), (-12, -20, 4))
    _comando(b, l, k)
    a, c = _extremos(b, l)
    assert _radio(b, k) == pytest.approx(10, abs=1e-9) and np.allclose(a, (-10, 0, 0), atol=1e-9)
    assert math.dist(a, c) == pytest.approx(largo, abs=TOL)
    assert np.allclose(c, (-10, -largo, 0), atol=1e-4)                        # sigue la dirección del arco en la unión


@pytest.mark.parametrize("otra", [
    lambda b: b3.agregar_arco(b, (30, 0, 2), (22, 8, 2), (14, 0, 2)),         # sin el comando: 10 → 11,05 y 8 → 9,04
    lambda b: b3.agregar_circulo(b, (25, 3, 2), 8),                           # 10 → 11,69
    lambda b: b3.agregar_spline(b, [(-20, 13, 0), (0, 15, 0), (20, 13, 0)]),  # 10 → 10,26
    lambda b: b3.agregar_conica(b, (-20, 20, 0), (0, 12, 0), (20, 20, 0)),    # 10 → 10,67
    lambda b: b3.agregar_elipse(b, (0, 25, 2), (15, 0, 0), 8),                # 10 → 10,47
])
def test_con_cualquier_otra_curva_el_primer_arco_queda_quieto_y_ninguno_cambia_de_radio(otra):
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    o = otra(b)
    radio_otra = _radio(b, o) if b3.datos(b)["curvas"][o]["tipo"] == "arco" else None
    antes = _extremos(b, k)
    _comando(b, k, o)
    assert np.allclose(_extremos(b, k), antes, atol=1e-9)
    assert radio_otra is None or _radio(b, o) == pytest.approx(radio_otra, abs=1e-6)


def test_dos_arcos_encadenados_tampoco_cambian_de_radio():
    b = Boceto()
    k1 = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    k2 = b3.agregar_arco(b, (-10, 0, 0), (-14, -5, 1), (-20, 0, 2))
    r2 = _radio(b, k2)
    _comando(b, k1, k2)
    assert _radio(b, k1) == pytest.approx(10, abs=1e-9) and _radio(b, k2) == pytest.approx(r2, abs=1e-6)


@pytest.mark.parametrize("entera", [True, False])                              # la línea entera o un extremo fuera del plano
def test_si_la_linea_no_puede_moverse_se_mueve_el_arco_entero(entera):
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, (-30, 14, 3), (30, 12, 2))
    b3.agregar_restriccion(b, "fijo", [l if entera else b3.datos(b)["curvas"][l]["puntos"][0]])
    _comando(b, l, k)
    a, c = _extremos(b, l)
    assert np.allclose(a, (-30, 14, 3), atol=1e-9)
    assert _radio(b, k) == pytest.approx(10, abs=1e-7)
    assert _dist_recta(b3.centro(b, k), a, c) == pytest.approx(10, abs=TOL)


def test_un_arco_vecino_de_la_linea_tampoco_cambia_de_radio():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, (-30, 14, 0), (30, 12, 0))
    vecino = b3.agregar_arco(b, (30, 12, 0), (40, 22, 0), (50, 12, 0))         # empieza donde termina la línea
    _comando(b, l, k)
    assert _radio(b, k) == pytest.approx(10, abs=1e-9) and _radio(b, vecino) == pytest.approx(10, abs=1e-6)


def test_el_comando_respeta_las_otras_restricciones_y_el_conflicto_sigue_siendo_conflicto():
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, (-30, 14, 3), (30, 14, 3))
    b3.agregar_restriccion(b, "eje", [l], eje="x")
    _comando(b, l, k)
    a, c = _extremos(b, l)
    assert _radio(b, k) == pytest.approx(10, abs=1e-9) and a[1] == pytest.approx(c[1], abs=TOL) and a[1] == pytest.approx(10, abs=TOL)
    b = Boceto()
    k = b3.agregar_circulo(b, (0, 0, 0), 10)
    l = b3.agregar_linea(b, (-20, 30, 0), (20, 30, 0))
    b3.agregar_restriccion(b, "fijo", [k, l])
    b3.agregar_restriccion(b, "tangente", [l, k])
    antes = dict(b3.datos(b)["puntos"])
    b3.acomodar_tangente(b, [l, k], {})
    assert b3.datos(b)["puntos"] == antes and not b3.resolver(b, {}).ok


def test_una_receta_guardada_resuelve_como_siempre():
    """Sin pasar por el comando nada cambia: el radio del boceto de `test_linea_y_arco_miden_contra_su_circulo` sigue dando 10,19."""
    b = Boceto()
    k = b3.agregar_arco(b, (10, 0, 0), (0, 10, 0), (-10, 0, 0))
    l = b3.agregar_linea(b, *_uno())
    b3.agregar_restriccion(b, "tangente", [l, k])
    otra = Boceto()
    otra.geo3d = b3.desde_dict(b3.a_dict(b.geo3d))
    assert b3.resolver(otra, {}).ok and _radio(otra, k) == pytest.approx(10.1903, abs=1e-3)


def test_add_constraint_3d_no_cambia_el_radio_y_la_receta_lo_conserva():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    api.llamar(s, "create_parameter", {"name": "largo", "expression": "62 mm"})
    a = api.llamar(s, "draw_arc_3d", {"start": [12, 0, 0], "through": [0, 12, 0], "end": [-12, 0, 0]})["result"]["entity"]
    l = api.llamar(s, "draw_line_3d", {"start": [20, 3, -15], "end": [22, 3, 15]})["result"]["entity"]
    assert api.llamar(s, "add_dimension_3d", {"entities": [l], "value": "largo"})["ok"]

    def medir():
        e = {x["id"]: x for x in api.llamar(s, "get_sketch", {"sketch": "U"})["result"]["entities_3d"]}
        return e[a]["radius"], *e[a]["center"], e[l]["length"], e[l]["start"][2], e[l]["end"][2]
    assert api.llamar(s, "add_constraint_3d", {"type": "tangent", "entities": [l, a]})["ok"]
    assert medir() == pytest.approx((12, 0, 0, 0, 62, 0, 0))
    receta = api.llamar(s, "get_recipe", {})["result"]
    assert api.llamar(s, "apply_recipe", {"recipe": receta})["ok"]
    assert medir() == pytest.approx((12, 0, 0, 0, 62, 0, 0))


def test_add_constraint_3d_con_una_cota_rota_da_un_error_claro():
    """Una receta con una expresión rota: la tangente no se agrega y el error dice qué pasa."""
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    a = api.llamar(s, "draw_arc_3d", {"start": [12, 0, 0], "through": [0, 12, 0], "end": [-12, 0, 0]})["result"]["entity"]
    l = api.llamar(s, "draw_line_3d", {"start": [-30, 14, 3], "end": [30, 12, 2]})["result"]["entity"]
    assert api.llamar(s, "add_dimension_3d", {"entities": [l], "value": 60})["ok"]
    for cota in s.doc.operaciones[-1].boceto.geo3d["cotas"].values():
        cota["expresion"] = "no_existe * 2"
    r = api.llamar(s, "add_constraint_3d", {"type": "tangent", "entities": [l, a]})
    assert r["error_kind"] == "INVALID_EXPRESSION" and "no_existe" in r["mensaje"], r


def test_add_constraint_3d_con_circulo_y_elipse_y_aviso_del_arco():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    k = api.llamar(s, "draw_circle_3d", {"center": [0, 0, 0], "radius": 10, "normal": [0, 0, 1]})["result"]["entity"]
    l = api.llamar(s, "draw_line_3d", {"start": [-20, 14, 2], "end": [20, 12, 1]})["result"]["entity"]
    r = api.llamar(s, "add_constraint_3d", {"type": "tangent", "entities": [l, k]})
    assert r["ok"] and r["result"]["status_3d"] == "under_constrained", r
    a = api.llamar(s, "draw_arc_3d", {"start": [50, 0, 0], "through": [40, 10, 0], "end": [30, 0, 0]})["result"]["entity"]
    api.llamar(s, "add_constraint_3d", {"type": "fix", "entities": [a]})
    l2 = api.llamar(s, "draw_line_3d", {"start": [20, -12, 0], "end": [60, -13, 0]})["result"]["entity"]
    r = api.llamar(s, "add_constraint_3d", {"type": "tangent", "entities": [l2, a]})
    assert r["ok"] and any("fuera del tramo" in x for x in r["avisos"])
    info = api.llamar(s, "get_sketch", {"sketch": "U"})["result"]
    assert info["tangents_off_arc_3d"] == [[l2, a]]
    p = api.llamar(s, "draw_point_3d", {"x": 11, "y": 1, "z": 3})["result"]["point"]
    assert api.llamar(s, "add_constraint_3d", {"type": "coincident", "entities": [p, k]})["ok"]
    assert api.llamar(s, "add_constraint_3d", {"type": "tangent", "entities": [l, l2]})["error_kind"] == "INVALID_CONSTRAINT"


def test_parametrica_de_una_arista():
    f, t0, t1 = curvas3d.parametrica(curvas3d.arista_arco((10, 0, 0), (0, 10, 0), (-10, 0, 0)))
    punto, derivada = f((t0 + t1) / 2)
    assert t1 - t0 == pytest.approx(math.pi)
    assert punto == pytest.approx([0, 10, 0], abs=TOL) and np.linalg.norm(derivada) == pytest.approx(10)


def test_boc82_un_arrastre_resuelve_solo_su_grupo_y_el_resto_no_se_mueve():
    """BOC-82: cada grupo independiente se resuelve aparte. Arrastrar la línea de una tangente no toca la otra, y los
    grados de libertad son la suma de los de cada grupo."""
    b = Boceto()
    pares = []
    for x in (0.0, 100.0):
        k = b3.agregar_circulo(b, (x, 0, 0), 10, (0, 0, 1))
        l = b3.agregar_linea(b, (x - 30, 14, 3), (x + 30, 12, 2))
        b3.agregar_restriccion(b, "tangente", [l, k])
        pares.append((l, k))
    r = b3.resolver(b, {})
    assert r.ok
    solo = Boceto()
    k = b3.agregar_circulo(solo, (0, 0, 0), 10, (0, 0, 1))
    b3.agregar_restriccion(solo, "tangente", [b3.agregar_linea(solo, (-30, 14, 3), (30, 12, 2)), k])
    assert r.gdl == 2 * b3.resolver(solo, {}).gdl
    otro = {p: _p(b, p).copy() for c in pares[1] for p in b3.datos(b)["curvas"][c]["puntos"]}
    g = b3.datos(b)
    extremo = g["curvas"][pares[0][0]]["puntos"][1]
    g["puntos"][extremo] = [g["puntos"][extremo][0] + 2, g["puntos"][extremo][1] + 1, g["puntos"][extremo][2]]
    assert b3.resolver(b, {}).ok
    assert all(np.array_equal(_p(b, p), v) for p, v in otro.items())
    a, c = _extremos(b, pares[0][0])
    assert _dist_recta(_p(b, g["curvas"][pares[0][1]]["puntos"][0]), a, c) == pytest.approx(10, abs=TOL)
