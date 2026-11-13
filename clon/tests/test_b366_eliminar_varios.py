# -*- coding: utf-8 -*-
"""B-366: «Eliminar» con varios pasos elegidos del timeline borra toda la selección en UN paso de deshacer
(Fusion: Delete sobre varias operaciones); un paso que usa otro también elegido no cuenta como dependiente."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from test_hallazgos_ui import app_qt as app_qt, v as v, ventana as ventana  # noqa: E402, F401

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento, ErrorDocumento  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto, OpCombinar, OpExtrusion  # noqa: E402

PASOS = ["op1", "op2", "op3", "op4", "op5"]       # Boceto1, Extrusión1, Boceto2, Extrusión2, Combinar1


def _doc():
    doc = Documento()
    for x in (0, 8):
        b = Boceto()
        b.agregar_rectangulo((x, 0), (x + 10, 10))
        n = doc.nuevo_id()
        doc.agregar(OpBoceto(n, f"Boceto{x // 8 + 1}", plano="XY", boceto=b))
        perfil = doc.estado_final.bocetos[n].perfiles[0]
        doc.agregar(OpExtrusion(doc.nuevo_id(), f"Extrusión{x // 8 + 1}", boceto=n,
                                perfiles=[OpExtrusion.referencia_perfil(perfil)], distancia="5", operacion="nuevo"))
    doc.agregar(OpCombinar(doc.nuevo_id(), objetivo="op2.c1", herramientas=["op4.c1"], operacion="unir"))
    return doc


def test_nucleo_borra_la_cadena_entera_en_un_deshacer():
    doc = _doc()
    assert [o.id for o in doc.operaciones] == PASOS
    n = len(doc._deshacer)
    doc.eliminar_varios(["op2", "op1", "op5", "op4", "op3", "op2"])      # desordenado y con un repetido
    assert doc.operaciones == [] and len(doc._deshacer) == n + 1
    doc.deshacer()
    assert [o.id for o in doc.operaciones] == PASOS and all(r.estado == "ok" for r in doc.resultados)


def test_nucleo_un_dependiente_fuera_de_la_seleccion_rechaza_y_lo_nombra():
    doc = _doc()
    antes = len(doc._deshacer)
    with pytest.raises(ErrorDocumento, match=r"la usan Extrusión1\."):
        doc.eliminar_varios(["op1"])
    with pytest.raises(ErrorDocumento, match="Combinar"):
        doc.eliminar_varios(["op1", "op2", "op3", "op4"])               # Combinar1 queda fuera
    with pytest.raises(ErrorDocumento):
        doc.eliminar_varios([])
    assert [o.id for o in doc.operaciones] == PASOS and len(doc._deshacer) == antes     # nada a medias
    doc.eliminar_varios(["op5"])                                         # una sola entrada: igual que eliminar
    doc.eliminar_varios(["op3", "op4"])
    assert [o.id for o in doc.operaciones] == ["op1", "op2"] and doc.resultados[1].estado == "ok"


def test_nucleo_el_marcador_y_los_grupos_se_ajustan():
    doc = _doc()
    doc.agrupar(["op3", "op4"])
    doc.agrupar(["op1", "op2"])
    doc.mover_marcador(4)                                # después de Extrusión2
    doc.eliminar_varios(["op5", "op3", "op4"])
    assert doc.marcador == 2 and [g["pasos"] for g in doc.grupos] == [["op1", "op2"]]
    doc.deshacer()
    assert len(doc.grupos) == 2 and doc.marcador == 4


def test_api_delete_feature_con_lista():
    s = api.Sesion()
    s.doc = _doc()
    r = api.llamar(s, "delete_feature", {"feature": ["op5", "Extrusión2", "op3", "op5"]})
    assert r["ok"] and [f["id"] for f in r["result"]["features"]] == ["op5", "op4", "op3"] and r["result"]["deleted"]
    assert [o.id for o in s.doc.operaciones] == ["op1", "op2"]
    assert api.llamar(s, "undo", {})["ok"] and len(s.doc.operaciones) == 5          # UN deshacer
    assert api.llamar(s, "delete_feature", {"feature": ["op1", "op3"]})["error_kind"] == "FEATURE_IN_USE"
    assert api.llamar(s, "delete_feature", {"feature": []})["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "delete_feature", {"feature": ["op1", "nada"]})["error_kind"] == "FEATURE_NOT_FOUND"
    assert len(s.doc.operaciones) == 5                                   # lo que falla no deja nada a medias
    assert api.llamar(s, "delete_feature", {"feature": "op5"})["result"]["deleted"]    # un texto sigue andando


def _elegir(v, ids):
    """Clic en el primero y Ctrl+clic en los demás, como una persona."""
    lista = v.timeline.lista
    for k, i in enumerate(ids):
        item = next(lista.item(j) for j in range(lista.count()) if lista.item(j).data(Qt.UserRole) == i)
        pos = lista.visualItemRect(item).center()
        QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.ControlModifier if k else Qt.NoModifier, pos)
    assert sorted(v.timeline.elegidos()) == sorted(ids)


def test_menu_dice_eliminar_n_pasos_y_ventana_borra_todo(v):
    v.set_documento(_doc())
    _elegir(v, PASOS)
    textos = [e.texto for e in v.timeline.entradas_menu("op2", v.timeline.elegidos()) if e is not None]
    assert "Eliminar 5 pasos" in textos and "Eliminar" not in textos
    assert "Eliminar" in [e.texto for e in v.timeline.entradas_menu("op2") if e is not None]      # uno solo: «Eliminar»
    next(e for e in v.timeline.entradas_menu("op2", v.timeline.elegidos()) if e and e.texto == "Eliminar 5 pasos").funcion()
    assert v.doc.operaciones == []
    v.doc.deshacer()
    assert [o.id for o in v.doc.operaciones] == PASOS


def test_tecla_supr_en_el_timeline_borra_los_pasos_elegidos(v):
    v.set_documento(_doc())
    v.timeline.lista.setFocus()
    _elegir(v, ["op3", "op4", "op5"])
    QTest.keyClick(v.timeline.lista, Qt.Key_Delete)
    assert [o.id for o in v.doc.operaciones] == ["op1", "op2"]
    v.doc.deshacer()
    assert len(v.doc.operaciones) == 5
    _elegir(v, ["op1"])                       # Supr con un paso que otro usa: avisa con el nombre y no borra nada
    QTest.keyClick(v.timeline.lista, Qt.Key_Delete)
    assert len(v.doc.operaciones) == 5 and "Extrusión1" in v.timeline.estado.toolTip()
