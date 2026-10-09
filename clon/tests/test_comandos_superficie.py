# -*- coding: utf-8 -*-
"""SUPERFICIE y CONSTRUIR por los diálogos de comando."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpPlano, OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _h(doc, ref):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref(ref, doc.estado_final)


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    op = cmd.construir(v, ctx)
    res = doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    return op


def _boceto(doc, plano="XY", lineas=(), rect=None):
    b = Boceto()
    ids = [b.agregar_linea(a, c) for a, c in lineas]
    if rect:
        ids += b.agregar_rectangulo(*rect)
    op = OpBoceto(doc.nuevo_id(), plano=plano, boceto=b)
    doc.agregar(op)
    return op.id, ids


def _curvas(doc, bid, ids):
    return [_h(doc, {"tipo": "curva_boceto", "boceto": bid, "curva": i}) for i in ids]


def _ultimo(doc):
    return list(doc.estado_final.cuerpos.values())[-1]


def test_extruir_revolucion_y_parche_de_superficie():
    from omnicad.ui.comandos.superficie import Parche, SupExtruir, SupRevolucion
    doc = Documento()
    bid, ids = _boceto(doc, lineas=[((0, 0), (10, 0))])
    _ejecutar(doc, SupExtruir, curvas=_curvas(doc, bid, ids), distancia="5 mm")
    c = _ultimo(doc)
    assert c.tipo == "superficie" and g.area(c.forma) == pytest.approx(50)
    bid, ids = _boceto(doc, plano="XZ", lineas=[((5, 0), (5, 10))])
    _ejecutar(doc, SupRevolucion, curvas=_curvas(doc, bid, ids), eje=[_h(doc, {"tipo": "eje", "id": "Z"})])
    assert g.area(_ultimo(doc).forma) == pytest.approx(2 * math.pi * 5 * 10, rel=1e-6)
    bid, ids = _boceto(doc, rect=((0, 0), (10, 10)))
    _ejecutar(doc, Parche, contorno=_curvas(doc, bid, ids))
    assert g.area(_ultimo(doc).forma) == pytest.approx(100)


def test_engrosar_recortar_coser_y_descoser():
    from omnicad.ui.comandos.superficie import Coser, Descoser, Engrosar, Parche, Recortar
    doc = Documento()
    bid, ids = _boceto(doc, rect=((0, 0), (10, 10)))
    _ejecutar(doc, Parche, contorno=_curvas(doc, bid, ids))
    parche = _ultimo(doc)
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="YZ", distancia="5 mm"))
    cara = refs.subformas(parche.forma, "cara")[0]
    region = _h(doc, refs.referencia(parche.id, cara, parche.forma))
    region["punto"] = np.array([2.0, 5.0, 0.0])
    _ejecutar(doc, Recortar, herramienta=[_h(doc, {"tipo": "plano", "id": "op3"})], region=[region])
    assert g.area(doc.estado_final.cuerpos[parche.id].forma) == pytest.approx(50)
    _ejecutar(doc, Engrosar, caras=[_h(doc, {"tipo": "cuerpo", "cuerpo": parche.id})], espesor="2 mm")
    solido = _ultimo(doc)
    assert solido.tipo == "solido" and g.volumen(solido.forma) == pytest.approx(100)
    doc2 = Documento()
    doc2.agregar(OpPrimitiva(doc2.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    _ejecutar(doc2, Descoser, cuerpos=[_h(doc2, {"tipo": "cuerpo", "cuerpo": "op1.c1"})])
    assert len(doc2.estado_final.cuerpos) == 6
    assert all(c.tipo == "superficie" for c in doc2.estado_final.cuerpos.values())
    _ejecutar(doc2, Coser, cuerpos=[_h(doc2, {"tipo": "cuerpo", "cuerpo": c}) for c in doc2.estado_final.cuerpos])
    (unico,) = doc2.estado_final.cuerpos.values()
    assert unico.tipo == "solido" and g.volumen(unico.forma) == pytest.approx(1000)


def test_construccion_planos_ejes_y_puntos():
    from omnicad.ui.comandos.construir import CATALOGO_LOCAL as C
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="3", alto="10", x="30"))
    forma = doc.estado_final.cuerpos["op1.c1"].forma

    def cara(centro, cid="op1.c1"):
        f = doc.estado_final.cuerpos[cid].forma
        sub = next(s for s in refs.subformas(f, "cara") if np.allclose(refs.firma_cara(s)["centro"], centro))
        return [_h(doc, refs.referencia(cid, sub, f))]

    op = _ejecutar(doc, C["plano_medio"], r0=cara((5, 5, 0)), r1=cara((5, 5, 10)))
    assert doc.estado_final.planos[op.id].origen[2] == pytest.approx(5) and op.nombre == "Plano1"
    lateral = next(s for s in refs.subformas(doc.estado_final.cuerpos["op2.c1"].forma, "cara")
                   if refs.firma_cara(s)["geom"] == "cilindro")
    op = _ejecutar(doc, C["eje_cilindro"], r0=[_h(doc, refs.referencia("op2.c1", lateral))])
    p, d, _ = doc.estado_final.ejes[op.id]
    assert np.allclose(np.abs(d), (0, 0, 1)) and np.allclose(p[:2], (30, 0))
    op = _ejecutar(doc, C["punto_tres_planos"], r0=cara((5, 5, 10)), r1=cara((10, 5, 5)), r2=cara((5, 10, 5)))
    assert np.allclose(doc.estado_final.puntos[op.id][0], (10, 10, 10))
    op = _ejecutar(doc, C["plano_angulo"], r0=[_h(doc, {"tipo": "eje", "id": "X"})], angulo="90 deg")
    assert abs(doc.estado_final.planos[op.id].normal[2]) < 1e-9
    assert forma is not None
