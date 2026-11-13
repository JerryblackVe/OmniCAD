"""B-348: los perfiles vecinos teselan la extrusión inclinada sin cuñas ni solapes."""
import math

import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _ok(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta
    assert not any("partido" in aviso for aviso in respuesta.get("avisos", [])), respuesta
    return respuesta["result"]


@pytest.mark.parametrize("angulo", [-5, 5])
@pytest.mark.parametrize("direccion", ["one_side", "two_sides", "symmetric"])
def test_b348_los_tres_perfiles_conservan_volumen_orden_y_union(angulo, direccion):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch")
    _ok(sesion, "draw_rectangle", x1=0, y1=0, x2=60, y2=40)
    _ok(sesion, "draw_circle", radius=8)
    boceto = sesion.doc.estado_final.bocetos["op1"]
    perfiles = [p.cara for p in boceto.perfiles]
    assert len(perfiles) == 3
    region = geo.caras(geo.unificar_caras(geo.unir_todos(perfiles)))
    referencia = sc.extruir_avanzado(
        region, boceto.plano.normal, distancia1=10, distancia2=6,
        direccion={"one_side": "un_lado", "two_sides": "dos_lados", "symmetric": "simetrica"}[direccion],
        medida_simetrica="total", conicidad1=angulo, conicidad2=-angulo)
    esperado = geo.volumen_exacto(referencia)
    if direccion == "one_side":
        assert esperado == pytest.approx({-5: 24546.64300661411, 5: 26486.399718552773}[angulo], rel=1e-9)

    resultado = _ok(sesion, "extrude", sketch="Boceto1", profile="all", distance=10,
                    direction=direccion, distance2=6, taper_angle=angulo, taper_angle2=-angulo)
    ids = [c["id"] for c in resultado["bodies_created"]]
    assert ids == ["op2.c1", "op2.c2", "op2.c3"]
    cuerpos = [sesion.cuerpo(cid).forma for cid in ids]
    assert sum(geo.volumen_exacto(c) for c in cuerpos) == pytest.approx(esperado, rel=1e-8)
    for perfil, cuerpo in zip(perfiles, cuerpos, strict=True):
        assert geo.es_valida(cuerpo) and len(geo.solidos(cuerpo)) == 1
        base = geo.booleano(cuerpo, perfil, "intersecar")
        assert geo.area(base) == pytest.approx(geo.area(perfil), rel=1e-8)
    for i, cuerpo in enumerate(cuerpos):
        for otro in cuerpos[i + 1:]:
            comun = geo.booleano(cuerpo, otro, "intersecar")
            assert geo.volumen_exacto(comun) == pytest.approx(0, abs=1e-6)
            for cara in geo.caras(comun):
                superficie = BRepAdaptor_Surface(cara)
                if superficie.GetType() == GeomAbs_Plane:
                    assert abs(superficie.Plane().Axis().Direction().Z()) < 1e-8
                else:
                    assert superficie.GetType() == GeomAbs_Cylinder
                    assert abs(superficie.Cylinder().Axis().Direction().Z()) == pytest.approx(1)

    _ok(sesion, "boolean_operation", target=ids[0], tools=[ids[1]])
    _ok(sesion, "boolean_operation", target=ids[0], tools=[ids[2]])
    unidos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(unidos) == 1
    forma = unidos[0].forma
    assert len(geo.solidos(forma)) == 1 and geo.es_valida(forma)
    assert geo._aristas_defectuosas(forma) == (0, 0)
    assert geo.volumen_exacto(forma) == pytest.approx(esperado, rel=1e-8)


@pytest.mark.parametrize("angulo", [-5, 5])
@pytest.mark.parametrize("separados", [False, True])
def test_b348_un_perfil_solo_y_perfiles_sin_vecinos_no_cambian(angulo, separados):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch")
    _ok(sesion, "draw_circle", radius=8)
    if separados:
        _ok(sesion, "draw_circle", center_x=40, radius=8)
    resultado = _ok(sesion, "extrude", sketch="Boceto1", profile="all", distance=10, taper_angle=angulo)
    pendiente = math.tan(math.radians(angulo))
    esperado = math.pi * (8 ** 2 * 10 + 8 * pendiente * 10 ** 2 + pendiente ** 2 * 10 ** 3 / 3)
    assert len(resultado["bodies_created"]) == (2 if separados else 1)
    for cuerpo in resultado["bodies_created"]:
        forma = sesion.cuerpo(cuerpo["id"]).forma
        assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
        assert geo.volumen_exacto(forma) == pytest.approx(esperado, rel=1e-9)
