# -*- coding: utf-8 -*-
"""SC9: carpetas del timeline (Fusion: Use the Timeline › Organize features into groups, Rename groups, Edit Group ›
Expand) y copiar/pegar pasos. Una carpeta NO es un paso: no cambia el recálculo ni el orden de ejecución."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QInputDialog  # noqa: E402
from test_hallazgos_ui import _doc_timeline, app_qt as app_qt, v as v, ventana as ventana  # noqa: E402, F401

from omnicad import api  # noqa: E402
from omnicad.timeline.documento import Documento, ErrorDocumento  # noqa: E402
from omnicad.ui.panel_timeline import MARCADOR, PanelTimeline, destino_arrastre  # noqa: E402

GRUPO = "grupo:"              # prefijo de la fila de una carpeta en el timeline (mismo rol que MARCADOR)


def _caja_empalme():
    """Caja 20³ con un empalme de radio 2 en las aristas verticales: op1 caja, op2 empalme."""
    s = api.Sesion()
    cid = api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})["result"]["bodies_created"][0]["id"]
    api.llamar(s, "fillet", {"body": cid, "edges": "|Z", "radius": 2})
    return s


def _tres_cajas():
    s = api.Sesion()
    for x in (0, 50, 100):
        api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": x})
    return s


def _volumen(s):
    return round(sum(b["volume"] for b in api.llamar(s, "get_scene_info")["result"]["bodies"]), 3)


def _chip(lista, gid):
    return next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == GRUPO + gid)


def _entrada_grupo(t, g, texto):
    return next(e for e in t.entradas_grupo(g) if e is not None and e.texto == texto)


def _doble_clic_en(lista, punto):
    """El doble clic como lo hace una persona: aprieta, suelta y llega el doble clic. QTest.mouseDClick solo no
    dispara itemDoubleClicked en esta lista (Qt pide la presión previa), así que el tercer evento se manda a mano,
    como en tests/test_boceto_fase7_ui.py. El suelto FINAL no se simula: en la app real cae dentro del lazo del
    diálogo abierto, donde `PanelTimeline._plegar_bloqueado` lo ignora."""
    vp = lista.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, punto)
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, punto)
    QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseButtonDblClick, QPointF(punto),
                                           QPointF(vp.mapToGlobal(punto)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    QTest.qWait(10)


# ---------------------------------------------------------------- la carpeta, en el documento
def test_agrupar_crea_una_carpeta_sin_tocar_el_timeline():
    s = _tres_cajas()
    doc = s.doc
    antes = [(o.id, o.nombre, o.TIPO, o.suprimida) for o in doc.operaciones]
    v0 = _volumen(s)
    g = doc.agrupar(["op3", "op1", "op2"], "Cajas")
    assert g["nombre"] == "Cajas" and g["plegado"] is False and g["id"]
    assert g["pasos"] == ["op1", "op2", "op3"]                       # en orden del timeline
    assert [(o.id, o.nombre, o.TIPO, o.suprimida) for o in doc.operaciones] == antes      # la carpeta no es un paso
    assert _volumen(s) == v0 and all(r.estado == "ok" for r in doc.resultados)
    assert doc.grupo_de("op2") == g
    assert doc.grupo_de("op4") is None and doc.grupo_de("nada") is None
    with pytest.raises(ErrorDocumento, match="al menos dos"):
        doc.agrupar(["op1"])
    with pytest.raises(ErrorDocumento, match="existe la operación"):
        doc.agrupar(["op1", "op9"])
    assert doc.agrupar(["op1", "op2"], "   ")["nombre"] == "Grupo 2"     # un nombre en blanco no deja carpeta invisible


def test_un_paso_solo_en_una_carpeta():
    doc = _tres_cajas().doc
    a = doc.agrupar(["op1", "op2"], "A")
    b = doc.agrupar(["op2", "op3"], "B")
    assert b["pasos"] == ["op2", "op3"] and a["pasos"] == ["op1"]    # op2 pasa a B y A se queda con lo suyo
    assert sum(1 for g in doc.grupos if "op2" in g["pasos"]) == 1


def test_guardar_y_reabrir_conserva_la_carpeta(tmp_path):
    s = _tres_cajas()
    s.doc.agrupar(["op1", "op2", "op3"], "Maza")
    ruta = api.llamar(s, "save_document", {"path": str(tmp_path / "sc9.omnicad")})["result"]["path"]
    otra = api.Sesion()
    api.llamar(otra, "open_document", {"path": ruta})
    assert [(g["nombre"], g["pasos"], g["plegado"]) for g in otra.doc.grupos] == [("Maza", ["op1", "op2", "op3"], False)]
    assert "grupos" not in _tres_cajas().doc.a_dict()                # sin carpetas, la receta no cambia
    assert Documento.desde_dict(_tres_cajas().doc.a_dict()).grupos == []


def test_una_receta_ajena_con_grupos_raros_se_sanea():
    datos = _tres_cajas().doc.a_dict()
    ids = [o["id"] for o in datos["operaciones"]]
    assert Documento.desde_dict(dict(datos, grupos="no es lista")).grupos == []
    assert Documento.desde_dict(dict(datos, grupos=[{"id": 3, "pasos": ids[:2]}, {"pasos": "raro"}, []])).grupos == []
    basura = [{"id": "g1", "nombre": 5, "pasos": [None, ids[0], ids[0], ids[2], "op999"], "plegado": 0}]
    assert Documento.desde_dict(dict(datos, grupos=basura)).grupos == [
        {"id": "g1", "nombre": "Grupo 1", "pasos": [ids[0], ids[2]], "plegado": False}]     # solo ids reales, sin repetir
    rara = [{"id": "g1", "nombre": "Rara", "pasos": ids[:2], "plegado": "sí"}]
    assert Documento.desde_dict(dict(datos, grupos=rara)).grupos[0]["plegado"] is True


def test_deshacer_y_rehacer_la_carpeta():
    doc = _tres_cajas().doc
    g = doc.agrupar(["op1", "op2"], "Asa")
    doc.deshacer()
    assert doc.grupos == []
    doc.rehacer()
    assert [x["id"] for x in doc.grupos] == [g["id"]] and doc.grupos[0]["nombre"] == "Asa"
    doc.renombrar_grupo(g["id"], "Asa grande")
    doc.deshacer()
    assert doc.grupos[0]["nombre"] == "Asa"
    doc.rehacer()
    assert doc.grupos[0]["nombre"] == "Asa grande"
    doc.desagrupar(g["id"])
    assert doc.grupos == [] and len(doc.operaciones) == 3            # desagrupar deja los pasos
    doc.deshacer()
    assert [x["nombre"] for x in doc.grupos] == ["Asa grande"]


def test_contraer_la_carpeta_no_gasta_un_paso_de_deshacer():
    doc = _tres_cajas().doc
    g = doc.agrupar(["op1", "op2"], "A")
    pasos = [(o.id, o.suprimida) for o in doc.operaciones]
    n = len(doc._deshacer)
    doc.plegar_grupo(g["id"])
    assert doc.grupos[0]["plegado"] is True and [(o.id, o.suprimida) for o in doc.operaciones] == pasos
    assert len(doc._deshacer) == n                                   # contraer no desaloja el deshacer de los cambios reales
    with pytest.raises(ErrorDocumento, match="existe el grupo"):
        doc.plegar_grupo("g404")


def test_suprimir_el_grupo_suprime_sus_tres_pasos():
    uno, otro = _tres_cajas(), _tres_cajas()
    g = uno.doc.agrupar(["op1", "op2", "op3"], "Las tres")
    api.llamar(uno, "suppress_feature", {"feature": g["pasos"], "suppressed": True})
    for i in ("op1", "op2", "op3"):
        api.llamar(otro, "suppress_feature", {"feature": i, "suppressed": True})
    assert all(o.suprimida for o in uno.doc.operaciones)
    assert _volumen(uno) == _volumen(otro) == 0.0
    assert api.llamar(uno, "undo")["ok"] and not any(o.suprimida for o in uno.doc.operaciones)


def test_desagrupar_no_cambia_el_volumen():
    s = _tres_cajas()
    g = s.doc.agrupar(["op1", "op2"], "Dos")
    v0 = _volumen(s)
    s.doc.desagrupar(g["id"])
    assert s.doc.grupos == [] and _volumen(s) == v0 and len(s.doc.operaciones) == 3
    with pytest.raises(ErrorDocumento, match="existe el grupo"):
        s.doc.desagrupar(g["id"])


def test_borrar_un_paso_lo_saca_de_la_carpeta():
    doc = _tres_cajas().doc
    doc.agrupar(["op1", "op2", "op3"], "Tres")
    doc.suprimir("op3", True)                     # op3 ya no lo usa nadie: se puede eliminar
    doc.eliminar("op3")
    assert doc.grupos[0]["pasos"] == ["op1", "op2"]
    doc.eliminar("op2")
    doc.eliminar("op1")
    assert doc.grupos == []                       # sin pasos, sin carpeta


# ---------------------------------------------------------------- copiar y pegar un paso
def test_pegar_un_empalme_da_otro_empalme_con_el_mismo_radio():
    s = _caja_empalme()
    doc = s.doc
    nueva = doc.pegar(doc.operacion("op2").a_dict(), doc.operacion("op2").dependencias())
    assert doc.operaciones[-1] is nueva and nueva.TIPO == "empalme" and nueva.id == "op3"
    assert nueva.p["radio"] == doc.operacion("op2").p["radio"] == "2.0"
    assert [a["cuerpo"] for a in nueva.p["aristas"]] == [a["cuerpo"] for a in doc.operacion("op2").p["aristas"]]
    assert nueva.nombre == "Empalme1 (1)" and len(doc.operaciones) == 3
    assert doc.pegar(doc.operacion("op2").a_dict(), doc.operacion("op2").dependencias()).nombre == "Empalme1 (2)"


def test_pegar_un_paso_sin_referencias_suma_su_geometria():
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    v0 = _volumen(s)
    nueva = s.doc.pegar(s.doc.operacion("op1").a_dict())
    assert s.doc.resultado(nueva.id).estado == "ok"
    assert _volumen(s) == round(v0 * 2, 3)                            # la copia aportó su caja


def test_pegar_un_paso_incompleto_pega_otro_incompleto_sin_reventar():
    doc = _doc_timeline()
    union = doc.operacion("op4")                    # Unión1 sin cuerpos: su estado es error
    nueva = doc.pegar(union.a_dict(), union.dependencias())
    assert nueva.TIPO == "union" and nueva.nombre == "Unión1 (1)"
    assert doc.resultados[-1].estado == "error" and len(doc.operaciones) == 5


def test_pegar_avisa_claro_cuando_una_referencia_no_esta():
    s = _caja_empalme()
    op = s.doc.operacion("op2")
    vacio = Documento()
    with pytest.raises(ErrorDocumento, match="no está en este documento"):
        vacio.pegar(op.a_dict(), op.dependencias())
    assert vacio.operaciones == [] and not vacio.puede_deshacer()


def test_pegar_no_pega_dentro_de_un_tramo_retrocedido():
    s = _caja_empalme()
    s.doc.mover_marcador(0)                                          # todo retrocedido: el marcador abre el timeline
    with pytest.raises(ErrorDocumento, match="después del marcador"):
        s.doc.pegar(s.doc.operacion("op2").a_dict(), s.doc.operacion("op2").dependencias())
    assert len(s.doc.operaciones) == 2


# ---------------------------------------------------------------- la API
def test_manage_feature_groups():
    s = _tres_cajas()
    r = api.llamar(s, "manage_feature_groups", {"action": "create", "steps": ["op1", "op2"], "name": "Bases"})
    assert r["ok"], r
    gid = r["result"]["group"]["id"]
    assert r["result"]["group"] == {"id": gid, "name": "Bases", "steps": ["op1", "op2"], "collapsed": False}
    assert api.llamar(s, "manage_feature_groups", {"action": "rename", "group": gid,
                                                   "name": "Soportes"})["ok"]
    assert api.llamar(s, "manage_feature_groups", {"action": "list"})["result"]["groups"] == [
        {"id": gid, "name": "Soportes", "steps": ["op1", "op2"], "collapsed": False}]
    assert api.llamar(s, "undo")["ok"] and api.llamar(s, "manage_feature_groups", {"action": "list"})[
        "result"]["groups"][0]["name"] == "Bases"
    assert api.llamar(s, "manage_feature_groups", {"action": "ungroup", "group": gid})["ok"] and s.doc.grupos == []
    for args in ({"action": "list", "group": gid}, {"action": "create", "steps": ["op1"]}, {"action": "create"},
                 {"action": "rename", "group": gid}, {"action": "rename", "group": "g1", "name": "  "}):
        assert api.llamar(s, "manage_feature_groups", args)["error_kind"] == "INVALID_ARGUMENTS", args
    assert api.llamar(s, "manage_feature_groups", {"action": "create",
                                                   "steps": ["op1", "op9"]})["error_kind"] == "FEATURE_NOT_FOUND"
    for args in ({"action": "rename", "group": "g404", "name": "x"}, {"action": "ungroup", "group": "g404"}):
        assert api.llamar(s, "manage_feature_groups", args)["error_kind"] == "GROUP_NOT_FOUND", args


def test_duplicate_feature():
    s = _caja_empalme()
    r = api.llamar(s, "duplicate_feature", {"feature": "Empalme1"})
    assert r["ok"] and r["result"]["feature"] == {"id": "op3", "name": "Empalme1 (1)", "type": "empalme"}
    assert r["result"]["index"] == 2 and r["result"]["from"] == "op2"
    assert s.doc.operaciones[-1].p["radio"] == "2.0"
    # las aristas del empalme original ya no están: la copia se pega igual, en rojo y avisada (como en la ventana)
    assert any("quedó con error" in a for a in r["avisos"]), r["avisos"]
    assert api.llamar(s, "undo")["ok"] and len(s.doc.operaciones) == 2
    for feature in ("noexiste", "op1.c1"):
        assert api.llamar(s, "duplicate_feature", {"feature": feature})["error_kind"] == "FEATURE_NOT_FOUND"


def test_get_timeline_muestra_el_grupo_de_cada_paso():
    s = _tres_cajas()
    g = s.doc.agrupar(["op1", "op2"], "Maza")
    esperado = [{"id": g["id"], "name": "Maza"}, {"id": g["id"], "name": "Maza"}, None]
    pasos = api.llamar(s, "get_timeline", {"include_params": False})["result"]["steps"]
    assert [p.get("group") for p in pasos] == esperado               # aparece sin pedir los parámetros


# ---------------------------------------------------------------- el panel (botones y teclas)
def test_mayus_elege_un_rango_y_el_menu_ofrece_agrupar(app_qt):
    t = PanelTimeline()
    doc = _doc_timeline()
    t.actualizar(doc)
    ids = []
    t.agrupar.connect(ids.append)
    lista = t.lista
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, lista.visualItemRect(lista.item(0)).center())
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.ShiftModifier, lista.visualItemRect(lista.item(2)).center())
    elegidos = t.elegidos()
    assert len(elegidos) >= 2, elegidos
    entrada = next(e for e in t.entradas_menu(elegidos[0], elegidos) if e is not None and e.texto.startswith("Agrupar"))
    assert entrada.texto == f"Agrupar {len(elegidos)} pasos" and entrada.habilitada
    entrada.funcion()
    assert ids == [elegidos]
    assert not any(str(e.texto).startswith("Agrupar") for e in t.entradas_menu("op1", ["op1"]) if e is not None)


def test_la_carpeta_va_delante_de_sus_pasos_y_contrae(app_qt):
    t = PanelTimeline()
    doc = _doc_timeline()
    g = doc.agrupar(["op2", "op3"], "Sólidos")
    t.actualizar(doc)
    filas = t.claves()
    assert filas[filas.index(GRUPO + g["id"]) + 1] == "op2"          # la carpeta delante de sus pasos
    assert "op4" in filas and "▾" in _chip(t.lista, g["id"]).text()
    doc.mover("op3", 1)                                              # se arrastró un miembro más atrás
    t.actualizar(doc)
    filas = t.claves()
    assert filas[filas.index(GRUPO + g["id"]) + 1] == "op3"          # la carpeta sigue al paso más antiguo
    t.plegar.connect(lambda gid, p: (doc.plegar_grupo(gid, p), t.actualizar(doc)))
    tocados = []
    t.tocado.connect(tocados.append)
    centro = lambda: t.lista.visualItemRect(_chip(t.lista, g["id"])).center()      # noqa: E731
    QTest.mouseClick(t.lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro())
    assert doc.grupos[0]["plegado"] is False and tocados == []        # un clic en la carpeta no hace nada (no edifica)
    _entrada_grupo(t, g, "Contraer el grupo").funcion()
    filas = t.claves()
    assert GRUPO + g["id"] in filas and "op2" not in filas and "op3" not in filas and "op4" in filas
    assert "▸" in _chip(t.lista, g["id"]).text()                     # cerrada: la flechita lo dice
    _entrada_grupo(t, g, "Expandir el grupo").funcion()
    assert "op2" in t.claves() and "▾" in _chip(t.lista, g["id"]).text()


def test_el_marcador_dentro_de_una_carpeta_contraida_sigue_visible(app_qt):
    t = PanelTimeline()
    doc = _doc_timeline()
    g = doc.agrupar(["op2", "op3"], "Sólidos")
    doc.mover_marcador(2)                                            # el marcador abre justo en op2
    doc.plegar_grupo(g["id"], True)
    t.actualizar(doc)
    assert MARCADOR in t.claves()


def test_menu_y_doble_clic_de_la_carpeta(app_qt, monkeypatch):
    t = PanelTimeline()
    t.show()                                            # el doble clic real necesita la ventana visible
    QTest.qWait(10)
    doc = _doc_timeline()
    g = doc.agrupar(["op2", "op3"], "Sólidos")
    t.actualizar(doc)
    desag, renom, supr, edits = [], [], [], []
    t.desagrupar.connect(desag.append)
    t.renombrar_grupo.connect(lambda gid, nombre: renom.append((gid, nombre)))
    t.suprimir_varios.connect(lambda ids, sup: supr.append((ids, sup)))
    t.editar.connect(edits.append)
    t.plegar.connect(lambda gid, p: (doc.plegar_grupo(gid, p), t.actualizar(doc)))
    entradas = t.entradas_grupo(g)
    textos = [e.texto if e is not None else "-" for e in entradas]
    assert "Renombrar…" in textos and "Desagrupar" in textos and "Suprimir el grupo (2 pasos)" in textos
    assert "Contraer el grupo" in textos                                   # el +/− de Fusion, en el menú
    for e in entradas:
        if e is not None and e.texto in ("Desagrupar", "Suprimir el grupo (2 pasos)"):
            e.funcion()
    assert desag == [g["id"]] and supr == [(["op2", "op3"], True)]
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Maza", True)))
    centro = t.lista.visualItemRect(_chip(t.lista, g["id"])).center()
    _doble_clic_en(t.lista, centro)
    assert renom == [(g["id"], "Maza")] and edits == []              # doble clic en la carpeta NO edita un paso
    assert doc.grupos[0]["plegado"] is False                         # y tampoco la contrajo de paso
    renom.clear()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))      # Esc: descarta
    _doble_clic_en(t.lista, centro)
    assert renom == [] and doc.grupos[0]["plegado"] is False


def test_pegar_un_boceto_con_cotas_se_rechaza_sin_romper_el_documento():
    """Límite honesto de SC9: la copia de un boceto trae las cotas con el MISMO nombre (d1), y dos cotas no pueden
    compartirlo. Se avisa y el documento queda intacto (renombrar las cotas de la copia sería otro pedido)."""
    s = api.Sesion()
    sk = api.llamar(s, "create_sketch", {"plane": "XY"})["result"]["sketch"]["id"]
    rect = api.llamar(s, "draw_rectangle", {"sketch": sk, "x1": 0, "y1": 0, "x2": 20, "y2": 10})["result"]
    api.llamar(s, "add_dimension", {"sketch": sk, "type": "horizontal", "entities": [rect["entities"][0]["id"]],
                                    "value": 25})
    op = s.doc.operacion("op1")
    n = len(s.doc._deshacer)
    with pytest.raises(ValueError, match="d1"):
        s.doc.pegar(op.a_dict(), op.dependencias())
    assert [o.id for o in s.doc.operaciones] == ["op1"]
    assert len(s.doc._deshacer) == n                                   # el rechazo no deja un paso de deshacer fantasma
    assert api.llamar(s, "get_parameters")["result"]["parameters"][0]["name"] == "d1"


def test_doble_clic_en_un_paso_sigue_editando_el_paso(app_qt):
    t = PanelTimeline()
    t.show()
    QTest.qWait(10)
    doc = _doc_timeline()
    doc.agrupar(["op2", "op3"], "Sólidos")
    t.actualizar(doc)
    edits = []
    t.editar.connect(edits.append)
    centro = t.lista.visualItemRect(next(t.lista.item(i) for i in range(t.lista.count())
                                         if t.lista.item(i).data(Qt.UserRole) == "op2")).center()
    _doble_clic_en(t.lista, centro)
    assert edits == ["op2"]


def test_ctrl_c_ctrl_v_duplican_el_paso_elegido(v):
    s = _caja_empalme()
    v.set_documento(s.doc)
    lista = v.timeline.lista
    centro = lista.visualItemRect(next(lista.item(i) for i in range(lista.count())
                                       if lista.item(i).data(Qt.UserRole) == "op2")).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    QTest.keyClick(lista, Qt.Key_C, Qt.ControlModifier)
    QTest.keyClick(lista, Qt.Key_V, Qt.ControlModifier)
    QTest.qWait(10)
    assert [o.id for o in v.doc.operaciones] == ["op1", "op2", "op3"]
    assert v.doc.operaciones[-1].TIPO == "empalme"
    assert v.doc.operaciones[-1].p["radio"] == v.doc.operacion("op2").p["radio"]
    v.timeline._soltado("op3", 1)                                    # arrastrar sigue cayendo en el índice justo
    assert [o.id for o in v.doc.operaciones] == ["op1", "op3", "op2"]


def test_lo_copiado_en_un_documento_no_se_pega_en_otro(v):
    a, b = _caja_empalme(), _tres_cajas()
    v.set_documento(a.doc)
    lista = v.timeline.lista
    centro = lista.visualItemRect(next(lista.item(i) for i in range(lista.count())
                                       if lista.item(i).data(Qt.UserRole) == "op2")).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    QTest.keyClick(lista, Qt.Key_C, Qt.ControlModifier)
    assert v.timeline._copiado is not None
    v.set_documento(b.doc)                                     # se cambió de documento
    assert v.timeline._copiado is None
    QTest.keyClick(lista, Qt.Key_V, Qt.ControlModifier)
    QTest.qWait(10)
    assert [o.id for o in v.doc.operaciones] == ["op1", "op2", "op3"]       # no pegó nada


def test_arrastrar_ignora_las_carpetas():
    assert destino_arrastre(["op1", GRUPO + "g1", "op2", MARCADOR], "op2", 3) == 1
    assert destino_arrastre(["op1", "op2"], "op1", 2) == 1
