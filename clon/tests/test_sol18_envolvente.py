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


def test_origen_del_componente_centro_y_esquina():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=10, x=100, name="A")        # x de 90 a 110
    r = api.llamar(s, "create_bounding_solid", {"bodies": ["A"], "origin": "center"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"                  # sin componente no hay origen
    llamar(s, "create_bounding_solid", bodies=["A"], component=True, origin="center")
    envolvente = next(c for c in llamar(s, "get_assembly")["components"] if c.get("origin"))
    assert envolvente["origin"] == pytest.approx([100, 0, 5], abs=1e-3)
    llamar(s, "create_bounding_solid", bodies=["A"], component=True, origin="corner")
    esquinas = [c["origin"] for c in llamar(s, "get_assembly")["components"] if c.get("origin")]
    assert esquinas[-1] == pytest.approx([90, -5, 0], abs=1e-3)
    caja = geo.caja_envolvente(_nuevo(s).forma)
    assert caja[0] == pytest.approx((90, -5, 0), abs=1e-3) and geo.es_valida(_nuevo(s).forma)


def test_pared_del_tubo_acepta_un_parametro_y_vacia_sigue_andando():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=50, name="Eje")
    llamar(s, "create_parameter", name="pared", expression="2 mm")
    llamar(s, "create_bounding_solid", bodies=["Eje"], shape="tube", tube_wall="pared")
    assert geo.volumen(_nuevo(s).forma) == pytest.approx(math.pi * (10 ** 2 - 8 ** 2) * 50, rel=1e-3)
    llamar(s, "set_parameter", name="pared", expression="3 mm")                   # el parámetro llega al paso
    assert geo.volumen(_nuevo(s).forma) == pytest.approx(math.pi * (10 ** 2 - 7 ** 2) * 50, rel=1e-3)
    assert "pared" in llamar(s, "get_parameters")["parameters"][0]["name"]
    llamar(s, "create_bounding_solid", bodies=["Eje"], shape="tube")              # espesor_tubo "" = la décima parte
    assert geo.volumen(_nuevo(s).forma) == pytest.approx(math.pi * (10 ** 2 - 9 ** 2) * 50, rel=1e-3)


def test_esquina_y_centro_se_miden_en_el_marco_de_la_orientacion():
    """Una viga girada 45° en Z con orientación automática: la esquina es un vértice del sólido, no la del mundo."""
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=10, height=10, name="Viga")
    llamar(s, "move_body", body="Viga", rotate=[0, 0, 45], pivot="origin")
    llamar(s, "create_bounding_solid", bodies=["Viga"], orientation="automatic", component=True, origin="corner")
    esquina = next(c["origin"] for c in llamar(s, "get_assembly")["components"] if c.get("origin"))
    forma = _nuevo(s).forma
    from omnicad.nucleo import referencias as refs
    vertices = [geo.caja_envolvente(v)[0] for v in refs.subformas(forma, "vertice")]
    assert min(math.dist(esquina, v) for v in vertices) < 1e-3
    llamar(s, "create_bounding_solid", bodies=["Viga"], orientation="automatic", component=True, origin="center")
    centro = [c["origin"] for c in llamar(s, "get_assembly")["components"] if c.get("origin")][-1]
    caja = geo.caja_envolvente(_nuevo(s).forma)
    assert centro == pytest.approx([(caja[0][i] + caja[1][i]) / 2 for i in range(3)], abs=1e-3)


def test_origen_tambien_con_grupo_rigido_y_la_copia_del_componente_lo_conserva():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=10, x=100, name="A")
    llamar(s, "create_bounding_solid", bodies=["A"], rigid_group=True, origin="corner")
    assert any(c.get("origin") for c in llamar(s, "get_assembly")["components"])
    llamar(s, "rectangular_pattern", components=[next(k for k, c in s.doc.estado_final.componentes.items()
                                                       if c.get("origen"))], x_count=2, x_spacing=50)
    assert sum(1 for c in llamar(s, "get_assembly")["components"] if c.get("origin")) == 2
