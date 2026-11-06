# -*- coding: utf-8 -*-
"""
Elementos que flotan sobre el lienzo 3D, como en Fusion 360:
  - ViewCube (arriba a la derecha): cubo que gira con la cámara; clic en una cara = vista estándar,
    arrastrar = órbita, casita = vista inicial (isométrica). Ejes X rojo, Y verde, Z azul.
  - Barra de navegación (abajo al centro) con los menús de visualización, rejilla y ventanas gráficas.
  - AreaVisor: contenedor que apila el visor OpenGL, la capa del boceto y estas superposiciones.
Todo está dibujado con QPainter; QOpenGLWidget admite widgets hijos transparentes encima.
"""
import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFontMetricsF, QKeySequence, QPainter, QPen, QPolygonF,
                           QTransform)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

from . import temas
from .iconos import icono

# cara: (normal, derecha del texto, arriba del texto, etiqueta, vista del visor)
CARAS = [((0, 0, 1), (1, 0, 0), (0, 1, 0), "SUPERIOR", "arriba"),
         ((0, 0, -1), (1, 0, 0), (0, -1, 0), "INFERIOR", "abajo"),
         ((0, -1, 0), (1, 0, 0), (0, 0, 1), "FRONTAL", "frente"),
         ((0, 1, 0), (-1, 0, 0), (0, 0, 1), "POSTERIOR", "atras"),
         ((1, 0, 0), (0, 1, 0), (0, 0, 1), "DERECHA", "derecha"),
         ((-1, 0, 0), (0, -1, 0), (0, 0, 1), "IZQUIERDA", "izquierda")]
TAMANOS = {"pequeno": 90, "automatico": 120, "grande": 150}
EJES = [((1, 0, 0), QColor("#d23c3c"), "X", ((0, -1, 0), (0, 0, -1))),
        ((0, 1, 0), QColor("#3fa34d"), "Y", ((-1, 0, 0), (0, 0, -1))),
        ((0, 0, 1), QColor("#2f5fd0"), "Z", ((-1, 0, 0), (0, -1, 0)))]


