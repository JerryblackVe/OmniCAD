"""B-669 (gemelo de B-650): la tangente línea–elipse (2D) y línea–curva del boceto 3D se resolvía con la recta infinita y
el contacto podía caer en la prolongación de la línea. Ahora queda dentro del tramo."""
import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, grados_de_libertad, resolver  # noqa: E402
from omnicad.restricciones import boceto3d as b3  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _contacto_elipse(b, k, l):
    """(error de tangencia en mm, parámetro del contacto en la línea) con la recta infinita: el punto de la elipse con la
    normal de la línea, del lado de la línea."""
    e = b.curvas[k]
    (ox, oy), (mx, my) = b.coords(e.centro), b.coords(e.mayor)
    ra, rb, ang = math.hypot(mx - ox, my - oy), e.radio_menor, math.atan2(my - oy, mx - ox)
    (ax, ay), (bx, by) = (b.coords(p) for p in b.curvas[l].puntos())
    dx, dy = bx - ax, by - ay
    largo = math.hypot(dx, dy)
    nx, ny = -dy / largo, dx / largo
    cs, sn = math.cos(ang), math.sin(ang)
    nu, nv = nx * cs + ny * sn, -nx * sn + ny * cs
    h = math.hypot(ra * nu, rb * nv)
    lado = 1 if (ox - ax) * nx + (oy - ay) * ny < 0 else -1          # la elipse queda del otro lado de la normal
    tu, tv = lado * ra * ra * nu / h, lado * rb * rb * nv / h
    qx, qy = ox + tu * cs - tv * sn, oy + tu * sn + tv * cs
    return abs((qx - ax) * nx + (qy - ay) * ny), ((qx - ax) * dx + (qy - ay) * dy) / (largo * largo)


@pytest.mark.parametrize("destino", [(-60, 20), (-90, 60)])
def test_elipse_arrastrar_el_extremo_libre(destino):
    """El caso del video de B-650 con una elipse: 50 pasos del extremo libre; el contacto no sale del tramo."""
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b = Boceto()
    b.asegurar_referencias([Boceto.ORIGEN])
    k = b.agregar_elipse((0, 0), (75, 0), 55)
    l = b.agregar_linea((-50, 47), (-5, 100))
    v = b.agregar_linea((0, 0), (0, 97.5))
    b.agregar_restriccion("coincidente", [b.curvas[k].centro, Boceto.ORIGEN])
    b.agregar_restriccion("coincidente", [b.curvas[v].p1, Boceto.ORIGEN])
    b.agregar_restriccion("vertical", [v])
    b.agregar_restriccion("coincidente", [b.curvas[l].p2, b.curvas[v].p2])
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    lz.set_herramienta("r_tangente")
    assert lz.aplicar_restriccion("tangente", [l, k])
    lz.set_herramienta("seleccionar")
    x0, y0 = b.coords(b.curvas[l].p1)
    for i in range(1, 51):
        lz._mover_punto(b.curvas[l].p1, (x0 + (destino[0] - x0) * i / 50, y0 + (destino[1] - y0) * i / 50))
        err, t = _contacto_elipse(b, k, l)
        assert err < 1e-3 and -1e-6 <= t <= 1 + 1e-6, (i, err, t)
        assert b.coords(b.curvas[l].p2)[1] < 200


@pytest.mark.parametrize("abajo", [0, -10])
def test_elipse_contacto_justo_en_el_extremo_cuenta_igual(abajo):
    """Con el contacto en el extremo (abajo=0) o adentro del tramo, la tangente saca los mismos grados de libertad."""
    b = Boceto()
    k = b.agregar_elipse((0, 0), (15, 0), 8)
    l = b.agregar_linea((15, abajo), (15, 20))
    sin = grados_de_libertad(b)
    b.agregar_restriccion("tangente", [l, k])
    assert resolver(b).ok
    assert grados_de_libertad(b) == sin - 1
    err, t = _contacto_elipse(b, k, l)
    assert err < 1e-9 and t == pytest.approx(-abajo / (20 - abajo), abs=1e-9)


@pytest.mark.parametrize("curva", ["circulo", "elipse"])
@pytest.mark.parametrize("linea", [((12, 5, 0), (30, 20, 0)), ((-30, 14, 3), (-12, 12, 2))])
def test_3d_el_contacto_queda_en_el_tramo(curva, linea):
    """Boceto 3D: la línea queda tangente y el contacto, entre sus extremos (antes caía en t = −0,55 o 1,95)."""
    b = Boceto()
    if curva == "circulo":
        k = b3.agregar_circulo(b, (0, 0, 0), 10, (0, 0, 1))
    else:
        k = b3.agregar_elipse(b, (0, 0, 0), (15, 0, 0), 8, (0, 0, 1))
    l = b3.agregar_linea(b, *linea)
    b3.agregar_restriccion(b, "tangente", [l, k])
    r = b3.resolver(b, {})
    assert r.ok, r.mensaje
    g = b3.datos(b)
    p1, p2 = (np.array(g["puntos"][p], float) for p in g["curvas"][l]["puntos"])
    cur = b3.curva_parametrica(b, k)
    pts = np.array([cur.f(t)[0] for t in np.linspace(0, math.tau, 20000)])
    d = p2 - p1
    dist = np.linalg.norm(np.cross(pts - p1, d / np.linalg.norm(d)), axis=1)
    q = pts[np.argmin(dist)]
    assert dist.min() < 1e-2
    assert -1e-3 <= float((q - p1) @ d / (d @ d)) <= 1 + 1e-3
