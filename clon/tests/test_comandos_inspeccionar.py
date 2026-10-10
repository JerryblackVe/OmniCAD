# -*- coding: utf-8 -*-
"""INSPECCIONAR: medir, interferencia, centro de masa y los análisis guardados en el navegador."""
import os

import numpy as np
import pytest

from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="5"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="10", x="50"))
    return doc


def _cara(doc, cid, centro):
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(forma, "cara") if np.allclose(refs.firma_cara(s)["centro"], centro))
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _cuerpo(doc, cid):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, doc.estado_final)


def _valores(cmd, ctx, **v):
    base = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    base.update(v)
    return base


def test_medir_distancia_y_angulo_entre_caras():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.inspeccionar import Medir
    doc = _doc()
    cmd, ctx = Medir(), ContextoComando(doc)
    v = _valores(cmd, ctx, a=[_cara(doc, "op1.c1", (0, 10, 15))], b=[_cara(doc, "op1.c1", (10, 10, 15))])
    texto = cmd._resultado(v, ctx)
    assert "Distancia: 10" in texto and "Ángulo: 0" in texto
    v = _valores(cmd, ctx, a=[_cara(doc, "op1.c1", (5, 10, 30))])
    assert "Área: 200" in cmd._resultado(v, ctx)


def test_interferencia_y_centro_de_masa():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.inspeccionar import CentroMasa, Interferencia
    doc = _doc()
    cmd, ctx = Interferencia(), ContextoComando(doc)
    texto = cmd._resultado(_valores(cmd, ctx), ctx)
    assert "500" in texto and texto.count("↔") == 1          # caja 10×20×30 y caja 10³ corrida 5 en X
    cm, ctx = CentroMasa(), ContextoComando(doc)
    centro, masa = cm._calcular(_valores(cm, ctx, cuerpos=[_cuerpo(doc, "op1.c1")]), ctx)
    assert np.allclose(centro, (5, 10, 15)) and masa == pytest.approx(6000 * 7.85e-3)
    doc.set_propiedad(["op1.c1"], "material", "Aluminio 6061")
    _, masa = cm._calcular(_valores(cm, ctx, cuerpos=[_cuerpo(doc, "op1.c1")]), ctx)
    assert masa == pytest.approx(6000 * 2.70e-3)


@pytest.mark.parametrize("tipo, params", [
    ("seccion", {"plano": {"tipo": "plano", "id": "XY"}, "desfase_mm": 5.0}),
    ("cebra", {"frecuencia": 8}),
    ("mapa_entorno", {}),
    ("desmoldeo", {"direccion": None}),
    ("curvatura", {"tipo_curvatura": "media"}),
    ("isocurva", {"densidad": 5}),
    ("accesibilidad", {}),
    ("radio_minimo", {"radio": 2.0}),
])
def test_analisis_se_calculan_y_se_guardan(tipo, params):
    from omnicad.ui import analisis_vista
    doc = _doc()
    nombre = doc.agregar_analisis(tipo, params)
    datos = analisis_vista.calcular(tipo, params, doc.estado_final)
    if tipo in ("cebra", "mapa_entorno"):
        n = np.array([[0, 0, 1.0], [1.0, 0, 0]])
        assert np.asarray(datos["colores"](n, np.array([0, 0, 1.0]))).shape == (2, 3)
    elif tipo == "seccion":
        assert datos["cortes"] and any(p[0] == "tris" and len(p[1]) for p in datos["capas"])
    elif tipo == "isocurva":
        assert datos["capas"]
    else:
        v, n, c = datos["mallas"]["op1.c1"]
        assert len(v) == len(n) == len(c) > 0
    otro = Documento.desde_dict(doc.a_dict())
    assert otro.analisis[nombre]["tipo"] == tipo
    doc.alternar_analisis(nombre)
    assert doc.analisis[nombre]["visible"] is False


# ---------------------------------------------------------------- Revisar geometría y Reparar cuerpo
def _doc_roto():
    """_doc() más un cuerpo «Roto»: caja 10×20×30 con una cara al revés (inválida) y tolerancias de 0,5 mm."""
    from OCP.BRep import BRep_Builder
    from OCP.ShapeFix import ShapeFix_ShapeTolerance
    from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid

    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import intercambio
    from omnicad.timeline.operaciones import OpOperacionBase
    sh, so, b = TopoDS_Shell(), TopoDS_Solid(), BRep_Builder()
    b.MakeShell(sh)
    for i, f in enumerate(geo.caras(geo.caja(10, 20, 30))):
        b.Add(sh, f.Reversed() if i == 0 else f)
    b.MakeSolid(so)
    b.Add(so, sh)
    ShapeFix_ShapeTolerance().SetTolerance(so, 0.5)
    doc = _doc()
    doc.agregar(OpOperacionBase(doc.nuevo_id(), cuerpos=[{"id": "x.c1", "nombre": "Roto", "tipo": "solido",
                                                          "brep": intercambio.brep_a_texto(so)}]))
    return doc


