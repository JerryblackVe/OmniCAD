# -*- coding: utf-8 -*-
"""
Diálogos de ADMINISTRAR, CONFIGURAR y UTILIDADES:
  - Lista de materiales (BOM) [ASM-FUSION-BOM]: componentes y cuerpos con cantidad, material, masa y
    volumen; los cuerpos iguales se agrupan (cantidad); exportar a CSV.
  - Tabla de configuraciones [CFG-CONFIGURATIONS]: filas = configuraciones, columnas = parámetros y
    supresión de pasos; activar una fila aplica sus valores (un solo paso de deshacer).
  - Secuencias de comandos y complementos [SLD-MANAGE-SCRIPTS-ADD-INS]: scripts Python del usuario que
    reciben `app` (la ventana) y `doc` (el diseño).
  - Biblioteca de roscas [SLD-MANAGE-THREADS-LIBRARY]: consulta de TABLA_ROSCAS.
"""
import contextlib
import csv
import io
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from . import formato

CARPETA_SCRIPTS = Path.home() / "OmniCAD" / "Scripts"
PLANTILLA_SCRIPT = '''# -*- coding: utf-8 -*-
"""Script de OmniCAD. Variables disponibles:
  app  -> la ventana principal (app.doc, app.visor, app.mensaje("texto"))
  doc  -> el diseño abierto (doc.parametros, doc.operaciones, doc.estado_final.cuerpos)
Ejemplo: agrega un cilindro de radio 5 en el origen."""
from omnicad.timeline.operaciones import OpPrimitiva

doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5 mm", alto="20 mm"))
print("Cuerpos:", len(doc.estado_final.cuerpos))
'''


def _tabla(columnas):
    t = QTableWidget(0, len(columnas))
    t.setHorizontalHeaderLabels(columnas)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.verticalHeader().setVisible(False)
    return t


# ---------------------------------------------------------------- lista de materiales
def filas_bom(doc, nombre_de=None):
    """[(n.º, nombre, cantidad, material, masa g, volumen mm³, componente)] agrupando cuerpos iguales."""
    estado = doc.estado_final
    nombre_de = nombre_de or (lambda c: doc.propiedad(c.id, "nombre") or c.nombre)
    grupos = {}
    for c in estado.cuerpos.values():
        if getattr(c, "tipo", "solido") != "solido":
            continue
        material = doc.propiedad(c.id, "material") or getattr(c, "material", None) or "Acero"
        vol = geo.volumen(c.forma)
        comp = estado.componentes.get(c.componente, {}).get("nombre", "") if c.componente else ""
        base = nombre_de(c).split(" (")[0]
        clave = (comp or base, round(vol, 3), round(geo.area(c.forma), 3), material)
        g = grupos.setdefault(clave, {"nombre": comp or base, "cantidad": 0, "material": material, "volumen": vol,
                                      "componente": comp})
        g["cantidad"] += 1
    filas = []
    for i, g in enumerate(sorted(grupos.values(), key=lambda g: g["nombre"]), 1):
        dens = an.TABLA_MATERIALES.get(g["material"], {"densidad": 7.85})["densidad"]
        filas.append((i, g["nombre"], g["cantidad"], g["material"], g["volumen"] * dens / 1000.0, g["volumen"],
                      g["componente"]))
    return filas


class DialogoListaMateriales(QDialog):
    COLUMNAS = ["N.º", "Nombre", "Cantidad", "Material", "Masa (g)", "Volumen (mm³)"]

    def __init__(self, doc, parent=None, nombre_de=None):
        super().__init__(parent)
        self.setWindowTitle("Lista de materiales")
        self.resize(820, 420)
        self.filas = filas_bom(doc, nombre_de)
        t = _tabla(self.COLUMNAS)
        for fila in self.filas:
            r = t.rowCount()
            t.insertRow(r)
            textos = [str(fila[0]), fila[1], str(fila[2]), fila[3], formato.numero(fila[4], miles=True),
                      formato.numero(fila[5], miles=True)]
            for c, texto in enumerate(textos):
                it = QTableWidgetItem(texto)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                t.setItem(r, c, it)
        total = sum(f[4] * f[2] for f in self.filas)
        exportar = QPushButton("Exportar CSV…")
        exportar.clicked.connect(self._exportar)
        botones = QDialogButtonBox(QDialogButtonBox.Close)
        botones.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(t)
        pie = QHBoxLayout()
        pie.addWidget(QLabel(f"{sum(f[2] for f in self.filas)} pieza(s) · masa total {formato.numero(total, miles=True)} g"))
        pie.addStretch()
        pie.addWidget(exportar)
        pie.addWidget(botones)
        lay.addLayout(pie)

    def texto_csv(self):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(self.COLUMNAS)
        for f in self.filas:
            w.writerow([f[0], f[1], f[2], f[3], f"{f[4]:.3f}", f"{f[5]:.3f}"])
        return buf.getvalue()

    def _exportar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar lista de materiales", "lista_materiales.csv", "CSV (*.csv)")
        if ruta:
            Path(ruta).write_text(self.texto_csv(), encoding="utf-8")


