# -*- coding: utf-8 -*-
"""B-417: el doble clic sobre un paso NO elegido del timeline abre la edición al primer intento
(el primer clic no debe reconstruir la lista: Qt descarta el doble clic si el ítem apretado ya no existe)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from test_b366_eliminar_varios import _doc  # noqa: E402
from test_hallazgos_ui import app_qt as app_qt, v as v, ventana as ventana  # noqa: E402, F401


def _doble_clic(v, op_id):
    """Como una persona: apretar, soltar, apretar (doble clic), soltar, con el intervalo real de Qt entre clics."""
    lista = v.timeline.lista
    item = next(lista.item(j) for j in range(lista.count()) if lista.item(j).data(Qt.UserRole) == op_id)
    pos = lista.visualItemRect(item).center()
    vp = lista.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, pos)
    QTest.qWait(60)
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, pos)
    v.timeline.repintar_iconos()                # la lista se rearma entre el primer clic y el doble clic
    QTest.qWait(120)                            # lo que dispare el primer clic (temporizadores, avisos) corre ahora
    QTest.mouseDClick(vp, Qt.LeftButton, Qt.NoModifier, pos)


def test_doble_clic_en_un_paso_no_elegido_abre_la_edicion(v):
    v.set_documento(_doc())
    abiertos = []
    v.timeline.editar.connect(abiertos.append)
    for paso in ("op2", "op4", "op1"):          # extrusiones y un boceto, cada uno sin estar elegido
        abiertos.clear()
        _doble_clic(v, paso)
        assert abiertos == [paso], f"{paso}: el doble clic no abrió la edición ({abiertos})"


def test_doble_clic_en_solevacion_y_otros_tipos_abre_la_edicion(v):
    """B-465: E11 vio que el doble clic en una Solevación no abría el editor; se prueba con cada tipo de paso."""
    from omnicad.restricciones.boceto import Boceto
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
    from omnicad.timeline.ops_solido import OpSolevacion
    doc = _doc()
    b = Boceto()
    b.agregar_circulo((40, 40), 4)
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto3", plano="XY", boceto=b))
    nuevo = doc.operaciones[-1].id
    secciones = [{"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(
        doc.estado_final.bocetos[bid].perfiles[0])} for bid in ("op1", nuevo)]
    doc.agregar(OpSolevacion(doc.nuevo_id(), "Solevación1", secciones=secciones))
    sole = doc.operaciones[-1].id
    v.set_documento(doc)
    abiertos = []
    v.timeline.editar.connect(abiertos.append)
    for paso in (sole, "op5", "op2", "op1"):    # solevación, combinar, extrusión, boceto
        abiertos.clear()
        _doble_clic(v, paso)
        assert abiertos == [paso], f"{paso}: el doble clic no abrió la edición ({abiertos})"


def test_doble_clic_en_solevacion_valida_abre_la_edicion(v):
    """B-465: con una solevación que sí calcula (dos círculos en planos distintos), el doble clic abre la edición."""
    from omnicad.restricciones import Boceto
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPlano
    from omnicad.timeline.ops_solido import OpSolevacion
    doc = Documento()
    ids = []
    for plano, r in (("XY", 10), (None, 6)):
        if plano is None:
            doc.agregar(OpPlano(doc.nuevo_id(), "Plano1", base="XY", distancia="40 mm"))
            plano = doc.operaciones[-1].id
        b = Boceto()
        b.agregar_circulo((0, 0), r)
        n = doc.nuevo_id()
        doc.agregar(OpBoceto(n, f"B{n}", plano=plano, boceto=b))
        ids.append(n)
    secciones = [{"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(
        doc.estado_final.bocetos[bid].perfiles[0])} for bid in ids]
    doc.agregar(OpSolevacion(doc.nuevo_id(), "Solevación1", secciones=secciones))
    sole = doc.operaciones[-1].id
    assert doc.estado_final.cuerpos, "la solevación debería crear un cuerpo"
    v.set_documento(doc)
    abiertos = []
    v.timeline.editar.connect(abiertos.append)
    _doble_clic(v, sole)
    assert abiertos == [sole], f"el doble clic no abrió la edición ({abiertos})"
    assert v.panel is not None, "el doble clic no abrió el panel de edición de la solevación"
