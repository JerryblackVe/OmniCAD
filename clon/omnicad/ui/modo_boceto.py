# -*- coding: utf-8 -*-
"""
Modo boceto dentro de la vista 3D (como el entorno de boceto de Fusion 360):
  - la capa de dibujo (Lienzo) sobre el visor, proyectada con su cámara;
  - la PALETA DE BOCETO a la derecha (Opciones: tipo de línea —construcción / línea central—, Mirar a,
    rejilla, forzar, corte, perfil, puntos, cotas, restricciones, geometrías proyectadas, construcción;
    opciones de cada herramienta como las "Feature Options" de Fusion; y Terminar boceto);
  - la pestaña contextual BOCETO de la cinta (la arma la ventana con las acciones de acá);
  - el sombreado azul de los perfiles cerrados, recalculado al cambiar el boceto.
Al terminar se devuelve el boceto editado; la ventana lo guarda como paso del timeline.
"""
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLayout, QMessageBox, QPushButton, QSpinBox, QToolButton,
                               QVBoxLayout, QWidget)

from .. import NOMBRE_APP
from ..nucleo.perfiles import detectar
from . import temas
from .editor_boceto import HERRAMIENTAS, NOMBRES_RESTRICCION, RESTRICCIONES_HERRAMIENTA, Lienzo
from .iconos import icono

# acción → (texto del menú, herramienta, atajo, ícono). Atajos de Fusion: L, R, C, D, T, O, P, M, Mayús+V.
ACCIONES_BOCETO = [
    ("sk_linea", "Línea", "linea", "L", "linea"),
    ("sk_linea_medio", "Línea de punto medio", "linea_medio", None, "linea_punto_medio"),
    ("sk_rectangulo", "Rectángulo de 2 puntos", "rectangulo", "R", "rectangulo"),
    ("sk_rectangulo_3p", "Rectángulo de 3 puntos", "rectangulo_3p", None, "rectangulo_3p"),
    ("sk_rectangulo_centro", "Rectángulo central", "rectangulo_centro", None, "rectangulo_centro"),
    ("sk_circulo", "Círculo de centro y diámetro", "circulo", "C", "circulo"),
    ("sk_circulo_2p", "Círculo de 2 puntos", "circulo_2p", None, "circulo_2p"),
    ("sk_circulo_3p", "Círculo de 3 puntos", "circulo_3p", None, "circulo_3p"),
    ("sk_circulo_2t", "Círculo de 2 tangentes", "circulo_2t", None, "circulo"),
    ("sk_circulo_3t", "Círculo de 3 tangentes", "circulo_3t", None, "circulo"),
    ("sk_arco", "Arco de 3 puntos", "arco", None, "arco"),
    ("sk_arco_centro", "Arco de punto central", "arco_centro", None, "arco_centro"),
    ("sk_arco_tangente", "Arco tangente", "arco_tangente", None, "arco_tangente"),
    ("sk_poligono_circunscrito", "Polígono circunscrito", "poligono_circunscrito", None, "poligono_circunscrito"),
    ("sk_poligono_inscrito", "Polígono inscrito", "poligono_inscrito", None, "poligono_inscrito"),
    ("sk_poligono_arista", "Polígono de aristas", "poligono_arista", None, "poligono_arista"),
    ("sk_elipse", "Elipse", "elipse", None, "elipse"),
    ("sk_ranura_centro", "Ranura de centro a centro", "ranura_centro", None, "ranura"),
    ("sk_ranura_total", "Ranura total", "ranura_total", None, "ranura"),
    ("sk_ranura_punto", "Ranura de punto central", "ranura_punto", None, "ranura"),
    ("sk_ranura_arco_3p", "Ranura de arco de tres puntos", "ranura_arco_3p", None, "ranura"),
    ("sk_ranura_arco_centro", "Ranura de arco de punto central", "ranura_arco_centro", None, "ranura"),
    ("sk_spline_ajuste", "Spline de ajuste de puntos", "spline_ajuste", None, "spline"),
    ("sk_spline_control", "Spline de puntos de control", "spline_control", None, "spline"),
    ("sk_conica", "Curva cónica", "conica", None, "conica"),
    ("sk_punto", "Punto", "punto", None, "punto"),
    ("sk_texto", "Texto", "texto", None, "texto"),
    ("sk_desglosar_texto", "Desglosar texto", "desglosar_texto", None, "texto"),
    ("sk_espiral", "Espiral", "espiral", None, "helice"),
    ("sk_simetria", "Simetría", "simetria", None, "simetria_boceto"),
    ("sk_patron_circular", "Patrón circular", "patron_circular", None, "patron_circular"),
    ("sk_patron_rectangular", "Patrón rectangular", "patron_rectangular", None, "patron_rectangular"),
    ("sk_proyectar", "Proyectar", "proyectar", "P", "proyectar"),
    ("sk_intersecar", "Intersecar", "intersecar", None, "proyectar"),
    ("sk_incluir_3d", "Incluir geometría 3D", "incluir_3d", None, "proyectar"),
    ("sk_cota", "Cota de boceto", "cota", "D", "cota"),
    ("sk_empalme", "Empalme", "empalme", None, "empalme"),
    ("sk_chaflan", "Chaflán de distancias iguales", "chaflan", None, "chaflan_boceto"),
    ("sk_chaflan_dist_angulo", "Chaflán de distancia y ángulo", "chaflan_dist_angulo", None, "chaflan_boceto"),
    ("sk_chaflan_dos_dist", "Chaflán de dos distancias", "chaflan_dos_dist", None, "chaflan_boceto"),
    ("sk_curva_fusion", "Curva de fusión", "curva_fusion", None, "curva_fusion"),
    ("sk_desfase", "Desfase", "desfase", "O", "desfase"),
    ("sk_recortar", "Recortar", "recortar", "T", "recortar"),
    ("sk_alargar", "Alargar", "alargar", "Shift+V", "alargar"),
    ("sk_partir", "Partir", "partir", None, "partir"),
    ("sk_escala", "Escala del boceto", "escala", None, "escala_boceto"),
    ("sk_mover", "Mover/copiar", "mover", "M", "mover"),
] + [(f"sk_{h}", NOMBRES_RESTRICCION[h], h, None, h) for h in RESTRICCIONES_HERRAMIENTA]
TIPOS_POR_FAMILIA = {
    "rectangulo": [("rectangulo", "2 puntos"), ("rectangulo_3p", "3 puntos"), ("rectangulo_centro", "Central")],
    "circulo": [("circulo", "Centro y diámetro"), ("circulo_2p", "2 puntos"), ("circulo_3p", "3 puntos"),
                ("circulo_2t", "2 tangentes"), ("circulo_3t", "3 tangentes")],
    "arco": [("arco", "3 puntos"), ("arco_centro", "Punto central"), ("arco_tangente", "Tangente")],
    "poligono": [("poligono_circunscrito", "Circunscrito"), ("poligono_inscrito", "Inscrito"),
                 ("poligono_arista", "De aristas")],
    "ranura": [("ranura_centro", "Centro a centro"), ("ranura_total", "Total"), ("ranura_punto", "Punto central"),
               ("ranura_arco_3p", "Arco de tres puntos"), ("ranura_arco_centro", "Arco de punto central")],
    "spline": [("spline_ajuste", "Ajuste de puntos"), ("spline_control", "Puntos de control")],
    "chaflan": [("chaflan", "Distancias iguales"), ("chaflan_dist_angulo", "Distancia y ángulo"),
                ("chaflan_dos_dist", "Dos distancias")],
    "proyectar": [("proyectar", "Proyectar"), ("intersecar", "Intersecar"), ("incluir_3d", "Incluir geometría 3D")],
}
# Opciones de función (Feature Options de Fusion): herramienta → [(clave, etiqueta, [(valor, texto), ...])]
OPCIONES_HERRAMIENTA = {
    "spline_control": [("grado_spline", "Grado", [(3, "3"), (5, "5")])],
    "curva_fusion": [("continuidad", "Continuidad", [("G1", "Tangente (G1)"), ("G2", "Curvatura (G2)")])],
    "patron_rectangular": [("patron_distancia", "Distancia", [("extension", "Extensión"), ("espaciado", "Espaciado")])],
    "proyectar": [("filtro_proyectar", "Filtro", [("entidades", "Entidades especificadas"), ("cuerpos", "Cuerpos")])],
    "intersecar": [("filtro_proyectar", "Filtro", [("entidades", "Entidades especificadas"), ("cuerpos", "Cuerpos")])],
}
# Opciones del texto: viven en el panel «Carácter» (PanelCaracter), no en la paleta de boceto
ALINEACIONES_TEXTO = [("izq", "Izquierda"), ("centro", "Centro"), ("der", "Derecha")]
ANCLAJES_TEXTO = [("base", "Línea base"), ("arriba", "Arriba"), ("medio", "Medio"), ("abajo", "Abajo")]
LADOS_TEXTO = [("izq", "Izquierda de la curva"), ("der", "Derecha (al revés)")]
_FUENTES = []