class ViewCube(QWidget):
    def __init__(self, visor, parent=None):
        super().__init__(parent)
        self.visor = visor
        self.setMouseTracking(True)
        self.setToolTip("ViewCube: clic en una cara para la vista estándar, arrastrar para orbitar.\n"
                        "Atajos: 0 isométrica, 1 frente, 2 arriba, 3 derecha.")
        self._poligonos = []          # [(QPolygonF, vista)] de las caras visibles, para el clic
        self._hover = None
        self._presionado, self._arrastrado = None, False
        self.set_tamano("automatico")
        visor.camara_cambiada.connect(self.update)

    def set_tamano(self, clave):
        lado = TAMANOS.get(clave, TAMANOS["automatico"])
        self.setFixedSize(lado, lado)

    def _proyectar(self, rot, p, centro, escala):
        v = rot @ np.asarray(p, float)
        return QPointF(centro.x() + v[0] * escala, centro.y() - v[1] * escala), v[2]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rot = self.visor.matriz_vista()[:3, :3]
        centro = QPointF(self.width() * 0.52, self.height() * 0.5)
        escala = self.width() * 0.27
        self._poligonos = []
        luz = np.array([0.35, 0.55, 0.75])
        for normal, der, arr, texto, vista in CARAS:
            n, u, w = (np.array(x, float) for x in (normal, der, arr))
            if (rot @ n)[2] <= 1e-6:
                continue
            esquinas = [n - u + w, n + u + w, n + u - w, n - u - w]
            poli = QPolygonF([self._proyectar(rot, c, centro, escala)[0] for c in esquinas])
            brillo = 0.80 + 0.20 * max(0.0, float((rot @ n) @ luz))
            base = QColor("#8fc3ee") if vista == self._hover else QColor(int(196 * brillo), int(199 * brillo), int(204 * brillo))
            p.setPen(QPen(QColor("#7d838b"), 1))
            p.setBrush(base)
            p.drawPolygon(poli)
            self._etiqueta(p, poli, texto)
            self._poligonos.append((poli, vista))
        origen = np.array([-1.0, -1.0, -1.0])
        f = temas.qfont_cotas(max(7, int(self.width() / 13)))
        f.setBold(True)
        p.setFont(f)
        for eje, color, letra, caras_vecinas in EJES:
            if not any((rot @ np.array(c, float))[2] > 1e-6 for c in caras_vecinas):
                continue                     # la arista queda detrás del cubo
            a = self._proyectar(rot, origen, centro, escala)[0]
            b = self._proyectar(rot, origen + np.array(eje) * 2.55, centro, escala)[0]
            p.setPen(QPen(color, 2))
            p.drawLine(a, b)
            p.drawText(QRectF(b.x() - 10, b.y() - 10, 20, 20), Qt.AlignCenter, letra)
        p.drawPixmap(self._rect_casa().adjusted(2, 2, -2, -2), icono("casa").pixmap(32, 32), QRectF(0, 0, 32, 32))
        p.end()

    def _rect_casa(self):
        """Botón "vista inicial" arriba a la derecha (a la izquierda tapaba la letra Z del eje)."""
        return QRectF(self.width() - 20, 0, 20, 20)

    def _etiqueta(self, p, poli, texto):
        ancho, alto = 100.0, 100.0
        f = temas.qfont_cotas(15)
        f.setBold(True)
        while QFontMetricsF(f).horizontalAdvance(texto) > ancho * 0.9 and f.pointSizeF() > 6:
            f.setPointSizeF(f.pointSizeF() - 1)
        t = QTransform()
        if not QTransform.quadToQuad(QPolygonF([QPointF(0, 0), QPointF(ancho, 0), QPointF(ancho, alto), QPointF(0, alto)]),
                                     poli, t):
            return
        p.save()
        p.setTransform(t, True)
        p.setFont(f)
        p.setPen(QColor("#5f656d"))
        p.drawText(QRectF(0, 0, ancho, alto), Qt.AlignCenter, texto)
        p.restore()

    def _cara_en(self, pos):
        for poli, vista in self._poligonos:
            if poli.containsPoint(pos, Qt.OddEvenFill):
                return vista
        return None

    def mouseMoveEvent(self, e):
        if self._presionado is not None and e.buttons() & Qt.LeftButton:
            d = e.position() - self._presionado
            if d.manhattanLength() > 3:
                self.visor.orbitar(d.x(), d.y())
                self._presionado = e.position()
                self._arrastrado = True
            return
        cara = self._cara_en(e.position())
        if cara != self._hover:
            self._hover = cara
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._presionado, self._arrastrado = e.position(), False

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._presionado is None:
            return
        arrastrado, self._presionado = self._arrastrado, None
        if arrastrado:
            return
        if self._rect_casa().contains(e.position()):
            self.visor.animar_vista(lambda: self.visor.vista("iso"))
            return
        cara = self._cara_en(e.position())
        if cara:
            self.visor.animar_vista(lambda: self.visor.vista(cara))

    def leaveEvent(self, _e):
        self._hover = None
        self.update()


