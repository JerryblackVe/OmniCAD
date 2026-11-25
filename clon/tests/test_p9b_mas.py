# -*- coding: utf-8 -*-
"""P9 (segunda tanda): botón «Más» (⋮) de los comandos de los menús de la cinta: Fijar en atajos, Fijar en la barra
y Cambiar atajo de teclado (`ui/mas_comando.py`)."""
import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMenu, QToolButton  # noqa: E402

from omnicad.ui.caja_herramientas import leer_fijados  # noqa: E402
from omnicad.ui.mas_comando import DialogoAtajo, alternar, conflicto, leer_barra, leer_teclas  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402


@pytest.fixture
def ini(tmp_path):
    return str(tmp_path / "p.ini")


def _ventana(ini):
    QApplication.instance() or QApplication([])
    v = VentanaPrincipal(prefs=Preferencias(QSettings(ini, QSettings.IniFormat)))
    v.show()
    QTest.qWait(30)
    return v


def _cerrar(v):
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


@pytest.fixture
def v(ini):
    ventana = _ventana(ini)
    yield ventana
    _cerrar(ventana)


def _menu_de(v, clave):
    return next(m for m in v.cinta.pila.currentWidget().findChildren(QMenu) if v.acciones[clave] in m.actions())


def test_alternar_agrega_al_final_o_quita():
    assert alternar(["a", "b"], "c") == ["a", "b", "c"] and alternar(["a", "b"], "a") == ["b"]


def test_solo_los_comandos_reales_tienen_mas(v):
    f = v._filtro_mas
    assert f.clave(v.acciones["extruir"]) == "extruir" and f.clave(v.acciones["vaciado"]) == "vaciado"
    assert f.clave(None) is None
    menu = next(m for m in v.findChildren(QMenu)          # el menú CREAR: tiene el submenú «Patrón»
                if v.acciones["extruir"] in m.actions() and any(a.menu() for a in m.actions()))
    sub = next(a for a in menu.actions() if a.menu() is not None)
    assert f.clave(sub) is None                                   # un submenú no es un comando
    assert all(f.clave(a) is None for a in v.cinta.no_disponibles)    # lo no disponible no tiene «Más»


def test_clic_en_el_mas_abre_el_menu_y_no_ejecuta_el_comando(v):
    menu = _menu_de(v, "extruir")
    menu.popup(QPoint(40, 40))
    QTest.qWait(30)
    accion = v.acciones["extruir"]
    zona = v._filtro_mas.zona(menu, accion)
    assert menu.actionGeometry(accion).contains(zona) and zona.width() == 22
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, zona.center())
    mas = v._filtro_mas.menu_abierto
    assert [a.text() for a in mas.actions() if a.text()] == ["Anclar en los accesos directos",
                                                           "Anclar en la barra de herramientas",
                                                           "Cambiar las teclas de acceso rápido…"]
    assert v.panel is None                                        # no se abrió el diálogo de Extruir
    acceso, barra = mas.actions()[:2]
    assert acceso.isCheckable() and acceso.isChecked()
    assert barra.isCheckable() and barra.isChecked()
    mas.hide()
    menu.hide()


def test_b768_las_casillas_conservan_el_texto_al_alternar(v):
    filtro = v._filtro_mas
    accion = v.acciones["extruir"]
    textos = ["Anclar en los accesos directos", "Anclar en la barra de herramientas"]
    for estado in ((True, True), (False, False), (True, True)):
        menu = filtro.construir_menu(accion)
        casillas = menu.actions()[:2]
        assert [a.text() for a in casillas] == textos
        assert all(a.isCheckable() for a in casillas)
        assert tuple(a.isChecked() for a in casillas) == estado
        for a in casillas:
            a.trigger()
        menu.deleteLater()


def test_b769_la_casilla_sigue_los_botones_de_la_cinta(v):
    accion = v.acciones["extruir"]
    def botones():
        return [b.defaultAction() for b in v.cinta.pila.currentWidget().findChildren(QToolButton, "boton_cinta")]
    assert accion in botones() and "extruir" not in leer_barra(v.prefs)
    for esperado in (True, False, True):
        menu = v._filtro_mas.construir_menu(accion)
        casilla = menu.actions()[1]
        assert casilla.isChecked() == esperado == (accion in botones())
        casilla.trigger()
        menu.deleteLater()
        QTest.qWait(10)
    assert accion not in botones() and "extruir" not in leer_barra(v.prefs)


