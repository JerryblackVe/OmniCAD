"""H-101: Inicio › Objeto más desfase, según Start de Extrude reference de Fusion."""
import copy
import math

import numpy as np
import pytest
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_VERTEX
from OCP.TopoDS import TopoDS

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.timeline.ops_superficie import OpSupExtruir


def _ok(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.mark.parametrize("por_api", [False, True], ids=["operacion", "api"])
@pytest.mark.parametrize("superficie", [False, True], ids=["solido", "superficie"])
@pytest.mark.parametrize("angulo", [0, 30], ids=["paralelo", "inclinado"])
@pytest.mark.parametrize("desfase", [3, -3, None], ids=["positivo", "negativo", "receta_vieja"])
@pytest.mark.parametrize("invertir", [False, True], ids=["normal", "invertida"])
def test_h101_desfase_desde_objeto(por_api, superficie, angulo, desfase, invertir):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_rectangle", sketch="Perfil", x1=0, y1=0, x2=20, y2=10)
    _ok(sesion, "create_construction_plane", plane="XY", offset=4, name="Base")
    if angulo:
        _ok(sesion, "create_construction_plane", type="angle", plane="Base", references=["X"],
            angle=angulo, name="Inicio")
    inicio = "Inicio" if angulo else "Base"
    opciones = {"start_offset": desfase} if desfase is not None else {}
    if por_api:
        if superficie:
            resultado = _ok(sesion, "create_surface_extrude", profiles={"sketch": "Perfil", "profile": 0},
                            distance=10, start="object", start_object=inicio, flip=invertir, **opciones)
        else:
            resultado = _ok(sesion, "extrude", sketch="Perfil", distance=10, start="object",
                            start_object=inicio, reverse=invertir, **opciones)
        op = sesion.doc.operaciones[-1]
        forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    else:
        boceto = sesion.paso("Perfil").id
        perfil = OpExtrusion.referencia_perfil(sesion.doc.estado_final.bocetos[boceto].perfiles[0])
        seleccion = {"curvas": [{"tipo": "perfil", "boceto": boceto, **perfil}]} if superficie else {
            "boceto": boceto, "perfiles": [perfil]}
        if desfase is not None:
            seleccion["desfase_inicio"] = str(desfase)
        clase = OpSupExtruir if superficie else OpExtrusion
        op = clase(sesion.doc.nuevo_id(), inicio="objeto", inicio_objeto={"tipo": "plano", "id": sesion.paso(inicio).id},
                   distancia="10", invertir=invertir, **seleccion)
        anterior = copy.deepcopy(op.p)
        # La previa y el resultado aceptado deben coincidir, sin modificar la receta.
        previa, _ = sesion.doc.previsualizar(op, en_vivo=True)
        resultado = sesion.doc.agregar(op)
        assert resultado.estado == "ok", resultado.mensaje
        assert op.p == anterior
        forma = sesion.doc.estado_final.cuerpos[f"{op.id}.c1"].forma
        assert np.allclose(geo.caja_envolvente(previa.cuerpos[f"{op.id}.c1"].forma), geo.caja_envolvente(forma))
    assert geo.es_valida(forma)
    signo = -1 if invertir else 1
    # El plano en ángulo gira sobre el eje X de origen (como el caso B-206).
    base = (0 if angulo else 4) + signo * (desfase or 0)
    pendiente = math.tan(math.radians(angulo))
    assert np.allclose(geo.caja_envolvente(forma),
                       [[0, 0, base + min(0, signo * 10)],
                        [20, 10, base + 10 * pendiente + max(0, signo * 10)]], atol=1e-6)
    puntos = [BRep_Tool.Pnt_s(TopoDS.Vertex(v)) for v in geo._explorar(forma, TopAbs_VERTEX)]
    # Cada vértice pertenece a la base corrida según Z o a la tapa, nunca según la normal del objeto.
    niveles = [p.Z() - p.Y() * pendiente for p in puntos]
    assert all(min(abs(z - base), abs(z - base - signo * 10)) < 1e-6 for z in niveles)
    medir, esperado = (geo.area, 600) if superficie else (geo.volumen_exacto, 2000)
    assert medir(forma) == pytest.approx(esperado, rel=1e-8)


def test_h101_desfase_objeto_es_parametro_activo_del_modelo():
    assert "desfase_inicio" in OpExtrusion("op1", inicio="objeto").claves_modelo()
    assert "desfase_inicio" not in OpExtrusion("op1", inicio="plano").claves_modelo()


@pytest.mark.parametrize("desfase", [3, -3])
@pytest.mark.parametrize("extension", ["distance", "to_object"])
def test_h101_delgada_inclinada_suma_desfase_antes_del_limite(desfase, extension):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_rectangle", sketch="Perfil", x1=0, y1=0, x2=20, y2=10)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    _ok(sesion, "create_construction_plane", plane="XY", offset=30, name="Tope")
    opciones = {"to": "Tope"} if extension == "to_object" else {}
    resultado = _ok(sesion, "extrude", sketch="Perfil", thin=True, wall_thickness=1, wall_location="center",
                    start="object", start_object="Inicio", start_offset=desfase, distance=10, extent=extension, **opciones)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    pendiente = math.tan(math.radians(30))
    volumen = 600 if extension == "distance" else 60 * (30 - desfase - 5 * pendiente)
    assert geo.volumen_exacto(forma) == pytest.approx(volumen, rel=1e-8)
    lo, hi = geo.caja_envolvente(forma)
    assert lo[2] == pytest.approx(desfase - 0.5 * pendiente, abs=1e-6)
    assert hi[2] == pytest.approx(30 if extension == "to_object" else desfase + 10 + 10.5 * pendiente, abs=1e-6)
