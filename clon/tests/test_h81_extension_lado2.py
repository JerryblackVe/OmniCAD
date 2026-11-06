"""H-81: cada lado de Extruir tiene su propio límite, también en la previa."""
import copy

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion


def _ok(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _sesion():
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_rectangle", sketch="Perfil", x1=0, y1=0, x2=20, y2=10)
    _ok(sesion, "create_box", length=30, width=20, height=8, x=-5, y=-5, z=-20, anchor="corner", name="Tope")
    _ok(sesion, "create_construction_plane", plane="XY", offset=-12, name="Limite")
    return sesion


@pytest.mark.parametrize("via", ["operacion", "api", "run_operation"])
@pytest.mark.parametrize("extension", ["objeto", "todo"])
@pytest.mark.parametrize("invertir", [False, True])
def test_h81_limite_independiente(via, extension, invertir):
    sesion = _sesion()
    # Invertir intercambia los lados; el inicio sigue siendo el mismo.
    if invertir:
        _ok(sesion, "create_construction_plane", plane="XY", offset=12, name="Limite2")
    limite = "Limite2" if invertir else "Limite"
    boceto = sesion.paso("Perfil").id
    perfil = OpExtrusion.referencia_perfil(sesion.doc.estado_final.bocetos[boceto].perfiles[0])
    params = dict(boceto=boceto, perfiles=[perfil], direccion="dos_lados", distancia="5", distancia2="3",
                  extension2=extension, invertir=invertir)
    if extension == "objeto":
        params["hasta2"] = {"tipo": "plano", "id": sesion.paso(limite).id}
    elif invertir:
        _ok(sesion, "create_box", length=30, width=20, height=8, x=-5, y=-5, z=12, anchor="corner", name="Tope2")
    if via == "api":
        opciones = {"side2_to": limite} if extension == "objeto" else {}
        salida = _ok(sesion, "extrude", sketch="Perfil", direction="two_sides", distance=5, distance2=3,
                     side2_extent="to_object" if extension == "objeto" else "all", reverse=invertir, **opciones)
        forma = sesion.cuerpo(salida["bodies_created"][0]["id"]).forma
    elif via == "run_operation":
        _ok(sesion, "run_operation", type="extrusion", params=params)
        op = sesion.doc.operaciones[-1]
        forma = sesion.doc.estado_final.cuerpos[f"{op.id}.c1"].forma
    else:
        op = OpExtrusion(sesion.doc.nuevo_id(), **params)
        anterior = copy.deepcopy(op.p)
        previa, _ = sesion.doc.previsualizar(op, en_vivo=True)
        res = sesion.doc.agregar(op)
        assert res.estado == "ok", res.mensaje
        forma = sesion.doc.estado_final.cuerpos[f"{op.id}.c1"].forma
        assert np.allclose(geo.caja_envolvente(previa.cuerpos[f"{op.id}.c1"].forma), geo.caja_envolvente(forma))
        assert op.p == anterior
        if extension == "objeto":
            assert sesion.paso(limite).id in op.dependencias()
    assert geo.es_valida(forma)
    lo, hi = geo.caja_envolvente(forma)
    if extension == "objeto":
        assert (lo[2], hi[2]) == pytest.approx((-5, 12) if invertir else (-12, 5), abs=1e-6)
        assert geo.volumen_exacto(forma) == pytest.approx(3400)
    else:
        assert (lo[2] == pytest.approx(-5, abs=1e-6) and hi[2] > 20) if invertir else (
            lo[2] < -20 and hi[2] == pytest.approx(5, abs=1e-6))


@pytest.mark.parametrize("via", ["operacion", "api", "run_operation"])
def test_h81_objeto_sin_limite_da_error(via):
    sesion = _sesion()
    if via == "api":
        res = api.llamar(sesion, "extrude", dict(sketch="Perfil", direction="two_sides", side2_extent="to_object"))
        assert not res["ok"] and "side2_to" in res["mensaje"], res
    else:
        boceto = sesion.paso("Perfil").id
        perfil = OpExtrusion.referencia_perfil(sesion.doc.estado_final.bocetos[boceto].perfiles[0])
        params = dict(boceto=boceto, perfiles=[perfil], direccion="dos_lados", extension2="objeto")
        if via == "run_operation":
            res = api.llamar(sesion, "run_operation", dict(type="extrusion", params=params))
            assert not res["ok"] and "lado 2" in res["mensaje"], res
        else:
            res = sesion.doc.agregar(OpExtrusion(sesion.doc.nuevo_id(), **params))
            assert res.estado == "error" and "lado 2" in res.mensaje


@pytest.mark.parametrize("extension1", ["distance", "to_object", "all"])
@pytest.mark.parametrize("extension2", ["distance", "to_object", "all"])
def test_h81_combinaciones_con_inicio_desfasado(extension1, extension2):
    sesion = _sesion()
    _ok(sesion, "create_construction_plane", plane="XY", offset=15, name="Superior")
    _ok(sesion, "create_box", length=30, width=20, height=8, z=20, name="Techo")
    opciones = {"to": "Superior"} if extension1 == "to_object" else {}
    if extension2 == "to_object":
        opciones["side2_to"] = "Limite"
    salida = _ok(sesion, "extrude", sketch="Perfil", direction="two_sides", distance=5, distance2=-3,
                 start="offset", start_offset=2, extent=extension1, side2_extent=extension2, **opciones)
    forma = sesion.cuerpo(salida["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    lo, hi = geo.caja_envolvente(forma)
    assert hi[2] == pytest.approx(7 if extension1 == "distance" else 15, abs=1e-6) if extension1 != "all" else hi[2] > 28
    assert lo[2] == pytest.approx(-1 if extension2 == "distance" else -12, abs=1e-6) if extension2 != "all" else lo[2] < -20


@pytest.mark.parametrize("modo, inferior", [("body", -12), ("through", -20)])
def test_h81_lado2_hasta_cuerpo(modo, inferior):
    sesion = _sesion()
    salida = _ok(sesion, "extrude", sketch="Perfil", direction="two_sides", distance=5,
                 side2_extent="to_object", side2_to="Tope", to_mode=modo)
    forma = sesion.cuerpo(salida["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    lo, hi = geo.caja_envolvente(forma)
    assert (lo[2], hi[2]) == pytest.approx((inferior, 5), abs=1e-6)
    assert geo.volumen_exacto(forma) == pytest.approx(200 * (5 - inferior))
