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
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QFontMetricsF, QKeySequence, QPainter, QPen, QPolygonF,
                           QTransform)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

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
        f = QFont("Segoe UI", max(7, int(self.width() / 13)))
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
        f = QFont("Segoe UI", 15)
        f.setBold(True)
        while QFontMetricsF(f).horizontalAdvance(texto) > ancho * 0.9 and f.pointSize() > 6:
            f.setPointSize(f.pointSize() - 1)
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
            self.visor.vista("iso")
            return
        cara = self._cara_en(e.position())
        if cara:
            self.visor.vista(cara)

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
        s = QFrame()
        s.setFixedSize(1, 18)
        s.setStyleSheet("background: #c8c8c8;")
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
        return b

    def _opcion(self, menu, texto, clave, valor=None, atajo=None, grupo=None, activa=True):
        """Ítem que lee y escribe una opción de vista (`clave`). Con `valor` es de opción única."""
        a = menu.addAction(texto)
        a.setCheckable(True)
        a.setEnabled(activa)
        if not activa:
            a.setToolTip("No disponible en OmniCAD.")
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
        sub = m.addMenu("Estilo visual")
        g = QActionGroup(self)
        self.estilos = {}
        for i, (clave, texto) in enumerate(ESTILOS.items()):
            self.estilos[clave] = self._opcion(sub, texto, "estilo_visual", clave, f"Ctrl+{i + 4}", g)
        sub = m.addMenu("Entorno")
        g = QActionGroup(self)
        self._opcion(sub, ENTORNOS["tema"][0], "entorno", "tema", grupo=g)
        sub.addSeparator()
        self._titulo(sub, "Entornos de temas")
        for clave in ("fotomaton", "rubicon", "cielo_oscuro"):
            self._opcion(sub, "   " + ENTORNOS[clave][0], "entorno", clave, grupo=g)
        sub.addSeparator()
        self._titulo(sub, "Entornos heredados")
        for clave in ("infinito", "habitacion_gris", "azul_tranquilidad"):
            self._opcion(sub, "   " + ENTORNOS[clave][0], "entorno", clave, grupo=g)
        sub = m.addMenu("Valor predefinido de gráficos")
        g = QActionGroup(self)
        for clave, texto in (("rendimiento", "Rendimiento"), ("calidad", "Calidad"), ("personalizar", "Personalizar")):
            self._opcion(sub, texto, "preset", clave, grupo=g)
        sub = m.addMenu("Efectos")
        indicador = sub.addAction("Valor predefinido de gráficos")
        indicador.setCheckable(True)
        indicador.setEnabled(False)
        sub.aboutToShow.connect(lambda: (indicador.setChecked(True), indicador.setText(
            f"Valor predefinido de gráficos: {self.ctl.valor_vista('preset')}")))
        sub.addSeparator()
        for clave, texto, activa in (("cupula", "Cúpula de entorno", True), ("suelo", "Plano del suelo", True),
                                     ("sombra_suelo", "Sombra en el suelo", True),
                                     ("reflejo", "Reflejo en el suelo", True), ("sombra_objeto", "Sombra de objeto", False),
                                     ("oclusion", "Oclusión ambiental", False), ("aa", "Anti-aliasing", True)):
            self._opcion(sub, texto, f"efecto:{clave}", activa=activa)
        sub = m.addMenu("Visibilidad del objeto")
        self._opcion(sub, "Todas las operaciones de trabajo", "visibilidad:todas")
        sub.addSeparator()
        for clave, texto, activa in (
                ("planos_origen", "Planos de origen", True), ("ejes_origen", "Ejes de origen", True),
                ("punto_origen", "Puntos de origen", True), ("planos_usuario", "Planos de trabajo de usuario", True),
                ("ejes_usuario", "Ejes de trabajo de usuario", False), ("puntos_usuario", "Puntos de trabajo de usuario", False),
                ("bocetos", "Bocetos", True), ("scu", "Sistemas de coordenadas del usuario", False),
                ("origenes_union", "Orígenes de unión", False), ("ejes_union", "Ejes de origen de unión", False),
                ("uniones", "Uniones", False)):
            self._opcion(sub, texto, f"visibilidad:{clave}", activa=activa)
        sub = m.addMenu("Cámara")
        g = QActionGroup(self)
        self.camaras = {}
        for clave, texto in (("ortografica", "Ortográfica"), ("perspectiva", "Perspectiva"),
                             ("persp_orto_caras", "Perspectiva con caras ortográficas")):
            self.camaras[clave] = self._opcion(sub, texto, "camara", clave, grupo=g)
        self._opcion(m, "Desfase de plano de suelo", "desfase_suelo")
        m.addSeparator()
        a = m.addAction(icono("pantalla_completa"), "Activar pantalla completa\tControl+Mayúsculas+F")
        a.setShortcut(QKeySequence("Ctrl+Shift+F"))
        a.triggered.connect(self.ctl.pantalla_completa)
        self.ctl.addAction(a)
        return m

    def _menu_rejilla(self):
        m = self._menu("rejilla")
        self._opcion(m, "Rejilla de esbozo", "rejilla")
        self._opcion(m, "Bloqueo de rejilla de esbozo", "rejilla_bloqueada")
        self._opcion(m, "Forzar objetos a rejilla", "forzar_rejilla")
        a = m.addAction(icono("rejilla"), "Parámetros de rejilla")
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
        self._opcion(m, "Vista única", "vistas_multiples", False, grupo=g)
        self._opcion(m, "Vistas múltiples", "vistas_multiples", True, "Shift+1", g)
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
        self.capa = None
        self.paleta = None
        self.panel = None                 # diálogo de comando abierto (a la derecha, debajo del ViewCube)
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

    def set_capa_boceto(self, capa, paleta):
        self.capa, self.paleta = capa, paleta
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
        y = self.viewcube.y() + self.viewcube.height() + 10
        if self.panel is not None and self.panel.isVisible():
            self.panel.adjustSize()
            self.panel.move(g.right() - self.panel.width() - 10, y)
            self.panel.raise_()
            y += self.panel.height() + 8
        if self.paleta is not None:
            self.paleta.ajustar()
            self.paleta.move(g.right() - self.paleta.width() - 10, y)
            self.paleta.raise_()
        if self.barra is not None:
            self.barra.adjustSize()
            self.barra.move((w - self.barra.width()) // 2, h - self.barra.height() - 8)
            self.barra.raise_()
        if self.aviso.isVisible():
            self.aviso.move((w - self.aviso.width()) // 2, 12)
            self.aviso.raise_()
        if self.toast.isVisible():
            self.toast.move(g.right() - self.toast.width() - 10, g.bottom() - self.toast.height() - 10)
            self.toast.raise_()
