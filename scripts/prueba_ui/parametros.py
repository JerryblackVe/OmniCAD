# -*- coding: utf-8 -*-
"""DISEÑO › Parámetros como una persona: abrir desde la acción, teclear en cada columna, unidades, renombrar, estrella,
filtros, orden, agregar, importar con Parámetros seleccionados, Aceptar, deshacer, reabrir y ventana chica. Después, en
Extruir: `alto=15 mm`, la lista de sugerencias y el ícono fx."""
import os
import sys
import tempfile

import arnes as A
from omnicad import api
from omnicad.ui import ventana as modulo_ventana
from omnicad.ui.dialogo_parametros import COMENTARIOS, EXPRESION, NOMBRE, UNIDAD, VALOR, DialogoParametros
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLineEdit
from teclado import teclear

AR = "PARÁMETROS"
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_parameter", name="ancho", expression="60 mm", comment="Placa")
L("create_parameter", name="alto", expression="ancho / 6", comment="Espesor 10")
L("create_sketch", name="Rect", plane="XY")
L("draw_rectangle", sketch="Rect", x1=0, y1=0, x2=40, y2=30)
L("extrude", sketch="Rect", distance="alto")
s.doc.operaciones[-1].nombre = "Placa"


class Dialogo(DialogoParametros):
    """El de la ventana, abierto como toda ventana de prueba: en minimizada no se ve ni roba el foco."""

    def show(self):
        if A.modo_ventana() == "minimizada":
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
            self.setWindowOpacity(0.0)
        super().show()


modulo_ventana.DialogoParametros = Dialogo
QDialog.open = A.mostrar           # Agregar e Importar: tampoco se ven en minimizada
app, v = A.iniciar(s.doc)


def foto(d, nombre):
    d.grab().save(str(A.CAPTURAS / f"parametros_{nombre}.png"))


def volumen():
    return L("get_scene_info")["bodies"][0]["volume"]


def fila(d, nombre):
    return d.arbol.findItems(nombre, Qt.MatchExactly | Qt.MatchRecursive, NOMBRE)[-1]


def aplicar(d):
    A.esperar(350)              # el reloj de Cálculo automático


def celda(d, nombre, columna, texto):
    """Clic en la celda, F2, teclear, Enter."""
    item = fila(d, nombre)
    d.arbol.setCurrentItem(item, columna)
    d.arbol.scrollToItem(item)
    d.arbol.editItem(item, columna)
    A.esperar(40)
    editor = d.arbol.findChild(QComboBox) or d.arbol.findChild(QLineEdit)
    editor = editor.lineEdit() if isinstance(editor, QComboBox) else editor
    editor.selectAll()
    QTest.keyClick(editor, Qt.Key_Delete)
    QTest.keyClicks(editor, texto)
    QTest.keyClick(editor, Qt.Key_Return)
    aplicar(d)


v.acciones["parametros"].trigger()
A.esperar(200)
d = v.dlg_parametros
A.reg(AR, "la acción abre el diálogo sin bloquear la ventana", d is not None and d.isVisible() and not d.isModal())
titulos = [d.arbol.headerItem().text(i) for i in range(6)]
A.reg(AR, "columnas como Fusion", titulos == ["Parámetro", "Nombre", "Unidad", "Expresión", "Valor", "Comentarios"], titulos)
grupos = [d.arbol.topLevelItem(i).text(0) for i in range(3)]
A.reg(AR, "Favoritos, usuario y modelo fijos", grupos == ["Favoritos", "Parámetros de usuario", "Parámetros del modelo"], grupos)
A.reg(AR, "la extrusión aparece en el modelo", fila(d, "d1").text(EXPRESION) == "alto" or any(
    fila(d, f"d{i}").text(0) == "distancia" for i in range(1, 8) if d.arbol.findItems(f"d{i}", Qt.MatchExactly | Qt.MatchRecursive, NOMBRE)))
foto(d, "1_abierto")

# ---------- teclear en cada columna
inicial = volumen()
celda(d, "ancho", EXPRESION, "120 mm")
A.reg(AR, "expresión: Enter recalcula con Cálculo automático", abs(volumen() - inicial * 2) < 1e-6, volumen())
for texto, esperado in (("12,5 cm", "125 mm"), ("1 in * 5", "127 mm"), ("max(60 mm; 80 mm)", "80 mm"),
                        ("if(1 > 0; 70 mm; 2 mm)", "70 mm"), ("60", "60 mm"), ("1e2 mm", "100 mm")):
    celda(d, "ancho", EXPRESION, texto)
    A.reg(AR, f"expresión «{texto}»", fila(d, "ancho").text(VALOR) == esperado and not d.error.text(), fila(d, "ancho").text(VALOR))
