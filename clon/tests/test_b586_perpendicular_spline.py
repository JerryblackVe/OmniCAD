"""B-586: Perpendicular acepta línea–spline como Fusion: la línea gira a 90° de la tangente de la spline, sin tocarla
ni deformar la spline. Línea–arco y línea–círculo siguen rechazadas (Fusion tampoco las acepta)."""
import math

import pytest

from omnicad import api
from omnicad.restricciones import Boceto, ErrorBoceto
from omnicad.restricciones.boceto_geometria import pie_normal
from omnicad.restricciones.solver import resolver

SPLINE = [(0, 0), (20, 10), (40, -5), (60, 5)]
PLANA = [v for q in SPLINE for v in q]


def _escena():
    b = Boceto()
    return b, b.agregar_spline(SPLINE), b.agregar_linea((-30, 20), (-20, 40))


def _medio_y_dir(b, l):
    p, q = (b.coords(i) for i in b.curvas[l].puntos())
    return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), (q[0] - p[0], q[1] - p[1])


@pytest.mark.parametrize("orden", ["linea_spline", "spline_linea"])
def test_b586_la_linea_gira_normal_a_la_spline_sin_moverla(orden):
    b, s, l = _escena()
    medio0, u0 = _medio_y_dir(b, l)
    gdl0 = resolver(b).gdl
    ents = [l, s] if orden == "linea_spline" else [s, l]
    b.girar_a_perpendicular(*ents)
    b.agregar_restriccion("perpendicular", ents)
    r = resolver(b)
    assert r.ok and r.gdl == gdl0 - 1
    medio, u = _medio_y_dir(b, l)
    assert math.dist(medio, medio0) < 1e-6 and math.hypot(*u) == pytest.approx(math.hypot(*u0))   # solo gira
    assert [v for q in b.curvas[s].pts for v in b.coords(q)] == pytest.approx(PLANA, abs=1e-6)             # la spline queda igual
    _t, _c, d = pie_normal(b.primitivas(s)[0], medio)
    assert abs(u[0] * d[0] + u[1] * d[1]) / (math.hypot(*u) * math.hypot(*d)) < 1e-6


@pytest.mark.parametrize("curva", ["arco", "circulo"])
def test_b586_linea_arco_y_linea_circulo_siguen_rechazadas(curva):
    b = Boceto()
    l = b.agregar_linea((0, 0), (10, 0))
    c = b.agregar_arco_centro((20, 0), (25, 0), (20, 5)) if curva == "arco" else b.agregar_circulo((20, 0), 5)
    with pytest.raises(ErrorBoceto, match="no aplica"):
        b.agregar_restriccion("perpendicular", [l, c])


def test_b586_el_comando_de_la_ventana_la_aplica():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui import editor_boceto
    b, s, l = _escena()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    assert lz.aplicar_restriccion("perpendicular", [l, s])
    assert [r.tipo for r in b.restricciones.values()] == ["perpendicular"]
    assert [v for q in b.curvas[s].pts for v in b.coords(q)] == pytest.approx(PLANA, abs=1e-6)


def test_b586_la_api_la_acepta():
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "B"})["ok"]
    sp = api.llamar(s, "draw_spline", {"points": [list(p) for p in SPLINE]})["result"]["entities"][0]["id"]
    ln = api.llamar(s, "draw_line", {"start_x": -30, "start_y": 20, "end_x": -20, "end_y": 40})["result"]["entities"][0]["id"]
    r = api.llamar(s, "add_constraint", {"sketch": "B", "type": "perpendicular", "entities": [ln, sp]})
    assert r["ok"], r
    linea = next(e for e in api.llamar(s, "get_sketch", {})["result"]["entities"] if e["id"] == ln)
    assert linea["length"] == pytest.approx(math.hypot(10, 20), abs=1e-3)       # gira sin estirarse


def test_b586_cambiar_tangente_a_perpendicular_no_deforma_la_spline():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui import editor_boceto
    b, s, l = _escena()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    assert lz.aplicar_restriccion("tangente", [l, s])
    antes = [v for q in b.curvas[s].pts for v in b.coords(q)]
    rid = next(iter(b.restricciones))
    assert lz.reemplazar_restriccion(rid, "perpendicular")                  # menú de la restricción › Cambiar a
    assert [r.tipo for r in b.restricciones.values()] == ["perpendicular"]
    assert [v for q in b.curvas[s].pts for v in b.coords(q)] == pytest.approx(antes, abs=1e-6)


def _contacto(b, l, s):
    """(distancia de la recta de la línea a la spline, |coseno| entre la línea y la tangente ahí)."""
    from omnicad.restricciones.boceto_geometria import dominio, evaluar_primitiva
    p, q = (b.coords(i) for i in b.curvas[l].puntos())
    u = ((q[0] - p[0]) / math.dist(p, q), (q[1] - p[1]) / math.dist(p, q))
    prim = b.primitivas(s)[0]
    t0, t1 = dominio(prim)[:2]
    muestras = [evaluar_primitiva(prim, t0 + (t1 - t0) * k / 4000, 1) for k in range(4001)]
    c, d = min(muestras, key=lambda m: abs((m[0][0] - p[0]) * u[1] - (m[0][1] - p[1]) * u[0]))
    return abs((c[0] - p[0]) * u[1] - (c[1] - p[1]) * u[0]), abs(u[0] * d[0] + u[1] * d[1]) / math.hypot(*d)


def test_b667_dos_arrastres_seguidos_mueven_la_linea_y_no_la_spline():
    b, s, l = _escena()
    b.girar_a_perpendicular(l, s)
    b.agregar_restriccion("perpendicular", [l, s])
    previo = resolver(b)
    pid = b.curvas[l].puntos()[1]
    for destino in ((-5, 45), (10, 40)):             # como el ratón: 20 movimientos y soltar
        x0, y0 = b.coords(pid)
        for k in range(1, 21):
            b.puntos[pid].x, b.puntos[pid].y = x0 + (destino[0] - x0) * k / 20, y0 + (destino[1] - y0) * k / 20
            previo = resolver(b, arrastrado=pid, previo=previo)
            assert [v for q in b.curvas[s].pts for v in b.coords(q)] == pytest.approx(PLANA, abs=1e-3)
        previo = resolver(b, arrastrado=pid)
        assert previo.ok and b.coords(pid) == pytest.approx(destino, abs=1e-6)
        assert [v for q in b.curvas[s].pts for v in b.coords(q)] == pytest.approx(PLANA, abs=1e-3)
        distancia, coseno = _contacto(b, l, s)
        assert distancia < 0.02 and coseno < 1e-3         # la recta sigue pasando por la spline, a 90°