def _fuentes():
    """Fuentes que entiende el Texto de boceto (se consultan una sola vez)."""
    if not _FUENTES:
        try:
            from ..nucleo.perfiles import fuentes_disponibles
            _FUENTES.extend(fuentes_disponibles())
        except Exception:  # noqa: BLE001 — sin lista de fuentes, igual se puede escribir con Arial
            pass
        if not _FUENTES:
            _FUENTES.append("Arial")
    return _FUENTES


def _familia(h):
    for fam, tipos in TIPOS_POR_FAMILIA.items():
        if any(h == t for t, _ in tipos):
            return fam
    return None


class PaletaBoceto(QFrame):
    """Panel flotante a la derecha del lienzo, con las opciones de la Paleta de boceto de Fusion."""
    terminar = Signal()
    mirar_a = Signal()
    opcion = Signal(str, bool)
    herramienta = Signal(str)
    lados = Signal(int)
    opcion_cota = Signal(str)
    construccion = Signal()
    eje = Signal()
    ajuste = Signal(str, object)       # opción de la herramienta activa (clave, valor)

    OPCIONES = [("rejilla", "Rejilla del boceto", True, True), ("forzar", "Forzar", False, True),
                ("corte", "Corte", False, True), ("perfil", "Perfil", True, True), ("puntos", "Puntos", True, True),
                ("cotas", "Cotas", True, True), ("restricciones", "Restricciones", True, True),
                ("proyectadas", "Geometrías proyectadas", True, True),
                ("construccion", "Geometrías de construcción", True, True), ("boceto3d", "Boceto 3D", False, False)]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("paleta_boceto")
        v = QVBoxLayout(self)
        v.setSizeConstraint(QLayout.SetFixedSize)      # el panel mide siempre lo que su contenido
        v.setContentsMargins(8, 4, 8, 8)
        v.setSpacing(4)
        cab = QHBoxLayout()
        self.b_plegar = QToolButton(text="–")
        self.b_plegar.clicked.connect(self._plegar)
        cab.addWidget(self.b_plegar)
        titulo = QLabel("PALETA DE BOCETO")
        titulo.setStyleSheet("font-size: 8pt; letter-spacing: 0.3px;")
        cab.addWidget(titulo)
        cab.addStretch(1)
        v.addLayout(cab)
        self.cuerpo = QWidget()
        self.cuerpo.setFixedWidth(234)
        c = QVBoxLayout(self.cuerpo)
        c.setContentsMargins(0, 0, 0, 0)
        seccion = QLabel("▾ <b>Opciones</b>")
        c.addWidget(seccion)
        self.contexto = QWidget()
        self.form_contexto = QFormLayout(self.contexto)
        self.form_contexto.setContentsMargins(0, 2, 0, 2)
        c.addWidget(self.contexto)
        grilla = QGridLayout()
        grilla.setColumnStretch(0, 1)
        grilla.addWidget(QLabel("Tipo de línea"), 0, 0)
        self.b_construccion = QToolButton()
        self.b_construccion.setIcon(icono("rectangulo_centro"))
        self.b_construccion.setCheckable(True)
        self.b_construccion.setToolTip("<b>Construcción (X)</b><br>Alterna la geometría seleccionada (o la nueva) "
                                       "entre normal y construcción.")
        self.b_construccion.clicked.connect(self.construccion)
        self.b_eje = QToolButton()
        self.b_eje.setIcon(icono("simetria_boceto"))
        self.b_eje.setCheckable(True)
        self.b_eje.setToolTip("<b>Línea central</b><br>Alterna la geometría seleccionada (o la nueva) entre normal "
                              "y línea central (eje): forma perfiles y es el eje que propone Revolución.")
        self.b_eje.clicked.connect(self.eje)
        tipos = QHBoxLayout()
        tipos.setSpacing(2)
        tipos.addWidget(self.b_construccion)
        tipos.addWidget(self.b_eje)
        grilla.addLayout(tipos, 0, 1, Qt.AlignRight)
        grilla.addWidget(QLabel("Mirar a"), 1, 0)
        b = QToolButton()
        b.setIcon(icono("mirar_a"))
        b.setToolTip("<b>Mirar a</b><br>Gira la cámara para mirar de frente el plano del boceto.")
        b.clicked.connect(self.mirar_a)
        grilla.addWidget(b, 1, 1, Qt.AlignRight)
        self.checks = {}
        for fila, (clave, texto, inicial, activa) in enumerate(self.OPCIONES, start=2):
            grilla.addWidget(QLabel(texto), fila, 0)
            ch = QCheckBox()
            ch.setChecked(inicial)
            ch.setEnabled(activa)
            if not activa:
                ch.setToolTip("No disponible en OmniCAD (no hay bocetos 3D).")
            ch.toggled.connect(lambda valor, k=clave: self.opcion.emit(k, valor))
            grilla.addWidget(ch, fila, 1, Qt.AlignRight)
            self.checks[clave] = ch
        c.addLayout(grilla)
        self.estado = QLabel()
        self.estado.setWordWrap(True)
        c.addWidget(self.estado)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.b_terminar = QPushButton("Terminar boceto")
        self.b_terminar.clicked.connect(self.terminar)
        fila.addWidget(self.b_terminar)
        c.addLayout(fila)
        v.addWidget(self.cuerpo)
        self.ajustar()

    def ajustar(self):
        """Tamaño justo para el contenido (las opciones contextuales cambian con la herramienta)."""
        self.layout().activate()
        self.adjustSize()

    def _plegar(self):
        self.cuerpo.setVisible(not self.cuerpo.isVisible())
        self.b_plegar.setText("–" if self.cuerpo.isVisible() else "+")
        self.ajustar()

    def set_herramienta(self, h, lados=6, opcion_cota="auto", opciones=None):
        """Opciones contextuales según la herramienta activa (como las de Fusion)."""
        opciones = opciones or {}
        while self.form_contexto.rowCount():
            self.form_contexto.removeRow(0)
        fam = _familia(h)
        if fam:
            combo = QComboBox()
            for clave, texto in TIPOS_POR_FAMILIA[fam]:
                combo.addItem(texto, clave)
            combo.setCurrentIndex(combo.findData(h))
            combo.currentIndexChanged.connect(lambda _i, cb=combo: self.herramienta.emit(cb.currentData()))
            self.form_contexto.addRow("Tipo", combo)
        if fam == "poligono":
            sp = QSpinBox()
            sp.setRange(3, 64)
            sp.setValue(lados)
            sp.valueChanged.connect(self.lados)
            self.form_contexto.addRow("Lados", sp)
        if h == "cota":
            combo = QComboBox()
            combo.addItem("Automática (horizontal / vertical)", "auto")
            combo.addItem("Alineada", "alineada")
            combo.setCurrentIndex(combo.findData(opcion_cota))
            combo.currentIndexChanged.connect(lambda _i, cb=combo: self.opcion_cota.emit(cb.currentData()))
            self.form_contexto.addRow("Cota", combo)
        for clave, etiqueta, valores in OPCIONES_HERRAMIENTA.get(h, []):
            combo = QComboBox()
            for valor, texto in valores:
                combo.addItem(texto, valor)
            combo.setCurrentIndex(max(0, combo.findData(opciones.get(clave))))
            combo.currentIndexChanged.connect(lambda _i, cb=combo, k=clave: self.ajuste.emit(k, cb.currentData()))
            self.form_contexto.addRow(etiqueta, combo)
        if h == "mover":
            ch = QCheckBox()
            ch.setChecked(bool(opciones.get("copiar")))
            ch.toggled.connect(lambda valor: self.ajuste.emit("copiar", valor))
            self.form_contexto.addRow("Copiar", ch)
        self.contexto.setVisible(self.form_contexto.rowCount() > 0)
        self.ajustar()

    def set_estado(self, resultado):
        if resultado is None:
            self.estado.setText("")
        elif not resultado.ok:
            self.estado.setText(f"⚠ {resultado.descripcion()}")
            temas.poner_rol(self.estado, "error")
        elif resultado.gdl == 0:
            self.estado.setText("Totalmente restringido.")
            temas.poner_rol(self.estado, "ok")
        else:
            self.estado.setText(f"Faltan {resultado.gdl} grado(s) de libertad por restringir.")
            temas.poner_rol(self.estado, "tenue")
        self.ajustar()