class BarraNavegacion(QFrame):
    """
    Barra de navegación y visualización (abajo al centro), con los menús de Fusion:
    Órbita ▾ (libre / restringida), Mirar a, Encuadre, Zoom, Ventana de zoom ▾ (ventana / ajustar),
    Configuración de visualización ▾ (estilo visual, entorno, valor predefinido de gráficos, efectos,
    visibilidad del objeto, cámara, desfase de plano de suelo, pantalla completa), Rejilla y
    forzados ▾ y Ventanas gráficas ▾. Lo que el clon no tiene aparece grisado.
    `ctl` es la ventana: guarda las preferencias y aplica los cambios a todas las vistas.
    """

    def __init__(self, visor, ctl, parent=None):
        super().__init__(parent)
        self.setObjectName("barra_navegacion")
        self.visor, self.ctl = visor, ctl
        self.menus = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 4, 1)
        lay.setSpacing(1)
        self.grupo_modos = QActionGroup(self)
        self.grupo_modos.setExclusionPolicy(QActionGroup.ExclusionPolicy.ExclusiveOptional)
        self.modos = {}
        for modo, nombre, ico, ayuda in (
                ("orbita", "Órbita", "orbita_libre", "Gira la vista con el botón izquierdo (Esc para salir)."),
                ("mirar", "Mirar a", "mirar_a", "Hacé clic en una cara plana o un plano para mirarlo de frente."),
                ("encuadre", "Encuadre", "encuadre", "Desplaza la vista con el botón izquierdo."),
                ("zoom", "Zoom", "zoom", "Acerca o aleja arrastrando con el botón izquierdo."),
                ("ventana", "Ventana de zoom", "ventana_zoom", "Dibujá un rectángulo: lo que encierra llena la vista.")):
            a = QAction(icono(ico), nombre, self, checkable=True)
            a.setToolTip(f"<b>{nombre}</b><br>{ayuda}")
            a.toggled.connect(lambda activo, m=modo: self._modo(m, activo))
            self.grupo_modos.addAction(a)
            self.modos[modo] = a

        menu = self._menu("orbita")
        g = QActionGroup(self)
        self.tipos_orbita = {}
        for clave, texto in (("libre", "Órbita libre"), ("restringida", "Órbita restringida")):
            a = menu.addAction(icono(f"orbita_{clave}"), texto)
            a.setCheckable(True)
            a.triggered.connect(lambda _=False, c=clave: self._tipo_orbita(c))
            g.addAction(a)
            self.tipos_orbita[clave] = a
        menu.aboutToShow.connect(lambda: self.tipos_orbita[ctl.valor_vista("tipo_orbita")].setChecked(True))
        lay.addWidget(self._boton(self.modos["orbita"], menu))
        lay.addWidget(self._boton(self.modos["mirar"]))
        lay.addWidget(self._boton(self.modos["encuadre"]))
        lay.addWidget(self._boton(self.modos["zoom"]))
        menu = self._menu("ventana")
        menu.addAction(self.modos["ventana"])
        menu.addAction(ctl.acciones["ajustar"])
        lay.addWidget(self._boton(self.modos["ventana"], menu))
        lay.addWidget(self._separador())
        lay.addWidget(self._boton_menu("visualizacion", "Configuración de visualización", self._menu_visualizacion()))
        lay.addWidget(self._boton_menu("rejilla", "Rejilla y forzados", self._menu_rejilla()))
        lay.addWidget(self._boton_menu("vistas_multiples", "Ventanas gráficas", self._menu_ventanas()))
        visor.modo_cambiado.connect(self._sincronizar_modo)

    # ------------------------------------------------------------ armado
    def _menu(self, clave):
        m = QMenu(self)
        m.setToolTipsVisible(True)
        self.menus[clave] = m
        return m

    def _separador(self):
        s = QFrame(objectName="separador_barra")
        s.setFixedSize(1, 18)
        return s

    def _boton(self, accion, menu=None):
        b = QToolButton()
        b.setDefaultAction(accion)
        b.setIconSize(QSize(20, 20))
        if menu is not None:
            b.setMenu(menu)
            b.setPopupMode(QToolButton.MenuButtonPopup)
            b.setStyleSheet("QToolButton::menu-button { width: 10px; border: 0; }"
                            "QToolButton::menu-arrow { width: 7px; }")
        return b

    def _boton_menu(self, ico, ayuda, menu):
        b = QToolButton()
        b.setIcon(icono(ico))
        b.setIconSize(QSize(20, 20))
        b.setText(" ▾")
        b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        b.setToolTip(f"<b>{ayuda}</b>")
        b.setPopupMode(QToolButton.InstantPopup)
        b.setMenu(menu)
        # Sin esto el botón queda más angosto que icono + «▾» + flecha del menú (medido: 48 px para
        # 51 necesarios): la flecha se corta (auditoría P9, 2026-10-16).
        b.setMinimumWidth(b.sizeHint().width())
        return b

    def _opcion(self, menu, texto, clave, valor=None, atajo=None, grupo=None, activa=True, ayuda=None):
        """Ítem que lee y escribe una opción de vista (`clave`). Con `valor` es de opción única."""
        a = menu.addAction(texto)
        a.setCheckable(True)
        a.setEnabled(activa)
        if not activa:
            a.setToolTip("No disponible en OmniCAD.")
        elif ayuda:
            a.setToolTip(f"<b>{texto.split(chr(9))[0]}</b><br>{ayuda}")
        if atajo:
            a.setShortcut(QKeySequence(atajo))
            a.setText(f"{texto}\t{atajo.replace('Ctrl', 'Control').replace('Shift', 'Mayúsculas')}")
            self.ctl.addAction(a)
        if grupo is not None:
            grupo.addAction(a)
        if valor is None:
            a.triggered.connect(lambda marcado, c=clave: self.ctl.cambiar_vista(c, marcado))
        else:
            a.triggered.connect(lambda _=False, c=clave, v=valor: self.ctl.cambiar_vista(c, v))
        menu.aboutToShow.connect(lambda a=a, c=clave, v=valor: a.setChecked(
            self.ctl.valor_vista(c) == v if v is not None else bool(self.ctl.valor_vista(c))))
        return a

    def _titulo(self, menu, texto):
        a = menu.addAction(texto)
        a.setEnabled(False)

    def _menu_visualizacion(self):
        from .visor3d import ENTORNOS, ESTILOS
        m = self._menu("visualizacion")
        AYUDA_ESTILO = {"sombreado": "Superficies pintadas, con la luz del entorno.",
                        "sombreado_ocultas": "Superficies pintadas y las aristas tapadas en punteado.",
                        "sombreado_aristas": "Superficies pintadas y solo las aristas que se ven.",
                        "alambrico": "Solo las aristas del modelo, sin superficies.",
                        "alambrico_ocultas": "Solo aristas, con las tapadas en punteado.",
                        "alambrico_visibles": "Solo las aristas que se ven, sin superficies."}
        sub = m.addMenu("Estilo visual")
        g = QActionGroup(self)
        self.estilos = {}
        for i, (clave, texto) in enumerate(ESTILOS.items()):
            self.estilos[clave] = self._opcion(sub, texto, "estilo_visual", clave, f"Ctrl+{i + 4}", g,
                                               ayuda=AYUDA_ESTILO.get(clave))
        sub = m.addMenu("Entorno")
        g = QActionGroup(self)
        self._opcion(sub, ENTORNOS["tema"][0], "entorno", "tema", grupo=g,
                     ayuda="El fondo de la vista sale del tema activo de la interfaz.")
        sub.addSeparator()
        self._titulo(sub, "Entornos de temas")
        for clave in ("fotomaton", "rubicon", "cielo_oscuro"):
            self._opcion(sub, "   " + ENTORNOS[clave][0], "entorno", clave, grupo=g,
                         ayuda="Cambia el fondo y la luz con que se ve el modelo.")
        sub.addSeparator()
        self._titulo(sub, "Entornos heredados")
        for clave in ("infinito", "habitacion_gris", "azul_tranquilidad"):
            self._opcion(sub, "   " + ENTORNOS[clave][0], "entorno", clave, grupo=g,
                         ayuda="Cambia el fondo y la luz con que se ve el modelo.")
        sub = m.addMenu("Valor predefinido de gráficos")
        g = QActionGroup(self)
        for clave, texto, ayuda in (
                ("rendimiento", "Rendimiento", "Lo más rápido: menos efectos, para modelos grandes."),
                ("equilibrado", "Equilibrado", "Buen punto medio entre velocidad y calidad."),
                ("calidad", "Calidad", "Todos los efectos, al costo de cuadros por segundo."),
                ("personalizar", "Personalizar", "Elegir a mano cada efecto (menú Efectos).")):
            self._opcion(sub, texto, "preset", clave, grupo=g, ayuda=ayuda)
        sub = m.addMenu("Efectos")
        indicador = sub.addAction("Valor predefinido de gráficos")
        indicador.setCheckable(True)
        indicador.setEnabled(False)
        sub.aboutToShow.connect(lambda: (indicador.setChecked(True), indicador.setText(
            f"Valor predefinido de gráficos: {self.ctl.valor_vista('preset')}")))
        sub.addSeparator()
        for clave, texto, activa, ayuda in (
                ("cupula", "Cúpula de entorno", True, "Dibujar el degradado del entorno alrededor del modelo."),
                ("suelo", "Plano del suelo", True, "Dibujar el plano que apoya al modelo."),
                ("sombra_suelo", "Sombra en el suelo", True, "La sombra del modelo sobre el plano del suelo."),
                ("reflejo", "Reflejo en el suelo", True, "Reflejar el modelo en el plano del suelo."),
                ("sombra_objeto", "Sombra de objeto", False, ""),
                ("oclusion", "Oclusión ambiental", False, ""),
                ("aa", "Anti-aliasing", True, "Suaviza las aristas diagonales de la vista.")):
            self._opcion(sub, texto, f"efecto:{clave}", activa=activa, ayuda=ayuda)
        sub = m.addMenu("Visibilidad del objeto")
        self._opcion(sub, "Todas las operaciones de trabajo", "visibilidad:todas",
                     ayuda="Mostrar todo, apagado o no en el navegador.")
        sub.addSeparator()
        for clave, texto, activa in (
                ("planos_origen", "Planos de origen", True), ("ejes_origen", "Ejes de origen", True),
                ("punto_origen", "Puntos de origen", True), ("planos_usuario", "Planos de trabajo de usuario", True),
                ("ejes_usuario", "Ejes de trabajo de usuario", False), ("puntos_usuario", "Puntos de trabajo de usuario", False),
                ("nombres_planos_construccion", "Nombres de planos de construcción", True),
                ("nombres_planos_origen", "Nombres de planos de origen", True),
                ("bocetos", "Bocetos", True), ("scu", "Sistemas de coordenadas del usuario", False),
                ("origenes_union", "Orígenes de unión", False), ("ejes_union", "Ejes de origen de unión", False),
                ("uniones", "Uniones", False)):
            self._opcion(sub, texto, f"visibilidad:{clave}", activa=activa,
                         ayuda="Mostrar este tipo de elemento aunque esté apagado en el navegador.")
        sub = m.addMenu("Cámara")
        g = QActionGroup(self)
        self.camaras = {}
        for clave, texto, ayuda in (("ortografica", "Ortográfica",
                                     "Sin perspectiva: lo lejano no se achica (dibujos técnicos)."),
                                    ("perspectiva", "Perspectiva", "Como el ojo: lo lejano se ve más chico."),
                                    ("persp_orto_caras", "Perspectiva con caras ortográficas",
                                     "Perspectiva general con las caras frontales sin deformación.")):
            self.camaras[clave] = self._opcion(sub, texto, "camara", clave, grupo=g, ayuda=ayuda)
        self._opcion(m, "Desfase de plano de suelo", "desfase_suelo",
                     ayuda="Sube o baja el plano del suelo (el valor de Preferencias › Visualización).")
        m.addSeparator()
        a = m.addAction(icono("pantalla_completa"), "Activar pantalla completa\tControl+Mayúsculas+F")
        a.setToolTip("<b>Activar pantalla completa</b><br>La ventana ocupa toda la pantalla (mismo atajo para salir).")
        a.setShortcut(QKeySequence("Ctrl+Shift+F"))
        a.triggered.connect(self.ctl.pantalla_completa)
        self.ctl.addAction(a)
        return m

    def _menu_rejilla(self):
        m = self._menu("rejilla")
        self._opcion(m, "Rejilla de esbozo", "rejilla", ayuda="Mostrar la rejilla de la vista.")
        self._opcion(m, "Bloqueo de rejilla de esbozo", "rejilla_bloqueada",
                     ayuda="Fija la rejilla: ya no se mueve con la cámara.")
        self._opcion(m, "Forzar objetos a rejilla", "forzar_rejilla",
                     ayuda="Los clics y puntos se pegan a los pasos de la rejilla.")
        a = m.addAction(icono("rejilla"), "Parámetros de rejilla")
        a.setToolTip("<b>Parámetros de rejilla</b><br>Paso y estilo de la rejilla (igual que Preferencias).")
        a.triggered.connect(self.ctl.parametros_rejilla)
        m.addSeparator()
        for texto in ("Desplazamiento incremental", "Definir incrementos"):
            a = m.addAction(texto)
            a.setEnabled(False)
            a.setToolTip("No disponible en OmniCAD: no hay herramienta de mover con incrementos.")
        return m

    def _menu_ventanas(self):
        m = self._menu("ventanas")
        g = QActionGroup(self)
        self._opcion(m, "Vista única", "vistas_multiples", False, grupo=g,
                     ayuda="Una sola vista del modelo.")
        self._opcion(m, "Vistas múltiples", "vistas_multiples", True, "Shift+1", g,
                     ayuda="Cuatro vistas a la vez: frente, arriba, derecha e isométrica.")
        return m

    # ------------------------------------------------------------ modos de navegación
    def _modo(self, modo, activo):
        if modo == "mirar" and activo and self.ctl.mirar_a():
            self.modos["mirar"].setChecked(False)      # en un boceto, "Mirar a" mira el plano directamente
            return
        if activo:
            self.visor.set_modo(modo)
        elif self.visor.modo == modo:
            self.visor.set_modo(None)

    def _tipo_orbita(self, clave):
        self.ctl.cambiar_vista("tipo_orbita", clave)
        self.modos["orbita"].setIcon(icono(f"orbita_{clave}"))
        self.modos["orbita"].setChecked(True)

    def _sincronizar_modo(self, modo):
        for clave, a in self.modos.items():
            if a.isChecked() != (clave == modo):
                a.setChecked(clave == modo)

    def set_estilo(self, clave):
        if clave in self.estilos:
            self.estilos[clave].setChecked(True)


