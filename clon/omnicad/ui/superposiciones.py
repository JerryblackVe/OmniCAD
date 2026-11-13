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
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFontMetricsF, QKeySequence, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF, QRadialGradient, QTransform)
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
TAMANOS = {"diminuto": 70, "pequeno": 90, "normal": 110, "automatico": 120, "grande": 150}
# Menú del clic derecho del ViewCube, como Fusion (ViewCube Size: Automatic, Large, Normal, Small, Tiny)
TAMANOS_TEXTO = [("automatico", "Automático"), ("grande", "Grande"), ("normal", "Normal"), ("pequeno", "Pequeño"),
                 ("diminuto", "Diminuto")]
EJES = [((1, 0, 0), QColor("#d23c3c"), "X", ((0, -1, 0), (0, 0, -1))),
        ((0, 1, 0), QColor("#3fa34d"), "Y", ((-1, 0, 0), (0, 0, -1))),
        ((0, 0, 1), QColor("#2f5fd0"), "Z", ((-1, 0, 0), (0, -1, 0)))]


LARGO_EJE = 2.12             # el eje sobresale del cubo hasta aquí (el cubo mide 2)
CIAN_CUBO = QColor("#35d0ee")       # lo que está bajo el cursor
COLOR_BOTON = QColor("#c3c8d0")      # triángulos, flechas y ▽, claros sobre el fondo oscuro del visor
COLOR_CARA, COLOR_BISEL, COLOR_VERTICE = (238, 240, 244), (216, 220, 227), (198, 203, 212)   # gris claro mate; aristas y vértices biselados
BANDAS = ((-1, -1.0, -0.74), (0, -0.74, 0.74), (1, 0.74, 1.0))   # franjas de cada cara: vértice, arista o centro
# Giros de 90° del marco de la cámara (derecha r, arriba u, atrás b): triángulos y flechas curvas de una vista de cara.
GIROS = {"der": lambda r, u, b: (-b, u, r),          # ◁ del borde derecho: la cara de la derecha pasa al frente
         "izq": lambda r, u, b: (b, u, -r),          # ▷ del borde izquierdo
         "arriba": lambda r, u, b: (r, -b, u),       # ▽ del borde de arriba: la cara de arriba pasa al frente
         "abajo": lambda r, u, b: (r, b, -u),        # △ del borde de abajo
         "antihorario": lambda r, u, b: (-u, r, b),  # flecha curva de arriba: la escena gira 90° contra el reloj
         "horario": lambda r, u, b: (u, -r, b)}      # flecha curva de la derecha: la escena gira 90° con el reloj


