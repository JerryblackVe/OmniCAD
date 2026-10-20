# -*- coding: utf-8 -*-
"""
Espacio de trabajo ANIMACIÓN (Fusion › Animation): guiones gráficos (storyboards) con su línea de tiempo y las
acciones de Fusion — Transformar componentes (mover/girar), Restaurar posición inicial, Explosión automática de un
nivel o de todos los niveles, Mostrar/Ocultar, Vista (cámara) y Anotación —, reproducir/pausar/ir a, invertir y
copiar guiones, y Publicar video (GIF animado o secuencia PNG).

Punto de entrada para la ventana principal:
    ventana = VentanaAnimacion(doc, parent)   # doc: timeline.documento.Documento
    ventana.desde_dict(datos)                 # opcional: guiones guardados con `a_dict()`
    ventana.show()
    datos = ventana.a_dict()                  # la señal `cambiado` avisa cada edición

Formato de `a_dict()` (JSON): {"version": 1, "actual": índice del guion visible, "guiones": [guion, …]} con
    guion = {"nombre": str, "inicial": {"matrices": {id: [16 floats, por filas]}, "opacidad": {id: 0..1},
             "camara": cámara | None}, "acciones": [acción, …]}
    acción = {"id": "a1", "tipo": …, "inicio": s, "duracion": s, …} según el tipo:
      "transformar": "cuerpos": [ids], "traslacion": [x, y, z] mm, "giro": [rx, ry, rz] vector de rotación en grados
                     (alrededor del centro de los cuerpos)
      "restaurar":   "cuerpos": [ids] (vuelven a la posición del diseño); con "destinos": {id: 16 floats} va a esas
      "explosion":   "cuerpos", "nivel": "uno" | "todos", "distancia": mm, "secuencial": bool,
                     "desplazamientos": {id: [x, y, z]}, "orden": [[ids de cada pieza que se mueve junta], …]
      "visibilidad": "cuerpos", "visible": bool (con duracion > 0 se desvanece)
      "vista":       "camara": {"R": 3x3 (filas: derecha, arriba, atrás), "objetivo": [x, y, z], "distancia", "fov",
                     "ortografica"}
      "anotacion":   "texto", "punto": [x, y, z] (coordenadas del cuerpo, si "cuerpo" no está vacío; si no, del mundo),
                     "cuerpo": id | "" (duracion 0 = visible hasta el final del guion)
Los movimientos usan suavizado (entra y sale despacio), como Fusion.

La lógica pura (Guion, evaluar, explosión, interpolación, exportar cuadros) vive en `nucleo/animacion.py`, sin Qt;
este módulo la importa y agrega la interfaz.
"""
import copy
import json
import os
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFontMetricsF, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
                               QMenu, QMessageBox, QProgressDialog, QRadioButton, QScrollArea, QSlider, QSpinBox,
                               QTabBar, QToolButton, QVBoxLayout, QWidget)

from .. import NOMBRE_APP
from ..nucleo import render_cpu as rc
from ..nucleo.animacion import (DURACION_DEFECTO, TIPOS, Guion, centros_de, calcular_explosion, cuadro_gif,
                                dibujar_notas, estado_final, evaluar, euler_a_giro, grupos_explosion, guardar_gif,
                                invertir, proyectar_notas, tiempos)
from ..nucleo.animacion import interpolar_camara, interpolar_matriz, matriz_movimiento, matriz_rotacion, slerp, suavizado, vector_rotacion  # noqa: F401 — se re-exportan (tests/test_animacion.py)
from ..nucleo.geometria import ErrorGeometria
from . import temas
from .render import SEP, CintaEspacio, LienzoRender, _Oyente, _resaltar_cuerpos, icono_render
from .superposiciones import AreaVisor

# =============================================================== interfaz
COLORES = {"transformar": "#4a9be0", "restaurar": "#8fbde6", "explosion": "#ef9a2a", "visibilidad": "#e8c13a",
           "vista": "#2fa84f", "anotacion": "#a77ad6"}


def etiqueta(a):
    tipo = a["tipo"]
    if tipo == "transformar":
        mueve = any(abs(float(x)) > 1e-9 for x in a.get("traslacion", ()))
        gira = any(abs(float(x)) > 1e-9 for x in a.get("giro", ()))
        return "Mover y girar" if mueve and gira else "Girar" if gira else "Mover"
    if tipo == "visibilidad":
        return "Mostrar" if a.get("visible", True) else "Ocultar"
    if tipo == "anotacion":
        return a.get("texto") or "Anotación"
    if tipo == "explosion":
        return "Explosión (todos)" if a.get("nivel") == "todos" else "Explosión"
    return TIPOS[tipo]


class CapaNotas(QWidget):
    """Anotaciones sobre el lienzo (no toma el ratón)."""

    def __init__(self, lienzo, parent=None):
        super().__init__(parent)
        self.lienzo = lienzo
        self.notas = []
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        lienzo.camara_cambiada.connect(self.update)

    def set_notas(self, notas):
        self.notas = list(notas)
        self.update()

    def paintEvent(self, _e):
        if not self.notas:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fm = QFontMetricsF(self.font())
        for n in self.notas:
            q = self.lienzo.proyectar(n["punto"])
            if q is None:
                continue
            caja = QRectF(q.x() + 40, q.y() - 46, fm.horizontalAdvance(n["texto"] or " ") + 16, fm.height() + 10)
            p.setPen(QPen(QColor("#2b78c2"), 2))
            p.drawLine(q, QPointF(caja.left(), caja.center().y()))
            p.setBrush(QColor("#ffffff"))
            p.drawRect(caja)
            p.setPen(QColor("#282828"))
            p.drawText(caja.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, n["texto"])
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.setBrush(QColor("#d64545"))
            p.drawEllipse(q, 4, 4)


