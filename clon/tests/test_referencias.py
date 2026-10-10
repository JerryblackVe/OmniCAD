# -*- coding: utf-8 -*-
"""Referencias estables a vértices (`nucleo/referencias.py`): la distancia entre firmas de vértice suma la
posición relativa a la caja cuando las dos la tienen, y una referencia a una esquina sobrevive a un cambio
de tamaño del cuerpo (como el `entityToken` de Fusion). Hallazgo de la prueba de uso del 2026-10-09:
`_distancia` tenía un segundo `return` inalcanzable para vértices."""
import inspect

import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs


def test_distancia_de_vertices_sin_y_con_posicion_relativa():
    f = {"geom": "punto", "punto": [0.0, 0.0, 0.0]}
    g = {"geom": "punto", "punto": [3.0, 4.0, 0.0]}
    # Sin "rel": distancia absoluta (5) normalizada por la escala (10).
    assert refs._distancia("vertice", f, g, 10.0) == pytest.approx(0.5)
    # Con "rel" en las dos: |rel| (0,5) + 5 / (4 · 10).
    f_rel = {**f, "rel": [0.0, 0.0, 0.0]}
    g_rel = {**g, "rel": [0.3, 0.4, 0.0]}
    assert refs._distancia("vertice", f_rel, g_rel, 10.0) == pytest.approx(0.5 + 5 / 40)


def test_distancia_de_vertices_sin_codigo_muerto():
    """La rama de vértices devuelve una sola vez: no queda un segundo `return` inalcanzable."""
    fuente = inspect.getsource(refs._distancia)
    rama = fuente.split('if tipo == "vertice":', 1)[1].split('if tipo == "arista":', 1)[0]
    assert rama.count("return") == 1


def test_referencia_a_vertice_sobrevive_al_cambio_de_tamano():
    caja = geo.caja(20, 30, 10)
    assert geo.es_valida(caja)
    esquina = max(refs.subformas(caja, "vertice"), key=lambda v: tuple(refs.punto_de_vertice(v)))
    assert refs.punto_de_vertice(esquina).tolist() == pytest.approx([20, 30, 10])
    ref = refs.referencia("c1", esquina, forma=caja)
    assert ref["tipo"] == "vertice" and ref["firma"]["rel"] == pytest.approx([1, 1, 1])

    grande = geo.caja(40, 60, 20)
    assert geo.es_valida(grande)
    sub = refs.resolver(grande, ref)
    assert sub is not None
    assert refs.punto_de_vertice(sub).tolist() == pytest.approx([40, 60, 20])
