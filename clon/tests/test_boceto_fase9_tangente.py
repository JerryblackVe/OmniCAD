"""BOC-9: tangente al empezar una línea sobre un círculo o arco."""
import math

import pytest

from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones.inferencia import _tangencias, inferir


@pytest.mark.parametrize("tipo", ["circulo", "arco"])
@pytest.mark.parametrize("signo", [-1, 1])
def test_base_sobre_curva_infiere_tangente_en_ambos_sentidos(tipo, signo):
    b = Boceto()
    cid = (b.agregar_circulo((0, 0), 10) if tipo == "circulo"
           else b.agregar_arco_centro((0, 0), (10, 0), (0, 10)))
    base = (10, 0)
    prim, = b.primitivas(cid)
    assert list(_tangencias(prim, base)) == [pytest.approx(base, abs=1e-9)]
    antes = b.a_dict()

    r = inferir(b, (10.05, signo * 7), 0.1, base)

    assert r is not None and r.tipo == "tangente"
    assert r.xy == pytest.approx((10, signo * 7), abs=1e-9)
    assert r.objetivo == cid and r.restriccion == ("tangente", cid)
    assert r.guias == [(base, r.xy)]
    direccion = tuple((r.xy[i] - base[i]) / math.dist(base, r.xy) for i in range(2))
    assert direccion == pytest.approx((0, signo), abs=1e-9)
    assert b.a_dict() == antes


@pytest.mark.parametrize("base", [(0, 0), (3, 4), (9.99, 0)])
def test_base_interior_no_tiene_contactos_tangentes(base):
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 10)
    prim, = b.primitivas(cid)
    assert list(_tangencias(prim, base)) == []
    r = inferir(b, (6, 8), 0.1, base)
    assert r.tipo == "sobre_curva"


def test_base_exterior_conserva_las_dos_tangentes():
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 10)
    base = (20, 0)
    prim, = b.primitivas(cid)
    contactos = list(_tangencias(prim, base))
    assert len(contactos) == 2
    for contacto, signo in zip(contactos, (-1, 1), strict=True):
        assert contacto == pytest.approx((5, signo * math.sqrt(75)), abs=1e-9)
        assert math.hypot(*contacto) == pytest.approx(10, abs=1e-9)
        assert sum((contacto[i] - base[i]) * contacto[i] for i in range(2)) == pytest.approx(0, abs=1e-9)
        r = inferir(b, contacto, 0.1, base)
        assert r.tipo == "tangente" and r.xy == pytest.approx(contacto, abs=1e-9)


@pytest.mark.parametrize("desvio", [-5e-10, 5e-10])
def test_base_sobre_circulo_admite_el_redondeo_numerico(desvio):
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 10)
    base = (10 + desvio, 0)
    prim, = b.primitivas(cid)
    assert list(_tangencias(prim, base)) == [base]
    r = inferir(b, (10.05, 7), 0.1, base)
    assert r.tipo == "tangente"
    assert r.xy == pytest.approx((base[0], 7), abs=1e-9)


def test_base_en_la_prolongacion_del_arco_no_infiere_tangente():
    b = Boceto()
    cid = b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    base = (0, -10)
    prim, = b.primitivas(cid)
    assert list(_tangencias(prim, base)) == []
    r = inferir(b, (7, -10), 0.1, base)
    assert r.tipo == "horizontal"


@pytest.mark.parametrize("cursor, tolerancia_angular", [
    ((11, 7), math.radians(3)), ((10.05, 7), 0.001), ((10, 0), math.radians(3)),
])
def test_tangente_desde_la_curva_respeta_distancia_angulo_y_longitud(cursor, tolerancia_angular):
    b = Boceto()
    b.agregar_circulo((0, 0), 10)
    r = inferir(b, cursor, 0.1, (10, 0), angulo_tol=tolerancia_angular)
    assert r is None or r.tipo != "tangente"


def test_tangente_oblicua_desde_la_curva_es_aplicable_sin_mover_la_linea():
    b = Boceto()
    cid = b.agregar_circulo((3, 4), 10)
    base, cursor = (9, 12), (5.03, 15.04)
    b.agregar_restriccion("fijo", [cid])
    r = inferir(b, cursor, 0.1, base)
    assert r is not None and r.tipo == "tangente"
    assert r.xy == pytest.approx((5, 15), abs=1e-9)
    assert 6 * (r.xy[0] - base[0]) + 8 * (r.xy[1] - base[1]) == pytest.approx(0, abs=1e-9)
    inicio = b.agregar_punto(*base)
    b.agregar_restriccion("fijo", [inicio])
    linea = b.agregar_linea(inicio, r.xy)
    b.agregar_restriccion(r.restriccion[0], [linea, r.objetivo])

    resultado = resolver(b)

    assert resultado.ok, resultado.descripcion()
    assert b.coords(b.curvas[linea].p2) == pytest.approx((5, 15), abs=1e-7)