FILTROS_FUENTE = [("todo", "Todo"), ("variables", "Variables"), ("negrita", "Con negrita"),
                  ("cursiva", "Con cursiva")]
ESTILOS_TEXTO = [("regular", "Regular"), ("negrita", "Negrita"), ("cursiva", "Cursiva"),
                 ("negrita_cursiva", "Negrita cursiva")]
_ESTILO_BC = {"regular": (False, False), "negrita": (True, False), "cursiva": (False, True),
              "negrita_cursiva": (True, True)}
DECORACIONES_TEXTO = [("ninguno", "Ninguno"), ("simple", "Simple"), ("doble", "Doble")]
CAPITALIZACIONES_TEXTO = [("ninguno", "Ninguno"), ("mayusculas", "MAYÚSCULAS"), ("minusculas", "minúsculas"),
                          ("titulo", "Título"), ("versalitas", "Versalitas")]


def familias_filtradas(filtro):
    """Nombres de familia que muestra la lista de fuentes según el filtro (todo, variables, negrita, cursiva)."""
    nombres = _fuentes()
    if filtro == "todo":
        return nombres
    try:
        from ..nucleo import fuentes as catalogo
        registros = catalogo.catalogo()
    except Exception:  # noqa: BLE001 — sin catálogo no se puede filtrar: queda la lista completa
        return nombres
    buenas = {r["familia"] for r in registros
              if (filtro == "variables" and "wght" in r["ejes"]) or (filtro == "negrita" and r["peso"] >= 600)
              or (filtro == "cursiva" and r["cursiva"])}
    return [n for n in nombres if n in buenas]


