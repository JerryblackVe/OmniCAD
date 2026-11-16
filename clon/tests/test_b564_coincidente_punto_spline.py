"""B-564: Coincidente punto + spline dejaba el punto a 2,29 mm de la spline, en la prolongación fuera del tramo (el
parámetro del contacto quedaba libre y la spline se evaluaba extrapolada). Ahora el punto queda sobre la spline."""
import pytest

from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones.boceto import mas_cercano

FIT = [(15, 35), (25, 50), (35, 32), (45, 46)]


def _distancia(b, s, q):
    return mas_cercano(b.primitivas(s)[0], q)[1]           # el más cercano DENTRO del tramo


@pytest.mark.parametrize("orden", [0, 1])
@pytest.mark.parametrize("fijo", [False, True])
def test_el_punto_queda_sobre_el_tramo(orden, fijo):
    b = Boceto()
    s = b.agregar_spline(FIT)
    p = b.agregar_punto(60, 40)
    if fijo:
        b.agregar_restriccion("fijo", [p])
    b.agregar_restriccion("coincidente", [p, s] if orden == 0 else [s, p])
    assert resolver(b).ok
    assert _distancia(b, s, b.coords(p)) < 1e-6


def test_gemelo_tangente_linea_spline_toca_el_tramo():
    """La tangente línea–spline usaba el mismo parámetro libre: quedaba tangente a la prolongación (0,68 mm del tramo)."""
    b = Boceto()
    s = b.agregar_spline(FIT)
    l = b.agregar_linea((50, 60), (70, 40))
    b.agregar_restriccion("tangente", [l, s])
    assert resolver(b).ok
    (x1, y1), (x2, y2) = b.coords(b.curvas[l].p1), b.coords(b.curvas[l].p2)
    prim = b.primitivas(s)[0]
    ux, uy = x2 - x1, y2 - y1
    largo = (ux * ux + uy * uy) ** 0.5
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva
    a, z, _ = dominio(prim)
    dist = min(abs(ux * (q[1] - y1) - uy * (q[0] - x1)) / largo
               for q in (evaluar_primitiva(prim, a + (z - a) * k / 4000)[0] for k in range(4001)))
    assert dist < 1e-3