def test_b769_mas_resuelve_el_grupo_del_boton_y_no_un_menu_ajeno(v):
    accion = v.acciones["extruir"]
    origen = _menu_de(v, "extruir")
    grupo = origen.parentWidget()
    ajeno = QMenu(v)
    ajeno.addAction(accion)
    assert v._filtro_mas._grupo_cinta(accion, ajeno) is grupo
    actual = v.cinta.pila.currentIndex()
    v.cinta.pila.setCurrentIndex(actual + 1)
    try:
        assert v._filtro_mas._grupo_cinta(accion, origen) is grupo
    finally:
        v.cinta.pila.setCurrentIndex(actual)
        ajeno.deleteLater()


def test_un_clic_fuera_del_mas_sigue_ejecutando_el_comando(v):
    menu = _menu_de(v, "caja")
    menu.popup(QPoint(40, 40))
    QTest.qWait(30)
    fila = menu.actionGeometry(v.acciones["caja"])
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, QPoint(fila.left() + 30, fila.center().y()))
    QTest.qWait(30)
    assert v.panel is not None
    v.panel.close()


def test_fijar_en_atajos_usa_la_lista_del_contexto_y_quita_lo_ya_fijado(v):
    assert leer_fijados(v.prefs, "diseno") == ["extruir", "empalme_3d"]
    assert v._filtro_mas.alternar_atajo("vaciado") == "diseno"
    assert leer_fijados(v.prefs, "diseno") == ["extruir", "empalme_3d", "vaciado"]
    v._filtro_mas.alternar_atajo("extruir")
    assert leer_fijados(v.prefs, "diseno") == ["empalme_3d", "vaciado"]
    assert leer_fijados(v.prefs, "boceto") == []


def test_fijar_en_la_barra_agrega_el_boton_y_al_reabrir_sigue_ahi(ini):
    v1 = _ventana(ini)
    assert v1._lay_fijados.count() == 0
    v1._filtro_mas.alternar_barra("vaciado")
    boton = v1._lay_fijados.itemAt(0).widget()
    assert isinstance(boton, QToolButton) and boton.defaultAction() is v1.acciones["vaciado"]
    _cerrar(v1)
    v2 = _ventana(ini)
    assert leer_barra(v2.prefs) == ["vaciado"] and v2._lay_fijados.count() == 1
    v2._filtro_mas.alternar_barra("vaciado")
    QTest.qWait(10)
    assert v2._lay_fijados.count() == 0 and leer_barra(v2.prefs) == []
    _cerrar(v2)


def test_cambiar_el_atajo_se_aplica_en_el_acto_y_se_guarda(ini):
    v1 = _ventana(ini)
    a = v1.acciones["vaciado"]
    assert a.shortcut().isEmpty()
    assert v1._filtro_mas.cambiar_tecla("vaciado", "Ctrl+Alt+V") == "Ctrl+Alt+V"
    assert a.shortcut() == QKeySequence("Ctrl+Alt+V") and "Alt" in a.text().split("\t")[1]
    assert "Alt" in a.toolTip() and json.loads(v1.prefs["atajos/teclas"]) == {"vaciado": "Ctrl+Alt+V"}
    _cerrar(v1)
    v2 = _ventana(ini)                                            # al reabrir, sigue
    assert v2.acciones["vaciado"].shortcut() == QKeySequence("Ctrl+Alt+V")
    _cerrar(v2)


def test_no_deja_repetir_el_atajo_de_otro_comando(v):
    assert v.acciones["deshacer"].shortcut() == QKeySequence("Ctrl+Z")
    assert conflicto(v.acciones, "vaciado", "Ctrl+Z") == "Deshacer"
    assert v._filtro_mas.cambiar_tecla("vaciado", "Ctrl+Z") is None
    assert v.acciones["vaciado"].shortcut().isEmpty() and leer_teclas(v.prefs) == {}


