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
