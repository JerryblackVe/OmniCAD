"""SOL-18: sólido envolvente con tubo, orientación y grupo rígido."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _nuevo(s):
    return list(s.doc.estado_final.cuerpos.values())[-1]


def test_caja_orientacion_automatica_es_menor_que_la_del_modelo():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=10, height=10, name="Viga")
    llamar(s, "move_body", body="Viga", rotate=[0, 0, 30], pivot="origin")
    llamar(s, "create_bounding_solid", bodies=["Viga"])
    en_modelo = geo.volumen(_nuevo(s).forma)
    llamar(s, "create_bounding_solid", bodies=["Viga"], orientation="automatic")
    forma = _nuevo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(4000, rel=1e-3)
    assert en_modelo > 5000


def test_tubo_es_un_cilindro_hueco():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=50, name="Eje")
    llamar(s, "create_bounding_solid", bodies=["Eje"], shape="tube", tube_wall=2)
    forma = _nuevo(s).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(math.pi * (10 ** 2 - 8 ** 2) * 50, rel=1e-3)


def test_orientacion_por_dos_ejes_y_por_scu():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=10, height=10, name="Viga")
    llamar(s, "create_bounding_solid", bodies=["Viga"], orientation="z_x", axis_a="X", axis_b="Y")
    assert geo.volumen(_nuevo(s).forma) == pytest.approx(4000, rel=1e-3)
    llamar(s, "create_ucs", origin="O")
    llamar(s, "create_bounding_solid", bodies=["Viga"], shape="cylinder", orientation="ucs", ucs="SCU1")
    assert geo.es_valida(_nuevo(s).forma)
    r = api.llamar(s, "create_bounding_solid", {"bodies": ["Viga"], "orientation": "z_x", "axis_a": "X"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    r = api.llamar(s, "create_bounding_solid", {"bodies": ["Viga"], "shape": "box", "tube_wall": 2})
    assert not r["ok"]


def test_componente_y_grupo_rigido():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="A")
    llamar(s, "create_component", bodies=["A"], name="Pieza")
    llamar(s, "create_bounding_solid", bodies=["A"], component=True, rigid_group=True)
    estado = s.doc.estado_final
    assert len(estado.componentes) == 2
    assert len(estado.grupos_rigidos) == 1 and len(estado.grupos_rigidos[0]) == 2
    llamar(s, "undo")
    assert len(s.doc.estado_final.componentes) == 1