class ViewCube(QWidget):
    """Cubo de navegación como el de Fusion: 26 zonas (6 caras, 12 aristas, 8 vértices) que llevan a su vista; en una
    vista de cara, 4 triángulos y 2 flechas curvas que giran 90°; la casita, el menú ▽ y los ejes."""

    def __init__(self, visor, parent=None):
        super().__init__(parent)
        self.visor = visor
        self.setMouseTracking(True)
        self.setToolTip("ViewCube: clic en una cara, arista o vértice para esa vista, arrastrar para orbitar.\n"
                        "Atajos: 0 isométrica, 1 frente, 2 arriba, 3 derecha. Clic derecho o ▽: menú del ViewCube.")
        self._zonas = []              # [(QPolygonF, dirección)] de las zonas visibles de las caras, para el clic
        self._hover = None            # ("zona", dirección) | ("giro", clave) | ("casa",) | ("menu",)
        self._presionado, self._arrastrado, self._objetivo = None, False, None
        self._tamano = "automatico"
        self.al_elegir_tamano = None  # función(clave): la ventana la guarda en las preferencias
        self.al_elegir_camara = None  # función(clave): la ventana la aplica a todas las vistas
        self.al_guardar_vistas = None  # función(): la ventana guarda el Inicio y las vistas de cara en el documento
        self.menu_abierto = None
        self.set_tamano("automatico")
        visor.camara_cambiada.connect(self.update)

    def set_tamano(self, clave):
        self._tamano = clave
        lado = TAMANOS.get(clave, TAMANOS["automatico"])
        self.setFixedSize(lado, lado)

    # ------------------------------------------------------------ menú
    def menu_tamano(self):
        """Menú «Tamaño de ViewCube», con las cinco opciones de Fusion."""
        m = QMenu("Tamaño de ViewCube", self)
        grupo = QActionGroup(m)
        for clave, texto in TAMANOS_TEXTO:
            a = m.addAction(texto)
            a.setCheckable(True)
            a.setChecked(clave == self._tamano)
            a.triggered.connect(lambda _=False, c=clave: self._elegir_tamano(c))
            grupo.addAction(a)
        return m

    def menu(self):
        """Menú del ViewCube (clic derecho o ▽): ir al inicio, cámara y tamaño."""
        m = QMenu(self)
        m.addAction("Ir al inicio").triggered.connect(self._ir_al_inicio)
        sub = m.addMenu("Cámara")
        grupo = QActionGroup(sub)
        for clave, texto in (("ortografica", "Ortográfica"), ("perspectiva", "Perspectiva"),
                             ("persp_orto_caras", "Perspectiva con caras ortográficas")):
            a = sub.addAction(texto)
            a.setCheckable(True)
            a.setChecked(self.visor.config.camara == clave)
            a.triggered.connect(lambda _=False, c=clave: self._elegir_camara(c))
            grupo.addAction(a)
        self._acciones_vistas(m)
        m.addSeparator()
        m.addMenu(self.menu_tamano())
        return m

    def _acciones_vistas(self, m):
        """«Establecer la vista actual como Inicio» (ajustada o a distancia fija), «Restablecer Inicio» y, mirando una cara, las
        dos de esa cara, como el menú de Fusion."""
        m.addSeparator()
        sub = m.addMenu("Establecer la vista actual como Inicio")
        sub.addAction("Ajustar a la vista").triggered.connect(lambda: self._fijar_inicio("ajustar"))
        sub.addAction("Distancia fija").triggered.connect(lambda: self._fijar_inicio("distancia_fija"))
        reset = m.addAction("Restablecer Inicio")
        reset.triggered.connect(lambda: self._fijar_inicio(None))
        reset.setEnabled(bool(self.visor.home))
        cara = self._cara_actual()
        nombre = cara[1].capitalize() if cara else "cara"
        a = m.addAction(f"Establecer la vista actual como {nombre}")
        b = m.addAction(f"Restablecer {nombre}")
        a.setEnabled(cara is not None)
        b.setEnabled(cara is not None and cara[0] in self.visor.vistas_cara)
        if cara:
            a.triggered.connect(lambda: self._fijar_cara(cara[0], True))
            b.triggered.connect(lambda: self._fijar_cara(cara[0], False))

    def _ir_al_inicio(self):
        self.visor.animar_vista(self.visor.vista_inicio)

    def _cara_actual(self):
        """(vista, etiqueta) de la cara que mira la cámara, o None."""
        i = self._cara_alineada()
        if i is None:
            return None
        n = [0, 0, 0]
        n[i] = 1 if self.visor.R[2][i] > 0 else -1
        return next((v, t) for nn, _u, _w, t, v in CARAS if tuple(nn) == tuple(n))

    def _fijar_inicio(self, modo):
        self.visor.home = None if modo is None else self.visor.vista_actual(modo)
        self._guardar_vistas()

    def _fijar_cara(self, vista, fijar):
        if fijar:
            self.visor.vistas_cara[vista] = {"R": self.visor.R.tolist()}
        else:
            self.visor.vistas_cara.pop(vista, None)
        self._guardar_vistas()

    def _guardar_vistas(self):
        if self.al_guardar_vistas is not None:
            self.al_guardar_vistas()

    def _elegir_camara(self, clave):
        if self.al_elegir_camara is not None:
            self.al_elegir_camara(clave)
        else:
            self.visor.set_camara(clave)

    def _elegir_tamano(self, clave):
        self.set_tamano(clave)
        if self.al_elegir_tamano is not None:
            self.al_elegir_tamano(clave)

    def contextMenuEvent(self, e):
        self.menu().exec(e.globalPos())

    def abrir_menu(self):
        """El ▽ de abajo a la derecha: el mismo menú, que se abre debajo del botón."""
        self.menu_abierto = self.menu()
        self.menu_abierto.popup(self.mapToGlobal(self._rect_menu().bottomLeft().toPoint()))

    # ------------------------------------------------------------ geometría de los botones (en píxeles del widget)
    def _k(self):
        return self.width() / 120.0

    def _rect_casa(self):
        """Botón «vista inicial» arriba a la izquierda, como Fusion."""
        k = self._k()
        return QRectF(0, 0, 20 * k, 20 * k)

    def _rect_menu(self):
        k = self._k()
        return QRectF(self.width() - 20 * k, self.height() - 20 * k, 18 * k, 18 * k)

    def _rects_giro(self):
        """Cuatro triángulos (en una vista de cara) y dos flechas curvas, por clave de GIROS."""
        w, h, k = self.width(), self.height(), self._k()
        t = 9 * k
        cx, cy = w * 0.52, h * 0.5
        return {"izq": QRectF(w * 0.10 - t / 2, cy - t / 2, t, t), "der": QRectF(w * 0.94 - t / 2 - 2 * k, cy - t / 2, t, t),
                "arriba": QRectF(cx - t / 2, h * 0.09 - t / 2, t, t), "abajo": QRectF(cx - t / 2, h * 0.91 - t / 2, t, t),
                "antihorario": QRectF(w * 0.66, 2 * k, 22 * k, 16 * k), "horario": QRectF(w - 22 * k, 20 * k, 20 * k, 24 * k)}

    def _cara_alineada(self):
        """El índice del eje (0 X, 1 Y, 2 Z) de la cara que mira la cámara si mira de frente a una, o None (arista o vértice)."""
        atras = self.visor.R[2]
        i = int(np.argmax(np.abs(atras)))
        return i if abs(atras[i]) > 0.9995 else None

    # ------------------------------------------------------------ dibujo
    def _proyectar(self, rot, p, centro, escala):
        v = rot @ np.asarray(p, float)
        return QPointF(centro.x() + v[0] * escala, centro.y() - v[1] * escala), v[2]

    def _punto_cara(self, rot, n, u, w, s, t, centro, escala):
        return self._proyectar(rot, n + s * u + t * w, centro, escala)[0]

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rot = self.visor.matriz_vista()[:3, :3]
        centro = QPointF(self.width() * 0.52, self.height() * 0.48)
        escala = self.width() * 0.255
        self._zonas = []
        luz = np.array([0.35, 0.55, 0.75])
        resaltada = self._hover[1] if self._hover and self._hover[0] == "zona" else None
        brillantes = []
        self._dibujar_ejes(p, rot, centro, escala, False)
        for normal, der, arr, texto, _vista in CARAS:
            n, u, w = (np.array(x, float) for x in (normal, der, arr))
            if (rot @ n)[2] <= 1e-6:
                continue
            brillo = 0.86 + 0.14 * max(0.0, float((rot @ n) @ luz))
            esquinas = [n - u + w, n + u + w, n + u - w, n - u - w]
            poli = QPolygonF([self._proyectar(rot, c, centro, escala)[0] for c in esquinas])
            for i, s0, s1 in BANDAS:
                for j, t0, t1 in BANDAS:
                    d = tuple(int(round(c)) for c in n + i * u + j * w)
                    zona = QPolygonF([self._punto_cara(rot, n, u, w, s, t, centro, escala)
                                      for s, t in ((s0, t1), (s1, t1), (s1, t0), (s0, t0))])
                    self._zonas.append((zona, d))
                    self._pintar_zona(p, rot, n, u, w, i, j, (s0, s1), (t0, t1), zona, brillo, centro, escala)
                    if d == resaltada:
                        brillantes.append((zona, d))
            p.setPen(QPen(QColor(96, 104, 116, 190), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPolygon(poli)                                # el contorno redondeado del cubo
            self._etiqueta(p, poli, texto)
        for zona, d in brillantes:                              # el cian va encima: una línea luminosa en la arista
            self._brillo(p, rot, zona, d, centro, escala)
        self._letras_ejes(p, rot, centro, escala)
        if self._cara_alineada() is not None:
            self._dibujar_giros(p)
        self._dibujar_botones(p)
        p.end()

    @staticmethod
    def _gris(base, brillo):
        return QColor(min(255, int(base[0] * brillo)), min(255, int(base[1] * brillo)), min(255, int(base[2] * brillo)))

    def _pintar_zona(self, p, rot, n, u, w, i, j, s, t, zona, brillo, centro, escala):
        """Una zona del cubo: el centro de la cara lisa; la arista como un redondeo (el degradé se oscurece hacia el borde
        y tiene un filo claro); el vértice como una esquina redonda (degradé radial)."""
        p.setPen(Qt.NoPen)
        if i == j == 0:
            p.setBrush(self._gris(COLOR_CARA, brillo))
            p.drawPolygon(zona)
            return
        if i != 0 and j != 0:                                   # vértice
            c = zona.boundingRect().center()
            g = QRadialGradient(c, max(zona.boundingRect().width(), zona.boundingRect().height()) * 0.75)
            g.setColorAt(0.0, self._gris(COLOR_CARA, brillo * 1.02))
            g.setColorAt(1.0, self._gris(COLOR_VERTICE, brillo))
        else:                                                   # arista: de la cara hacia el borde
            adentro, afuera = (0.74 * i, 1.0 * i) if i else (0.74 * j, 1.0 * j)
            a = self._punto_cara(rot, n, u, w, adentro if i else 0, adentro if j else 0, centro, escala)
            b = self._punto_cara(rot, n, u, w, afuera if i else 0, afuera if j else 0, centro, escala)
            g = QLinearGradient(a, b)
            g.setColorAt(0.0, self._gris(COLOR_CARA, brillo))
            g.setColorAt(0.7, self._gris(COLOR_BISEL, brillo))
            g.setColorAt(1.0, self._gris(COLOR_VERTICE, brillo * 0.85))
        p.setBrush(g)
        p.drawPolygon(zona)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))            # el filo de la zona, para que se vea aparte
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(zona)

    def _brillo(self, p, rot, zona, d, centro, escala):
        """Resalta la zona bajo el cursor: una arista brilla en cian a lo largo de la arista, un vértice como un punto
        luminoso y una cara con su cuadro central marcado."""
        pesos = sum(map(abs, d))
        p.setBrush(QColor(53, 208, 238, 55))
        p.setPen(Qt.NoPen)
        p.drawPolygon(zona)
        k = self._k()
        if pesos == 2:
            e = d.index(0)
            ext = [self._proyectar(rot, [(sg if q == e else d[q]) for q in range(3)], centro, escala)[0] for sg in (-1, 1)]
            for ancho, alfa in ((7 * k, 55), (4 * k, 110), (1.8 * k, 255)):
                p.setPen(QPen(QColor(53, 208, 238, alfa), ancho, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(ext[0], ext[1])
        elif pesos == 3:
            c = self._proyectar(rot, d, centro, escala)[0]
            g = QRadialGradient(c, 8 * k)
            g.setColorAt(0.0, QColor(255, 255, 255, 255))
            g.setColorAt(0.35, QColor(53, 208, 238, 230))
            g.setColorAt(1.0, QColor(53, 208, 238, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(c, 8 * k, 8 * k)
        else:
            for ancho, alfa in ((5 * k, 60), (1.6 * k, 255)):
                p.setPen(QPen(QColor(53, 208, 238, alfa), ancho, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(zona)

    def _dibujar_ejes(self, p, rot, centro, escala, delante):
        """Los tres ejes desde la esquina (−1, −1, −1). Los que corren por una arista de atrás se dibujan antes del
        cubo (queda a la vista solo lo que sobresale, como Fusion); las letras van siempre encima, un poco hacia afuera."""
        origen = np.array([-1.0, -1.0, -1.0])
        f = temas.qfont_cotas(max(7, int(self.width() / 13)))
        f.setBold(True)
        p.setFont(f)
        for eje, color, letra, caras_vecinas in EJES:
            enfrente = any((rot @ np.array(c, float))[2] > 1e-6 for c in caras_vecinas)
            if enfrente != delante:
                continue
            a = self._proyectar(rot, origen, centro, escala)[0]
            b = self._proyectar(rot, origen + np.array(eje) * LARGO_EJE, centro, escala)[0]
            p.setPen(QPen(color, 2))
            p.drawLine(a, b)

    def _letras_ejes(self, p, rot, centro, escala):
        origen = np.array([-1.0, -1.0, -1.0])
        for eje, color, letra, vecinas in EJES:
            b = self._proyectar(rot, origen + np.array(eje) * LARGO_EJE, centro, escala)[0]
            if not any((rot @ np.array(c, float))[2] > 1e-6 for c in vecinas) and \
                    any(poli.containsPoint(b, Qt.OddEvenFill) for poli, _d in self._zonas):
                continue                      # el eje corre por detrás y su punta queda tapada por el cubo
            fuera = np.array([b.x() - centro.x(), b.y() - centro.y()])
            fuera = fuera / (np.linalg.norm(fuera) or 1.0) * 7
            p.setPen(color)
            p.drawText(QRectF(b.x() + fuera[0] - 10, b.y() + fuera[1] - 10, 20, 20), Qt.AlignCenter, letra)

    def _color_boton(self, clave):
        return CIAN_CUBO if self._hover == ("giro", clave) else COLOR_BOTON

    def _dibujar_giros(self, p):
        """Los cuatro triángulos del borde y las dos flechas curvas, llenos y cian al pasar el cursor."""
        for clave, r in self._rects_giro().items():
            color = self._color_boton(clave)
            if clave in ("horario", "antihorario"):
                p.setPen(QPen(color, 2.4, Qt.SolidLine, Qt.RoundCap))
                p.setBrush(Qt.NoBrush)
                if clave == "antihorario":              # de la derecha hacia la izquierda, por arriba
                    marco, ini, barrido, sentido = QRectF(r.adjusted(0, 0, 0, r.height())), 20, 130, QPointF(-0.5, 0.85)
                else:                                   # de arriba hacia abajo, por la derecha
                    marco, ini, barrido, sentido = QRectF(r.adjusted(-r.width(), 0, 0, 0)), 80, -140, QPointF(-0.6, 0.8)
                camino = QPainterPath()
                camino.arcMoveTo(marco, ini)
                camino.arcTo(marco, ini, barrido)
                p.drawPath(camino)
                self._cabeza(p, camino.currentPosition(), sentido, color)
                continue
            c, m = r.center(), r.width() / 2
            punta = {"izq": ((-m, -m), (-m, m), (m, 0)), "der": ((m, -m), (m, m), (-m, 0)),
                     "arriba": ((-m, -m), (m, -m), (0, m)), "abajo": ((-m, m), (m, m), (0, -m))}[clave]
            p.setPen(QPen(color, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(color)
            p.drawPolygon(QPolygonF([QPointF(c.x() + dx, c.y() + dy) for dx, dy in punta]))

    @staticmethod
    def _cabeza(p, punta, sentido, color):
        """Cabeza de flecha en `punta`, apuntando hacia `sentido`."""
        d = np.array([sentido.x(), sentido.y()], float)
        d /= np.linalg.norm(d)
        o = np.array([-d[1], d[0]])
        base = np.array([punta.x(), punta.y()]) - d * 6
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([punta] + [QPointF(*(base + o * s * 4)) for s in (1, -1)]))

    def _dibujar_botones(self, p):
        casa = self._rect_casa()
        if self._hover == ("casa",):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(53, 208, 238, 70))
            p.drawRoundedRect(casa, 3, 3)
        p.drawPixmap(casa.adjusted(2, 2, -2, -2), icono("casa").pixmap(32, 32), QRectF(0, 0, 32, 32))
        r = self._rect_menu()
        c, m = r.center(), r.width() * 0.32
        color = CIAN_CUBO if self._hover == ("menu",) else COLOR_BOTON
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(c.x() - m, c.y() - m * 0.5), QPointF(c.x() + m, c.y() - m * 0.5), QPointF(c.x(), c.y() + m * 0.9)]))

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
        p.setPen(QColor("#4a515b"))
        p.drawText(QRectF(0, 0, ancho, alto), Qt.AlignCenter, texto)
        p.restore()

    # ------------------------------------------------------------ ratón
    def _objetivo_en(self, pos):
        """Qué hay bajo `pos`: ("casa",), ("menu",), ("giro", clave) o ("zona", dirección); None si nada."""
        if self._rect_casa().contains(pos):
            return ("casa",)
        if self._rect_menu().contains(pos):
            return ("menu",)
        if self._cara_alineada() is not None:
            for clave, r in self._rects_giro().items():
                if r.adjusted(-3, -3, 3, 3).contains(pos):
                    return ("giro", clave)
        for poli, d in self._zonas:
            if poli.containsPoint(pos, Qt.OddEvenFill):
                return ("zona", d)
        return None

    def mouseMoveEvent(self, e):
        if self._presionado is not None and e.buttons() & Qt.LeftButton:
            d = e.position() - self._presionado
            if d.manhattanLength() > 3:
                self.visor.orbitar(d.x(), d.y())
                self._presionado = e.position()
                self._arrastrado = True
            return
        objetivo = self._objetivo_en(e.position())
        if objetivo != self._hover:
            self._hover = objetivo
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._presionado, self._arrastrado = e.position(), False

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._presionado is None:
            return
        arrastrado, self._presionado = self._arrastrado, None
        if not arrastrado:
            self._activar(self._objetivo_en(e.position()))

    def _activar(self, objetivo):
        if objetivo is None:
            return
        if objetivo == ("casa",):
            self._ir_al_inicio()
        elif objetivo == ("menu",):
            self.abrir_menu()
        elif objetivo[0] == "giro":
            r, u, b = self.visor.R
            nueva = GIROS[objetivo[1]](r, u, b)
            self.visor.animar_vista(lambda: self.visor.poner_rotacion(nueva))
        else:
            d = objetivo[1]
            if sum(map(abs, d)) == 1:                      # una cara: su vista estándar
                vista = next(v for n, _a, _b, _t, v in CARAS if tuple(n) == d)
                self.visor.animar_vista(lambda: self.visor.vista(vista))
            else:                                          # una arista (45°) o un vértice (isométrica)
                self.visor.animar_vista(lambda: self.visor.vista_direccion(d))

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
        self._reacomodo = False
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
        for w in self.laterales:
            w.installEventFilter(self)
        self.reubicar()

    def eventFilter(self, obj, e):
        """B-387: un panel lateral que cambia de alto (otra casilla le suma filas) se vuelve a acomodar: si no, su pie
        quedaba bajo la barra de vista. Un solo reacomodo por tanda de cambios."""
        if e.type() == QEvent.Resize and obj in self.laterales and obj.isVisible() and not self._reacomodo:
            self._reacomodo = True
            QTimer.singleShot(0, self._reacomodar)
        return False

    def _reacomodar(self):
        try:
            self.reubicar()                 # sus propios cambios de tamaño no vuelven a disparar el reacomodo
        finally:
            self._reacomodo = False

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
        elif self.panel is not None and self.panel.isVisible() and self.paleta is None:
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
            if fija is None and self.panel is not None and self.panel.isVisible():
                # B-342: con el boceto abierto el panel de un comando va a la izquierda de la paleta, como las tarjetas
                # (en columna la paleta, que es alta, lo tapaba junto con su Aceptar).
                if hasattr(self.panel, "ajustar_alto"):
                    self.panel.ajustar_alto(abajo - g.top() - 4)
                self.panel.move(max(g.left() + 4, self.paleta.x() - self.panel.width() - 8),
                                max(g.top() + 4, min(y, abajo - self.panel.height())))
                self.panel.raise_()
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
