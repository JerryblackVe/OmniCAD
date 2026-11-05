# -*- coding: utf-8 -*-
"""FU-6: Empalme con varios grupos de aristas, cada uno con su radio (tabla de Fusion).
El paso (OpEmpalme.conjuntos) y la API (fillet sets) ya lo admitían; acá se prueba el ciclo completo:
núcleo, API, receta vieja y el diálogo con la tabla de conjuntos."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.ops_modificar import OpEmpalme
from omnicad.timeline.operaciones import OpPrimitiva

# Caja de 40 x 30 x 20 (mm). Los empalmes sacan (1 - pi/4) r^2 L por arista recta de largo L.
CAJA = 24000.0
FACTOR = 1 - math.pi / 4


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40 mm", largo="30 mm", alto="20 mm"))
    return doc


def _aristas(doc, z, n=4):
    """Las n aristas del borde de la cara z (0 o 20), como referencias."""
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    medios = [(20, 0, z), (20, 30, z), (0, 15, z), (40, 15, z)]
    salida = []
    for medio in medios[:n]:
        sub = next(s for s in refs.subformas(forma, "arista")
                   if np.allclose(refs.firma(s)["medio"], medio, atol=1e-6))
        salida.append(refs.referencia("op1.c1", sub, forma))
    return salida


def _volumen(doc):
    return g.volumen(doc.estado_final.cuerpos["op1.c1"].forma)


def _op_grupos(doc, radios):
    """Un OpEmpalme con un grupo por radio: [(radio, z), ...] (z = cara cuyas 4 aristas toma)."""
    primero = radios[0]
    op = OpEmpalme(doc.nuevo_id(), "Empalme1", aristas=_aristas(doc, primero[1]), radio=primero[0])
    for radio, z in radios[1:]:
        op.p["conjuntos"].append({"aristas": _aristas(doc, z), "radio": radio})
    res = doc.agregar(op)
    assert res.estado == "ok", res.mensaje
    return op


# ---------------------------------------------------------------- nucleo

def test_dos_grupos_volumen_calculado_a_mano():
    """4 aristas de arriba a 2 mm y las 4 de abajo a 5 mm: volumen a mano dentro de 0,5 % (las esquinas
    del box restan un poco menos que la suma de cilindros, el margen las cubre)."""
    doc = _doc_caja()
    _op_grupos(doc, [("2 mm", 20), ("5 mm", 0)])
    esperado = CAJA - FACTOR * (2 ** 2 + 5 ** 2) * 140
    v = _volumen(doc)
    assert v == pytest.approx(esperado, rel=0.005), f"{v} contra {esperado}"
    assert g.es_valida(doc.estado_final.cuerpos["op1.c1"].forma)


def test_un_grupo_da_lo_mismo_que_hoy():
    doc = _doc_caja()
    _op_grupos(doc, [("2 mm", 20)])
    esperado = CAJA - FACTOR * 4 * 140
    assert _volumen(doc) == pytest.approx(esperado, rel=0.005)


def test_receta_vieja_sin_conjuntos_abre_igual():
    """Una receta del formato anterior (aristas y radio sueltos, sin conjuntos) abre y da el mismo volumen."""
    doc = _doc_caja()
    vieja = dict(aristas=_aristas(doc, 20), tipo_radio="constante", radio="2 mm", cadena_tangente=True)
    op = OpEmpalme(doc.nuevo_id(), "Empalme1", **vieja)
    res = doc.agregar(op)
    assert res.estado == "ok", res.mensaje
    assert _volumen(doc) == pytest.approx(CAJA - FACTOR * 4 * 140, rel=0.005)
    assert op.p["conjuntos"] == []


def test_radio_que_no_entra_da_error_claro():
    doc = _doc_caja()
    op = OpEmpalme(doc.nuevo_id(), "Empalme1", aristas=_aristas(doc, 20), radio="50 mm")
    res = doc.agregar(op)
    assert res.estado == "error"
    assert res.mensaje and res.mensaje.strip() and not res.mensaje.isascii(), res.mensaje


def test_deshacer_y_rehacer_con_dos_grupos():
    doc = _doc_caja()
    _op_grupos(doc, [("2 mm", 20), ("5 mm", 0)])
    con_grupos = _volumen(doc)
    doc.deshacer()
    assert _volumen(doc) == pytest.approx(CAJA)
    doc.rehacer()
    assert _volumen(doc) == pytest.approx(con_grupos)


# ---------------------------------------------------------------- API

def test_api_fillet_acepta_sets_con_radio_por_conjunto():
    """fillet acepta groups/sets: [{"edges": [...], "radius": ...}] además de edges/radius sueltos."""
    from omnicad import api
    doc = _doc_caja()
    s = api.Sesion(doc)
    r = api.llamar(s, "fillet", dict(edges="nearest:[20,0,20]", radius=2,
                                     sets=[dict(edges="nearest:[20,30,0]", radius=5)]))
    assert r["ok"], r
    # «nearest» elige UNA arista de cada grupo (dos aristas de 40 mm en total).
    esperado = CAJA - FACTOR * (2 ** 2 * 40 + 5 ** 2 * 40)
    assert _volumen(doc) == pytest.approx(esperado, rel=0.005)


# ---------------------------------------------------------------- dialogo (QTest)

def _panel(doc, op=None):
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.modificar import Empalme
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    ctx = ContextoComando(doc, op=op)
    visor.set_modelo(doc.estado_en(ctx.indice))
    return PanelComando(Empalme(), ctx, visor), ctx


def _hits(doc, z):
    """Las 4 aristas de la cara z, como hits de selección."""
    from omnicad.ui.comando import hit_desde_ref
    return [hit_desde_ref(r, doc.estado_final) for r in _aristas(doc, z)]


def test_dialogo_agregar_fila_teclear_radio_y_aceptar():
    from PySide6.QtTest import QTest
    doc = _doc_caja()
    panel, ctx = _panel(doc)
    panel.set_valor("aristas", _hits(doc, 20))
    wr = panel.widgets["radio"]                              # el radio del primer grupo
    wr.clear()
    QTest.keyClicks(wr, "2 mm")
    panel.widgets["conjuntos"].agregar.click()               # el + de Fusion: fila nueva
    panel.widgets["conjuntos"].agregar.click()               # dos filas: la elegida es la 2.a
    assert len(panel.valores["_conjuntos"]) == 2
    panel.widgets["conjuntos"].tabla.selectRow(0)            # editar la primera
    panel.set_valor("c_aristas", _hits(doc, 0))
    w = panel.widgets["c_radio"]
    w.clear()
    QTest.keyClicks(w, "5 mm")
    panel._calcular_previa()
    capturada = []

    def _confirmar(op):                     # como la ventana: aplica el paso al documento
        capturada.append(op)
        return doc.agregar(op).estado == "ok"

    panel.confirmar = _confirmar
    panel.aceptar()
    assert capturada and capturada[0].p["conjuntos"][0]["radio"] == "5 mm"
    assert len(capturada[0].p["conjuntos"][0]["aristas"]) == 4
    assert _volumen(doc) == pytest.approx(CAJA - FACTOR * (2 ** 2 + 5 ** 2) * 140, rel=0.005)


def test_dialogo_radio_vacio_da_rojo_y_mensaje():
    from PySide6.QtTest import QTest
    doc = _doc_caja()
    panel, ctx = _panel(doc)
    panel.set_valor("aristas", _hits(doc, 20))
    panel.widgets["conjuntos"].agregar.click()
    panel.set_valor("c_aristas", _hits(doc, 0))
    w = panel.widgets["c_radio"]
    w.clear()                                                # vacío: expresión inválida → rojo y mensaje
    QTest.keyClicks(w, " ")
    panel._calcular_previa()
    assert w.styleSheet() != ""                              # marcado en rojo
    assert panel.mensaje.text().strip() != ""


def test_dialogo_radio_cero_y_negativo_avisan():
    from PySide6.QtTest import QTest
    doc = _doc_caja()
    for texto in ("0", "-1 mm"):
        panel, ctx = _panel(doc)
        panel.set_valor("aristas", _hits(doc, 20))
        panel.widgets["conjuntos"].agregar.click()
        panel.set_valor("c_aristas", _hits(doc, 0))
        w = panel.widgets["c_radio"]
        w.clear()
        QTest.keyClicks(w, texto)
        panel._calcular_previa()
        assert panel.mensaje.text().strip() != "", texto     # mensaje donde la persona mira


def test_dialogo_reabrir_conserva_los_conjuntos():
    """Aceptar, reabrir con doble clic: la tabla muestra los grupos del paso y el radio por fila."""
    doc = _doc_caja()
    panel, ctx = _panel(doc)
    panel.set_valor("aristas", _hits(doc, 20))
    panel.widgets["conjuntos"].agregar.click()
    panel.set_valor("c_aristas", _hits(doc, 0))
    panel.widgets["c_radio"].setText("3 mm")
    panel._calcular_previa()
    capturada = []

    def _confirmar(op):                     # como la ventana: aplica el paso al documento
        capturada.append(op)
        return doc.agregar(op).estado == "ok"

    panel.confirmar = _confirmar
    panel.aceptar()
    op = capturada[0]
    panel2, ctx2 = _panel(doc, op=op)                        # editar el paso (doble clic en el timeline)
    conjuntos = panel2.valores["_conjuntos"]
    assert len(conjuntos) == 1 and conjuntos[0]["radio"] == "3 mm"
    assert len(conjuntos[0]["aristas"]) == 4                 # vuelve como hits para editar
    assert panel2.widgets["c_radio"].text() == "3 mm"        # el editor muestra la fila elegida
    panel2.widgets["c_radio"].setText("1 mm")
    nueva = panel2.comando.construir(panel2.valores, ctx2)
    assert nueva.p["conjuntos"][0]["radio"] == "1 mm"
    panel2.widgets["conjuntos"].quitar.click()               # el - quita la fila elegida
    nueva = panel2.comando.construir(panel2.valores, ctx2)
    assert nueva.p["conjuntos"] == []


def test_dialogo_quitar_fila():
    doc = _doc_caja()
    panel, ctx = _panel(doc)
    panel.set_valor("aristas", _hits(doc, 20))
    panel.widgets["conjuntos"].agregar.click()
    panel.widgets["conjuntos"].agregar.click()
    panel.widgets["conjuntos"].tabla.selectRow(1)
    panel.widgets["conjuntos"].quitar.click()
    assert len(panel.valores["_conjuntos"]) == 1
    panel.widgets["conjuntos"].quitar.click()
    assert panel.valores["_conjuntos"] == []
    panel._calcular_previa()
    assert panel.ultima_op is not None and panel.ultima_op.p["conjuntos"] == []