# ---------------------------------------------------------------- configuraciones
class DialogoConfiguraciones(QDialog):
    """Tabla de configuraciones: la primera columna es el nombre; después parámetros (expresión) y pasos
    del timeline (columna «Suprimir X»: sí/no)."""

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("Tabla de configuración")
        self.resize(900, 420)
        datos = doc.configuraciones or {"columnas": [], "filas": [], "activa": ""}
        self.columnas = [dict(c) for c in datos["columnas"]] or [{"tipo": "parametro", "nombre": p.nombre}
                                                                for p in doc.parametros]
        self.tabla = _tabla([])
        self._encabezados()
        for fila in datos["filas"] or [{"nombre": "Predeterminada", "valores": self._valores_actuales()}]:
            self._agregar_fila(fila["nombre"], fila["valores"])
        b_fila, b_param, b_supr, b_quitar = (QPushButton("Agregar configuración"), QPushButton("Columna de parámetro…"),
                                             QPushButton("Columna de supresión…"), QPushButton("Quitar fila"))
        b_fila.clicked.connect(lambda: self._agregar_fila(f"Configuración{self.tabla.rowCount() + 1}",
                                                          self._valores_actuales()))
        b_param.clicked.connect(self._columna_parametro)
        b_supr.clicked.connect(self._columna_supresion)
        b_quitar.clicked.connect(lambda: self.tabla.removeRow(self.tabla.currentRow()))
        self.activa = QComboBox()
        self._refrescar_activas(datos.get("activa", ""))
        self.tabla.itemChanged.connect(lambda *_: self._refrescar_activas(self.activa.currentText()))
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Guardar y activar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Cada fila es una configuración del diseño. Al activarla, sus valores se aplican."))
        lay.addWidget(self.tabla)
        fila = QHBoxLayout()
        for b in (b_fila, b_param, b_supr, b_quitar):
            fila.addWidget(b)
        fila.addStretch()
        fila.addWidget(QLabel("Activa:"))
        fila.addWidget(self.activa)
        lay.addLayout(fila)
        lay.addWidget(botones)

    def _titulo(self, c):
        if c["tipo"] == "parametro":
            return c["nombre"]
        try:
            return f"Suprimir {self.doc.operacion(c['op']).nombre}"
        except ValueError:
            return f"Suprimir {c['op']}"

    def _encabezados(self):
        self.tabla.setColumnCount(1 + len(self.columnas))
        self.tabla.setHorizontalHeaderLabels(["Configuración"] + [self._titulo(c) for c in self.columnas])

    def _valores_actuales(self):
        salida = []
        for c in self.columnas:
            if c["tipo"] == "parametro":
                p = next((p for p in self.doc.parametros if p.nombre == c["nombre"]), None)
                salida.append(p.expresion if p else "")
            else:
                try:
                    salida.append("sí" if self.doc.operacion(c["op"]).suprimida else "no")
                except ValueError:
                    salida.append("no")
        return salida

    def _agregar_fila(self, nombre, valores):
        self.tabla.blockSignals(True)
        r = self.tabla.rowCount()
        self.tabla.insertRow(r)
        self.tabla.setItem(r, 0, QTableWidgetItem(nombre))
        for i, val in enumerate(valores):
            self.tabla.setItem(r, i + 1, QTableWidgetItem(str(val)))
        self.tabla.blockSignals(False)
        if hasattr(self, "activa"):
            self._refrescar_activas(self.activa.currentText())

    def _columna_parametro(self):
        nombres = [p.nombre for p in self.doc.parametros if all(c.get("nombre") != p.nombre for c in self.columnas)]
        if not nombres:
            QMessageBox.information(self, "Configuraciones", "No hay más parámetros de usuario para agregar.")
            return
        nombre, ok = QInputDialog.getItem(self, "Columna de parámetro", "Parámetro:", nombres, 0, False)
        if ok:
            self._agregar_columna({"tipo": "parametro", "nombre": nombre})

    def _columna_supresion(self):
        pasos = {o.nombre: o.id for o in self.doc.operaciones if all(c.get("op") != o.id for c in self.columnas)}
        if not pasos:
            return
        nombre, ok = QInputDialog.getItem(self, "Columna de supresión", "Paso del timeline:", list(pasos), 0, False)
        if ok:
            self._agregar_columna({"tipo": "suprimir", "op": pasos[nombre]})

    def _agregar_columna(self, columna):
        self.columnas.append(columna)
        valor = self._valores_actuales()[-1]
        self.tabla.blockSignals(True)
        self._encabezados()
        for r in range(self.tabla.rowCount()):
            self.tabla.setItem(r, len(self.columnas), QTableWidgetItem(valor))
        self.tabla.blockSignals(False)

    def _refrescar_activas(self, actual):
        nombres = [self.tabla.item(r, 0).text() for r in range(self.tabla.rowCount()) if self.tabla.item(r, 0)]
        self.activa.blockSignals(True)
        self.activa.clear()
        self.activa.addItems(nombres)
        if actual in nombres:
            self.activa.setCurrentText(actual)
        self.activa.blockSignals(False)

    def datos(self):
        filas = []
        for r in range(self.tabla.rowCount()):
            filas.append({"nombre": self.tabla.item(r, 0).text().strip(),
                          "valores": [(self.tabla.item(r, i + 1).text().strip() if self.tabla.item(r, i + 1) else "")
                                      for i in range(len(self.columnas))]})
        return {"columnas": self.columnas, "filas": filas, "activa": self.activa.currentText()}