def test_revisar_geometria_informa_marca_y_repara():
    from omnicad.nucleo import geometria as geo
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos import POR_TIPO, comando_para
    from omnicad.ui.comandos.revision import RepararCuerpo, RevisarGeometria, primitivas
    doc = _doc_roto()
    roto = next(c for c in doc.estado_final.cuerpos.values() if c.nombre == "Roto")
    cmd, ctx = RevisarGeometria(), ContextoComando(doc)
    assert cmd.verificar(ctx) is None
    texto = cmd._resultado(_valores(cmd, ctx, cuerpos=[_cuerpo(doc, "op1.c1")]), ctx)
    assert "Válido: sí" in texto and "Sin problemas." in texto and "Volumen: 6000" in texto
    v = _valores(cmd, ctx, cuerpos=[_cuerpo(doc, roto.id)])
    texto = cmd._resultado(v, ctx)
    assert "Válido: NO" in texto and "orientación invertida" in texto and "… y" in texto
    prims = primitivas([g for _c, g, _i in cmd.calcular(v, ctx)])
    assert {p[0] for p in prims} == {"puntos"} and len(prims[-1][1]) == 1 and len(prims[1][1]) == 26  # error y avisos
    v_imp = _valores(cmd, ctx, cuerpos=[_cuerpo(doc, "op1.c1")], impresion=True, espesor="12 mm")
    texto = cmd._resultado(v_imp, ctx)                   # la caja 10×20×30: la pared más fina mide 10
    assert "Impresión 3D:" in texto and "Pared de 10 mm (mínimo 12 mm)" in texto and "Imprimible: NO" in texto
    todos = _valores(cmd, ctx)                           # sin selección: los 4 cuerpos, una línea por cuerpo
    compacto = cmd._resultado(todos, ctx)
    assert compacto.count("■") == 4 and "Roto: INVÁLIDO, estanco; 1 error(es), 26 aviso(s)" in compacto
    assert compacto.count("sin problemas") == 3
    pasos = len(doc.operaciones)
    cmd.aplicar(todos, ctx)                              # sin «Reparar al aceptar» no agrega nada
    assert len(doc.operaciones) == pasos
    cmd.aplicar(dict(todos, reparar=True, tolerancia="0.001 mm"), ctx)     # repara solo los que tienen problemas
    assert len(doc.operaciones) == pasos + 1 and doc.operaciones[-1].TIPO == "reparar_cuerpo"
    assert doc.operaciones[-1].nombre == "Reparar1" and doc.operaciones[-1].p["cuerpos"] == [roto.id]
    assert geo.es_valida(doc.estado_final.cuerpos[roto.id].forma)
    assert POR_TIPO["reparar_cuerpo"] is RepararCuerpo and comando_para(doc.operaciones[-1]) is RepararCuerpo
    ctx = ContextoComando(doc)
    with pytest.raises(ErrorComando, match="no hace falta reparar"):
        RevisarGeometria().aplicar(dict(_valores(cmd, ctx), reparar=True), ctx)


def test_revisar_y_reparar_en_el_panel_de_comando():
    """El panel real (sin ventana: un visor y lo poco que el panel usa de ella): informe, marcas en la capa «medida»,
    Aceptar con «Reparar al aceptar» agrega el paso y al cerrar se borran las marcas; después se edita el paso."""
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.revision import RepararCuerpo, RevisarGeometria
    from omnicad.ui.visor3d import Visor3D

    class Ventana:
        def __init__(self, doc, visor):
            self.doc, self.visor, self.agregados = doc, visor, []

        def info_seleccion(self, texto):
            pass

        def _agregar(self, op):
            self.agregados.append(op)
            self.doc.agregar(op)

    doc = _doc_roto()
    roto = next(c for c in doc.estado_final.cuerpos.values() if c.nombre == "Roto")
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    ventana = Ventana(doc, visor)
    panel = PanelComando(RevisarGeometria(), ContextoComando(doc, ventana), visor,
                         {"cuerpos": [_cuerpo(doc, roto.id)], "impresion": True})
    panel._calcular_previa()
    assert "Válido: NO" in panel.widgets["resultado"].text() and "Impresión 3D:" in panel.widgets["resultado"].text()
    assert visor._capas["medida"] and not panel.mensaje.text()
    panel.set_valor("reparar", True)
    panel.aceptar()
    assert [op.TIPO for op in ventana.agregados] == ["reparar_cuerpo"] and "medida" not in visor._capas
    editar = PanelComando(RepararCuerpo(), ContextoComando(doc, ventana, ventana.agregados[0]), visor)
    editar._calcular_previa()
    assert "Roto: INVÁLIDO" in editar.widgets["antes"].text() and editar.ultima_op.p["cuerpos"] == [roto.id]
    editar.cancelar()


def test_reparar_cuerpo_construye_y_edita_el_paso():
    from omnicad.nucleo import geometria as geo
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.revision import RepararCuerpo
    doc = _doc_roto()
    roto = next(c for c in doc.estado_final.cuerpos.values() if c.nombre == "Roto")
    cmd, ctx = RepararCuerpo(), ContextoComando(doc)
    with pytest.raises(ErrorComando):
        cmd.construir(_valores(cmd, ctx), ctx)
    v = _valores(cmd, ctx, cuerpos=[_cuerpo(doc, roto.id)], refinar=False)
    assert "INVÁLIDO" in cmd._antes(v, ctx) and "estanco" in cmd._antes(v, ctx)
    op = cmd.construir(v, ctx)
    assert op.p == {"cuerpos": [roto.id], "tolerancia": "0.01 mm", "coser": True, "refinar": False, "arreglar": True}
    assert doc.agregar(op).estado == "ok" and geo.es_valida(doc.estado_final.cuerpos[roto.id].forma)
    editar = ContextoComando(doc, op=op)
    valores = cmd.desde_op(op, editar)
    assert [h["ref"]["cuerpo"] for h in valores["cuerpos"]] == [roto.id] and valores["refinar"] is False
    nueva = cmd.construir(dict(valores, tolerancia="0.002 mm"), editar)
    assert nueva.id == op.id and nueva.nombre == op.nombre and nueva.p["tolerancia"] == "0.002 mm"
