# -*- coding: utf-8 -*-
"""Tubería: cadena tangente, límites de ruta y compatibilidad de recetas y agentes."""
import copy
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, operacion_desde_dict
from omnicad.timeline.ops_solido import OpTuberia


LARGO = 20 + 5 * math.pi


def _ruta():
    doc = Documento()
    boceto = Boceto()
    linea = boceto.agregar_linea((0, 0), (20, 0))
    arco = boceto.agregar_arco_centro((20, 10), (20, 0), (30, 10))
    # Esta continuación está conectada, pero NO es tangente; no debe entrar en la cadena.
    boceto.agregar_linea((30, 10), (40, 10))
    op = OpBoceto(doc.nuevo_id(), plano="XY", boceto=boceto)
    resultado = doc.agregar(op)
    assert resultado.estado == "ok", resultado.mensaje
    refs = [{"tipo": "curva_boceto", "boceto": op.id, "curva": cid} for cid in (linea, arco)]
    return doc, refs


def _volumen(doc, op):
    parametros = copy.deepcopy(op.p)
    resultado = doc.agregar(op)
    assert resultado.estado == "ok", resultado.mensaje
    assert op.p == parametros
    forma = list(doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(forma)
    return geo.volumen_exacto(forma)


@pytest.mark.parametrize("cadena,largo", [(True, LARGO), (False, 20)])
def test_una_arista_amplia_solo_la_cadena_tangente(cadena, largo):
    doc, refs = _ruta()
    op = OpTuberia(doc.nuevo_id(), ruta=refs[:1], tamano="2 mm", cadena=cadena)
    assert _volumen(doc, op) == pytest.approx(math.pi * largo, rel=1e-5)


@pytest.mark.parametrize("seleccion", [slice(1, 2), slice(None)], ids=["desde_arco", "ambas_aristas"])
def test_cadena_desde_el_arco_y_sin_duplicar_selecciones(seleccion):
    doc, refs = _ruta()
    op = OpTuberia(doc.nuevo_id(), ruta=refs[seleccion], tamano="2 mm", cadena=True)
    assert _volumen(doc, op) == pytest.approx(math.pi * LARGO, rel=1e-5)


@pytest.mark.parametrize("fin,inicio", [(1, 0.2), (0.8, 0.2), (1, 0.7)])
def test_dos_distancias_recortan_la_ruta(fin, inicio):
    doc, refs = _ruta()
    op = OpTuberia(doc.nuevo_id(), ruta=refs[:1], tamano="2 mm", cadena=True,
                   distancia=str(fin), distancia2=str(inicio))
    volumen = _volumen(doc, op)
    assert volumen == pytest.approx(math.pi * LARGO * (fin - inicio), rel=1e-5)
    assert volumen < math.pi * LARGO


@pytest.mark.parametrize("invertida", [False, True])
def test_recorte_respeta_la_orientacion_de_la_arista(invertida):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt
    ruta = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0)).Edge()
    if invertida:
        ruta = TopoDS.Edge(ruta.Reversed())
    forma = sc.tuberia(ruta, tamano=2, distancia=0.8, distancia2=0.1)
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(math.pi * 14, rel=1e-6)
    assert geo.centro_masa(forma)[0] == pytest.approx(11 if invertida else 9, abs=1e-6)


@pytest.mark.parametrize("cadena,largo", [(True, LARGO), (False, 20)])
def test_cadena_en_aristas_de_un_cuerpo(cadena, largo):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    from omnicad.nucleo import referencias
    from omnicad.nucleo.perfiles import aristas_boceto
    from omnicad.timeline.operaciones import Cuerpo, OpOperacionBase
    origen, refs = _ruta()
    br = origen.estado_final.bocetos[refs[0]["boceto"]]
    aristas = [a for _, a in aristas_boceto(br.boceto.geometria(), br.plano)]
    superficie = BRepPrimAPI_MakePrism(sc._alambre(aristas), gp_Vec(0, 0, 10)).Shape()
    doc = Documento()
    base = OpOperacionBase.desde_cuerpos(doc.nuevo_id(), [Cuerpo("origen", "Ruta", superficie, "origen", "superficie")])
    assert doc.agregar(base).estado == "ok"
    cuerpo = next(iter(doc.estado_final.cuerpos.values()))
    arista = referencias.resolver(cuerpo.forma, {"tipo": "arista", "firma": referencias.firma_arista(aristas[0])})
    ref = referencias.referencia(cuerpo.id, arista, cuerpo.forma)
    op = OpTuberia(doc.nuevo_id(), ruta=[ref], tamano="2 mm", cadena=cadena)
    assert _volumen(doc, op) == pytest.approx(math.pi * largo, rel=1e-5)


@pytest.mark.parametrize("distancia", ["1", "0.4"])
def test_receta_vieja_conserva_el_solido(distancia):
    doc, refs = _ruta()
    op = operacion_desde_dict({"tipo": "tuberia", "id": doc.nuevo_id(),
                              "params": {"ruta": refs[:1], "tamano": "2 mm", "distancia": distancia}})
    assert op.p["cadena"] is False and op.p["distancia2"] == "0"
    assert _volumen(doc, op) == pytest.approx(math.pi * 20 * float(distancia), rel=1e-6)


@pytest.mark.parametrize("fin,inicio", [(0.5, 0.5), (0.4, 0.6), (1, -0.1), (1, 1), (math.nan, 0), (1, math.inf)])
def test_limites_invalidos(fin, inicio):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    ruta = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0)).Edge()
    with pytest.raises(geo.ErrorGeometria, match="distancias"):
        sc.tuberia(ruta, tamano=2, distancia=fin, distancia2=inicio)


def test_agentes_run_operation_expone_y_ejecuta_las_opciones():
    doc, refs = _ruta()
    sesion = api.Sesion(doc)
    descripcion = api.llamar(sesion, "describe_operation", {"type": "tuberia"})
    assert descripcion["ok"], descripcion
    parametros = {p["name"]: p for p in descripcion["result"]["params"]}
    assert parametros["cadena"]["default"] is False
    assert parametros["distancia2"]["accepts_expression"]
    respuesta = api.llamar(sesion, "run_operation", {"type": "tuberia", "params": {
        "ruta": refs[:1], "tamano": "2 mm", "cadena": True, "distancia": "0.9", "distancia2": "0.2"}})
    assert respuesta["ok"], respuesta
    assert respuesta["result"]["status"] == "ok", respuesta
    forma = doc.estado_final.cuerpos[respuesta["result"]["new_bodies"][0]].forma
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(math.pi * LARGO * 0.7, rel=1e-5)


def test_dialogo_predeterminados_textos_y_edicion_compatible():
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.crear import Tuberia
    doc, refs = _ruta()
    comando, contexto = Tuberia(), ContextoComando(doc)
    campos = {campo.clave: campo for campo in comando.campos(contexto)}
    valores = {clave: campo.defecto for clave, campo in campos.items()}
    assert valores["cadena"] is True
    assert valores["distancia"] == "1.00" and valores["distancia2"] == "0.00"
    assert campos["hueca"].etiqueta == "Hueco"
    assert campos["espesor"].etiqueta == "Espesor de sección"
    valores["ruta"] = [hit_desde_ref(refs[0], doc.estado_final)]
    op = comando.construir(valores, contexto)
    assert _volumen(doc, op) == pytest.approx(math.pi * 2.5 ** 2 * LARGO, rel=1e-5)
    vieja = OpTuberia("vieja", ruta=refs[:1])
    editados = comando.desde_op(vieja, contexto)
    assert editados["cadena"] is False and editados["distancia2"] == "0"
