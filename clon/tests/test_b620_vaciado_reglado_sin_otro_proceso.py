# -*- coding: utf-8 -*-
"""B-620: en el trabajador, la revisión de cruces de un Vaciado sobre caras regladas que no enroscan (una solevación
reglada, una extrusión de spline de un .f3d) se hace ahí mismo; antes abría otro proceso por cuerpo (~5 s en Windows:
la previa de un Vaciado de 2 cuerpos tardaba ~19 s). La rosca modelada sigue aparte (B-570: test_b570_*)."""
import numpy as np
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad.nucleo import aislado, intercambio, revision, solidos_modificar
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpOperacionBase, OpPrimitiva
from omnicad.timeline.ops_modificar import OpVaciado


def _solevacion_reglada():
    s = BRepOffsetAPI_ThruSections(True, True)
    for cx, cy, z, r in ((0, 0, 0, 30), (8, 3, 40, 20)):
        circ = gp_Circ(gp_Ax2(gp_Pnt(cx, cy, z), gp_Dir(0, 0, 1)), r)
        s.AddWire(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ).Edge()).Wire())
    s.Build()
    return geo.solidos(s.Shape())[0]


def _vaciar(doc):
    c = doc.estado_final.cuerpos["op1.c1"]
    caras = [refs.referencia("op1.c1", s, c.forma) for s in refs.subformas(c.forma, "cara")
             if np.isclose(refs.firma(s)["centro"][2], 40)]
    return doc.agregar(OpVaciado(doc.nuevo_id(), "Vaciado1", caras=caras, espesor_interior="1 mm", tangente=True))


@pytest.fixture
def doc_cortado():
    """La solevación reglada, ya modificada por un paso anterior (un hueco cortado en la base)."""
    doc = Documento()
    doc.agregar(OpOperacionBase(doc.nuevo_id(), cuerpos=[{"id": "c0", "brep": intercambio.brep_a_texto(_solevacion_reglada())}]))
    assert doc.agregar(OpPrimitiva(doc.nuevo_id(), ancho="10 mm", largo="10 mm", alto="5 mm", x="-5 mm", y="-5 mm", z="-1 mm",
                                   operacion="cortar", objetivo="op1.c1")).estado == "ok"
    return doc


def test_b620_vaciado_reglado_se_revisa_en_el_trabajador(doc_cortado, monkeypatch):
    forma = doc_cortado.estado_final.cuerpos["op1.c1"].forma
    assert geo.es_forma_libre(forma) and revision._pocos_polos(forma)
    monkeypatch.setattr(aislado, "EN_HIJO", True)
    monkeypatch.setattr(aislado, "_correr", lambda *a, **k: pytest.fail("abrió otro proceso para revisar los cruces"))
    volumen = geo.volumen(forma)
    assert _vaciar(doc_cortado).estado == "ok"
    vaciado = doc_cortado.estado_final.cuerpos["op1.c1"].forma
    assert geo.es_valida(vaciado) and 0 < geo.volumen(vaciado) < 0.5 * volumen


def test_b620_si_la_via_rapida_falla_va_al_proceso_aparte(doc_cortado, monkeypatch):
    llamadas = []
    intentos_bop = []

    def fallar_malla(*a, **k):
        raise RuntimeError("malla no disponible")

    def fallar_bop(forma, limite):
        intentos_bop.append(forma)
        raise RuntimeError("BOP falló en el trabajador")

    monkeypatch.setattr(aislado, "EN_HIJO", True)
    monkeypatch.setattr(solidos_modificar, "_cruces_pared_malla", fallar_malla)
    monkeypatch.setattr(revision, "_autointersecciones", fallar_bop)
    monkeypatch.setattr(aislado, "_correr", lambda *a, **k: llamadas.append(a) or (0, [], True))
    assert _vaciar(doc_cortado).estado == "ok"
    assert intentos_bop
    assert [a[0] for a in llamadas] == ["autointersecciones"]