# ---------------------------------------------------------------- secuencias de comandos
def ejecutar_script(codigo, ventana, nombre="script"):
    """Ejecuta un script del usuario con `app` y `doc`. Devuelve (ok, salida de texto)."""
    salida = io.StringIO()
    espacio = {"app": ventana, "doc": ventana.doc, "__name__": "__omnicad_script__"}
    with contextlib.redirect_stdout(salida):
        try:
            exec(compile(codigo, nombre, "exec"), espacio)   # noqa: S102 — el usuario corre SUS scripts
            return True, salida.getvalue()
        except Exception:  # noqa: BLE001 — el error del script se muestra, no tumba la app
            return False, salida.getvalue() + traceback.format_exc()


class DialogoScripts(QDialog):
    def __init__(self, ventana, carpeta=CARPETA_SCRIPTS):
        super().__init__(ventana)
        self.ventana, self.carpeta = ventana, Path(carpeta)
        self.setWindowTitle("Secuencias de comandos y complementos")
        self.resize(720, 460)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.lista = QListWidget()
        self.salida = QPlainTextEdit(readOnly=True)
        botones = {t: QPushButton(t) for t in ("Ejecutar", "Nuevo…", "Editar", "Abrir carpeta", "Actualizar")}
        botones["Ejecutar"].clicked.connect(self.ejecutar)
        botones["Nuevo…"].clicked.connect(self.nuevo)
        botones["Editar"].clicked.connect(self.editar)
        botones["Abrir carpeta"].clicked.connect(lambda: self._abrir(self.carpeta))
        botones["Actualizar"].clicked.connect(self.cargar)
        self.lista.itemDoubleClicked.connect(lambda *_: self.ejecutar())
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Scripts en {self.carpeta} (reciben «app» y «doc»):"))
        h = QHBoxLayout()
        h.addWidget(self.lista, 1)
        col = QVBoxLayout()
        for b in botones.values():
            col.addWidget(b)
        col.addStretch()
        h.addLayout(col)
        lay.addLayout(h, 2)
        lay.addWidget(QLabel("Salida:"))
        lay.addWidget(self.salida, 1)
        self.cargar()

    def cargar(self):
        self.lista.clear()
        for p in sorted(self.carpeta.glob("*.py")):
            self.lista.addItem(p.name)

    def _actual(self):
        it = self.lista.currentItem()
        return self.carpeta / it.text() if it else None

    def ejecutar(self):
        ruta = self._actual()
        if ruta is None:
            return
        ok, texto = ejecutar_script(ruta.read_text(encoding="utf-8"), self.ventana, str(ruta))
        self.salida.setPlainText(("✔ Terminó.\n" if ok else "⚠ Error:\n") + texto)

    def nuevo(self):
        nombre, ok = QInputDialog.getText(self, "Nuevo script", "Nombre:", QLineEdit.Normal, "mi_script")
        if ok and nombre.strip():
            ruta = self.carpeta / f"{nombre.strip().removesuffix('.py')}.py"
            if not ruta.exists():
                ruta.write_text(PLANTILLA_SCRIPT, encoding="utf-8")
            self.cargar()

    def editar(self):
        ruta = self._actual()
        if ruta is not None:
            self._abrir(ruta)

    @staticmethod
    def _abrir(ruta):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))


# ---------------------------------------------------------------- biblioteca de roscas
class DialogoRoscas(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from ..nucleo.solidos_crear import TABLA_ROSCAS, datos_rosca
        self.setWindowTitle("Biblioteca de roscas")
        self.resize(640, 480)
        t = _tabla(["Designación", "Diámetro (mm)", "Paso (mm)", "Ø menor básico (mm)", "Broca para roscar (mm)"])
        for nombre in TABLA_ROSCAS:
            try:
                d = datos_rosca(nombre)
            except Exception:  # noqa: BLE001
                continue
            r = t.rowCount()
            t.insertRow(r)
            for c, val in enumerate((d.get("designacion", nombre), d.get("diametro"), d.get("paso"),
                                     d.get("diametro_menor"), d.get("broca"))):
                t.setItem(r, c, QTableWidgetItem("" if val is None else (f"{val:g}" if isinstance(val, float) else str(val))))
        botones = QDialogButtonBox(QDialogButtonBox.Close)
        botones.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Roscas ISO métricas (gruesa y fina) y unificadas (UNC/UNF) disponibles para Agujero y Rosca."))
        lay.addWidget(t)
        lay.addWidget(botones)
