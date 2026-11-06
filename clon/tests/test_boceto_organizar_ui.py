# -*- coding: utf-8 -*-
"""Navegador del boceto en edición, como lo usa una persona: categorías, clics, ojo, clic derecho y deshacer."""
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox

from omnicad.restricciones import Boceto
from omnicad.restricciones import objetos as ob


@pytest.fixture
def ventana(tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    b.agregar_rectangulo((-40, 0), (-20, 10))
    svg = ob.crear(b, b.agregar_rectangulo((10, 10), (50, 30)), "logo.svg")
    b.objetos[svg]["tipo_origen"] = "SVG"
    disco = ob.crear(b, [b.agregar_circulo((80, 20), 6)], "Disco")
    doc = Documento()
    doc.agregar(OpBoceto("sk", "Boceto1", boceto=b, plano="XY"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    app.processEvents()
    yield v, svg, disco
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _clic(nav, clave, mods=Qt.NoModifier, ojo=False):
    it = nav.item(clave)
    assert it is not None, clave
    nav.revelar(clave)
    rect = nav.arbol.visualItemRect(it)
    pos = QPoint(rect.left() + 12, rect.center().y()) if ojo else QPoint(rect.left() + 60, rect.center().y())
    QTest.mouseClick(nav.arbol.viewport(), Qt.LeftButton, mods, pos)
    QApplication.processEvents()


def _menu(v, clave, elegir):
    """Clic derecho sobre la fila (o el área vacía con clave None) y elige la acción por su texto."""
    nav = v.navegador
    if clave is None:
        rect = nav.arbol.viewport().rect()
        pos = QPoint(rect.center().x(), rect.bottom() - 2)
        assert nav.arbol.itemAt(pos) is None
    else:
        nav.revelar(clave)
        r = nav.arbol.visualItemRect(nav.item(clave))
        pos = QPoint(r.left() + 60, r.center().y())
    vistos = []

    def elegir_accion():
        m = next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible())
        textos = {a.text(): a for a in m.actions()} | {a.text(): a for s in m.actions() if s.menu()
                                                       for a in s.menu().actions()}
        vistos.append(textos)
        accion = textos.get(elegir)
        m.close()
        if accion is not None and accion.isEnabled():
            accion.trigger()
    QTimer.singleShot(0, elegir_accion)
    nav.arbol.customContextMenuRequested.emit(pos)
    QApplication.processEvents()
    return vistos[0]


def test_entrar_al_boceto_muestra_categorias_y_salir_las_quita(ventana):
    v, svg, disco = ventana
    nav = v.navegador
    assert nav.item("bk:geometrias") is None
    v.editar_operacion("sk")
    QApplication.processEvents()
    assert "En edición" in nav.item("sk").text(0)
    assert nav.item("bk:geometrias").text(0) == "Geometrías (5)"          # 4 líneas sueltas + el disco
    assert nav.item("bk:vectores").text(0) == "SVG / DXF (1)"
    assert nav.item(f"bo:{svg}").parent() is nav.item("bk:vectores")
    nav.filtro.setText("logo")                                         # buscar por nombre
    assert not nav.item(f"bo:{svg}").isHidden() and nav.item(f"bo:{disco}").isHidden()
    nav.filtro.clear()
    v.modo_boceto.terminar()
    QApplication.processEvents()
    assert nav.item("bk:geometrias") is None and "En edición" not in nav.item("sk").text(0)
    v.editar_operacion("sk")                                           # al volver, la organización sigue ahí
    QApplication.processEvents()
    assert nav.item(f"bo:{svg}") is not None


def test_seleccion_sincronizada_ojo_y_renombrar(ventana):
    v, svg, disco = ventana
    nav = v.navegador
    v.editar_operacion("sk")
    QApplication.processEvents()
    lz = v.modo_boceto.lienzo
    _clic(nav, f"bo:{svg}")
    assert lz.objetos.seleccion() == [svg]
    _clic(nav, f"bo:{disco}", Qt.ControlModifier)                      # Ctrl suma
    assert sorted(lz.objetos.seleccion()) == sorted([svg, disco])
    lz.seleccion = [disco]                                            # el visor elige → el navegador lo muestra
    lz._notificar_seleccion()
    assert [i.data(0, Qt.UserRole) for i in nav.arbol.selectedItems()] == [f"bo:{disco}"]
    _clic(nav, f"bo:{disco}", ojo=True)                                # el ojo oculta sin sacarlo de los perfiles
    assert lz.b.objetos[disco]["visible"] is False and lz.b.objetos[disco].get("perfiles", True)
    assert disco not in {ob.indice(lz.b)[c][0] for c in ob.curvas_visibles(lz.b) if c in ob.indice(lz.b)}
    lz.deshacer()
    QApplication.processEvents()
    assert lz.b.objetos[disco]["visible"] is True
    it = nav.item(f"bo:{svg}")
    nav.renombrar_en_linea(it)                                         # doble clic / F2: renombrar en el lugar
    editor = nav.arbol.focusWidget() or nav.arbol.viewport()
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(editor, "Marca")
    QTest.keyClick(editor, Qt.Key_Return)
    QApplication.processEvents()
    assert lz.b.objetos[svg]["nombre"] == "Marca"
    assert nav.item(f"bo:{svg}").text(0).startswith("Marca")


def test_menus_del_clic_derecho_y_deshacer(ventana, monkeypatch):
    v, svg, disco = ventana
    nav = v.navegador
    v.editar_operacion("sk")
    QApplication.processEvents()
    lz = v.modo_boceto.lienzo
    perfiles = lambda: len(v.modo_boceto.lienzo.b.geometria())  # noqa: E731
    textos = _menu(v, f"bo:{disco}", "Participar en perfiles")
    for esperado in ("Editar", "Renombrar…", "Mover / Rotar", "Escalar", "Horizontal", "Duplicar", "Agrupar",
                     "Ocultar", "Aislar", "Bloquear", "Participar en perfiles", "Propiedades", "Eliminar…"):
        assert esperado in textos, esperado
    assert lz.b.objetos[disco]["perfiles"] is False and "[sin perfiles]" in nav.item(f"bo:{disco}").text(0)
    from omnicad.nucleo.perfiles import detectar_boceto
    assert not any(p.firma <= set(ob.curvas(lz.b, [disco])) for p in detectar_boceto(lz.b, v.modo_boceto.plano))
    _menu(v, f"bo:{disco}", "Bloquear")
    assert lz.b.objetos[disco]["bloqueado"] and "[bloqueado]" in nav.item(f"bo:{disco}").text(0)
    textos = _menu(v, f"bo:{disco}", "Eliminar…")
    assert not textos["Eliminar…"].isEnabled() and "Desbloque" in textos["Eliminar…"].toolTip()
    _menu(v, f"bo:{disco}", "Desbloquear")
    caja = ob.caja(lz.b, [svg])
    _menu(v, f"bo:{svg}", "Horizontal")                              # Reflejar › Horizontal, en su lugar
    assert ob.caja(lz.b, [svg]) == pytest.approx(caja)
    assert ob.acumulada(lz.b, svg)[0, 0] == pytest.approx(-1)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Composición1", True))
    nav.seleccionar([f"bo:{svg}", f"bo:{disco}"])
    _menu(v, f"bo:{svg}", "Agrupar")
    grupo = next(i for i in lz.b.objetos if lz.b.objetos[i]["nombre"] == "Composición1")
    assert nav.item("bk:grupos").text(0) == "Grupos personalizados (1)"
    assert nav.item(f"bg:{grupo}:{svg}") is not None and nav.item(f"bo:{svg}").parent() is nav.item("bk:vectores")
    _menu(v, f"bo:{grupo}", "Aislar grupo")
    assert ob.aislamiento_activo(lz.b)
    suelta = ob.geometria_suelta(lz.b)[0]
    assert not lz._visible(lz.b.curvas[suelta])                      # la geometría suelta tampoco se ve ni se agarra
    textos = _menu(v, None, "Restaurar aislamiento")       # área vacía del navegador
    assert "Crear grupo" in textos and not ob.aislamiento_activo(lz.b)
    _menu(v, f"bo:{grupo}", "Eliminar grupo (conservar objetos)")
    assert grupo not in lz.b.objetos and {svg, disco} <= set(ob.raices(lz.b))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    n = len(lz.b.curvas)
    _menu(v, f"bo:{disco}", "Eliminar…")
    assert disco not in lz.b.objetos and len(lz.b.curvas) == n - 1 and nav.item(f"bo:{disco}") is None
    lz.deshacer()
    QApplication.processEvents()
    assert disco in lz.b.objetos and nav.item(f"bo:{disco}") is not None
    textos = _menu(v, "bk:geometrias", "Ocultar todo")
    assert {"Crear grupo", "Seleccionar contenido", "Mostrar todo", "Aislar categoría", "Contraer"} <= set(textos)
    assert lz.b.objetos[disco]["visible"] is False
    assert perfiles()                                                 # ocultar no borró nada


def test_miembro_de_grupo_se_elige_desde_el_navegador(ventana, monkeypatch):
    v, svg, disco = ventana
    nav = v.navegador
    v.editar_operacion("sk")
    QApplication.processEvents()
    lz = v.modo_boceto.lienzo
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("G", True))
    nav.seleccionar([f"bo:{svg}", f"bo:{disco}"])
    _menu(v, f"bo:{svg}", "Agrupar")
    grupo = next(i for i in lz.b.objetos if lz.b.objetos[i]["nombre"] == "G")
    _clic(nav, f"bg:{grupo}:{disco}")
    assert lz.objetos.seleccion() == [disco]
    assert lz.objetos.caja() == pytest.approx(ob.caja(lz.b, [disco]))
    lz.repaint()                                                      # el marco de un miembro se dibuja sin error
    assert len(lz.objetos.manijas()) == 10


def test_alt_clic_elige_el_objeto_de_abajo():
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    abajo = ob.crear(b, b.agregar_rectangulo((0, 0), (40, 40)), "Abajo")
    arriba = ob.crear(b, [b.agregar_circulo((20, 20), 8)], "Arriba")
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(900, 600)
    lz.ajustar_grilla = lz.objetos.snap = False
    lz.show()
    app.processEvents()
    pos = lz.a_px(20, 20).toPoint()
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, pos)
    assert lz.objetos.seleccion() == [arriba]
    QTest.mouseClick(lz, Qt.LeftButton, Qt.AltModifier, pos)
    assert lz.objetos.seleccion() == [abajo]
    QTest.mouseClick(lz, Qt.LeftButton, Qt.AltModifier, pos)          # en ciclo
    assert lz.objetos.seleccion() == [arriba]
    assert b.a_dict() == Boceto.desde_dict(b.a_dict()).a_dict() and not lz.historial   # elegir no cambia nada
    lz.close()
    lz.deleteLater()
    app.processEvents()


