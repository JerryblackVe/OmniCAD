# -*- coding: utf-8 -*-
"""B-356: `_es_filete` (B-306) tomaba por rosca modelada cualquier cara libre ondulada, y Vaciado y Desfase de caras
quedaban bloqueados en piezas sin rosca. Ahora cuenta las vueltas con signo: una onda no suma, una hélice sí."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo, referencias as refs, solidos_modificar as sm


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def _prisma_ondulado():
    """El caso del auditor: un lado en onda (4 ondas de 2 mm en 40 mm), 30 de ancho y 20 de alto."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY")
    onda = [[x, 2 * math.sin(x * math.pi / 5)] for x in range(0, 41)]
    _llamar(s, "draw_spline", points=onda)
    _llamar(s, "draw_line", start_x=40, start_y=0, end_x=40, end_y=30)
    _llamar(s, "draw_line", start_x=40, start_y=30, end_x=0, end_y=30)
    _llamar(s, "draw_line", start_x=0, start_y=30, end_x=0, end_y=0)
    _llamar(s, "extrude", sketch="Boceto1", profile="all", distance=20)
    return s, next(iter(s.doc.estado_final.cuerpos.values())).forma


def test_la_cara_en_onda_no_es_un_filete_y_se_vacia():
    s, forma = _prisma_ondulado()
    onda = [c for c in geo.caras(forma) if refs.cara_libre(c)]
    assert onda and not any(map(sm._es_filete, onda))
    tapa = max((c for c in geo.caras(forma) if refs.firma_cara(c)["geom"] == "plano"),
               key=lambda c: refs.firma_cara(c)["centro"][2])
    hueco = sm.vaciado(forma, [tapa], espesor_interior=0.5)
    assert 0 < geo.volumen(hueco) < geo.volumen(forma)


def test_el_filete_de_una_rosca_sigue_siendo_filete():
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=20, radius=4, name="Eje")
    _llamar(s, "create_thread", faces="%CYLINDER", body="Eje", thread="M8", modeled=True)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert any(map(sm._es_filete, geo.caras(forma)))


@pytest.mark.parametrize("distancia", [0.5, -0.5])
def test_la_cara_en_onda_se_desfasa(distancia):
    _s, forma = _prisma_ondulado()
    onda = next(c for c in geo.caras(forma) if refs.cara_libre(c))
    assert geo.volumen(sm.desfasar_caras(forma, [onda], distancia)) == pytest.approx(
        geo.volumen(forma) + 40 * 20 * distancia, rel=2e-2)
