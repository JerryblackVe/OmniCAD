# -*- coding: utf-8 -*-
"""MALLA por los comandos: insertar, teselar, reducir, cortar, combinar, separar, convertir y exportar."""
import os

import numpy as np
import pytest

from omnicad.io_archivos import exportar as ex
from omnicad.nucleo import geometria as g
from omnicad.nucleo import malla
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_malla import OpInsertarMalla


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _cubo(lado=10.0, x=0.0):
    return malla.desde_brep(g.caja(lado, lado, lado, (x, 0, 0)), refinamiento="bajo")


def _h(doc, cid):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, doc.estado_final)


def _ejecutar(doc, clase, **valores):
    from omnicad.ui.comando import ContextoComando
    cmd, ctx = clase(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(valores)
    res = doc.agregar(cmd.construir(v, ctx))
    assert res.estado in ("ok", "aviso"), res.mensaje


def _doc_mallas():
    doc = Documento()
    doc.agregar(OpInsertarMalla(doc.nuevo_id(), "Insertar cubo", archivo="cubo", datos=_cubo().a_dict()))
    doc.agregar(OpInsertarMalla(doc.nuevo_id(), "Insertar cubo 2", archivo="cubo2", datos=_cubo(10, 5).a_dict()))
    return doc


def test_insertar_y_guardar_la_malla_en_la_receta():
    doc = _doc_mallas()
    c = doc.estado_final.cuerpos["op1.c1"]
    assert c.tipo == "malla" and c.forma.volumen() == pytest.approx(1000)
    otro = Documento.desde_dict(doc.a_dict())
    assert otro.estado_final.cuerpos["op1.c1"].forma.volumen() == pytest.approx(1000)


def test_combinar_cortar_separar_y_convertir():
    from omnicad.ui.comandos.malla import CombinarMallas, Convertir, CortarPlano, Separar
    doc = _doc_mallas()
    _ejecutar(doc, CombinarMallas, objetivo=[_h(doc, "op1.c1")], herramientas=[_h(doc, "op2.c1")], operacion="unir")
    assert doc.estado_final.cuerpos["op1.c1"].forma.volumen() == pytest.approx(1500, rel=1e-6)
    from omnicad.timeline.operaciones import OpPlano
    from omnicad.ui.comando import hit_desde_ref
    doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="5 mm"))
    _ejecutar(doc, CortarPlano, cuerpos=[_h(doc, "op1.c1")],
              plano=[hit_desde_ref({"tipo": "plano", "id": "op4"}, doc.estado_final)], tipo="partir")
    vols = sorted(c.forma.volumen() for c in doc.estado_final.cuerpos.values())
    assert vols == pytest.approx([750, 750], rel=1e-6)
    doc2 = Documento()
    doc2.agregar(OpInsertarMalla(doc2.nuevo_id(), "dos", archivo="dos", datos=malla.Malla(
        np.concatenate([_cubo().vertices, _cubo(10, 30).vertices]),
        np.concatenate([_cubo().caras, _cubo(10, 30).caras + len(_cubo().vertices)])).a_dict()))
    _ejecutar(doc2, Separar, cuerpos=[_h(doc2, "op1.c1")])
    assert len(doc2.estado_final.cuerpos) == 2
    _ejecutar(doc2, Convertir, cuerpos=[_h(doc2, "op1.c1")])
    convertido = [c for c in doc2.estado_final.cuerpos.values() if c.tipo == "solido"]
    assert convertido and g.volumen(convertido[0].forma) == pytest.approx(1000)


def test_teselar_reducir_y_exportar(tmp_path):
    from omnicad.ui.comandos.malla import Reducir, Teselar
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="10"))
    _ejecutar(doc, Teselar, cuerpos=[_h(doc, "op1.c1")], refinamiento="medio")
    mid = next(c for c, cu in doc.estado_final.cuerpos.items() if cu.tipo == "malla")
    antes = len(doc.estado_final.cuerpos[mid].forma.caras)
    _ejecutar(doc, Reducir, cuerpos=[_h(doc, mid)], tipo="proporcion", proporcion="0.5")
    m = doc.estado_final.cuerpos[mid].forma
    assert len(m.caras) <= antes * 0.55 and m.volumen() == pytest.approx(4 / 3 * np.pi * 1000, rel=0.06)
    cuerpos = list(doc.estado_final.cuerpos.values())
    for ext in ("3mf", "ply", "stl", "obj"):
        ruta = tmp_path / f"modelo.{ext}"
        ex.exportar(cuerpos, ruta)
        assert ruta.stat().st_size > 100
    ruta = tmp_path / "modelo.iges"
    ex.exportar([doc.estado_final.cuerpos["op1.c1"]], ruta)
    assert ruta.stat().st_size > 100