for texto, parte in (("", "vacía"), ("ancho", "circular"), ("abc", "desconocido"), ("30 deg", "ángulo"), ("ancho *", "Sintaxis"),
                     ("60 mm * 2 mm", "mm^2")):
    antes = volumen()
    celda(d, "alto" if texto == "ancho" else "ancho", EXPRESION, "alto" if texto == "ancho" else texto)
    if texto == "ancho":
        celda(d, "ancho", EXPRESION, "alto")
    A.reg(AR, f"«{texto}» en rojo con mensaje", parte in d.error.text() and volumen() == antes, d.error.text())
    foto(d, "error") if parte == "mm^2" else None
    d._invalidas.clear()
    d.error.clear()
    d._poblar()
celda(d, "ancho", EXPRESION, "60 mm")
celda(d, "alto", UNIDAD, "cm")
A.reg(AR, "unidad en la lista: cm", fila(d, "alto").text(UNIDAD) == "cm" and fila(d, "alto").text(VALOR) == "1 cm", fila(d, "alto").text(VALOR))
celda(d, "alto", UNIDAD, "mm")
celda(d, "alto", UNIDAD, "kg")
A.reg(AR, "unidad de otra magnitud: rechazada", "kg" not in fila(d, "alto").text(VALOR) and d.error.text(), d.error.text())
d._invalidas.clear()
d.error.clear()
d._poblar()
celda(d, "alto", COMENTARIOS, "Espesor 8")
A.reg(AR, "comentario", s.doc.parametros.obtener("alto").comentario == "Espesor 8")

# ---------- renombrar, también con pasos que lo citan
paso = s.paso("Placa")
celda(d, "alto", NOMBRE, "espesor")
A.reg(AR, "renombrar actualiza el paso", s.paso("Placa").p["distancia"] == "espesor", paso.id)
celda(d, "espesor", NOMBRE, "ancho")
A.reg(AR, "nombre repetido: rechazado", "Ya existe" in d.error.text(), d.error.text())
d._invalidas.clear()
d.error.clear()
d._poblar()

# ---------- estrella, filtros, búsqueda y orden
rect = d.arbol.visualItemRect(fila(d, "ancho"))
QTest.mouseClick(d.arbol.viewport(), Qt.LeftButton, Qt.NoModifier, rect.topLeft() + type(rect.topLeft())(10, 6))
aplicar(d)
A.reg(AR, "clic en la estrella", d.arbol.topLevelItem(0).childCount() == 1 and s.doc.parametros.obtener("ancho").favorito)
foto(d, "2_favorito")
d.b_favoritos.click()
A.reg(AR, "filtro de favoritos", d.arbol.topLevelItem(1).childCount() == 1)
d.b_favoritos.click()
d.b_usuario.click()
A.reg(AR, "filtro de usuario", d.arbol.topLevelItem(2).childCount() == 0 and d.arbol.topLevelItem(1).childCount() == 2)
d.b_usuario.click()
QTest.keyClicks(d.busqueda, "ESPES")
A.reg(AR, "búsqueda", d.arbol.topLevelItem(1).childCount() == 1 and d.arbol.topLevelItem(1).child(0).text(NOMBRE) == "espesor")
d.busqueda.clear()
cabecera = d.arbol.header()
QTest.mouseClick(cabecera.viewport(), Qt.LeftButton, Qt.NoModifier, cabecera.rect().topLeft() + type(cabecera.rect().topLeft())(
    cabecera.sectionViewportPosition(NOMBRE) + 8, 8))
A.reg(AR, "clic en la cabecera ordena", not d.b_orden.isChecked() and d._orden[0] == "name", d._orden)
d.b_orden.click()
A.reg(AR, "orden temporal", d.b_orden.isChecked() and d._orden[0] == "timeline")

# ---------- agregar y parámetro de otra familia
d.b_mas.click()
A.esperar(80)
n = d.dlg_nuevo
QTest.keyClicks(n.nombre, "masa_total")
n.unidad.setCurrentText("kg")
QTest.keyClicks(n.expresion, "2,5")
QTest.keyClicks(n.comentario, "Del proveedor")        # keyClicks con una tilde cierra el proceso sin avisar
n.grab().save(str(A.CAPTURAS / "parametros_3_agregar.png"))
A.reg(AR, "Agregar: valor calculado", n.valor.text() == "2,5 kg", n.valor.text())
n.botones.button(n.botones.StandardButton.Ok).click()
aplicar(d)
A.reg(AR, "Agregar: entra a la tabla", fila(d, "masa_total").text(VALOR) == "2,5 kg")

# ---------- importar con selección
carpeta = tempfile.mkdtemp()
ruta = os.path.join(carpeta, "p.csv")
with open(ruta, "w", encoding="utf-8") as f:
    f.write("Name,Unit,Expression,Value,Comments,Favorite\ngrosor,in,.75,.75 in,Terciado,true\notro,mm,3,,,false\n")
