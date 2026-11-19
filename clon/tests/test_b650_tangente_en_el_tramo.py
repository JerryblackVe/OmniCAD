"""B-650 y B-651: la tangente línea–círculo se resolvía con la recta infinita; el contacto se iba a la prolongación y,
al arrastrar, el extremo compartido con la vertical se escapaba (y → 10⁷ mm) o la línea cruzaba el círculo. Ahora el
contacto queda dentro del tramo de la línea (como B-564 con las splines). Caso del video de Gerardo del 19/11."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, grados_de_libertad, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402


def _video():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b = Boceto()
    b.asegurar_referencias([Boceto.ORIGEN])
    k = b.agregar_circulo((0, 0), 60)
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
    lz.aplicar_cambio(lambda: b.agregar_cota("diametro", [k], "119.73"))
    lz.set_herramienta("seleccionar")
    return b, lz, k, l


def _contacto(b, k, l):
    """(error de tangencia en mm, parámetro del contacto en la línea: 0..1 = dentro del tramo)."""
    (ax, ay), (bx, by) = (b.coords(p) for p in b.curvas[l].puntos())
    ox, oy = b.coords(b.curvas[k].centro)
    dx, dy = bx - ax, by - ay
    n2 = dx * dx + dy * dy
    dist = abs(dx * (oy - ay) - dy * (ox - ax)) / math.sqrt(n2)
    return abs(dist - b.curvas[k].radio), ((ox - ax) * dx + (oy - ay) * dy) / n2


def _revisar(b, k, l):
    err, t = _contacto(b, k, l)
    alto = b.coords(b.curvas[l].p2)[1]
    assert err < 1e-3 and -1e-6 <= t <= 1 + 1e-6, (err, t)
    assert alto < 200, alto                                  # antes se iba a millones de mm


@pytest.mark.parametrize("destino", [(-60, 20), (-30, 70), (-80, 60), (-20, 30)])
def test_arrastrar_el_extremo_libre(destino):
    """B-651: 50 pasos del extremo libre; la tangente se sostiene en el tramo y el extremo compartido no se escapa."""
    b, lz, k, l = _video()
    x0, y0 = b.coords(b.curvas[l].p1)
    for i in range(1, 51):
        lz._mover_punto(b.curvas[l].p1, (x0 + (destino[0] - x0) * i / 50, y0 + (destino[1] - y0) * i / 50))
        _revisar(b, k, l)


@pytest.mark.parametrize("paso", [(-1.2, 0), (-0.9, -0.6), (0.9, 0.6), (-0.6, 0.9)])
def test_arrastrar_la_linea(paso):
    """B-650: 50 pasos arrastrando la línea; no cruza el círculo ni se escapa."""
    b, lz, k, l = _video()
    (ax, ay), (bx, by) = (b.coords(p) for p in b.curvas[l].puntos())
    g = (ax + (bx - ax) * 0.3, ay + (by - ay) * 0.3)
    lz._empezar_arrastre(l, lz.a_px(*g))
    for i in range(1, 51):
        lz._mover_curva(l, lz._arrastre[2], (g[0] + paso[0] * i, g[1] + paso[1] * i))
        _revisar(b, k, l)


@pytest.mark.parametrize("abajo", [0, -10])
def test_contacto_justo_en_el_extremo_cuenta_un_grado(abajo):
    """El contacto en el extremo (abajo=0) o adentro del tramo saca un grado de libertad: 3 del círculo + 4 de la línea − 1."""
    b = Boceto()
    k = b.agregar_circulo((0, 0), 10)
    l = b.agregar_linea((10, abajo), (10, 20))
    b.agregar_restriccion("tangente", [l, k])
    assert resolver(b).ok
    assert grados_de_libertad(b) == 6
    assert _contacto(b, k, l)[0] < 1e-9 and b.coords(b.curvas[l].p1) == pytest.approx((10, abajo))