ALTO_UTIL_PANEL = 330        # alto mínimo que se le quiere dar a un panel de comando debajo del ViewCube


class CabeceraMovible(QFrame):
    """Cabecera de una tarjeta flotante: arrastrarla mueve la tarjeta (queda en `posicion_usuario`, siempre dentro de la
    vista, y `AreaVisor.reubicar` la respeta); el doble clic la devuelve a su lugar de siempre."""

    def __init__(self, tarjeta):
        super().__init__(tarjeta, objectName="cabecera_comando")
        self.tarjeta = tarjeta
        self._inicio = None
        self._movida = False
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Arrastrá para mover. Doble clic: volver a su lugar")

    def _area(self):
        return self.tarjeta.parentWidget()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._inicio = e.globalPosition().toPoint() - self.tarjeta.pos()
            self._movida = False

    def mouseMoveEvent(self, e):
        if self._inicio is not None:
            self.tarjeta.posicion_usuario = e.globalPosition().toPoint() - self._inicio
            self._movida = True
            area = self._area()
            if hasattr(area, "reubicar"):
                area.reubicar()

    def mouseReleaseEvent(self, _e):
        self._inicio = None
        area = self._area()
        if self._movida and hasattr(area, "posicion_cambiada"):
            area.posicion_cambiada(self.tarjeta)         # solo si se movió: un clic suelto no borra la posición recordada

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.tarjeta.posicion_usuario = None
            area = self._area()
            if hasattr(area, "posicion_cambiada"):
                area.posicion_cambiada(self.tarjeta, restablecida=True)
            if hasattr(area, "reubicar"):
                area.reubicar()


