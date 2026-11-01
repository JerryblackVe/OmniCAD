# -*- coding: utf-8 -*-
"""H-6: menú del timeline con Configurar, Suprimir varios pasos, Buscar en la ventana y Crear conjunto de selección
(Fusion: Use the Timeline, Find in Window, Configure suppression, selection sets)."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QInputDialog  # noqa: E402
from test_ensamblar_asm import _mecanismo  # noqa: E402
from test_hallazgos_ui import _doc_timeline, app_qt as app_qt, v as v, ventana as ventana  # noqa: E402, F401

from omnicad import api  # noqa: E402


def _sesion():
    s = api.Sesion()
    s.doc = _doc_timeline()
    return s


def _llamar(s, herramienta, **args):
    return api.llamar(s, herramienta, args)


def _entrada(t, op_id, texto, ids=None):
    return next(e for e in t.entradas_menu(op_id, ids) if e is not None and e.texto == texto)


# ---------------------------------------------------------------- herramientas
def test_suppress_feature_varios_pasos_es_un_solo_deshacer():
    s = _sesion()
    r = _llamar(s, "suppress_feature", feature=["op2", "Esfera1", "op2"], suppressed=True)
    assert r["ok"] and [f["id"] for f in r["result"]["features"]] == ["op2", "op3"]
    assert s.doc.operacion("op2").suprimida and s.doc.operacion("op3").suprimida
    r = _llamar(s, "suppress_feature", feature=["op2", "op1"], suppressed=True)          # op2 ya estaba
    assert r["ok"] and any("ya estaban" in a for a in r["avisos"]) and s.doc.operacion("op1").suprimida
    assert _llamar(s, "undo")["ok"] and not s.doc.operacion("op1").suprimida
    assert s.doc.operacion("op2").suprimida                                 # el primer deshacer solo revirtió la segunda llamada
    assert _llamar(s, "undo")["ok"]
    assert not s.doc.operacion("op2").suprimida and not s.doc.operacion("op3").suprimida   # la primera: UN deshacer
    assert _llamar(s, "suppress_feature", feature=[])["error_kind"] == "INVALID_ARGUMENTS"
    assert _llamar(s, "suppress_feature", feature=["op2", "nada"])["error_kind"] == "FEATURE_NOT_FOUND"
    assert not s.doc.operacion("op2").suprimida                             # el pedido que falla no deja nada a medias


def test_suprimir_varios_deja_en_rojo_lo_que_depende_en_vez_de_rechazar():
    s = _sesion()
    n = len(s.doc._deshacer)
    r = _llamar(s, "suppress_feature", feature=["op1", "op3"])               # la Extrusión1 (op2) usa el boceto op1
    assert r["ok"] and s.doc.operacion("op1").suprimida and s.doc.operacion("op3").suprimida
    assert s.doc.resultados[1].estado == "error" and any("Extrusión1" in a and "error" in a for a in r["avisos"])
    assert len(s.doc._deshacer) == n + 1                                      # un solo paso de deshacer
    assert _llamar(s, "undo")["ok"]
    assert not s.doc.operacion("op1").suprimida and not s.doc.operacion("op3").suprimida
    assert s.doc.resultados[1].estado == "ok"
    # la tolerancia es solo de la lista: suprimir UNO por la API sigue rechazando lo que rompe (ASM-8)
    uno = _llamar(s, "suppress_feature", feature="op1")
    assert uno["error_kind"] == "OPERATION_FAILED" and not s.doc.operacion("op1").suprimida


def test_asm8_una_lista_de_un_paso_rechaza_igual_que_un_texto():
    """Un vínculo de movimiento usa J1: suprimirla se rechaza con texto y con una lista de uno; con dos pasos se tolera."""
    s, *_ = _mecanismo()
    _llamar(s, "create_motion_link", joint1="J1", joint2="J2", ratio=0.2, name="V")
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    texto = _llamar(s, "suppress_feature", feature="J1")
    uno = _llamar(s, "suppress_feature", feature=["J1"])
    for r in (texto, uno):
        assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and "unión «op7»" in r["mensaje"]
    assert uno["mensaje"] == texto["mensaje"]
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta              # no quedó nada a medias
    suelta = _llamar(s, "create_box", length=5, width=5, height=5, x=500)["result"]["bodies_created"][0]["id"]
    paso_suelto = s.doc.estado_final.cuerpos[suelta].op_id
    _llamar(s, "suppress_feature", feature=paso_suelto)                       # ya suprimido: no cuenta como cambio
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    efectivo_uno = _llamar(s, "suppress_feature", feature=["J1", paso_suelto])  # en la práctica cambia un solo paso
    assert not efectivo_uno["ok"] and efectivo_uno["error_kind"] == "OPERATION_FAILED"
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta
    dos = _llamar(s, "suppress_feature", feature=["J1", "J2"])
    assert dos["ok"] and any("V" in a and "error" in a for a in dos["avisos"])


def test_conjunto_de_seleccion_desde_pasos():
    s = _sesion()
    r = _llamar(s, "manage_selection_sets", action="create", name="Piezas", steps=["op2", "Esfera1"])
    assert r["ok"] and r["result"]["sets"] == [{"name": "Piezas", "bodies": 2, "faces": 0, "edges": 0}]
    r = _llamar(s, "manage_selection_sets", action="select", name="Piezas")
    assert sorted(r["result"]["bodies"]) == ["op2.c1", "op3.c1"]
    sin_cuerpo = _llamar(s, "manage_selection_sets", action="create", name="Vacío", steps=["op1"])
    assert sin_cuerpo["error_kind"] == "BODY_NOT_FOUND"                     # un boceto no crea cuerpos
    # sumar el mismo cuerpo por paso y por nombre no lo repite
    assert _llamar(s, "manage_selection_sets", action="update", name="Piezas", steps=["op2"], bodies=["op2.c1"])["ok"]
    assert _llamar(s, "manage_selection_sets", action="list")["result"]["sets"][0]["bodies"] == 2


def test_find_in_window_con_pasos_pide_la_app_en_vivo_y_encuadra_sus_cuerpos():
    s = _sesion()
    assert _llamar(s, "find_in_window", steps=["op2"])["error_kind"] == "APP_NOT_RUNNING"
    buscados = []
    s.buscar_en_ventana = lambda ids: buscados.append(ids) or {"bodies": ids}
    assert _llamar(s, "find_in_window", steps=["op2", "op3"])["ok"] and buscados == [["op2.c1", "op3.c1"]]
    assert _llamar(s, "find_in_window", steps=["op1"])["error_kind"] == "BODY_NOT_FOUND"


def test_manage_configurations_add_column_toma_el_valor_de_hoy():
    s = _sesion()
    assert _llamar(s, "manage_configurations", action="add_column",
                   column={"type": "suppress", "feature": "op2"})["ok"]                 # tabla vacía: solo la columna
    assert _llamar(s, "manage_configurations", action="add_row", row="Con", values=["no"])["ok"]
    _llamar(s, "suppress_feature", feature="op3")
    r = _llamar(s, "manage_configurations", action="add_column", column={"type": "suppress", "feature": "Esfera1"})
    assert r["ok"] and r["result"]["columns"] == [{"type": "suppress", "feature": "op2"},
                                                  {"type": "suppress", "feature": "op3"}]
    assert r["result"]["rows"] == [{"name": "Con", "values": ["no", "sí"]}]            # op3 estaba suprimida hoy
    assert _llamar(s, "manage_configurations", action="add_column",
                   column={"type": "suppress", "feature": "op3"})["error_kind"] == "INVALID_ARGUMENTS"   # repetida
    assert _llamar(s, "manage_configurations", action="add_column")["error_kind"] == "INVALID_ARGUMENTS"
    assert len(s.doc.configuraciones["columnas"]) == 2                          # el rechazo no dejó nada a medias
    assert _llamar(s, "undo")["ok"] and len(s.doc.configuraciones["columnas"]) == 1


# ---------------------------------------------------------------- menú del panel
def test_menu_del_timeline_tiene_las_entradas_nuevas(app_qt):
    from omnicad.ui.panel_timeline import PanelTimeline
    t = PanelTimeline()
    t.actualizar(_doc_timeline())
    for op_id in ("op1", "op2", "op3", "op4"):
        textos = [e.texto for e in t.entradas_menu(op_id) if e is not None]
        for nueva in ("Configurar", "Buscar en la ventana", "Crear conjunto de selección…"):
            assert nueva in textos
    assert not _entrada(t, "op1", "Buscar en la ventana").habilitada          # el boceto no creó cuerpos
    assert not _entrada(t, "op1", "Crear conjunto de selección…").habilitada
    assert _entrada(t, "op2", "Buscar en la ventana").habilitada and _entrada(t, "op3", "Crear conjunto de selección…").habilitada
    assert _entrada(t, "op2", "Configurar").habilitada


def test_menu_con_varios_pasos_elegidos(app_qt):
    from omnicad.ui.panel_timeline import PanelTimeline
    t = PanelTimeline()
    doc = _doc_timeline()
    t.actualizar(doc)
    suprimir, buscar, conjunto = [], [], []
    t.suprimir_varios.connect(lambda ids, v: suprimir.append((ids, v)))
    t.buscar_ventana.connect(buscar.append)
    t.crear_conjunto.connect(conjunto.append)
    ids = ["op2", "op3"]
    _entrada(t, "op2", "Suprimir 2 pasos", ids).funcion()
    _entrada(t, "op3", "Buscar en la ventana", ids).funcion()
    _entrada(t, "op2", "Crear conjunto de selección…", ids).funcion()
    assert suprimir == [(ids, True)] and buscar == [ids] and conjunto == [ids]
    assert not _entrada(t, "op2", "Configurar", ids).habilitada               # una columna por paso: de a uno
    doc.operacion("op2").suprimida = True
    t.actualizar(doc)
    assert any(e is not None and e.texto == "Desuprimir 2 pasos" for e in t.entradas_menu("op2", ids))
    # un paso fuera de lo elegido ignora la elección: menú de un solo paso
    textos = [e.texto for e in t.entradas_menu("op1", ids) if e is not None]
    assert "Suprimir boceto" in textos and not any("2 pasos" in x for x in textos)
    assert t.lista.selectionMode() == t.lista.SelectionMode.ExtendedSelection


# ---------------------------------------------------------------- ventana
def test_ventana_ejecuta_las_cuatro_entradas(v, monkeypatch):
    v.set_documento(_doc_timeline())
    tl = v.timeline
    tl.suprimir_varios.emit(["op2", "op3"], True)
    assert v.doc.operacion("op2").suprimida and v.doc.operacion("op3").suprimida
    v.doc.deshacer()                                                           # un solo paso de deshacer
    assert not v.doc.operacion("op2").suprimida and not v.doc.operacion("op3").suprimida

    tl.suprimir_varios.emit(["op1", "op3"], True)                              # lo que depende queda en rojo, no se rechaza
    assert v.doc.operacion("op1").suprimida and v.doc.resultados[1].estado == "error"
    v.doc.deshacer()
    assert not v.doc.operacion("op1").suprimida and v.doc.resultados[1].estado == "ok"

    tl.configurar.emit("op2")
    assert v.doc.configuraciones["columnas"] == [{"tipo": "suprimir", "op": "op2"}]
    tl.configurar.emit("op2")                                                  # ya estaba: avisa y no repite
    assert len(v.doc.configuraciones["columnas"]) == 1

    tl.buscar_ventana.emit(["op2"])
    assert [h["ref"]["cuerpo"] for h in v.seleccion] == ["op2.c1"]
    assert tl.lista.currentItem().data(0x100) == "op2"                         # Qt.UserRole: el paso creador queda elegido

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Mi conjunto", True)))
    tl.crear_conjunto.emit(["op2", "op3"])
    assert v.doc.espacios["conjuntos_seleccion"]["Mi conjunto"] == [{"tipo": "cuerpo", "cuerpo": "op2.c1"},
                                                                    {"tipo": "cuerpo", "cuerpo": "op3.c1"}]
    propuestos = []
    aceptar = staticmethod(lambda *a, **k: (propuestos.append(k["text"]) or k["text"], True))
    monkeypatch.setattr(QInputDialog, "getText", aceptar)
    tl.crear_conjunto.emit(["op2"])                        # hay «Mi conjunto»: propone «Conjunto 2»
    v.doc.espacios["conjuntos_seleccion"]["Conjunto 3"] = [{"tipo": "cuerpo", "cuerpo": "op2.c1"}]
    del v.doc.espacios["conjuntos_seleccion"]["Conjunto 2"]
    tl.crear_conjunto.emit(["op3"])                        # hay dos y «Conjunto 3» (= largo + 1) ya existe: sube hasta uno libre
    assert propuestos == ["Conjunto 2", "Conjunto 4"], propuestos
    assert sorted(v.doc.espacios["conjuntos_seleccion"]) == ["Conjunto 3", "Conjunto 4", "Mi conjunto"]
    antes = sorted(v.doc.espacios["conjuntos_seleccion"])
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))     # Cancelar: nada
    tl.crear_conjunto.emit(["op2"])
    assert sorted(v.doc.espacios["conjuntos_seleccion"]) == antes


def _centro(lista, op_id):
    item = next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == op_id)
    return lista.visualItemRect(item).center()


def _arrastrar_paso(lista, que, antes_de):
    """Aprieta el botón sobre `que` (evento simulado) y lo suelta sobre `antes_de`. El arrastre del sistema (QDrag) no se
    puede manejar con eventos simulados: el soltar es un QDropEvent armado a mano sobre la mitad izquierda del destino."""
    QTest.mousePress(lista.viewport(), Qt.LeftButton, Qt.NoModifier, _centro(lista, que))
    destino = _centro(lista, antes_de)
    lista.dropEvent(QDropEvent(QPointF(destino.x() - 8, destino.y()), Qt.MoveAction, QMimeData(), Qt.LeftButton,
                               Qt.NoModifier))
    QTest.mouseRelease(lista.viewport(), Qt.LeftButton, Qt.NoModifier, _centro(lista, que))


def test_arrastrar_un_paso_con_dos_elegidos_mueve_solo_el_arrastrado(v):
    """Ctrl+clic eligió dos pasos: Qt deja como actual al que se aprieta, así que `_Lista.dropEvent` mueve ese y no el
    último que se eligió con Ctrl."""
    v.set_documento(_doc_timeline())
    lista = v.timeline.lista
    for primero, segundo in (("op3", "op4"), ("op4", "op3")):                  # se arrastra el 1.º y el 2.º elegido
        v.set_documento(_doc_timeline())
        QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, _centro(lista, primero))
        QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.ControlModifier, _centro(lista, segundo))
        assert sorted(v.timeline.elegidos()) == ["op3", "op4"]
        _arrastrar_paso(lista, primero, "op1")
        orden = [o.id for o in v.doc.operaciones]
        assert orden[0] == primero and orden[1:] == [i for i in ("op1", "op2", "op3", "op4") if i != primero], orden