class _AgarreTamano(QWidget):
    """Esquina inferior izquierda de un panel flotante: arrastrarla lo agranda (a la izquierda y hacia abajo, porque
    el panel está pegado a la paleta por la derecha)."""

    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.setFixedSize(16, 16)
        self.setCursor(Qt.SizeBDiagCursor)
        self.setToolTip("Arrastrá para agrandar o achicar el panel")
        self._inicio = None

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setPen(QPen(QColor(150, 150, 160), 1))
        for k in (5, 9, 13):
            p.drawLine(0, 16 - k, k, 16)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._inicio = (e.globalPosition().toPoint(), self.panel.width(), self.panel.height())

    def mouseMoveEvent(self, e):
        if self._inicio is not None:
            g0, w0, h0 = self._inicio
            d = e.globalPosition().toPoint() - g0
            self.panel.set_tamano_usuario(w0 - d.x(), h0 + d.y())

    def mouseReleaseEvent(self, _e):
        self._inicio = None


class PanelCaracter(QFrame):
    """Panel «Carácter» del texto del boceto, ordenado de lo más usado a lo avanzado: Fuente (familia con filtro y
    búsqueda, estilo, tamaño y kerning de la fuente), Espaciado (interletraje, kerning de un par e interlineado),
    Alineación y curva, y plegadas Decoraciones, Transformaciones y Avanzado. No guarda estado: `cargar` lo llena con
    las opciones del Lienzo y cada cambio sale por `cambio(clave, valor)`. Con un texto abierto, el Lienzo le avisa
    sus valores (`mostrar_valores`): tamaño, interletraje e interlineado son los mismos de la barra del texto."""
    cambio = Signal(str, object)
    ANCHO = 300                  # ancho mínimo; se puede agrandar arrastrando la esquina inferior izquierda

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("paleta_boceto")
        self._tam_usuario = [0, 0]
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 4, 8, 8)
        v.setSpacing(4)
        cab = QHBoxLayout()
        self.b_plegar = QToolButton(text="–")
        self.b_plegar.clicked.connect(self._plegar)
        cab.addWidget(self.b_plegar)
        titulo = QLabel("CARÁCTER")
        titulo.setStyleSheet("font-size: 8pt; letter-spacing: 0.3px;")
        cab.addWidget(titulo)
        cab.addStretch(1)
        v.addLayout(cab)
        self.cuerpo = QWidget()
        self.cuerpo.setMinimumWidth(self.ANCHO)
        c = QVBoxLayout(self.cuerpo)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(6)
        # ---- Fuente: familia (filtro + búsqueda), estilo, tamaño y kerning de la fuente
        fila = QHBoxLayout()
        self.filtro = QComboBox()
        for clave, texto in FILTROS_FUENTE:
            self.filtro.addItem(texto, clave)
        self.filtro.setFixedWidth(88)
        self.filtro.setToolTip("<b>Filtro de fuentes</b><br>Limita las fuentes de la lista: todas, variables "
                               "(peso ajustable), con negrita real o con cursiva real.")
        self.filtro.currentIndexChanged.connect(lambda _i: self._poblar_fuentes(self.fuente.currentText()))
        self.fuente = QComboBox()
        self.fuente.setEditable(True)
        self.fuente.setInsertPolicy(QComboBox.NoInsert)
        self.fuente.setToolTip("<b>Familia tipográfica</b><br>Elegí la fuente de la lista o escribí parte del "
                               "nombre para buscarla. Cada nombre se ve con su propia tipografía.")
        self.fuente.currentIndexChanged.connect(self._fuente_elegida)
        fila.addWidget(self.filtro)
        fila.addWidget(self.fuente, 1)
        c.addLayout(fila)
        fila = QHBoxLayout()
        self.estilo = QComboBox()
        for clave, texto in ESTILOS_TEXTO:
            self.estilo.addItem(texto, clave)
        self.estilo.setToolTip("<b>Variante</b><br>Regular, negrita, cursiva o negrita cursiva (el peso y la "
                               "cursiva más cercanos que tenga la familia).")
        self.estilo.currentIndexChanged.connect(self._estilo_elegido)
        self.altura = self._spin("altura_texto", 0.1, 10000.0, 0.5, " mm", "<b>Tamaño</b><br>Altura de la letra "
                                 "en mm (la misma que «Altura» de la barra del texto).")
        self.altura.setFixedWidth(96)
        self.b_kerning = QToolButton(text="V/A")
        self.b_kerning.setCheckable(True)
        self.b_kerning.setToolTip("<b>Kerning de la fuente</b><br>Usa los pares de letras que trae la fuente "
                                  "(AV, To…). Apagado, todas las letras van con su avance normal.")
        self.b_kerning.toggled.connect(lambda x: self.cambio.emit("kerning", bool(x)))
        fila.addWidget(self.estilo, 1)
        fila.addWidget(self.altura)
        fila.addWidget(self.b_kerning)
        self.b_voltear_h = self._boton_voltear("↔", "voltear_h", "<b>Voltear horizontal</b><br>Espeja el texto "
                                               "de izquierda a derecha dentro de su bloque.")
        self.b_voltear_v = self._boton_voltear("↕", "voltear_v", "<b>Voltear vertical</b><br>Espeja el texto "
                                               "de arriba abajo dentro de su bloque.")
        fila.addWidget(self.b_voltear_h)
        fila.addWidget(self.b_voltear_v)
        c.addLayout(fila)
        # ---- Espaciado
        self._seccion(c, "Espaciado", True)
        self.interletraje = self._spin("espaciado", -1000.0, 1000.0, 0.1, " mm", "<b>Interletraje (tracking)</b><br>"
                                       "Suma o resta distancia entre TODAS las letras (mm). Negativo las junta.")
        self.par = self._spin("kerning_par", -1000.0, 1000.0, 0.05, " mm", "<b>Kerning de un par</b><br>Ajusta la "
                              "distancia entre las dos letras que rodean al cursor (mm). Con el texto abierto, "
                              "Alt+← / Alt+→ lo ajustan sin salir del teclado.")
        self.par.setEnabled(False)
        self.interlineado = self._spin("interlineado", 0.1, 20.0, 0.05, " ×", "<b>Interlineado (leading)</b><br>"
                                       "Distancia vertical entre líneas, como factor del salto de la fuente "
                                       "(1 = el de la fuente).")
        f = QFormLayout()
        f.setContentsMargins(10, 0, 0, 0)
        f.addRow("Interletraje", self.interletraje)
        f.addRow("Kerning (par)", self.par)
        f.addRow("Interlineado", self.interlineado)
        self._cuerpo_de["Espaciado"].setLayout(f)
        # ---- Alineación y curva
        self._seccion(c, "Alineación y curva", True)
        self.alineacion = self._combo(ALINEACIONES_TEXTO, "alineacion", "<b>Alineación</b><br>De cada línea dentro "
                                      "de la caja (en curva: qué parte del texto cae en su posición).")
        self.ancla_v = self._combo(ANCLAJES_TEXTO, "ancla_v", "<b>Punto de anclaje</b><br>Qué parte del bloque "
                                   "de texto cae sobre el punto donde se hizo clic.")
        self.camino_lado = self._combo(LADOS_TEXTO, "camino_lado", "<b>Lado en curva</b><br>De qué lado de la "
                                       "curva van las letras (solo para texto sobre una curva).")
        f = QFormLayout()
        f.setContentsMargins(10, 0, 0, 0)
        f.addRow("Alineación", self.alineacion)
        f.addRow("Anclaje", self.ancla_v)
        f.addRow("Lado en curva", self.camino_lado)
        self._cuerpo_de["Alineación y curva"].setLayout(f)
        # ---- Decoraciones
        self._seccion(c, "Decoraciones", False)
        self.subrayado = self._combo(DECORACIONES_TEXTO, "subrayado", "<b>Subrayado</b><br>Barra bajo cada línea; "
                                     "forma perfiles que se pueden extruir con las letras.")
        self.tachado = self._combo(DECORACIONES_TEXTO, "tachado", "<b>Tachado</b><br>Barra a media altura de cada "
                                   "línea; forma perfiles que se pueden extruir.")
        self.grosor = self._spin("grosor_decoracion", 0.0, 1000.0, 0.1, " mm", "<b>Grosor</b><br>Grosor de las "
                                 "barras del subrayado y el tachado. «Auto» usa el que trae la fuente.")
        self.grosor.setSpecialValueText("Auto")
        f = QFormLayout()
        f.setContentsMargins(10, 0, 0, 0)
        f.addRow("Subrayado", self.subrayado)
        f.addRow("Tachado", self.tachado)
        f.addRow("Grosor", self.grosor)
        self._cuerpo_de["Decoraciones"].setLayout(f)
        # ---- Transformaciones
        self._seccion(c, "Transformaciones", False)
        self.base = self._spin("desfase_base", -100000.0, 100000.0, 0.5, " mm", "<b>Línea base</b><br>Sube (+) o "
                               "baja (−) todo el texto respecto de su ancla.")
        self.inclinacion = self._spin("inclinacion", -80.0, 80.0, 1.0, " °", "<b>Inclinación</b><br>Sesga las "
                                      "letras, como una cursiva falsa (no usa la cursiva de la fuente).")
        self.escala_h = self._spin("escala_h", 1.0, 1000.0, 5.0, " %", "<b>Ancho</b><br>Escala horizontal de las "
                                   "letras en % del normal.")
        self.escala_v = self._spin("escala_v", 1.0, 1000.0, 5.0, " %", "<b>Alto</b><br>Escala vertical de las "
                                   "letras en % del normal.")
        self.proporcional = QCheckBox("Mantener proporciones (ancho = alto)")
        self.proporcional.setToolTip("Si está activo, cambiar el ancho cambia también el alto, y al revés.")
        self.escala_h.valueChanged.connect(lambda x: self._proporcion(self.escala_v, x))
        self.escala_v.valueChanged.connect(lambda x: self._proporcion(self.escala_h, x))
        self.capitalizacion = self._combo(CAPITALIZACIONES_TEXTO, "capitalizacion", "<b>Mayúsculas y minúsculas"
                                          "</b><br>Cambia cómo se escribe el texto sin tocar lo escrito: "
                                          "MAYÚSCULAS, minúsculas, Título o Versalitas.")
        f = QFormLayout()
        f.setContentsMargins(10, 0, 0, 0)
        f.addRow("Línea base", self.base)
        f.addRow("Inclinación", self.inclinacion)
        f.addRow("Ancho", self.escala_h)
        f.addRow("Alto", self.escala_v)
        f.addRow("", self.proporcional)
        f.addRow("Mayúsculas", self.capitalizacion)
        self._cuerpo_de["Transformaciones"].setLayout(f)
        # ---- Avanzado
        self._seccion(c, "Avanzado", False)
        self.sin_division = QCheckBox("Sin división")
        self.sin_division.setToolTip("<b>Sin división</b><br>Aunque el texto tenga una caja con ancho, no parte las "
                                     "líneas en palabras.")
        self.sin_division.toggled.connect(lambda x: self.cambio.emit("sin_division", bool(x)))
        f = QVBoxLayout()
        f.setContentsMargins(10, 0, 0, 0)
        f.addWidget(self.sin_division)
        self._cuerpo_de["Avanzado"].setLayout(f)
        c.addStretch(1)
        v.addWidget(self.cuerpo, 1)
        self._agarre = _AgarreTamano(self)
        self._agarre.raise_()
        self.ajustar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._agarre.move(0, self.height() - self._agarre.height())
        self._agarre.raise_()

    def set_tamano_usuario(self, ancho, alto):
        """Tamaño elegido arrastrando la esquina: los controles se estiran con él (el alto no baja de lo que
        hace falta para mostrar las secciones abiertas)."""
        self._tam_usuario = [max(int(ancho), 0), max(int(alto), 0)]
        self._reubicar()

    # ------------------------------------------------------------ armado
    def _seccion(self, layout, titulo, abierta):
        """Encabezado plegable «▾ Título» y el cuerpo que muestra u oculta (queda en `_cuerpo_de[titulo]`)."""
        if not hasattr(self, "_cuerpo_de"):
            self._cuerpo_de = {}
        boton = QToolButton()
        boton.setText(("▾ " if abierta else "▸ ") + titulo)
        boton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        boton.setAutoRaise(True)
        boton.setStyleSheet("text-align: left; font-weight: 600;")
        cuerpo = QWidget()
        cuerpo.setVisible(abierta)
        layout.addWidget(boton)
        layout.addWidget(cuerpo)
        self._cuerpo_de[titulo] = cuerpo

        def alternar():
            visible = not cuerpo.isVisible()
            cuerpo.setVisible(visible)
            boton.setText(("▾ " if visible else "▸ ") + titulo)
            self._tam_usuario[1] = 0                  # abrir o plegar una sección: el alto vuelve a ser automático
            self._reubicar()
        boton.clicked.connect(alternar)

    def _combo(self, opciones, clave, ayuda):
        cb = QComboBox()
        for valor, texto in opciones:
            cb.addItem(texto, valor)
        cb.setToolTip(ayuda)
        cb.currentIndexChanged.connect(lambda _i, k=clave, w=cb: self.cambio.emit(k, w.currentData()))
        return cb

    def _spin(self, clave, minimo, maximo, paso, sufijo, ayuda):
        sp = QDoubleSpinBox()
        sp.setDecimals(2)
        sp.setRange(minimo, maximo)
        sp.setSingleStep(paso)
        sp.setSuffix(sufijo)
        sp.setAlignment(Qt.AlignRight)
        sp.setMinimumHeight(24)
        sp.setToolTip(ayuda)
        sp.valueChanged.connect(lambda x, k=clave: self.cambio.emit(k, float(x)))
        return sp

    def _proporcion(self, otro, valor):
        """Con «mantener proporciones», el otro lado de la escala copia el valor."""
        if self.proporcional.isChecked() and abs(otro.value() - valor) > 1e-9:
            otro.setValue(valor)

    # ------------------------------------------------------------ comportamiento
    def ajustar(self):
        """Tamaño: el que hace falta para el contenido o el que eligió la persona si es mayor."""
        self.layout().activate()
        hint = self.sizeHint()
        self.resize(max(hint.width(), self._tam_usuario[0]), max(hint.height(), self._tam_usuario[1]))

    def _reubicar(self):
        self.ajustar()
        area = self.parentWidget()
        if area is not None and hasattr(area, "reubicar"):
            area.reubicar()

    def _plegar(self):
        self._tam_usuario[1] = 0
        self.cuerpo.setVisible(not self.cuerpo.isVisible())
        self.b_plegar.setText("–" if self.cuerpo.isVisible() else "+")
        self._reubicar()

    def _poblar_fuentes(self, actual):
        """Llena la lista según el filtro; la fuente en uso queda en la lista aunque el filtro la excluya."""
        nombres = familias_filtradas(self.filtro.currentData())
        if actual and actual not in nombres:
            nombres = [actual] + nombres
        self.fuente.blockSignals(True)
        self.fuente.clear()
        self.fuente.addItems(nombres)
        for i, nombre in enumerate(nombres):          # cada nombre se ve con su propia tipografía
            self.fuente.setItemData(i, QFont(nombre), Qt.FontRole)
        self.fuente.setCurrentIndex(max(0, self.fuente.findText(actual)))
        if self.fuente.completer() is not None:
            self.fuente.completer().deleteLater()
        comp = QCompleter(nombres, self.fuente)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.activated.connect(lambda t: self.fuente.setCurrentIndex(max(0, self.fuente.findText(t))))
        self.fuente.setCompleter(comp)
        self.fuente.blockSignals(False)

    def _fuente_elegida(self, indice):
        if indice >= 0:
            self.cambio.emit("fuente", self.fuente.itemText(indice))

    def _boton_voltear(self, texto, clave, ayuda):
        b = QToolButton(text=texto)
        b.setCheckable(True)
        b.setToolTip(ayuda)
        b.toggled.connect(lambda x: self.cambio.emit(clave, bool(x)))
        return b

    def _estilo_elegido(self, _i):
        negrita, cursiva = _ESTILO_BC[self.estilo.currentData()]
        self.cambio.emit("negrita", negrita)
        self.cambio.emit("cursiva", cursiva)

    def mostrar_valores(self, altura, interletraje, interlineado, par):
        """Con un texto abierto: los valores de su barra y el kerning en el cursor (sin emitir cambios)."""
        for sp, valor in ((self.altura, altura), (self.interletraje, interletraje),
                          (self.interlineado, interlineado), (self.par, par)):
            sp.blockSignals(True)
            sp.setValue(float(valor))
            sp.blockSignals(False)
        self.par.setEnabled(True)

    def _widgets(self):
        return (self.filtro, self.fuente, self.estilo, self.b_kerning, self.b_voltear_h, self.b_voltear_v, self.subrayado, self.tachado, self.grosor,
                self.base, self.inclinacion, self.escala_h, self.escala_v, self.capitalizacion, self.sin_division,
                self.alineacion, self.ancla_v, self.camino_lado, self.altura, self.interletraje, self.interlineado,
                self.par)

    def cargar(self, o):
        """Muestra las opciones `o` (las del Lienzo) sin emitir cambios."""
        widgets = self._widgets()
        for w in widgets:
            w.blockSignals(True)
        try:
            self._poblar_fuentes(o.get("fuente", "Arial"))
            clave = {v: k for k, v in _ESTILO_BC.items()}[(bool(o.get("negrita")), bool(o.get("cursiva")))]
            self.estilo.setCurrentIndex(max(0, self.estilo.findData(clave)))
            self.b_kerning.setChecked(bool(o.get("kerning", True)))
            self.b_voltear_h.setChecked(bool(o.get("voltear_h")))
            self.b_voltear_v.setChecked(bool(o.get("voltear_v")))
            for cb, clave, defecto in ((self.subrayado, "subrayado", "ninguno"), (self.tachado, "tachado", "ninguno"),
                                       (self.capitalizacion, "capitalizacion", "ninguno"),
                                       (self.alineacion, "alineacion", "izq"), (self.ancla_v, "ancla_v", "base"),
                                       (self.camino_lado, "camino_lado", "izq")):
                cb.setCurrentIndex(max(0, cb.findData(o.get(clave, defecto))))
            for sp, clave, defecto in ((self.grosor, "grosor_decoracion", 0.0), (self.base, "desfase_base", 0.0),
                                       (self.inclinacion, "inclinacion", 0.0), (self.escala_h, "escala_h", 100.0),
                                       (self.escala_v, "escala_v", 100.0), (self.altura, "altura_texto", 5.0),
                                       (self.interletraje, "espaciado", 0.0), (self.interlineado, "interlineado", 1.0)):
                sp.setValue(float(o.get(clave, defecto)))
            self.par.setValue(0.0)
            self.par.setEnabled(False)               # el kerning de un par se ajusta con un texto abierto
            self.sin_division.setChecked(bool(o.get("sin_division")))
        finally:
            for w in widgets:
                w.blockSignals(False)


