# -*- coding: utf-8 -*-
"""Diálogo Parámetros como una persona: doble clic en la celda, teclear, Enter, estrella, filtros, orden e importar."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from omnicad import api
from omnicad.ui.campo_expresion import CampoExpresion, nombres_sugeridos
from omnicad.ui.comando import ContextoComando
from omnicad.ui.dialogo_parametros import (COMENTARIOS, EXPRESION, NOMBRE, PARAMETRO, UNIDAD, VALOR, DialogoParametros,
                                           texto_valor)


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def s(app_qt):
    s = api.Sesion()
    llamar(s, "create_parameter", name="w", expression="10 mm", comment="Ancho 9")
    llamar(s, "create_parameter", name="h", expression="w * 2", comment="Alto 10")
    llamar(s, "create_box", length="w", width="h", height=5, name="Caja")
    return s


@pytest.fixture
def dlg(s):
    d = DialogoParametros(s.doc)
    d.show()
    QTest.qWait(20)
    yield d
    d.close()


def fila(d, nombre):
    return d.arbol.findItems(nombre, Qt.MatchExactly | Qt.MatchRecursive, NOMBRE)[-1]


def editar(d, nombre, columna, texto):
    """Doble clic en la celda, teclear y Enter."""
    item = fila(d, nombre)
    d.arbol.scrollToItem(item)
    d.arbol.setCurrentItem(item, columna)
    d.arbol.editItem(item, columna)
    QTest.qWait(10)
    editor = QApplication.focusWidget() if isinstance(QApplication.focusWidget(), (QLineEdit, QComboBox)) else None
    editor = editor or d.arbol.findChild(QComboBox) or d.arbol.findChild(QLineEdit)
    if isinstance(editor, QComboBox):
        editor = editor.lineEdit()
    editor.selectAll()
    QTest.keyClick(editor, Qt.Key_Delete)
    QTest.keyClicks(editor, texto)
    QTest.keyClick(editor, Qt.Key_Return)
    QTest.qWait(20)
    d._reloj.stop()
    if d._pendiente:
        d._reloj.timeout.emit()
    QTest.qWait(10)


def volumen(s):
    return llamar(s, "get_scene_info")["bodies"][0]["volume"]


def test_columnas_y_grupos_fijos(dlg):
    assert [dlg.arbol.headerItem().text(i) for i in range(6)] == ["Parámetro", "Nombre", "Unidad", "Expresión", "Valor", "Comentarios"]
    arriba = [dlg.arbol.topLevelItem(i).text(0) for i in range(dlg.arbol.topLevelItemCount())]
    assert arriba == ["Favoritos", "Parámetros de usuario", "Parámetros del modelo"]
    assert dlg.arbol.topLevelItem(0).childCount() == 0
    paso = dlg.arbol.topLevelItem(2).child(0)
    assert paso.text(0) == "Caja1" and paso.childCount() == 3 and paso.child(0).text(UNIDAD) == "mm"


def test_valor_completo_con_unidad():
    assert texto_valor({"value": 12345.678, "unit": "mm"}) == "12345,678 mm"
    assert texto_valor({"value": 2.0, "unit": ""}) == "2"
    assert texto_valor({"value": None, "unit": "mm"}) == "—"
    assert texto_valor({"value": "Hola", "unit": ""}) == "Hola"


def test_teclear_expresion_aplica_con_calculo_automatico(s, dlg):
    editar(dlg, "w", EXPRESION, "20 mm")
    assert volumen(s) == pytest.approx(20 * 40 * 5)
    assert fila(dlg, "w").text(VALOR) == "20 mm" and fila(dlg, "h").text(VALOR) == "40 mm"
    editar(dlg, "w", EXPRESION, "30 mm")
    assert volumen(s) == pytest.approx(30 * 60 * 5)


def test_todo_lo_del_dialogo_es_un_solo_deshacer(s):
    d, antes = DialogoParametros(s.doc), volumen(s)
    d.show()
    editar(d, "w", EXPRESION, "20 mm")
    editar(d, "w", EXPRESION, "30 mm")
    d._aceptar()
    assert not d.isVisible() and volumen(s) == pytest.approx(30 * 60 * 5)
    llamar(s, "undo")
    assert volumen(s) == pytest.approx(antes)


@pytest.mark.parametrize("texto,parte", [("w *", "Sintaxis"), ("", "vacía"), ("30 deg", "ángulo"), ("h", "circular"),
                                         ("d3 * d3", "mm^2")])
def test_valor_malo_queda_en_rojo_y_no_toca_el_modelo(s, dlg, texto, parte):
    antes = volumen(s)
    editar(dlg, "w", EXPRESION, texto)
    assert parte in dlg.error.text() and volumen(s) == antes
    assert fila(dlg, "w").text(EXPRESION) == texto and fila(dlg, "w").foreground(EXPRESION).color().name() != "#000000"
    assert not fila(dlg, "w").isSelected()
    dlg._aceptar()
    assert dlg.isVisible() and "rojo" in dlg.error.text()
    editar(dlg, "w", EXPRESION, "12 mm")
    assert dlg.error.text() == "" and volumen(s) == pytest.approx(12 * 24 * 5)


@pytest.mark.parametrize("texto,valor", [("1,5 mm", "1,5 mm"), ("0", "0 mm"), ("-5 mm", "-5 mm"), ("2 cm", "20 mm"),
                                         ("max(1 mm; 3 mm)", "3 mm"), ("1000000", "1000000 mm")])
def test_valores_de_cada_tipo_en_la_celda(dlg, texto, valor):
    llamar(api.Sesion(dlg.doc), "create_parameter", name="suelto", expression="1 mm")
    editar(dlg, "suelto", EXPRESION, texto)
    assert fila(dlg, "suelto").text(VALOR) == valor


def test_renombrar_desde_la_celda(s, dlg):
    antes = volumen(s)
    editar(dlg, "w", NOMBRE, "ancho")
    assert fila(dlg, "h").text(EXPRESION) == "ancho * 2" and volumen(s) == antes
    assert s.doc.parametros.obtener("h").expresion == "ancho * 2"
    editar(dlg, "h", NOMBRE, "ancho")
    assert "Ya existe" in dlg.error.text()


def test_unidad_comentario_y_estrella(s, dlg):
    editar(dlg, "w", UNIDAD, "cm")
    assert "cm" in fila(dlg, "w").text(VALOR) or "ángulo" in dlg.error.text() or dlg.error.text() == ""
    editar(dlg, "w", COMENTARIOS, "Nuevo")
    assert s.doc.parametros.obtener("w").comentario == "Nuevo"
    dlg.arbol.itemClicked.emit(fila(dlg, "h"), PARAMETRO)
    dlg._reloj.timeout.emit()
    QTest.qWait(10)
    assert dlg.arbol.topLevelItem(0).childCount() == 1 and s.doc.parametros.obtener("h").favorito


def test_unidad_de_un_parametro_del_modelo_no_se_edita(dlg):
    item = fila(dlg, "d1")
    d = dlg.arbol.itemDelegate()
    assert d.createEditor(dlg.arbol.viewport(), None, dlg.arbol.indexFromItem(item, UNIDAD)) is None
    assert d.createEditor(dlg.arbol.viewport(), None, dlg.arbol.indexFromItem(item, VALOR)) is None


def test_editar_un_parametro_del_modelo(s, dlg):
    editar(dlg, "d3", EXPRESION, "7 mm")
    assert s.doc.operacion("op1").p["alto"] == "7 mm" and volumen(s) == pytest.approx(10 * 20 * 7)


def test_filtros_busqueda_y_orden(s, dlg):
    llamar(s, "set_parameter", name="h", favorite=True)
    assert fila(dlg, "h").text(NOMBRE) == "h"
    assert dlg.b_orden.isChecked() and dlg.b_orden.toolTip() == "Ordenar entradas de tabla de parámetros en orden de secuencia temporal"
    dlg.b_favoritos.click()
    assert dlg.arbol.topLevelItem(1).childCount() == 1
    dlg.b_favoritos.click()
    dlg.b_usuario.click()
    assert dlg.arbol.topLevelItem(2).childCount() == 0 and dlg.arbol.topLevelItem(1).childCount() == 2
    dlg.b_usuario.click()
    QTest.keyClicks(dlg.busqueda, "ALTO 1")
    assert dlg.arbol.topLevelItem(1).childCount() == 1 and dlg.arbol.topLevelItem(1).child(0).text(NOMBRE) == "h"
    dlg.busqueda.clear()
    dlg.arbol.header().sectionClicked.emit(NOMBRE)
    assert [dlg.arbol.topLevelItem(1).child(i).text(NOMBRE) for i in range(2)] == ["h", "w"] and not dlg.b_orden.isChecked()
    dlg.arbol.header().sectionClicked.emit(NOMBRE)
    assert [dlg.arbol.topLevelItem(1).child(i).text(NOMBRE) for i in range(2)] == ["w", "h"]
    dlg.arbol.header().sectionClicked.emit(COMENTARIOS)
    assert [dlg.arbol.topLevelItem(1).child(i).text(NOMBRE) for i in range(2)] == ["h", "w"]    # «Alto» antes que «Ancho»
    dlg.b_orden.click()
    assert dlg.b_orden.isChecked() and dlg.arbol.topLevelItem(1).child(0).text(NOMBRE) == "w"


def test_agregar_copiar_y_borrar(s, dlg):
    dlg.b_mas.click()
    n = dlg.dlg_nuevo
    aceptar = n.botones.button(n.botones.StandardButton.Ok)
    assert not aceptar.isEnabled()
    QTest.keyClicks(n.nombre, "espesor")
    QTest.keyClicks(n.expresion, "w / 2")
    assert aceptar.isEnabled() and n.valor.text() == "5 mm"
    n.expresion.clear()
    QTest.keyClicks(n.expresion, "w * h")
    assert not aceptar.isEnabled() and "mm^2" in n.error.text()
    n.unidad.setCurrentText("mm^2")
    assert aceptar.isEnabled() and n.valor.text() == "200 mm^2"
    n.unidad.setCurrentText("mm")
    n.expresion.clear()
    QTest.keyClicks(n.expresion, "w / 2")
    QTest.keyClicks(n.comentario, "Pared")
    aceptar.click()
    QTest.qWait(10)
    dlg._reloj.timeout.emit()
    QTest.qWait(10)
    assert "espesor" in s.doc.parametros and s.doc.parametros.valores()["espesor"] == 5
    assert not dlg.b_copiar.isEnabled()
    dlg.arbol.setCurrentItem(fila(dlg, "espesor"))
    assert dlg.b_copiar.isEnabled() and dlg.b_borrar.isEnabled()
    dlg.b_copiar.click()
    QTest.qWait(10)
    assert "espesor_copia" in dlg.tabla
    dlg.arbol.setCurrentItem(fila(dlg, "w"))
    dlg.b_borrar.click()
    assert "lo usan" in dlg.error.text() and "w" in dlg.tabla
    dlg.arbol.setCurrentItem(fila(dlg, "espesor_copia"))
    dlg.b_borrar.click()
    QTest.qWait(10)
    assert "espesor_copia" not in dlg.tabla


def test_el_modelo_no_se_borra_ni_se_copia(dlg):
    dlg.arbol.setCurrentItem(fila(dlg, "d1"))
    assert not dlg.b_borrar.isEnabled() and not dlg.b_copiar.isEnabled()


def test_calculo_automatico_apagado(s, dlg):
    assert not dlg.b_aplicar.isVisibleTo(dlg)
    dlg.automatico.click()
    assert dlg.b_aplicar.isVisibleTo(dlg)
    antes = volumen(s)
    item = fila(dlg, "w")
    dlg.arbol.editItem(item, EXPRESION)
    editor = dlg.arbol.findChild(QLineEdit)
    editor.selectAll()
    QTest.keyClicks(editor, "20 mm")
    QTest.keyClick(editor, Qt.Key_Return)
    QTest.qWait(300)
    assert volumen(s) == antes and fila(dlg, "w").text(VALOR) == "20 mm"
    dlg.b_aplicar.click()
    assert volumen(s) == pytest.approx(20 * 40 * 5)


def test_apagado_y_cerrar_sin_aceptar_descarta(s):
    d, antes = DialogoParametros(s.doc), volumen(s)
    d.show()
    d.automatico.click()
    d.tabla.modificar("w", "20 mm")
    d._pendiente = True
    d.reject()
    assert volumen(s) == antes


def test_el_dialogo_sigue_al_documento(s, dlg):
    llamar(s, "set_parameter", name="w", expression="11 mm")
    assert fila(dlg, "w").text(VALOR) == "11 mm"
    llamar(s, "undo")
    assert fila(dlg, "w").text(VALOR) == "10 mm"


def test_renombrar_uno_agregado_sin_aplicar(s):
    d = DialogoParametros(s.doc)
    d.show()
    d.automatico.click()
    d._agregar({"nombre": "nuevo", "expresion": "3 mm", "tipo": "longitud", "comentario": "", "unidad": "mm"})
    QTest.qWait(10)
    fila(d, "nuevo").setText(NOMBRE, "otro")
    QTest.qWait(10)
    assert "otro" in d.tabla and "nuevo" not in d.tabla and "nuevo" not in s.doc.parametros
    d.b_aplicar.click()
    assert "otro" in s.doc.parametros
    d.close()


def test_el_rojo_de_una_fila_borrada_no_traba_aceptar(s, dlg):
    llamar(s, "create_parameter", name="z", expression="1 mm")
    editar(dlg, "z", EXPRESION, "1 +")
    assert dlg._invalidas
    dlg.arbol.setCurrentItem(fila(dlg, "z"))
    dlg.b_borrar.click()
    QTest.qWait(10)
    dlg.b_aceptar.click()
    assert not dlg.isVisible() and "z" not in s.doc.parametros


def test_un_cambio_por_fuera_descarta_lo_no_aplicado_y_avisa(s):
    d = DialogoParametros(s.doc)
    d.show()
    d.automatico.click()
    d.tabla.modificar("w", "20 mm")
    d._cambio()
    llamar(s, "create_box", length=1, width=1, height=1, name="Otra")
    assert not d._pendiente and "descartó" in d.error.text() and d.tabla.obtener("w").expresion == "10 mm"
    assert len(s.doc.operaciones) == 2
    d.close()


def test_importar_con_parametros_seleccionados(s, dlg, tmp_path):
    ruta = tmp_path / "p.csv"
    ruta.write_text("Name,Unit,Expression\nuno,mm,1\ndos,in,2\ntres,kg,3\n", encoding="utf-8")
    dlg.elegir_importacion(str(ruta))
    elegir = dlg.dlg_importar
    assert elegir.lista.count() == 3 and elegir.windowTitle() == "Parámetros seleccionados"
    elegir.lista.item(1).setCheckState(Qt.Unchecked)
    elegir.accept()
    QTest.qWait(10)
    assert "uno" in s.doc.parametros and "tres" in s.doc.parametros and "dos" not in s.doc.parametros
    assert fila(dlg, "tres").text(VALOR) == "3 kg"


def test_importar_csv_roto_avisa(dlg, tmp_path):
    ruta = tmp_path / "p.csv"
    ruta.write_text("sin cabecera\n", encoding="utf-8")
    dlg.elegir_importacion(str(ruta))
    assert "⚠" in dlg.error.text()


def test_exportar_solo_usuario(dlg, tmp_path):
    ruta = tmp_path / "s.csv"
    assert dlg.exportar_csv(str(ruta))
    assert ruta.read_text(encoding="utf-8").count("\n") == 3


def test_campo_alterna_expresion_y_valor(s, app_qt):
    ctx = ContextoComando(s.doc)
    c = CampoExpresion("w * 2", ctx, "longitud")
    cambios = []
    c.textChanged.connect(cambios.append)
    c.accion_fx.setChecked(True)
    assert QLineEdit.text(c) == "20 mm" and c.text() == "w * 2" and c.isReadOnly() and not cambios
    c.accion_fx.setChecked(False)
    assert QLineEdit.text(c) == "w * 2" and not c.isReadOnly()
    c.setText("w +")
    c.accion_fx.setChecked(True)
    assert not c.accion_fx.isChecked() and QLineEdit.text(c) == "w +"


def test_campo_sugiere_favoritos_primero_y_no_despues_de_un_numero(s, app_qt):
    llamar(s, "set_parameter", name="h", favorite=True)
    assert nombres_sugeridos(s.doc.parametros) == ["h", "w"]
    c = CampoExpresion("", ContextoComando(s.doc), "longitud")
    c.show()
    QTest.keyClicks(c, "w")
    assert c.lista.completionCount() == 1
    c.lista.activated[str].emit("w")
    assert c.text() == "w"
    c.clear()
    c.lista.popup().hide()
    QTest.keyClicks(c, "5 m")
    assert not c.lista.popup().isVisible()
    c.close()


def test_contexto_rechaza_la_magnitud_al_teclear(s, app_qt):
    ctx = ContextoComando(s.doc)
    with pytest.raises(ValueError, match="mm\\^2"):
        ctx.evaluar("w * h")
    assert ctx.evaluar("alto=w * 2") == 20
