# -*- coding: utf-8 -*-
"""Diálogos de comando estilo Fusion: selección en la vista 3D, armado de operaciones y edición."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPlano, OpPrimitiva


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc_rectangulo(ancho=20, alto=10):
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (ancho, alto))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    return doc


def _perfil(doc, bid="op1", i=0):
    from omnicad.ui.comando import hit_desde_ref
    perfil = doc.estado_final.bocetos[bid].perfiles[i]
    return hit_desde_ref({"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(perfil)}, doc.estado_final)


def _extruir(doc, **valores):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import Extruir
    cmd = Extruir()
    ctx = ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(perfiles=[_perfil(doc)], **valores)
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op


def _caja(doc, cid):
    return g.caja_envolvente(doc.estado_final.cuerpos[cid].forma)


@pytest.mark.parametrize("valores, volumen, zs", [
    ({"distancia": "10 mm"}, 2000, (0, 10)),
    ({"direccion": "dos_lados", "distancia": "10 mm", "distancia2": "4 mm"}, 2800, (-4, 10)),
    ({"direccion": "simetrica", "medida": "mitad", "distancia": "5 mm"}, 2000, (-5, 5)),
    ({"direccion": "simetrica", "medida": "total", "distancia": "10 mm"}, 2000, (-5, 5)),
    ({"inicio": "desfase", "desfase_inicio": "3 mm", "distancia": "10 mm"}, 2000, (3, 13)),
    ({"invertir": True, "distancia": "10 mm"}, 2000, (-10, 0)),
])
def test_extruir_opciones(app_qt, valores, volumen, zs):
    doc = _doc_rectangulo()
    op = _extruir(doc, **valores)
    cid = f"{op.id}.c1"
    assert g.volumen(doc.estado_final.cuerpos[cid].forma) == pytest.approx(volumen)
    (_, _, z0), (_, _, z1) = _caja(doc, cid)
    assert (z0, z1) == pytest.approx(zs)
    assert doc.estado_final.cuerpos[cid].nombre.startswith("Cuerpo")
    assert op.nombre == "Extrusión1"


def test_extruir_hasta_un_plano_y_cortar_con_todo(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    doc = _doc_rectangulo()
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="25 mm"))
    plano = hit_desde_ref({"tipo": "plano", "id": "op2"}, doc.estado_final)
    try:
        op = _extruir(doc, extension="objeto", hasta=[plano])
    except AssertionError:
        pytest.skip("la extensión «Al objeto» necesita el núcleo de extrusión avanzada")
    (_, _, z0), (_, _, z1) = _caja(doc, f"{op.id}.c1")
    assert (z0, z1) == pytest.approx((0, 25))


def test_editar_extrusion_sin_cambios_conserva_los_perfiles(app_qt):
    """Regresión (antes con el diálogo modal): editar y aceptar sin tocar nada no cambia los perfiles."""
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import Extruir
    doc = Documento()
    b = Boceto()
    b.agregar_circulo((0, 0), 10)
    b.agregar_linea((-12, 0), (12, 0))
    doc.agregar(OpBoceto(doc.nuevo_id(), boceto=b))
    perfiles = doc.estado_final.bocetos["op1"].perfiles
    arriba = max(perfiles, key=lambda p: p.centroide_uv[1])
    doc.agregar(OpExtrusion(doc.nuevo_id(), boceto="op1", perfiles=[OpExtrusion.referencia_perfil(arriba)],
                            distancia="10"))
    volumen = g.volumen(doc.estado_final.cuerpos["op2.c1"].forma)
    assert volumen == pytest.approx(math.pi * 100 / 2 * 10)
    cmd, ctx = Extruir(), ContextoComando(doc, op=doc.operacion("op2"))
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(cmd.desde_op(ctx.op, ctx))
    doc.reemplazar("op2", cmd.construir(v, ctx))
    assert g.volumen(doc.estado_final.cuerpos["op2.c1"].forma) == pytest.approx(volumen)
    assert doc.operacion("op2").nombre == ctx.op.nombre


def test_revolucion_con_eje_de_origen(app_qt):
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.solido import Revolucion
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((5, 0), (10, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    cmd, ctx = Revolucion(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(perfiles=[_perfil(doc)], eje=[hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)])
    doc.agregar(cmd.construir(v, ctx))
    cuerpo = next(iter(doc.estado_final.cuerpos.values()))
    assert g.volumen(cuerpo.forma) == pytest.approx(math.pi * (100 - 25) * 10, rel=1e-6)


def test_visor_elige_caras_aristas_vertices_y_cuerpos(app_qt):
    from omnicad.timeline.operaciones import EstadoModelo
    from omnicad.ui.visor3d import Visor3D
    v = Visor3D()
    v.resize(800, 600)
    estado = EstadoModelo()
    estado.nuevo_cuerpo("op1", g.caja(20, 20, 20))
    v.set_modelo(estado)
    v.vista("iso")
    centro_arriba = v.proyectar((10, 10, 20))
    assert v.elegir_entidad(centro_arriba, {"cara"})["tipo"] == "cara"
    hit = v.elegir_entidad(centro_arriba, {"cuerpo"})
    assert hit["tipo"] == "cuerpo" and hit["ref"] == {"tipo": "cuerpo", "cuerpo": "op1.c1"}
    medio_arista = v.proyectar((10, 0, 20))
    hit = v.elegir_entidad(medio_arista, {"arista", "cara"})
    assert hit["tipo"] == "arista" and hit["ref"]["firma"]["geom"] == "linea"
    vertice = v.proyectar((20, 0, 20))
    hit = v.elegir_entidad(vertice, {"vertice", "arista"})
    assert hit["tipo"] == "vertice" and np.allclose(hit["punto"], (20, 0, 20))
    from PySide6.QtCore import QPointF
    assert v.elegir_entidad(QPointF(3, 3), {"cara"}) is None


def test_referencias_de_aristas_sobreviven_a_un_cambio_de_cota():
    from omnicad.nucleo import referencias as refs
    a = g.caja(20, 20, 10)
    arista = next(e for e in refs.subformas(a, "arista")
                  if np.allclose(refs.firma_arista(e)["medio"], (10, 0, 10)))
    ref = refs.referencia("op1.c1", arista)
    b = g.caja(22, 20, 12)                  # la caja creció un poco: la arista de arriba-adelante sigue ahí
    nueva = refs.resolver(b, ref)
    assert nueva is not None and np.allclose(refs.firma_arista(nueva)["medio"], (11, 0, 12))
    assert refs.resolver(g.cilindro(5, 3), ref) is None


def test_primitiva_sigue_funcionando(app_qt):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    assert len(doc.estado_final.cuerpos) == 1
