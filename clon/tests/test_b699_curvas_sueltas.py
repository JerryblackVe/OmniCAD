"""B-699: una curva suelta dentro de una región (sin cerrar nada) no entra en el perfil, como en Fusion. El Splitter de
OpenCascade la dejaba en la cara como arista interna y al extruir quedaba una pared adentro: «cuerpo inválido»."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import perfiles

PLANO = geo.Plano("XY")
CUADRADO = [("linea", 1, (0., 0.), (10., 0.)), ("linea", 2, (10., 0.), (10., 10.)), ("linea", 3, (10., 10.), (0., 10.)),
            ("linea", 4, (0., 10.), (0., 0.))]
# galería de Fusion 138071_f8d5a493: el arco toca el lado en su extremo y sigue 0,235 mm hacia adentro (dos colitas)
GALERIA = [("arco", 1, (7.5, 7.970000000000001), 7.499999999999998, -0.03133846266152215, -3.1102541909282713),
           ("circulo", 5, (7.499999999999998, 7.910000000000002), 2.56),
           ("linea", 9, (0.0, 0.0), (15.0, 0.0)), ("linea", 12, (15.0, 0.0), (15.0, 7.9700000000000015)),
           ("linea", 14, (0.0, 7.9700000000000015), (0.0, 0.0))]


@pytest.mark.parametrize("geometria, area", [
    (CUADRADO + [("linea", 5, (0., 5.), (5., 5.))], 100.0),            # recta suelta desde un lado
    (CUADRADO + [("linea", 5, (3., 5.), (6., 5.))], 100.0),            # recta suelta en el medio
    (CUADRADO + [("arco", 5, (0., 5.), 3., -1.5, 1.5)], 100.0),        # arco suelto desde un lado
    (GALERIA, 187.319),
])
def test_curva_suelta_no_rompe_la_extrusion(geometria, area):
    p = max(perfiles._detectar_occ(geometria, PLANO), key=lambda p: p.area)
    assert p.area == pytest.approx(area, abs=1e-3)
    assert geo.es_valida(p.cara)
    solido = geo.extruir([p.cara], (0, 0, 1), 5.0)
    assert geo.es_valida(solido)
    assert geo.volumen(solido) == pytest.approx(5 * area, abs=5e-3)