class ModoBoceto(QObject):
    terminado = Signal(object, object)       # boceto editado, datos de contexto (dict)

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.lienzo = None
        self.paleta = None
        self.caracter = None
        self.datos = None
        self.plano = None
        self.boceto = None
        self._t_perfiles = QTimer(self, singleShot=True, interval=60)
        self._t_perfiles.timeout.connect(self._actualizar_perfiles)
        self._tapadas = []          # acciones de la ventana con el mismo atajo que una del boceto (p. ej. M)
        self.acciones = {}
        self.grupo = QActionGroup(self)
        for clave, texto, herramienta, atajo, ico in ACCIONES_BOCETO:
            a = QAction(icono(ico), texto, ventana, checkable=True)
            ayuda = HERRAMIENTAS.get(herramienta, ("", f"{texto}: hacé clic en la geometría a restringir."))[1]
            visible = (atajo or "").replace("Shift", "Mayúsculas")
            a.setToolTip(f"<b>{texto}</b><br>{ayuda}" + (f"<br><span style='color:#bbbbbb'>{visible}</span>" if atajo else ""))
            if atajo:
                a.setShortcut(QKeySequence(atajo))
                a.setText(f"{texto}\t{visible}")
            a.triggered.connect(lambda _=False, h=herramienta: self.herramienta(h))
            a.setEnabled(False)
            self.grupo.addAction(a)
            ventana.addAction(a)
            self.acciones[clave] = a
        for clave, texto, atajo, ico, funcion, ayuda in (
                ("sk_terminar", "Terminar boceto", None, "terminar", self.terminar,
                 "Sale del boceto y guarda los cambios en el timeline."),
                ("sk_construccion", "Normal / construcción", "X", "rectangulo_centro", self._construccion,
                 "Alterna la geometría seleccionada entre normal y construcción."),
                ("sk_eje", "Normal / línea central", None, "simetria_boceto", self._eje,
                 "Alterna la geometría seleccionada entre normal y línea central (eje)."),
                ("sk_autorestringir", "Restringir automáticamente", None, "r_fijo", self._autorestringir,
                 "AutoConstrain: detecta horizontales, verticales, coincidencias e igualdades y agrega las cotas que "
                 "faltan hasta dejar el boceto totalmente restringido.")):
            a = QAction(icono(ico), texto, ventana)
            a.setToolTip(f"<b>{texto}</b><br>{ayuda}")
            if atajo:
                a.setShortcut(QKeySequence(atajo))
                a.setText(f"{texto}\t{atajo}")
            a.triggered.connect(funcion)
            a.setEnabled(False)
            ventana.addAction(a)
            self.acciones[clave] = a

    @property
    def activo(self):
        return self.lienzo is not None

    # ------------------------------------------------------------ entrar / salir
    def iniciar(self, boceto, plano, datos, mirar=True):
        v = self.v
        self.boceto, self.plano, self.datos = boceto.copia(), plano, datos
        area, visor = v.area, v.visor
        area.set_vistas_multiples(False)
        # evaluar se busca en el documento en cada uso: "Cambiar parámetros" puede reemplazar la tabla
        self.lienzo = Lienzo(self.boceto, lambda *a: v.doc.parametros.evaluar(*a), area, visor=visor, plano=plano)
        self.lienzo.mensaje.connect(lambda t: v.mensaje(t, 7000))
        self.lienzo.cambio.connect(self._cambio)
        self.lienzo.herramienta_cambiada.connect(self._sincronizar_herramienta)
        self.lienzo.texto_en_edicion.connect(self._opciones_de_texto)
        self.lienzo.info.connect(v.info_seleccion)               # "1 línea de boceto | Longitud: …"
        self.lienzo.aviso.connect(lambda t: v.aviso_flotante(t))
        self.paleta = PaletaBoceto(area)
        self.paleta.terminar.connect(self.terminar)
        self.paleta.mirar_a.connect(lambda: visor.mirar_a_plano(self.plano))
        self.paleta.opcion.connect(self._opcion)
        self.paleta.herramienta.connect(self.herramienta)
        self.paleta.lados.connect(lambda n: setattr(self.lienzo, "lados", n))
        self.paleta.opcion_cota.connect(lambda o: setattr(self.lienzo, "opcion_cota", o))
        self.paleta.construccion.connect(self._construccion)
        self.paleta.eje.connect(self._eje)
        self.paleta.ajuste.connect(self._ajuste)
        self.caracter = PanelCaracter(area)         # fuente, decoraciones y transformación del texto
        self.caracter.cambio.connect(self._ajuste)
        self.lienzo.texto_valores.connect(self.caracter.mostrar_valores)
        self.caracter.hide()
        area.set_capa_boceto(self.lienzo, self.paleta, self.caracter)
        visor.paso_boceto = None
        visor.set_plano_boceto(plano, self._opciones_visor())
        if mirar:
            visor.mirar_a_plano(plano)
            if self.boceto.curvas:
                self.lienzo.encuadrar()
        for a in self.acciones.values():
            a.setEnabled(True)
        self._tapar_atajos()
        v.cinta.mostrar_contextual("BOCETO")
        self.lienzo.show()
        self.paleta.show()
        area.reubicar()
        self.lienzo.setFocus()
        self.herramienta("seleccionar")
        self._cambio()

    def terminar(self):
        if not self.activo:
            return True
        self.lienzo.confirmar_texto_pendiente()      # el texto que se está escribiendo entra en el boceto
        r = self.lienzo.resultado
        if r is not None and not r.ok:
            resp = QMessageBox.question(self.v, NOMBRE_APP, "El boceto tiene restricciones en conflicto. "
                                        "¿Terminar igual?")
            if resp != QMessageBox.Yes:
                return False
        boceto, datos = self.boceto, self.datos
        self._limpiar()
        self.terminado.emit(boceto, datos)
        return True

    def cancelar(self):
        """Sale del boceto SIN guardar (al cambiar de documento)."""
        if self.activo:
            self._limpiar()
            self.v._indice_boceto = None
            self.v._refrescar_visibilidad()

    def set_forzar(self, valor):
        if self.activo:
            self.lienzo.ajustar_grilla = valor
            ch = self.paleta.checks["forzar"]
            ch.blockSignals(True)
            ch.setChecked(valor)
            ch.blockSignals(False)

    def _tapar_atajos(self):
        """Dentro del boceto, sus atajos (M = Mover del boceto…) no deben chocar con los de la ventana
        (M = Mover/copiar 3D): con dos acciones habilitadas y el mismo atajo, Qt lo vuelve ambiguo y no
        hace nada. Se deshabilitan las de la ventana mientras dure el boceto."""
        propias = set(self.acciones.values())
        atajos = {a.shortcut().toString() for a in propias if not a.shortcut().isEmpty()}
        self._tapadas = [a for a in self.v.acciones.values()
                         if a not in propias and a.isEnabled() and not a.shortcut().isEmpty()
                         and a.shortcut().toString() in atajos]
        for a in self._tapadas:
            a.setEnabled(False)

    def _limpiar(self):
        self.lienzo._cerrar_entrada()
        self.v.area.set_capa_boceto(None, None)
        for w in (self.lienzo, self.paleta, self.caracter):
            w.hide()
            w.deleteLater()
        self.lienzo = self.paleta = self.caracter = None
        self.v.visor.set_plano_boceto(None)
        self.v.cinta.ocultar_contextual("BOCETO")
        self.v.info_seleccion("")
        for a in self.acciones.values():
            a.setEnabled(False)
            a.setChecked(False)
        for a in self._tapadas:
            a.setEnabled(True)
        self._tapadas = []

    # ------------------------------------------------------------ herramientas y opciones
    def herramienta(self, h):
        if not self.activo:
            return
        self.lienzo.set_herramienta(h)
        self.lienzo.setFocus()

    def _sincronizar_herramienta(self, h):
        clave = f"sk_{h}"
        for k, a in self.acciones.items():
            if a.isCheckable():
                a.setChecked(k == clave)
        if self.paleta is not None:
            self.paleta.set_herramienta(h, self.lienzo.lados, self.lienzo.opcion_cota, self.lienzo.opciones)
            self._mostrar_caracter(h == "texto")
            self.v.area.reubicar()

    def _mostrar_caracter(self, visible):
        """El panel «Carácter» se ve con la herramienta Texto (o al editar un texto) y arranca con sus opciones."""
        if self.caracter is not None:
            if visible:
                self.caracter.cargar(self.lienzo.opciones)
            self.caracter.setVisible(visible)

    def _opciones_de_texto(self):
        """Doble clic sobre un texto: la paleta muestra sus opciones aunque la herramienta activa sea otra."""
        if self.paleta is not None:
            self.paleta.set_herramienta("texto", self.lienzo.lados, self.lienzo.opcion_cota, self.lienzo.opciones)
            self._mostrar_caracter(True)
            self.v.area.reubicar()

    def _tipo_de_linea(self):
        self.paleta.b_construccion.setChecked(self.lienzo.construccion)
        self.paleta.b_eje.setChecked(self.lienzo.eje)

    def _construccion(self):
        if self.activo:
            self.lienzo.alternar_construccion()
            self._tipo_de_linea()

    def _eje(self):
        if self.activo:
            self.lienzo.alternar_eje()
            self._tipo_de_linea()

    def _autorestringir(self):
        if self.activo:
            self.lienzo.auto_restringir()

    def _ajuste(self, clave, valor):
        if self.activo:
            if clave in ("altura_texto", "espaciado", "interlineado"):
                self.lienzo.aplicar_opcion_texto(clave, valor)       # van también a la barra del texto abierto
            elif clave == "kerning_par":
                self.lienzo.ajustar_kerning_par(valor)               # entre las dos letras del cursor
                return
            else:
                self.lienzo.opciones[clave] = valor
            self.lienzo.refrescar_previa_texto()          # fuente, estilo y alineación se ven en vivo

    def _opciones_visor(self):
        ch = self.paleta.checks
        return {"rejilla": ch["rejilla"].isChecked(), "corte": ch["corte"].isChecked(),
                "perfil": ch["perfil"].isChecked()}

    def _opcion(self, clave, valor):
        lz = self.lienzo
        if clave == "forzar":
            self.v.cambiar_vista("forzar_rejilla", valor)     # misma opción que "Forzar objetos a rejilla"
        elif clave in ("puntos", "cotas", "restricciones", "construccion", "rejilla", "proyectadas"):
            lz.mostrar[clave] = valor
        self.v.visor.set_plano_boceto(self.plano, self._opciones_visor())
        lz.update()

    def _cambio(self):
        if self.paleta is not None:
            self.paleta.set_estado(self.lienzo.resultado)
            self.v.area.reubicar()
        self._t_perfiles.start()

    def _actualizar_perfiles(self):
        if not self.activo:
            return
        try:
            perfiles = detectar(self.boceto.geometria(), self.plano)
        except Exception:  # noqa: BLE001 — un boceto a medio dibujar no debe romper la vista
            perfiles = []
        self.v.visor.set_perfiles([p.cara for p in perfiles])
