# -*- coding: utf-8 -*-
"""
Panel ASPECTO de Fusion 360 (MODIFICAR › Aspecto): «Aplicar a» cuerpos o caras, «En este diseño» con miniaturas y su
menú (Editar, Duplicar, Suprimir, Copiar en Mis aspectos, Añadir a Favoritos), la biblioteca con buscador, familias y
pestañas (Aspectos de OmniCAD / Mis aspectos / Favoritos), el selector rápido de un aspecto y el Editor de materiales.

Los widgets solo muestran y editan una copia de trabajo de los aspectos: lo que se elige se ve en el modelo al instante
(el comando lo pasa a la vista) y recién «Aceptar» lo escribe en el diseño (`timeline/aspectos_doc.py`, con las mismas
funciones que las herramientas `set_appearance`, `edit_appearance` y `manage_appearance`).
"""
import base64
import copy
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QRadioButton, QSlider, QSpinBox, QTabBar,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..nucleo import aspectos as asp
from . import temas

_ICONOS = {}


def icono_de(aspecto, tam=48):
    """Miniatura (esfera iluminada) de un aspecto como QPixmap, guardada por sus propiedades visibles."""
    a = asp.normalizar(aspecto)
    clave = (tuple(a["color"]), a["aspereza"], a["metalico"], a["transparencia"], a["reflectancia"], a["emisividad"],
             a["luminancia"], tuple(a["color_filtro"]), tam)
    if clave not in _ICONOS:
        if len(_ICONOS) > 600:
            _ICONOS.clear()
        rgba = asp.miniatura_rgba(a, tam)
        img = QImage(rgba.data, tam, tam, tam * 4, QImage.Format_RGBA8888).copy()
        _ICONOS[clave] = QPixmap.fromImage(img)
    return _ICONOS[clave]


def _qcolor(rgb):
    return QColor.fromRgbF(*[float(x) for x in rgb])


def _rgb(c):
    return [c.redF(), c.greenF(), c.blueF()]


# ---------------------------------------------------------------- controles pequeños
class BotonColor(QPushButton):
    """Muestra «RGB r g b» sobre su color; un clic abre el selector de colores del sistema."""
    cambiado = Signal(list)

    def __init__(self, rgb=(1, 1, 1), titulo="Color", parent=None):
        super().__init__(parent)
        self.titulo = titulo
        self.set_color(rgb)
        self.clicked.connect(self._elegir)

    def set_color(self, rgb):
        self.rgb = [float(x) for x in rgb]
        c = _qcolor(self.rgb)
        claro = c.lightnessF() > 0.55
        self.setText("RGB {} {} {}".format(*(round(x * 255) for x in self.rgb)))
        self.setStyleSheet(f"background: {c.name()}; color: {'#101010' if claro else '#f4f4f4'}; text-align: left; "
                           "padding: 3px 8px;")

    def _elegir(self):
        c = QColorDialog.getColor(_qcolor(self.rgb), self, self.titulo, QColorDialog.DontUseNativeDialog)
        if c.isValid():
            self.set_color(_rgb(c))
            self.cambiado.emit(list(self.rgb))


