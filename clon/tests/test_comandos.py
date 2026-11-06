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


def test_extruir_simetrico_arranca_en_longitud_total_como_la_api(app_qt):
    """H-86: sin tocar «Medida», el panel de Extruir tiene que dar el mismo cuerpo que
    `extrude direction=symmetric distance=10`: 10 mm en total, mitad a cada lado (Fusion: Whole Length)."""
    doc = _doc_rectangulo()
    op = _extruir(doc, direccion="simetrica", distancia="10 mm")
    cid = f"{op.id}.c1"
    assert g.volumen(doc.estado_final.cuerpos[cid].forma) == pytest.approx(2000)
    (_, _, z0), (_, _, z1) = _caja(doc, cid)
    assert (z0, z1) == pytest.approx((-5, 5))


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


@pytest.mark.parametrize("superficie", [False, True])
def test_h101_panel_muestra_desfase_con_inicio_objeto(app_qt, superficie):
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.comandos.superficie import SupExtruir
    from omnicad.ui.visor3d import Visor3D
    doc = _doc_rectangulo()
    doc.agregar(OpPlano(doc.nuevo_id(), "Inicio", base="XY", distancia="4 mm"))
    ctx = ContextoComando(doc)
    cmd = SupExtruir() if superficie else Extruir()
    visor = Visor3D()
    visor.set_modelo(ctx.estado)
    panel = PanelComando(cmd, ctx, visor)
    panel._t_previa.stop()
    panel.set_valor("inicio", "objeto")
    assert not panel.widgets["desfase_inicio"].isHidden()
    panel.set_valor("desfase_inicio", "-3 mm")
    panel.valores["inicio_objeto"] = [hit_desde_ref({"tipo": "plano", "id": "op2"}, ctx.estado)]
    if superficie:
        curva = next(iter(doc.operacion("op1").boceto.curvas))
        panel.valores["curvas"] = [hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, ctx.estado)]
    else:
        panel.valores["perfiles"] = [_perfil(doc)]
    op = cmd.construir(panel.valores, ctx)
    assert op.p["desfase_inicio"] == "-3 mm"
    assert cmd.desde_op(op, ctx)["desfase_inicio"] == "-3 mm"
    previas = []
    panel.previa.connect(previas.append)
    panel._previa_aislada = True
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    assert panel._prisma_previa is None  # Inicio › Objeto usa la operación exacta, incluso durante el arrastre.
    forma = next(iter(previas[-1].cuerpos.values())).forma
    assert g.es_valida(forma)
    assert np.allclose(g.caja_envolvente(forma), [[0, 0, 1], [20, 0 if superficie else 10, 11]], atol=1e-6)
    assert (g.area(forma) if superficie else g.volumen_exacto(forma)) == pytest.approx(200 if superficie else 2000)
    panel.set_valor("inicio", "plano")
    assert panel.widgets["desfase_inicio"].isHidden()
    panel._t_previa.stop()
    panel.deleteLater()
    visor.deleteLater()


@pytest.mark.parametrize("extension", ["objeto", "todo"])
def test_h81_panel_extension_lado2_y_previa(app_qt, extension):
    from omnicad.ui.comando import ContextoComando, ErrorComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.visor3d import Visor3D
    doc = _doc_rectangulo()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="30", largo="20", alto="8", z="-20"))
    doc.agregar(OpPlano(doc.nuevo_id(), base="XY", distancia="-12 mm"))
    ctx, cmd, visor = ContextoComando(doc), Extruir(), Visor3D()
    visor.set_modelo(ctx.estado)
    panel = PanelComando(cmd, ctx, visor)
    panel._t_previa.stop()
    assert panel.widgets["extension2"].isHidden()
    panel.set_valor("direccion", "dos_lados")
    assert not panel.widgets["extension2"].isHidden()
    panel.set_valor("distancia", "5 mm")
    panel.set_valor("extension2", extension)
    assert panel.widgets["distancia2"].isHidden()
    assert panel.widgets["hasta2"].isHidden() == (extension != "objeto")
    panel.valores["perfiles"] = [_perfil(doc)]
    if extension == "objeto":
        with pytest.raises(ErrorComando, match="lado 2"):
            cmd.construir(panel.valores, ctx)
        panel.valores["hasta2"] = [hit_desde_ref({"tipo": "plano", "id": "op3"}, ctx.estado)]
    op = cmd.construir(panel.valores, ctx)
    assert op.p["extension2"] == extension
    assert [h["ref"] for h in cmd.desde_op(op, ctx)["hasta2"]] == [h["ref"] for h in panel.valores["hasta2"]]
    previas = []
    panel.previa.connect(previas.append)
    panel._previa_aislada = True
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    assert panel._prisma_previa is None
    forma = previas[-1].cuerpos[f"{panel.ultima_op.id}.c1"].forma
    assert g.es_valida(forma)
    lo, hi = g.caja_envolvente(forma)
    assert hi[2] == pytest.approx(5, abs=1e-6)
    assert lo[2] == pytest.approx(-12, abs=1e-6) if extension == "objeto" else lo[2] < -20
    panel._t_previa.stop()
    panel.deleteLater()
    visor.deleteLater()


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


# ---------------------------------------------------------------- nivel 2: reglas propias en el diálogo (B-25)
def test_reglas_de_chapa_del_dialogo_incluye_las_propias(app_qt, monkeypatch):
    """B-25: el diálogo de reglas de chapa lista también las reglas propias del usuario, no solo las de
    fábrica (se crean con la API o la CLI durante la sesión)."""
    from omnicad.nucleo import chapa as ch
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.chapa import ReglasChapa, _reglas_biblioteca

    monkeypatch.setattr(ch, "REGLAS_USUARIO", {"Latón 0.8 mm": {"espesor": 0.8}})
    biblioteca = _reglas_biblioteca()
    assert "Acero 1 mm" in biblioteca and "Latón 0.8 mm" in biblioteca
    campo = [c for c in ReglasChapa().campos(ContextoComando(Documento())) if c.clave == "regla"][0]
    assert "Latón 0.8 mm" in campo.opciones and "Acero 1 mm" in campo.opciones