def test_arrastrar_fila_del_arbol_mueve_el_objeto_al_grupo(ventana, monkeypatch):
    v, svg, disco = ventana
    nav = v.navegador
    v.editar_operacion("sk")
    QApplication.processEvents()
    lz = v.modo_boceto.lienzo
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Composición1", True))
    nav.seleccionar([f"bo:{svg}"])
    _menu(v, f"bo:{svg}", "Agrupar")
    grupo = next(i for i in lz.b.objetos if lz.b.objetos[i]["nombre"] == "Composición1")
    assert nav.item(f"bg:{grupo}:{svg}") is not None and nav.item(f"bo:{disco}") is not None
    # arrastrar el disco (suelto) sobre el grupo del árbol: entra al grupo (un paso de deshacer)
    assert nav.arbol.on_dejar_en_grupo(f"bo:{disco}", f"bo:{grupo}") is True
    QApplication.processEvents()
    assert nav.item(f"bg:{grupo}:{disco}") is not None
    # arrastrar sobre un objeto que no es grupo no hace nada
    assert nav.arbol.on_dejar_en_grupo(f"bo:{disco}", f"bo:{svg}") is False
    # arrastrar un grupo sobre sí mismo tampoco
    assert nav.arbol.on_dejar_en_grupo(f"bo:{grupo}", f"bo:{grupo}") is False
    # se deshace en un paso
    lz.deshacer()
    QApplication.processEvents()
    assert nav.item(f"bg:{grupo}:{disco}") is None and nav.item(f"bo:{disco}") is not None


def test_el_arbol_del_navegador_toma_el_foco_del_teclado(ventana):
    v, svg, disco = ventana
    nav = v.navegador
    v.editar_operacion("sk")
    QApplication.processEvents()
    # H-71: el árbol ya no tiene NoFocus, así que las flechas eligen filas
    assert nav.arbol.focusPolicy() != Qt.NoFocus
    nav.arbol.setFocus()
    nav.arbol.setCurrentItem(nav.item("bk:geometrias"))
    QApplication.processEvents()
    QTest.keyClick(nav.arbol, Qt.Key_Down)
    QApplication.processEvents()
    assert nav.arbol.currentItem() is not None and nav.arbol.currentItem() != nav.item("bk:geometrias")