def test_volver_al_atajo_de_fabrica_borra_la_eleccion(v):
    a = v.acciones["extruir"]
    defecto = a.property("atajo_defecto")
    assert defecto == "E"
    v._filtro_mas.cambiar_tecla("extruir", "Ctrl+Alt+E")
    assert a.shortcut() == QKeySequence("Ctrl+Alt+E")
    v._filtro_mas.cambiar_tecla("extruir", defecto)
    assert a.shortcut() == QKeySequence("E") and leer_teclas(v.prefs) == {}
    v._filtro_mas.cambiar_tecla("extruir", "")                    # «Sin atajo»
    assert a.shortcut().isEmpty() and leer_teclas(v.prefs) == {"extruir": ""}


def test_un_json_roto_de_teclas_no_rompe_la_ventana(ini):
    QApplication.instance() or QApplication([])
    prefs = Preferencias(QSettings(ini, QSettings.IniFormat))
    prefs["atajos/teclas"] = "no es json"
    assert leer_teclas(prefs) == {}
    prefs["atajos/teclas"] = "[1, 2]"
    assert leer_teclas(prefs) == {}
    prefs["atajos/teclas"] = "[" * 100000                         # anidado sin fin: RecursionError, no ValueError
    assert leer_teclas(prefs) == {}
    prefs["atajos/teclas"] = json.dumps({"extruir": None, "vaciado": "Ctrl+Foo", "chaflan_3d": {"a": 1},
                                         "empalme_3d": "Ctrl+Alt+F", "medir": ""})
    assert leer_teclas(prefs) == {"empalme_3d": "Ctrl+Alt+F", "medir": ""}


def test_una_tecla_repetida_a_mano_en_las_preferencias_no_deja_dos_comandos_con_la_misma(ini):
    QApplication.instance() or QApplication([])
    prefs = Preferencias(QSettings(ini, QSettings.IniFormat))
    prefs["atajos/teclas"] = json.dumps({"vaciado": "E"})          # E es la de fábrica de Extruir
    v = _ventana(ini)
    assert v.acciones["extruir"].shortcut() == QKeySequence("E")
    assert v.acciones["vaciado"].shortcut().isEmpty()              # la repetida no se aplica (Qt no dispararía ninguna)
    _cerrar(v)


def test_el_dialogo_avisa_del_conflicto_y_bloquea_aceptar(v):
    dlg = DialogoAtajo("Vaciado", "", "", lambda s: conflicto(v.acciones, "vaciado", s), v)
    ok = dlg.botones.button(QDialogButtonBox.Ok)
    assert ok.isEnabled() and dlg.aviso.text() == ""
    dlg.editor.setKeySequence(QKeySequence("Ctrl+Z"))
    assert not ok.isEnabled() and "Deshacer" in dlg.aviso.text()
    dlg.editor.setKeySequence(QKeySequence("Ctrl+Alt+V"))
    assert ok.isEnabled() and dlg.secuencia() == "Ctrl+Alt+V"
    dlg.restablecer.click()
    assert dlg.secuencia() == ""
    dlg.deleteLater()


def test_p187_las_herramientas_del_boceto_tienen_mas_y_la_cinta_muestra_las_de_fusion(v):
    from omnicad.ui.cinta_boceto import GRUPOS_BOCETO
    assert v._filtro_mas.clave(v.acciones["sk_linea"]) == "sk_linea"
    assert v._filtro_mas.clave(v.acciones["sk_autorestringir"]) == "sk_autorestringir"
    restr = next(g for g in GRUPOS_BOCETO if g[0] == "RESTRICCIONES")[1]
    assert restr[0] == "sk_autorestringir" and len(restr) == 13 and "sk_r_poligono" not in restr
    v._filtro_mas.cambiar_tecla("sk_linea", "Ctrl+Alt+L")
    assert v.acciones["sk_linea"].shortcut().toString() == "Ctrl+Alt+L"


def test_p187_soltar_una_herramienta_en_un_grupo_de_boceto_la_ancla_y_se_guarda(v):
    from PySide6.QtCore import QMimeData
    from PySide6.QtGui import QDropEvent

    from omnicad.api import cinta_personal as cp
    from omnicad.ui.cinta import MIME_COMANDO, _ZonaSoltar
    zona = next(z for z in v.cinta.findChildren(_ZonaSoltar)
                if any(b.defaultAction() is v.acciones["sk_empalme"] for b in z.findChildren(QToolButton)))
    mime = QMimeData()
    mime.setData(MIME_COMANDO, b"sk_chaflan")
    zona.dropEvent(QDropEvent(QPointF(3, 3), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))
    assert cp.leer(v.prefs["cinta/personal"])["BOCETO/MODIFICAR"][-1] == "sk_chaflan"
    avisos = []
    v.cinta.aviso.connect(avisos.append)
    v.cinta.anclar("BOCETO", "MODIFICAR", "sk_chaflan")                 # ya está
    assert avisos == ["Ya está en la barra."]


