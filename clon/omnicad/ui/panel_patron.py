# -*- coding: utf-8 -*-
"""Panel PATRÓN RECTANGULAR / PATRÓN CIRCULAR del boceto (Fusion: Rectangular / Circular Pattern), con la misma cara que
SIMETRÍA: Objetos, Dirección o Centro, cantidades, distancias o ángulo, Vista previa, Aceptar y Cancelar.

No guarda estado de la herramienta: `mostrar` lo llena con lo que manda `ui/patron_boceto.py` y cada cambio sale como
una señal con los TEXTOS de los campos (el controlador los evalúa con las unidades y expresiones del documento). Los
campos son `QLineEdit` a propósito: las asas de la vista (`GestorAsas2D`) escriben en ellos, y el panel y el dibujo
quedan siempre sincronizados. Los botones no toman el foco: Enter y Esc siguen siendo del Lienzo salvo dentro de un
campo, donde Enter acepta y Esc cancela."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractButton, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from .comando import _FilaSeleccion
from .formulario import ANCHOS, armar_cabecera, armar_estado, poner_estado
from .iconos import icono

TITULOS = {"rectangular": "PATRÓN RECTANGULAR", "circular": "PATRÓN CIRCULAR"}
MODOS = (("extension", "Extensión", "La distancia es la total: de la primera a la última copia."),
         ("espaciado", "Espaciado", "La distancia es la de cada paso: entre una copia y la siguiente."))
DISTRIBUCIONES = (("completo", "Completa (360°)", "Reparte las copias en la vuelta entera."),
                  ("parcial", "Ángulo", "Reparte las copias en el ángulo total, la primera y la última en los extremos."),
                  ("simetrico", "Simétrica", "Como Ángulo, pero el original queda en el medio."))
ESTILO_MAL = "border: 1px solid #d9534f;"


class _Campo(QLineEdit):
    """Campo de valor: Enter acepta y Esc cancela el panel (el foco está acá, no en el Lienzo)."""
    aceptar = Signal()
    cancelar = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.aceptar.emit()
        elif e.key() == Qt.Key_Escape:
            self.cancelar.emit()
        else:
            super().keyPressEvent(e)


class PanelPatron(QFrame):
    TIPO_INICIAL = "rectangular"     # `PanelTransformar` (Escala y Mover/copiar) hereda de acá con sus propias filas
    ANCHO = ANCHOS["normal"]
    campo = Signal(str)          # lo que va a elegir el próximo clic: seleccion, centro, dir1 o dir2
    limpiar = Signal(str)
    cambio = Signal(object)      # {clave: texto} de todos los campos, a cada tecla
    invertir = Signal(str)       # «distancia1», «distancia2» o «angulo»: cambia el signo del valor
    previa = Signal(bool)
    aceptado = Signal()
    cancelado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_comando")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.tipo = self.TIPO_INICIAL
        self.filas, self.campos, self.combos, self.casillas = {}, {}, {}, {}
        self._rectangular, self._circular = [], []
        self._quieto = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        cab, self.icono, self.titulo = armar_cabecera(self, self.cancelado)
        v.addWidget(cab)
        self.cuerpo = QWidget()
        self.g = QGridLayout(self.cuerpo)
        self.g.setContentsMargins(10, 8, 10, 6)
        self.g.setHorizontalSpacing(8)
        self.g.setVerticalSpacing(4)
        self.g.setColumnMinimumWidth(1, 150)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.cuerpo)
        v.addWidget(self.scroll)
        self._armar()
        armar_estado(self, v, self.ANCHO)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        pie.addStretch(1)
        self.boton_ok = QPushButton("Aceptar", objectName="boton_primario")
        self.boton_ok.clicked.connect(self.aceptado)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.cancelado)
        pie.addWidget(self.boton_ok)
        pie.addWidget(cancelar)
        v.addLayout(pie)
        for w in self.findChildren(QAbstractButton):
            w.setFocusPolicy(Qt.NoFocus)
        self.configurar(self.TIPO_INICIAL)

    # ------------------------------------------------------------ armado
    def _fila(self, clave, texto, widget, ayuda, grupo):
        """Una fila de la grilla: etiqueta y widget; `grupo` dice con qué tipo de patrón se ve."""
        etiqueta = QLabel(texto, objectName="etiqueta_cmd")
        etiqueta.setToolTip(ayuda)
        widget.setToolTip(ayuda)
        fila = self.g.rowCount()
        self.g.addWidget(etiqueta, fila, 0)
        self.g.addWidget(widget, fila, 1)
        self.filas[clave] = (etiqueta, widget)
        if grupo in ("rectangular", "ambos"):
            self._rectangular.append(clave)
        if grupo in ("circular", "ambos"):
            self._circular.append(clave)
        return widget

    def _valor(self, clave, texto, ayuda, grupo, unidad="", invertir=None):
        """Fila con un campo de texto (con su unidad al lado) y, si `invertir`, un botón ⇄ que cambia el signo."""
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(3)
        campo = _Campo()
        campo.setMinimumWidth(70)
        campo.textChanged.connect(self._emitir)
        campo.aceptar.connect(self.aceptado)
        campo.cancelar.connect(self.cancelado)
        h.addWidget(campo, 1)
        if unidad:
            h.addWidget(QLabel(unidad))
        if invertir is not None:
            b = QToolButton(text="⇄")
            b.setToolTip("Invertir el sentido (cambia el signo del valor).")
            b.clicked.connect(lambda: self.invertir.emit(invertir))
            b.setFocusPolicy(Qt.NoFocus)
            h.addWidget(b)
        self.campos[clave] = campo
        self._fila(clave, texto, caja, ayuda, grupo)
        return campo

    def _combo(self, clave, texto, opciones, grupo):
        c = QComboBox()
        for dato, etiqueta, ayuda in opciones:
            c.addItem(etiqueta, dato)
            c.setItemData(c.count() - 1, ayuda, Qt.ToolTipRole)
        c.currentIndexChanged.connect(self._emitir)
        c.setFocusPolicy(Qt.NoFocus)
        self.combos[clave] = c
        self._fila(clave, texto, c, opciones[0][2], grupo)

    def _casilla(self, clave, texto, ayuda, grupo, marcada=False):
        c = QCheckBox(texto)
        c.setChecked(marcada)
        c.toggled.connect(self._emitir)
        c.setFocusPolicy(Qt.NoFocus)
        self.casillas[clave] = c
        self._fila(clave, "", c, ayuda, grupo)

    def _seleccion(self, clave, texto, ayuda, grupo):
        w = _FilaSeleccion(clave)
        w.activar.connect(lambda f: self.campo.emit(f.campo))
        w.limpiar.connect(lambda f: self.limpiar.emit(f.campo))
        self._fila(clave, texto, w, ayuda, grupo)
        return w

    def _armar(self):
        self.sel = {}
        self.sel["seleccion"] = self._seleccion("seleccion", "Objetos", "La geometría a repetir: clic en cada curva o "
                                                "una ventana de selección. Las copias quedan atadas al original.", "ambos")
        # ---- circular
        self.sel["centro"] = self._seleccion("centro", "Centro", "Punto alrededor del cual se reparten las copias: el "
                                             "origen, el centro de un círculo o arco, o cualquier punto del boceto.", "circular")
        self._valor("centro_x", "Centro X", "Coordenada X del centro (mm). Escribirla desata el centro de un punto.",
                    "circular", "mm")
        self._valor("centro_y", "Centro Y", "Coordenada Y del centro (mm).", "circular", "mm")
        self._combo("distribucion", "Distribución", DISTRIBUCIONES, "circular")
        self._valor("angulo_total", "Ángulo total", "Ángulo que recorren las copias. Negativo: sentido horario. La "
                    "cantidad incluye al original.", "circular", "°", invertir="angulo_total")
        self._valor("cantidad", "Cantidad", "Cantidad de ejemplares, contando el original (2 o más).", "circular")
        # ---- rectangular, dirección 1
        self.sel["dir1"] = self._seleccion("dir1", "Dirección 1", "Una línea del boceto que da la dirección (de su "
                                           "inicio a su fin). Sin línea se usa el ángulo de abajo.", "rectangular")
        self._valor("angulo1", "Ángulo 1", "Dirección de la fila 1, en grados desde el eje X del boceto.", "rectangular", "°")
        self._combo("modo", "Distribución", MODOS, "rectangular")
        self._valor("cantidad1", "Cantidad 1", "Ejemplares en la dirección 1, contando el original.", "rectangular")
        self._valor("distancia1", "Extensión total 1", "Total (extensión) o por paso (espaciado). Negativa: sentido contrario.",
                    "rectangular", "mm", invertir="distancia1")
        self._casilla("simetrico1", "Simétrico", "Reparte las copias a los dos lados del original.", "rectangular")
        self._casilla("dos", "Dirección 2", "Agrega una segunda dirección (filas y columnas).", "rectangular")
        # ---- rectangular, dirección 2
        self.sel["dir2"] = self._seleccion("dir2", "Dirección 2", "Una línea del boceto que da la dirección 2. Sin "
                                           "línea se usa el ángulo de abajo (no tiene que ser perpendicular).", "rectangular")
        self._valor("angulo2", "Ángulo 2", "Dirección 2, en grados desde el eje X del boceto.", "rectangular", "°")
        self._valor("cantidad2", "Cantidad 2", "Ejemplares en la dirección 2, contando el original.", "rectangular")
        self._valor("distancia2", "Extensión total 2", "Total (extensión) o por paso (espaciado). Negativa: sentido contrario.",
                    "rectangular", "mm", invertir="distancia2")
        self._casilla("simetrico2", "Simétrico", "Reparte las copias de la dirección 2 a los dos lados del original.",
                      "rectangular")
        self.casilla_previa = QCheckBox()
        self.casilla_previa.setChecked(True)
        self.casilla_previa.setToolTip("Muestra las copias antes de aceptar. Clic en una copia del dibujo para excluirla.")
        self.casilla_previa.toggled.connect(self.previa)
        self.casilla_previa.setFocusPolicy(Qt.NoFocus)
        self._fila("previa", "Vista previa", self.casilla_previa, self.casilla_previa.toolTip(), "ambos")

    # ------------------------------------------------------------ valores
    @property
    def lista_campos(self):
        """Los `QLineEdit` en el orden que usan las asas (`asas_patron`)."""
        return [self.campos[k] for k in ("cantidad1", "distancia1", "cantidad2", "distancia2", "cantidad",
                                         "angulo_total", "angulo1", "angulo2")]

    def textos(self):
        d = {k: c.text() for k, c in self.campos.items()}
        d.update({k: c.currentData() for k, c in self.combos.items()})
        d.update({k: c.isChecked() for k, c in self.casillas.items()})
        return d

    def _emitir(self, *_):
        if not self._quieto:
            self.cambio.emit(self.textos())

    def poner(self, valores):
        """Fija campos, combos y casillas sin emitir (el controlador ya lo sabe). Un campo con el mismo texto no se toca."""
        self._quieto = True
        try:
            for k, t in valores.items():
                if k in self.campos and self.campos[k].text() != t:
                    self.campos[k].setText(t)
                elif k in self.combos:
                    self.combos[k].setCurrentIndex(max(0, self.combos[k].findData(t)))
                elif k in self.casillas:
                    self.casillas[k].setChecked(bool(t))
        finally:
            self._quieto = False

    # ------------------------------------------------------------ estado
    def configurar(self, tipo, editando=False):
        """Muestra las filas del patrón `tipo`; el título cambia al editar uno ya hecho."""
        self.tipo = tipo
        self.titulo.setText(("EDITAR " if editando else "") + TITULOS[tipo])
        self.icono.setPixmap(icono("patron_rectangular" if tipo == "rectangular" else "patron_circular").pixmap(18, 18))
        visibles = set(self._rectangular if tipo == "rectangular" else self._circular)
        for clave, (etiqueta, widget) in self.filas.items():
            etiqueta.setVisible(clave in visibles)
            widget.setVisible(clave in visibles)
        self.ajustar()

    def mostrar(self, e):
        """Pinta el estado del controlador: conteos de cada selección, campo activo, qué se ve y qué falta."""
        self.configurar(e["tipo"], e["editando"])
        for clave, fila in self.sel.items():
            fila.set_estado(e["conteos"].get(clave, 0), e["campo"] == clave)
            if e["etiquetas"].get(clave):
                fila.boton.setText(e["etiquetas"][clave])
        self.poner(e["campos"])
        paso = e["campos"].get("modo") == "espaciado"          # la etiqueta dice qué mide el valor (como en los paneles de comando)
        for n in ("1", "2"):
            self.filas["distancia" + n][0].setText(("Separación " if paso else "Extensión total ") + n)
        dos = bool(e["campos"].get("dos")) or e["tipo"] == "circular"
        for clave in ("dir2", "angulo2", "cantidad2", "distancia2", "simetrico2"):
            visible = e["tipo"] == "rectangular" and dos
            for w in self.filas[clave]:
                w.setVisible(visible)
        for clave in ("angulo1", "angulo2"):
            self.campos[clave].setEnabled(not e["conteos"]["dir" + clave[-1]])
        self.campos["angulo_total"].setEnabled(e["campos"].get("distribucion") != "completo")
        for clave, c in self.campos.items():
            c.setStyleSheet(ESTILO_MAL if clave in e["malos"] else "")
        antes = self.size()
        self.boton_ok.setEnabled(e["valido"])
        self.boton_ok.setText("Aceptar")
        poner_estado(self, e["guia"], e["error"])
        self.casilla_previa.blockSignals(True)
        self.casilla_previa.setChecked(e["previa"])
        self.casilla_previa.blockSignals(False)
        self.ajustar()
        if self.size() != antes and hasattr(self.parentWidget(), "reubicar"):
            self.parentWidget().reubicar()               # un mensaje nuevo agranda el panel: que no lo tape la barra de vista

    def ajustar(self):
        """Tamaño del panel: lo que piden sus filas, y si no entra en la vista el cuerpo se desplaza (ventanas chicas)."""
        self.cuerpo.adjustSize()
        self.setFixedWidth(self.ANCHO)
        self.scroll.setFixedHeight(self.cuerpo.sizeHint().height() + 2)
        self.layout().activate()
        self.adjustSize()
        padre = self.parentWidget()
        exceso = self.height() - (padre.height() - 100) if padre is not None else 0     # 100: barra de vista y márgenes
        if exceso > 0:
            self.scroll.setFixedHeight(max(110, self.scroll.height() - exceso))
            self.layout().activate()
            self.adjustSize()