class AreaVisor(QWidget):
    """
    Lienzo 3D con widgets flotantes encima (posicionados en resizeEvent): navegador arriba a la
    izquierda, ViewCube arriba a la derecha, paleta de boceto debajo del ViewCube, barra de
    navegación abajo al centro y, en el modo boceto, la capa de dibujo sobre el visor.
    Con "Vistas múltiples" muestra 4 vistas (superior, frontal, derecha y la principal).
    """

    def __init__(self, visor, parent=None):
        super().__init__(parent)
        self.visor = visor
        visor.setParent(self)
        self.arriba_izq = []
        self.abajo_izq = []               # panel COMENTARIOS (abajo a la izquierda, sobre el timeline)
        self.viewcube = ViewCube(visor, self)
        self.barra = None
        self.tira = None                  # comandos sugeridos según lo elegido (ui/sugerencias.py), sobre la barra
        self.capa = None
        self.paleta = None
        self.laterales = []               # paneles del boceto a la izquierda de la paleta: «Carácter» (texto) y SIMETRÍA
        self.panel = None                 # diálogo de comando abierto (a la derecha, debajo del ViewCube)
        self.barra_posicion = None        # panel «Posición»: componentes movidos sin capturar (arriba al centro)
        self.posicion_panel = None        # dónde lo dejó la persona: (distancia al borde derecho, distancia al borde de arriba)
        self.al_mover_panel = None        # función(posicion_panel o None): la ventana la guarda en las preferencias
        self.extras = []                  # visores de las vistas múltiples
        self.multiples = False
        self.aviso = QLabel(self)
        self.aviso.setStyleSheet("background: #4a4a4a; color: #ffffff; padding: 5px 10px; border-radius: 3px;")
        self.aviso.hide()
        from .avisos import AvisoFlotante
        self.toast = AvisoFlotante(self)       # "1 advertencia(s)" abajo a la derecha, como Fusion

    @property
    def visores(self):
        return [self.visor] + (self.extras if self.multiples else [])

    def set_barra(self, barra):
        self.barra = barra
        barra.setParent(self)

    def set_tira(self, tira):
        self.tira = tira
        tira.setParent(self)

    def anclar_arriba_izq(self, w):
        w.setParent(self)
        self.arriba_izq.append(w)

    def anclar_abajo_izq(self, w):
        w.setParent(self)
        self.abajo_izq.append(w)

    def set_panel(self, panel):
        self.panel = panel
        if panel is not None:
            panel.setParent(self)
        self.reubicar()

    def set_capa_boceto(self, capa, paleta, *laterales):
        self.capa, self.paleta = capa, paleta
        self.laterales = [w for w in laterales if w is not None]
        self.reubicar()

    def mostrar_aviso(self, texto):
        if texto:
            self.aviso.setText(texto)
            self.aviso.adjustSize()
            self.aviso.show()
        else:
            self.aviso.hide()
        self.reubicar()

    def set_vistas_multiples(self, activo, preparar=None):
        """Vista única o 4 vistas. `preparar(visor, vista)` configura cada vista nueva."""
        if activo and not self.extras:
            from .visor3d import Visor3D
            for vista in ("arriba", "frente", "derecha"):
                v = Visor3D(self, config=self.visor.config)
                if preparar is not None:
                    preparar(v, vista)
                self.extras.append(v)
        self.multiples = bool(activo) and bool(self.extras)
        for v in self.extras:
            v.setVisible(self.multiples)
        self.reubicar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.reubicar()

    def _posicion_fija_panel(self, g):
        """Esquina del panel de comando si la persona lo movió (mientras lo arrastra o recordada de antes); si no, None."""
        if self.panel is None or not self.panel.isVisible() or not hasattr(self.panel, "posicion_usuario"):
            return None                       # los paneles de render no tienen cabecera movible: no heredan el lugar de los de comando
        viva = self.panel.posicion_usuario
        if viva is not None or self.posicion_panel is None:
            return viva
        derecha, arriba = self.posicion_panel
        return QPoint(g.right() - derecha - self.panel.width(), g.top() + arriba)

    def posicion_cambiada(self, tarjeta, restablecida=False):
        """La persona soltó la cabecera de `tarjeta` o le hizo doble clic: del panel de comando se recuerda dónde quedó
        (respecto del borde derecho y del de arriba, para que siga bien si cambia el tamaño de la ventana)."""
        if tarjeta is not self.panel:
            return
        g = self.visor.geometry()
        if restablecida or tarjeta.posicion_usuario is None:
            self.posicion_panel = None
        else:
            self.posicion_panel = (g.right() - (tarjeta.x() + tarjeta.width()), tarjeta.y() - g.top())
            tarjeta.posicion_usuario = None            # en adelante manda la recordada, anclada al borde derecho
        if self.al_mover_panel is not None:
            self.al_mover_panel(self.posicion_panel)

    def reubicar(self):
        w, h = self.width(), self.height()
        if self.multiples:
            mw, mh = w // 2, h // 2
            for v, (x, y) in zip(self.extras, ((0, 0), (mw, 0), (0, mh)), strict=True):
                v.setGeometry(x, y, mw - 1, mh - 1)
            self.visor.setGeometry(mw, mh, w - mw, h - mh)
        else:
            self.visor.setGeometry(self.rect())
        if self.capa is not None:
            self.capa.setGeometry(self.visor.geometry())
            self.capa.raise_()
        for wid in self.arriba_izq:
            if hasattr(wid, "ajustar_alto"):
                wid.ajustar_alto()          # el alto máximo depende del alto del lienzo
            wid.move(6, 6)
            wid.raise_()
        g = self.visor.geometry()
        for wid in self.abajo_izq:
            wid.adjustSize()
            wid.move(g.left() + 2, g.bottom() - wid.height() - 2)
            wid.raise_()
        self.viewcube.move(g.right() - self.viewcube.width() - 14, g.top() + 12)
        self.viewcube.raise_()
        for hijo in self.findChildren(QFrame, options=Qt.FindDirectChildrenOnly):
            if hasattr(hijo, "ubicar_informacion"):
                hijo.ubicar_informacion()
        if self.barra_posicion is not None and self.barra_posicion.isVisible():
            self.barra_posicion.adjustSize()
            libre = max((wid.geometry().right() for wid in self.arriba_izq if wid.isVisible()), default=g.left()) + 8
            self.barra_posicion.move(max(libre, g.left() + (g.width() - self.barra_posicion.width()) // 2), g.top() + 8)
            self.barra_posicion.raise_()
        y = self.viewcube.y() + self.viewcube.height() + 10
        abajo = h - (self.barra.height() + 8 if self.barra is not None and self.barra.isVisible() else 0) - 8
        fija = self._posicion_fija_panel(g)
        if fija is not None:                  # lo movió la persona: queda ahí, sin salirse de la vista ni bajo la barra (el pie siempre entra)
            if hasattr(self.panel, "ajustar_alto"):
                self.panel.ajustar_alto(abajo - g.top() - 4)
            self.panel.move(max(g.left() + 4, min(fija.x(), g.right() - self.panel.width() - 4)),
                            max(g.top() + 4, min(fija.y(), abajo - self.panel.height())))
            self.panel.raise_()
        elif self.panel is not None and self.panel.isVisible():
            if hasattr(self.panel, "ajustar_alto"):
                if g.bottom() - y - 8 < ALTO_UTIL_PANEL:         # ventana baja: el panel sube y tapa el ViewCube (si no, queda un cuerpo de pocas filas)
                    y = g.top() + 8
                self.panel.ajustar_alto(g.bottom() - y - 8)      # B-105: los paneles de comando tienen barra
            if y + self.panel.height() > g.bottom() - 8:         # F3: en una ventana baja, sube para que el pie se vea
                y = max(g.top() + 4, g.bottom() - self.panel.height() - 8)
            self.panel.move(g.right() - self.panel.width() - 10, y)
            self.panel.raise_()
            y += self.panel.height() + 8
        if self.paleta is not None:
            self.paleta.ajustar(g.height() - 12)
            # en una ventana baja sube y tapa el ViewCube: Terminar boceto siempre tiene que verse
            self.paleta.move(g.right() - self.paleta.width() - 10,
                             max(g.top() + 4, min(y, g.bottom() - self.paleta.height() - 8)))
            self.paleta.raise_()
            for lateral in self.laterales:
                if lateral.isVisible():
                    if hasattr(lateral, "ajustar_alto"):
                        lateral.ajustar_alto(abajo - g.top() - 4)       # UI-8: no pasa del alto del lienzo, su cuerpo tiene barra
                    else:
                        lateral.ajustar()
                    sube = y + lateral.height() > abajo and lateral.height() <= abajo - g.top() - 4
                    x, ly = max(g.left() + 4, self.paleta.x() - lateral.width() - 8), abajo - lateral.height() if sube else y     # en una ventana baja sube: la barra de vista no lo tapa
                    if (g.width() < 1100 and getattr(lateral, "control", None) is not None and getattr(lateral, "control", None) is
                            getattr(self.capa, "objetos", None)):
                        # En una ventana baja las dos tarjetas comparten columna; Terminar sigue a la vista.
                        x, ly = g.right() - lateral.width() - 10, g.top() + 4
                        pie = self.paleta.b_terminar.mapTo(self, QPoint(0, 0)).y() - 8
                        lateral.ajustar_alto(max(80, min(abajo, pie) - ly))
                    fija = getattr(lateral, "posicion_usuario", None)
                    if fija is not None:                 # la movió la persona: queda ahí, sin salirse de la vista
                        x = max(g.left() + 4, min(fija.x(), g.right() - lateral.width() - 4))
                        ly = max(g.top() + 4, min(fija.y(), abajo - lateral.height()))
                    lateral.move(x, ly)
                    lateral.raise_()
        if self.barra is not None:
            self.barra.adjustSize()
            self.barra.move((w - self.barra.width()) // 2, h - self.barra.height() - 8)
            self.barra.raise_()
        panel_objetos = getattr(self, "panel_objetos", None)
        if panel_objetos is not None and panel_objetos.isVisible() and self.panel is None and self.paleta is None:
            y_objetos = self.viewcube.geometry().bottom() + 8
            if abajo - y_objetos < ALTO_UTIL_PANEL:
                y_objetos = g.top() + 8
            panel_objetos.ajustar_alto(abajo - y_objetos)
            panel_objetos.move(g.right() - panel_objetos.width() - 8, y_objetos)
            panel_objetos.raise_()
        if self.tira is not None and self.tira.isVisible():
            self.tira.adjustSize()
            abajo = h - (self.barra.height() + 8 if self.barra is not None and self.barra.isVisible() else 0) - 8
            self.tira.move((w - self.tira.width()) // 2, abajo - self.tira.height())
            self.tira.raise_()
        if self.aviso.isVisible():
            self.aviso.move((w - self.aviso.width()) // 2, 12)
            self.aviso.raise_()
        if self.toast.isVisible():
            # en el boceto va al lado de la paleta: encima taparía Terminar boceto
            derecha = g.right() if self.paleta is None else self.paleta.x() - 2
            self.toast.move(max(g.left() + 4, derecha - self.toast.width() - 8), g.bottom() - self.toast.height() - 10)
            p = self.panel
            if p is not None and p.isVisible() and p.geometry().intersects(self.toast.geometry()):
                # H-94: como Fusion, no tapa el panel de comando: a su izquierda, o a su derecha si no entra
                x = p.x() - self.toast.width() - 8
                self.toast.move(x if x >= g.left() + 4 else p.geometry().right() + 8, self.toast.y())
            self.toast.raise_()
