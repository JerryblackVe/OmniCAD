# -*- coding: utf-8 -*-
"""ENSAMBLAR: componentes, uniones (posición y movimiento), grupos rígidos, vínculos e insertar diseños."""
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_ensamblar import OpComponente, OpInsertarDiseno, OpUnion


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _cara(doc, cid, centro):
    f = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(f, "cara") if np.allclose(refs.firma_cara(s)["centro"], centro))
    return refs.referencia(cid, sub, f)


def _doc_dos_cajas():
    """Base 40×40×10 en el origen (componente fijo) y un bloque 10×10×10 lejos (componente móvil)."""
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="100", y="50"))
    doc.agregar(OpComponente(doc.nuevo_id(), "Base", cuerpos=["op1.c1"], fijo=True))
    doc.agregar(OpComponente(doc.nuevo_id(), "Bloque", cuerpos=["op2.c1"]))
    return doc


def _caja(doc, cid="op2.c1"):
    return g.caja_envolvente(doc.estado_final.cuerpos[cid].forma)


def test_union_rigida_apoya_el_bloque_sobre_la_base():
    doc = _doc_dos_cajas()
    # cara de abajo del bloque contra la cara de arriba de la base: quedan enfrentadas (como en Fusion)
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida", origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                        origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    (x0, y0, z0), (x1, y1, z1) = _caja(doc)
    assert (x0, y0, z0, x1, y1, z1) == pytest.approx((15, 15, 10, 25, 25, 20))
    assert doc.estado_final.componentes["op4"]["nombre"] == "Bloque"


def test_union_de_revolucion_gira_y_se_acciona():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.ensamblar import AccionarUniones
    doc = _doc_dos_cajas()
    op = OpUnion(doc.nuevo_id(), "Unión1", tipo="revolucion", origen1=_cara(doc, "op2.c1", (105, 55, 0)),
                 origen2=_cara(doc, "op1.c1", (20, 20, 10)), dx="10 mm", giro="0 deg")
    doc.agregar(op)
    (x0, y0, _), (x1, y1, _) = _caja(doc)
    assert (x0, x1) == pytest.approx((25, 35)) or (y0, y1) == pytest.approx((25, 35))
    cmd = AccionarUniones()
    ctx = ContextoComando(doc)
    cmd.aplicar({"union": op.id, "giro": "180 deg", "desliz": "0 mm"}, ctx)
    (x0, y0, _), (x1, y1, _) = _caja(doc)
    assert (min(x0, y0), max(x1, y1)) == pytest.approx((5, 25), abs=1e-6)    # giró 180° alrededor del centro
    assert doc.estado_final.uniones[op.id]["valores"]["giro"] == pytest.approx(180)


def test_componente_fijo_no_se_mueve_y_limites():
    doc = _doc_dos_cajas()
    res = doc.agregar(OpUnion(doc.nuevo_id(), "Mal", tipo="rigida", origen1=_cara(doc, "op1.c1", (20, 20, 10)),
                              origen2=_cara(doc, "op2.c1", (105, 55, 0))))
    assert res.estado == "error" and "fijo" in res.mensaje
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Desliz", tipo="deslizante", eje_desliz="Z", desliz="50 mm", maximo="5 mm",
                        origen1=_cara(doc, "op2.c1", (105, 55, 0)), origen2=_cara(doc, "op1.c1", (20, 20, 10))))
    (_, _, z0), _ = _caja(doc)
    assert z0 == pytest.approx(15)               # el límite máximo cortó el deslizamiento en 5 mm


def test_union_como_esta_e_insertar_diseno():
    doc = _doc_dos_cajas()
    doc.agregar(OpUnion(doc.nuevo_id(), "Giro", tipo="revolucion", como_esta=True, giro="90 deg",
                        origen1=_cara(doc, "op2.c1", (105, 55, 10))))
    (x0, y0, z0), (x1, y1, z1) = _caja(doc)
    assert (x0, x1, y0, y1, z0, z1) == pytest.approx((100, 110, 50, 60, 0, 10))   # giró sobre su propio centro
    otro = Documento()
    otro.agregar(OpPrimitiva(otro.nuevo_id(), forma="cilindro", radio="3", alto="20"))
    doc.agregar(OpInsertarDiseno(doc.nuevo_id(), "Insertar pasador", archivo="pasador", receta=otro.a_dict()))
    ins = [c for c in doc.estado_final.cuerpos.values() if c.componente == doc.operaciones[-1].id]
    assert len(ins) == 1 and g.volumen(ins[0].forma) == pytest.approx(np.pi * 9 * 20)
    assert Documento.desde_dict(doc.a_dict()).estado_final.componentes
