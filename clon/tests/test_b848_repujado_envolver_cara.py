# -*- coding: utf-8 -*-
"""B-848: Repujado sobre una cara cilíndrica: «Envolver en la cara» se tilda solo al elegir la cara (y queda
editable) y, si queda sin tildar, el aviso es de 1 renglón en español simple: «Marcá «Envolver en la cara»»."""
import math
import os

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import solidos_crear as sc
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _poligono(puntos):
    mk = BRepBuilderAPI_MakePolygon()
    for p in puntos:
        mk.Add(gp_Pnt(*map(float, p)))
    mk.Close()
    return BRepBuilderAPI_MakeFace(mk.Wire(), True).Face()


def _h(doc, ref):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref(ref, doc.estado_final)


def _cilindro_y_perfil():
    """Cilindro r10 h30 de pie (eje Z) y un perfil de 4×6 en el plano YZ (x = 0, paralelo al eje): envolviendo con
    1 mm suma el sector (4/10)/2·6 · (11²−10²) = 25,2 mm³ (como `test_repujado_envolviendo_un_cilindro`)."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="10", alto="30"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    lateral = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    b = Boceto()
    b.agregar_rectangulo((-2, 12), (2, 18))
    bid = doc.nuevo_id()
    doc.agregar(OpBoceto(bid, plano="YZ", boceto=b))
    perfil = doc.estado_final.bocetos[bid].perfiles[0]
    return (doc, _h(doc, refs.referencia("op1.c1", lateral, forma)),
            _h(doc, {"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(perfil)}))


def _panel(doc, perfil, caras):
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.crear import Repujado
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    return PanelComando(Repujado(), ContextoComando(doc), visor, {"perfiles": [perfil], "caras": caras})


def test_sin_envolver_el_aviso_es_de_1_renglon_y_sin_codigo():
    """B-848: el mensaje del núcleo es «Marcá «Envolver en la cara»» (UX-1: sin código como `envolver=True`;
    UX-9: 1 renglón, máx. 60 caracteres)."""
    cil = g.cilindro(10, 30)
    lateral = [c for c in g.caras(cil) if g.plano_de_cara(c) is None][0]
    perfil = _poligono([(0, -2, 12), (0, 2, 12), (0, 2, 18), (0, -2, 18)])   # plano YZ, paralelo al eje
    with pytest.raises(g.ErrorGeometria) as e:
        sc.repujado(cil, [perfil], lateral, 1.0)
    assert e.value.args[0] == "Marcá «Envolver en la cara»."
    assert len(e.value.args[0]) <= 60


def test_al_elegir_una_cara_cilindrica_se_tilda_envolver_y_la_previa_envuelve():
    """B-848: con la cara cilíndrica ya elegida al abrir (preselección), la casilla se tilda sola y la previa
    envuelve sin tocar nada más (UX-7)."""
    doc, cara, perfil = _cilindro_y_perfil()
    panel = _panel(doc, perfil, [cara])
    assert panel.valores["envolver"] is True
    estados = []
    panel.previa.connect(estados.append)
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    assert g.volumen(next(iter(estados[-1].cuerpos.values())).forma) == \
        pytest.approx(math.pi * 100 * 30 + 25.2, rel=1e-6)
    panel.cancelar()


def test_la_cara_plana_no_tilda_y_la_cilindrica_si():
    """B-848: al elegir una cara plana la casilla queda como estaba; al elegir la cilíndrica se tilda sola."""
    doc, cara_cil, perfil = _cilindro_y_perfil()
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    tapa = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "plano")
    panel = _panel(doc, perfil, [])
    assert panel.valores["envolver"] is False
    panel.set_valor("caras", [_h(doc, refs.referencia("op1.c1", tapa, forma))])   # como un clic en la vista
    assert panel.valores["envolver"] is False
    panel.set_valor("caras", [cara_cil])
    assert panel.valores["envolver"] is True
    panel.cancelar()


def test_la_casilla_queda_editable_y_sin_tildar_avisa_en_1_renglon():
    """B-848: destildada a mano se queda destildada (editable) y la previa avisa en 1 renglón, en rojo."""
    doc, cara, perfil = _cilindro_y_perfil()
    panel = _panel(doc, perfil, [cara])
    assert panel.valores["envolver"] is True
    panel.set_valor("envolver", False)              # el usuario la destilda: nada la vuelve a tildar
    assert panel.valores["envolver"] is False
    panel._calcular_previa()
    assert not panel._previa_ok
    assert panel.mensaje.text().endswith("Marcá «Envolver en la cara»."), panel.mensaje.text()
    panel.cancelar()