def test_p187_arrastrar_la_fila_de_un_menu_arma_el_arrastre_con_su_comando(v, monkeypatch):
    from PySide6.QtGui import QMouseEvent

    from omnicad.ui import mas_comando
    from omnicad.ui.cinta import MIME_COMANDO
    vistos = []

    class FalsoDrag:
        def __init__(self, _):
            pass

        def setMimeData(self, m):
            vistos.append(bytes(m.data(MIME_COMANDO)).decode())

        def exec(self, _):
            return 0
    monkeypatch.setattr(mas_comando, "QDrag", FalsoDrag)
    menu = _menu_de(v, "extruir")
    menu.popup(QPoint(40, 40))
    QTest.qWait(30)
    fila = menu.actionGeometry(v.acciones["extruir"]).center()
    f = v._filtro_mas
    for tipo, p, botones in ((QEvent.MouseButtonPress, fila, Qt.LeftButton), (QEvent.MouseMove, fila + QPoint(30, 0), Qt.LeftButton)):
        e = QMouseEvent(tipo, QPointF(p), QPointF(menu.mapToGlobal(p)), Qt.LeftButton, botones, Qt.NoModifier)
        f.eventFilter(menu, e)
    assert vistos == ["extruir"]


def test_p189_la_misma_tecla_en_boceto_y_en_diseno_se_aplica_en_las_dos(v):
    v.prefs["atajos/teclas"] = json.dumps({"vaciado": "Ctrl+Alt+7", "sk_linea": "Ctrl+Alt+7"})
    v.aplicar_teclas()
    assert v.acciones["vaciado"].shortcut().toString() == v.acciones["sk_linea"].shortcut().toString() == "Ctrl+Alt+7"


def test_b770_anclar_al_final_quitar_y_persistir(ini):
    from omnicad.api import cinta_personal as cp
    seccion = "SÓLIDO/CREAR"
    base = cp.SECCIONES[seccion]

    def grupo(v):
        return next(t for t in v.cinta.pila.currentWidget().findChildren(QToolButton, "titulo_grupo")
                    if t.toolTip() == "CREAR")

    def claves(v):
        return [b.defaultAction().property("clave") for b in
                grupo(v).parentWidget().findChildren(QToolButton, "boton_cinta")]

    def alternar_caja(v):
        menu = grupo(v).menu()
        menu.popup(QPoint(40, 40))
        QTest.qWait(30)
        a = v.acciones["caja"]
        QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, v._filtro_mas.zona(menu, a).center())
        mas = v._filtro_mas.menu_abierto
        QTest.mouseClick(mas, Qt.LeftButton, Qt.NoModifier, mas.actionGeometry(mas.actions()[1]).center())
        QTest.qWait(30)

    v = _ventana(ini)
    # Un menú abierto debe alternar sobre la lista vigente, no la capturada al abrirlo.
    retenido = v._filtro_mas.construir_menu(v.acciones["caja"], grupo(v).menu())
    v.cinta.anclar("SÓLIDO", "CREAR", "cilindro")
    retenido.actions()[1].trigger()
    assert claves(v) == [*base, "cilindro", "caja"]
    retenido.deleteLater()
    alternar_caja(v)
    assert claves(v) == [*base, "cilindro"]
    v.cinta.personalizar({})
    v.cinta.cambio_personal.emit({})
    alternar_caja(v)
    assert claves(v) == [*base, "caja"]
    _cerrar(v)
    v = _ventana(ini)
    assert claves(v) == [*base, "caja"]
    # El menú reconstruido al cargar preferencias debe tener filtro «Más».
    alternar_caja(v)
    assert claves(v) == base
    assert seccion not in cp.leer(v.prefs["cinta/personal"])
    _cerrar(v)
    v = _ventana(ini)
    assert claves(v) == base
    _cerrar(v)