class PistasAnimacion(QWidget):
    """Línea de tiempo: regla, una fila para la Vista, otra para las Anotaciones y una por cuerpo, con las barras de
    las acciones. Clic en la regla = ir a; arrastrar una barra = moverla; arrastrar sus bordes = cambiar la duración;
    doble clic = editar; clic derecho = Editar acción / Eliminar."""
    NOMBRES, FILA, REGLA = 170, 22, 24

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.escala = 90.0                  # píxeles por segundo
        self.seleccion = None               # id de la acción elegida
        self._arrastre = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

    def filas(self):
        cuerpos = [(cid, o["nombre"]) for cid, o in self.v.lienzo.objetos.items()]
        return [("__vista__", "Vista"), ("__notas__", "Anotaciones")] + cuerpos

    def sizeHint(self):
        return QSize(800, self.REGLA + self.FILA * len(self.filas()) + 4)

    def minimumSizeHint(self):
        return QSize(300, self.REGLA + self.FILA * len(self.filas()) + 4)

    def x_de(self, t):
        return self.NOMBRES + 8 + t * self.escala

    def t_de(self, x):
        return max(0.0, (x - self.NOMBRES - 8) / self.escala)

    def barras(self):
        """[(QRectF, acción, fila)] — una por fila afectada (la explosión, con el tramo de cada pieza)."""
        g = self.v.guion
        filas = {k: i for i, (k, _n) in enumerate(self.filas())}
        salida = []
        for a in g.acciones:
            ini, dur = float(a["inicio"]), float(a.get("duracion", 0.0))
            tramos = []
            if a["tipo"] == "vista":
                tramos = [("__vista__", ini, dur)]
            elif a["tipo"] == "anotacion":
                tramos = [("__notas__", ini, dur if dur > 1e-9 else max(0.0, g.duracion - ini))]
            elif a["tipo"] == "explosion":
                orden = a.get("orden") or []
                n = max(1, len(orden))
                for k, pieza in enumerate(orden):
                    i0 = ini + (dur * k / n if a.get("secuencial") else 0.0)
                    d0 = dur / n if a.get("secuencial") else dur
                    tramos += [(c, i0, d0) for c in pieza]
            else:
                tramos = [(c, ini, dur) for c in a.get("cuerpos", [])]
            for fila, i0, d0 in tramos:
                if fila in filas:
                    y = self.REGLA + filas[fila] * self.FILA + 3
                    x0 = self.x_de(i0)
                    salida.append((QRectF(x0, y, max(8.0, d0 * self.escala), self.FILA - 6), a, fila))
        return salida

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        tc = temas.activo()
        p.fillRect(self.rect(), QColor(tc["entrada"]))
        filas = self.filas()
        for i, (clave, nombre) in enumerate(filas):
            y = self.REGLA + i * self.FILA
            p.fillRect(QRectF(0, y, w, self.FILA), QColor(tc["panel"] if i % 2 else tc["entrada"]))
            sel = clave in self.v.seleccion
            p.fillRect(QRectF(0, y, self.NOMBRES, self.FILA), QColor(tc["seleccion"] if sel else tc["panel_cabecera"]))
            p.setPen(QColor((tc["seleccion_texto"] if sel else tc["texto"]) if not clave.startswith("__")
                            else tc["texto_tenue"]))
            f = p.font()
            f.setItalic(clave.startswith("__"))
            p.setFont(f)
            p.drawText(QRectF(8, y, self.NOMBRES - 12, self.FILA), Qt.AlignVCenter | Qt.AlignLeft,
                       p.fontMetrics().elidedText(nombre, Qt.ElideRight, self.NOMBRES - 14))
        f = p.font()
        f.setItalic(False)
        p.setFont(f)
        p.setPen(QColor(tc["borde"]))
        p.drawLine(QPointF(self.NOMBRES, 0), QPointF(self.NOMBRES, h))
        # regla
        p.fillRect(QRectF(self.NOMBRES + 1, 0, w, self.REGLA), QColor(tc["fondo"]))
        paso = next(s for s in (0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60) if s * self.escala >= 40)
        t, fin = 0.0, self.t_de(w)
        while t <= fin + 1e-9:
            x = self.x_de(t)
            p.setPen(QColor(tc["texto_tenue"]))
            p.drawLine(QPointF(x, self.REGLA - 7), QPointF(x, self.REGLA))
            p.setPen(QColor(tc["borde_suave"]))
            p.drawLine(QPointF(x, self.REGLA), QPointF(x, h))
            p.setPen(QColor(tc["texto_tenue"]))
            p.drawText(QRectF(x - 30, 2, 60, 14), Qt.AlignCenter, f"{t:g} s")
            t += paso
        dur = self.v.guion.duracion
        p.fillRect(QRectF(self.x_de(dur), self.REGLA, 2, h), QColor(tc["borde"]))
        # barras
        for r, a, _fila in self.barras():
            color = QColor(COLORES.get(a["tipo"], "#888888"))
            elegida = a.get("id") == self.seleccion
            if float(a.get("duracion", 0.0)) <= 1e-9 and a["tipo"] != "anotacion":
                c = QPointF(r.left(), r.center().y())
                rombo = QPolygonF([QPointF(c.x(), r.top()), QPointF(c.x() + 7, c.y()), QPointF(c.x(), r.bottom()),
                                   QPointF(c.x() - 7, c.y())])
                p.setPen(QPen(QColor("#1d3c5a") if elegida else color.darker(150), 2 if elegida else 1))
                p.setBrush(color)
                p.drawPolygon(rombo)
                continue
            p.setPen(QPen(QColor("#1d3c5a") if elegida else color.darker(140), 2 if elegida else 1))
            p.setBrush(color.lighter(115) if not elegida else color)
            p.drawRoundedRect(r, 3, 3)
            texto = etiqueta(a)
            if r.width() > 30:
                p.setPen(QColor("#ffffff") if a["tipo"] not in ("visibilidad",) else QColor("#3c3c3c"))
                p.drawText(r.adjusted(5, 0, -3, 0), Qt.AlignVCenter | Qt.AlignLeft,
                           p.fontMetrics().elidedText(texto, Qt.ElideRight, int(r.width() - 8)))
        # cursor de tiempo
        x = self.x_de(self.v.t)
        p.setPen(QPen(QColor("#d64545"), 2))
        p.drawLine(QPointF(x, 4), QPointF(x, h))
        p.setBrush(QColor("#d64545"))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(x - 6, 2), QPointF(x + 6, 2), QPointF(x, 11)]))

    def _barra_en(self, pos):
        for r, a, fila in reversed(self.barras()):
            if r.adjusted(-7, 0, 7, 0).contains(pos):
                return r, a, fila
        return None

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.LeftButton and pos.y() < self.REGLA and pos.x() > self.NOMBRES:
            self._arrastre = ("tiempo",)
            self.v.ir_a(self.t_de(pos.x()))
            return
        if pos.x() < self.NOMBRES:
            i = int((pos.y() - self.REGLA) // self.FILA)
            filas = self.filas()
            if 0 <= i < len(filas) and not filas[i][0].startswith("__"):
                self.v.clic_en_cuerpo(filas[i][0])
            return
        hit = self._barra_en(pos)
        self.seleccion = hit[1]["id"] if hit else None
        self.update()
        if hit is None:
            if e.button() == Qt.LeftButton:
                self._arrastre = ("tiempo",)
                self.v.ir_a(self.t_de(pos.x()))
            return
        r, a, _f = hit
        if e.button() == Qt.RightButton:
            m = QMenu(self)
            m.addAction("Editar acción…", lambda: self.v.editar_accion(a["id"]))
            m.addAction("Eliminar", lambda: self.v.eliminar_accion(a["id"]))
            m.exec(e.globalPosition().toPoint())
            return
        borde = "izq" if abs(pos.x() - r.left()) < 5 else "der" if abs(pos.x() - r.right()) < 5 and \
            float(a.get("duracion", 0)) > 0 else "mover"
        self._arrastre = (borde, a["id"], pos.x(), float(a["inicio"]), float(a.get("duracion", 0.0)))

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._arrastre is None:
            hit = self._barra_en(pos)
            cursor = Qt.ArrowCursor
            if hit is not None:
                r = hit[0]
                cursor = Qt.SizeHorCursor if min(abs(pos.x() - r.left()), abs(pos.x() - r.right())) < 5 else \
                    Qt.OpenHandCursor
            self.setCursor(cursor)
            return
        if self._arrastre[0] == "tiempo":
            self.v.ir_a(self.t_de(pos.x()))
            return
        modo, ident, x0, ini, dur = self._arrastre
        dt = (pos.x() - x0) / self.escala
        if modo == "mover":
            self.v.cambiar_tiempos(ident, max(0.0, ini + dt), dur, final=False)
        elif modo == "der":
            self.v.cambiar_tiempos(ident, ini, max(0.05, dur + dt), final=False)
        else:
            nuevo = min(max(0.0, ini + dt), ini + dur - 0.05) if dur > 0 else max(0.0, ini + dt)
            self.v.cambiar_tiempos(ident, nuevo, max(0.0, dur - (nuevo - ini)), final=False)

    def mouseReleaseEvent(self, e):
        if self._arrastre and self._arrastre[0] != "tiempo":
            a = self.v.guion.accion(self._arrastre[1])
            self.v.cambiar_tiempos(a["id"], a["inicio"], a["duracion"], final=True)
        self._arrastre = None

    def mouseDoubleClickEvent(self, e):
        hit = self._barra_en(e.position())
        if hit is not None:
            self.v.editar_accion(hit[1]["id"])

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete and self.seleccion:
            self.v.eliminar_accion(self.seleccion)
        else:
            super().keyPressEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.escala = min(800.0, max(10.0, self.escala * 1.15 ** (e.angleDelta().y() / 120)))
            self.update()
            e.accept()
        else:
            super().wheelEvent(e)


class LineaTiempoAnimacion(QWidget):
    """Panel de abajo: controles de reproducción, las pistas y las pestañas de los guiones gráficos."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.setObjectName("barra_timeline")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        barra = QHBoxLayout()
        barra.setContentsMargins(8, 3, 8, 3)
        titulo = QLabel("LÍNEA DE TIEMPO DE ANIMACIÓN")
        temas.poner_rol(titulo, "encabezado")
        barra.addWidget(titulo)
        barra.addSpacing(12)
        self.botones = {}
        for clave, ico, ayuda, funcion in (("inicio", "tl_inicio", "Ir al inicio", lambda: ventana.ir_a(0.0)),
                                           ("anterior", "tl_anterior", "Acción anterior", ventana.ir_anterior),
                                           ("reproducir", "tl_reproducir", "Reproducir / pausar (Espacio)",
                                            ventana.reproducir_pausar),
                                           ("siguiente", "tl_siguiente", "Acción siguiente", ventana.ir_siguiente),
                                           ("fin", "tl_fin", "Ir al final", lambda: ventana.ir_a(ventana.guion.duracion))):
            b = QToolButton()
            b.setIcon(icono_render(ico))
            b.setIconSize(QSize(18, 18))
            b.setToolTip(ayuda)
            b.clicked.connect(funcion)
            barra.addWidget(b)
            self.botones[clave] = b
        self.tiempo = QDoubleSpinBox()
        self.tiempo.setDecimals(2)
        self.tiempo.setRange(0.0, 3600.0)
        self.tiempo.setSingleStep(0.1)
        self.tiempo.setSuffix(" s")
        self.tiempo.setToolTip("Ir a (segundos)")
        self.tiempo.valueChanged.connect(lambda t: ventana.ir_a(t) if abs(t - ventana.t) > 1e-6 else None)
        barra.addSpacing(8)
        barra.addWidget(self.tiempo)
        self.total = QLabel()
        barra.addWidget(self.total)
        self.bucle = QCheckBox("Repetir")
        barra.addSpacing(10)
        barra.addWidget(self.bucle)
        barra.addStretch(1)
        barra.addWidget(QLabel("Zoom"))
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(15, 400)
        self.zoom.setValue(90)
        self.zoom.setFixedWidth(120)
        barra.addWidget(self.zoom)
        lay.addLayout(barra)
        self.pistas = PistasAnimacion(ventana)
        self._zoom_manual = self._ajustando = False
        self.zoom.valueChanged.connect(self._zoom)
        area = QScrollArea()
        area.setWidget(self.pistas)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setMinimumHeight(150)
        lay.addWidget(area, 1)
        abajo = QHBoxLayout()
        abajo.setContentsMargins(4, 0, 4, 2)
        self.pestanas = QTabBar()
        self.pestanas.setShape(QTabBar.RoundedSouth)
        self.pestanas.setExpanding(False)
        self.pestanas.setDrawBase(False)
        self.pestanas.currentChanged.connect(ventana.elegir_guion)
        self.pestanas.tabBarDoubleClicked.connect(ventana.renombrar_guion)
        self.pestanas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pestanas.customContextMenuRequested.connect(self._menu_pestana)
        abajo.addWidget(self.pestanas)
        nuevo = QToolButton(text="+")
        nuevo.setToolTip("Nuevo guion gráfico")
        nuevo.clicked.connect(ventana.nuevo_guion)
        abajo.addWidget(nuevo)
        abajo.addStretch(1)
        lay.addLayout(abajo)

    def _zoom(self, v):
        if self._ajustando:
            return
        self._zoom_manual = True
        self.pistas.escala = float(v)
        self.pistas.update()

    def ajustar_zoom(self):
        """Escala de la línea de tiempo para que entre el guion entero (hasta que el usuario use el zoom)."""
        if self._zoom_manual:
            return
        ancho = max(200, self.pistas.width() - PistasAnimacion.NOMBRES - 40)
        escala = min(400.0, max(15.0, ancho / max(self.v.guion.duracion * 1.15, 4.0)))
        self.pistas.escala = escala
        self._ajustando = True
        self.zoom.setValue(int(escala))
        self._ajustando = False

    def _menu_pestana(self, pos):
        i = self.pestanas.tabAt(pos)
        if i < 0:
            return
        m = QMenu(self)
        m.addAction("Renombrar", lambda: self.v.renombrar_guion(i))
        m.addAction("Copiar", lambda: self.v.copiar_guion(i))
        m.addAction("Invertir", lambda: self.v.invertir_guion(i))
        m.addSeparator()
        m.addAction("Eliminar", lambda: self.v.eliminar_guion(i))
        m.exec(self.pestanas.mapToGlobal(pos))

    def actualizar(self):
        v = self.v
        self.pestanas.blockSignals(True)
        while self.pestanas.count() > len(v.guiones):
            self.pestanas.removeTab(self.pestanas.count() - 1)
        for i, g in enumerate(v.guiones):
            if i < self.pestanas.count():
                self.pestanas.setTabText(i, g.nombre)
            else:
                self.pestanas.addTab(g.nombre)
        self.pestanas.setCurrentIndex(v.actual)
        self.pestanas.blockSignals(False)
        self.tiempo.blockSignals(True)
        self.tiempo.setValue(v.t)
        self.tiempo.blockSignals(False)
        self.total.setText(f" / {v.guion.duracion:.2f} s")
        self.ajustar_zoom()
        self.botones["reproducir"].setIcon(icono_render("pausa" if v.reproduciendo else "tl_reproducir"))
        self.pistas.updateGeometry()
        self.pistas.adjustSize()
        self.pistas.update()


class DialogoAccion(QDialog):
    """Opciones de una acción (crear o «Editar acción»): las del diálogo de Fusion de cada comando."""

    def __init__(self, parent, tipo, valores, ncuerpos=0, nuevo=True):
        super().__init__(parent)
        self.tipo = tipo
        titulos = {"transformar": "Transformar componentes", "restaurar": "Restaurar posición inicial",
                   "explosion": "Explosión automática", "visibilidad": "Mostrar/Ocultar", "vista": "Vista",
                   "anotacion": "Anotación"}
        self.setWindowTitle(titulos[tipo] if nuevo else f"Editar acción — {titulos[tipo]}")
        f = QFormLayout(self)
        self.campos = {}
        if tipo in ("transformar", "restaurar", "visibilidad"):
            f.addRow("Componentes", QLabel(f"{ncuerpos} cuerpo(s) seleccionado(s)"))
        if tipo == "transformar":
            tras, giro = valores.get("traslacion", (0, 0, 0)), valores.get("giro", (0, 0, 0))
            for i, eje in enumerate("XYZ"):
                self.campos[f"d{eje}"] = self._num(tras[i], -1e5, 1e5, " mm")
                f.addRow(f"Distancia {eje}", self.campos[f"d{eje}"])
            for i, eje in enumerate("XYZ"):
                self.campos[f"a{eje}"] = self._num(giro[i], -3600, 3600, "°")
                f.addRow(f"Ángulo {eje}", self.campos[f"a{eje}"])
        elif tipo == "explosion":
            self.campos["nivel"] = QComboBox()
            self.campos["nivel"].addItem("Un nivel", "uno")
            self.campos["nivel"].addItem("Todos los niveles", "todos")
            self.campos["nivel"].setCurrentIndex(1 if valores.get("nivel") == "todos" else 0)
            f.addRow("Explosión automática", self.campos["nivel"])
            self.campos["distancia"] = self._num(valores.get("distancia", 50.0), 0.0, 1e5, " mm")
            f.addRow("Escala de la explosión", self.campos["distancia"])
            self.campos["secuencial"] = QComboBox()
            self.campos["secuencial"].addItem("En un paso", False)
            self.campos["secuencial"].addItem("Secuencial", True)
            self.campos["secuencial"].setCurrentIndex(1 if valores.get("secuencial") else 0)
            f.addRow("Explosión", self.campos["secuencial"])
            f.addRow("", QLabel(f"{ncuerpos} cuerpo(s)" if ncuerpos else "Todo el modelo"))
        elif tipo == "visibilidad":
            self.campos["visible"] = QComboBox()
            self.campos["visible"].addItem("Ocultar", False)
            self.campos["visible"].addItem("Mostrar", True)
            self.campos["visible"].setCurrentIndex(1 if valores.get("visible") else 0)
            f.addRow("Acción", self.campos["visible"])
            self.instantanea = QRadioButton("Instantánea")
            self.con_duracion = QRadioButton("Con duración (se desvanece)")
            (self.con_duracion if float(valores.get("duracion", 0)) > 0 else self.instantanea).setChecked(True)
            f.addRow("Transición", self.instantanea)
            f.addRow("", self.con_duracion)
        elif tipo == "anotacion":
            self.campos["texto"] = QLineEdit(valores.get("texto", ""))
            self.campos["texto"].setPlaceholderText("Texto de la anotación")
            f.addRow("Texto", self.campos["texto"])
        self.campos["inicio"] = self._num(valores.get("inicio", 0.0), 0.0, 3600.0, " s")
        self.campos["duracion"] = self._num(valores.get("duracion", DURACION_DEFECTO), 0.0, 3600.0, " s")
        f.addRow("Inicio", self.campos["inicio"])
        f.addRow("Duración" if tipo != "anotacion" else "Duración (0 = hasta el final)", self.campos["duracion"])
        if tipo == "visibilidad":
            self.instantanea.toggled.connect(lambda v: self.campos["duracion"].setEnabled(not v))
            self.campos["duracion"].setEnabled(not self.instantanea.isChecked())
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)

    @staticmethod
    def _num(valor, minimo, maximo, sufijo):
        s = QDoubleSpinBox()
        s.setRange(minimo, maximo)
        s.setDecimals(2)
        s.setSuffix(sufijo)
        s.setValue(float(valor))
        return s

    def valores(self):
        c = self.campos
        v = {"inicio": c["inicio"].value(), "duracion": c["duracion"].value()}
        if self.tipo == "transformar":
            v["traslacion"] = [c["dX"].value(), c["dY"].value(), c["dZ"].value()]
            v["giro"] = [float(x) for x in euler_a_giro(c["aX"].value(), c["aY"].value(), c["aZ"].value())]
        elif self.tipo == "explosion":
            v.update(nivel=c["nivel"].currentData(), distancia=c["distancia"].value(),
                     secuencial=bool(c["secuencial"].currentData()))
        elif self.tipo == "visibilidad":
            v["visible"] = bool(c["visible"].currentData())
            if self.instantanea.isChecked():
                v["duracion"] = 0.0
        elif self.tipo == "anotacion":
            v["texto"] = c["texto"].text()
        return v


class DialogoPublicar(QDialog):
    """PUBLICAR › Publicar video [GUID-5C687D49]: alcance, resolución, cuadros por segundo y formato."""
    RESOLUCIONES = [("Tamaño de la ventana actual", 0, 0), ("640 × 360", 640, 360), ("854 × 480", 854, 480),
                    ("1280 × 720", 1280, 720), ("1920 × 1080", 1920, 1080), ("Personalizado", -1, -1)]

    def __init__(self, parent, tam_ventana, ruta):
        super().__init__(parent)
        self.setWindowTitle("Opciones de video")
        self.tam_ventana = tam_ventana
        f = QFormLayout(self)
        self.alcance = QComboBox()
        self.alcance.addItem("Guion gráfico actual", "actual")
        self.alcance.addItem("Documento (todos los guiones)", "documento")
        f.addRow("Alcance del video", self.alcance)
        self.resolucion = QComboBox()
        for texto, w, h in self.RESOLUCIONES:
            self.resolucion.addItem(texto, (w, h))
        self.resolucion.setCurrentIndex(1)
        self.ancho, self.alto = QSpinBox(), QSpinBox()
        for s in (self.ancho, self.alto):
            s.setRange(16, 4096)
            s.setSuffix(" px")
        fila = QHBoxLayout()
        fila.addWidget(self.ancho)
        fila.addWidget(QLabel("×"))
        fila.addWidget(self.alto)
        f.addRow("Resolución", self.resolucion)
        f.addRow("", fila)
        self.fps = QComboBox()
        for n in (10, 12, 15, 24, 30):
            self.fps.addItem(f"{n} cuadros/s", n)
        self.fps.setCurrentIndex(2)
        f.addRow("Velocidad", self.fps)
        self.formato = QComboBox()
        self.formato.addItem("GIF animado (.gif)", "gif")
        self.formato.addItem("Secuencia de imágenes PNG (carpeta)", "png")
        f.addRow("Formato", self.formato)
        self.estilo = QComboBox()
        self.estilo.addItem("Renderizado (aspectos, sombras y entorno)", "render")
        self.estilo.addItem("Como el lienzo (con aristas)", "lienzo")
        f.addRow("Estilo", self.estilo)
        self.motor = QComboBox()
        self.motor.addItem("OpenGL (rápido)", "gl")
        self.motor.addItem("CPU (software)", "cpu")
        f.addRow("Renderizador", self.motor)
        self.ruta = QLineEdit(str(ruta))
        examinar = QToolButton(text="…")
        examinar.clicked.connect(self._examinar)
        fr = QHBoxLayout()
        fr.addWidget(self.ruta, 1)
        fr.addWidget(examinar)
        f.addRow("Guardar en", fr)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.button(QDialogButtonBox.Ok).setText("Publicar")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)
        self.resolucion.currentIndexChanged.connect(self._res)
        self.formato.currentIndexChanged.connect(self._formato)
        self._res()

    def _res(self):
        w, h = self.resolucion.currentData()
        if w == 0:
            w, h = self.tam_ventana
        if w > 0:
            self.ancho.setValue(w)
            self.alto.setValue(h)
        manual = self.resolucion.currentData()[0] < 0
        self.ancho.setEnabled(manual)
        self.alto.setEnabled(manual)

    def _formato(self):
        ruta = Path(self.ruta.text())
        if self.formato.currentData() == "gif":
            self.ruta.setText(str(ruta.with_suffix(".gif")) if ruta.suffix else str(ruta) + ".gif")
        else:
            self.ruta.setText(str(ruta.with_suffix("")))

    def _examinar(self):
        if self.formato.currentData() == "gif":
            ruta, _f = QFileDialog.getSaveFileName(self, "Publicar video", self.ruta.text(), "GIF animado (*.gif)")
        else:
            ruta = QFileDialog.getExistingDirectory(self, "Carpeta para la secuencia PNG", self.ruta.text())
        if ruta:
            self.ruta.setText(ruta)

    def valores(self):
        return {"ruta": self.ruta.text().strip(), "formato": self.formato.currentData(), "ancho": self.ancho.value(),
                "alto": self.alto.value(), "fps": self.fps.currentData(), "alcance": self.alcance.currentData(),
                "motor": self.motor.currentData(), "estilo": self.estilo.currentData()}


GRUPOS_ANIMACION = [
    ("GUION GRÁFICO", ["nuevo_guion"], ["nuevo_guion", "copiar_guion", "invertir_guion", SEP, "eliminar_guion"]),
    ("TRANSFORMAR", ["transformar", "restaurar", "explosion_uno", "explosion_todos", "visibilidad"],
     ["transformar", "restaurar", SEP, "explosion_uno", "explosion_todos", ("Explosión manual",), SEP, "visibilidad",
      ("Aspecto",), ("Mostrar trayectorias",)]),
    ("ANOTACIÓN", ["anotacion"], ["anotacion"]),
    ("VISTA", ["vista", "grabar_vista"], ["vista", "grabar_vista"]),
    ("PUBLICAR", ["publicar"], ["publicar"]),
]


class VentanaAnimacion(QMainWindow):
    """Espacio de trabajo ANIMACIÓN para el documento `doc` (ver el docstring del módulo)."""
    cambiado = Signal()

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        app = QApplication.instance()
        if app is not None and not app.styleSheet():
            temas.aplicar_a_app(app)
        self.doc = doc
        self.setWindowTitle(f"{doc.nombre} — Animación — {NOMBRE_APP}")
        self.resize(1400, 920)
        self.guiones = [Guion("Guion gráfico1")]
        self.actual = 0
        self.t = 0.0
        self.reproduciendo = False
        self.seleccion = []
        self.centros = {}
        self._programado = self._pendiente = False
        self._colocando_nota = False
        self._cam_referencia = None
        self._reloj = None
        self.lienzo = LienzoRender()
        self.lienzo.aristas = True
        self.lienzo.escena = rc.escena_normalizada({"reflejos": False, "oclusion": False})
        self.lienzo.set_escena(self.lienzo.escena)
        self.area = AreaVisor(self.lienzo)
        self.notas = CapaNotas(self.lienzo, self.area)
        self.area.set_capa_boceto(self.notas, None)
        self.acciones = self._crear_acciones()
        self.cinta = CintaEspacio("ANIMACIÓN", "ANIMACIÓN", GRUPOS_ANIMACION, self.acciones, self)
        self.cinta.ir_a_diseno.connect(self.close)
        self.linea = LineaTiempoAnimacion(self)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.cinta)
        lay.addWidget(self.area, 1)
        lay.addWidget(self.linea)
        self.setCentralWidget(central)
        self.temporizador = QTimer(self, interval=33)
        self.temporizador.timeout.connect(self._paso)
        self.lienzo.set_filtro({"cuerpo"})
        self.lienzo.entidad_elegida.connect(lambda hit: self.clic_en_cuerpo(hit.get("cuerpo")))
        self.lienzo.clic_vacio.connect(lambda: self.seleccionar([]))
        self.lienzo.navegacion_terminada.connect(self._navegacion_terminada)
        self.lienzo.installEventFilter(self)
        self.area.viewcube.installEventFilter(self)
        espacio = QAction(self)
        espacio.setShortcut(Qt.Key_Space)
        espacio.triggered.connect(self.reproducir_pausar)
        self.addAction(espacio)
        doc.suscribir(_Oyente(self))
        self.actualizar()
        QTimer.singleShot(0, self, self._encuadrar_inicial)
        self.indicar("Elegí cuerpos (clic o en la línea de tiempo), ubicá el cursor de tiempo y usá TRANSFORMAR.")

    @property
    def guion(self):
        return self.guiones[self.actual]

    # ------------------------------------------------------------ acciones de la cinta
    def _crear_acciones(self):
        definicion = [
            ("nuevo_guion", "Nuevo guion gráfico…", "guion", self.nuevo_guion, False),
            ("copiar_guion", "Copiar guion gráfico", "guion", lambda: self.copiar_guion(self.actual), False),
            ("invertir_guion", "Invertir guion gráfico", "invertir", lambda: self.invertir_guion(self.actual), False),
            ("eliminar_guion", "Eliminar guion gráfico", "suprimir", lambda: self.eliminar_guion(self.actual), False),
            ("transformar", "Transformar componentes", "mover", lambda: self.comando("transformar"), False),
            ("restaurar", "Restaurar posición inicial", "casa", lambda: self.comando("restaurar"), False),
            ("explosion_uno", "Explosión automática: un nivel", "explosion",
             lambda: self.comando("explosion", nivel="uno"), False),
            ("explosion_todos", "Explosión automática: todos los niveles", "explosion_todos",
             lambda: self.comando("explosion", nivel="todos"), False),
            ("visibilidad", "Mostrar/Ocultar", "ojo", lambda: self.comando("visibilidad"), False),
            ("anotacion", "Crear anotación", "anotacion", self.empezar_anotacion, False),
            ("vista", "Vista (guardar la cámara)", "camara", lambda: self.comando("vista"), False),
            ("grabar_vista", "Grabar cámara", "mirar_a", self._grabar_vista, True),
            ("publicar", "Publicar video…", "video", self.dialogo_publicar, False),
        ]
        acciones = {}
        for clave, texto, ico, funcion, marcable in definicion:
            a = QAction(icono_render(ico), texto, self)
            a.setToolTip(texto.rstrip("…"))
            a.setCheckable(marcable)
            a.triggered.connect(lambda _c=False, f=funcion: f())
            acciones[clave] = a
        return acciones

    def indicar(self, texto):
        self.statusBar().showMessage(texto)

    # ------------------------------------------------------------ modelo
    def actualizar(self):
        self._programado = self._pendiente = False
        estado = self.doc.estado_final
        self.lienzo.cargar(estado, self.doc.propiedades)
        self.centros = centros_de(estado)
        self.seleccion = [c for c in self.seleccion if c in self.lienzo.objetos]
        self.setWindowTitle(f"{self.doc.nombre} — Animación — {NOMBRE_APP}")
        self.ir_a(self.t)

    def _modelo_cambio(self):
        if not self.isVisible():
            self._pendiente = True
            return
        if not self._programado:
            self._programado = True
            QTimer.singleShot(0, self.actualizar)

    def showEvent(self, e):
        super().showEvent(e)
        if self._pendiente:
            self.actualizar()

    def _encuadrar_inicial(self):
        self.lienzo.vista("iso")
        self._cam_referencia = self.lienzo.camara_dict()

    def _cambio(self):
        self.linea.actualizar()
        self.cambiado.emit()

    # ------------------------------------------------------------ tiempo
    def cuadro(self, t=None):
        """Estado de la escena (`evaluar`) del guion actual en t (por defecto, el cursor)."""
        return evaluar(self.guion, self.t if t is None else t, self.centros)

    def ir_a(self, t):
        """Lleva el cursor de tiempo a t y muestra la escena en ese instante."""
        self.t = min(max(0.0, float(t)), max(self.guion.duracion, 0.0) + 3600.0)
        fr = self.cuadro()
        self._aplicar_cuadro(fr)
        if not self.reproduciendo:
            self._cam_referencia = self.lienzo.camara_dict()
        self.linea.actualizar()

    def _aplicar_cuadro(self, fr, lienzo=None):
        lz = lienzo or self.lienzo
        lz.set_transformaciones(fr["matrices"])
        lz.opacidad = {c: v for c, v in fr["opacidad"].items() if v < 0.999}
        if fr["camara"]:
            lz.aplicar_camara(fr["camara"])
        if lienzo is None:
            self.notas.set_notas(fr["notas"])
            self._resaltar()
        lz.update()

    def reproducir_pausar(self):
        if self.reproduciendo:
            self.pausar()
        else:
            self.reproducir()

    def reproducir(self):
        if self.guion.duracion <= 0:
            self.indicar("El guion no tiene acciones.")
            return
        if self.t >= self.guion.duracion - 1e-6:
            self.t = 0.0
        self.reproduciendo = True
        self._reloj = (time.perf_counter(), self.t)
        self.temporizador.start()
        self.linea.actualizar()

    def pausar(self):
        self.reproduciendo = False
        self.temporizador.stop()
        self.linea.actualizar()

    def _paso(self):
        t0, base = self._reloj
        t = base + (time.perf_counter() - t0)
        dur = self.guion.duracion
        if t >= dur:
            if self.linea.bucle.isChecked() and dur > 0:
                self._reloj = (time.perf_counter(), 0.0)
                t = 0.0
            else:
                t = dur
                self.reproduciendo = False
                self.temporizador.stop()
        self.ir_a(t)

    def _bordes(self):
        bordes = {0.0, self.guion.duracion}
        for a in self.guion.acciones:
            bordes |= {float(a["inicio"]), float(a["inicio"]) + float(a.get("duracion", 0.0))}
        return sorted(bordes)

    def ir_anterior(self):
        previos = [b for b in self._bordes() if b < self.t - 1e-6]
        self.ir_a(previos[-1] if previos else 0.0)

    def ir_siguiente(self):
        siguientes = [b for b in self._bordes() if b > self.t + 1e-6]
        self.ir_a(siguientes[0] if siguientes else self.guion.duracion)

    # ------------------------------------------------------------ selección
    def clic_en_cuerpo(self, cid):
        if self._colocando_nota:
            return
        if cid is None:
            return
        if QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            sel = [c for c in self.seleccion if c != cid] + ([] if cid in self.seleccion else [cid])
        else:
            sel = [cid]
        self.seleccionar(sel)

    def seleccionar(self, ids):
        self.seleccion = [c for c in ids if c in self.lienzo.objetos]
        self._resaltar()
        self.linea.pistas.update()
        if self.seleccion:
            self.indicar("Seleccionado: " + ", ".join(self.lienzo.objetos[c]["nombre"] for c in self.seleccion))

    def _resaltar(self):
        _resaltar_cuerpos(self.lienzo, self.seleccion)

    # ------------------------------------------------------------ crear y editar acciones
    def agregar_accion(self, accion):
        """Agrega una acción al guion actual (completa la explosión) y muestra el resultado. Devuelve la acción."""
        a = dict(accion)
        if a["tipo"] == "explosion":
            estado = self.doc.estado_final
            grupos = grupos_explosion(estado, a.get("cuerpos") or list(self.lienzo.objetos), a.get("nivel", "uno"))
            a["cuerpos"] = [c for g in grupos for c in g]
            a["desplazamientos"], a["orden"] = calcular_explosion(self.centros, grupos, float(a.get("distancia", 50)))
        if a["tipo"] == "vista" and self.guion.inicial.get("camara") is None:
            self.guion.inicial["camara"] = copy.deepcopy(self._cam_referencia or self.lienzo.camara_dict())
        a = self.guion.agregar(a)
        self.linea.pistas.seleccion = a["id"]
        self.ir_a(self.t)
        self._cambio()
        return a

    def _distancia_defecto(self):
        pts = [o["v0"] for o in self.lienzo.objetos.values()]
        if not pts:
            return 50.0
        p = np.concatenate(pts)
        return round(float(np.linalg.norm(np.ptp(p, axis=0))) * 0.6, 1)

    def comando(self, tipo, **extra):
        """Abre el diálogo de la acción (Transformar, Restaurar, Explosión, Mostrar/Ocultar, Vista)."""
        if tipo in ("transformar", "restaurar", "visibilidad") and not self.seleccion:
            self.indicar("Elegí uno o más cuerpos en el lienzo o en la línea de tiempo.")
            if self.isVisible():
                QMessageBox.information(self, TIPOS[tipo], "Elegí uno o más cuerpos en el lienzo o en la línea de tiempo.")
            return None
        valores = {"inicio": self.t, "duracion": DURACION_DEFECTO, **extra}
        if tipo == "explosion":
            valores.setdefault("distancia", self._distancia_defecto())
        if tipo == "visibilidad":
            fr = self.cuadro()
            valores["visible"] = all(fr["opacidad"].get(c, 1.0) < 0.5 for c in self.seleccion)
            valores["duracion"] = 0.0
        # Explosión sin selección = todo el modelo (agregar_accion); el diálogo lo muestra con 0 cuerpos.
        d = DialogoAccion(self, tipo, valores, len(self.seleccion))
        if d.exec() != QDialog.Accepted:
            return None
        a = {"tipo": tipo, **valores, **d.valores()}
        if tipo in ("transformar", "restaurar", "visibilidad", "explosion"):
            a["cuerpos"] = list(self.seleccion)
        if tipo == "vista":
            a["camara"] = self.lienzo.camara_dict()
        return self.agregar_accion(a)

    def editar_accion(self, ident):
        a = self.guion.accion(ident)
        cuerpos = a.get("cuerpos", [])
        valores = dict(a)
        if a["tipo"] == "transformar":
            valores["giro"] = a.get("giro", (0, 0, 0))
        d = DialogoAccion(self, a["tipo"], valores, len(cuerpos), nuevo=False)
        if d.exec() != QDialog.Accepted:
            return
        nuevos = d.valores()
        a.update(nuevos)
        if a["tipo"] == "explosion":
            grupos = grupos_explosion(self.doc.estado_final, cuerpos or list(self.lienzo.objetos), a.get("nivel", "uno"))
            a["desplazamientos"], a["orden"] = calcular_explosion(self.centros, grupos, float(a["distancia"]))
        self.ir_a(self.t)
        self._cambio()

    def eliminar_accion(self, ident):
        self.guion.quitar(ident)
        if self.linea.pistas.seleccion == ident:
            self.linea.pistas.seleccion = None
        self.ir_a(self.t)
        self._cambio()

    def cambiar_tiempos(self, ident, inicio, duracion, final=True):
        a = self.guion.accion(ident)
        a["inicio"], a["duracion"] = round(max(0.0, float(inicio)), 3), round(max(0.0, float(duracion)), 3)
        self.ir_a(self.t)
        if final:
            self._cambio()

    # ------------------------------------------------------------ anotación y vista
    def empezar_anotacion(self):
        self._colocando_nota = True
        self.lienzo.setCursor(Qt.CrossCursor)
        self.indicar("Hacé clic en un cuerpo (la anotación lo sigue) o en el lienzo para ubicar la anotación. "
                     "Esc cancela.")

    def crear_anotacion(self, texto, punto, cuerpo="", inicio=None, duracion=2.0):
        """Anotación en `punto` (mundo). Si `cuerpo` no está vacío queda pegada a ese cuerpo."""
        punto = np.asarray(punto, float)
        if cuerpo:
            M = self.cuadro()["matrices"].get(cuerpo, np.identity(4))
            punto = np.linalg.inv(M) @ np.r_[punto, 1.0]
            punto = punto[:3]
        return self.agregar_accion({"tipo": "anotacion", "texto": texto, "punto": [float(x) for x in punto],
                                    "cuerpo": cuerpo or "", "inicio": self.t if inicio is None else inicio,
                                    "duracion": duracion})

    def eventFilter(self, obj, e):
        if obj is self.lienzo and self._colocando_nota:
            if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
                self._terminar_nota()
                return True
            if e.type() == QEvent.MouseButtonRelease and e.button() == Qt.LeftButton:
                pos = e.position()
                hit = self.lienzo.elegir_entidad(pos, {"cuerpo"})
                punto = hit["punto"] if hit else self.lienzo.punto_focal(pos)
                self._terminar_nota()
                if punto is not None:
                    texto, ok = QInputDialog.getText(self, "Anotación", "Texto de la anotación:")
                    if ok and texto.strip():
                        self.crear_anotacion(texto.strip(), punto, hit["cuerpo"] if hit else "")
                return True
            if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
                return True
        if obj is self.area.viewcube and e.type() == QEvent.MouseButtonRelease:
            QTimer.singleShot(0, self._navegacion_terminada)
        return super().eventFilter(obj, e)

    def _terminar_nota(self):
        self._colocando_nota = False
        self.lienzo.setCursor(Qt.ArrowCursor)
        self.indicar("")

    def _grabar_vista(self):
        if self.acciones["grabar_vista"].isChecked():
            self.indicar("Grabando la cámara: cada vez que orbites o hagas zoom se agrega una acción Vista en el cursor "
                         "de tiempo.")
        else:
            self.indicar("La cámara ya no se graba.")

    def _navegacion_terminada(self):
        if not self.acciones["grabar_vista"].isChecked() or self.reproduciendo:
            return
        cam = self.lienzo.camara_dict()
        for a in self.guion.acciones:                      # misma posición del cursor: se actualiza esa vista
            if a["tipo"] == "vista" and abs(float(a["inicio"]) - self.t) < 1e-6:
                a["camara"] = cam
                self._cambio()
                return
        self.agregar_accion({"tipo": "vista", "camara": cam, "inicio": self.t, "duracion": DURACION_DEFECTO})

    # ------------------------------------------------------------ guiones
    def nuevo_guion(self, tipo=None):
        """GUION GRÁFICO › Nuevo guion gráfico [GUID-0EAFB4F6]: «limpio» o «continuar» (desde el final del actual)."""
        if tipo is None:
            opciones = ["Limpio", "Comenzar desde el final del anterior"]
            if self.isVisible():
                elegido, ok = QInputDialog.getItem(self, "Nuevo guion gráfico", "Tipo de guion:", opciones, 0, False)
                if not ok:
                    return None
            else:
                elegido = opciones[0]
            tipo = "continuar" if elegido == opciones[1] else "limpio"
        inicial = estado_final(self.guion, self.centros) if tipo == "continuar" else None
        nombres = {g.nombre for g in self.guiones}
        n = len(self.guiones) + 1
        while f"Guion gráfico{n}" in nombres:
            n += 1
        self.guiones.append(Guion(f"Guion gráfico{n}", None, inicial))
        self.elegir_guion(len(self.guiones) - 1)
        self._cambio()
        return self.guion

    def elegir_guion(self, i):
        if 0 <= i < len(self.guiones):
            self.pausar()
            self.actual = i
            self.linea.pistas.seleccion = None
            self.ir_a(0.0)

    def renombrar_guion(self, i):
        if not 0 <= i < len(self.guiones):
            return
        nombre, ok = QInputDialog.getText(self, "Renombrar guion gráfico", "Nombre:", text=self.guiones[i].nombre)
        if ok and nombre.strip():
            self.guiones[i].nombre = nombre.strip()
            self._cambio()

    def copiar_guion(self, i):
        g = Guion.desde_dict(self.guiones[i].a_dict())
        g.nombre = f"{self.guiones[i].nombre} (copia)"
        self.guiones.insert(i + 1, g)
        self.elegir_guion(i + 1)
        self._cambio()

    def invertir_guion(self, i):
        """Clic derecho › Invertir [GUID-CE177759]."""
        self.guiones[i] = invertir(self.guiones[i], self.centros)
        self.elegir_guion(i)
        self._cambio()

    def eliminar_guion(self, i):
        if len(self.guiones) <= 1:
            self.guiones[0] = Guion(self.guiones[0].nombre)
        else:
            del self.guiones[i]
        self.elegir_guion(min(i, len(self.guiones) - 1))
        self._cambio()

    # ------------------------------------------------------------ publicar
    def _ruta_defecto(self):
        base = Path(self.doc.ruta).parent if getattr(self.doc, "ruta", None) else Path.home()
        nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.doc.nombre).strip() or "animacion"
        return base / f"{nombre}_{self.guion.nombre}.gif".replace(" ", "_")

    def dialogo_publicar(self):
        tam = (max(16, self.lienzo.width()), max(16, self.lienzo.height()))
        d = DialogoPublicar(self, tam, self._ruta_defecto())
        if d.exec() == QDialog.Accepted:
            self.publicar(**d.valores())

    def publicar(self, ruta, formato="gif", ancho=640, alto=360, fps=15, alcance="actual", motor="gl", estilo="render",
                 supermuestreo=1):
        """Exporta la animación (GIF animado o secuencia PNG en la carpeta `ruta`). Devuelve la lista de archivos."""
        guiones = self.guiones if alcance == "documento" else [self.guion]
        tramos = [(g, t) for g in guiones for t in tiempos(g.duracion, fps)]
        if not ruta:
            raise ErrorGeometria("Elegí dónde guardar el video.")
        if formato == "png":
            os.makedirs(ruta, exist_ok=True)
        dlg = None
        if self.isVisible():
            dlg = QProgressDialog("Publicando video…", "Cancelar", 0, len(tramos), self)
            dlg.setWindowModality(Qt.WindowModal)
            dlg.setMinimumDuration(200)
        self.pausar()
        t_previo, cam_previa = self.t, self.lienzo.camara_dict()
        escena_previa = self.lienzo.escena
        aristas_previas = self.lienzo.aristas
        if estilo == "render":
            e = dict(escena_previa)
            e.update(reflejos=True, oclusion=True)
            self.lienzo.set_escena(e)
            self.lienzo.aristas = False
        cuadros, archivos = [], []
        try:
            for i, (g, t) in enumerate(tramos):
                if dlg is not None:
                    dlg.setValue(i)
                    QApplication.processEvents()
                    if dlg.wasCanceled():
                        return []
                fr = evaluar(g, t, self.centros)
                if fr["camara"] is None:
                    fr["camara"] = cam_previa
                self._aplicar_cuadro(fr, self.lienzo)
                img = self.lienzo.renderizar_imagen(ancho, alto, supermuestreo, motor)
                if fr["notas"]:
                    img = dibujar_notas(img, proyectar_notas(fr["notas"], self.lienzo.camara_dict(), ancho, alto),
                                        max(1.0, alto / 480))
                if formato == "png":
                    nombre = os.path.join(ruta, f"cuadro_{i + 1:04d}.png")
                    rc.guardar_png(img, nombre)
                    archivos.append(nombre)
                else:
                    cuadros.append(cuadro_gif(img))
            if formato != "png":
                guardar_gif(cuadros, ruta, fps)
                archivos = [ruta]
        finally:
            if dlg is not None:
                dlg.close()
            self.lienzo.set_escena(escena_previa)
            self.lienzo.aristas = aristas_previas
            self.lienzo.aplicar_camara(cam_previa)
            self.ir_a(t_previo)
        self.indicar(f"Video publicado: {archivos[0] if len(archivos) == 1 else ruta} ({len(tramos)} cuadros).")
        return archivos

    # ------------------------------------------------------------ persistencia
    def a_dict(self):
        """Guiones gráficos (JSON) para guardarlos con el documento (formato en el docstring del módulo)."""
        datos = {"version": 1, "actual": self.actual, "guiones": [g.a_dict() for g in self.guiones]}
        json.dumps(datos)                     # garantiza que sea serializable
        return datos

    def desde_dict(self, datos):
        datos = datos or {}
        guiones = [Guion.desde_dict(g) for g in datos.get("guiones") or []]
        self.guiones = guiones or [Guion("Guion gráfico1")]
        self.actual = min(max(0, int(datos.get("actual", 0))), len(self.guiones) - 1)
        self.t = 0.0
        self.linea.pistas.seleccion = None
        self.ir_a(0.0)
        self._cambio()
