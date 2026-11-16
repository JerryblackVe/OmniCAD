# -*- coding: utf-8 -*-
"""B-598: Extruir «Hasta la cara seleccionada» + Unir buscaba qué cuerpo toca la herramienta midiendo el cuerpo entero
(15 letras B-spline contra un cuerpo de 353 caras: 108 s de 115). Ahora alcanza con que toque la cara límite; si esa
medida falla, se mide el cuerpo como siempre."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.geometria import TopAbs_COMPOUND, TopAbs_FACE, TopAbs_SOLID


def _llamar(sesion, herramienta, **argumentos):
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"], resultado
    return resultado


def _unir_hasta_la_cara_de_abajo():
    """Caja con empalmes (un cuerpo ya modificado) y un cilindro que sube desde z=0 hasta su cara de abajo (z=5)."""
    s = api.Sesion()
    _llamar(s, "create_box", length=20, width=20, height=10, z=5)
    _llamar(s, "fillet", edges="|Z", radius=2)
    _llamar(s, "create_sketch", plane="XY", name="B1")
    _llamar(s, "draw_circle", center_x=10, center_y=10, radius=3)
    _llamar(s, "extrude", sketch="B1", profile=0, extent="to_object", to="<Z", operation="join")
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    return geo.volumen_exacto(cuerpo.forma)


def _esperado():
    caja = 20 * 20 * 10 - 4 * (2 * 2 - math.pi * 2 * 2 / 4) * 10
    return caja + math.pi * 3 * 3 * 5


def test_b598_la_cara_limite_alcanza_para_saber_que_cuerpo_unir(monkeypatch):
    medidas, original = [], geo.se_tocan
    monkeypatch.setattr(geo, "se_tocan", lambda a, b, *x: medidas.append(a.ShapeType()) or original(a, b, *x))
    assert _unir_hasta_la_cara_de_abajo() == pytest.approx(_esperado(), rel=1e-6)
    assert TopAbs_FACE in medidas and not {TopAbs_SOLID, TopAbs_COMPOUND} & set(medidas)   # la cara, nunca el cuerpo entero


def test_b598_si_la_cara_limite_falla_se_mide_el_cuerpo_como_siempre(monkeypatch):
    original = geo.se_tocan

    def falla_con_caras(a, b, *x):
        if a.ShapeType() == TopAbs_FACE:
            raise RuntimeError("vía rápida rota")
        return original(a, b, *x)
    monkeypatch.setattr(geo, "se_tocan", falla_con_caras)
    assert _unir_hasta_la_cara_de_abajo() == pytest.approx(_esperado(), rel=1e-6)