d.elegir_importacion(ruta)
A.esperar(80)
i = d.dlg_importar
i.grab().save(str(A.CAPTURAS / "parametros_4_importar.png"))
i.lista.item(1).setCheckState(Qt.Unchecked)
i.accept()
aplicar(d)
A.reg(AR, "importar respeta las casillas", "grosor" in s.doc.parametros and "otro" not in s.doc.parametros)
A.reg(AR, "importar: valor en pulgadas", fila(d, "grosor").text(VALOR) == "0,75 in", fila(d, "grosor").text(VALOR))

# ---------- Cálculo automático apagado
d.automatico.click()
foto(d, "5_sin_automatico")
A.reg(AR, "apagado aparece Aplicar", d.b_aplicar.isVisibleTo(d))
antes = volumen()
celda(d, "ancho", EXPRESION, "90 mm")
A.reg(AR, "apagado: la tabla cambia y el modelo no", fila(d, "ancho").text(VALOR) == "90 mm" and volumen() == antes)
d.b_aplicar.click()
A.esperar(100)
A.reg(AR, "Aplicar lleva el cambio al modelo", abs(volumen() - antes * 1.5) < 1e-6, volumen())
d.automatico.click()

# ---------- ventana chica
for ancho, alto in ((1024, 640), (800, 520)):
    v.resize(ancho, alto)
    d.resize(min(ancho, d.width()), min(alto, d.height()))
    d.resize(ancho - 40, alto - 60)
    A.esperar(120)
    foto(d, f"6_{ancho}x{alto}")
    boton = d.b_aceptar.geometry()
    A.reg(AR, f"Aceptar entra en {ancho}x{alto}", d.rect().contains(boton), (boton, d.rect()))
v.resize(1900, 1000)

# ---------- Aceptar, deshacer y reabrir
marca = volumen()
d.b_aceptar.click()
A.esperar(200)
A.reg(AR, "Aceptar cierra", v.dlg_parametros is None)
v.acciones["deshacer"].trigger()
A.esperar(300)
A.reg(AR, "un solo deshacer vuelve a como se abrió", abs(volumen() - inicial) < 1e-6 and "ancho" in s.doc.parametros
      and s.doc.parametros.obtener("ancho").expresion == "60 mm", volumen())
v.acciones["rehacer"].trigger()
A.esperar(300)
A.reg(AR, "rehacer", abs(volumen() - marca) < 1e-6 and "grosor" in s.doc.parametros, volumen())
v.acciones["parametros"].trigger()
A.esperar(200)
d = v.dlg_parametros
A.reg(AR, "al reabrir sigue todo", fila(d, "ancho").text(VALOR) == "90 mm" and fila(d, "espesor").text(NOMBRE) == "espesor")
QTest.keyClick(d, Qt.Key_Escape)
A.esperar(200)
A.reg(AR, "Esc cierra sin perder nada", v.dlg_parametros is None and abs(volumen() - marca) < 1e-6)

# ---------- campos de expresión de un comando
A.MODALES.clear()
p = A.abrir(v, "extruir")
A.elegir(p, "perfiles", A.hit_perfil(v, s, "Rect", 0))
w = teclear(p, "distancia", "pieza=15 mm")
A.esperar(200)
A.reg(AR, "Extruir: «pieza=15 mm» se acepta", "campo_error" not in w.styleSheet() and not w.styleSheet(), w.toolTip())
w = teclear(p, "distancia", "30 mm * 2 mm")
A.esperar(200)
A.reg(AR, "Extruir: una magnitud mala queda en rojo", bool(w.styleSheet()) and "mm^2" in w.toolTip(), w.toolTip())
w.clear()
w.setFocus()
QTest.keyClicks(w, "esp")
A.esperar(100)
A.reg(AR, "la lista sugiere el parámetro", w.lista.completionCount() >= 1 and w.lista.currentCompletion() == "espesor", w.lista.currentCompletion())
w.lista.popup().hide()
w.lista.activated[str].emit("espesor")
A.reg(AR, "elegir de la lista completa el nombre", w.text() == "espesor", w.text())
w.accion_fx.trigger()
A.reg(AR, "ícono fx muestra el valor", QLineEdit.text(w) != "espesor" and w.text() == "espesor", QLineEdit.text(w))
A.foto(v, "parametros_7_extruir")
w.accion_fx.trigger()
teclear(p, "distancia", "pieza=15 mm")
A.esperar(200)
p.aceptar()
A.esperar(400)
fila_pieza = next((x for x in L("get_parameters")["parameters"] if x["name"] == "pieza"), None)
A.reg(AR, "Aceptar crea el parámetro favorito", fila_pieza is not None and fila_pieza.get("favorite") and fila_pieza["expression"] == "15 mm", fila_pieza)
A.reg(AR, "ninguna excepción en un slot", not A.ERRORES, A.ERRORES)
A.reg(AR, "ningún cartel modal", not A.MODALES, A.MODALES)

A.guardar_registro("parametros")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
QApplication.processEvents()
v.close()
sys.exit(0)
