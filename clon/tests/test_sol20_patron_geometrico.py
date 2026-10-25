"""SOL-20: patrón geométrico sobre una cara (distribuciones, gradiente, perímetro y operaciones)."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo

PLACA = 60 * 60 * 6


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _placa():
    s = api.Sesion()
    llamar(s, "create_box", length=60, width=60, height=6, name="Placa")
    return s


def _volumen(s):
    f = s.cuerpo("Placa").forma
    assert geo.es_valida(f)
    return geo.volumen(f)


def test_rectangular_corta_esferas_y_limpia_el_perimetro():
    s = _placa()
    llamar(s, "create_geometric_pattern", faces=">Z", size1=4, size2=4, distance=10)
    # 5 x 5 esferas de diámetro 4 centradas en la cara: cada una saca media esfera
    assert PLACA - _volumen(s) == pytest.approx(25 * 2 / 3 * math.pi * 8, rel=1e-3)


def test_sin_limpiar_el_perimetro_entran_las_del_borde():
    a, b = _placa(), _placa()
    llamar(a, "create_geometric_pattern", faces=">Z", size1=4, size2=4, distance=10)
    llamar(b, "create_geometric_pattern", faces=">Z", size1=4, size2=4, distance=10, clear_perimeter=False)
    assert PLACA - _volumen(b) > PLACA - _volumen(a)


def test_gradiente_de_tamano_entre_los_limites():
    chico, grande, gradiente = _placa(), _placa(), _placa()
    for s, (a, b) in ((chico, (2, 2)), (grande, (6, 6)), (gradiente, (2, 6))):
        llamar(s, "create_geometric_pattern", faces=">Z", size1=a, size2=b, distance=12, clear_perimeter=False)
    assert PLACA - _volumen(chico) < PLACA - _volumen(gradiente) < PLACA - _volumen(grande)


@pytest.mark.parametrize("distribucion", ["triangular", "hexagonal", "circular", "radial"])
def test_otras_distribuciones(distribucion):
    s = _placa()
    llamar(s, "create_geometric_pattern", faces=">Z", size1=3, size2=3, distribution=distribucion, distance=9,
           radial_distance=9, spokes=6)
    assert 0 < PLACA - _volumen(s) < PLACA / 2


def test_hexagonal_tiene_menos_objetos_que_triangular():
    t, h = _placa(), _placa()
    llamar(t, "create_geometric_pattern", faces=">Z", size1=3, size2=3, distribution="triangular", distance=9)
    llamar(h, "create_geometric_pattern", faces=">Z", size1=3, size2=3, distribution="hexagonal", distance=9)
    assert PLACA - _volumen(h) < PLACA - _volumen(t)


def test_extension_reparte_la_cantidad_pedida():
    s = _placa()
    llamar(s, "create_geometric_pattern", faces=">Z", size1=2, size2=2, spacing_type="extent", quantity_u=4,
           quantity_v=3, clear_perimeter=False)
    assert PLACA - _volumen(s) > 0


def test_unir_cilindros_suma_volumen_y_cajas_y_a_medida():
    s = _placa()
    llamar(s, "create_geometric_pattern", faces=">Z", object_type="cylinder", size1=4, size2=4, distance=15, operation="join")
    assert _volumen(s) > PLACA
    c = _placa()
    llamar(c, "create_box", length=5, width=5, height=5, name="Modulo", x=200)
    llamar(c, "create_geometric_pattern", faces=">Z", body="Placa", object_type="custom", custom_body="Modulo", size1=4, size2=4,
           distance=15, operation="new_body")
    assert len(c.doc.estado_final.cuerpos) > 2
    k = _placa()
    llamar(k, "create_geometric_pattern", faces=">Z", object_type="box", size1=4, size2=4, distance=15)
    assert 0 < PLACA - _volumen(k)


def test_errores():
    s = _placa()
    for args in ({"faces": ">Z", "distance": 0},
                 {"faces": ">Z", "object_type": "custom"},
                 {"faces": ">Z", "distance": 0.2, "size1": 0.1, "size2": 0.1},          # más de 2000 objetos
                 {"faces": ">Z", "size1": 0},
                 {"faces": ">Z", "size1": 500, "size2": 500}):                           # no entra ninguno
        r = api.llamar(s, "create_geometric_pattern", {"body": "Placa", **args})
        assert not r["ok"], args


def _base_p(**extra):
    p = dict(separacion="incremento", distancia=10.0, cantidad_u=3, cantidad_v=3, distancia_radial=10.0, rayos=8,
             alineacion_u="centro", desfase_u=0.0, alineacion_v="medio", desfase_v=0.0)
    p.update(extra)
    return p


def test_hexagonal_es_un_panal_cada_vertice_interior_tiene_tres_vecinos():
    import numpy as np
    from omnicad.nucleo import patron_geometrico as pg
    pts = np.array(pg._puntos("hexagonal", -100, 100, -100, 100, _base_p()))
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
    vecinos = (np.abs(d - 10.0) < 1e-6).sum(axis=1)
    interior = (np.abs(pts) < 70).all(axis=1)
    assert interior.sum() > 50 and (vecinos[interior] == 3).all()


def test_una_distancia_diminuta_se_rechaza_antes_de_enumerar():
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import patron_geometrico as pg
    for dist in ("rectangular", "triangular", "hexagonal", "circular", "radial"):
        with pytest.raises(geo.ErrorGeometria, match="muchísimos"):
            pg._puntos(dist, 0, 60, 0, 60, _base_p(distancia=0.003, distancia_radial=0.003))