class Deslizante(QWidget):
    """Deslizador de 0 a 1 con su número (como las filas del Editor de materiales)."""
    cambiado = Signal(float)

    def __init__(self, valor=0.0, maximo=1.0, decimales=2, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        self.maximo = maximo
        self.numero = QDoubleSpinBox(decimals=decimales, minimum=0.0, maximum=maximo, singleStep=maximo / 100)
        self.numero.setFixedWidth(72)
        self.barra = QSlider(Qt.Horizontal, minimum=0, maximum=1000)
        fila.addWidget(self.numero)
        fila.addWidget(self.barra, 1)
        self.set_valor(valor)
        self.numero.valueChanged.connect(self._numero)
        self.barra.valueChanged.connect(self._barra)

    def set_valor(self, v):
        for w in (self.numero, self.barra):
            w.blockSignals(True)
        self.numero.setValue(float(v))
        self.barra.setValue(round(float(v) / self.maximo * 1000))
        for w in (self.numero, self.barra):
            w.blockSignals(False)

    def valor(self):
        return self.numero.value()

    def _numero(self, v):
        self.barra.blockSignals(True)
        self.barra.setValue(round(v / self.maximo * 1000))
        self.barra.blockSignals(False)
        self.cambiado.emit(v)

    def _barra(self, n):
        v = n / 1000 * self.maximo
        self.numero.blockSignals(True)
        self.numero.setValue(v)
        self.numero.blockSignals(False)
        self.cambiado.emit(self.numero.value())


class EspectroColor(QWidget):
    """Cuadrado de saturación/brillo y barra de tono (el espectro de color de la ventana de Fusion)."""
    cambiado = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setMinimumWidth(250)
        self.h, self.s, self.v = 0.0, 0.0, 1.0
        self._arrastre = None

    def set_color(self, rgb):
        c = _qcolor(rgb)
        h, s, v, _a = c.getHsvF()
        if s > 0.001 and v > 0.001:              # el gris no tiene tono: se conserva el que había
            self.h = max(h, 0.0)
        self.s, self.v = s, v
        self.update()

    def _zonas(self):
        ancho = self.width()
        return (0, 0, ancho - 24, self.height()), (ancho - 18, 0, 18, self.height())

    def paintEvent(self, _e):
        p = QPainter(self)
        (sx, sy, sw, sh), (hx, hy, hw, hh) = self._zonas()
        base = QColor.fromHsvF(self.h, 1.0, 1.0)
        p.fillRect(sx, sy, sw, sh, base)
        blanco = QLinearGradient(sx, 0, sx + sw, 0)
        blanco.setColorAt(0, QColor("white"))
        blanco.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(sx, sy, sw, sh, blanco)
        negro = QLinearGradient(0, sy, 0, sy + sh)
        negro.setColorAt(0, QColor(0, 0, 0, 0))
        negro.setColorAt(1, QColor("black"))
        p.fillRect(sx, sy, sw, sh, negro)
        tono = QLinearGradient(0, hy, 0, hy + hh)
        for i in range(7):
            tono.setColorAt(i / 6, QColor.fromHsvF(min(i / 6, 0.999), 1, 1))
        p.fillRect(hx, hy, hw, hh, tono)
        p.setPen(QColor("white"))
        p.drawEllipse(QPoint(round(sx + self.s * sw), round(sy + (1 - self.v) * sh)), 4, 4)
        p.drawRect(hx, round(hy + self.h * hh) - 1, hw, 2)

    def mousePressEvent(self, e):
        (sx, sy, sw, sh), (hx, _hy, hw, _hh) = self._zonas()
        self._arrastre = "sv" if e.position().x() < sx + sw + 3 else "h"
        self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        if self._arrastre is None:
            return
        (sx, sy, sw, sh), (hx, hy, hw, hh) = self._zonas()
        x, y = e.position().x(), e.position().y()
        if self._arrastre == "sv":
            self.s = min(1.0, max(0.0, (x - sx) / sw))
            self.v = 1.0 - min(1.0, max(0.0, (y - sy) / sh))
        else:
            self.h = min(0.999, max(0.0, (y - hy) / hh))
        self.update()
        self.cambiado.emit(_rgb(QColor.fromHsvF(self.h, self.s, self.v)))

    def mouseReleaseEvent(self, _e):
        self._arrastre = None


# ---------------------------------------------------------------- selector rápido (imagen 5 de Fusion)
class SelectorRapido(QFrame):
    """Ventanita para cambiar un aspecto a las apuradas: nombre, color (espectro y RGB), aspereza, reflectancia y
    profundidad de translucidez. «Avanzada…» abre el Editor de materiales. Cada cambio sale por `cambiado` al instante."""
    cambiado = Signal(dict)
    avanzada = Signal()
    terminado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("selector_rapido")
        self.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(self)
        self.nombre = QLineEdit()
        v.addWidget(self.nombre)
        self.bibliotecas = QPushButton("Bibliotecas de color")
        self.menu_colores = QMenu(self.bibliotecas)
        self.bibliotecas.setMenu(self.menu_colores)
        v.addWidget(self.bibliotecas)
        self.espectro = EspectroColor()
        v.addWidget(self.espectro)
        fila = QHBoxLayout()
        self.rgb = [QSpinBox(minimum=0, maximum=255) for _ in range(3)]
        for caja in self.rgb:
            fila.addWidget(caja)
        v.addLayout(fila)
        self.aspereza, self.reflectancia = Deslizante(), Deslizante()
        self.profundidad = Deslizante(maximo=5.0)
        form = QFormLayout()
        form.addRow("Aspereza", self.aspereza)
        form.addRow("Reflectancia", self.reflectancia)
        form.addRow("Profundidad de translucidez", self.profundidad)
        v.addLayout(form)
        pie = QHBoxLayout()
        self.b_avanzada = QPushButton("Avanzada…")
        self.b_terminar = QPushButton("Terminar", objectName="boton_primario")
        pie.addWidget(self.b_avanzada)
        pie.addStretch(1)
        pie.addWidget(self.b_terminar)
        v.addLayout(pie)
        self._cargando = False
        self.espectro.cambiado.connect(lambda rgb: self._color(rgb, desde="espectro"))
        for i, caja in enumerate(self.rgb):
            caja.valueChanged.connect(lambda _n: self._color([c.value() / 255 for c in self.rgb], desde="rgb"))
        self.nombre.textEdited.connect(lambda t: self.cambiado.emit({"nombre": t}))
        self.aspereza.cambiado.connect(lambda x: self.cambiado.emit({"aspereza": x}))
        self.reflectancia.cambiado.connect(lambda x: self.cambiado.emit({"reflectancia": x}))
        self.profundidad.cambiado.connect(lambda x: self.cambiado.emit({"profundidad": x, "translucidez": x > 0}))
        self.b_avanzada.clicked.connect(self.avanzada.emit)
        self.b_terminar.clicked.connect(self._terminar)
        for nombre, color in (("Blanco", (1, 1, 1)), ("Negro", (0.05, 0.05, 0.05)), ("Gris", (0.5, 0.5, 0.5)),
                              ("Rojo", (0.8, 0.1, 0.1)), ("Naranja", (0.95, 0.5, 0.1)), ("Amarillo", (0.97, 0.8, 0.1)),
                              ("Verde", (0.15, 0.6, 0.25)), ("Azul", (0.1, 0.3, 0.8)), ("Violeta", (0.5, 0.2, 0.7))):
            self.menu_colores.addAction(nombre, lambda c=color: self._color(list(c), desde="biblioteca"))

    def cargar(self, a):
        self._cargando = True
        self.nombre.setText(a["nombre"])
        self.espectro.set_color(a["color"])
        for caja, x in zip(self.rgb, a["color"], strict=True):
            caja.setValue(round(x * 255))
        self.aspereza.set_valor(a["aspereza"])
        self.reflectancia.set_valor(a["reflectancia"])
        self.profundidad.set_valor(min(a["profundidad"], 5.0) if a["translucidez"] else 0.0)
        self._cargando = False

    def _color(self, rgb, desde):
        if self._cargando:
            return
        self._cargando = True
        if desde != "espectro":
            self.espectro.set_color(rgb)
        if desde != "rgb":
            for caja, x in zip(self.rgb, rgb, strict=True):
                caja.setValue(round(x * 255))
        self._cargando = False
        self.cambiado.emit({"color": [float(x) for x in rgb]})

    def _terminar(self):
        self.terminado.emit()
        self.close()


# ---------------------------------------------------------------- Editor de materiales (imagen 6 de Fusion)
class EditorMateriales(QDialog):
    """«Editor de materiales»: nombre, parámetros, translucidez, emisividad, patrón de relieve, corte y controles
    avanzados de resaltes. Cada cambio sale por `cambiado(propiedades)` al instante (el modelo lo muestra); «Aplicar»
    fija el estado como punto de vuelta, «Cancelar» vuelve al estado del último «Aplicar» (o de la apertura)."""
    cambiado = Signal(dict)
    revertido = Signal(dict)

    def __init__(self, aspecto, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor de materiales")
        self.setModal(False)
        self.a = asp.normalizar(aspecto)
        self._base = copy.deepcopy(self.a)
        v = QVBoxLayout(self)
        self.miniatura = QLabel(alignment=Qt.AlignCenter)
        self.miniatura.setFixedHeight(84)
        v.addWidget(self.miniatura)
        self.nombre = QLineEdit(self.a["nombre"])
        v.addWidget(self.nombre)

        form = QFormLayout()
        self.color = BotonColor(self.a["color"], "Color")
        self.reflectancia, self.aspereza, self.metalico = Deslizante(), Deslizante(), Deslizante()
        form.addRow("Color", self.color)
        form.addRow("Reflectancia", self.reflectancia)
        form.addRow("Aspereza", self.aspereza)
        form.addRow("Metálico", self.metalico)
        grupo = QGroupBox("Parámetros")
        grupo.setLayout(form)
        v.addWidget(grupo)

        self.g_transl = QGroupBox("Translucidez")
        self.g_transl.setCheckable(True)
        f = QFormLayout(self.g_transl)
        self.profundidad = QDoubleSpinBox(decimals=3, minimum=0.0, maximum=1000.0, suffix=" mm")
        self.grosor = BotonColor(self.a["grosor_color"], "Grosor")
        self.transparencia = Deslizante()
        f.addRow("Profundidad", self.profundidad)
        f.addRow("Grosor", self.grosor)
        f.addRow("Transparencia", self.transparencia)
        v.addWidget(self.g_transl)

        self.g_emi = QGroupBox("Emisividad")
        self.g_emi.setCheckable(True)
        f = QFormLayout(self.g_emi)
        self.luminancia = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=1e6, suffix=" cd/m²")
        self.filtro = BotonColor(self.a["color_filtro"], "Color de filtro")
        f.addRow("Luminancia", self.luminancia)
        f.addRow("Color de filtro", self.filtro)
        v.addWidget(self.g_emi)

        self.imagenes = {}
        for clave, titulo in (("relieve", "Patrón de relieve"), ("corte", "Corte")):
            g = QGroupBox(titulo)
            g.setCheckable(True)
            f = QFormLayout(g)
            fila = QHBoxLayout()
            etiqueta = QLabel("(ninguna imagen seleccionada)")
            b_elegir, b_quitar = QPushButton("Imagen…"), QPushButton("Quitar")
            fila.addWidget(b_elegir)
            fila.addWidget(b_quitar)
            f.addRow("Imagen", fila)
            f.addRow("", etiqueta)
            if clave == "relieve":
                cantidad = Deslizante(maximo=10.0)
                f.addRow("Cantidad", cantidad)
                cantidad.cambiado.connect(self._cantidad_relieve)
                self.cantidad = cantidad
            b_elegir.clicked.connect(lambda _c=False, k=clave: self.elegir_imagen(k))
            b_quitar.clicked.connect(lambda _c=False, k=clave: self.poner_imagen(k, None))
            g.toggled.connect(lambda activo, k=clave: None if activo else self.poner_imagen(k, None))
            self.imagenes[clave] = (g, etiqueta)
            v.addWidget(g)

        avanzado = QGroupBox("Controles avanzados de resaltes")
        f = QFormLayout(avanzado)
        self.anisotropia = Deslizante()
        self.orientacion = QDoubleSpinBox(decimals=2, minimum=-360.0, maximum=360.0, suffix="°")
        self.color_resalte = BotonColor((1, 1, 1), "Color del resalte")
        self.forma = QComboBox()
        self.forma.addItems(asp.FORMAS_RESALTE)
        f.addRow("Anisotropía", self.anisotropia)
        f.addRow("Orientación", self.orientacion)
        f.addRow("Color", self.color_resalte)
        f.addRow("Forma", self.forma)
        v.addWidget(avanzado)

        pie = QHBoxLayout()
        pie.addStretch(1)
        self.b_aceptar = QPushButton("Aceptar", objectName="boton_primario")
        self.b_cancelar = QPushButton("Cancelar")
        self.b_aplicar = QPushButton("Aplicar")
        for b in (self.b_aceptar, self.b_cancelar, self.b_aplicar):
            pie.addWidget(b)
        v.addLayout(pie)
        self._cargar(self.a)
        self._conectar()

    # ------------------------------------------------------------ carga y cambios
    def _cargar(self, a):
        self._cargando = True
        self.nombre.setText(a["nombre"])
        self.color.set_color(a["color"])
        self.reflectancia.set_valor(a["reflectancia"])
        self.aspereza.set_valor(a["aspereza"])
        self.metalico.set_valor(a["metalico"])
        self.g_transl.setChecked(a["translucidez"])
        self.profundidad.setValue(a["profundidad"])
        self.grosor.set_color(a["grosor_color"])
        self.transparencia.set_valor(a["transparencia"])
        self.g_emi.setChecked(a["emisividad"])
        self.luminancia.setValue(a["luminancia"])
        self.filtro.set_color(a["color_filtro"])
        for clave in ("relieve", "corte"):
            self._mostrar_imagen(clave, a[clave])
        self.cantidad.set_valor((a["relieve"] or {}).get("cantidad", 1.0))
        r = a["resalte"]
        self.anisotropia.set_valor(r["anisotropia"])
        self.orientacion.setValue(r["orientacion"])
        self.color_resalte.set_color(r["color"])
        self.forma.setCurrentText(r["forma"])
        self.miniatura.setPixmap(icono_de(a, 72))
        self._cargando = False

    def _mostrar_imagen(self, clave, imagen):
        grupo, etiqueta = self.imagenes[clave]
        grupo.blockSignals(True)
        grupo.setChecked(imagen is not None)
        grupo.blockSignals(False)
        etiqueta.setText(imagen["archivo"] if imagen else "(ninguna imagen seleccionada)")

    def _conectar(self):
        self.nombre.textEdited.connect(lambda t: self._poner(nombre=t))
        self.color.cambiado.connect(lambda c: self._poner(color=c))
        self.reflectancia.cambiado.connect(lambda x: self._poner(reflectancia=x))
        self.aspereza.cambiado.connect(lambda x: self._poner(aspereza=x))
        self.metalico.cambiado.connect(lambda x: self._poner(metalico=x))
        self.g_transl.toggled.connect(lambda b: self._poner(translucidez=b))
        self.profundidad.valueChanged.connect(lambda x: self._poner(profundidad=x))
        self.grosor.cambiado.connect(lambda c: self._poner(grosor_color=c))
        self.transparencia.cambiado.connect(lambda x: self._poner(transparencia=x))
        self.g_emi.toggled.connect(lambda b: self._poner(emisividad=b))
        self.luminancia.valueChanged.connect(lambda x: self._poner(luminancia=x))
        self.filtro.cambiado.connect(lambda c: self._poner(color_filtro=c))
        self.anisotropia.cambiado.connect(lambda x: self._resalte(anisotropia=x))
        self.orientacion.valueChanged.connect(lambda x: self._resalte(orientacion=x))
        self.color_resalte.cambiado.connect(lambda c: self._resalte(color=c))
        self.forma.currentTextChanged.connect(lambda t: self._resalte(forma=t))
        self.b_aceptar.clicked.connect(self.aceptar)
        self.b_cancelar.clicked.connect(self.cancelar)
        self.b_aplicar.clicked.connect(self.aplicar)

    def _poner(self, **cambios):
        if getattr(self, "_cargando", False):
            return
        self.a = asp.normalizar(dict(self.a, **cambios))
        self.miniatura.setPixmap(icono_de(self.a, 72))
        self.cambiado.emit(dict(cambios))

    def _resalte(self, **cambios):
        self._poner(resalte=dict(self.a["resalte"], **cambios))

    def _cantidad_relieve(self, x):
        if self.a["relieve"] is not None and not getattr(self, "_cargando", False):
            self._poner(relieve=dict(self.a["relieve"], cantidad=x))

    # ------------------------------------------------------------ imágenes
    def elegir_imagen(self, clave, ruta=None):
        if ruta is None:
            ruta, _ = QFileDialog.getOpenFileName(self, "Imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not ruta:
            return
        p = Path(ruta)
        if not p.is_file() or p.stat().st_size > 6 * 1024 * 1024:       # el tamaño se mira ANTES de leerla entera
            return
        datos = p.read_bytes()
        if QImage.fromData(datos).isNull():                              # no es una imagen que se pueda leer
            return
        self.poner_imagen(clave, {"archivo": p.name, "imagen": base64.b64encode(datos).decode("ascii"),
                                  "cantidad": 1.0})

    def poner_imagen(self, clave, imagen):
        self._mostrar_imagen(clave, imagen)
        self._poner(**{clave: imagen})

    # ------------------------------------------------------------ botones
    def aplicar(self):
        self._base = copy.deepcopy(self.a)

    def aceptar(self):
        self.aplicar()
        self.accept()

    def cancelar(self):
        self.a = copy.deepcopy(self._base)
        self._cargar(self.a)
        self.revertido.emit(copy.deepcopy(self.a))
        self.reject()


# ---------------------------------------------------------------- el panel
class RadiosAplicarA(QWidget):
    """«Aplicar a:  (•) Cuerpos/componentes  ( ) Caras» del panel Aspecto."""
    cambiado = Signal(str)

    def __init__(self, valor="cuerpos", parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel("<b>Aplicar a:</b>"))
        self.r_cuerpos, self.r_caras = QRadioButton("Cuerpos/componentes"), QRadioButton("Caras")
        v.addWidget(self.r_cuerpos)
        v.addWidget(self.r_caras)
        self.set_valor(valor)
        self.r_cuerpos.toggled.connect(lambda b: self.cambiado.emit("cuerpos" if b else "caras"))

    def set_valor(self, valor):
        (self.r_cuerpos if valor != "caras" else self.r_caras).setChecked(True)


class PanelAspectos(QWidget):
    """Lo de adentro del panel Aspecto: «En este diseño» y la biblioteca. Guarda la copia de trabajo de
    los aspectos del diseño (`diseno`), el aspecto elegido (`elegido`) y avisa con `cambiado` cada vez que algo
    cambia (para que el modelo lo muestre al instante)."""
    cambiado = Signal()

    def __init__(self, diseno, parent=None):
        super().__init__(parent)
        self.diseno = copy.deepcopy(diseno)            # copia de trabajo: [{"id", …}] del diseño
        self.elegido = None                            # dict de aspecto (con "id" si es del diseño) o None
        self._proximo = 1
        self.usados = set()                            # ids con quien los usa (no se pueden suprimir)
        self.selector = None
        self.editor = None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel("<b>En este diseño</b>"))
        self.lista = QListWidget()
        self.lista.setViewMode(QListView.IconMode)
        self.lista.setIconSize(QSize(48, 48))
        self.lista.setResizeMode(QListView.Adjust)
        self.lista.setMovement(QListView.Static)
        self.lista.setFixedHeight(84)
        self.lista.setStyleSheet("QListWidget::item { border: 2px solid transparent; border-radius: 6px; } "
                                 f"QListWidget::item:selected {{ background: transparent; "
                                 f"border: 2px solid {temas.color('seleccion')}; }}")
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu_diseno)
        self.lista.itemClicked.connect(lambda it: self.elegir(it.data(Qt.UserRole)))
        v.addWidget(self.lista)
        v.addWidget(QLabel("<b>Biblioteca</b>"))
        self.buscador = QLineEdit(placeholderText="Buscar")
        self.buscador.setClearButtonEnabled(True)
        v.addWidget(self.buscador)
        self.pestanas = QTabBar()
        for t in ("Aspectos de OmniCAD", "Mis aspectos", "Favoritos"):
            self.pestanas.addTab(t)
        v.addWidget(self.pestanas)
        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setIconSize(QSize(28, 28))
        self.arbol.setMinimumHeight(150)
        self.arbol.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbol.customContextMenuRequested.connect(self._menu_biblioteca)
        self.arbol.itemClicked.connect(self._clic_biblioteca)
        v.addWidget(self.arbol)
        self.buscador.textChanged.connect(lambda _t: self.llenar_biblioteca())
        self.pestanas.currentChanged.connect(lambda _i: self.llenar_biblioteca())
        self.llenar_biblioteca()
        self.llenar_diseno()

    # ------------------------------------------------------------ estado
    def _id_nuevo(self):
        usados = {a["id"] for a in self.diseno}
        while f"nuevo{self._proximo}" in usados:
            self._proximo += 1
        return f"nuevo{self._proximo}"

    def _con_nombre_unico(self, nombre, ignorar=None):
        usados = {a["nombre"].casefold() for a in self.diseno if a["id"] != ignorar}
        if nombre.casefold() not in usados:
            return nombre
        n = 1
        while f"{nombre} ({n})".casefold() in usados:
            n += 1
        return f"{nombre} ({n})"

    def entrada(self, aid):
        return next((a for a in self.diseno if a["id"] == aid), None)

    def llenar_diseno(self):
        self.lista.clear()
        for a in self.diseno:
            it = QListWidgetItem(icono_de(a, 48), "")
            it.setToolTip(a["nombre"])
            it.setData(Qt.UserRole, a["id"])
            self.lista.addItem(it)
            if self.elegido is not None and self.elegido.get("id") == a["id"]:
                self.lista.setCurrentItem(it)

    def llenar_biblioteca(self):
        usuario = asp.cargar_usuario()
        pestana = self.pestanas.currentIndex()
        if pestana == 0:
            origen = asp.BIBLIOTECA
        elif pestana == 1:
            origen = usuario["mis"]
        else:
            origen = {n: a for n in usuario["favoritos"] if (a := asp.buscar(n)) is not None}
        q = self.buscador.text().strip().casefold()
        filtrados = {n: a for n, a in origen.items() if not q or q in n.casefold() or q in a["categoria"].casefold()}
        self.arbol.clear()
        for categoria, nombres in asp.categorias_con_aspectos(filtrados).items():
            padre = QTreeWidgetItem(self.arbol, [categoria])
            for n in nombres:
                hoja = QTreeWidgetItem(padre, [n])
                hoja.setIcon(0, icono_de(filtrados[n], 28))
                hoja.setData(0, Qt.UserRole, n)
            padre.setExpanded(bool(q))
        self.arbol.setProperty("favoritos", set(usuario["favoritos"]))

    def _clic_biblioteca(self, item, _col):
        nombre = item.data(0, Qt.UserRole)
        if nombre is None:
            item.setExpanded(not item.isExpanded())
            return
        a = asp.buscar(nombre)
        if a is not None:
            self.elegir(a, desde_biblioteca=True)

    def elegir(self, aspecto_o_id, desde_biblioteca=False):
        """Elige el aspecto que se va a aplicar (el modelo lo muestra al instante). Acepta el id de uno del diseño o
        el dict de uno de la biblioteca."""
        a = self.entrada(aspecto_o_id) if isinstance(aspecto_o_id, str) else aspecto_o_id
        if a is None:
            return
        if desde_biblioteca:
            existente = next((x for x in self.diseno if x["nombre"] == a["nombre"]
                              and {k: v for k, v in x.items() if k not in ("id", "origen")}
                              == {k: v for k, v in a.items() if k not in ("id", "origen")}), None)
            a = existente or dict(a)
        self.elegido = copy.deepcopy(a)
        self.llenar_diseno()
        self.cambiado.emit()

    def sincronizar(self, diseno, usados, mapa=None):
        """Pone la copia de trabajo al día con el diseño (después de escribirlo o de que cambió por otro lado): `usados`
        son los ids con quien los usa y `mapa` los ids definitivos de los aspectos nuevos ({provisorio: definitivo})."""
        self.diseno = copy.deepcopy(diseno)
        self.usados = set(usados)
        if self.elegido is not None and self.elegido.get("id") in (mapa or {}):
            self.elegido["id"] = mapa[self.elegido["id"]]
        self.llenar_diseno()

    # ------------------------------------------------------------ «En este diseño»
    def _menu_diseno(self, pos):
        it = self.lista.itemAt(pos)
        if it is None:
            return
        aid = it.data(Qt.UserRole)
        a = self.entrada(aid)
        m = QMenu(self.lista)
        m.addAction("Editar", lambda: self.editar(aid))
        m.addAction("Duplicar", lambda: self.duplicar(aid))
        suprimir = m.addAction("Suprimir", lambda: self.suprimir(aid))
        suprimir.setEnabled(aid not in self.usados)
        if aid in self.usados:
            suprimir.setToolTip("Lo usan cuerpos o caras del diseño: quitáselo antes.")
        m.addAction("Copiar en Mis aspectos", lambda: self.copiar_en_mis(a))
        favorito = a["nombre"] in asp.cargar_usuario()["favoritos"]
        m.addAction("Quitar de Favoritos" if favorito else "Añadir a Favoritos", lambda: self.favorito(a, not favorito))
        m.exec(self.lista.mapToGlobal(pos))

    def editar(self, aid):
        """Abre el selector rápido sobre un aspecto del diseño: lo que se cambia se ve en el modelo al instante."""
        a = self.entrada(aid)
        if a is None:
            return None
        self.selector = SelectorRapido(self)
        self.selector.cargar(a)
        self.selector.cambiado.connect(lambda cambios, k=aid: self.cambiar(k, cambios))
        self.selector.avanzada.connect(lambda k=aid: self.abrir_editor(k))
        self.selector.move(self.mapToGlobal(QPoint(0, 0)) + QPoint(-self.selector.sizeHint().width() - 10, 40))
        self.selector.show()
        return self.selector

    def abrir_editor(self, aid):
        """Editor de materiales (imagen 6 de Fusion) sobre un aspecto del diseño; sigue abierto mientras se edita."""
        a = self.entrada(aid)
        if a is None:
            return None
        if self.selector is not None:
            self.selector.close()
        self.editor = EditorMateriales(a, self)
        self.editor.cambiado.connect(lambda cambios, k=aid: self.cambiar(k, cambios))
        self.editor.revertido.connect(lambda original, k=aid: self.cambiar(k, original))
        self.editor.show()
        return self.editor

    def cambiar(self, aid, cambios):
        """Cambia propiedades de un aspecto del diseño (copia de trabajo)."""
        a = self.entrada(aid)
        if a is None:
            return
        nuevo = dict(asp.normalizar(asp.mezclar(a, cambios)), id=aid)
        if "origen" in a:
            nuevo["origen"] = a["origen"]
        if "nombre" in cambios:
            nuevo["nombre"] = self._con_nombre_unico(nuevo["nombre"], ignorar=aid) if cambios["nombre"].strip() \
                else a["nombre"]
        self.diseno = [nuevo if x["id"] == aid else x for x in self.diseno]
        if self.elegido is not None and self.elegido.get("id") == aid:
            self.elegido = copy.deepcopy(nuevo)
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.data(Qt.UserRole) == aid:
                it.setIcon(icono_de(nuevo, 48))
                it.setToolTip(nuevo["nombre"])
        self.cambiado.emit()

    def duplicar(self, aid):
        a = self.entrada(aid)
        copia = dict(copy.deepcopy(a), id=self._id_nuevo(), nombre=self._con_nombre_unico(a["nombre"]))
        self.diseno.append(copia)
        self.llenar_diseno()
        self.cambiado.emit()
        return copia

    def suprimir(self, aid):
        if aid in self.usados:
            return False
        self.diseno = [a for a in self.diseno if a["id"] != aid]
        if self.elegido is not None and self.elegido.get("id") == aid:
            self.elegido = None
        self.llenar_diseno()
        self.cambiado.emit()
        return True

    def copiar_en_mis(self, a):
        """«Copiar en Mis aspectos»: guarda una copia con un nombre libre y devuelve el nombre con que quedó."""
        nombre = asp.agregar_mio(dict(a, nombre=asp.nombre_para_mio(a["nombre"])))["nombre"]
        self.llenar_biblioteca()
        return nombre

    def favorito(self, a, valor):
        asp.marcar_favorito(a["nombre"], valor)
        self.llenar_biblioteca()

    # ------------------------------------------------------------ biblioteca
    def _menu_biblioteca(self, pos):
        it = self.arbol.itemAt(pos)
        nombre = it.data(0, Qt.UserRole) if it is not None else None
        if nombre is None:
            return
        a = asp.buscar(nombre)
        mis = nombre in asp.cargar_usuario()["mis"]
        m = QMenu(self.arbol)
        m.addAction("Editar (copia en el diseño)", lambda: self.editar_de_biblioteca(a))
        if not mis:
            m.addAction("Copiar en Mis aspectos", lambda: self.copiar_en_mis(a))
        else:
            m.addAction("Suprimir de Mis aspectos", lambda: (asp.quitar_mio(nombre), self.llenar_biblioteca()))
        favorito = nombre in asp.cargar_usuario()["favoritos"]
        m.addAction("Quitar de Favoritos" if favorito else "Añadir a Favoritos", lambda: self.favorito(a, not favorito))
        m.exec(self.arbol.mapToGlobal(pos))

    def editar_de_biblioteca(self, a):
        """Editar un aspecto de la biblioteca hace una copia en el diseño («X (1)») y edita esa: el original no cambia."""
        copia = dict(copy.deepcopy(a), id=self._id_nuevo(), nombre=self._con_nombre_unico(a["nombre"]),
                     origen="mis" if a["nombre"] in asp.cargar_usuario()["mis"] else "biblioteca")
        self.diseno.append(copia)
        self.elegir(copia["id"])
        return self.editar(copia["id"])
