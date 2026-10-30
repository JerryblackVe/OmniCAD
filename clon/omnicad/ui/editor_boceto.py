# -*- coding: utf-8 -*-
"""
Entorno de boceto, como el de Fusion 360 (ver docs/investigacion_boceto_fusion.md).

Se dibuja DIRECTAMENTE sobre el plano, en la vista 3D: el Lienzo es una capa transparente encima
del visor que proyecta el boceto con la cámara del visor, así que se puede orbitar, desplazar y
hacer zoom mientras se dibuja (botón del medio, Mayús + medio, rueda; el izquierdo dibuja).
Sin visor, el Lienzo trabaja en 2D (lo usan las pruebas).

Comportamiento tomado de la ayuda de Fusion (libro "Design: Sketch", SKT-*):
  - Línea: clic, clic… encadena segmentos; arrastrar desde el último punto crea un arco tangente;
    escribir un número abre la entrada de longitud (Tab pasa al ángulo) y crea la cota; Esc corta.
  - CREAR: rectángulos, círculos (centro, 2 y 3 puntos, 2 y 3 tangentes), arcos, polígonos, elipse,
    ranuras (5 tipos), splines de ajuste y de puntos de control, cónica, punto, texto, espiral,
    simetría, patrones rectangular y circular, Proyectar / Intersecar / Incluir geometría 3D.
  - MODIFICAR: empalme, chaflanes, curva de fusión (G1/G2), desfase (O), recortar (T), alargar,
    partir, escala, mover/copiar (M).
  - Al enganchar un punto existente se comparte (coincidencia) y, si un segmento queda casi a 0° o
    90°, se agrega horizontal o vertical automáticamente (restricciones inferidas).
  - Cota de boceto (D): clic en la geometría, clic para ubicar, se escribe el valor o una expresión
    con parámetros y Enter. Doble clic en una cota la edita (y en un texto, edita el texto); el clic
    derecho suma «Editar valor» y «Renombrar parámetro», y al pasar el mouse muestra «nombre : valor».
  - Restricciones: se elige la herramienta y se hace clic en la geometría (o se preselecciona).
  - Herramientas que trabajan sobre una selección (simetría, patrones, escala, mover): se usa lo
    preseleccionado o se eligen las curvas con clics y Enter para seguir.
  - Colores: azul = libre, blanco/negro = totalmente restringido, verde = fijo, naranja punteado =
    construcción, violeta = proyectada; los ejes (líneas centrales) van con trazo y punto. X alterna
    normal/construcción. Supr borra. Ctrl+Z deshace dentro del boceto.
"""
import copy
import math
import re
import threading
import time
import warnings

import numpy as np

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFontMetricsF, QKeySequence, QMouseEvent, QPainter, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
                               QMessageBox, QToolTip, QWidget)

from ..restricciones import Boceto, ErrorBoceto, TIPOS_COTA, TIPOS_RESTRICCION, auto_restringir, resolver
from ..restricciones.solver import restricciones_en_conflicto
from ..restricciones.inferencia import Inferencia, inferir
from ..restricciones.boceto import (Arco, Circulo, Conica, Cota, Linea, Spline, Texto, agregar_linea_medio, agregar_rectangulo_3p,
                                    agregar_rectangulo_centro, cambiar_radio, centro_arco_tangente,
                                    circunferencia_3_puntos, dominio,
                                    evaluar_primitiva, fraccion_en_camino, mas_cercano, paradas_cursor,
                                    primitivas_entidad, puntos_espiral, puntos_primitiva, validar_valor_cota,
                                    _validar_opciones_texto)
from ..timeline.parametros import (ANGULO, ESCALAR, LONGITUD, ErrorExpresion, nombres_usados, separar_nombre,
                                   validar_nombre)
from . import formato, temas
from .iconos import icono

HERRAMIENTAS = {
    "seleccionar": ("Seleccionar", "Clic: seleccionar (Ctrl o Mayús suman); doble clic: toda la cadena unida. "
                    "Arrastrá un punto, una línea, un círculo o un arco para moverlo (lo restringido no se mueve); "
                    "arrastrá en vacío para seleccionar con ventana. Supr borra, X alterna construcción."),
    "linea": ("Línea", "Clic, clic… encadena segmentos. Arrastrá desde el último punto para un arco tangente. "
              "Escribí un número para la longitud (Tab: ángulo). Esc termina."),
    "linea_medio": ("Línea de punto medio", "Clic en el punto medio y clic en un extremo."),
    "rectangulo": ("Rectángulo de 2 puntos", "Clic en una esquina y clic en la opuesta (o escribí ancho, Tab, alto)."),
    "rectangulo_3p": ("Rectángulo de 3 puntos", "Clic, clic para el primer lado y clic para el ancho."),
    "rectangulo_centro": ("Rectángulo central", "Clic en el centro y clic en una esquina."),
    "circulo": ("Círculo de centro y diámetro", "Clic en el centro y clic para el tamaño (o escribí el diámetro)."),
    "circulo_2p": ("Círculo de 2 puntos", "Clic en los dos extremos de un diámetro."),
    "circulo_3p": ("Círculo de 3 puntos", "Tres clics sobre la circunferencia."),
    "circulo_2t": ("Círculo de 2 tangentes", "Clic en dos líneas y clic para ubicar el círculo (o escribí el radio)."),
    "circulo_3t": ("Círculo de 3 tangentes", "Clic en tres líneas."),
    "arco": ("Arco de 3 puntos", "Clic en el inicio, clic en el final y clic para la curvatura."),
    "arco_centro": ("Arco de punto central", "Clic en el centro, clic en el inicio (radio) y clic en el final."),
    "arco_tangente": ("Arco tangente", "Clic en el extremo de una curva y clic en el final del arco."),
    "poligono_circunscrito": ("Polígono circunscrito", "Clic en el centro y clic para el tamaño y la "
                              "orientación (o escribí el radio, Tab, la cantidad de lados)."),
    "poligono_inscrito": ("Polígono inscrito", "Clic en el centro y clic en un vértice (o escribí el radio, "
                          "Tab, la cantidad de lados)."),
    "poligono_arista": ("Polígono de aristas", "Clic, clic para una arista y clic del lado donde va el polígono."),
    "elipse": ("Elipse", "Clic en el centro, clic en el extremo del eje mayor y clic en un punto de la elipse."),
    "ranura_centro": ("Ranura de centro a centro", "Clic en el centro de un extremo, clic en el del otro y clic "
                      "para el ancho."),
    "ranura_total": ("Ranura total", "Clic en un extremo, clic en el otro y clic para el ancho."),
    "ranura_punto": ("Ranura de punto central", "Clic en el centro de la ranura, clic en el centro de un extremo "
                     "y clic para el ancho."),
    "ranura_arco_3p": ("Ranura de arco de tres puntos", "Clic en el centro de un extremo, clic en el del otro, "
                       "clic en un punto del arco y clic para el ancho."),
    "ranura_arco_centro": ("Ranura de arco de punto central", "Clic en el centro del arco, clic en el centro de "
                           "un extremo, clic en el del otro y clic para el ancho."),
    "spline_ajuste": ("Spline de ajuste de puntos", "Clic, clic… por donde pasa la curva. Enter o doble clic "
                      "termina; clic en el primer punto la cierra."),
    "spline_control": ("Spline de puntos de control", "Clic, clic… en los puntos de control. Enter o doble clic "
                       "termina."),
    "conica": ("Curva cónica", "Clic en los extremos y en el vértice; mové el ratón para ajustar Rho o escribilo. "
                              "Clic o Enter confirma."),
    "punto": ("Punto", "Clic para ubicar puntos."),
    "texto": ("Texto", "Clic en una esquina y clic en la opuesta: el cuadro fija la altura y el ancho del texto; "
                       "escribí y mirá los cambios en vivo, Enter acepta (fuente y estilo en la paleta)."),
    "espiral": ("Espiral", "Clic en el centro y clic en el inicio; escribí las vueltas y el paso y Enter."),
    "simetria": ("Simetría", "Seleccioná la geometría, Enter y clic en la línea de simetría."),
    "patron_rectangular": ("Patrón rectangular", "Seleccioná la geometría y Enter; escribí cantidad y distancia "
                           "en cada dirección (X e Y del boceto)."),
    "patron_circular": ("Patrón circular", "Seleccioná la geometría, Enter y clic en el centro; escribí la "
                        "cantidad y el ángulo total."),
    "proyectar": ("Proyectar", "Clic en aristas, caras, vértices o cuerpos del modelo: se proyectan sobre el "
                  "plano del boceto (violeta, fijos). Esc termina."),
    "intersecar": ("Intersecar", "Clic en caras, aristas o cuerpos: se agregan las curvas donde cortan el plano "
                   "del boceto."),
    "incluir_3d": ("Incluir geometría 3D", "Clic en aristas o vértices del modelo para incluirlos en el boceto "
                   "(el boceto es plano: se llevan al plano)."),
    "proyectar_eje": ("Proyectar eje", "Proyecta el eje del perfil giratorio elegido en la paleta sobre el plano "
                      "del boceto, con el vínculo de proyección elegido."),
    "perfil_giratorio": ("Perfil giratorio", "Clic en aristas, caras o cuerpos del modelo: se giran alrededor del "
                         "eje de la paleta y su perfil queda en el boceto. Con eje «Arista», el primer clic elige "
                         "una arista recta como eje."),
    "cota": ("Cota de boceto", "Clic en una línea, círculo o arco (o en dos entidades) y clic para ubicar; "
             "escribí el valor o una expresión y Enter. Mayús + doble clic en una cota: de referencia ↔ driving."),
    "empalme": ("Empalme", "Clic en dos curvas cerca de la esquina; escribí el radio y Enter."),
    "chaflan": ("Chaflán de distancias iguales", "Clic en dos líneas; escribí la distancia y Enter."),
    "chaflan_dist_angulo": ("Chaflán de distancia y ángulo", "Clic en dos líneas; escribí la distancia y el ángulo."),
    "chaflan_dos_dist": ("Chaflán de dos distancias", "Clic en dos líneas; escribí las dos distancias."),
    "curva_fusion": ("Curva de fusión", "Clic cerca del extremo de una curva y cerca del extremo de otra "
                     "(G1 o G2 en la paleta)."),
    "desfase": ("Desfase", "Clic en una curva (se toma la cadena conectada), llevá el ratón al lado del desfase, "
                "escribí la distancia y Enter."),
    "recortar": ("Recortar", "Clic en el tramo a quitar (hasta las intersecciones más cercanas)."),
    "alargar": ("Alargar", "Clic cerca del extremo de una línea o un arco para llevarlo a la próxima intersección."),
    "partir": ("Partir", "Clic en una curva para partirla en las intersecciones más cercanas."),
    "escala": ("Escala del boceto", "Seleccioná la geometría, Enter y clic en el punto base; escribí el factor y Enter."),
    "mover": ("Mover/copiar", "Seleccioná la geometría, Enter, clic en el punto base y clic en el destino "
              "(o escribí ΔX, ΔY y el ángulo). «Copiar» en la paleta."),
    "desglosar_texto": ("Desglosar texto", "Clic en un texto para convertirlo en curvas fijas."),
}
# herramienta de restricción → (tipo, cantidad de entidades que pide)
RESTRICCIONES_HERRAMIENTA = {
    "r_horizontal_vertical": ("horizontal_vertical", 1), "r_coincidente": ("coincidente", 2),
    "r_tangente": ("tangente", 2), "r_igual": ("igual", 2), "r_paralela": ("paralela", 2),
    "r_perpendicular": ("perpendicular", 2), "r_fijo": ("fijo", 1), "r_punto_medio": ("punto_medio", 2),
    "r_concentrica": ("concentrica", 2), "r_colineal": ("colineal", 2), "r_simetria": ("simetrica", 3),
    "r_curvatura": ("curvatura", 2), "r_poligono": ("poligono", 1),
}
NOMBRES_RESTRICCION = {"r_horizontal_vertical": "Horizontal/Vertical", "r_coincidente": "Coincidente",
                       "r_tangente": "Tangente", "r_igual": "Igual", "r_paralela": "Paralelo",
                       "r_perpendicular": "Perpendicular", "r_fijo": "Fijar/anular fijación",
                       "r_punto_medio": "Punto medio", "r_concentrica": "Concéntrica", "r_colineal": "Colineal",
                       "r_simetria": "Simetría", "r_curvatura": "Curvatura", "r_poligono": "Polígono"}
ICONO_RESTRICCION = {"horizontal": "r_horizontal_vertical", "vertical": "r_horizontal_vertical",
                     "coincidente": "r_coincidente", "paralela": "r_paralela", "perpendicular": "r_perpendicular",
                     "igual": "r_igual", "tangente": "r_tangente", "concentrica": "r_concentrica",
                     "punto_medio": "r_punto_medio", "fijo": "r_fijo", "colineal": "r_colineal",
                     "simetrica": "r_simetria", "curvatura": "r_curvatura", "poligono": "r_poligono",
                     "desfase": "desfase", "patron": "patron_rectangular"}
NOMBRES_ENTIDAD = {"punto": "punto", "linea": "línea", "circulo": "círculo", "arco": "arco", "elipse": "elipse",
                   "arco_elipse": "arco de elipse", "spline": "spline", "conica": "cónica", "texto": "texto"}
# Herramientas que piden curvas (clic sobre la geometría): cuántas y de qué tipos.
PICKS = {"circulo_2t": (2, ("linea",)), "circulo_3t": (3, ("linea",)), "empalme": (2, None),
         "chaflan": (2, ("linea",)), "chaflan_dist_angulo": (2, ("linea",)), "chaflan_dos_dist": (2, ("linea",)),
         "curva_fusion": (2, None), "desfase": (1, None), "recortar": (1, None), "alargar": (1, None),
         "partir": (1, None), "desglosar_texto": (1, ("texto",))}
SELECCION = ("simetria", "patron_rectangular", "patron_circular", "escala", "mover")
SPLINES = ("spline_ajuste", "spline_control")
PROYECCION = ("proyectar", "intersecar", "incluir_3d", "perfil_giratorio")
CURVA_TEXTO = ("camino_lado", "camino_desfase", "camino_ajustar")      # opciones del texto sobre una curva
MODIFICAN = tuple(PICKS) + SELECCION + PROYECCION       # no aplican el tipo de línea a lo que crean
PORTAPAPELES = {}         # Ctrl+C / Ctrl+V entre bocetos: {"boceto": copia del origen, "ids": [...]}
VIOLETA = QColor(170, 90, 230)
TOL_PX = 8.0
TOL_PUNTO = 11.0          # radio (px) para agarrar un punto: más grande que lo que se ve
TOL_MANIJA = 12.0         # radio (px) de las manijas del marco de control
RADIO_INTERIOR_PX = 80.0  # círculos de hasta este radio en pantalla se agarran también desde adentro
TOL_INFERENCIA = math.radians(3.0)
# Cotas en vivo mientras se dibuja (las cajas de valor de Fusion): herramientas que las muestran.
RANURAS_RECTAS = ("ranura_centro", "ranura_total", "ranura_punto")
VIVAS = ("linea", "rectangulo", "rectangulo_3p", "rectangulo_centro", "circulo", "arco", "arco_centro",
         "poligono_inscrito", "poligono_circunscrito", "circulo_2p", "linea_medio", "elipse", "arco_tangente",
         "poligono_arista") + RANURAS_RECTAS + ("ranura_arco_3p", "ranura_arco_centro")
ANGULARES = ("angulo", "barrido")
# Colores de Fusion: cotas verde oliva sobre el fondo oscuro (#2d323f); gris oscuro sobre fondo claro.
COTA_OSCURO, COTA_CLARO = QColor(0xa9, 0xc4, 0x6c), QColor(70, 72, 78)
REFERENCIA = QColor(140, 140, 146)        # cota de referencia (driven): gris medio, legible en los dos temas
AZUL_CAJA = QColor(0, 120, 215)
FONDO_LIENZO = QColor(250, 250, 252)      # lienzo 2D (sin visor)
TOPE_DIAGNOSTICO_S = 3.0                 # B-111: el diagnóstico de qué choca (un resolver por vínculo) se abandona a los 3 s
CONFLICTO = QColor(225, 45, 45)           # BOC-7: restricciones, cotas y geometría en choque, en rojo como Fusion
# Ventana de selección: de izquierda a derecha (adentro) y de derecha a izquierda (lo que toca).
VENTANA_RELLENO, VENTANA_BORDE = QColor(237, 120, 0, 70), QColor(140, 150, 180)
VENTANA_CRUCE = QColor(193, 191, 0, 70)
AVISO_BORRADAS = "Las restricciones o las cotas se han eliminado durante la operación."


def _tipo_valor(tipo_cota):
    return ANGULO if tipo_cota == "angulo" else LONGITUD


def _unitario(dx, dy):
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-12 else (1.0, 0.0)


def _distancia_a_raya(q, a, b):
    """Distancia (px) del punto `q` al segmento a–b."""
    dx, dy = b.x() - a.x(), b.y() - a.y()
    largo2 = dx * dx + dy * dy
    t = 0.0 if largo2 < 1e-12 else max(0.0, min(1.0, ((q.x() - a.x()) * dx + (q.y() - a.y()) * dy) / largo2))
    return math.hypot(q.x() - (a.x() + t * dx), q.y() - (a.y() + t * dy))


def _rotar(v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def _tenido(pm, color):
    """El mismo dibujo pintado de un solo color (los glifos claros del tema oscuro)."""
    salida = QPixmap(pm.size())
    salida.setDevicePixelRatio(pm.devicePixelRatio())
    salida.fill(Qt.transparent)
    q = QPainter(salida)
    q.drawPixmap(0, 0, pm)
    q.setCompositionMode(QPainter.CompositionMode_SourceIn)
    q.fillRect(salida.rect(), color)
    q.end()
    return salida


def _es_numero(texto):
    try:
        float(str(texto).replace(",", "."))
    except ValueError:
        return False
    return True


def texto_valor(valor, angular=False, entero=False):
    """Valor de una caja de la entrada dinámica, como Fusion: "74.407 mm", "45.0 deg", "6"."""
    if entero:
        return str(int(round(valor)))
    config = getattr(formato, "_config", {})
    decimales = config.get("angular" if angular else "lineal", 1 if angular else 3)
    return f"{valor:.{decimales}f} {'deg' if angular else 'mm'}"


def _vertices_poligono(centro, vertice, lados, tipo):
    """(radio del círculo de construcción, vértices) de un polígono inscrito o circunscrito."""
    cx, cy = centro
    r = math.dist(centro, vertice)
    a0 = math.atan2(vertice[1] - cy, vertice[0] - cx)
    if tipo == "circunscrito":       # el cursor marca el punto medio de una arista
        rv, a0 = r / math.cos(math.pi / lados), a0 - math.pi / lados
    else:
        rv = r
    return r, [(cx + rv * math.cos(a0 + 2 * math.pi * k / lados), cy + rv * math.sin(a0 + 2 * math.pi * k / lados))
               for k in range(lados)]


def _segmento_en_rect(rect, a, b):
    """¿El segmento ab (px) toca el rectángulo? (recorte de Liang-Barsky)."""
    t0, t1 = 0.0, 1.0
    dx, dy = b.x() - a.x(), b.y() - a.y()
    for p, q in ((-dx, a.x() - rect.left()), (dx, rect.right() - a.x()),
                 (-dy, a.y() - rect.top()), (dy, rect.bottom() - a.y())):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


class CampoVivo:
    """Una caja de valor de la entrada dinámica (lo que mide la geometría que se está dibujando).
    `cota` describe la línea de cota provisional en mm: ("lineal", a, b, lado) —`lado`: punto del lado
    del que se aleja—, ("angular", centro, t0, t1, con_referencia), ("radial", desde, hasta) o None."""
    __slots__ = ("clave", "valor", "cota", "angular", "entero")

    def __init__(self, clave, valor, cota, angular=False, entero=False):
        self.clave, self.valor, self.cota, self.angular, self.entero = clave, valor, cota, angular, entero

    def __repr__(self):
        return f"CampoVivo({self.clave}={texto_valor(self.valor, self.angular, self.entero)})"


def _dist_px(p, a, b):
    """Distancia (px) de p al segmento ab (QPointF)."""
    dx, dy = b.x() - a.x(), b.y() - a.y()
    L2 = dx * dx + dy * dy or 1e-18
    t = max(0.0, min(1.0, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / L2))
    return math.hypot(p.x() - a.x() - t * dx, p.y() - a.y() - t * dy)


def _barrido(a0, a1):
    return (a1 - a0) % (2 * math.pi) or 2 * math.pi


def _numero(texto):
    return float(str(texto).replace(",", "."))


_CACHE_MUESTRAS = {}


def _muestras(prim, pasos):
    """`puntos_primitiva` con caché: la primitiva (tupla de números) es la clave, así un cambio la invalida."""
    clave = (prim, pasos)
    try:
        r = _CACHE_MUESTRAS.get(clave)
    except TypeError:                         # alguna primitiva con listas: sin caché
        return puntos_primitiva(prim, pasos)
    if r is None:
        if len(_CACHE_MUESTRAS) > 50000:
            _CACHE_MUESTRAS.clear()
        r = _CACHE_MUESTRAS[clave] = tuple(puntos_primitiva(prim, pasos))
    return r


def _inicio_palabra(texto, i):
    """Dónde empieza la palabra a la izquierda de `i` (Ctrl+← y Ctrl+Retroceso)."""
    while i > 0 and not texto[i - 1].isalnum():
        i -= 1
    while i > 0 and texto[i - 1].isalnum():
        i -= 1
    return i


def _fin_palabra(texto, i):
    """Dónde termina la palabra a la derecha de `i` (Ctrl+→ y Ctrl+Supr)."""
    n = len(texto)
    while i < n and not texto[i].isalnum():
        i += 1
    while i < n and texto[i].isalnum():
        i += 1
    return i


def _palabra_en(texto, i):
    """(inicio, fin) de la palabra que toca la posición `i` (doble clic); (i, i) si ahí no hay palabra."""
    n = len(texto)
    i = min(max(i, 0), n)
    ref = i if i < n and texto[i].isalnum() else i - 1
    if ref < 0 or ref >= n or not texto[ref].isalnum():
        return i, i
    a, b = ref, ref + 1
    while a > 0 and texto[a - 1].isalnum():
        a -= 1
    while b < n and texto[b].isalnum():
        b += 1
    return a, b


class EntradaValor(QFrame):
    """Entrada en pantalla (1 o más campos) para cotas y valores dinámicos; Tab cambia de campo."""
    aceptado = Signal(list)
    cancelado = Signal()
    tabulado = Signal(str, int)        # con `tab_externo`: Tab / Mayús+Tab con un solo campo (texto, +1 / -1)

    def __init__(self, etiquetas, textos, parent):
        super().__init__(parent)
        self.tab_externo = False
        self._arrastre = None
        self._movible = False
        self.setObjectName("entrada_valor")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 2, 3, 2)
        lay.setSpacing(4)
        self.campos = []
        for etiqueta, texto in zip(etiquetas, textos, strict=True):
            if etiqueta:
                lay.addWidget(QLabel(etiqueta))
            c = QLineEdit(texto)
            c.installEventFilter(self)
            lay.addWidget(c)
            self.campos.append(c)
        self.adjustSize()

    def hacer_movible(self):
        """La barra se arrastra con el ratón desde cualquier parte que no sea un campo (agarre ⋮⋮ a la izquierda)."""
        self._movible = True
        agarre = QLabel("⋮⋮")
        agarre.setToolTip("Arrastrá para mover la barra")
        agarre.setCursor(Qt.SizeAllCursor)
        self.layout().insertWidget(0, agarre)
        self.setCursor(Qt.SizeAllCursor)
        self.layout().activate()
        self.adjustSize()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.position().toPoint()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            nueva = self.pos() + e.position().toPoint() - self._arrastre
            padre = self.parentWidget()
            if padre is not None:
                nueva.setX(max(0, min(nueva.x(), padre.width() - self.width())))
                nueva.setY(max(0, min(nueva.y(), padre.height() - self.height())))
            self.move(nueva)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._arrastre = None
        super().mouseReleaseEvent(e)

    def ocultar_primero(self):
        """El primer campo (el texto) se escribe directamente en el cuadro del lienzo, no en la barra."""
        lay = self.layout()
        desde = 1 if self._movible else 0
        for i in range(desde, desde + 2):
            w = lay.itemAt(i).widget()
            if w is not None:
                w.hide()
        self.layout().activate()
        self.adjustSize()

    def abrir(self, pos):
        self.move(int(pos.x()) + 14, int(pos.y()) + 10)
        self.show()
        self.raise_()
        self.campos[0].setFocus()
        self.campos[0].selectAll()

    def eventFilter(self, obj, e):
        if e.type() == e.Type.KeyPress:
            if e.key() in (Qt.Key_Tab, Qt.Key_Backtab) and self.tab_externo:
                self.tabulado.emit(obj.text().strip(), 1 if e.key() == Qt.Key_Tab else -1)
                return True
            visibles = [c for c in self.campos if not c.isHidden()]
            if e.key() in (Qt.Key_Tab, Qt.Key_Backtab) and len(visibles) > 1:
                i = visibles.index(obj)
                siguiente = visibles[(i + (1 if e.key() == Qt.Key_Tab else -1)) % len(visibles)]
                siguiente.setFocus()
                siguiente.selectAll()
                return True
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.aceptado.emit([c.text().strip() for c in self.campos])
                return True
            if e.key() == Qt.Key_Escape:
                self.cancelado.emit()
                return True
        return super().eventFilter(obj, e)

    def marcar_error(self, i=0):
        self.campos[i].setStyleSheet(f"background: {temas.color('campo_error')};")


class Lienzo(QWidget):
    cambio = Signal()
    mensaje = Signal(str)
    herramienta_cambiada = Signal(str)
    texto_en_edicion = Signal()     # se edita un texto ya creado: la paleta muestra sus opciones (fuente, estilo…)
    texto_valores = Signal(float, float, float, float)   # altura, interletraje, interlineado y kerning en el cursor
    info = Signal(str)          # medidas de lo elegido, como Fusion ("1 línea de boceto | Longitud: …")
    aviso = Signal(str)         # aviso flotante (p. ej. una operación borró restricciones o cotas)

    def __init__(self, boceto, evaluar, parent=None, visor=None, plano=None):
        super().__init__(parent)
        self.b = boceto
        self._evaluar_doc = evaluar
        self._nombradas = {}             # nombre dN → id de las cotas que se nombraron al citarlas (BOC-35)
        self.visor, self.plano = visor, plano
        self.herramienta = "seleccionar"
        self.ultima_herramienta = None
        self.construccion = False
        self.eje = False                           # tipo de línea "línea central" para lo nuevo
        self.ajustar_grilla = visor is None          # en la vista 3D, "Forzar" arranca apagado (Fusion)
        self.mostrar = {"puntos": True, "cotas": True, "restricciones": True, "construccion": True, "rejilla": True,
                        "proyectadas": True}
        self.opcion_cota = "auto"
        self.lados = 6
        # Opciones de la paleta (Opciones de función de Fusion) para las herramientas nuevas.
        self.opciones = {"grado_spline": 3, "continuidad": "G1", "patron_distancia": "extension",
                         "filtro_proyectar": "entidades", "copiar": False, "fuente": "Arial",
                         "direccion_desfase": "un", "match_topology": False,
                         "vinculo_proyeccion": True, "eje_giro": "Z", "contorno_exterior": True, "proyectar_eje": False,
                         "tolerancia_giro": 0.1, "invertir_giro": False,
                         "pivote_texto": None, "marco_texto": False, "parametro_texto": None,
                         "valor_parametro_texto": "",
                         "negrita": False, "cursiva": False,
                         "alineacion": "izq", "ancla_v": "base", "camino_lado": "izq",
                         "camino_desfase": 0.0, "camino_ajustar": False,
                         "altura_texto": 5.0, "espaciado": 0.0, "interlineado": 1.0,
                         "voltear_h": False, "voltear_v": False,
                         **{k: Texto._PREDETERMINADOS[k] for k in Texto.TIPOGRAFIA}}
        self.perdidas = []                         # ids de proyecciones perdidas en el último cálculo (los pone el modo)
        self._revincular = None                    # proyección perdida que se re-vincula con el próximo clic
        self._brillantes = None                    # ids que se ven normales con «Atenuar el resto» (None: todo normal)
        self._eje_giro = None                      # (eje, referencia) de la arista elegida para el perfil giratorio
        self.estado_referencias = lambda: None     # el modo consulta el estado actual del documento
        self._sel_texto = []                       # cuadriláteros de lo seleccionado en el texto que se escribe
        self._arrastre_texto = False               # se está seleccionando texto arrastrando el ratón
        self._paleta_texto = False                 # la paleta muestra las opciones del texto que se edita
        self._previa_texto = None                  # texto en vivo mientras se escribe en la caja (como Fusion)
        self._previa_polis = []                    # contornos de esa vista previa (coordenadas del boceto)
        self._texto_oculto = None                  # texto existente en edición: en su lugar se dibuja la previa
        self.editar_parametro_texto = None         # el modo usa set_parameter sobre el documento
        self.valores_parametros = lambda: {}
        self._caret = None                         # segmento del cursor de escritura, en coordenadas del boceto
        self._caret_on = True
        self._t_caret = QTimer(self)
        self._t_caret.setInterval(530)
        self._t_caret.timeout.connect(self._parpadeo)
        self.escala = 4.0
        self.centro = [0.0, 0.0]
        self.seleccion = []
        self.mostrar_marco = True       # marco de control (Fusion: «Mostrar el marco de control») sobre lo elegido
        self._marco = None              # arrastre en curso de una manija del marco
        self.clics = []
        self.picks = []
        self.picks_xy = []
        self.fase = None             # en herramientas de varios pasos: seleccion | eje | base | destino | centro
        self.cursor = None
        self.inferencia = None
        self.inf_actual = None
        self._inf_inicio = None
        self._inf_lado = None
        self._inf_clics = []             # BOC-9: (xy, tipo, objetivo) de cada clic, para las herramientas que no son Línea
        self._eligiendo_punto = None     # BOC-5: {"lazo", "pid"} mientras se elige el datum en el lienzo
        self.perfiles_sel = []           # BOC-23: índices de los perfiles elegidos con un clic (orden de `detectar`)
        self._modificadores_raton = Qt.NoModifier
        self.historial = []
        self.pila_rehacer = []
        self.resultado = None
        self._conflictos = []            # BOC-7: ids de restricciones/cotas en choque (se pintan en rojo)
        self._generacion = 0             # B-111: cuenta los cambios del boceto; un diagnóstico de otra generación se descarta
        self._diagnostico_agotado = False   # el diagnóstico pasó TOPE_DIAGNOSTICO_S sin terminar
        self._diagnostico = None         # (generación, caja) del diagnóstico de conflictos que corre en otro hilo
        self._mostrar_conflictos_al_llegar = False
        self._t_diagnostico = QTimer(self)
        self._t_diagnostico.setSingleShot(True)
        self._t_diagnostico.timeout.connect(self._sondear_conflictos)
        self.previa_auto = []
        self.entrada = None
        self._asas = None                          # asas de arrastre de la herramienta (ui/asas_boceto.py)
        self._mvp = None
        self._sobre = None               # entidad bajo el ratón en Seleccionar (se resalta y cambia el cursor)
        self._manija_sobre = None        # manija del marco bajo el ratón
        self._zona_sobre = None          # cota o símbolo de restricción bajo el ratón
        self._arrastre, self._movio = None, False
        self._desliz = None              # (fracción al agarrar, posición del texto, camino cerrado)
        self._presion = None
        self._tangente = None            # (punto de partida, línea) mientras se arrastra un arco tangente
        self._ventana = None
        self._pan = None
        self._reenvio = None
        self._ultima_linea = None
        self._zonas_cotas, self._zonas_glifos, self._trazos_cotas = {}, {}, {}
        self._fondos_cotas = {}          # cota → caja del fondo de su texto (para las pruebas y el repintado)
        self._esperando_ubicacion = False
        self._pos_cursor = QPointF(0, 0)
        self._presion_inferencia = None
        self._presion_inf_actual = None
        self._cache_cortes = {}
        self._previa_recorte = None
        self._base = (0.0, 0.0)          # punto base de Mover/copiar
        # Cotas en vivo: lo escrito queda bloqueado (clave → (texto, valor)) hasta crear la geometría.
        self._bloqueos = {}
        self._activo = 0                 # caja activa (Tab pasa a la siguiente)
        self._editando = None            # clave de la caja que se está escribiendo
        self._post_crear = None          # agrega las cotas de lo escrito dentro del mismo paso de deshacer
        self._sentido_vivo = None        # arco de punto central con el barrido escrito: antihorario o no
        self._cajas_vivas = []           # [(clave, QRectF)] dibujadas
        self._ultimo = None              # arrastre de curvas: última posición del ratón (mm)
        self._info = None                # último texto de medidas emitido
        self._cota_editada = None
        self._cota_previa = None         # Cota provisional (id -1) mientras se escribe su valor
        self._cota_abierta = None        # (tipo, entidades, pos) de la cota nueva cuya caja está abierta
        self._opc_cota = {}              # opciones del menú antes de ubicar: referencia, tipo, modo (BOC-34)
        self._evaluando = set()          # nombres en evaluación: corta las referencias circulares
        self._cita_sobre = None          # cota bajo el ratón: se cita con una caja abierta o muestra su cartel
        self._texto_inicial = None       # valor con el que se abrió la caja de valor
        self._derecho = None             # (pos px, pos global) del clic derecho apretado en una herramienta
        self._t_derecho = QTimer(self)   # clic derecho mantenido con una cota a medias: menú de opciones (BOC-34)
        self._t_derecho.setSingleShot(True)
        self._t_derecho.timeout.connect(self._opciones_cota_mantenido)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        if visor is None:
            self.setMinimumSize(520, 420)
        else:
            self.setAttribute(Qt.WA_TranslucentBackground)
            visor.camara_cambiada.connect(self.update)
        self.resolver()

    # ------------------------------------------------------------ coordenadas (2D o proyectadas por el visor)
    def _camara(self):
        if self.visor is not None:
            self._mvp = self.visor.matriz_mvp()

    def a_px(self, x, y):
        if self.visor is None:
            return QPointF((x - self.centro[0]) * self.escala + self.width() / 2,
                           self.height() / 2 - (y - self.centro[1]) * self.escala)
        if self._mvp is None:
            self._camara()
        q = self.visor.proyectar(self.plano.a_3d(x, y), self._mvp)
        return q if q is not None else QPointF(-1e5, -1e5)

    def a_mm(self, p):
        if self.visor is None:
            return ((p.x() - self.width() / 2) / self.escala + self.centro[0],
                    (self.height() / 2 - p.y()) / self.escala + self.centro[1])
        p3 = self.visor.interseccion_plano(p, self.plano)
        return self.plano.a_uv(p3) if p3 is not None else (self.cursor or (0.0, 0.0))

    def px_por_mm(self):
        return self.visor.px_por_mm() if self.visor is not None else self.escala

    def paso_grilla(self):
        if self.visor is not None:
            return self.visor.paso_rejilla()
        bruto = 14 / self.escala
        e = 10 ** math.floor(math.log10(bruto))
        for m in (1, 2, 5, 10):
            if m * e >= bruto:
                return m * e
        return 10 * e

    def encuadrar(self):
        xs, ys = [], []
        for p in self.b.puntos.values():
            xs.append(p.x)
            ys.append(p.y)
        for c in self.b.curvas.values():
            for poli in self._polilineas(c, 16):
                xs += [q[0] for q in poli]
                ys += [q[1] for q in poli]
        if self.visor is not None:
            if xs:
                self.visor.objetivo = self.plano.a_3d((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
                radio = max(max(xs) - min(xs), max(ys) - min(ys), 20) / 2
                self.visor.distancia = radio / math.sin(math.radians(self.visor.fov) / 2) * 1.3
                self.visor.update()
            return
        if not xs:
            self.centro, self.escala = [0.0, 0.0], 4.0
        else:
            self.centro = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
            ancho, alto = max(max(xs) - min(xs), 20), max(max(ys) - min(ys), 20)
            self.escala = min(self.width() / (ancho * 1.4), self.height() / (alto * 1.4))
        self.update()

    # ------------------------------------------------------------ deshacer
    def _instantanea(self):
        self.historial.append(self.b.a_dict())
        del self.historial[:-(200 if len(self.b.puntos) < 3000 else 100)]    # un boceto enorme pesa MB por instantánea

    def _restaurar(self, datos):
        nuevo = Boceto.desde_dict(datos)
        self.b.__dict__.update(nuevo.__dict__)   # se conserva el mismo objeto (lo referencian otros)

    def deshacer(self):
        if not self.historial:
            return
        self.pila_rehacer.append(self.b.a_dict())
        self._restaurar(self.historial.pop())
        self._tras_deshacer()

    def rehacer(self):
        """Ctrl+Y dentro del boceto: vuelve lo último que se deshizo (cualquier cambio nuevo vacía la pila)."""
        if not self.pila_rehacer:
            return
        self.historial.append(self.b.a_dict())
        self._restaurar(self.pila_rehacer.pop())
        self._tras_deshacer()

    def _tras_deshacer(self):
        self.seleccion, self.clics, self.picks, self.picks_xy = [], [], [], []
        self.perfiles_sel = []
        self.inf_actual = self.inferencia = self._inf_inicio = None
        self._reiniciar_vivo()
        self.resolver()

    # ------------------------------------------------------------ resolver
    def evaluar(self, expr, tipo=LONGITUD):
        """Evalúa contra el documento. Una cota nombrada al citarla todavía no está en su tabla (entra al terminar el
        boceto): se cita por su valor, y una referencia circular entre ellas es un error de expresión."""
        usadas = nombres_usados(expr) & self._nombradas.keys() if isinstance(expr, str) else set()
        for nombre in usadas:
            cota = self.b.cotas.get(self._nombradas[nombre])
            if cota is None:
                continue
            if nombre in self._evaluando:
                raise ErrorExpresion(f"Referencia circular: la cota {nombre} depende de sí misma.")
            self._evaluando.add(nombre)
            try:
                valor = self.evaluar(cota.expresion, _tipo_valor(cota.tipo))
            finally:
                self._evaluando.discard(nombre)
            unidad = "deg" if cota.tipo == "angulo" else "mm"
            expr = re.sub(rf"\b{re.escape(nombre)}\b", f"({valor!r} {unidad})", expr)
        return self._evaluar_doc(expr, tipo)

    def valores_cotas(self):
        return {c.id: self.evaluar(c.expresion, _tipo_valor(c.tipo)) for c in self.b.cotas.values()}

    def resolver(self, arrastrado=None, rapido=False):
        """`rapido` (arrastrar un punto): solo se resuelve la parte de ese punto y sin recontar grados de libertad;
        al soltar se resuelve todo."""
        try:
            valores = self.valores_cotas()
        except ErrorExpresion as e:
            self.mensaje.emit(f"Hay una cota con expresión inválida: {e}")
            valores = {}
        previo = self.resultado if rapido and arrastrado is not None else None
        self.resultado = resolver(self.b, valores, arrastrado, previo)
        self._cache_cortes = {}
        if arrastrado is None:
            self._generacion += 1
            self._diagnostico_agotado = False
            self._conflictos = [] if self.resultado.ok else None      # None: se diagnostica en otro hilo al pintar
            self.cambio.emit()
            self._notificar_seleccion()
        self.update()
        return self.resultado

    def _valores_para_diagnostico(self):
        try:
            return self.valores_cotas()
        except ErrorExpresion:
            return {}

    @property
    def conflictos(self):
        """BOC-7: ids de restricciones/cotas cuya retirada sola resuelve el conflicto (vacía si no hay conflicto).
        Espera el cálculo (lo usan los tests y la API); el pintado y los textos usan `conflictos_sin_esperar`.
        shortcut: una resolución por vínculo; se calcula una vez por estado y solo si hay conflicto."""
        if self._conflictos is None:
            self._conflictos = restricciones_en_conflicto(self.b, self._valores_para_diagnostico())
        return self._conflictos

    def conflictos_sin_esperar(self):
        """B-111: lo que ya se sabe del diagnóstico ([] mientras se calcula, que corre en otro hilo con «lo último
        gana»). Al llegar se emite `cambio` y se repinta, así que el rojo y el texto aparecen un poco después."""
        if self._conflictos is None:
            if self._diagnostico is None:
                caja, generacion = {}, self._generacion
                copia, valores = self.b.copia(), self._valores_para_diagnostico()

                def correr():
                    try:
                        limite = time.monotonic() + TOPE_DIAGNOSTICO_S
                        caja["res"] = restricciones_en_conflicto(
                            copia, valores, lambda: generacion != self._generacion or time.monotonic() > limite)
                    except Exception as e:  # noqa: BLE001 — se vuelve a lanzar en el hilo de la ventana
                        caja["error"] = e
                    caja["listo"] = True
                self._diagnostico = (generacion, caja)
                threading.Thread(target=correr, daemon=True).start()
                self._t_diagnostico.start(40)
            return []
        return self._conflictos

    def _sondear_conflictos(self):
        generacion, caja = self._diagnostico
        if not caja.get("listo"):
            self._t_diagnostico.start(40)
            return
        self._diagnostico = None
        if "error" in caja:
            raise caja["error"]
        if generacion != self._generacion:
            if self._conflictos is None:
                self.conflictos_sin_esperar()           # el boceto cambió mientras tanto: diagnosticar el nuevo estado
            return
        self._diagnostico_agotado = caja["res"] is None     # pasó el tope de tiempo: no se sabe cuál vínculo sobra
        self._conflictos = caja["res"] or []
        self.cambio.emit()
        self.update()
        if self._mostrar_conflictos_al_llegar:
            self._mostrar_conflictos_al_llegar = False
            self.mensaje.emit(self.texto_conflictos() or "No hay restricciones ni cotas en conflicto.")

    def geometria_en_conflicto(self, esperar=True):
        """Puntos y curvas que tocan las restricciones/cotas en conflicto (se dibujan en rojo)."""
        vinculos = {**self.b.restricciones, **self.b.cotas}
        ids = self.conflictos if esperar else self.conflictos_sin_esperar()
        return {e for i in ids if i in vinculos for e in vinculos[i].entidades}

    def texto_conflictos(self, esperar=False):
        """Qué choca, en palabras: «cota d3 = 30, horizontal (5)»; vacío si el boceto está bien. Mientras el diagnóstico
        se calcula (otro hilo) todavía no nombra nada; `esperar=True` lo espera."""
        if self.resultado is None or self.resultado.ok:
            return ""
        ids = self.conflictos if esperar else self.conflictos_sin_esperar()
        if self._conflictos is None:
            return ""
        if self._diagnostico_agotado:
            return "Hay restricciones en conflicto; el boceto es grande y no se pudo ver cuál sobra."
        nombres = []
        for i in ids:
            if i in self.b.cotas:
                k = self.b.cotas[i]
                nombres.append(f"cota {k.nombre or TIPOS_COTA[k.tipo].lower()} = {k.expresion}")
            elif i in self.b.restricciones:
                nombres.append(f"{TIPOS_RESTRICCION[self.b.restricciones[i].tipo].lower()} ({i})")
        if not nombres:
            return "No hay un solo vínculo que sobre: hay que quitar o cambiar varios."
        return f"Chocan: {', '.join(nombres)}. Quitá o cambiá uno para resolverlo."

    def mostrar_conflictos(self):
        """F5 «Qué choca»: lista las restricciones y cotas en conflicto (ya pintadas en rojo)."""
        if self.resultado is not None and not self.resultado.ok and not self.conflictos_sin_esperar() \
                and self._conflictos is None:
            self._mostrar_conflictos_al_llegar = True       # el diagnóstico corre en otro hilo: el mensaje sale al llegar
            texto = "Calculando qué choca…"
            self.mensaje.emit(texto)
            return texto
        texto = self.texto_conflictos() or "No hay restricciones ni cotas en conflicto."
        self.mensaje.emit(texto)
        self.update()
        return texto

    def aplicar_cambio(self, funcion, operacion=False, anclar=True):
        """Aplica una modificación. Si deja en conflicto un boceto que estaba bien, se deshace sola.
        Lo que crean las herramientas de dibujo toma el tipo de línea elegido (normal / línea central).
        Con `operacion` (empalme, chaflán, recortar…), si se perdieron restricciones o cotas se avisa
        como Fusion."""
        estaba_ok = self.resultado is None or self.resultado.ok
        antes = set(self.b.curvas)
        puntos_antes = set(self.b.puntos)
        vinculos = set(self.b.restricciones) | set(self.b.cotas)
        self._instantanea()
        try:
            funcion()
            if self._post_crear is not None:        # cotas de lo escrito en las cajas de valor
                self._post_crear(sorted(set(self.b.curvas) - antes))
            if anclar and self.herramienta not in MODIFICAN:
                self._anclar_al_origen(set(self.b.puntos) - puntos_antes)
        except (ErrorBoceto, ErrorExpresion) as e:
            self._restaurar(self.historial.pop())
            self.mensaje.emit(str(e))
            self.update()
            return False
        if anclar and self.herramienta not in MODIFICAN + ("linea", "texto") and set(self.b.puntos) - puntos_antes:
            self._restringir_clics(set(self.b.puntos) - puntos_antes, set(self.b.curvas) - antes)
        if anclar and self.eje and self.herramienta not in MODIFICAN:
            for cid in set(self.b.curvas) - antes:
                c = self.b.curvas[cid]
                if not c.construccion and not isinstance(c, Texto):
                    c.eje = True
        r = self.resolver()
        if estaba_ok and not r.ok:
            self._restaurar(self.historial.pop())
            self.resolver()
            self.mensaje.emit("Eso entra en conflicto con las restricciones que ya había (sobre-restringe): se deshizo.")
            return False
        self.pila_rehacer.clear()
        self.perfiles_sel = []                     # los índices de perfil dejan de valer al cambiar el boceto
        if operacion and not vinculos <= (set(self.b.restricciones) | set(self.b.cotas)):
            self.aviso.emit(AVISO_BORRADAS)
        return True

    def _anclar_al_origen(self, puntos_nuevos):
        """Anclaje compartido con los rectángulos de la API."""
        return self.b.anclar_al_origen(puntos_nuevos)

    # ------------------------------------------------------------ geometría en pantalla
    def _polilineas(self, c, pasos=64):
        """Polilíneas (u, v) de una curva (un texto da una por contorno). Con caché por primitiva: con miles de
        curvas, muestrear las splines en cada cuadro tardaba ~1 s y trababa el zoom y el paneo."""
        if isinstance(c, Texto) and c.parametro_texto:
            from ..timeline.operaciones import _contenido_texto, texto_con_valores
            valores = self.valores_parametros()
            if c.parametro_texto in valores:
                c = copy.copy(c)
                c.texto = texto_con_valores(_contenido_texto(c, valores), valores)
                return [_muestras(p, pasos) for p in primitivas_entidad(c, self.b.coords, curvas=self.b.curvas)]
        return [_muestras(p, pasos) for p in self.b.primitivas(c.id)]

    def _poli_px(self, puntos):
        if self.visor is None:               # boceto 2D: la cuenta de a_px en línea (se hace miles de veces)
            s, cx, cy = self.escala, self.centro[0], self.centro[1]
            w2, h2 = self.width() / 2, self.height() / 2
            return [QPointF((x - cx) * s + w2, h2 - (y - cy) * s) for x, y in puntos]
        if self._mvp is None:
            self._camara()
        # Con la cámara quieta (repintar por el hover, una selección…) se reusa lo proyectado. Solo se guardan las
        # tuplas (las muestras cacheadas de `_muestras`, que no cambian); la entrada retiene la tupla: su id no se recicla.
        firma = (self._mvp.tobytes(), self.visor.width(), self.visor.height())
        if firma != getattr(self, "_firma_px", None):
            self._firma_px, self._cache_px = firma, {}
        hecho = self._cache_px.get(id(puntos))
        if hecho is not None and hecho[0] is puntos:
            return hecho[1]
        # En bloque, como a_px pero con un solo producto de matrices (punto a punto: 5 µs por punto).
        uv = np.asarray(puntos, dtype=float).reshape(-1, 2)
        pl = self.plano
        p3 = pl.origen + uv[:, :1] * pl.u + uv[:, 1:] * pl.v
        c = np.hstack([p3, np.ones((len(uv), 1))]) @ self._mvp.T
        w = c[:, 3]
        delante = w > 1e-9
        w = np.where(delante, w, 1.0)
        x = np.where(delante, (c[:, 0] / w + 1) / 2 * self.visor.width(), -1e5)
        y = np.where(delante, (1 - c[:, 1] / w) / 2 * self.visor.height(), -1e5)
        poli = [QPointF(a, b) for a, b in zip(x.tolist(), y.tolist(), strict=True)]
        if isinstance(puntos, tuple):
            if len(self._cache_px) > 20000:
                self._cache_px.clear()
            self._cache_px[id(puntos)] = (puntos, poli)
        return poli

    def _visible(self, c):
        return not ((c.construccion and not self.mostrar["construccion"])
                    or (c.proyectada and not self.mostrar["proyectadas"]))

    def _punto_cercano(self, pos, excluir=None, radio_px=TOL_PUNTO):
        mejor, dmin = None, radio_px
        for p in self.b.puntos.values():
            if p.id == excluir:
                continue
            q = self.a_px(p.x, p.y)
            d = math.hypot(q.x() - pos.x(), q.y() - pos.y())
            if d < dmin:
                mejor, dmin = p.id, d
        return mejor

    def _curva_cercana(self, pos, radio_px=6.0, tipos=None, interior=False):
        mejor, dmin = None, radio_px
        for c in self.b.curvas.values():
            if not self._visible(c) or (tipos and c.tipo not in tipos):
                continue
            if interior and isinstance(c, Circulo) and radio_px * 0.8 < dmin:
                # círculo chico (un agujero): también se agarra desde adentro, cediendo ante lo que esté más cerca
                centro = self.a_px(*self.b.coords(c.centro))
                r_px = self.b.radio(c.id) * self.px_por_mm()
                if r_px <= RADIO_INTERIOR_PX and math.hypot(pos.x() - centro.x(), pos.y() - centro.y()) <= r_px:
                    mejor, dmin = c.id, radio_px * 0.8
            xs, ys = [], []
            for poli in self._polilineas(c, 48):
                px = self._poli_px(poli)
                d = min(_dist_px(pos, a, b) for a, b in zip(px, px[1:], strict=False))
                if d < dmin:
                    mejor, dmin = c.id, d
                if isinstance(c, Texto):
                    xs += [q.x() for q in px]
                    ys += [q.y() for q in px]
            if xs and min(xs) - radio_px <= pos.x() <= max(xs) + radio_px \
                    and min(ys) - radio_px <= pos.y() <= max(ys) + radio_px and radio_px * 0.9 < dmin:
                mejor, dmin = c.id, radio_px * 0.9      # dentro de la caja del texto: cede ante lo que esté más cerca
        return mejor

    def entidad_en(self, pos):
        pid = self._punto_cercano(pos)
        return pid if pid is not None else self._curva_cercana(pos, interior=True)

    # ------------------------------------------------------------ perfiles (BOC-23)
    def _plano_perfiles(self):
        from ..nucleo import geometria as geo
        return self.plano if self.plano is not None else geo.Plano("XY")

    def _perfiles(self):
        """Perfiles del boceto en el orden de `detectar` (el mismo índice que `profile` en la API). Con caché por
        geometría en el núcleo: repetir la consulta sin cambios no vuelve a partir caras."""
        from ..nucleo.perfiles import detectar
        try:
            return detectar(self.b.geometria(), self._plano_perfiles())
        except Exception:  # noqa: BLE001 — un boceto a medio dibujar no debe romper la selección
            return []

    def perfil_en(self, pos):
        """Índice del perfil (región cerrada) bajo `pos`, o None. Si hay varios (no debería), el más chico."""
        from .manipuladores import punto_en_cara
        p3 = self._plano_perfiles().a_3d(*self.a_mm(pos))
        dentro = [(p.area, i) for i, p in enumerate(self._perfiles()) if punto_en_cara(p.cara, p3, 1e-7)]
        return min(dentro)[1] if dentro else None

    def perfiles_seleccionados(self):
        """Perfiles elegidos con clic en el editor (objetos `Perfil` del núcleo: cara, área, centroide, firma)."""
        todos = self._perfiles()
        return [todos[i] for i in self.perfiles_sel if i < len(todos)]

    def _clic_perfil(self, pos):
        if self.herramienta != "seleccionar":
            return
        i = self.perfil_en(pos)
        if i is None:
            return
        if i in self.perfiles_sel:            # con Ctrl o Mayús, un segundo clic lo quita
            self.perfiles_sel.remove(i)
        else:
            self.perfiles_sel.append(i)
        self._notificar_seleccion()
        self.update()

    def _ajustar(self, pos, excluir=None, base=None):
        """Punto existente y origen primero; después ajustes a objetos, H/V y rejilla."""
        self.inf_actual = self.inferencia = None
        pid = self._punto_cercano(pos, excluir)
        if pid is not None:
            return pid, self.b.coords(pid)
        o = self.a_px(0.0, 0.0)
        if math.hypot(o.x() - pos.x(), o.y() - pos.y()) < TOL_PX:
            return None, (0.0, 0.0)                     # el origen del boceto también engancha
        x, y = self.a_mm(pos)
        excluidos = [excluir] if excluir is not None else []
        if self.herramienta == "linea" and self.clics and self._ultima_linea is not None:
            excluidos.append(self._ultima_linea)
        self.inf_actual = inferir(self.b, (x, y), TOL_PX / self.px_por_mm(), base=base,
                                  excluir=excluidos,
                                  coincidente=bool(self._modificadores_raton & Qt.ShiftModifier),
                                  angulo_tol=TOL_INFERENCIA)
        if self.inf_actual is not None:
            if self.inf_actual.tipo in ("horizontal", "vertical"):
                self.inferencia = self.inf_actual.tipo
            return None, self.inf_actual.xy
        if self.ajustar_grilla:
            s = self.paso_grilla()
            x, y = round(x / s) * s, round(y / s) * s
        return None, (x, y)

    # ------------------------------------------------------------ herramientas
    def set_herramienta(self, h):
        self.confirmar_texto_pendiente()          # cambiar de herramienta no pierde el texto escrito
        if h == "texto":
            self.opciones.update(pivote_texto=None, marco_texto=False, parametro_texto=None, valor_parametro_texto="")
        self.herramienta = h
        if h != "seleccionar":
            self.ultima_herramienta = h           # para «Repetir» del menú radial
        self.clics, self.picks, self.picks_xy = [], [], []
        self.inf_actual = self.inferencia = self._inf_inicio = None
        self.fase = None
        self._previa_recorte = None
        self._esperando_ubicacion = False
        self._opc_cota = {}
        self._revincular = self._eje_giro = None
        self._cerrar_entrada()
        self._reiniciar_vivo()
        nombre, ayuda = HERRAMIENTAS.get(h, (NOMBRES_RESTRICCION.get(h, h), ""))
        if h in RESTRICCIONES_HERRAMIENTA:
            ayuda = f"{NOMBRES_RESTRICCION[h]}: hacé clic en la geometría a restringir."
            if self._restriccion_con_seleccion():
                return
        if h in SELECCION:
            self.fase = "seleccion"
            if self._seleccion_util():
                self._avanzar_seleccion(avisar=False)
        self.mensaje.emit(f"{nombre}: {ayuda}" if ayuda else nombre)
        self.herramienta_cambiada.emit(h)
        self.update()

    def _hay_operacion(self):
        """Algo a medias en la herramienta: clics puestos, cota o selección a medio elegir, caja de valor o texto
        abiertos, o una fase de la herramienta."""
        return bool(self.clics or self.picks or self.entrada is not None or self._tangente is not None
                    or self.fase not in (None, "seleccion"))

    def cancelar(self):
        """Esc y clic derecho sin arrastrar: si hay algo a medias lo corta y la herramienta sigue; si no, sale de la
        herramienta y vuelve a Seleccionar; en Seleccionar, borra la selección."""
        if self._eligiendo_punto is not None:
            self._terminar_eleccion()
            return
        if self._arrastre is not None:             # B-111: Esc en pleno arrastre lo cancela y deja el boceto como estaba
            self._arrastre = None
            self._restaurar(self.historial.pop())
            self._cache_cortes = {}
            self.cambio.emit()
            self.update()
            return
        self.inf_actual = self.inferencia = self._inf_inicio = None
        if self._hay_operacion():
            self._cerrar_entrada()
            self.clics, self.picks, self.picks_xy = [], [], []
            self._esperando_ubicacion = False
            self._opc_cota = {}
            self._ultima_linea = None
            self._reiniciar_vivo()
            if self.fase is not None:
                self.fase = "seleccion"
        elif self.herramienta != "seleccionar":
            self.set_herramienta("seleccionar")
        else:
            self.seleccion, self.perfiles_sel = [], []
        self._notificar_seleccion()
        self.update()

    def _crear_linea(self, a, b, inferencia=None, cota=None):
        (p1, xa), (p2, xb) = a, b
        nueva = {}
        inf_inicio, inf_fin = self._inf_inicio, self.inf_actual
        post_crear = self._post_crear

        def restringir(nuevas):
            if post_crear is not None:
                post_crear(nuevas)
            linea = self.b.curvas[nueva["id"]]
            pendientes = [(linea.p1, inf_inicio), (linea.p2, inf_fin)]
            if not inferencia or (p1 is not None and p2 is not None):
                pendientes = [(pid, inf) for pid, inf in pendientes
                              if inf is None or inf.tipo not in ("horizontal", "vertical")]
            self._restringir_inferencias(linea.id, pendientes)

        def crear():
            lid = self.b.agregar_linea(p1 if p1 is not None else xa, p2 if p2 is not None else xb, self.construccion)
            nueva["id"] = lid
            if inferencia and inf_fin is None and not (p1 is not None and p2 is not None):
                self.b.agregar_restriccion(inferencia, [lid])
            if cota:
                self.b.agregar_cota("distancia", [lid], cota)
        self._post_crear = restringir
        try:
            if self.aplicar_cambio(crear):
                return nueva["id"]
        finally:
            self._post_crear = post_crear
        return None

    def _restringir_inferencias(self, linea, extremos):
        """Ensaya las restricciones inferidas sin perder la geometría si alguna entra en conflicto."""
        pendientes = [(pid, inf) for pid, inf in extremos if inf is not None and inf.restriccion]
        if not pendientes:
            return
        antes = self.b.a_dict()
        try:
            for pid, inf in pendientes:
                tipo, *objetivos = inf.restriccion
                entidad = pid if tipo in ("punto_medio", "coincidente") else linea
                self.b.agregar_restriccion(tipo, [entidad, objetivos[0]] if objetivos else [entidad])
                for adicional, destino in objetivos[1:]:
                    self.b.agregar_restriccion(adicional, [pid, destino])
            if not resolver(self.b.copia(), self.valores_cotas()).ok:
                raise ErrorBoceto("La inferencia entra en conflicto con las restricciones existentes.")
        except ErrorBoceto:
            self._restaurar(antes)

    def _guardar_inferencia_clic(self, pid, xy):
        """BOC-9: qué une el clic en `xy` (punto existente, punto medio o punto sobre una curva), para restringir el
        punto que la herramienta cree ahí. Línea, línea de punto medio y rectángulo 3p también restringen su lado;
        círculo convierte el radio perpendicular en tangencia con la línea objetivo."""
        inf = self.inf_actual
        if pid is not None:
            union = ("coincidente", pid)
        elif inf is None or not inf.restriccion or inf.objetivo is None:
            return
        elif inf.restriccion[0] in ("coincidente", "punto_medio"):
            union = inf.restriccion[:2]
        elif inf.tipo == "tangente" or ("coincidente", inf.objetivo) in inf.restriccion[2:]:
            union = ("coincidente", inf.objetivo)          # el punto de contacto queda sobre la curva
        else:
            return
        self._inf_clics.append((xy, *union))

    def _restringir_clics(self, puntos_nuevos, curvas_nuevas):
        """Agrega las uniones guardadas por `_guardar_inferencia_clic` a los puntos nuevos que quedaron en el lugar
        del clic. Cada una se ensaya sola: si choca con lo que ya hay, se descarta sin perder la geometría."""
        pendientes, self._inf_clics = self._inf_clics, []
        for xy, tipo, objetivo in pendientes:
            if objetivo in curvas_nuevas or objetivo in puntos_nuevos:
                continue
            pid = next((p for p in sorted(puntos_nuevos) if math.dist(self.b.coords(p), xy) < 1e-6), None)
            if pid is None or any(r.tipo == tipo and set(r.entidades) == {pid, objetivo}
                                  for r in self.b.restricciones.values()):
                continue
            antes = self.b.a_dict()
            try:
                self.b.agregar_restriccion(tipo, [pid, objetivo])
                if not resolver(self.b.copia(), self.valores_cotas()).ok:
                    raise ErrorBoceto("La inferencia entra en conflicto con las restricciones existentes.")
            except ErrorBoceto:
                self._restaurar(antes)

    def _curvas_con_extremo(self, pid):
        """Curvas abiertas (línea, arco, spline, cónica…) que terminan en el punto `pid`."""
        return [k.id for k in self.b.curvas.values() if pid in (k.extremos() or ())]

    def _crear_arco_tangente(self, pid, linea, fin):
        """Arco desde el punto `pid` (extremo de la curva `linea`) hasta `fin`, tangente a ella."""
        (pfin, xyf) = fin
        p, salida = self.b._salida_extremo(linea, pid)
        geometria = centro_arco_tangente(p, (p[0] - salida[0], p[1] - salida[1]), xyf)
        if geometria is None:
            return None
        centro, izquierda = geometria
        nuevo = {}

        def crear():
            destino = pfin if pfin is not None else xyf
            aid = (self.b.agregar_arco_centro(centro, pid, destino, self.construccion) if izquierda
                   else self.b.agregar_arco_centro(centro, destino, pid, self.construccion))
            self.b.agregar_restriccion("tangente", [linea, aid])
            nuevo["id"] = aid
        if self.aplicar_cambio(crear):
            arco = self.b.curvas[nuevo["id"]]
            return nuevo["id"], (arco.fin if izquierda else arco.inicio)
        return None

    def _rectangulo_3p(self, a, b, c):
        return agregar_rectangulo_3p(self.b, a, b, c, self.construccion)

    def _poligono(self, centro, vertice, lados, tipo, centro_pid=None):
        r, esquinas = _vertices_poligono(centro, vertice, lados, tipo)
        if r < 1e-9:
            raise ErrorBoceto("El polígono necesita un tamaño.")
        cid = self.b.agregar_circulo(centro_pid if centro_pid is not None else centro, r, True)
        verts = [self.b.agregar_punto(*q) for q in esquinas]
        ls = [self.b.agregar_linea(verts[k], verts[(k + 1) % lados], self.construccion) for k in range(lados)]
        for k in range(1, lados):
            self.b.agregar_restriccion("igual", [ls[0], ls[k]])
        if tipo == "circunscrito":
            for ln in ls:
                self.b.agregar_restriccion("tangente", [ln, cid])
            # con lados pares, «igual» + «tangente» deja los tramos de tangencia alternar (un grado de libertad de
            # más): la restricción de polígono regular lo cierra (igual que `create_polygon` de la API)
            self.b.agregar_restriccion("poligono", list(ls))
        else:
            for v in verts:
                self.b.agregar_restriccion("coincidente", [v, cid])
        return ls, cid

    @staticmethod
    def _eje_ranura(h, pts):
        """Centros de los extremos de una ranura recta."""
        if h == "ranura_punto":
            m, b = pts[0], pts[1]
            return (2 * m[0] - b[0], 2 * m[1] - b[1]), b
        return pts[0], pts[1]

    @staticmethod
    def _arco_ranura(h, pts):
        """(centro, radio) del eje de una ranura de arco."""
        if h == "ranura_arco_3p":
            circ = circunferencia_3_puntos(pts[0], pts[2], pts[1])
            return ((circ[0], circ[1]), circ[2]) if circ else (pts[0], 0.0)
        return pts[0], math.dist(pts[0], pts[1])

    def _ancho_ranura(self, h, c, cur):
        """Medio ancho de la ranura: distancia del último clic al eje (recto o de arco)."""
        pts = [p for _, p in c]
        if h not in RANURAS_RECTAS:
            centro, R = self._arco_ranura(h, pts)
            return abs(math.dist(cur, centro) - R)
        a, b = self._eje_ranura(h, pts)
        L = math.dist(a, b) or 1e-9
        return abs((b[0] - a[0]) * (cur[1] - a[1]) - (b[1] - a[1]) * (cur[0] - a[0])) / L

    def _crear_ranura(self, h, c, cur):
        tipo = {"ranura_centro": "centro", "ranura_total": "total", "ranura_punto": "punto",
                "ranura_arco_3p": "arco_3p", "ranura_arco_centro": "arco_centro"}[h]
        n = 2 if tipo in ("centro", "total", "punto") else 3
        puntos = [pid if pid is not None and tipo == "centro" else xy for pid, xy in c[:n]]
        if tipo == "arco_3p":
            puntos = [c[0][1], c[1][1], c[2][1]]
        ancho = 2 * self._ancho_ranura(h, c[:n], cur)
        self.aplicar_cambio(lambda: self.b.agregar_ranura(tipo, puntos, ancho, self.construccion))

    def _espiral(self, centro, inicio, vueltas, paso):
        pts = puntos_espiral(centro, inicio, vueltas, paso)
        return self.b.agregar_spline(pts, "ajuste", 3, False, construccion=self.construccion)

    def _rho_conica(self, punto):
        """Rho de Fusion: proyección relativa sobre el segmento punto medio–vértice."""
        a, b, v = [xy for _, xy in self.clics[:3]]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        dx, dy = v[0] - m[0], v[1] - m[1]
        largo2 = dx * dx + dy * dy
        if largo2 < 1e-18:
            return 0.5
        rho = ((punto[0] - m[0]) * dx + (punto[1] - m[1]) * dy) / largo2
        return max(1e-6, min(1 - 1e-6, rho))      # 0 y 1 son cónicas degeneradas

    def _actualizar_rho_conica(self, pos):
        """El ratón cambia Rho sin ajuste a rejilla; lo escrito conserva prioridad."""
        self.cursor = self.a_mm(pos)
        self.inf_actual = self.inferencia = None
        campo = self.entrada.campos[0]
        if not campo.isModified():
            campo.setText(f"{self._rho_conica(self.cursor):.12g}")
            campo.selectAll()

    def _procesar_clics(self):
        h, c = self.herramienta, self.clics
        if h == "linea" and len(c) == 2:
            if math.dist(c[0][1], c[1][1]) < 1e-9:
                c.pop()
                return
            lid = self._crear_linea(c[0], c[1], self.inferencia)
            if lid is not None:
                fin = self.b.curvas[lid].p2
                self.clics, self._ultima_linea = [(fin, self.b.coords(fin))], lid
            else:
                self.clics = []
        elif h == "linea_medio" and len(c) == 2:
            (pm, m), (pe, e) = c
            self.aplicar_cambio(lambda: agregar_linea_medio(self.b, pm if pm is not None else m,
                                                            pe if pe is not None else e, self.construccion))
            self.clics = []
        elif h == "rectangulo" and len(c) == 2:
            (p1, a), (p2, b) = c

            def crear():
                ls = self.b.agregar_rectangulo(a, b, self.construccion)
                if p1 is not None:
                    self.b.agregar_restriccion("coincidente", [self.b.curvas[ls[0]].p1, p1])
                if p2 is not None:
                    self.b.agregar_restriccion("coincidente", [self.b.curvas[ls[2]].p1, p2])
            self.aplicar_cambio(crear)
            self.clics = []
        elif h == "rectangulo_3p" and len(c) == 3:
            self.aplicar_cambio(lambda: self._rectangulo_3p(c[0][1], c[1][1], c[2][1]))
            self.clics = []
        elif h == "rectangulo_centro" and len(c) == 2:
            (pc, m), (_, k) = c
            self.aplicar_cambio(lambda: agregar_rectangulo_centro(self.b, pc if pc is not None else m, k,
                                                                  self.construccion))
            self.clics = []
        elif h == "circulo" and len(c) == 2:
            (pc, a), (_, b) = c
            r = math.dist(a, b)
            if r < 1e-9:
                c.pop()
                return
            self.aplicar_cambio(lambda: self.b.agregar_circulo(pc if pc is not None else a, r, self.construccion))
            self.clics = []
        elif h == "circulo_2p" and len(c) == 2:
            (_, a), (_, b) = c
            r = math.dist(a, b) / 2
            if r < 1e-9:
                c.pop()
                return
            self.aplicar_cambio(lambda: self.b.agregar_circulo(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), r,
                                                               self.construccion))
            self.clics = []
        elif h == "circulo_3p" and len(c) == 3:
            def crear():
                circ = circunferencia_3_puntos(c[0][1], c[1][1], c[2][1])
                if circ is None:
                    raise ErrorBoceto("Los tres puntos están alineados: no definen un círculo.")
                self.b.agregar_circulo((circ[0], circ[1]), circ[2], self.construccion)
            self.aplicar_cambio(crear)
            self.clics = []
        elif h == "circulo_2t" and c:
            ubicacion = c[-1][1]
            self.clics = []
            if len(self.picks) == 2:
                lineas = list(self.picks)
                self.aplicar_cambio(lambda: self.b.agregar_circulo_tangente(lineas, ubicacion, None, None,
                                                                            self.construccion))
                self.picks, self.picks_xy = [], []
        elif h == "arco" and len(c) == 3:
            (pi, a), (pf, b), (_, m) = c
            self.aplicar_cambio(lambda: self.b.agregar_arco_3_puntos(pi if pi is not None else a, m,
                                                                     pf if pf is not None else b, self.construccion))
            self.clics = []
        elif h == "arco_centro" and len(c) == 3:
            (pc, ce), (pi, ini), (_, f) = c
            r = math.dist(ce, ini)
            a1 = math.atan2(f[1] - ce[1], f[0] - ce[0])
            fin = (ce[0] + r * math.cos(a1), ce[1] + r * math.sin(a1))
            a0 = math.atan2(ini[1] - ce[1], ini[0] - ce[0])
            antihorario = _barrido(a0, a1) <= math.pi      # se toma el arco corto, como al mover el ratón
            if self._sentido_vivo is not None:             # …salvo que se haya escrito el barrido
                antihorario = self._sentido_vivo
            centro = pc if pc is not None else ce
            inicio = pi if pi is not None else ini
            self.aplicar_cambio(lambda: (self.b.agregar_arco_centro(centro, inicio, fin, self.construccion)
                                         if antihorario else
                                         self.b.agregar_arco_centro(centro, fin, inicio, self.construccion)))
            self.clics = []
        elif h == "arco_tangente":
            if len(c) == 1:
                if c[0][0] is None or not self._curvas_con_extremo(c[0][0]):
                    self.mensaje.emit("Hacé clic en el extremo de una curva abierta.")
                    self.clics = []
            elif len(c) == 2:
                pid = c[0][0]
                self._crear_arco_tangente(pid, self._curvas_con_extremo(pid)[0], c[1])
                self.clics = []
        elif h in ("poligono_inscrito", "poligono_circunscrito") and len(c) == 2:
            (pc, ce), (_, v) = c
            tipo = "inscrito" if h == "poligono_inscrito" else "circunscrito"
            self.aplicar_cambio(lambda: self._poligono(ce, v, self.lados, tipo, pc))
            self.clics = []
        elif h == "poligono_arista" and len(c) == 3:
            (_, a), (_, b), (_, lado) = c
            L = math.dist(a, b)

            def crear():
                if L < 1e-9:
                    raise ErrorBoceto("La arista no puede medir cero.")
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
                if (lado[0] - mx) * nx + (lado[1] - my) * ny < 0:
                    nx, ny = -nx, -ny
                apotema = L / (2 * math.tan(math.pi / self.lados))
                self._poligono((mx + nx * apotema, my + ny * apotema), a, self.lados, "inscrito")
            self.aplicar_cambio(crear)
            self.clics = []
        elif h == "elipse" and len(c) == 3:
            (pc, ce), (_, m), (_, q) = c
            a = math.dist(ce, m) or 1e-9
            radio_menor = abs((m[0] - ce[0]) * (q[1] - ce[1]) - (m[1] - ce[1]) * (q[0] - ce[0])) / a
            self.aplicar_cambio(lambda: self.b.agregar_elipse(pc if pc is not None else ce, m, radio_menor,
                                                              self.construccion))
            self.clics = []
        elif h.startswith("ranura_") and len(c) == (3 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 4):
            self._crear_ranura(h, c, c[-1][1])
            self.clics = []
        elif h in SPLINES and len(c) >= 2:
            if h == "spline_ajuste" and len(c) >= 4 and math.dist(c[-1][1], c[0][1]) < 1e-9:
                self._terminar_spline(cerrar=True)
            elif math.dist(c[-1][1], c[-2][1]) < 1e-9:
                c.pop()
        elif h == "conica" and len(c) == 3:
            def aceptar(v):
                rho = _numero(v[0] or "0.5")
                (p0, a), (p2, b), (pv, vx) = self.clics
                ok = self.aplicar_cambio(lambda: self.b.agregar_conica(p0 if p0 is not None else a,
                                                                       pv if pv is not None else vx,
                                                                       p2 if p2 is not None else b, rho,
                                                                       self.construccion))
                if ok:
                    self.clics = []
                return ok
            self._abrir_entrada(["Rho"], ["0.5"], self._pos_cursor, aceptar)
            self.entrada.campos[0].textChanged.connect(lambda _t: self.update())
        elif h == "punto" and len(c) == 1:
            if c[0][0] is None:
                self.aplicar_cambio(lambda: self.b.agregar_punto(*c[0][1]))
            self.clics = []
        elif h == "texto" and c:
            if len(c) > 1 and self.entrada is not None:
                c.pop()                                 # ya hay una caja de texto abierta
                return
            pid, xy = c[0]
            # clic sobre una curva (no sobre un punto): texto en curva, centrado donde se hizo clic
            camino = None
            if len(c) == 1 and pid is None:
                camino = self._curva_cercana(self.a_px(*xy))
                if camino is not None and isinstance(self.b.curvas.get(camino), Texto):
                    camino = None
                if camino is None:
                    self.mensaje.emit("Texto: clic en la esquina opuesta para dibujar el cuadro del texto "
                                      "(o clic otra vez en el mismo lugar para un texto de 5 mm).")
                    return                              # falta la 2.ª esquina del cuadro
            en_curva, caja, altura_ini, rect = {}, {}, self.opciones["altura_texto"], None
            if camino is not None:
                pos = fraccion_en_camino(self.b.primitivas(camino)[0], xy)
                en_curva = {"camino": camino, "camino_pos": pos, "alineacion": "centro"}
            elif len(c) == 2:
                fin_xy = c[1][1]
                x0, x1 = sorted((xy[0], fin_xy[0]))
                y0, y1 = sorted((xy[1], fin_xy[1]))
                if x1 - x0 > 1e-6 and y1 - y0 > 1e-6:   # cuadro dibujado: su alto es el de la letra, su ancho parte líneas
                    pid, xy, altura_ini = None, (x0, y1), y1 - y0
                    caja = {"ancho_caja": x1 - x0, "ancla_v": "arriba"}
                    rect = (x0, y0, x1, y1)

            def aceptar(v):
                v = (list(v) + [""] * 5)[:5]          # los campos de más (espaciado, interlineado) son opcionales
                altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
                espaciado, interlineado = self.evaluar(v[3] or "0"), _numero(v[4] or "1")
                o = self.opciones
                extra = {"alineacion": o["alineacion"], "ancla_v": o["ancla_v"], "voltear_h": o["voltear_h"],
                         "voltear_v": o["voltear_v"]} | en_curva | caja | {k: o[k] for k in Texto.TIPOGRAFIA}
                if en_curva:
                    extra |= {k: o[k] for k in CURVA_TEXTO}
                ok = self.aplicar_cambio(lambda: self.b.agregar_texto(
                    pid if pid is not None else xy, v[0].replace("\\n", "\n"), altura, ang, o["fuente"],
                    o["negrita"], o["cursiva"], espaciado=espaciado, interlineado=interlineado, **extra))
                self.clics = []
                self.opciones["ajustes_kerning"] = []          # el kerning a mano es de ESE texto
                return ok
            if camino is not None:
                self.mensaje.emit("Texto en curva: las letras siguen la curva elegida (Lado en curva, en el panel "
                                  "Carácter).")
            self.opciones["ajustes_kerning"] = []
            from .asas_boceto import asas_texto
            self._abrir_entrada(["Texto", "Altura", "∠", "Espaciado", "Interlineado"],
                                ["Texto", formato.numero(altura_ini), "0", formato.numero(self.opciones["espaciado"]),
                                 formato.numero(self.opciones["interlineado"])], self._pos_cursor, aceptar,
                                None if camino is not None else asas_texto(self, xy, caja.get("ancho_caja", 0.0)))
            self._previa_texto = {"pos": pid if pid is not None else xy, "existente": None,
                                  "extra": en_curva | caja, "caja": rect, "reemplazar": True}
            self._conectar_previa_texto()
        elif h == "espiral" and len(c) == 2:
            (_, ce), (_, ini) = c

            def aceptar(v):
                vueltas, paso = _numero(v[0] or "3"), self.evaluar(v[1] or "2")
                ok = self.aplicar_cambio(lambda: self._espiral(ce, ini, vueltas, paso))
                self.clics = []
                return ok
            self._abrir_entrada(["Vueltas", "Paso"], ["3", formato.numero(max(math.dist(ce, ini), 1.0) / 2)],
                                self._pos_cursor, aceptar)
        elif h in SELECCION and c:
            self._clic_fase(c[-1])
            self.clics = []

    def _terminar_spline(self, cerrar=False):
        """Enter, doble clic o clic en el primer punto: crea la spline con los puntos marcados."""
        h, c = self.herramienta, list(self.clics)
        if cerrar and c and len(c) > 1 and math.dist(c[-1][1], c[0][1]) < 1e-9:
            c.pop()
        self.clics = []
        if len(c) < 2:
            return None
        puntos = [pid if pid is not None else xy for pid, xy in c]
        modo = "ajuste" if h == "spline_ajuste" else "control"
        grado = self.opciones["grado_spline"] if modo == "control" else 3
        nuevo = {}

        def crear():
            nuevo["id"] = self.b.agregar_spline(puntos, modo, grado, cerrar, construccion=self.construccion)
        self.aplicar_cambio(crear)
        return nuevo.get("id")

    # ------------------------------------------------------------ herramientas sobre una selección
    def _seleccion_util(self):
        return [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos]

    def _avanzar_seleccion(self, avisar=True):
        """Enter en la fase de selección: pasa al paso siguiente de la herramienta."""
        h = self.herramienta
        ids = self._seleccion_util()
        if not ids:
            if avisar:
                self.mensaje.emit("Seleccioná primero la geometría (clic en las curvas).")
            return
        if h == "simetria":
            self.fase = "eje"
            self.mensaje.emit("Simetría: clic en la línea de simetría.")
        elif h == "patron_rectangular":
            self.fase = "valores"

            def aceptar(v):
                n1, d1 = int(_numero(v[0] or "1")), self.evaluar(v[1] or "0")
                n2, d2 = int(_numero(v[2] or "1")), self.evaluar(v[3] or "0")
                ok = self.aplicar_cambio(lambda: self.b.patron_rectangular(ids, n1, d1, n2, d2,
                                                                           modo=self.opciones["patron_distancia"]))
                if ok:
                    self.seleccion, self.fase = [], "seleccion"
                return ok
            from .asas_boceto import asas_patron_rectangular
            self._abrir_entrada(["Cant. X", "Dist. X", "Cant. Y", "Dist. Y"], ["3", "30", "1", "20"],
                                self._pos_cursor, aceptar, asas_patron_rectangular(self, ids))
        elif h == "patron_circular":
            self.fase = "centro"
            self.mensaje.emit("Patrón circular: clic en el punto central.")
        elif h in ("escala", "mover"):
            self.fase = "base"
            self.mensaje.emit("Clic en el punto base.")
        self.update()

    def _clic_fase(self, clic):
        """Clics de posición en las herramientas de selección (punto base, destino, centro)."""
        h, (pid, xy) = self.herramienta, clic
        ids = self._seleccion_util()
        if self.fase == "centro" and h == "patron_circular":
            centro = pid if pid is not None else xy

            def aceptar(v):
                n, ang = int(_numero(v[0] or "6")), self.evaluar(v[1] or "360", ANGULO)
                ok = self.aplicar_cambio(lambda: self.b.patron_circular(ids, centro, n, ang))
                if ok:
                    self.seleccion, self.fase = [], "seleccion"
                return ok
            from .asas_boceto import asas_patron_circular
            self._abrir_entrada(["Cantidad", "∠ total"], ["6", "360"], self._pos_cursor, aceptar,
                                asas_patron_circular(self, ids, centro))
        elif self.fase == "base" and h == "escala":
            def aceptar(v):
                f = self.evaluar(v[0] or "1", ESCALAR)
                ok = self.aplicar_cambio(lambda: self.b.escalar(ids, xy, f))
                if ok:
                    self.seleccion, self.fase = [], "seleccion"
                return ok
            from .asas_boceto import asas_escala
            self._abrir_entrada(["Factor"], ["2"], self._pos_cursor, aceptar, asas_escala(self, ids, xy))
        elif self.fase == "base" and h == "mover":
            self._base = xy
            self.fase = "destino"
            self.mensaje.emit("Clic en el destino (o escribí ΔX, Tab, ΔY, Tab, ángulo y Enter).")

            def aceptar(v):
                return self._mover(ids, self.evaluar(v[0] or "0"), self.evaluar(v[1] or "0"),
                                   self.evaluar(v[2] or "0", ANGULO))
            self._abrir_entrada(["ΔX", "ΔY", "∠"], ["0", "0", "0"], self._pos_cursor, aceptar)
        elif self.fase == "destino" and h == "mover":
            self._mover(ids, xy[0] - self._base[0], xy[1] - self._base[1], 0.0)

    def _mover(self, ids, dx, dy, ang):
        ok = self.aplicar_cambio(lambda: self.b.transformar(ids, dx, dy, ang, self._base, self.opciones["copiar"]))
        if ok:
            self.seleccion, self.fase = [], "seleccion"
        return ok

    # ------------------------------------------------------------ herramientas que eligen curvas
    def _clic_pick(self, pos):
        tipos = ("linea",) if self.fase == "eje" else PICKS[self.herramienta][1]
        cid = self._curva_cercana(pos, tipos=tipos)
        if cid is None:
            if self.herramienta == "circulo_2t" and len(self.picks) == 2:
                return False          # el clic ubica el círculo (lo procesa la herramienta de puntos)
            self.mensaje.emit("Hacé clic sobre " + ("una línea." if tipos == ("linea",) else
                                                     "un texto." if tipos == ("texto",) else "una curva."))
            return True
        self.agregar_pick(cid, self.a_mm(pos), pos)
        return True

    def agregar_pick(self, cid, xy, pos=None):
        """Suma una curva elegida (con el lugar del clic, en mm) a la herramienta actual."""
        h = self.herramienta
        pos = pos if pos is not None else self._pos_cursor
        if h == "simetria" and self.fase == "eje":
            ids = self._seleccion_util()
            if self.aplicar_cambio(lambda: self.b.simetria(ids, cid)):
                self.seleccion, self.fase = [], "seleccion"
            return
        n, _ = PICKS[h]
        if len(self.picks) >= n:
            self.picks, self.picks_xy = [], []
        if cid in self.picks:
            return
        self.picks.append(cid)
        self.picks_xy.append(xy)
        if len(self.picks) < n:
            self.update()
            return
        picks, xys = list(self.picks), list(self.picks_xy)
        listo = True
        if h == "recortar":
            self.aplicar_cambio(lambda: self.b.recortar(cid, xy), operacion=True)
        elif h == "alargar":
            self.aplicar_cambio(lambda: self.b.alargar(cid, xy), operacion=True)
        elif h == "partir":
            self.aplicar_cambio(lambda: self.b.partir(cid, xy), operacion=True)
        elif h == "desglosar_texto":
            self.aplicar_cambio(lambda: self.b.desglosar_texto(cid), operacion=True)
        elif h == "circulo_3t":
            self.aplicar_cambio(lambda: self.b.agregar_circulo_tangente(picks, None, None, xys, self.construccion))
        elif h == "circulo_2t":
            listo = False
            self.mensaje.emit("Clic para ubicar el círculo (o escribí el radio).")
        elif h == "curva_fusion":
            self.aplicar_cambio(lambda: self.b.curva_fusion(picks[0], xys[0], picks[1], xys[1],
                                                            self.opciones["continuidad"]), operacion=True)
        elif h == "empalme":
            listo = False
            from .asas_boceto import asas_empalme
            self._abrir_entrada(["Radio"], [formato.numero(self._radio_sugerido(picks))], pos,
                                lambda v: self._aplicar_y_limpiar(
                                    lambda: self.b.empalme(picks[0], picks[1], self.evaluar(v[0]), xys[0], xys[1], v[0])),
                                asas_empalme(self, picks, xys))
        elif h in ("chaflan", "chaflan_dist_angulo", "chaflan_dos_dist"):
            listo = False
            d = formato.numero(self._radio_sugerido(picks))
            if h == "chaflan":
                etiquetas, textos = ["Distancia"], [d]
            elif h == "chaflan_dos_dist":
                etiquetas, textos = ["Distancia 1", "Distancia 2"], [d, d]
            else:
                etiquetas, textos = ["Distancia", "∠"], [d, "45"]

            def aceptar(v):
                d1 = self.evaluar(v[0])
                d2 = self.evaluar(v[1]) if h == "chaflan_dos_dist" else None
                ang = self.evaluar(v[1], ANGULO) if h == "chaflan_dist_angulo" else None
                return self._aplicar_y_limpiar(lambda: self.b.chaflan(picks[0], picks[1], d1, d2, ang, xys[0], xys[1],
                                                                      v[0]))
            from .asas_boceto import asas_chaflan
            self._abrir_entrada(etiquetas, textos, pos, aceptar, asas_chaflan(self, h, picks, xys))
        elif h == "desfase":
            listo = False
            cadena, _ = self.b.cadena(cid)
            self.seleccion = [k for k, _ in cadena]

            modo = self.opciones["direccion_desfase"]          # un lado, dos lados o simétrico (SKT-OFFSET)

            def aceptar(v):
                d = self.evaluar(v[0])
                lado = self.cursor if self.cursor is not None else xy
                lado = lado if d >= 0 else self._lado_opuesto(cid, lado)
                pasos = [(abs(d), v[0].lstrip("-"), False)]
                if modo != "un":                               # el 2.º lado: positivo = al contrario del primero
                    texto = v[1] if modo == "dos" else v[0]
                    d2 = self.evaluar(texto)
                    pasos.append((abs(d2), texto.lstrip("-"), modo == "simetrico" or d2 >= 0))

                avisos = []

                def desfasar():
                    for dist, expresion, invertir in pasos:
                        if self.opciones["match_topology"]:
                            tope = self.b.desfase_con_topologia(cid, dist, lado, invertir)
                            if tope < dist:
                                avisos.append(f"Match Topology: la distancia se limitó de {dist:g} a {tope:.4g} mm "
                                               "para conservar todos los segmentos.")
                                dist = round(tope, 6)
                                expresion = repr(dist)
                        self.b.desfase(cid, dist, lado, expresion, invertir=invertir)
                ok = self._aplicar_y_limpiar(desfasar)
                if ok:
                    self.seleccion = []
                    if avisos:
                        self.mensaje.emit(" ".join(avisos))
                return ok
            sugerido = formato.numero(self._radio_sugerido(picks))
            self._abrir_entrada(["Desfase", "Desfase 2"] if modo == "dos" else ["Desfase"],
                                [sugerido] * (2 if modo == "dos" else 1), pos, aceptar)
        if listo:
            self.picks, self.picks_xy = [], []
        self.update()

    def _aplicar_y_limpiar(self, funcion):
        ok = self.aplicar_cambio(funcion, operacion=True)
        if ok:
            self.picks, self.picks_xy = [], []
        return ok

    def _lado_opuesto(self, cid, q):
        prim = self.b.primitivas(cid)[0]
        _t, _d, p = mas_cercano(prim, q)
        return (2 * p[0] - q[0], 2 * p[1] - q[1])

    def _radio_sugerido(self, ids):
        """Valor inicial (como Fusion: proporcional a la más chica de las curvas elegidas)."""
        largos = []
        for i in ids:
            pts = puntos_primitiva(self.b.primitivas(i)[0], 32)
            largos.append(sum(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False)))
        v = min(largos) / 5 if largos else 1.0
        e = 10 ** math.floor(math.log10(max(v, 1e-6)))
        return max(round(v / e) * e, 1e-3)

    # ------------------------------------------------------------ Proyectar / Intersecar / Incluir
    def proyectar_forma(self, forma, modo="proyectar", ref=None):
        """Agrega al boceto la proyección (o la intersección) de una forma OCC sobre su plano. Con `ref` (la
        referencia persistente de lo elegido) la proyección sigue al modelo cuando este cambia (B-09)."""
        from ..nucleo.perfiles import intersecar_forma, proyectar_forma
        if self.plano is None:
            raise ErrorBoceto("El boceto no tiene plano.")
        prims, puntos = (intersecar_forma if modo == "intersecar" else proyectar_forma)(forma, self.plano)
        if not prims and not puntos:
            self.mensaje.emit("Eso no deja nada sobre el plano del boceto.")
            return False
        origen = {"modo": "intersect" if modo == "intersecar" else "project", "refs": [ref]} if ref else None
        if not self.opciones["vinculo_proyeccion"]:          # Projection Link apagado: queda congelada
            origen = None
        return self.aplicar_cambio(lambda: self.b.agregar_proyeccion(prims, puntos, self.construccion, origen))

    def _eje_perfil_giratorio(self):
        from ..timeline import entidades as ent
        if self.opciones["eje_giro"] == "arista":
            if self._eje_giro is None:
                raise ErrorBoceto("Elegí primero una arista recta como eje del perfil giratorio.")
            return self._eje_giro
        ref = {"tipo": "eje", "id": self.opciones["eje_giro"]}
        return ent.como_eje(ent.resolver(ref, self.estado_referencias())), ref

    def _agregar_eje_proyectado(self, eje, ref):
        from ..timeline import entidades as ent
        prims, puntos = ent.proyectar_entidad(ent.Entidad("eje", eje=eje), self.plano)
        datos = {"modo": "project", "refs": [ref], "infinitas": {str(k): 0.0 for k in range(len(prims))}}
        if not self.opciones["vinculo_proyeccion"] or ref is None:
            prims, datos = self.b.derivar_proyeccion(datos, prims), None
        return self.b.agregar_proyeccion(prims, puntos, self.construccion, datos)

    def proyectar_eje(self):
        """Fusion: Project Axis; proyecta el eje elegido en la paleta, como línea o punto si es perpendicular."""
        from ..timeline import entidades as ent
        try:
            if self.plano is None:
                raise ErrorBoceto("El boceto no tiene plano para proyectar el eje.")
            eje, ref = self._eje_perfil_giratorio()
        except (ErrorBoceto, ent.ErrorReferencia) as e:
            self.mensaje.emit(str(e))
            return False
        return self.aplicar_cambio(lambda: self._agregar_eje_proyectado(eje, ref), anclar=False)

    def perfil_giratorio_forma(self, forma, ref=None):
        """Perfil giratorio (Fusion: Proyectar › Spun Profile) de una forma OCC alrededor del eje de la paleta
        (X, Y o Z del origen, o la arista elegida), con la tolerancia, el lado y el vínculo de la paleta."""
        from ..nucleo import geometria as geo
        from ..nucleo.perfiles import proyectar_giro_forma
        from ..timeline import entidades as ent
        o = self.opciones
        try:
            eje, ref_eje = self._eje_perfil_giratorio()
            prims, puntos = proyectar_giro_forma(forma, self.plano, eje, o["tolerancia_giro"], o["invertir_giro"])
        except (geo.ErrorGeometria, ErrorBoceto, ent.ErrorReferencia) as e:
            self.mensaje.emit(str(e))
            return False
        if not prims and not puntos:
            self.mensaje.emit("Eso no deja ningún perfil sobre el plano del boceto.")
            return False
        origen = {"modo": "giro", "refs": [ref], "eje": ref_eje, "tolerancia": o["tolerancia_giro"],
                  "invertir": bool(o["invertir_giro"])}
        if o["contorno_exterior"]:
            from ..api.herramientas_boceto import _eje_en_plano
            origen["contorno"] = _eje_en_plano(self.plano, eje)

        def agregar():
            datos = origen if ref and o["vinculo_proyeccion"] else None
            curvas = prims if datos is not None else self.b.derivar_proyeccion(origen, prims)
            self.b.agregar_proyeccion(curvas, puntos, self.construccion, datos)
            if o["proyectar_eje"]:
                self._agregar_eje_proyectado(eje, ref_eje)
        return self.aplicar_cambio(agregar, anclar=False)

    def _clic_proyectar(self, pos):
        elegir = getattr(self.visor, "elegir_entidad", None) if self.visor is not None else None
        if elegir is None:
            self.mensaje.emit("La vista 3D todavía no permite elegir aristas, caras o cuerpos.")
            return
        h = self.herramienta
        if self._revincular is not None:
            filtros = {"cuerpo", "cara", "arista", "vertice"}
        elif h == "incluir_3d" or (h == "perfil_giratorio" and self.opciones["eje_giro"] == "arista"
                                 and self._eje_giro is None):
            filtros = {"arista", "vertice"} if h == "incluir_3d" else {"arista"}
        elif self.opciones["filtro_proyectar"] == "cuerpos" and h != "perfil_giratorio":
            filtros = {"cuerpo"}
        else:
            filtros = {"cara", "arista", "vertice"} | ({"cuerpo"} if h in ("intersecar", "perfil_giratorio") else set())
        q = self.visor.mapFromGlobal(self.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))))
        info = elegir(QPointF(q), filtros)
        if not info or info.get("forma") is None:
            self.mensaje.emit("Hacé clic en una arista, una cara o un cuerpo del modelo.")
            return
        self._usar_entidad(info)

    def _usar_entidad(self, info):
        """Lo elegido en el modelo (dict de `elegir_entidad`) según la herramienta: re-vincular una proyección
        perdida, el eje o el perfil giratorio, o proyectar / intersecar."""
        h, forma, ref = self.herramienta, info["forma"], info.get("ref")
        if self._revincular is not None:
            return self._revincular_con(forma, ref)
        if h == "perfil_giratorio" and self.opciones["eje_giro"] == "arista" and self._eje_giro is None:
            from ..nucleo import referencias as refs
            firma = refs.firma_arista(forma) if info.get("tipo", "arista") == "arista" else {}
            if firma.get("geom") != "linea":
                self.mensaje.emit("Perfil giratorio: el eje tiene que ser una arista recta.")
                return False
            a, b = (np.array(p, float) for p in firma["extremos"])
            self._eje_giro = ((a, (b - a) / np.linalg.norm(b - a)), ref)
            self.mensaje.emit("Perfil giratorio: eje elegido. Ahora clic en lo que se gira.")
            return True
        if h == "perfil_giratorio":
            ok = self.perfil_giratorio_forma(forma, ref)
        else:
            ok = self.proyectar_forma(forma, "intersecar" if h == "intersecar" else "proyectar", ref)
        if ok:
            self.mensaje.emit(f"{HERRAMIENTAS[h][0]}: listo ({info.get('tipo', 'geometría')}). Seguí eligiendo o Esc.")
        return ok

    # ------------------------------------------------------------ vínculo de proyección (BOC-17)
    def _proyecciones_de(self, ids):
        """Ids de las proyecciones asociativas que tienen alguna de las entidades `ids`."""
        ids = set(ids)
        return [r["id"] for r in self.b.proyecciones if ids & set(r["ids"])]

    def romper_vinculo(self):
        """Romper vínculo (Fusion: Break Link) de las proyecciones de lo seleccionado."""
        pids = self._proyecciones_de(self.seleccion)
        if not pids:
            self.mensaje.emit("Romper vínculo: seleccioná geometría proyectada con vínculo.")
            return False
        return self.tratar_perdidas("break", pids)

    def tratar_perdidas(self, accion, pids):
        """Manage Lost Projections: "break" rompe el vínculo y "delete" borra la geometría de las proyecciones
        `pids` (un solo paso de deshacer)."""
        funcion = self.b.romper_vinculo if accion == "break" else self.b.eliminar_proyeccion
        ok = self.aplicar_cambio(lambda: [funcion(i) for i in pids], anclar=False)
        if ok:
            self.perdidas = [i for i in self.perdidas if i not in pids]
            self.seleccion = [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos]
        return ok

    def revincular(self, pid):
        """Re-vincular (Manage Lost Projections › Re-Link): el próximo clic en el modelo da la geometría nueva."""
        modo = next(r["modo"] for r in self.b.proyecciones if r["id"] == pid)
        self.set_herramienta("intersecar" if modo == "intersect" else "proyectar")
        self._revincular = pid
        self.mensaje.emit("Re-vincular: clic en la geometría del modelo que reemplaza a la perdida (misma forma).")

    def _revincular_con(self, forma, ref):
        from ..nucleo import geometria as geo
        from ..timeline import entidades as ent
        pid = self._revincular
        reg = next(r for r in self.b.proyecciones if r["id"] == pid)
        try:
            if ref is None:
                raise ErrorBoceto("Lo elegido no tiene referencia para re-vincular la proyección.")
            giro = None
            if reg["modo"] == "giro":
                giro = {"eje": ent.como_eje(ent.resolver(reg["eje"], self.estado_referencias())),
                        "tolerancia": reg["tolerancia"], "invertir": reg["invertir"]}
            prims, puntos = ent.proyectar_entidad(ent.Entidad("cuerpo", forma=forma), self.plano, reg["modo"], giro)
        except (geo.ErrorGeometria, ent.ErrorReferencia, ErrorBoceto) as e:
            self.mensaje.emit(str(e))
            return False
        if not self.aplicar_cambio(lambda: self.b.revincular(pid, [ref], prims, puntos), anclar=False):
            return False
        self.perdidas = [i for i in self.perdidas if i != pid]
        self._revincular = None
        self.mensaje.emit("Re-vincular: la proyección sigue ahora a la geometría elegida.")
        return True

    def atenuar_resto(self, activo):
        """«Atenuar el resto» de Administrar proyecciones perdidas: lo que no es una proyección perdida se dibuja
        apagado para ver mejor las perdidas (Fusion: Fade Other Geometry)."""
        self._brillantes = None
        if activo:
            self._brillantes = set(self.seleccion)
            for r in self.b.proyecciones:
                if r["id"] in self.perdidas:
                    self._brillantes.update(r["ids"])
            self._brillantes = self._brillantes or None          # sin perdidas que resaltar no se apaga nada
        self.update()

    def administrar_perdidas(self):
        """Diálogo Manage Lost Projections (lista, re-vincular, romper vínculo, borrar)."""
        from .dialogos_boceto import DialogoPerdidas
        if not self.perdidas:
            self.mensaje.emit("El boceto no tiene proyecciones perdidas.")
            return
        DialogoPerdidas(self).exec()

    # ------------------------------------------------------------ desfase y patrón ya hechos (BOC-14, BOC-16)
    def soltar_desfase(self):
        """Suelta la asociación de los desfases de lo seleccionado (Fusion: borrar el glifo de desfase)."""
        curvas = [i for i in self.seleccion if i in self.b.curvas]

        def soltar():
            hechos = 0
            for i in curvas:
                try:
                    self.b.soltar_desfase(i)
                    hechos += 1
                except ErrorBoceto:          # no es desfase, o ya lo soltó otra curva del mismo desfase
                    pass
            if not hechos:
                raise ErrorBoceto("Soltar desfase: seleccioná una curva de un desfase.")
        return self.aplicar_cambio(soltar, anclar=False)

    def patron_de(self, ids):
        """Id del patrón que tiene alguna de las entidades `ids` (original o copia), o None."""
        ids = set(ids)
        return next((r["id"] for r in self.b.patrones
                     if ids & set(r["ids"]) or any(ids & set(c) for c in r["copias"].values())), None)

    def editar_patron(self, pid=None):
        """Edita un patrón ya hecho con su diálogo (cantidades, distancias, direcciones y copias suprimidas). Sin
        `pid`, el patrón de lo seleccionado."""
        from .dialogos_boceto import DialogoPatron
        pid = self.patron_de(self.seleccion) if pid is None else pid
        if pid is None:
            self.mensaje.emit("Editar patrón: seleccioná una curva del patrón (o doble clic en su glifo).")
            return False
        dialogo = DialogoPatron(self.b, next(r for r in self.b.patrones if r["id"] == pid), self)
        if dialogo.exec() != QDialog.Accepted:
            return False
        cambios = dialogo.cambios()
        perdidas = []
        ok = self.aplicar_cambio(lambda: perdidas.extend(self.b.editar_patron(pid, **cambios)), anclar=False)
        if ok and perdidas:
            QMessageBox.warning(self, "Editar patrón", "Se borraron porque su copia ya no existe:\n" + "\n".join(perdidas))
        return ok

    # ------------------------------------------------------------ AutoConstrain, tipo de línea, texto
    def auto_restringir(self, **opciones):
        """Restringir automáticamente: agrega restricciones y cotas hasta dejarlo totalmente restringido.
        `opciones`: las de `auto_restringir` del solver (tipos, tolerancias, límite, datum, excluir)."""
        agregado = {}

        def hacer():
            agregado["lista"] = auto_restringir(self.b, self.valores_cotas(), **opciones)
        if self.aplicar_cambio(hacer):
            n = len(agregado.get("lista", []))
            estado = "totalmente restringido" if self.resultado.gdl == 0 else f"quedan {self.resultado.gdl} GDL"
            self.mensaje.emit(f"Restringir automáticamente: {n} restricciones/cotas agregadas ({estado}).")
            return agregado["lista"]
        return []

    def set_previa_auto(self, lista):
        """Actualiza las restricciones y cotas sugeridas que se dibujan en violeta."""
        self.previa_auto = lista
        self.update()

    def auto_restringir_dialogo(self):
        """AutoConstrain con el diálogo de resultados (BOC-5); el punto seleccionado, si hay uno, es el datum."""
        from .dialogo_autorestringir import ELEGIR_DATUM, DialogoAutoRestringir
        if not self.b.curvas and not self.b.puntos:
            self.mensaje.emit("Restringir automáticamente: el boceto está vacío.")
            return []
        puntos = [i for i in self.seleccion if i in self.b.puntos]
        try:
            dialogo = DialogoAutoRestringir(self.b, self.valores_cotas(), puntos[0] if len(puntos) == 1 else None, self)
        except (ErrorBoceto, ErrorExpresion) as e:
            self.mensaje.emit(str(e))
            return []
        dialogo.previa.connect(self.set_previa_auto)
        try:
            resultado = dialogo.resultado()
            self.set_previa_auto(resultado.sugerencias[:dialogo.cantidad.value()] if resultado is not None else [])
            codigo = dialogo.exec()
            while codigo == ELEGIR_DATUM:            # «Elegir en el lienzo»: el diálogo vuelve con el punto elegido
                pid = self.elegir_punto_en_lienzo("AutoConstrain: hacé clic en el punto datum (Esc cancela).")
                if pid is not None:
                    dialogo.fijar_datum(pid)
                codigo = dialogo.exec()
            aceptado = codigo == QDialog.Accepted
        finally:
            self.set_previa_auto([])
        return self.auto_restringir(**dialogo.opciones()) if aceptado else []

    def elegir_punto_en_lienzo(self, aviso="Hacé clic en un punto del boceto (Esc cancela)."):
        """Espera el próximo clic sobre un punto del boceto y devuelve su id (None con Esc, clic derecho o si el
        lienzo se oculta). Lo usa AutoConstrain para el datum, con su diálogo cerrado mientras tanto."""
        self._eligiendo_punto = {"lazo": QEventLoop(), "pid": None}
        self.mensaje.emit(aviso)
        self.setFocus()
        try:
            self._eligiendo_punto["lazo"].exec()
            return self._eligiendo_punto["pid"]
        finally:
            self._eligiendo_punto = None

    def _terminar_eleccion(self, pid=None):
        if self._eligiendo_punto is not None:
            self._eligiendo_punto["pid"] = pid
            self._eligiendo_punto["lazo"].quit()

    def hideEvent(self, e):
        self._terminar_eleccion()                    # salir del boceto no deja colgada la espera del clic
        super().hideEvent(e)

    def alternar_eje(self):
        """Tipo de línea «línea central» (eje): alterna lo seleccionado, o lo que se dibuje."""
        curvas = [i for i in self.seleccion if i in self.b.curvas and not isinstance(self.b.curvas[i], Texto)]
        if not curvas:
            self.eje = not self.eje
            if self.eje:
                self.construccion = False
            self.mensaje.emit("Las curvas nuevas son líneas centrales (eje)." if self.eje
                              else "Las curvas nuevas son normales.")
            return

        def cambiar():
            nuevo = not all(self.b.curvas[i].eje for i in curvas)
            for i in curvas:
                self.b.curvas[i].eje = nuevo
                if nuevo:
                    self.b.curvas[i].construccion = False
        self.aplicar_cambio(cambiar)

    def editar_texto(self, tid, pos):
        t = self.b.curvas[tid]
        # la paleta parte de lo que ya tiene el texto: aceptar sin tocar nada no le cambia la fuente ni la alineación
        self.opciones.update(fuente=t.fuente, negrita=t.negrita, cursiva=t.cursiva, alineacion=t.alineacion,
                             ancla_v=t.ancla_v, altura_texto=t.altura, **{k: getattr(t, k) for k in CURVA_TEXTO},
                             voltear_h=t.voltear_h, voltear_v=t.voltear_v,
                             espaciado=t.espaciado, interlineado=t.interlineado,
                             **{k: getattr(t, k) for k in Texto.TIPOGRAFIA})
        self.opciones.update(marco_texto=bool(t.marco), pivote_texto=None,
                             parametro_texto=t.parametro_texto, valor_parametro_texto="")

        def aceptar(v):
            t = self.b.curvas[tid]
            v = (list(v) + [""] * 5)[:5]
            altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
            espaciado, interlineado = self.evaluar(v[3] or "0"), _numero(v[4] or "1")
            if not v[0].strip():
                raise ErrorBoceto("El texto está vacío.")
            if interlineado <= 0:
                raise ErrorBoceto("El interlineado tiene que ser mayor que cero.")
            _validar_opciones_texto({k: self.opciones[k] for k in Texto.TIPOGRAFIA})
            pivote = self.opciones.get("pivote_texto")
            pivote = self.b.esquina_marco(tid, pivote.removeprefix("corner:")) if pivote else None

            def cambiar():
                texto = v[0].replace("\\n", "\n")
                t.texto, t.altura = texto, altura
                if t.marco:
                    self.b.girar_texto(tid, ang, pivote)
                else:
                    t.angulo = ang
                t.fuente, t.negrita, t.cursiva = self.opciones["fuente"], self.opciones["negrita"], self.opciones["cursiva"]
                t.espaciado, t.interlineado = espaciado, interlineado
                t.alineacion, t.ancla_v = self.opciones["alineacion"], self.opciones["ancla_v"]
                t.voltear_h, t.voltear_v = bool(self.opciones["voltear_h"]), bool(self.opciones["voltear_v"])
                for k in CURVA_TEXTO:
                    setattr(t, k, self.opciones[k])
                for k, tipo in Texto.TIPOGRAFIA.items():
                    setattr(t, k, tipo(self.opciones[k]))
                if t.parametro_texto and self.editar_parametro_texto is not None:
                    t.texto = "{" + t.parametro_texto + "}"
            rehacer = self.pila_rehacer[:]
            if not self.aplicar_cambio(cambiar):
                return False
            texto = v[0].replace("\\n", "\n")
            if t.parametro_texto and self.editar_parametro_texto is not None and texto != self.opciones["valor_parametro_texto"]:
                try:
                    self.editar_parametro_texto(t.parametro_texto, texto)
                except ErrorBoceto as e:
                    self._restaurar(self.historial.pop())
                    self.pila_rehacer[:] = rehacer
                    self.resolver()
                    self.mensaje.emit(str(e))
                    return False
            return True
        self._abrir_entrada(["Texto", "Altura", "∠", "Espaciado", "Interlineado"],
                            [t.texto.replace("\n", "\\n"), formato.numero(t.altura), formato.numero(t.angulo, True),
                             formato.numero(t.espaciado), formato.numero(t.interlineado)], pos, aceptar)
        # como en Fusion, al editar un texto se ven sus opciones (fuente, negrita, alineación…) en la paleta
        self._paleta_texto = True
        self._previa_texto = {"pos": None, "existente": tid, "extra": {}, "caja": None, "reemplazar": False,
                              "cursor": len(t.texto)}
        self._texto_oculto = tid                 # mientras se escribe se ve la previa en vivo en su lugar
        self._conectar_previa_texto()
        self.texto_en_edicion.emit()
        i = self._indice_en_texto(pos)           # el cursor queda donde se hizo doble clic
        if i is not None:
            self._previa_texto["cursor"] = i
            self._actualizar_cursor()

    # ------------------------------------------------------------ texto en vivo (como Fusion)
    # El texto se escribe en el lienzo con un cursor que se mueve: flechas, Inicio / Fin, Ctrl+←/→, el ratón
    # (clic, arrastre, doble clic), selección con Mayús, Ctrl+A, portapapeles y Ctrl+Z / Ctrl+Y.
    # `_previa_texto` guarda: "cursor" (posición 0..n en el texto), "ancla" (otro extremo de la selección o None),
    # "col" (columna que se conserva al subir y bajar), "mapa" (dónde cae cada posición, de `paradas_cursor`) y
    # las pilas "deshacer" / "rehacer".
    def _conectar_previa_texto(self):
        """Cada letra o número que se escribe en la caja redibuja el texto en vivo."""
        for campo in self.entrada.campos:
            campo.textChanged.connect(lambda _t: self.refrescar_previa_texto())
        self.entrada.hacer_movible()
        self.entrada.ocultar_primero()           # el texto se escribe en el cuadro, no en la barra
        d, n = self._previa_texto, len(self._texto_real())
        d.setdefault("cursor", n)
        d.update(ancla=None, col=None, mapa=None, deshacer=[], rehacer=[])
        if d.get("reemplazar") and n:            # el «Texto» de relleno arranca seleccionado: escribir lo reemplaza
            d["cursor"], d["ancla"] = n, 0
        d["cursor"] = min(d["cursor"], n)
        self._caret_on = True
        self._t_caret.start()
        self.setFocus()
        self.mensaje.emit("Escribí el texto directamente en el cuadro. Flechas o clic = mover el cursor; Mayús = "
                          "seleccionar; Enter = línea nueva; Ctrl+Enter o clic afuera = aceptar; Tab = altura y "
                          "demás; Esc = cancelar.")
        self.refrescar_previa_texto()

    def confirmar_texto_pendiente(self):
        """Acepta el texto que está abierto en el cuadro (si hay uno): al salir del boceto, cambiar de herramienta
        o usar el menú radial no se pierde lo escrito."""
        if self._previa_texto is not None and self.entrada is not None:
            self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])

    def _texto_real(self):
        """Lo escrito en el cuadro, con saltos de línea reales (en el campo van como «\\n»)."""
        return self.entrada.campos[0].text().replace("\\n", "\n")

    def _seleccion_texto(self):
        """(desde, hasta) de lo seleccionado en el texto, o None si no hay selección."""
        d = self._previa_texto
        a, c = d["ancla"], d["cursor"]
        return None if a is None or a == c else (min(a, c), max(a, c))

    def _escribir_texto(self, texto, cursor, ancla=None, historial=True):
        """Pone `texto` en el cuadro con el cursor (y la selección) donde se pide; queda para deshacer."""
        d = self._previa_texto
        if historial:
            d["deshacer"].append((self._texto_real(), d["cursor"], d["ancla"]))
            del d["deshacer"][:-200]
            d["rehacer"] = []
        d["cursor"], d["ancla"], d["col"] = cursor, ancla, None
        campo, nuevo = self.entrada.campos[0], texto.replace("\n", "\\n")
        if campo.text() != nuevo:
            campo.setText(nuevo)                 # textChanged vuelve a calcular la vista previa
        else:
            self.refrescar_previa_texto()

    def _reemplazar_rango(self, desde, hasta, nuevo):
        texto = self._texto_real()
        corrimiento = len(nuevo) - (hasta - desde)
        self.opciones["ajustes_kerning"] = [          # el kerning a mano sigue a sus letras; el de lo borrado se va
            [i + (corrimiento if i > hasta else 0), x] for i, x in self.opciones.get("ajustes_kerning", [])
            if i <= desde or i > hasta]
        self._escribir_texto(texto[:desde] + nuevo + texto[hasta:], desde + len(nuevo))

    def _kerning_en(self, i):
        """mm de kerning a mano entre la letra i - 1 y la i."""
        return next((x for j, x in self.opciones.get("ajustes_kerning", []) if j == i), 0.0)

    def ajustar_kerning_par(self, mm):
        """Kerning a mano entre las dos letras que rodean al cursor (mm; 0 lo quita)."""
        d = self._previa_texto
        if d is None or self.entrada is None or d["cursor"] <= 0:
            return
        i = d["cursor"]
        resto = [[j, x] for j, x in self.opciones.get("ajustes_kerning", []) if j != i]
        self.opciones["ajustes_kerning"] = resto + ([[i, float(mm)]] if abs(mm) > 1e-9 else [])
        self.refrescar_previa_texto()

    def aplicar_opcion_texto(self, clave, valor):
        """Tamaño, interletraje o interlineado desde el panel «Carácter»: quedan en las opciones y, con el cuadro
        abierto, en su barra (que es donde se leen al aceptar)."""
        self.opciones[clave] = float(valor)
        if self._previa_texto is not None and self.entrada is not None:
            campo = {"altura_texto": 1, "espaciado": 3, "interlineado": 4}[clave]
            if self.entrada.campos[campo].text() != formato.numero(valor):
                self.entrada.campos[campo].setText(formato.numero(valor))

    def _insertar_en_texto(self, cadena):
        """Escribe `cadena` en el cursor (si hay selección, la reemplaza)."""
        sel = self._seleccion_texto()
        cur = self._previa_texto["cursor"]
        self._reemplazar_rango(*(sel if sel else (cur, cur)), cadena)

    def _deshacer_texto(self, rehacer=False):
        d = self._previa_texto
        pila, otra = (d["rehacer"], d["deshacer"]) if rehacer else (d["deshacer"], d["rehacer"])
        if pila:
            otra.append((self._texto_real(), d["cursor"], d["ancla"]))
            texto, cursor, ancla = pila.pop()
            self._escribir_texto(texto, cursor, ancla, historial=False)

    def _mover_cursor(self, destino, extender=False, col=None):
        """Lleva el cursor a `destino`; con `extender` (Mayús) deja la selección desde donde estaba."""
        d = self._previa_texto
        if extender:
            if d["ancla"] is None:
                d["ancla"] = d["cursor"]
        else:
            d["ancla"] = None
        d["cursor"], d["col"] = destino, col
        self._caret_on = True
        self._t_caret.start()
        self._actualizar_cursor()
        self.update()

    def _vertical_texto(self, cur, delta):
        """Posición del cursor una línea más arriba (-1) o abajo (+1), en la misma columna; (posición, columna)."""
        d = self._previa_texto
        info = d.get("mapa")
        if not info:
            return (0 if delta < 0 else len(self._texto_real())), None
        k = info["linea_de"][cur] + delta
        if k < 0:
            return 0, None
        if k >= len(info["lineas"]):
            return len(info["paradas"]) - 1, None
        ux, uy = info["dir"]

        def columna(i):
            x, y = info["paradas"][i][0]
            return x * ux + y * uy
        col = d["col"] if d["col"] is not None else columna(cur)
        ini, fin = info["lineas"][k]
        return min(range(ini, fin + 1), key=lambda i: abs(columna(i) - col)), col

    def _teclado_en_texto(self, e):
        """Teclas con el cuadro de texto abierto: editan el texto del lienzo en la posición del cursor. True si las
        atendió."""
        d = self._previa_texto
        if d is None or self.entrada is None:
            return False
        k, mods = e.key(), e.modifiers()
        ctrl, mayus = bool(mods & Qt.ControlModifier), bool(mods & Qt.ShiftModifier)
        if k == Qt.Key_Escape:
            self.cancelar()
            return True
        texto = self._texto_real()
        n = len(texto)
        cur = min(max(d["cursor"], 0), n)
        sel = self._seleccion_texto()
        info = d.get("mapa")
        linea = info["lineas"][info["linea_de"][cur]] if info else (0, n)
        if k in (Qt.Key_Return, Qt.Key_Enter):
            if ctrl:
                self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])
            else:
                self._insertar_en_texto("\n")
        elif k in (Qt.Key_Left, Qt.Key_Right) and mods & Qt.AltModifier and not ctrl:
            paso = 0.02 * max(self.opciones.get("altura_texto", 5.0), 0.1)         # Alt+←/→: kerning del cursor
            self.ajustar_kerning_par(self._kerning_en(cur) + (-paso if k == Qt.Key_Left else paso))
        elif k == Qt.Key_Left:
            if sel and not mayus and not ctrl:
                self._mover_cursor(sel[0])
            else:
                self._mover_cursor(max(_inicio_palabra(texto, cur) if ctrl else cur - 1, 0), mayus)
        elif k == Qt.Key_Right:
            if sel and not mayus and not ctrl:
                self._mover_cursor(sel[1])
            else:
                self._mover_cursor(min(_fin_palabra(texto, cur) if ctrl else cur + 1, n), mayus)
        elif k in (Qt.Key_Up, Qt.Key_Down):
            destino, col = self._vertical_texto(cur, -1 if k == Qt.Key_Up else 1)
            self._mover_cursor(destino, mayus, col)
        elif k == Qt.Key_Home:
            self._mover_cursor(0 if ctrl else linea[0], mayus)
        elif k == Qt.Key_End:
            self._mover_cursor(n if ctrl else linea[1], mayus)
        elif k == Qt.Key_Backspace:
            if sel:
                self._reemplazar_rango(*sel, "")
            elif cur > 0:
                self._reemplazar_rango(_inicio_palabra(texto, cur) if ctrl else cur - 1, cur, "")
        elif k == Qt.Key_Delete:
            if sel:
                self._reemplazar_rango(*sel, "")
            elif cur < n:
                self._reemplazar_rango(cur, _fin_palabra(texto, cur) if ctrl else cur + 1, "")
        elif ctrl and k == Qt.Key_A:
            d["ancla"] = 0
            self._mover_cursor(n, True)
        elif ctrl and k in (Qt.Key_C, Qt.Key_X):
            if sel:
                QApplication.clipboard().setText(texto[sel[0]:sel[1]])
                if k == Qt.Key_X:
                    self._reemplazar_rango(*sel, "")
        elif ctrl and k == Qt.Key_V:
            pegado = QApplication.clipboard().text().replace("\r\n", "\n").replace("\r", "\n")
            pegado = pegado.replace("\t", "    ")
            self._insertar_en_texto("".join(c for c in pegado if c == "\n" or c.isprintable()))
        elif ctrl and k in (Qt.Key_Z, Qt.Key_Y):
            self._deshacer_texto(rehacer=k == Qt.Key_Y or mayus)
        elif e.text() and e.text().isprintable() and (not ctrl or mods & Qt.AltModifier):   # AltGr = Ctrl+Alt
            self._insertar_en_texto(e.text())
        else:
            return False
        return True

    def _indice_en_texto(self, pos):
        """Posición del texto (0..n) más cercana al punto de pantalla `pos`; None si todavía no hay mapa."""
        info = (self._previa_texto or {}).get("mapa")
        if not info:
            return None
        x, y = self.a_mm(pos)
        mejor, menor = None, None
        for i, (a, b) in enumerate(info["paradas"]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            largo2 = dx * dx + dy * dy
            t = 0.0 if largo2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / largo2))
            dist = math.hypot(x - (a[0] + t * dx), y - (a[1] + t * dy))
            if menor is None or dist < menor:
                mejor, menor = i, dist
        return mejor

    def _sobre_texto(self, pos):
        """True si el punto de pantalla cae sobre el texto que se escribe (o su cuadro): ahí el clic mueve el cursor;
        afuera, acepta el texto."""
        d = self._previa_texto
        if d is None or self.entrada is None:
            return False
        info = d.get("mapa")
        x, y = self.a_mm(pos)
        margen = 6.0 / max(self.px_por_mm(), 1e-6)
        cajas = [c for c in (d.get("caja"), info and info.get("caja")) if c]
        return any(c[0] - margen <= x <= c[2] + margen and c[1] - margen <= y <= c[3] + margen for c in cajas)

    def _clic_en_texto(self, pos, mods):
        """Clic dentro del texto que se escribe: el cursor va ahí; Mayús extiende la selección; arrastrar selecciona."""
        d = self._previa_texto
        i = self._indice_en_texto(pos)
        if i is None:
            return
        if mods & Qt.ShiftModifier:
            if d["ancla"] is None:
                d["ancla"] = d["cursor"]
        else:
            d["ancla"] = i
        d["cursor"], d["col"] = i, None
        self._arrastre_texto = True
        self._caret_on = True
        self._t_caret.start()
        self._actualizar_cursor()
        self.update()

    def _seleccionar_palabra(self, pos):
        i = self._indice_en_texto(pos)
        if i is None:
            return
        d = self._previa_texto
        d["ancla"], d["cursor"] = _palabra_en(self._texto_real(), i)
        d["col"] = None
        self._actualizar_cursor()
        self.update()

    def _actualizar_cursor(self):
        """Pone el cursor y la selección (cuadriláteros) según el mapa del texto y la posición guardada."""
        d = self._previa_texto
        info = d.get("mapa") if d else None
        self._sel_texto = []
        if not info:
            self._caret = None
            return
        paradas, n = info["paradas"], len(info["paradas"]) - 1
        d["cursor"] = cur = min(max(d["cursor"], 0), n)
        self._caret = paradas[cur]
        if d.get("valores"):
            self.texto_valores.emit(*d["valores"], self._kerning_en(cur))
        sel = self._seleccion_texto()
        if sel:
            desde, hasta = sel[0], min(sel[1], n)
            for ini, fin in info["lineas"]:
                a, b = max(desde, ini), min(hasta, fin)
                if a < b:
                    self._sel_texto.append([paradas[a][0], paradas[b][0], paradas[b][1], paradas[a][1]])

    def _texto_en_vivo(self, texto, altura, ang, esp, inter):
        """El Texto con lo escrito y las opciones de la paleta (sin tocar el boceto): de ahí salen los contornos
        de la vista previa y el mapa del cursor."""
        d, o = self._previa_texto, self.opciones
        tipografia = {k: o[k] for k in Texto.TIPOGRAFIA}
        if d["existente"] is not None:
            t = copy.copy(self.b.curvas[d["existente"]])
            if t.marco:
                a, b, c = map(self.b.coords, t.puntos())
                pivote = o.get("pivote_texto")
                px, py = self.b.esquina_marco(t.id, pivote.removeprefix("corner:")) if pivote else a
                giro = math.radians(ang) - math.atan2(b[1] - a[1], b[0] - a[0])
                cos, sin = math.cos(giro), math.sin(giro)
                esquinas = [(px + (x - px) * cos - (y - py) * sin,
                             py + (x - px) * sin + (y - py) * cos) for x, y in (a, b, c)]
                t.punto, t.marco = esquinas[0], esquinas[1:]
            t.texto, t.altura, t.angulo = texto, altura, ang
            t.fuente, t.negrita, t.cursiva = o["fuente"], o["negrita"], o["cursiva"]
            t.espaciado, t.interlineado = esp, inter
            t.alineacion, t.ancla_v = o["alineacion"], o["ancla_v"]
            t.voltear_h, t.voltear_v = bool(o["voltear_h"]), bool(o["voltear_v"])
            for k, v in tipografia.items():
                setattr(t, k, v)
            for k in CURVA_TEXTO:
                setattr(t, k, o[k])
            return t
        extra = {"alineacion": o["alineacion"], "ancla_v": o["ancla_v"], "voltear_h": o["voltear_h"],
                 "voltear_v": o["voltear_v"]} | d["extra"]
        if "camino" in d["extra"]:
            extra |= {k: o[k] for k in CURVA_TEXTO}
        return Texto(0, d["pos"], texto, o["fuente"], altura, ang, o["negrita"], o["cursiva"], espaciado=esp,
                     interlineado=inter, **extra, **tipografia)

    def _mapa_cursor(self, t, P, ang):
        """Mapa de posiciones del texto `t` para el cursor: ver `paradas_cursor` (más `dir` y `caja`)."""
        prim_camino = None
        if t.camino is not None and t.camino != t.id and t.camino in self.b.curvas \
                and not isinstance(self.b.curvas[t.camino], Texto):
            base = primitivas_entidad(self.b.curvas[t.camino], P)
            prim_camino = base[0] if base else None
        info = paradas_cursor(t, P(t.punto), prim_camino)
        if info is None:
            return None
        a = math.radians(ang)
        info["dir"] = (math.cos(a), math.sin(a))
        puntos = [q for seg in info["paradas"] for q in seg]
        info["caja"] = (min(q[0] for q in puntos), min(q[1] for q in puntos),
                        max(q[0] for q in puntos), max(q[1] for q in puntos))
        return info

    def _parpadeo(self):
        self._caret_on = not self._caret_on
        self.update()

    def refrescar_previa_texto(self):
        """Recalcula los contornos del texto con lo escrito en la caja y con las opciones de la paleta, y deja el
        cursor y la selección donde van."""
        d, e = self._previa_texto, self.entrada
        if d is None or e is None:
            return
        v = ([c.text() for c in e.campos] + [""] * 5)[:5]
        polis, info = [], None
        self._caret_on = True
        self._t_caret.start()         # al escribir el cursor queda fijo y vuelve a parpadear
        try:
            texto = v[0].replace("\\n", "\n")
            altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
            esp, inter = self.evaluar(v[3] or "0"), _numero(v[4] or "1")
            if altura > 0 and inter > 0:
                t = self._texto_en_vivo(texto, altura, ang, esp, inter)

                def P(q):
                    return q if isinstance(q, tuple) else self.b.coords(q)
                if texto.strip():
                    polis = [list(puntos_primitiva(prim)) for prim in primitivas_entidad(t, P, curvas=self.b.curvas)]
                info = self._mapa_cursor(t, P, ang)
                if info is not None and polis:      # la caja también cubre las letras (p. ej. los subrayados)
                    xs = [q[0] for poli in polis for q in poli]
                    ys = [q[1] for poli in polis for q in poli]
                    c = info["caja"]
                    info["caja"] = (min(c[0], min(xs)), min(c[1], min(ys)), max(c[2], max(xs)), max(c[3], max(ys)))
        except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError, KeyError):
            polis, info = [], None          # mientras se escribe un valor a medias, no se dibuja nada
        d["mapa"] = info
        self._previa_polis = polis
        try:                                  # lo de la barra pasa a las opciones (y de ahí al panel)
            alt, esp, inter = self.evaluar(v[1] or "5"), self.evaluar(v[3] or "0"), _numero(v[4] or "1")
            if alt > 0 and inter > 0:
                d["valores"] = (alt, esp, inter)
                if not d.get("caja"):
                    self.opciones["altura_texto"] = alt
                self.opciones["espaciado"], self.opciones["interlineado"] = esp, inter
        except (ErrorExpresion, ValueError, ZeroDivisionError, KeyError):
            pass
        self._actualizar_cursor()
        self.update()

    # ------------------------------------------------------------ entrada dinámica y cotas en pantalla
    def _abrir_entrada(self, etiquetas, textos, pos, al_aceptar, asas=None):
        """Barra de valores de la herramienta. `asas`: (asas, tipos, previa) de `ui/asas_boceto.py`: se pueden tirar con
        el ratón y escriben en las cajas."""
        self._cerrar_entrada()
        self._texto_inicial = textos[0] if textos else None
        self.entrada = EntradaValor(etiquetas, textos, self)

        def aceptar(valores):
            try:
                ok = al_aceptar(valores)
            except (ErrorExpresion, ValueError, ErrorBoceto) as e:
                self.mensaje.emit(str(e))
                self.entrada.marcar_error()
                return
            if ok is not False:
                self._cerrar_entrada()
        self.entrada.aceptado.connect(aceptar)
        self.entrada.cancelado.connect(self._cerrar_entrada)
        if asas is not None:
            from .asas_boceto import GestorAsas2D
            self._asas = GestorAsas2D(self, self.entrada, *asas)
        self.entrada.abrir(pos)

    def _cerrar_entrada(self):
        if self._asas is not None:
            self._asas.cerrar()
            self._asas = None
        if self.entrada is not None:
            entrada, self.entrada = self.entrada, None
            # Se sueltan antes las funciones conectadas (cierres que apuntan al Lienzo): con la caja
            # pendiente de deleteLater, ese ciclo hacía abortar a Qt si el Lienzo se borraba primero.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                for senal in [entrada.aceptado, entrada.tabulado, entrada.cancelado] + [c.textChanged for c in entrada.campos]:
                    try:
                        senal.disconnect()
                    except (RuntimeError, TypeError):
                        pass
            entrada.hide()
            entrada.deleteLater()
            self.setFocus()
            if self.herramienta == "texto":
                self.clics = []              # cancelar (Esc) también descarta la esquina del cuadro
            self.update()
        if self._previa_texto is not None:
            self._previa_texto, self._previa_polis, self._texto_oculto = None, [], None
            self._caret, self._sel_texto, self._arrastre_texto = None, [], False
            self._t_caret.stop()
            self.unsetCursor()
            self.update()
        if self._paleta_texto:
            self._paleta_texto = False
            self.herramienta_cambiada.emit(self.herramienta)     # la paleta vuelve a las opciones de la herramienta
        self._editando = None
        self._cota_editada = self._cota_previa = self._cota_abierta = None
        self._cita_sobre = None

    def _entrada_dinamica(self, primera):
        """Entrada escrita de las herramientas sin cajas de valor (círculo de 2 tangentes, mover/copiar)."""
        h, pos = self.herramienta, self._pos_cursor
        if h == "circulo_2t":
            lineas = list(self.picks)

            def aceptar(v):
                r = self.evaluar(v[0])
                return self._aplicar_y_limpiar(lambda: self.b.agregar_circulo_tangente(lineas, self.cursor, r, None,
                                                                                       self.construccion))
            self._abrir_entrada(["R"], [primera], pos, aceptar)
        elif h == "mover" and self.fase == "destino":
            ids = self._seleccion_util()
            self._abrir_entrada(["ΔX", "ΔY", "∠"], [primera, "0", "0"], pos,
                                lambda v: self._mover(ids, self.evaluar(v[0] or "0"), self.evaluar(v[1] or "0"),
                                                      self.evaluar(v[2] or "0", ANGULO)))

    # ------------------------------------------------------------ cotas en vivo (cajas de valor de Fusion)
    # Mientras se dibuja, junto a la vista previa se muestran cajas con lo que mide la geometría (con su
    # línea de cota provisional). La activa tiene borde azul y el texto seleccionado; Tab pasa a la otra.
    # Lo que se escribe queda BLOQUEADO (candadito): el ratón ya no lo cambia. Enter o clic confirman y
    # cada valor escrito se convierte en una cota de boceto.
    def _reiniciar_vivo(self):
        if self._editando is not None:
            self._cerrar_entrada()
        self._bloqueos, self._activo, self._editando, self._sentido_vivo = {}, 0, None, None

    def _claves_vivas(self):
        """Claves de las cajas del paso actual de la herramienta (sin depender del ratón)."""
        h, n = self.herramienta, len(self.clics)
        if h not in VIVAS or not n or self._tangente is not None:
            return []
        if h == "linea":
            return ["largo", "angulo"]
        if h in ("rectangulo", "rectangulo_centro"):
            return ["ancho", "alto"] if n == 1 else []
        if h == "rectangulo_3p":
            return {1: ["ancho"], 2: ["alto"]}.get(n, [])
        if h == "circulo":
            return ["diametro"] if n == 1 else []
        if h == "arco":
            return {1: ["cuerda"], 2: ["radio"]}.get(n, [])
        if h == "arco_centro":
            return {1: ["radio"], 2: ["barrido"]}.get(n, [])
        if h == "circulo_2p":
            return ["diametro"] if n == 1 else []
        if h == "linea_medio":
            return ["largo", "angulo"] if n == 1 else []
        if h == "elipse":
            return {1: ["radio_mayor", "angulo"], 2: ["radio_menor"]}.get(n, [])
        if h == "arco_tangente":
            return ["radio"] if n == 1 and self._tangente_de(self.clics[0][0]) is not None else []
        if h == "poligono_arista":
            return ["largo", "angulo", "lados"] if n == 1 else []
        if h.startswith("poligono_"):
            return ["radio", "lados"] if n == 1 else []
        if h in RANURAS_RECTAS:
            return {1: ["largo", "angulo"], 2: ["ancho"]}.get(n, [])
        return ["ancho"] if n == 3 else []                 # ranuras de arco: el ancho en el último paso

    def _tangente_de(self, pid):
        """(punto, dirección unitaria de salida) de la curva abierta que termina en `pid`; None si no hay."""
        curvas = self._curvas_con_extremo(pid) if pid is not None else []
        return self.b._salida_extremo(curvas[0], pid) if curvas else None

    def _evaluar_campo(self, clave, texto):
        if clave == "lados":
            n = int(round(_numero(texto)))
            if not 3 <= n <= 64:
                raise ErrorBoceto("El polígono necesita entre 3 y 64 lados.")
            return n
        valor = self.evaluar(texto, ANGULO if clave in ANGULARES else LONGITUD)
        if clave not in ANGULARES:          # lo escrito se vuelve cota: mayor que cero y hasta 1 km, igual que al editarla
            validar_valor_cota(clave if clave in ("radio", "diametro") else "distancia", valor)
        return valor

    def _valores_bloqueados(self):
        """Valores fijados (lo escrito); la caja que se está escribiendo ya manda mientras se escribe."""
        valores = {k: v for k, (_t, v) in self._bloqueos.items()}
        if self._editando is not None and self.entrada is not None:
            try:
                valores[self._editando] = self._evaluar_campo(self._editando, self.entrada.campos[0].text())
            except (ErrorExpresion, ErrorBoceto, ValueError, KeyError):
                pass
        return valores

    def _bloquear(self, clave, texto, valor):
        self._bloqueos[clave] = (texto.strip(), valor)
        if clave == "lados":
            self.lados = int(valor)
            self.herramienta_cambiada.emit(self.herramienta)      # la paleta muestra los lados nuevos

    def _linea_previa(self):
        """Línea anterior de la cadena (el ángulo se mide contra ella, como en Fusion)."""
        if self.herramienta != "linea" or not self.clics or self._ultima_linea not in self.b.curvas:
            return None
        junta = self.clics[-1][0]
        ln = self.b.curvas[self._ultima_linea]
        return self._ultima_linea if junta is not None and junta in (ln.p1, ln.p2) else None

    def _atras_previa(self):
        """Dirección (unitaria) que va de la unión hacia el otro extremo de la línea anterior."""
        previa = self._linea_previa()
        if previa is None:
            return None
        junta = self.clics[-1][0]
        ln = self.b.curvas[previa]
        a, o = self.b.coords(junta), self.b.coords(ln.p1 if ln.p2 == junta else ln.p2)
        return _unitario(o[0] - a[0], o[1] - a[1])

    def _sentido_barrido(self):
        """Arco de punto central: +1 antihorario / -1 horario, según hacia dónde va el ratón (arco corto)."""
        if len(self.clics) < 2 or self.cursor is None:
            return 1
        c, ini, cur = self.clics[0][1], self.clics[1][1], self.cursor
        a0 = math.atan2(ini[1] - c[1], ini[0] - c[0])
        a1 = math.atan2(cur[1] - c[1], cur[0] - c[0])
        return 1 if _barrido(a0, a1) <= math.pi else -1

    @staticmethod
    def _a_distancia_de_recta(cur, a, b, distancia):
        """Lleva `cur` a `distancia` de la recta ab, del lado en que está."""
        u = _unitario(b[0] - a[0], b[1] - a[1])
        n = (-u[1], u[0])
        d = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
        s = 1 if d >= 0 else -1
        return (cur[0] + (s * distancia - d) * n[0], cur[1] + (s * distancia - d) * n[1])

    @staticmethod
    def _punto_arco_radio(a, b, cur, radio):
        """Arco de 3 puntos con el radio escrito: el punto medio del arco, del lado del ratón."""
        c = math.dist(a, b)
        if c < 1e-9:
            return cur
        radio = max(radio, c / 2)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        u = _unitario(b[0] - a[0], b[1] - a[1])
        n = (-u[1], u[0])
        lado = 1 if (cur[0] - m[0]) * n[0] + (cur[1] - m[1]) * n[1] >= 0 else -1
        h = math.sqrt(max(radio * radio - c * c / 4, 0.0))
        circ = circunferencia_3_puntos(a, cur, b)
        mayor = circ is not None and ((circ[0] - m[0]) * n[0] + (circ[1] - m[1]) * n[1]) * lado > 0
        k = h * (lado if mayor else -lado)
        centro = (m[0] + n[0] * k, m[1] + n[1] * k)
        return (centro[0] + n[0] * lado * radio, centro[1] + n[1] * lado * radio)

    def _direccion_angulo(self, u, grados):
        atras = self._atras_previa()
        t = math.radians(grados)
        if atras is None:
            return (math.cos(t), math.sin(t))
        return max((_rotar(atras, t), _rotar(atras, -t)), key=lambda d: d[0] * u[0] + d[1] * u[1])

    def _aplicar_bloqueos(self, cur):
        """El punto que manda el ratón, corregido para respetar los valores escritos del paso actual."""
        claves = self._claves_vivas()
        vals = {k: v for k, v in self._valores_bloqueados().items() if k in claves}
        if cur is None or not vals:
            return cur
        h = self.herramienta
        pts = [q for _, q in self.clics]
        a = pts[-1] if h == "linea" else pts[0]
        u = _unitario(cur[0] - a[0], cur[1] - a[1])

        def desde(base, d, largo):
            return (base[0] + d[0] * largo, base[1] + d[1] * largo)
        if h == "linea":
            if "angulo" in vals:
                d = self._direccion_angulo(u, vals["angulo"])
                largo = vals.get("largo", max((cur[0] - a[0]) * d[0] + (cur[1] - a[1]) * d[1], 0.0))
                return desde(a, d, largo)
            return desde(a, u, vals["largo"])
        if h in ("rectangulo", "rectangulo_centro"):
            k = 1.0 if h == "rectangulo" else 0.5
            x, y = cur
            if "ancho" in vals:
                x = a[0] + (1 if cur[0] >= a[0] else -1) * k * vals["ancho"]
            if "alto" in vals:
                y = a[1] + (1 if cur[1] >= a[1] else -1) * k * vals["alto"]
            return (x, y)
        if h == "rectangulo_3p":
            return desde(a, u, vals["ancho"]) if len(pts) == 1 else self._a_distancia_de_recta(cur, a, pts[1], vals["alto"])
        if h == "circulo":
            return desde(a, u, vals["diametro"] / 2)
        if h == "arco":
            return desde(a, u, vals["cuerda"]) if len(pts) == 1 else self._punto_arco_radio(a, pts[1], cur, vals["radio"])
        if h == "arco_centro":
            if len(pts) == 1:
                return desde(a, u, vals["radio"])
            ini = pts[1]
            t = math.atan2(ini[1] - a[1], ini[0] - a[0]) + self._sentido_barrido() * math.radians(vals["barrido"])
            return desde(a, (math.cos(t), math.sin(t)), math.dist(a, ini))
        d = self._direccion_angulo(u, vals["angulo"]) if "angulo" in vals else u

        def libre():
            return max((cur[0] - a[0]) * d[0] + (cur[1] - a[1]) * d[1], 0.0)
        if h == "circulo_2p":
            return desde(a, u, vals["diametro"])
        if h == "linea_medio":
            return desde(a, d, vals["largo"] / 2 if "largo" in vals else libre())
        if h == "elipse":
            if len(pts) == 2:
                return self._a_distancia_de_recta(cur, a, pts[1], vals["radio_menor"])
            return desde(a, d, vals["radio_mayor"] if "radio_mayor" in vals else libre())
        if h == "arco_tangente":                 # el final queda sobre el círculo de ese radio, tangente a la curva
            p, s = self._tangente_de(self.clics[0][0])
            n = (-s[1], s[0])
            lado = 1 if (cur[0] - p[0]) * n[0] + (cur[1] - p[1]) * n[1] >= 0 else -1
            c = (p[0] + n[0] * lado * vals["radio"], p[1] + n[1] * lado * vals["radio"])
            return desde(c, _unitario(cur[0] - c[0], cur[1] - c[1]), vals["radio"])
        if h == "poligono_arista":
            if vals.keys() & {"largo", "angulo"}:
                return desde(a, d, vals["largo"] if "largo" in vals else libre())
            return cur
        if h.startswith("poligono_"):
            return desde(a, u, vals["radio"]) if "radio" in vals else cur
        if h in RANURAS_RECTAS:
            if len(pts) == 1:
                return desde(a, d, vals["largo"] / (2 if h == "ranura_punto" else 1) if "largo" in vals else libre())
            ini, fin = self._eje_ranura(h, pts)
            return self._a_distancia_de_recta(cur, ini, fin, vals["ancho"] / 2)
        centro, R = self._arco_ranura(h, pts)
        s = 1 if math.dist(cur, centro) >= R else -1
        return desde(centro, _unitario(cur[0] - centro[0], cur[1] - centro[1]), R + s * vals["ancho"] / 2)

    def _cursor_efectivo(self):
        cur = self.cursor
        if cur is None or not self.clics or self.herramienta not in VIVAS:
            return cur
        return self._aplicar_bloqueos(cur)

    def _campos_vivos(self, cur=None):
        """Las cajas de valor del paso actual, con lo que mide la vista previa (cursor ya corregido)."""
        claves = self._claves_vivas()
        cur = self._cursor_efectivo() if cur is None else cur
        if not claves or cur is None:
            return []
        h = self.herramienta
        pts = [q for _, q in self.clics]
        a = pts[-1] if h == "linea" else pts[0]
        u = _unitario(cur[0] - a[0], cur[1] - a[1])
        campos = []
        if h == "linea":
            campos.append(CampoVivo("largo", math.dist(a, cur), ("lineal", a, cur, None)))
            atras = self._atras_previa()
            if atras is not None:            # ángulo con la línea anterior de la cadena
                t0 = math.atan2(atras[1], atras[0])
                delta = math.atan2(atras[0] * u[1] - atras[1] * u[0], atras[0] * u[0] + atras[1] * u[1])
                campos.append(CampoVivo("angulo", math.degrees(abs(delta)),
                                        ("angular", a, min(t0, t0 + delta), max(t0, t0 + delta), False), True))
            else:                            # ángulo con el eje X del boceto
                ang = math.atan2(u[1], u[0]) % (2 * math.pi)
                campos.append(CampoVivo("angulo", math.degrees(ang), ("angular", a, 0.0, ang, True), True))
        elif h in ("rectangulo", "rectangulo_centro"):
            o = a if h == "rectangulo" else (2 * a[0] - cur[0], 2 * a[1] - cur[1])
            k = (cur[0], o[1])
            campos += [CampoVivo("ancho", abs(cur[0] - o[0]), ("lineal", o, k, cur)),
                       CampoVivo("alto", abs(cur[1] - o[1]), ("lineal", k, cur, o))]
        elif h == "rectangulo_3p":
            if len(pts) == 1:
                campos.append(CampoVivo("ancho", math.dist(a, cur), ("lineal", a, cur, None)))
            else:
                b = pts[1]
                ub = _unitario(b[0] - a[0], b[1] - a[1])
                n = (-ub[1], ub[0])
                d = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
                campos.append(CampoVivo("alto", abs(d), ("lineal", b, (b[0] + n[0] * d, b[1] + n[1] * d), a)))
        elif h == "circulo":
            r = math.dist(a, cur)
            campos.append(CampoVivo("diametro", 2 * r, ("radial", (a[0] - r * u[0], a[1] - r * u[1]), cur)))
        elif h == "arco":
            if len(pts) == 1:
                campos.append(CampoVivo("cuerda", math.dist(a, cur), ("lineal", a, cur, None)))
            else:
                circ = circunferencia_3_puntos(a, cur, pts[1])
                if circ is not None:
                    campos.append(CampoVivo("radio", circ[2], ("radial", (circ[0], circ[1]), cur)))
        elif h == "arco_centro":
            if len(pts) == 1:
                campos.append(CampoVivo("radio", math.dist(a, cur), ("radial", a, cur)))
            else:
                ini = pts[1]
                a0 = math.atan2(ini[1] - a[1], ini[0] - a[0])
                a1 = math.atan2(cur[1] - a[1], cur[0] - a[0])
                s = self._sentido_barrido()
                barrido = _barrido(a0, a1) if s > 0 else _barrido(a1, a0)
                t0, t1 = (a0, a0 + barrido) if s > 0 else (a0 - barrido, a0)
                campos.append(CampoVivo("barrido", math.degrees(barrido), ("angular", a, t0, t1, False), True))
        elif h == "circulo_2p":
            campos.append(CampoVivo("diametro", math.dist(a, cur), ("lineal", a, cur, None)))
        elif h == "linea_medio":
            ini = (2 * a[0] - cur[0], 2 * a[1] - cur[1])
            campos += [CampoVivo("largo", math.dist(ini, cur), ("lineal", ini, cur, None)), self._campo_angulo(a, u)]
        elif h == "elipse":
            if len(pts) == 1:
                campos += [CampoVivo("radio_mayor", math.dist(a, cur), ("radial", a, cur)), self._campo_angulo(a, u)]
            else:
                ue = _unitario(pts[1][0] - a[0], pts[1][1] - a[1])
                n = (-ue[1], ue[0])
                dn = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
                campos.append(CampoVivo("radio_menor", abs(dn), ("lineal", a, (a[0] + n[0] * dn, a[1] + n[1] * dn), pts[1])))
        elif h == "arco_tangente":
            p, s = self._tangente_de(self.clics[0][0])
            n = (-s[1], s[0])
            v = (cur[0] - p[0], cur[1] - p[1])
            alto = v[0] * n[0] + v[1] * n[1]
            if abs(alto) > 1e-9:
                r = (v[0] ** 2 + v[1] ** 2) / (2 * abs(alto))
                lado = 1 if alto > 0 else -1
                campos.append(CampoVivo("radio", r, ("radial", (p[0] + n[0] * lado * r, p[1] + n[1] * lado * r), cur)))
        elif h == "poligono_arista":
            campos += [CampoVivo("largo", math.dist(a, cur), ("lineal", a, cur, None)), self._campo_angulo(a, u),
                       CampoVivo("lados", self.lados, None, entero=True)]
        elif h.startswith("poligono_"):
            campos += [CampoVivo("radio", math.dist(a, cur), ("radial", a, cur)),
                       CampoVivo("lados", self.lados, None, entero=True)]
        elif h in RANURAS_RECTAS:
            if len(pts) == 1:
                ini = (2 * a[0] - cur[0], 2 * a[1] - cur[1]) if h == "ranura_punto" else a
                campos += [CampoVivo("largo", math.dist(ini, cur), ("lineal", ini, cur, None)), self._campo_angulo(a, u)]
            else:
                ini, fin = self._eje_ranura(h, pts)
                ue = _unitario(fin[0] - ini[0], fin[1] - ini[1])
                n = (-ue[1], ue[0])
                d = (cur[0] - ini[0]) * n[0] + (cur[1] - ini[1]) * n[1]
                otro = (cur[0] - 2 * d * n[0], cur[1] - 2 * d * n[1])
                campos.append(CampoVivo("ancho", 2 * abs(d), ("lineal", otro, cur, None)))
        else:
            centro, R = self._arco_ranura(h, pts)
            rc = math.dist(cur, centro)
            uc = _unitario(cur[0] - centro[0], cur[1] - centro[1])
            otro = (centro[0] + (2 * R - rc) * uc[0], centro[1] + (2 * R - rc) * uc[1])
            campos.append(CampoVivo("ancho", 2 * abs(rc - R), ("lineal", otro, cur, None)))
        return [c for c in campos if c.clave in claves]

    @staticmethod
    def _campo_angulo(a, u):
        """Caja de ángulo absoluto (contra el eje X del boceto) de la dirección unitaria `u` desde `a`."""
        ang = math.atan2(u[1], u[0]) % (2 * math.pi)
        return CampoVivo("angulo", math.degrees(ang), ("angular", a, 0.0, ang, True), True)

    def _editar_campo_vivo(self, primera):
        """Escribir sobre la caja activa: se abre su campo con lo tecleado (Tab o Enter lo bloquean)."""
        campos = self._campos_vivos()
        if not campos:
            return
        campo = campos[self._activo % len(campos)]
        caja = next((r for c, _t, r, _z in self._disponer_campos(campos) if c.clave == campo.clave), None)
        self._cerrar_entrada()
        self._editando = campo.clave
        ed = self.entrada = EntradaValor([""], [primera], self)
        ed.tab_externo = True
        ed.aceptado.connect(lambda v: self._fin_edicion_viva(v[0], confirmar=True))
        ed.tabulado.connect(lambda texto, paso: self._fin_edicion_viva(texto, paso=paso))
        ed.cancelado.connect(self._cerrar_entrada)
        ed.campos[0].textChanged.connect(lambda _t: self.update())
        esquina = caja.topLeft() if caja is not None else self._pos_cursor + QPointF(14, 10)
        ed.move(int(esquina.x()), int(esquina.y()) - 3)
        ed.show()
        ed.raise_()
        ed.campos[0].setFocus()
        ed.campos[0].deselect()
        ed.campos[0].end(False)               # se sigue escribiendo después del primer dígito
        self.update()

    def _fin_edicion_viva(self, texto, confirmar=False, paso=0):
        """Tab / Enter / clic sobre la caja que se escribe: bloquea el valor (y Enter crea la geometría)."""
        clave = self._editando
        if clave is not None and texto.strip():
            try:
                valor = self._evaluar_campo(clave, texto)
            except (ErrorExpresion, ErrorBoceto, ValueError) as e:
                self.mensaje.emit(str(e))
                if self.entrada is not None:
                    self.entrada.marcar_error()
                return False
            self._bloquear(clave, texto, valor)
        self._cerrar_entrada()
        if confirmar:
            self._confirmar_vivo()
        elif paso:
            n = len(self._claves_vivas()) or 1
            self._activo = (self._activo + paso) % n
        self.update()
        return True

    def _confirmar_vivo(self):
        """Enter: crea con los valores escritos (y el ratón para lo que no se escribió)."""
        if not self.clics:
            return
        self._registrar_clic(None, self.cursor if self.cursor is not None else self.clics[-1][1])

    def _registrar_clic(self, pid, xy):
        """Suma un clic de la herramienta de dibujo, respetando los valores escritos en las cajas."""
        h = self.herramienta
        fase = [k for k in self._claves_vivas() if k in self._bloqueos]
        if fase:
            xy, pid = self._aplicar_bloqueos(xy), None
            if self.inf_actual is not None and math.dist(xy, self.inf_actual.xy) > 1e-9:
                self.inf_actual = None       # la cota escrita manda sobre el ajuste del ratón
            if h == "linea" and "angulo" in fase:
                self.inferencia = None          # el ángulo escrito manda (y da su propia cota o restricción)
            if h == "arco_centro" and "barrido" in fase:
                self._sentido_vivo = self._sentido_barrido() > 0
        bloqueos = dict(self._bloqueos) if h in VIVAS else {}
        previa = self._linea_previa()
        antes, n = set(self.b.curvas), len(self.clics)
        if n == 0:
            self._inf_inicio = self.inf_actual
            self._inf_clics = []
        self._guardar_inferencia_clic(pid, xy)
        if bloqueos:
            self._post_crear = lambda nuevas: self._cotas_de_lo_escrito(h, bloqueos, nuevas, previa)
        if h == "rectangulo_3p" and n == 1:
            self._inf_lado = self.inf_actual
            if self._inf_lado is not None and self._inf_lado.tipo in ("horizontal", "vertical") and not self.inferencia:
                self._inf_lado = None
        if (h in ("linea_medio", "circulo") and n == 1) or (h == "rectangulo_3p" and n == 2):
            inf = self._inf_lado if h == "rectangulo_3p" else self.inf_actual
            if h == "circulo":
                inf = (Inferencia("tangente", inf.xy, inf.objetivo, ("tangente", inf.objetivo))
                       if inf is not None and inf.tipo == "perpendicular" else None)
            elif h == "linea_medio" and inf is not None and inf.tipo in ("horizontal", "vertical") and not self.inferencia:
                inf = None
            if inf is not None and inf.tipo in ("horizontal", "vertical", "tangente", "perpendicular"):
                post_crear = self._post_crear

                def restringir(nuevas):
                    if post_crear is not None:
                        post_crear(nuevas)
                    curva = self.b.curvas[nuevas[0]]
                    self._restringir_inferencias(curva.id, [(curva.p2 if isinstance(curva, Linea) else None, inf)])

                self._post_crear = restringir
        self.clics.append((pid, xy))
        try:
            self._procesar_clics()
        finally:
            self._post_crear = None
            self._sentido_vivo = None
        if h in VIVAS:
            if set(self.b.curvas) != antes or len(self.clics) <= n:
                if set(self.b.curvas) != antes or not self.clics:
                    self._inf_inicio = None
                self._reiniciar_vivo()          # se creó la geometría (o se cortó): cajas nuevas
            else:
                self._activo = 0                # paso siguiente de la misma herramienta

    def _horizontal_o_vertical(self, lineas, bloqueos):
        """Un ángulo escrito de 0°/180° o 90°/270° se vuelve horizontal o vertical en la línea que lo cumple."""
        if "angulo" not in bloqueos:
            return
        ang = math.radians(bloqueos["angulo"][1])
        tipo = "horizontal" if abs(math.sin(ang)) < 1e-9 else "vertical" if abs(math.cos(ang)) < 1e-9 else None
        for lid in lineas:
            (x1, y1), (x2, y2) = self.b._extremos_linea(lid)
            fuera = abs(y2 - y1) if tipo == "horizontal" else abs(x2 - x1)     # lo que se aparta del eje pedido
            if tipo and fuera < 1e-6 * max(math.dist((x1, y1), (x2, y2)), 1.0):
                self.b.agregar_restriccion(tipo, [lid])
                return

    def _cotas_de_lo_escrito(self, h, bloqueos, nuevas, previa):
        """Lo escrito en las cajas se vuelve cota de boceto (como Fusion), sobre la geometría recién creada."""
        texto = {k: t for k, (t, _v) in bloqueos.items()}
        tipos = {k: self.b.curvas[k].tipo for k in nuevas}
        lineas = [k for k in nuevas if tipos[k] == "linea"]
        arcos = [k for k in nuevas if tipos[k] == "arco"]
        circulos = [k for k in nuevas if tipos[k] == "circulo"]
        cota = self.b.agregar_cota
        if h == "linea" and lineas:
            lid = lineas[0]
            if "largo" in texto:
                cota("distancia", [lid], texto["largo"])
            if "angulo" in texto:
                if previa in self.b.curvas:
                    ln, t = self.b.curvas[previa], texto["angulo"]
                    if ln.p2 == self.b.curvas[lid].p1:     # la cota mide el desvío entre las direcciones
                        t = formato.numero(180 - bloqueos["angulo"][1], True) if _es_numero(t) else f"180 - ({t})"
                    cota("angulo", [previa, lid], t)
                else:
                    ang = math.radians(bloqueos["angulo"][1])
                    if abs(math.sin(ang)) < 1e-9:
                        self.b.agregar_restriccion("horizontal", [lid])
                    elif abs(math.cos(ang)) < 1e-9:
                        self.b.agregar_restriccion("vertical", [lid])
        elif h in ("rectangulo", "rectangulo_centro", "rectangulo_3p") and len(lineas) >= 2:
            if "ancho" in texto:
                cota("distancia", [lineas[0]], texto["ancho"])
            if "alto" in texto:
                cota("distancia", [lineas[1]], texto["alto"])
        elif h in ("circulo", "circulo_2p") and circulos and "diametro" in texto:
            cota("diametro", [circulos[0]], texto["diametro"])
        elif h == "linea_medio" and lineas:
            if "largo" in texto:
                cota("distancia", [lineas[0]], texto["largo"])
            self._horizontal_o_vertical(lineas, bloqueos)
        elif h == "elipse" and len(lineas) >= 2:        # los ejes de construcción: la cota es el eje entero
            for clave, lid in (("radio_mayor", lineas[0]), ("radio_menor", lineas[1])):
                if clave in texto:
                    t = texto[clave]
                    cota("distancia", [lid], formato.numero(2 * _numero(t)) if _es_numero(t) else f"2 * ({t})")
            self._horizontal_o_vertical(lineas[:1], bloqueos)
        elif h == "poligono_arista" and lineas:
            if "largo" in texto:
                cota("distancia", [lineas[0]], texto["largo"])
            self._horizontal_o_vertical(lineas, bloqueos)
        elif h == "arco" and arcos:
            arco = self.b.curvas[arcos[0]]
            if "cuerda" in texto:
                cota("distancia", [arco.inicio, arco.fin], texto["cuerda"])
            if "radio" in texto:
                cota("radio", [arcos[0]], texto["radio"])
        elif h in ("arco_centro", "arco_tangente") and arcos and "radio" in texto:
            cota("radio", [arcos[0]], texto["radio"])
        elif h.startswith("poligono_") and circulos and "radio" in texto:
            cota("radio", [circulos[0]], texto["radio"])
        elif h.startswith("ranura_") and arcos:
            self._horizontal_o_vertical(lineas[-1:], bloqueos)
            tapa = min(arcos, key=self.b.radio)            # los extremos: los arcos de radio = medio ancho
            if "ancho" in texto:
                cota("diametro", [tapa], texto["ancho"])
            if "largo" in texto and lineas:
                largo = texto["largo"]
                if h == "ranura_total":                    # la cota va entre centros: largo total − ancho
                    ancho = texto.get("ancho") or formato.numero(2 * self.b.radio(tapa))
                    largo = (formato.numero(_numero(largo) - _numero(ancho)) if _es_numero(largo) and _es_numero(ancho)
                             else f"({largo}) - ({ancho})")
                cota("distancia", [lineas[-1]], largo)      # el eje de construcción, entre los centros

    # ---- dibujo de las cajas y de las cotas provisionales
    def _color_cota(self):
        return COTA_OSCURO if self._oscuro() else COTA_CLARO

    def _color_fondo(self):
        """El color del lienzo detrás del texto de una cota: así el valor se lee sobre cualquier línea."""
        if self.visor is not None or self._oscuro():
            return QColor(temas.color("visor_arriba"))
        return QColor(FONDO_LIENZO)

    def _color_resalte(self):
        """Acento con el que se resalta la cota bajo el ratón (el mismo acento de la app)."""
        return QColor(temas.color("acento"))

    def _trazo_vivo(self, campo):
        """(segmentos, flechas [(punta, desde)], centro de la caja) en px de la cota provisional."""
        if campo.cota is None:
            return None
        tipo = campo.cota[0]
        if tipo == "lineal":
            _, a, b, lado = campo.cota
            pa, pb = self.a_px(*a), self.a_px(*b)
            dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
            largo = math.hypot(dx, dy)
            if largo < 1:
                return [], [], pb + QPointF(36, -22)
            n = QPointF(-dy / largo, dx / largo)
            medio = (pa + pb) / 2
            if lado is not None:
                pl = self.a_px(*lado)
                if (pl.x() - medio.x()) * n.x() + (pl.y() - medio.y()) * n.y() > 0:
                    n = QPointF(-n.x(), -n.y())
            qa, qb = pa + n * 24, pb + n * 24
            return [(pa + n * 3, qa + n * 4), (pb + n * 3, qb + n * 4), (qa, qb)], [(qa, qb), (qb, qa)], (qa + qb) / 2
        if tipo == "angular":
            _, c, t0, t1, referencia = campo.cota
            r = 40 / max(self.px_por_mm(), 1e-9)
            pasos = max(4, int(abs(t1 - t0) / 0.08))
            arco = [self.a_px(c[0] + r * math.cos(t0 + (t1 - t0) * i / pasos), c[1] + r * math.sin(t0 + (t1 - t0) * i / pasos))
                    for i in range(pasos + 1)]
            segmentos = list(zip(arco, arco[1:], strict=False))
            if referencia:                   # el eje de referencia del ángulo (horizontal del boceto)
                segmentos.append((self.a_px(*c), self.a_px(c[0] + 1.4 * r, c[1])))
            tm, r2 = (t0 + t1) / 2, 66 / max(self.px_por_mm(), 1e-9)
            flechas = [(arco[-1], arco[-2]), (arco[0], arco[1])] if abs(t1 - t0) > 0.15 else []
            return segmentos, flechas, self.a_px(c[0] + r2 * math.cos(tm), c[1] + r2 * math.sin(tm))
        _, a, b = campo.cota
        pa, pb = self.a_px(*a), self.a_px(*b)
        dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
        largo = math.hypot(dx, dy) or 1.0
        return [(pa, pb)], [(pb, pa)], pb + QPointF(dx / largo, dy / largo) * 40

    def _disponer_campos(self, campos):
        """[(campo, texto, caja QRectF, trazo)]: dónde va cada caja (sin pisarse)."""
        fm = QFontMetricsF(temas.qfont_cotas(9))
        cur = self._cursor_efectivo() or (0.0, 0.0)
        salida, ocupadas = [], []
        for campo in campos:
            trazo = self._trazo_vivo(campo)
            if trazo is not None:
                centro = trazo[2]
            elif ocupadas:
                centro = ocupadas[-1].center() + QPointF(0, 26)
            else:
                centro = self.a_px(*cur) + QPointF(50, 30)
            texto = texto_valor(campo.valor, campo.angular, campo.entero)
            ancho = fm.horizontalAdvance(texto) + 16 + (14 if campo.clave in self._bloqueos else 0)
            alto = fm.height() + 4              # el recuadro de agarre sigue al tamaño real del texto
            caja = QRectF(centro.x() - ancho / 2, centro.y() - alto / 2, ancho, alto)
            for _ in range(12):
                if not any(caja.intersects(o) for o in ocupadas):
                    break
                caja.translate(0, 24)
            ocupadas.append(caja)
            salida.append((campo, texto, caja, trazo))
        return salida

    @staticmethod
    def _candado(p, x, y):
        p.save()
        p.setPen(QPen(QColor(80, 80, 88), 1.3))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(x + 1.5, y, 6, 8), 0, 180 * 16)
        p.setBrush(QColor(80, 80, 88))
        p.drawRect(QRectF(x, y + 4, 9, 7))
        p.restore()

    def _dibujar_campos_vivos(self, p):
        campos = self._campos_vivos()
        self._cajas_vivas = []
        if not campos:
            return
        color = self._color_cota()
        activo = self._activo % len(campos)
        p.setFont(temas.qfont_cotas(9))
        fm = p.fontMetrics()
        for i, (campo, texto, caja, trazo) in enumerate(self._disponer_campos(campos)):
            self._cajas_vivas.append((campo.clave, caja))
            if trazo is not None:
                p.setPen(QPen(color, 1))
                p.setBrush(color)
                for a, b in trazo[0]:
                    p.drawLine(a, b)
                for punta, desde in trazo[1]:
                    self._flecha(p, punta, desde)
            if campo.clave == self._editando and self.entrada is not None:
                continue                      # encima está el campo donde se escribe
            p.setPen(QPen(AZUL_CAJA, 1.5) if i == activo else QPen(QColor(150, 150, 156), 1))
            p.setBrush(QColor(255, 255, 255))
            p.drawRect(caja)
            zona = QRectF(caja.x() + 7, caja.y() + 3, fm.horizontalAdvance(texto) + 1, 14)
            if i == activo:                   # texto seleccionado: lo que se escriba lo reemplaza
                p.fillRect(zona.adjusted(-2, -1, 2, 1), AZUL_CAJA)
                p.setPen(QColor(255, 255, 255))
            else:
                p.setPen(QColor(30, 30, 34))
            p.drawText(zona, Qt.AlignVCenter | Qt.AlignLeft, texto)
            if campo.clave in self._bloqueos:
                self._candado(p, caja.right() - 14, caja.y() + 4)
        p.setBrush(Qt.NoBrush)

    def _abrir_cota(self, tipo, entidades, pos):
        original = (tipo, list(entidades), pos)
        if tipo in ("radio", "diametro"):
            tipo = self._opc_cota.get("tipo", tipo)             # menú previo: Radio / Diámetro
        previa = Cota(-1, tipo, entidades, "", {})
        if tipo == "distancia" and sum(bool(getattr(self.b.curvas.get(i), "eje", False)) for i in entidades) == 1:
            previa.datos["diametral"] = True        # Fusion: una cota con la línea central es un diámetro
        if self.b.admite_modo(tipo, entidades) and "modo" in self._opc_cota:
            previa.datos["modo"] = self._opc_cota["modo"]       # menú previo: Centro / Tangente
        try:
            self.b._validar_cota(tipo, entidades)
            self.b.ubicar_cota(previa, self.a_mm(pos))  # el clic ubica la línea de cota y su texto (o el cuadrante)
            actual = self.b.medir(previa)
        except ErrorBoceto as e:
            self.mensaje.emit(str(e))
            self.picks = []
            return

        def aceptar(v):
            referencia = self._opc_cota.get("referencia", False)     # una cota de referencia mide: ignora el texto
            nombre, texto = separar_nombre(v[0])                    # «ANCHO=20mm» nombra el parámetro de la cota
            texto = texto or formato.numero(actual, angular=tipo == "angulo")
            self._comprobar_nombre_cota(nombre)
            if not referencia:
                validar_valor_cota(tipo, self.evaluar(texto, _tipo_valor(tipo)))     # −5 o 0: la caja queda en rojo

            def crear():
                cota = self.b.cotas[self.b.agregar_cota(tipo, entidades, texto, previa.datos, referencia=referencia)]
                if nombre:
                    cota.nombre, self._nombradas[nombre] = nombre, cota.id
                if not referencia and self._sobre_restringe(cota.id):   # Fusion: la que sobra entra de referencia
                    cota.referencia, cota.expresion = True, repr(actual)
                    self.mensaje.emit("La cota sobre-restringiría el boceto: se creó como cota de referencia.")
            self.aplicar_cambio(crear)
            self.picks, self._opc_cota = [], {}
            self._esperando_ubicacion = False
        unidad = "°" if tipo == "angulo" else ""
        self._abrir_entrada([TIPOS_COTA[tipo] + (f" ({unidad})" if unidad else "")],
                            [f"{actual:.3f}".rstrip("0").rstrip(".")], pos, aceptar)
        self._cota_abierta = original
        if self.b.ejes_cota(previa) is not None:        # cota lineal: se dibuja con sus líneas mientras se escribe
            self._cota_previa, self._cota_editada = previa, -1

    def _opciones_cota_mantenido(self):
        """Clic derecho mantenido con una cota a medias: abre sus opciones (el clic rápido cancela)."""
        if self._derecho is not None and self.herramienta == "cota" and self.picks:
            _pos, global_ = self._derecho
            self._derecho = None
            self._menu_cota_previa().exec(global_)

    def _menu_cota_previa(self):
        """Clic derecho antes de ubicar la cota (Fusion, «Dimension sketch geometry» › Tips): Driven o Driving,
        Radio o Diámetro, Centro o Tangente. Lo elegido vale para la cota que se está poniendo."""
        m = QMenu(self)
        abierta, opc = self._cota_abierta, self._opc_cota

        def elegir(clave, valor):
            opc[clave] = valor
            if abierta is not None and clave != "referencia":       # tipo y modo cambian lo que se mide
                self._abrir_cota(*abierta)

        def grupo(clave, items, actual):
            for valor, texto in items:
                a = m.addAction(texto, lambda c=clave, x=valor: elegir(c, x))
                a.setCheckable(True)
                a.setChecked(actual == valor)
        grupo("referencia", ((False, "Cota conductora (driving)"), (True, "Cota de referencia (driven)")),
              opc.get("referencia", False))
        if abierta is not None:
            tipo, ents, _ = abierta
            if tipo in ("radio", "diametro"):
                m.addSeparator()
                grupo("tipo", (("radio", "Radio"), ("diametro", "Diámetro")), opc.get("tipo", tipo))
            if self.b.admite_modo(tipo, ents):
                m.addSeparator()
                grupo("modo", (("centro", "Centro"), ("tangente", "Tangente")), opc.get("modo", "centro"))
        return m

    def _nombre_libre(self):
        """Primer dN que ni el documento ni otra cota de este boceto usan (el documento lo respeta al nombrar)."""
        usados = {k.nombre for k in self.b.cotas.values()}
        n = 1
        while f"d{n}" in usados or self._existe_en_documento(f"d{n}"):
            n += 1
        return f"d{n}"

    def _comprobar_nombre_cota(self, nombre, cota=None):
        """El nombre tipeado en la caja («ANCHO=20») tiene que ser válido y estar libre (la caja queda en rojo)."""
        if not nombre or (cota is not None and nombre == cota.nombre):
            return
        validar_nombre(nombre)
        if any(k.nombre == nombre for k in self.b.cotas.values()) or self._existe_en_documento(nombre):
            raise ErrorExpresion(f"Ya existe el parámetro '{nombre}': elegí otro nombre.")

    def _existe_en_documento(self, nombre):
        for tipo in (LONGITUD, ANGULO, ESCALAR):      # el parámetro puede ser de cualquiera de los tres tipos
            try:
                self._evaluar_doc(nombre, tipo)
                return True
            except ErrorExpresion:
                pass
        return False

    def _actualizar_cita(self, pos):
        """Cota bajo el ratón: con una caja de valor abierta se resalta para citarla (Fusion); en Seleccionar, sin
        caja, muestra su cartel «nombre : valor unidad»."""
        citando = self.entrada is not None and (self._cota_abierta is not None or self._cota_editada is not None)
        cid = None
        if citando:
            zona = self._zona_en(pos)
            if zona in self.b.cotas and zona != self._cota_editada:
                cid = zona
        elif self.entrada is None and self.herramienta == "seleccionar" and self._arrastre is None:
            cid = self._zona_sobre if self._zona_sobre in self.b.cotas else None
        if cid == self._cita_sobre:
            return
        self._cita_sobre = cid
        if cid is None:
            QToolTip.hideText()
            if citando:
                self.unsetCursor()
        else:
            cota = self.b.cotas[cid]
            angular = cota.tipo == "angulo"
            try:
                valor = formato.numero(self.b.medir(cota), angular=angular)
            except (ErrorBoceto, KeyError, ZeroDivisionError):
                return
            QToolTip.showText(self.mapToGlobal(pos.toPoint()),
                              f"{cota.nombre or self._nombre_libre()} : {valor}{'°' if angular else ' mm'}")
            if citando:
                self.setCursor(Qt.PointingHandCursor)
        self.update()

    def _citar_cota(self, pos):
        """Fusion: con la caja de valor de una cota abierta, un clic en otra cota pone su nombre (dN) en la
        expresión, en lugar de lo seleccionado. True si el clic se usó así."""
        if self._cota_abierta is None and self._cota_editada is None:
            return False
        cid = self._zona_en(pos)
        cota = self.b.cotas.get(cid)
        if cota is None or cid == self._cota_editada:
            return False
        if not cota.nombre:                  # el documento nombra las cotas nuevas al terminar el boceto: se adelanta
            cota.nombre = self._nombre_libre()
            self._nombradas[cota.nombre] = cid
        campo = self.entrada.campos[0]
        if campo.text() == self._texto_inicial:      # el clic en el lienzo le quitó el foco y la selección al valor
            campo.selectAll()
        campo.insert(cota.nombre)
        campo.setFocus()
        return True

    def _arco_cota(self, c):
        """(vértice, t0, t1) del arco de una cota de ángulo, o None si las líneas son paralelas."""
        try:
            return self.b.arco_angulo(c)
        except (ErrorBoceto, KeyError, ZeroDivisionError):
            return None

    def _sobre_restringe(self, cid):
        """Criterio de la API (BOC-1): la cota driving `cid` debe bajar los GDL sin dejar el boceto en conflicto."""
        valores, sin = self.valores_cotas(), self.b.copia()
        del sin.cotas[cid]
        con = resolver(self.b.copia(), valores)
        return not con.ok or con.gdl >= resolver(sin, valores).gdl

    def alternar_referencia(self, cid):
        """Cota de referencia (driven) ↔ driving, con Mayús + doble clic (BOC-3 la suma al menú de la cota).
        Toma la medida actual; si volver a driving sobre-restringiría, sigue de referencia y avisa."""
        cota = self.b.cotas[cid]

        def cambiar():
            cota.referencia = not cota.referencia
            cota.expresion = repr(self.b.medir(cota))
            if not cota.referencia and self._sobre_restringe(cid):
                raise ErrorBoceto("La cota sobre-restringiría el boceto: sigue como cota de referencia.")
        self.aplicar_cambio(cambiar)

    def _menu_cota(self, cid, pos=None):
        """Clic derecho en una cota (Fusion): editar el valor, renombrar el parámetro, referencia,
        radio/diámetro, centro/tangente y borrar."""
        QToolTip.hideText()
        self._cita_sobre = None
        cota = self.b.cotas[cid]
        m = QMenu(self)
        centro = pos if pos is not None else (self._zonas_cotas.get(cid) or QRectF()).center()
        m.addAction("Editar valor…", lambda: self.editar_cota(cid, centro))
        m.addAction("Renombrar parámetro…", lambda: self.renombrar_cota(cid))
        m.addSeparator()
        a = m.addAction("Cota de referencia", lambda: self.alternar_referencia(cid))
        a.setCheckable(True)
        a.setChecked(cota.referencia)
        m.addSeparator()
        opciones = ((("radio", "Radio"), ("diametro", "Diámetro")) if cota.tipo in ("radio", "diametro") else ())
        for tipo, texto in opciones:
            a = m.addAction(texto, lambda t=tipo: self.aplicar_cambio(lambda: self.b.cambiar_cota(cid, tipo=t)))
            a.setCheckable(True)
            a.setChecked(cota.tipo == tipo)
        if self.b.admite_modo(cota.tipo, cota.entidades):
            for modo, texto in (("centro", "Centro"), ("tangente", "Tangente")):
                a = m.addAction(texto, lambda md=modo: self.aplicar_cambio(lambda: self.b.cambiar_cota(cid, modo=md)))
                a.setCheckable(True)
                a.setChecked(cota.datos.get("modo", "centro") == modo)
        m.addSeparator()
        m.addAction("Borrar", lambda: self.aplicar_cambio(lambda: self.b.eliminar(cid)))
        return m

    def editar_cota(self, cid, pos):
        cota = self.b.cotas[cid]
        if cota.referencia:
            self.mensaje.emit("Es una cota de referencia: mide la geometría. Mayús + doble clic la vuelve driving.")
            return

        def aceptar(v):
            nombre, texto = separar_nombre(v[0])
            self._comprobar_nombre_cota(nombre, cota)
            validar_valor_cota(cota.tipo, self.evaluar(texto, _tipo_valor(cota.tipo)))

            def cambiar():
                cota.expresion = texto
                if nombre:
                    cota.nombre, self._nombradas[nombre] = nombre, cota.id
            self.aplicar_cambio(cambiar)
        self._abrir_entrada([TIPOS_COTA[cota.tipo]], [cota.expresion], pos, aceptar)
        self._cota_editada = cid             # mientras se edita, la caja con borde reemplaza al texto
        zona = self._zonas_cotas.get(cid)
        if zona is not None:
            self.entrada.move(int(zona.left()) - 4, int(zona.top()) - 4)

    def renombrar_cota(self, cid):
        """Menú de la cota: le da un nombre propio (el parámetro que se cita en las expresiones). Un nombre
        inválido o ya usado muestra el error y no cambia nada; es un solo paso de deshacer."""
        cota = self.b.cotas[cid]
        nombre, ok = QInputDialog.getText(self, "Renombrar parámetro", "Nombre del parámetro:",
                                          text=cota.nombre or self._nombre_libre())
        if not ok:
            return
        nombre = nombre.strip()
        try:
            if not nombre:
                raise ErrorExpresion("El nombre del parámetro no puede estar vacío.")
            self._comprobar_nombre_cota(nombre, cota)
        except ErrorExpresion as e:
            self.mensaje.emit(str(e))
            return
        if nombre == cota.nombre:
            return

        def cambiar():
            cota.nombre = nombre
            self._nombradas[nombre] = cota.id
        self.aplicar_cambio(cambiar)

    def _tipo_dos_puntos(self, pos):
        """Tipo de la cota entre los dos puntos elegidos, según dónde esté `pos` (px)."""
        (x1, y1), (x2, y2) = self.b.coords(self.picks[0]), self.b.coords(self.picks[1])
        if self.opcion_cota == "alineada":
            return "distancia"
        if abs(y2 - y1) < 1e-6:
            return "distancia_h"
        if abs(x2 - x1) < 1e-6:
            return "distancia_v"
        medio = self.a_px((x1 + x2) / 2, (y1 + y2) / 2)
        return "distancia_h" if abs(pos.y() - medio.y()) > abs(pos.x() - medio.x()) else "distancia_v"

    def _cota_viva(self):
        """Cota provisional que se dibuja: la que se está escribiendo o, con la herramienta Cota y una línea (o
        dos puntos) ya elegidos, la que sigue al cursor hasta el clic que la ubica."""
        if self._cota_previa is not None:
            return self._cota_previa
        if self.herramienta != "cota" or self.entrada is not None or not self.picks or self._pos_cursor is None:
            return None
        if self._esperando_ubicacion and self.b.tipo_de(self.picks[0]) == "linea":
            previa = Cota(-1, "angulo", list(self.picks), "", {})     # BOC-25: el ángulo del cuadrante del cursor
            self.b.ubicar_cota(previa, self.a_mm(self._pos_cursor))
            return previa
        if self._esperando_ubicacion:
            tipo = self._tipo_dos_puntos(self._pos_cursor)
        elif len(self.picks) == 1 and self.b.tipo_de(self.picks[0]) == "linea":
            tipo = "distancia"
        else:
            return None
        previa = Cota(-1, tipo, list(self.picks), "", {})
        if self.b.ejes_cota(previa) is None:
            return None
        self.b.ubicar_cota(previa, self.a_mm(self._pos_cursor))
        return previa

    def _clic_cota(self, pos):
        ent = self.entidad_en(pos)
        if not self.picks:
            if ent is None:
                return
            t = self.b.tipo_de(ent)
            if t in ("circulo", "arco"):
                self.picks = [ent]
                self._abrir_cota("diametro" if t == "circulo" else "radio", [ent], pos)
            else:
                self.picks = [ent]
            return
        primero, t1 = self.picks[0], self.b.tipo_de(self.picks[0])
        if self._esperando_ubicacion:        # dos puntos: la ubicación decide horizontal / vertical; dos líneas, el ángulo
            tipo = "angulo" if t1 == "linea" else self._tipo_dos_puntos(pos)
            self._abrir_cota(tipo, list(self.picks), pos)
            return
        if ent is None or ent == primero:
            if t1 == "linea":
                self._abrir_cota("distancia", [primero], pos)
            return
        t2 = self.b.tipo_de(ent)
        if t1 == "punto" and t2 == "punto":
            self.picks = [primero, ent]
            self._esperando_ubicacion = True
            self.mensaje.emit("Clic para ubicar la cota (arriba/abajo: horizontal; a un costado: vertical).")
        elif {t1, t2} == {"punto", "linea"}:
            ents = [primero, ent] if t1 == "punto" else [ent, primero]
            self._abrir_cota("distancia", ents, pos)
        elif t1 == "linea" and t2 == "linea":
            d1, d2 = self.b._direccion(primero), self.b._direccion(ent)
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-6:
                self._abrir_cota("distancia", [primero, ent], pos)
            else:                            # Fusion: el ángulo sigue al cursor hasta el clic que elige el cuadrante
                self.picks = [primero, ent]
                self._esperando_ubicacion = True
                self.mensaje.emit("Clic para ubicar la cota de ángulo: se mide el ángulo del lado donde está el cursor.")
        elif {t1, t2} & {"circulo", "arco"} or {t1, t2} == {"punto", "spline"}:
            self._abrir_cota("distancia", [primero, ent], pos)    # al centro; el menú de la cota pasa a tangente
        else:
            self.mensaje.emit("Esa combinación no se puede acotar.")
            self.picks = []

    # ------------------------------------------------------------ restricciones con herramienta
    def _ordenar(self, ids, primero):
        return sorted(ids, key=lambda i: 0 if self.b.tipo_de(i) == primero else 1)

    def aplicar_restriccion(self, tipo, ents):
        """Aplica una restricción a las entidades (en el orden que pide el modelo). Devuelve True si quedó."""
        if tipo == "horizontal_vertical":
            if self.b.tipo_de(ents[0]) == "linea":
                (x1, y1), (x2, y2) = self.b._extremos_linea(ents[0])
                ents = ents[:1]
            else:
                (x1, y1), (x2, y2) = self.b.coords(ents[0]), self.b.coords(ents[1])
            tipo = "horizontal" if abs(x2 - x1) >= abs(y2 - y1) else "vertical"
        elif tipo == "fijo":
            existente = [r.id for r in self.b.restricciones.values() if r.tipo == "fijo" and r.entidades == ents]
            if existente:
                return self.aplicar_cambio(lambda: self.b.eliminar(existente[0]))
        elif tipo == "poligono":
            if len(ents) == 1:            # un clic en un lado: se toma la cadena cerrada de líneas
                cadena, cerrada = self.b.cadena(ents[0])
                if not cerrada or any(self.b.tipo_de(k) != "linea" for k, _ in cadena):
                    self.mensaje.emit("Polígono: hacé clic en un lado de una cadena cerrada de líneas.")
                    return False
                ents = [k for k, _ in cadena]
        elif tipo in ("coincidente", "punto_medio"):
            ents = self._ordenar(ents, "punto")
        elif tipo == "tangente":
            ents = self._ordenar(ents, "linea")
        ok = self.aplicar_cambio(lambda: self.b.agregar_restriccion(tipo, ents))
        if ok:
            self.mensaje.emit(f"Restricción agregada: {TIPOS_RESTRICCION.get(tipo, tipo)}.")
        return ok

    def _restriccion_con_seleccion(self):
        tipo, n = RESTRICCIONES_HERRAMIENTA[self.herramienta]
        ents = [i for i in self.seleccion if i in self.b.puntos or i in self.b.curvas]
        listo = (len(ents) == n or (tipo == "horizontal_vertical" and len(ents) == 2)
                 or (tipo == "fijo" and len(ents) >= 1) or (tipo == "poligono" and len(ents) >= 3))
        if ents and listo:
            self.aplicar_restriccion(tipo, ents)
            self.seleccion = []
            self.update()
            return True
        return False

    def _clic_restriccion(self, pos):
        ent = self.entidad_en(pos)
        if ent is None:
            return
        tipo, n = RESTRICCIONES_HERRAMIENTA[self.herramienta]
        if ent in self.picks:
            return
        self.picks.append(ent)
        if tipo == "horizontal_vertical":
            if self.b.tipo_de(self.picks[0]) == "linea" or len(self.picks) == 2:
                self.aplicar_restriccion(tipo, list(self.picks))
                self.picks = []
        elif len(self.picks) >= n:
            self.aplicar_restriccion(tipo, list(self.picks))
            self.picks = []
        self.update()

    # ------------------------------------------------------------ selección y borrado
    def borrar_seleccion(self):
        ids = [i for i in self.seleccion if i in self.b.puntos or i in self.b.curvas
               or i in self.b.restricciones or i in self.b.cotas]
        if not ids:
            return

        def borrar():
            for i in ids:
                if i in self.b.puntos or i in self.b.curvas or i in self.b.restricciones or i in self.b.cotas:
                    self.b.eliminar(i)
        self.aplicar_cambio(borrar)
        self.seleccion = []
        self._notificar_seleccion()

    def copiar_seleccion(self):
        """Ctrl+C: guarda la selección (con una copia del boceto) para pegarla en este u otro boceto."""
        ids = [i for i in self.seleccion if i > 0 and (i in self.b.puntos or i in self.b.curvas)]
        if ids:
            PORTAPAPELES.update(boceto=self.b.copia(), ids=ids)
            self.mensaje.emit(f"{len(ids)} elemento(s) copiado(s): Ctrl+V los pega.")

    def pegar(self):
        """Ctrl+V: pega lo copiado en el mismo lugar, como geometría normal, y lo deja seleccionado."""
        nuevos = []
        origen, ids = PORTAPAPELES["boceto"], PORTAPAPELES["ids"]
        if self.aplicar_cambio(lambda: nuevos.extend(self.b.pegar_de(origen, ids)), operacion=True, anclar=False):
            self.seleccion = nuevos
            self._notificar_seleccion()
            self.update()

    def alternar_construccion(self):
        curvas = [i for i in self.seleccion if i in self.b.curvas]
        if not curvas:
            self.construccion = not self.construccion
            if self.construccion:
                self.eje = False
            self.mensaje.emit("Las curvas nuevas son de construcción." if self.construccion
                              else "Las curvas nuevas son normales.")
            return

        def cambiar():
            for i in curvas:
                self.b.curvas[i].construccion = not self.b.curvas[i].construccion
                if self.b.curvas[i].construccion:
                    self.b.curvas[i].eje = False
        self.aplicar_cambio(cambiar)

    def _zona_en(self, pos):
        """Cota o símbolo bajo `pos`: su texto o ícono, o (la cota) cualquier raya de su línea de cota, su flecha, su
        arco o su guía, salvo que ahí haya una curva o punto del boceto (esa gana)."""
        for tabla in (self._zonas_cotas, self._zonas_glifos):
            for ident, rect in tabla.items():
                if rect.adjusted(-4, -4, 4, 4).contains(pos):
                    return ident
        for cid, rayas in self._trazos_cotas.items():
            if any(_distancia_a_raya(pos, a, b) <= 5 for a, b in rayas) and self.entidad_en(pos) is None:
                return cid
        return None

    # ------------------------------------------------------------ eventos
    def _para_visor(self, e):
        if self.visor is None:
            return False
        if e.button() != Qt.LeftButton:
            return True
        return self.visor.modo in ("orbita", "encuadre", "zoom", "ventana", "mirar")

    def mousePressEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        if self._asas is not None and e.button() == Qt.LeftButton and self._asas.empezar(pos):
            return                                   # se tira de un asa de la herramienta
        if e.button() == Qt.LeftButton and self.herramienta == "seleccionar" and self._clic_casilla_patron(pos):
            return                                   # casilla de supresión de una copia del patrón
        if self.entrada is not None and e.button() == Qt.LeftButton and self._citar_cota(pos):
            return                                   # antes de setFocus: este saca el foco y la selección de la caja
        self._camara()
        self.setFocus()
        if self._eligiendo_punto is not None and not self._para_visor(e):
            pid = self._punto_cercano(pos) if e.button() == Qt.LeftButton else None
            if pid is not None or e.button() == Qt.RightButton:
                self._terminar_eleccion(pid)
            else:
                self.mensaje.emit("Ahí no hay un punto del boceto: hacé clic sobre uno (Esc cancela).")
            return
        if self._previa_texto is not None and self.entrada is not None and e.button() in (Qt.LeftButton,
                                                                                          Qt.RightButton):
            if e.button() == Qt.LeftButton and self._sobre_texto(pos):
                self._clic_en_texto(pos, e.modifiers())      # clic en el texto: mueve el cursor
                return
            self.confirmar_texto_pendiente()          # clic afuera o clic derecho (menú radial): el texto queda
            if e.button() == Qt.LeftButton:
                return
        if (self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None
                and e.button() == Qt.LeftButton and not self._para_visor(e)):
            self._actualizar_rho_conica(pos)
            self._presion = (pos, None, self.cursor)
            self.update()
            return
        if self.entrada is not None and e.button() == Qt.LeftButton:
            if self._editando is not None:          # clic con una caja a medio escribir: el valor queda fijo
                texto = self.entrada.campos[0].text()
                if not self._fin_edicion_viva(texto):
                    self._cerrar_entrada()
            else:
                self._cerrar_entrada()
        zona = self._zona_en(pos) if e.button() == Qt.RightButton and not self.clics else None
        if zona in self.b.cotas:
            self._menu_cota(zona, pos).exec(e.globalPosition().toPoint())
            return
        if e.button() == Qt.RightButton and (self.herramienta != "seleccionar" or self._hay_operacion()):
            # en una herramienta, el clic derecho rápido cancela o sale (al soltar); arrastrado, pasa al visor o al
            # desplazamiento; mantenido con una cota a medias, abre sus opciones
            self._derecho = (pos, e.globalPosition().toPoint())
            if self.herramienta == "cota" and self.picks:
                self._t_derecho.start(400)
            return
        if self._para_visor(e):
            self._reenvio = (e.button(), pos)
            self.visor.mousePressEvent(e)
            return
        if self.visor is None and (e.button() == Qt.MiddleButton or (e.button() == Qt.RightButton and not self.clics)):
            self._pan = pos
            return
        if e.button() == Qt.RightButton:
            self.cancelar()
            return
        if e.button() != Qt.LeftButton:
            return
        h = self.herramienta
        if h == "seleccionar" and self._presionar_marco(pos):
            pass
        elif h == "seleccionar":
            self._presionar_seleccion(pos, e.modifiers())
        elif h == "cota":
            self._clic_cota(pos)
        elif h in RESTRICCIONES_HERRAMIENTA:
            self._clic_restriccion(pos)
        elif h in PROYECCION:
            self._clic_proyectar(pos)
        elif h in SELECCION and self.fase == "seleccion":
            self._presionar_seleccion(pos, Qt.ControlModifier, arrastrar=False)
        elif (h in PICKS or (h in SELECCION and self.fase == "eje")) and self._clic_pick(pos):
            pass
        else:
            base = self.clics[-1][1] if self.clics else None
            self._presion = (pos, *self._ajustar(pos, base=base))
            self._presion_inferencia = self.inferencia
            self._presion_inf_actual = self.inf_actual
        self.update()

    # ------------------------------------------------------------ marco de control (mover, escalar, girar, espejar)
    def _ids_marco(self):
        return [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos]

    def _caja_marco(self):
        """Caja (xmin, ymin, xmax, ymax) en mm de lo elegido, o None si el marco no corresponde: hace falta
        estar seleccionando y tener al menos dos curvas (o un texto)."""
        if not self.mostrar_marco or self.herramienta != "seleccionar" or self.fase not in (None, "", "seleccion"):
            return None
        ids = self._ids_marco()
        curvas = [i for i in ids if i in self.b.curvas]
        if len(curvas) < 2 and not any(isinstance(self.b.curvas[i], Texto) for i in curvas):
            return None
        pts = []
        for i in ids:
            if i in self.b.puntos:
                pts.append(self.b.coords(i))
                continue
            for prim in self.b.primitivas(i):
                if prim[0] == "linea":
                    pts += [prim[2], prim[3]]
                elif prim[0] == "circulo":
                    (cx, cy), r = prim[2], prim[3]
                    pts += [(cx - r, cy - r), (cx + r, cy + r)]
                elif prim[0] == "spline":         # la curva queda dentro de su polígono de control
                    pts += list(prim[2])
                else:
                    pts += puntos_primitiva(prim, 24)
        if not pts:
            return None
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        caja = (min(xs), min(ys), max(xs), max(ys))
        a, b = self.a_px(caja[0], caja[1]), self.a_px(caja[2], caja[3])
        if abs(b.x() - a.x()) < 4 and abs(b.y() - a.y()) < 4:
            return None
        return caja

    def _manijas_marco(self, caja):
        """{nombre: punto en píxeles} de las manijas del marco."""
        x0, y0, x1, y1 = caja
        esq = [self.a_px(x0, y0), self.a_px(x1, y0), self.a_px(x1, y1), self.a_px(x0, y1)]
        arriba = self.a_px((x0 + x1) / 2, y1)
        derecha, abajo = self.a_px(x1, (y0 + y1) / 2), self.a_px((x0 + x1) / 2, y0)
        m = {f"escala{k}": q for k, q in enumerate(esq)}
        m["rotar"] = QPointF(arriba.x(), arriba.y() - 28)
        m["mover"] = self.a_px((x0 + x1) / 2, (y0 + y1) / 2)
        m["espejo_h"] = QPointF(derecha.x() + 18, derecha.y())
        m["espejo_v"] = QPointF(abajo.x(), abajo.y() + 18)
        return m

    def _presionar_marco(self, pos):
        caja = self._caja_marco()
        if caja is None:
            return False
        for nombre, q in self._manijas_marco(caja).items():
            if math.hypot(q.x() - pos.x(), q.y() - pos.y()) <= TOL_MANIJA:
                mm = self.a_mm(pos)
                self._marco = {"tipo": nombre, "caja": caja, "inicio": mm, "actual": mm, "px_inicio": pos,
                               "px_actual": pos, "shift": False}
                return True
        return False

    def _transformacion_marco(self):
        """(descripción, función punto → punto, acción sobre el boceto) del arrastre en curso."""
        m = self._marco
        x0, y0, x1, y1 = m["caja"]
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        (ix, iy), (ax, ay) = m["inicio"], m["actual"]
        tipo, ids = m["tipo"], self._ids_marco()
        if tipo == "mover":
            dx, dy = ax - ix, ay - iy
            if m["shift"]:                       # Shift: solo en el eje donde más se movió
                dx, dy = (dx, 0.0) if abs(dx) >= abs(dy) else (0.0, dy)
            return (f"Δ {formato.numero(dx)} ; {formato.numero(dy)} mm", lambda q: (q[0] + dx, q[1] + dy),
                    lambda: self.b.transformar(ids, dx=dx, dy=dy))
        if tipo.startswith("escala"):
            k = int(tipo[-1])
            esq = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            ancla = c if m["shift"] else esq[(k + 2) % 4]
            d0 = math.dist(esq[k], ancla)
            f = max(math.dist((ax, ay), ancla) / d0, 1e-3) if d0 > 1e-12 else 1.0
            return (f"× {formato.numero(f)}", lambda q: (ancla[0] + f * (q[0] - ancla[0]), ancla[1] + f * (q[1] - ancla[1])),
                    lambda: self.b.escalar(ids, ancla, f))
        if tipo == "rotar":
            ang = math.degrees(math.atan2(ay - c[1], ax - c[0]) - math.atan2(iy - c[1], ix - c[0]))
            ang = (ang + 180.0) % 360.0 - 180.0
            if m["shift"]:
                ang = round(ang / 15.0) * 15.0
            a = math.radians(ang)

            def girar(q):
                u, v = q[0] - c[0], q[1] - c[1]
                return (c[0] + u * math.cos(a) - v * math.sin(a), c[1] + u * math.sin(a) + v * math.cos(a))
            return (f"{formato.numero(ang)}°", girar, lambda: self.b.transformar(ids, angulo=ang, centro=c))
        horizontal = tipo == "espejo_h"
        return ("Espejo", (lambda q: (2 * c[0] - q[0], q[1])) if horizontal else (lambda q: (q[0], 2 * c[1] - q[1])),
                lambda: self._espejar_marco(ids, c, horizontal))

    def _espejar_marco(self, ids, centro, horizontal):
        _hechos, textos = self.b.reflejar(ids, centro, horizontal)
        if textos:
            self.mensaje.emit("Los textos rectos no se espejan con el marco: usá los botones de volteo del panel «Carácter».")

    def _soltar_marco(self):
        m, self._marco = self._marco, None
        if m is None:
            return
        movio = math.hypot(m["px_actual"].x() - m["px_inicio"].x(), m["px_actual"].y() - m["px_inicio"].y()) > 3
        if not movio and not m["tipo"].startswith("espejo"):
            return
        self._marco = m
        _texto, _f, accion = self._transformacion_marco()
        self._marco = None
        self.aplicar_cambio(accion)

    def _dibujar_marco(self, p):
        caja = self._marco["caja"] if self._marco is not None else self._caja_marco()
        if caja is None:
            return
        x0, y0, x1, y1 = caja
        azul = QColor(0, 150, 255)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(azul, 1, Qt.DashLine))
        esq = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        p.drawPolygon(QPolygonF([self.a_px(*q) for q in esq]))
        manijas = self._manijas_marco(caja)
        arriba = self.a_px((x0 + x1) / 2, y1)
        p.setPen(QPen(azul, 1))
        p.drawLine(arriba, manijas["rotar"])
        for nombre, q in manijas.items():
            p.setBrush(QColor(255, 170, 40) if nombre == self._manija_sobre else QColor(255, 255, 255))
            if nombre == "rotar":
                p.drawEllipse(q, 5, 5)
            elif nombre == "mover":
                p.drawLine(QPointF(q.x() - 6, q.y()), QPointF(q.x() + 6, q.y()))
                p.drawLine(QPointF(q.x(), q.y() - 6), QPointF(q.x(), q.y() + 6))
            elif nombre.startswith("espejo"):        # flecha doble dibujada (no depende de la fuente)
                h = nombre == "espejo_h"
                a = QPointF(q.x() - 7, q.y()) if h else QPointF(q.x(), q.y() - 7)
                b = QPointF(q.x() + 7, q.y()) if h else QPointF(q.x(), q.y() + 7)
                p.drawLine(a, b)
                for punta, s in ((a, 1), (b, -1)):
                    if h:
                        p.drawLine(punta, QPointF(punta.x() + 4 * s, punta.y() - 3))
                        p.drawLine(punta, QPointF(punta.x() + 4 * s, punta.y() + 3))
                    else:
                        p.drawLine(punta, QPointF(punta.x() - 3, punta.y() + 4 * s))
                        p.drawLine(punta, QPointF(punta.x() + 3, punta.y() + 4 * s))
            else:
                p.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8))
        p.setBrush(Qt.NoBrush)
        if self._marco is not None:                 # vista previa del resultado
            texto, f, _accion = self._transformacion_marco()
            p.setPen(QPen(QColor(255, 140, 0), 1.5, Qt.DashLine))
            p.drawPolygon(QPolygonF([self.a_px(*f(q)) for q in esq]))
            p.setPen(QPen(QColor(255, 140, 0), 1))
            q = self._marco["px_actual"]
            p.drawText(QPointF(q.x() + 14, q.y() - 10), texto)

    def _presionar_seleccion(self, pos, mods, arrastrar=True):
        suma = bool(mods & (Qt.ControlModifier | Qt.ShiftModifier))
        ent = self._zona_en(pos)
        if ent is None:
            ent = self.entidad_en(pos)
        if not suma:
            self.perfiles_sel = []
        if ent is None:
            if not suma:
                self.seleccion = []
            self._ventana = (pos, pos)
        elif suma:
            if ent in self.seleccion:
                self.seleccion.remove(ent)
            else:
                self.seleccion.append(ent)
        else:
            self.seleccion = [ent]
        if arrastrar and ent is not None:
            self._empezar_arrastre(ent, pos)
        self.cambio.emit()
        self._notificar_seleccion()

    # ------------------------------------------------------------ arrastrar puntos y curvas (con el solver)
    def _determinada(self, ent):
        r = self.resultado
        return r is not None and r.ok and ent in r.determinadas

    def _empezar_arrastre(self, ent, pos):
        """Arrastre en Seleccionar: puntos, líneas (sus dos extremos juntos), círculos y arcos. Lo fijo o
        totalmente restringido no se mueve (como en Fusion)."""
        fijos = self.b.puntos_fijos()
        if ent in self.b.puntos:
            if ent in fijos:
                self.mensaje.emit("Ese punto está fijo (o es proyectado): quitá la restricción «Fijo» para moverlo.")
                return
            if self._determinada(ent):
                self.mensaje.emit("Ese punto está totalmente restringido: no se puede arrastrar.")
                return
            self._arrastre = ent
        elif ent in self.b.curvas:
            c = self.b.curvas[ent]
            if isinstance(c, Texto) and c.camino in self.b.curvas:
                # texto en curva: arrastrarlo lo desliza por la curva (la posición sigue al ratón)
                cam = self.b.curvas[c.camino]
                inicio = fraccion_en_camino(self.b.primitivas(c.camino)[0], self.a_mm(pos))
                cerrada = isinstance(cam, Circulo) or bool(getattr(cam, "cerrada", False))
                self._arrastre = ("curva", ent, "deslizar")
                self._desliz = (inicio, c.camino_pos, cerrada)
                self._ultimo = self.a_mm(pos)
                self._movio = False
                self._instantanea()
                self.mensaje.emit("Arrastrá el texto para deslizarlo por la curva.")
                return
            if not isinstance(c, (Linea, Circulo, Arco, Texto)) or c.proyectada:
                return
            if set(c.puntos()) <= fijos or self._determinada(ent):
                self.mensaje.emit("Esa curva está totalmente restringida (o fija): no se puede arrastrar.")
                return
            self._arrastre = ("curva", ent, self._modo_arrastre(ent))
            self._ultimo = self.a_mm(pos)
        elif ent in self.b.cotas:
            # solo mueve la cota (línea, arco o texto): el valor no cambia. Agarrada de la línea y no del texto, el
            # texto de una cota lineal se queda donde está.
            QToolTip.hideText()
            self._cita_sobre = None
            sobre_texto = self._zonas_cotas[ent].adjusted(-4, -4, 4, 4).contains(pos)
            self._arrastre = ("cota", ent, None if sobre_texto else "linea")
        else:
            return
        self._movio = False
        self._instantanea()

    def _cambiar_radio(self, b, cid, radio):
        return cambiar_radio(b, cid, radio)

    def _modo_arrastre(self, cid):
        """"radio" si arrastrar la curva puede cambiar el radio (está libre); si no, "mover"."""
        c = self.b.curvas[cid]
        if isinstance(c, (Linea, Texto)):
            return "mover"
        copia = self.b.copia()
        r0 = copia.radio(cid)
        ref = self._cambiar_radio(copia, cid, r0 * 1.25 + 1.0)
        try:
            resolver(copia, self.valores_cotas(), ref)
        except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError):
            return "mover"
        return "radio" if abs(copia.radio(cid) - r0) > 1e-4 else "mover"

    def _deslizar_texto(self, cid, cur):
        """Mueve un texto en curva a lo largo de su camino: conserva el punto del texto que se agarró."""
        t = self.b.curvas[cid]
        inicio, pos0, cerrada = self._desliz
        ahora = fraccion_en_camino(self.b.primitivas(t.camino)[0], cur)
        delta = ahora - inicio
        if cerrada:
            delta = (delta + 0.5) % 1.0 - 0.5         # por el camino corto: da la vuelta sin saltar
            t.camino_pos = (pos0 + delta) % 1.0
        else:
            t.camino_pos = min(max(pos0 + delta, 0.0), 1.0)
        self.update()

    def _mover_curva(self, cid, modo, cur):
        if modo == "deslizar":
            self._deslizar_texto(cid, cur)
            return
        c = self.b.curvas[cid]
        fijos = self.b.puntos_fijos()
        if modo == "radio":
            cx, cy = self.b.coords(c.centro)
            ref = self._cambiar_radio(self.b, cid, max(math.hypot(cur[0] - cx, cur[1] - cy), 1e-3))
        else:
            dx, dy = cur[0] - self._ultimo[0], cur[1] - self._ultimo[1]
            libres = [pid for pid in c.puntos() if pid not in fijos]
            for pid in libres:
                p = self.b.puntos[pid]
                p.x, p.y = p.x + dx, p.y + dy
            ref = min(libres, key=lambda q: math.dist(self.b.coords(q), cur)) if libres else None
        self._ultimo = cur
        self.resolver(arrastrado=ref)

    def _mover_punto(self, pid, cur):
        """Arrastra un punto; si es el centro de arcos, el arco entero lo acompaña."""
        p = self.b.puntos[pid]
        dx, dy = cur[0] - p.x, cur[1] - p.y
        p.x, p.y = cur
        fijos = self.b.puntos_fijos()
        for c in self.b.curvas.values():
            if isinstance(c, Arco) and c.centro == pid:
                for q in (c.inicio, c.fin):
                    if q not in fijos and q != pid:
                        self.b.puntos[q].x += dx
                        self.b.puntos[q].y += dy
        # Rápido: lo movido es un punto (y, si es centro de arcos, sus arcos: misma parte del boceto). Arrastrar una
        # curva entera mueve puntos que pueden estar en partes distintas, por eso `_mover_curva` resuelve todo.
        self.resolver(arrastrado=pid, rapido=True)

    def _manija_en(self, pos):
        """Nombre de la manija del marco de control bajo `pos` (o None)."""
        caja = self._caja_marco() if self.mostrar_marco else None
        if caja is None:
            return None
        for nombre, q in self._manijas_marco(caja).items():
            if math.hypot(q.x() - pos.x(), q.y() - pos.y()) <= TOL_MANIJA:
                return nombre
        return None

    def _actualizar_sobre(self, pos):
        """Seleccionar: resalta lo que hay bajo el ratón (manija, cota, símbolo, curva o punto) y cambia el
        cursor, para que se vea dónde agarrar. Orden igual al del clic: manija, cota/símbolo, entidad."""
        manija = self._manija_en(pos)
        zona = None if manija is not None else self._zona_en(pos)
        ent = None
        if manija is None and zona is None and len(self.b.curvas) <= 400:
            ent = self.entidad_en(pos)
            if ent is not None and ent not in self.b.curvas and ent not in self.b.puntos:
                ent = None
        if (ent, manija, zona) != (self._sobre, self._manija_sobre, self._zona_sobre):
            self._sobre, self._manija_sobre, self._zona_sobre = ent, manija, zona
            if manija is not None:
                self.setCursor(Qt.CrossCursor if manija == "rotar" else Qt.SizeAllCursor)
            elif zona is not None:
                self.setCursor(Qt.PointingHandCursor)
            elif ent is not None:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.unsetCursor()
            self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        self._pos_cursor = pos
        self._camara()
        if self._asas is not None:
            if self._asas.arrastrando:
                self._asas.mover(pos)
                return
            if not (e.buttons() & Qt.LeftButton):
                self._asas.pasar(pos)
        if self._previa_texto is not None and self.entrada is not None:
            if self._arrastre_texto and e.buttons() & Qt.LeftButton:       # arrastrando: selecciona texto
                i = self._indice_en_texto(pos)
                d = self._previa_texto
                if i is not None and i != d["cursor"]:
                    d["cursor"], d["col"] = i, None
                    self._actualizar_cursor()
                    self.update()
                return
            self.setCursor(Qt.IBeamCursor if self._sobre_texto(pos) else Qt.ArrowCursor)
        if (self.herramienta == "seleccionar" and not (e.buttons() & Qt.LeftButton) and self.entrada is None
                and self._reenvio is None and self._marco is None):
            self._actualizar_sobre(pos)
        elif self._sobre is not None or self._manija_sobre is not None or self._zona_sobre is not None:
            self._sobre = self._manija_sobre = self._zona_sobre = None
            self.unsetCursor()
        self._actualizar_cita(pos)
        if self._derecho is not None and (pos - self._derecho[0]).manhattanLength() > 4:
            self._t_derecho.stop()
            inicio, global_ = self._derecho
            self._derecho = None
            if self.visor is not None:               # arrastre con el derecho: es del visor (gesto del menú radial)
                self._reenvio = (Qt.RightButton, inicio)
                self.visor.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, inicio, global_, Qt.RightButton,
                                                       Qt.RightButton, e.modifiers()))
            else:
                self._pan = inicio
        if self._reenvio is not None:
            self.visor.mouseMoveEvent(e)
            return
        if self._pan is not None:
            d = pos - self._pan
            self._pan = pos
            self.centro[0] -= d.x() / self.escala
            self.centro[1] += d.y() / self.escala
            self.update()
            return
        if self._ventana is not None:
            self._ventana = (self._ventana[0], pos)
            self.update()
            return
        if self._marco is not None:
            self._marco["actual"] = self.a_mm(pos)
            self._marco["px_actual"] = pos
            self._marco["shift"] = bool(e.modifiers() & Qt.ShiftModifier)
            self.update()
            return
        if self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None:
            self._actualizar_rho_conica(pos)
            self.update()
            return
        base = self.clics[-1][1] if self.clics and self.herramienta not in ("circulo_3p",) else None
        excluir = self._arrastre if isinstance(self._arrastre, int) else None
        self.cursor = self._ajustar(pos, excluir=excluir, base=base)[1]
        if (self._presion is not None and self.herramienta == "linea" and e.buttons() & Qt.LeftButton
                and self.clics and self._presion[1] is not None and self._presion[1] == self.clics[-1][0]
                and math.hypot(pos.x() - self._presion[0].x(), pos.y() - self._presion[0].y()) > 8):
            # arrastrar desde el extremo de la línea anterior, o de un arco, spline o cónica (BOC-12), da un arco tangente
            curvas = [k for k in self._curvas_con_extremo(self._presion[1]) if k == self._ultima_linea
                      or not isinstance(self.b.curvas[k], Linea)]
            if curvas:
                self._tangente = (self._presion[1], curvas[0])
        if isinstance(self._arrastre, tuple):
            _, cid, modo = self._arrastre
            if cid in self.b.curvas:
                self._mover_curva(cid, modo, self.a_mm(pos))
                self._movio = True
            elif cid in self.b.cotas:
                self.b.mover_cota(self.b.cotas[cid], self.a_mm(pos), con_texto=modo != "linea")
                self._movio = True
        elif self._arrastre is not None:
            self._mover_punto(self._arrastre, self.cursor)
            self._movio = True
        if self.herramienta == "recortar":
            self._previa_recorte = self._tramo_a_recortar(pos)
        self.update()

    def mouseReleaseEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        if self._asas is not None and self._asas.arrastrando:
            self._asas.soltar()
            return
        if self._arrastre_texto:
            self._arrastre_texto = False
            d = self._previa_texto
            if d is not None and d["ancla"] == d["cursor"]:
                d["ancla"] = None            # un clic sin arrastre no deja selección
                self._actualizar_cursor()
                self.update()
            return
        if self._derecho is not None and e.button() == Qt.RightButton:
            self._t_derecho.stop()
            self._derecho = None
            self.cancelar()
            return
        if self._reenvio is not None:
            boton, inicio = self._reenvio
            self._reenvio = None
            self.visor.mouseReleaseEvent(e)     # clic derecho: el visor abre el menú radial (Aceptar / Cancelar…)
            return
        self._pan = None
        if self._marco is not None:
            self._marco["shift"] = bool(e.modifiers() & Qt.ShiftModifier)
            self._soltar_marco()
            self.update()
            return
        if self._ventana is not None:
            a, b = self._ventana
            self._ventana = None
            if abs(b.x() - a.x()) < 3 and abs(b.y() - a.y()) < 3:
                self._clic_perfil(a)                  # BOC-23: clic (sin arrastrar) dentro de una región cerrada
            else:
                self._seleccionar_ventana(a, b)
        if self._arrastre is not None:
            if not self._movio:
                self.historial.pop()
            else:
                self.pila_rehacer.clear()
                self.resolver()
            self._arrastre = None
        if self._presion is not None and e.button() == Qt.LeftButton:
            if self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None:
                self._actualizar_rho_conica(pos)
                self._presion = None
                self.entrada.aceptado.emit([self.entrada.campos[0].text()])
                self.update()
                return
            _pos, pid, xy = self._presion
            self._presion = None
            if self._tangente is not None:
                inicio, linea = self._tangente
                self._tangente = None
                fin = self._ajustar(pos)
                res = self._crear_arco_tangente(inicio, linea, fin)
                if res is not None:
                    aid, punto_fin = res
                    self.clics = [(punto_fin, self.b.coords(punto_fin))]
                    self._ultima_linea = None
                    self._reiniciar_vivo()
                    self.mensaje.emit("Arco tangente creado. Seguí con la línea o Esc.")
            else:
                self.inferencia = self._presion_inferencia
                self.inf_actual = self._presion_inf_actual
                if (self.herramienta == "spline_ajuste" and len(self.clics) >= 3 and pid is not None
                        and pid == self.clics[0][0]):
                    xy = self.clics[0][1]            # clic en el primer punto: cierra la spline
                elif (self.herramienta == "spline_ajuste" and len(self.clics) >= 3 and pid is None
                      and self.clics[0][0] is None and math.dist(xy, self.clics[0][1]) * self.px_por_mm() < TOL_PX):
                    xy = self.clics[0][1]
                self._registrar_clic(pid, xy)
        self.update()

    # ------------------------------------------------------------ ventana de selección, cadenas y medidas
    def colores_ventana(self, a=None, b=None):
        """(relleno, borde o None) de la ventana de selección, con los colores de Fusion."""
        if a is None:
            a, b = self._ventana
        if b.x() < a.x():
            return VENTANA_CRUCE, None          # de derecha a izquierda: amarillo, elige lo que toca
        return VENTANA_RELLENO, VENTANA_BORDE   # de izquierda a derecha: naranja, elige lo que queda adentro

    def _seleccionar_ventana(self, a, b):
        rect = QRectF(a, b).normalized()
        if rect.width() < 3 and rect.height() < 3:
            return
        cruce = b.x() < a.x()       # de derecha a izquierda: alcanza con tocar (como en Fusion)
        sel = list(self.seleccion)
        visibles = {q for c in self.b.curvas.values() if self._visible(c) for q in c.puntos()}
        sueltos = {p for p in self.b.puntos if not any(p in c.puntos() for c in self.b.curvas.values())}
        for p in self.b.puntos.values():
            if (p.id in visibles or p.id in sueltos) and rect.contains(self.a_px(p.x, p.y)) and p.id not in sel:
                sel.append(p.id)
        for c in self.b.curvas.values():
            if not self._visible(c) or c.id in sel:
                continue
            polis = [self._poli_px(poli) for poli in self._polilineas(c, 24)]
            pts = [q for poli in polis for q in poli]
            if not pts:
                continue
            if cruce:
                toca = any(rect.contains(q) for q in pts) or any(
                    _segmento_en_rect(rect, q1, q2) for poli in polis for q1, q2 in zip(poli, poli[1:], strict=False))
            else:
                toca = all(rect.contains(q) for q in pts)
            if toca:
                sel.append(c.id)
        self.seleccion = sel
        self.cambio.emit()
        self._notificar_seleccion()

    def cadena_conectada(self, cid):
        """Curvas unidas por sus extremos a `cid` (doble clic de Fusion): puntos compartidos o coincidentes.
        Se recorren solo las del mismo tipo (normal / construcción)."""
        base = self.b.curvas[cid]
        gemelos = {}
        for r in self.b.restricciones.values():
            if r.tipo == "coincidente" and len(r.entidades) == 2 and all(e in self.b.puntos for e in r.entidades):
                a, b = r.entidades
                gemelos.setdefault(a, set()).add(b)
                gemelos.setdefault(b, set()).add(a)
        por_punto = {}
        for c in self.b.curvas.values():
            if self._visible(c) and not isinstance(c, Texto) and c.construccion == base.construccion:
                for p in c.extremos() or ():
                    por_punto.setdefault(p, []).append(c.id)
        salida, pendientes = [cid], [cid]
        while pendientes:
            k = pendientes.pop()
            for p in self.b.curvas[k].extremos() or ():
                for q in {p} | gemelos.get(p, set()):
                    for otra in por_punto.get(q, []):
                        if otra not in salida:
                            salida.append(otra)
                            pendientes.append(otra)
        return salida

    def _largo(self, cid):
        c = self.b.curvas[cid]
        if isinstance(c, Linea):
            return math.dist(*self.b._extremos_linea(cid))
        if isinstance(c, Circulo):
            return 2 * math.pi * c.radio
        if isinstance(c, Arco):
            (cx, cy), (sx, sy), (ex, ey) = (self.b.coords(q) for q in (c.centro, c.inicio, c.fin))
            return self.b.radio(cid) * _barrido(math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx))
        return sum(math.dist(a, b) for poli in self._polilineas(c, 256) for a, b in zip(poli, poli[1:], strict=False))

    def describir_seleccion(self):
        """Medidas de lo elegido con el formato de Fusion ("1 línea de boceto | Longitud: 123.698 mm")."""
        curvas = [i for i in self.seleccion if i in self.b.curvas]
        puntos = [i for i in self.seleccion if i in self.b.puntos]
        perfiles = self.perfiles_seleccionados() if self.perfiles_sel else []
        if perfiles:
            nombre = "1 perfil de boceto" if len(perfiles) == 1 else f"{len(perfiles)} perfiles de boceto"
            return f"{nombre} | Área: {formato.numero(sum(p.area for p in perfiles))} mm²"
        if curvas:
            if len(curvas) == 1 and not puntos:
                c = self.b.curvas[curvas[0]]
                nombre = f"1 {NOMBRES_ENTIDAD.get(c.tipo, c.tipo)} de boceto"
                if isinstance(c, Texto):
                    return nombre
                if isinstance(c, Circulo):
                    return f"{nombre} | Radio: {texto_valor(c.radio)}"
                return f"{nombre} | Longitud: {texto_valor(self._largo(c.id))}"
            total = sum(self._largo(k) for k in curvas if not isinstance(self.b.curvas[k], Texto))
            return f"{len(curvas)} curvas de boceto | Longitud: {texto_valor(total)}"
        if puntos:
            return "1 punto de boceto" if len(puntos) == 1 else f"{len(puntos)} puntos de boceto"
        cotas = sum(1 for i in self.seleccion if i in self.b.cotas)
        if cotas:
            return "1 cota de boceto" if cotas == 1 else f"{cotas} cotas de boceto"
        restricciones = sum(1 for i in self.seleccion if i in self.b.restricciones)
        if restricciones:
            return "1 restricción de boceto" if restricciones == 1 else f"{restricciones} restricciones de boceto"
        return ""

    def _notificar_seleccion(self):
        texto = self.describir_seleccion()
        if texto != self._info:
            self._info = texto
            self.info.emit(texto)

    def mouseDoubleClickEvent(self, e):
        if self.visor is not None and e.button() == Qt.MiddleButton:
            self.visor.mouseDoubleClickEvent(e)
            return
        if (e.button() == Qt.LeftButton and self._previa_texto is not None and self.entrada is not None
                and self._sobre_texto(e.position())):
            self._seleccionar_palabra(e.position())          # doble clic en el texto: elige la palabra
            return
        if e.button() == Qt.LeftButton:
            zona = self._zona_en(e.position())
            glifo = self.b.restricciones.get(zona) if zona not in self.b.cotas else None
            pid = self.patron_de(glifo.entidades) if glifo is not None and glifo.tipo == "patron" else None
            if pid is not None:                      # doble clic en el glifo del patrón: editarlo (BOC-16)
                self.editar_patron(pid)
            elif zona in self.b.cotas and e.modifiers() & Qt.ShiftModifier:
                self.alternar_referencia(zona)
            elif zona in self.b.cotas:
                self.editar_cota(zona, e.position())
            elif self.herramienta in SPLINES:
                self._terminar_spline()
            elif self.herramienta == "linea":
                self.cancelar()
            elif self.herramienta == "seleccionar":
                cid = self._curva_cercana(e.position(), tipos=("texto",))
                if cid is not None:
                    self.editar_texto(cid, e.position())
                    return
                cid = self._curva_cercana(e.position())
                if cid is not None:                  # doble clic: toda la cadena de curvas unidas
                    cadena = self.cadena_conectada(cid)
                    if e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                        cadena = self.seleccion + [k for k in cadena if k not in self.seleccion]
                    self.seleccion = cadena
                    self.cambio.emit()
                    self._notificar_seleccion()
                    self.update()

    def wheelEvent(self, e):
        if self.visor is not None:
            self.visor.wheelEvent(e)
            return
        antes = self.a_mm(e.position())
        self.escala = max(0.05, min(500.0, self.escala * (1.15 ** (e.angleDelta().y() / 120.0))))
        despues = self.a_mm(e.position())
        self.centro[0] += antes[0] - despues[0]
        self.centro[1] += antes[1] - despues[1]
        self.update()

    def _admite_entrada(self, e):
        if not (bool(e.text()) and e.text() in "0123456789.,-(" and not e.modifiers() & Qt.ControlModifier):
            return False
        h = self.herramienta
        if h == "circulo_2t":
            return len(self.picks) == 2
        if h == "mover":
            return self.fase == "destino"
        return bool(self._claves_vivas())

    def event(self, e):
        # Mientras se dibuja, los números son la entrada dinámica (no los atajos de vista 0-3) y
        # Supr / Enter / Esc son del boceto: se reclaman antes de que actúen los atajos de la ventana.
        if e.type() == e.Type.ShortcutOverride and self._previa_texto is not None and self.entrada is not None:
            e.accept()                      # escribiendo en el cuadro de texto: ningún atajo de la ventana
            return True
        if (e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Tab, Qt.Key_Backtab)
                and self._previa_texto is not None and self.entrada is not None):
            self.entrada.campos[1].setFocus()          # Tab: de la escritura en el cuadro a la altura
            self.entrada.campos[1].selectAll()
            return True
        if e.type() == e.Type.ShortcutOverride and (
                self._admite_entrada(e) or e.key() in (Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_Escape,
                                                       Qt.Key_Return, Qt.Key_Enter)):
            e.accept()
            return True
        # Tab / Mayús+Tab pasan de una caja de valor a la otra (no mueven el foco a otro control).
        if e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Tab, Qt.Key_Backtab) and self._claves_vivas():
            n = len(self._claves_vivas())
            atras = e.key() == Qt.Key_Backtab or bool(e.modifiers() & Qt.ShiftModifier)
            self._activo = (self._activo + (-1 if atras else 1)) % n
            self.update()
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        if self._teclado_en_texto(e):
            return
        k = e.key()
        h = self.herramienta
        if k == Qt.Key_Escape:
            if self.visor is not None and self.visor.modo:
                self.visor.set_modo(None)
            else:
                self.cancelar()
        elif e.matches(QKeySequence.Copy) and self.seleccion:
            self.copiar_seleccion()
        elif e.matches(QKeySequence.Paste) and PORTAPAPELES:
            self.pegar()
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            self.borrar_seleccion()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in SPLINES and self.clics:
            self._terminar_spline()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in SELECCION and self.fase == "seleccion":
            self._avanzar_seleccion()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and any(c in self._bloqueos for c in self._claves_vivas()):
            self._confirmar_vivo()                   # Enter con valores escritos: crea con esos valores
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h != "seleccionar":
            self.cancelar()
        elif self._admite_entrada(e):
            if self._claves_vivas():
                self._editar_campo_vivo(e.text())
            else:
                self._entrada_dinamica(e.text())
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------ colores (como Fusion)
    def _oscuro(self):
        return self.visor is not None and self.visor.config.oscuro()

    def _color_curva(self, c, determinadas, fijos, en_conflicto=frozenset()):
        if c.id in self.seleccion or c.id in self.picks:
            return QColor(0, 180, 255), 3.0
        if c.id == self._sobre:
            return QColor(255, 170, 40), 3.0        # lo que se agarraría al hacer clic
        if c.id in en_conflicto or set(c.puntos()) & en_conflicto:
            return CONFLICTO, 2.5
        if c.construccion:                      # tema oscuro de Fusion: gris claro punteado; claro: naranja
            return (QColor(205, 205, 210) if self._oscuro() else QColor(240, 150, 60)), 1.5   # también la proyectada
        if c.proyectada:
            return VIOLETA, 2.0
        if set(c.puntos()) <= fijos:
            return QColor(70, 200, 100), 2.0
        if c.id in determinadas:
            return (QColor(245, 245, 245) if self._oscuro() else QColor(20, 20, 20)), 2.0
        return QColor(90, 160, 255) if self._oscuro() else QColor(25, 90, 200), 2.0

    # ------------------------------------------------------------ dibujo
    def _dibujar_polilinea(self, p, puntos):
        poli = self._poli_px(puntos)
        if poli:
            p.drawPolyline(poli)

    def _ancla(self, ent):
        """Posición (px) donde dibujar textos asociados a una entidad."""
        if ent in self.b.puntos:
            return self.a_px(*self.b.coords(ent))
        c = self.b.curvas[ent]
        if isinstance(c, Linea):
            (x1, y1), (x2, y2) = self.b.coords(c.p1), self.b.coords(c.p2)
            return self.a_px((x1 + x2) / 2, (y1 + y2) / 2)
        if isinstance(c, Texto):
            return self.a_px(*self.b.coords(c.punto))
        prims = self.b.primitivas(ent)
        if not prims:
            return self.a_px(*self.b.coords(c.puntos()[0]))
        prim = prims[0]
        t0, t1, per = dominio(prim)
        t = t0 + (t1 - t0) * (0.125 if per else 0.5)
        return self.a_px(*evaluar_primitiva(prim, t)[0])

    def _fondo_2d(self, p):
        p.fillRect(self.rect(), FONDO_LIENZO)
        s = self.paso_grilla()
        (x0, y1), (x1, y0) = self.a_mm(QPointF(0, 0)), self.a_mm(QPointF(self.width(), self.height()))
        i0, i1 = math.floor(x0 / s), math.ceil(x1 / s)
        j0, j1 = math.floor(y0 / s), math.ceil(y1 / s)
        if (i1 - i0) + (j1 - j0) < 600:
            for i in range(i0, i1 + 1):
                p.setPen(QPen(QColor(215, 218, 225) if i % 5 else QColor(190, 195, 205), 1))
                q = self.a_px(i * s, 0)
                p.drawLine(QPointF(q.x(), 0), QPointF(q.x(), self.height()))
            for j in range(j0, j1 + 1):
                p.setPen(QPen(QColor(215, 218, 225) if j % 5 else QColor(190, 195, 205), 1))
                q = self.a_px(0, j * s)
                p.drawLine(QPointF(0, q.y()), QPointF(self.width(), q.y()))
        o = self.a_px(0, 0)
        p.setPen(QPen(QColor(210, 70, 70), 1.5))
        p.drawLine(QPointF(0, o.y()), QPointF(self.width(), o.y()))
        p.setPen(QPen(QColor(60, 160, 70), 1.5))
        p.drawLine(QPointF(o.x(), 0), QPointF(o.x(), self.height()))

    def _numeros_rejilla(self, p):
        """Números de referencia sobre los ejes del boceto (como la rejilla del boceto de Fusion)."""
        mayor = self.paso_grilla() * 5
        cu, cv = self.plano.a_uv(self.visor.objetivo)
        p.setFont(temas.qfont_cotas(8))
        p.setPen(QColor(140, 146, 158) if self._oscuro() else QColor(80, 85, 95))     # números tenues, como Fusion
        for i in range(-8, 9):
            for u, v in ((round(cu / mayor) * mayor + i * mayor, 0.0), (0.0, round(cv / mayor) * mayor + i * mayor)):
                valor = u if v == 0.0 and u != 0.0 else v
                if valor == 0.0:
                    continue
                q = self.a_px(u, v)
                if 0 <= q.x() <= self.width() and 0 <= q.y() <= self.height():
                    p.drawText(q + QPointF(4, -4), formato.numero(valor))

    def paintEvent(self, _):
        self._camara()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.visor is None:
            self._fondo_2d(p)
        elif self.mostrar["rejilla"]:
            self._numeros_rejilla(p)
        res = self.resultado
        determinadas = res.determinadas if res is not None else frozenset()
        fijos = self.b.puntos_fijos()
        # lo pegado al origen se ve como restringido (blanco), no como "fijo" (verde), igual que en Fusion
        en_origen = {e for r in self.b.restricciones.values() if r.tipo == "fijo" and r.datos.get("origen")
                     for e in r.entidades}
        fijos_verdes = fijos - en_origen
        en_conflicto = self.geometria_en_conflicto(esperar=False) if res is not None and not res.ok else set()
        self._dibujar_perfiles(p)
        ocultos = set()
        solo_auto, puntos_auto = self.b.ocultos_por_proyeccion_auto()    # no se dibujan (como Fusion)
        for c in self.b.curvas.values():
            if c.id == self._texto_oculto or c.id in solo_auto:
                continue                     # se está editando: se ve la vista previa en vivo
            if not self._visible(c):
                ocultos.update(c.puntos())
                continue
            color, ancho = self._color_curva(c, determinadas | en_origen, fijos_verdes, en_conflicto)
            if self._brillantes is not None and c.id not in self._brillantes:
                color = QColor(color)
                color.setAlphaF(0.2)
            pluma = QPen(color, ancho)
            if c.construccion:
                pluma.setStyle(Qt.DashLine)
            elif c.eje:
                pluma.setStyle(Qt.DashDotLine)
            p.setPen(pluma)
            for poli in self._polilineas(c):
                self._dibujar_polilinea(p, poli)
            if isinstance(c, Spline) and c.modo == "control" and not c.proyectada:
                p.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))      # marco de control, como Fusion
                self._dibujar_polilinea(p, [self.b.coords(q) for q in c.pts])
            if isinstance(c, Conica) and c.id in self.seleccion:
                self._dibujar_guias_conica(p, self.b.coords(c.inicio), self.b.coords(c.vertice), self.b.coords(c.fin))
        if self.mostrar["puntos"]:
            visibles = {q for c in self.b.curvas.values() if self._visible(c) for q in c.puntos()}
            vivos = None if self._brillantes is None else self._brillantes | {
                q for c in self.b.curvas.values() if c.id in self._brillantes for q in c.puntos()}
            ancho, alto = self.width() + 8, self.height() + 8
            for pt in self.b.puntos.values():
                if pt.id in ocultos and pt.id not in visibles or (pt.proyectado and not self.mostrar["proyectadas"]) \
                        or pt.id in puntos_auto:
                    continue
                q = self.a_px(pt.x, pt.y)
                if not (-8 <= q.x() <= ancho and -8 <= q.y() <= alto):
                    continue                          # fuera de la pantalla: no se dibuja
                if pt.id in self.seleccion or pt.id in self.picks:
                    color, relleno = QColor(0, 180, 255), QColor(0, 180, 255)
                elif pt.proyectado:
                    color, relleno = VIOLETA, VIOLETA
                elif pt.id in en_conflicto:
                    color, relleno = CONFLICTO, CONFLICTO
                elif pt.id in fijos_verdes:
                    color, relleno = QColor(70, 200, 100), QColor(70, 200, 100)
                elif pt.id in determinadas or pt.id in en_origen:
                    color = QColor(245, 245, 245) if self._oscuro() else QColor(20, 20, 20)
                    relleno = color
                else:
                    color = QColor(90, 160, 255) if self._oscuro() else QColor(25, 90, 200)
                    relleno = QColor(255, 255, 255)
                if vivos is not None and pt.id not in vivos:
                    color, relleno = QColor(color), QColor(relleno)
                    color.setAlphaF(0.2)
                    relleno.setAlphaF(0.2)
                p.setPen(QPen(color, 1))
                p.setBrush(relleno)
                p.drawRect(QRectF(q.x() - 3, q.y() - 3, 6, 6))
            p.setBrush(Qt.NoBrush)
        self._zonas_glifos = self._dibujar_glifos(p) if self.mostrar["restricciones"] else {}
        if self.herramienta == "seleccionar":
            self._dibujar_casillas_patron(p)
        self._trazos_cotas, self._fondos_cotas = {}, {}   # con las cotas ocultas no se agarra nada
        self._zonas_cotas = self._dibujar_cotas(p) if self.mostrar["cotas"] else {}
        self._dibujar_previa_auto(p)
        self._dibujar_marco(p)
        if self._zona_sobre is not None:                # la cota ya se resalta al dibujarse; el glifo, acá
            rect = self._zonas_glifos.get(self._zona_sobre)
            if rect is not None:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(255, 170, 40), 2))
                p.drawRect(rect.adjusted(-3, -3, 3, 3))
        self._dibujar_previa(p)
        self._dibujar_campos_vivos(p)
        if self._ventana is not None:
            a, b = self._ventana
            relleno, borde = self.colores_ventana(a, b)
            p.setPen(QPen(borde, 1) if borde is not None else Qt.NoPen)
            p.setBrush(relleno)
            p.drawRect(QRectF(a, b).normalized())
        p.end()
        self._notificar_seleccion()          # lo elegido pudo cambiar de tamaño o desaparecer

    def _dibujar_perfiles(self, p):
        """BOC-23: los perfiles elegidos con clic, rellenos en celeste translúcido (como el resaltado de Fusion)."""
        if not self.perfiles_sel:
            return
        from ..nucleo import geometria as geo
        pl = self._plano_perfiles()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 180, 255, 70))
        for perfil in self.perfiles_seleccionados():
            tris = np.asarray(geo.teselar(perfil.cara)[0], float).reshape(-1, 3) - pl.origen
            uv = np.column_stack([tris @ pl.u, tris @ pl.v]).reshape(-1, 3, 2)
            for tri in uv:
                p.drawPolygon(QPolygonF(self._poli_px([tuple(q) for q in tri])))
        p.setBrush(Qt.NoBrush)

    def _casillas_patron(self):
        """[(id del patrón, índice de copia, rectángulo en px, suprimida)] de los patrones que tienen algo elegido: una
        casilla junto a cada copia, marcada si existe (Fusion: se desmarca para suprimir esa instancia). Las suprimidas
        no tienen geometría: su lugar sale de la transformación del patrón aplicada al centro de lo original."""
        from .asas_boceto import centro_de
        elegidas, casillas = set(self.seleccion), []
        for r in self.b.patrones:
            copias = {i for lista in r["copias"].values() for i in lista}
            if not elegidas & (set(r["ids"]) | copias):
                continue
            try:
                trans = self.b._trans_rectangular(r["params"]) if r["tipo"] == "rectangular" \
                    else self.b._trans_circular(r["params"])[0]
            except (ErrorBoceto, KeyError):         # una línea de dirección o un centro que ya no existe: sin casillas
                continue
            centro = centro_de(self, r["ids"])
            for i, (fn, *_) in enumerate(trans):
                q = self.a_px(*fn(centro))
                casillas.append((r["id"], i, QRectF(q.x() + 6, q.y() - 18, 12, 12), i in r["suprimidos"]))
        return casillas

    def _dibujar_casillas_patron(self, p):
        p.save()
        oscuro = self._oscuro()
        for _pid, _i, caja, suprimida in self._casillas_patron():
            p.setPen(QPen(QColor(150, 155, 165) if oscuro else QColor(110, 110, 110), 1))
            p.setBrush(QColor(58, 63, 75, 230) if oscuro else QColor(250, 250, 250, 235))
            p.drawRect(caja)
            if not suprimida:                        # la tilde: la copia existe
                p.setPen(QPen(QColor(0, 180, 255), 2))
                p.drawLine(QPointF(caja.left() + 2.5, caja.center().y()), QPointF(caja.center().x() - 0.5, caja.bottom() - 3))
                p.drawLine(QPointF(caja.center().x() - 0.5, caja.bottom() - 3), QPointF(caja.right() - 2.5, caja.top() + 3))
        p.restore()

    def _clic_casilla_patron(self, pos):
        """Clic en la casilla de una copia: la suprime o la vuelve a crear (un paso de deshacer). True si la tocó."""
        for pid, i, caja, _suprimida in self._casillas_patron():
            if not caja.adjusted(-3, -3, 3, 3).contains(pos):
                continue
            self._alternar_copia_patron(pid, i)
            return True
        return False

    def _alternar_copia_patron(self, pid, i):
        registro = next(r for r in self.b.patrones if r["id"] == pid)
        nuevos, perdidas = set(registro["suprimidos"]) ^ {i}, []
        ok = self.aplicar_cambio(lambda: perdidas.extend(self.b.editar_patron(pid, suprimidos=nuevos)), anclar=False)
        if ok and perdidas:
            self.mensaje.emit("Se borraron porque su copia ya no existe: " + ", ".join(perdidas))

    def _dibujar_glifos(self, p):
        zonas, cuenta, grupos = {}, {}, set()
        en_conflicto = set(self.conflictos_sin_esperar()) if self.resultado is not None and not self.resultado.ok else set()
        p.setPen(QPen(QColor(150, 150, 150), 1))
        for r in self.b.restricciones.values():
            if r.datos.get("origen"):                 # pegado al origen: Fusion no le dibuja ícono aparte
                continue
            grupo = r.datos.get("grupo")
            if grupo is not None:                 # desfase y patrón: un solo glifo por grupo
                if (r.tipo, grupo) in grupos:
                    continue
                grupos.add((r.tipo, grupo))
            ent = r.entidades[-1] if r.tipo in ("coincidente", "punto_medio") else r.entidades[0]
            if r.tipo == "simetrica":
                ent = r.entidades[2]
            elif r.tipo == "desfase" and len(r.entidades) == 4:
                ent = r.entidades[1]
            elif r.tipo == "patron":
                ent = r.entidades[-1] if len(r.entidades) == 3 else r.entidades[1]
            if ent not in self.b.puntos and ent not in self.b.curvas:
                continue
            k = cuenta.get(ent, 0)
            cuenta[ent] = k + 1
            oscuro = self._oscuro()
            lado = 14 if oscuro else 16                # tema oscuro: glifos chicos y discretos, como Fusion
            q = self._ancla(ent) + QPointF(8 + (lado + 2) * k, -18)
            caja = QRectF(q.x() - lado / 2, q.y() - lado / 2, lado, lado)
            seleccionada = r.id in self.seleccion
            if oscuro:
                p.setPen(QPen(QColor(110, 116, 128), 1))
                p.setBrush(QColor(0, 180, 255) if seleccionada else QColor(58, 63, 75, 210))
            else:
                p.setPen(QPen(QColor(150, 150, 150), 1))
                p.setBrush(QColor(0, 180, 255) if seleccionada else QColor(250, 250, 250, 230))
            if r.id in en_conflicto:                    # BOC-7: el glifo que choca, con borde rojo
                p.setPen(QPen(CONFLICTO, 2))
            p.drawRoundedRect(caja, 2, 2)
            pm = icono(ICONO_RESTRICCION.get(r.tipo, "")).pixmap(24, 24)
            if oscuro and r.tipo not in ("fijo", "punto_medio"):
                pm = _tenido(pm, QColor(225, 228, 235))     # sobre el fondo oscuro, glifo claro como Fusion
            p.drawPixmap(caja.adjusted(2, 2, -2, -2), pm, QRectF(0, 0, 24, 24))
            zonas[r.id] = caja
        p.setBrush(Qt.NoBrush)
        return zonas

    def _dibujar_previa_auto(self, p):
        if not self.previa_auto:
            return
        cuenta = {}
        lado = 14 if self._oscuro() else 16
        p.save()
        p.setPen(QPen(VIOLETA, 2))
        p.setBrush(Qt.NoBrush)
        p.setFont(temas.qfont_cotas(9))
        for s in self.previa_auto:
            if not s.entidades or any(e not in self.b.puntos and e not in self.b.curvas for e in s.entidades):
                continue
            ent = s.entidades[0]
            if s.clase == "restriccion":
                if s.tipo in ("coincidente", "punto_medio"):
                    ent = s.entidades[-1]
                elif s.tipo == "simetrica":
                    ent = s.entidades[2]
                elif s.tipo == "desfase" and len(s.entidades) == 4:
                    ent = s.entidades[1]
                elif s.tipo == "patron":
                    ent = s.entidades[-1] if len(s.entidades) == 3 else s.entidades[1]
            k = cuenta.get(ent, 0)
            cuenta[ent] = k + 1
            q = self._ancla(ent)
            if s.clase == "restriccion":
                q += QPointF(8 + (lado + 2) * k, -18)
                caja = QRectF(q.x() - lado / 2, q.y() - lado / 2, lado, lado)
                p.drawRoundedRect(caja, 2, 2)
                pm = _tenido(icono(ICONO_RESTRICCION.get(s.tipo, "")).pixmap(24, 24), VIOLETA)
                p.drawPixmap(caja.adjusted(2, 2, -2, -2), pm, QRectF(0, 0, 24, 24))
            elif s.clase == "cota":
                prefijo = {"radio": "R", "diametro": "⌀"}.get(s.tipo, "")
                unidad = "°" if s.tipo == "angulo" else ""
                texto = f"{prefijo}{formato.numero(s.valor, angular=s.tipo == 'angulo')}{unidad}"
                p.drawText(q + QPointF(10, 18 + 18 * k), texto)
        p.restore()

    def _flecha(self, p, punta, desde):
        ang = math.atan2(punta.y() - desde.y(), punta.x() - desde.x())
        p.drawPolygon(QPolygonF([punta, punta - QPointF(math.cos(ang - 0.35) * 7, math.sin(ang - 0.35) * 7),
                                 punta - QPointF(math.cos(ang + 0.35) * 7, math.sin(ang + 0.35) * 7)]))

    @staticmethod
    def _auxiliar_cota(desde, hasta):
        """Línea auxiliar como Fusion: 3 px de hueco desde la geometría y 4 px pasada la línea de cota."""
        dx, dy = hasta.x() - desde.x(), hasta.y() - desde.y()
        largo = math.hypot(dx, dy)
        if largo <= 4:
            return None
        ux, uy = dx / largo, dy / largo
        return (QPointF(desde.x() + ux * 3, desde.y() + uy * 3),
                QPointF(hasta.x() + ux * 4, hasta.y() + uy * 4))

    @staticmethod
    def _texto_cota(c, valor):
        """Lo que se lee en la cota: el valor con su prefijo; entre paréntesis si es de referencia (driven) y con
        «fx:» delante si sale de una expresión (Fusion). Con la unidad: «20 mm» (la del documento) o «90°»."""
        angular = c.tipo == "angulo"
        unidad = "°" if angular else f" {formato.sufijo()}"
        prefijo = {"radio": "R", "diametro": "⌀"}.get(c.tipo, "")
        texto = f"{prefijo}{formato.numero(valor if angular else formato.longitud(valor), angular=angular)}{unidad}"
        if c.referencia:
            return f"({texto})"
        return texto if _es_numero(c.expresion) else f"fx: {texto}"

    def _dibujar_cotas(self, p):
        """Cotas como las de Fusion: líneas y texto en verde oliva sobre fondo oscuro (gris oscuro sobre
        fondo claro), el valor SIN caja, al costado de la línea de cota, con un fondo redondeado del color
        del lienzo para que se lea sobre cualquier línea. La caja con borde aparece solo al editarla
        (doble clic). Los textos no se pisan (ni entre ellos ni con los íconos de restricción)."""
        zonas, ocupadas = {}, list(self._zonas_glifos.values())
        trazos = self._trazos_cotas = {}              # por cota, las rayas donde se puede agarrar (no el texto)
        fondos = self._fondos_cotas = {}              # por cota, la caja del fondo de su texto
        actual = []

        def raya(a, b):
            p.drawLine(a, b)
            actual.append((a, b))
        base = self._color_cota()
        en_conflicto = set(self.conflictos_sin_esperar()) if self.resultado is not None and not self.resultado.ok else set()
        desfase = 22 / max(self.px_por_mm(), 1e-9)       # 22 px expresados en mm del boceto
        p.setFont(temas.qfont_cotas(9))
        fm = p.fontMetrics()
        pts = [self.b.coords(k) for k in self.b.puntos]
        centroide = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)) if pts else (0.0, 0.0)
        viva = self._cota_viva()
        for c in [*self.b.cotas.values(), *([viva] if viva is not None else [])]:
            actual.clear()
            girar = None                             # ángulo del texto (grados) en las cotas lineales
            try:
                valor = self.b.medir(c)
            except (ErrorBoceto, KeyError, ZeroDivisionError):
                continue
            texto = self._texto_cota(c, valor)
            resaltada = c.id == self._zona_sobre and c.id >= 0
            color = (QColor(0, 180, 255) if c.id in self.seleccion or (c.id == self._cita_sobre and self.entrada is not None)
                     else CONFLICTO if c.id in en_conflicto
                     else self._color_resalte() if resaltada
                     else REFERENCIA if c.referencia else base)
            p.setPen(QPen(color, 1))
            p.setBrush(color)
            afuera = QPointF(0, -1)                  # hacia dónde se aleja el texto de la línea de cota
            marco = self.b.ejes_cota(c)
            if marco is not None:
                a, b, u, n, s0 = marco
                off = c.datos.get("desfase")        # si el usuario la movió, manda su posición guardada
                if off is None:
                    off = desfase
                    if c.tipo == "distancia":        # del lado de afuera de la figura, como Fusion
                        medio = ((a[0] + b[0]) / 2 - centroide[0], (a[1] + b[1]) / 2 - centroide[1])
                        if medio[0] * n[0] + medio[1] * n[1] < 0:
                            off = -off
                s = s0 + off
                ua, ub = a[0] * u[0] + a[1] * u[1], b[0] * u[0] + b[1] * u[1]
                da = (u[0] * ua + n[0] * s, u[1] * ua + n[1] * s)
                db = (u[0] * ub + n[0] * s, u[1] * ub + n[1] * s)
                um = (ua + ub) / 2 + c.datos.get("texto", 0.0)
                qa, qb, pa, pb = self.a_px(*da), self.a_px(*db), self.a_px(*a), self.a_px(*b)
                auxiliares = [self._auxiliar_cota(pa, qa), self._auxiliar_cota(pb, qb)]
                for aux in auxiliares:
                    if aux is not None:
                        p.drawLine(*aux)
                raya(qa, qb)
                actual.extend(aux for aux in auxiliares if aux is not None)
                self._flecha(p, qa, qb)
                self._flecha(p, qb, qa)
                q = self.a_px(u[0] * um + n[0] * s, u[1] * um + n[1] * s)
                d = (qa + qb) / 2 - (pa + pb) / 2
                largo = math.hypot(d.x(), d.y())
                if largo > 1e-6:
                    afuera = d / largo
                girar = math.degrees(math.atan2(qb.y() - qa.y(), qb.x() - qa.x()))
                if girar > 90:
                    girar -= 180
                elif girar <= -90:
                    girar += 180
            elif c.tipo in ("radio", "diametro"):
                cent = self.b.coords(self.b.curvas[c.entidades[0]].centro)
                r = self.b.radio(c.entidades[0])
                ubic = c.datos.get("ubic")              # arrastrada: la línea sale hacia donde se la dejó
                ang = math.atan2(ubic[1] - cent[1], ubic[0] - cent[0]) if ubic else math.pi / 4
                dx, dy = math.cos(ang), math.sin(ang)
                borde = self.a_px(cent[0] + r * dx, cent[1] + r * dy)
                q = self.a_px(*ubic) if ubic else borde + QPointF(26, -18)
                raya(self.a_px(*cent) if c.tipo == "radio" else self.a_px(cent[0] - r * dx, cent[1] - r * dy), borde)
                if q != borde:
                    raya(borde, q)
                self._flecha(p, borde, self.a_px(*cent))
                afuera = QPointF(dx, -dy) if ubic else QPointF(1, 0)
            elif c.tipo == "angulo" and self._arco_cota(c) is not None:
                o, t0, t1 = self._arco_cota(c)
                ubic = c.datos.get("ubic")              # arrastrada: el radio del arco llega hasta donde se la dejó
                r = max(math.dist(o, ubic), 1e-6) if ubic else 40 / max(self.px_por_mm(), 1e-9)
                pasos = max(4, int(abs(t1 - t0) / 0.08))
                arco = [self.a_px(o[0] + r * math.cos(t0 + (t1 - t0) * i / pasos),
                                  o[1] + r * math.sin(t0 + (t1 - t0) * i / pasos)) for i in range(pasos + 1)]
                for a, b in zip(arco, arco[1:], strict=False):
                    raya(a, b)
                if abs(t1 - t0) > 0.15:
                    self._flecha(p, arco[0], arco[1])
                    self._flecha(p, arco[-1], arco[-2])
                tm = (t0 + t1) / 2
                q = self.a_px(o[0] + r * math.cos(tm), o[1] + r * math.sin(tm))
                d = q - self.a_px(*o)
                afuera = d / (math.hypot(d.x(), d.y()) or 1.0)
            else:
                anclas = [self._ancla(e) for e in c.entidades]
                q = sum(anclas[1:], anclas[0]) / len(anclas) + QPointF(0, 12)
                afuera = QPointF(0, 1)
                if "ubic" in c.datos:                   # arrastrada: el texto va donde se la dejó, con una guía fina
                    p.drawLine(q, self.a_px(*c.datos["ubic"]))
                    q, afuera = self.a_px(*c.datos["ubic"]), QPointF(0, 0)
            w, h = fm.horizontalAdvance(texto) + 4, fm.height()
            if girar is not None:                    # texto a lo largo de la línea: se aleja medio alto
                centro = q + afuera * (h / 2 + 1)
            else:
                centro = q + afuera * ((abs(afuera.x()) * w + abs(afuera.y()) * h) / 2 + 2)
            if girar is not None and abs(girar) > 1:     # el texto girado ocupa el rectángulo girado, no w × h
                cos, sin = abs(math.cos(math.radians(girar))), abs(math.sin(math.radians(girar)))
                caja = QRectF(0, 0, w * cos + h * sin, w * sin + h * cos)
                caja.moveCenter(centro)
            else:
                caja = QRectF(centro.x() - w / 2, centro.y() - h / 2, w, h)
            paso = QPointF(afuera.x() * (w + 4), afuera.y() * (h + 2))
            if math.hypot(paso.x(), paso.y()) < 1:
                paso = QPointF(0, h + 2)
            for _ in range(0 if "texto" in c.datos or "ubic" in c.datos else 20):   # un texto ubicado no se corre
                if not any(caja.intersects(o) for o in ocupadas):
                    break
                caja.translate(paso)
            ocupadas.append(caja)
            if c.id >= 0:
                zonas[c.id] = caja
                trazos[c.id] = list(actual)
            if c.id != self._cota_editada:
                girado = girar is not None and abs(girar) > 1
                fondo = QRectF(-w / 2 - 3, -h / 2 - 2, w + 6, h + 4) if girado else caja.adjusted(-3, -2, 3, 2)
                if c.id >= 0:
                    if girado:
                        cos, sin = abs(math.cos(math.radians(girar))), abs(math.sin(math.radians(girar)))
                        fondos[c.id] = QRectF(0, 0, (w + 6) * cos + (h + 4) * sin, (w + 6) * sin + (h + 4) * cos)
                        fondos[c.id].moveCenter(caja.center())
                    else:
                        fondos[c.id] = QRectF(fondo)
                p.save()
                if girado:
                    p.translate(caja.center())
                    p.rotate(girar)
                p.setPen(Qt.NoPen)
                p.setBrush(self._color_fondo())
                p.drawRoundedRect(fondo, 3, 3)
                if resaltada:
                    tinte = self._color_resalte()
                    tinte.setAlpha(32)
                    p.setBrush(tinte)
                    p.drawRoundedRect(fondo, 3, 3)
                p.setPen(color)
                p.setBrush(color)
                p.drawText(QRectF(-w / 2, -h / 2, w, h) if girado else caja, Qt.AlignCenter, texto)
                p.restore()
        p.setBrush(Qt.NoBrush)
        return zonas

    # ------------------------------------------------------------ vistas previas
    def _dibujar_guias_conica(self, p, inicio, vertice, fin):
        """Las rectas extremo–vértice son las tangentes de la cónica en sus extremos."""
        p.save()
        p.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))
        self._dibujar_polilinea(p, [inicio, vertice, fin])
        p.restore()

    def _tramo_a_recortar(self, pos):
        """Polilínea (u, v) del tramo que quitaría Recortar con el cursor en `pos` (para resaltarlo)."""
        cid = self._curva_cercana(pos)
        if cid is None or isinstance(self.b.curvas[cid], Texto) or self.b.curvas[cid].proyectada:
            return None
        clave = (cid, len(self.historial))
        if clave not in self._cache_cortes:
            try:
                self._cache_cortes[clave] = [t for t, _xy, _o in self.b._cortes(cid)]
            except (ErrorBoceto, ValueError, ZeroDivisionError):
                return None
        ts = self._cache_cortes[clave]
        prim = self.b.primitivas(cid)[0]
        t0, t1, per = dominio(prim)
        tc = mas_cercano(prim, self.a_mm(pos))[0]
        antes, despues = [t for t in ts if t < tc], [t for t in ts if t > tc]
        if per:
            if len(ts) < 2:
                lo, hi = t0, t1
            else:
                lo = antes[-1] if antes else ts[-1] - (t1 - t0)
                hi = despues[0] if despues else ts[0] + (t1 - t0)
        else:
            lo, hi = (antes[-1] if antes else t0), (despues[0] if despues else t1)
        n = 32
        return [evaluar_primitiva(prim, lo + (hi - lo) * i / n)[0] for i in range(n + 1)]

    def _temporal(self, construir):
        """Geometría de una vista previa: se arma en un boceto aparte (sin tocar el real)."""
        tmp = Boceto()
        try:
            construir(tmp)
        except (ErrorBoceto, ValueError, ZeroDivisionError, IndexError):
            return []
        return [puntos_primitiva(prim) for prim in tmp.geometria(incluir_construccion=True)]

    def _dibujar_previa(self, p):
        h, cur = self.herramienta, self._cursor_efectivo()      # con los valores escritos ya aplicados
        # Fusion dibuja la vista previa como geometría sin restringir: azul y continua
        acento = QColor(90, 160, 255) if self._oscuro() else QColor(25, 90, 200)
        if self._previa_polis or self._caret is not None or (self._previa_texto and self._previa_texto.get("caja")):
            if self._sel_texto:                    # lo seleccionado del texto que se escribe
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(acento.red(), acento.green(), acento.blue(), 80))
                for cuadro in self._sel_texto:
                    p.drawPolygon(QPolygonF([self.a_px(*q) for q in cuadro]))
                p.setBrush(Qt.NoBrush)
            p.setPen(QPen(acento, 2.0))
            for poli in self._previa_polis:
                self._dibujar_polilinea(p, poli)
            if self._caret is not None and self._caret_on and self.hasFocus():
                p.setPen(QPen(QColor(245, 245, 245) if self._oscuro() else QColor(20, 20, 20), 2.0))
                self._dibujar_polilinea(p, list(self._caret))     # el cursor parpadeante: acá se escribe
            caja = (self._previa_texto or {}).get("caja")
            if not caja and self._previa_polis:     # texto ya creado: el cuadro es el que lo envuelve
                xs = [q[0] for poli in self._previa_polis for q in poli]
                ys = [q[1] for poli in self._previa_polis for q in poli]
                caja = (min(xs), min(ys), max(xs), max(ys))
            if caja:                         # el cuadro dibujado con el ratón, en línea de trazos
                x0, y0, x1, y1 = caja
                p.setPen(QPen(acento, 1, Qt.DashLine))
                self._dibujar_polilinea(p, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
        if h == "recortar" and self._previa_recorte:
            p.setPen(QPen(QColor(230, 60, 60), 3, Qt.DashLine))
            self._dibujar_polilinea(p, self._previa_recorte)
        if self._asas is not None:
            self._asas.dibujar(p)
        if h == "desfase" and self.picks and self.entrada is not None and cur is not None:
            try:                       # el desfase sigue al ratón: el lado es donde está el cursor
                d = self.evaluar(self.entrada.campos[0].text())
                copia = self.b.copia()
                nuevos = copia.desfase(self.picks[0], abs(d), cur if d >= 0 else self._lado_opuesto(self.picks[0], cur))
                p.setPen(QPen(acento, 2.0))
                for k in nuevos:
                    for prim in copia.primitivas(k):
                        self._dibujar_polilinea(p, puntos_primitiva(prim))
            except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError):
                pass
        if cur is not None and self._tangente is not None:
            inicio, linea = self._tangente
            p.setPen(QPen(acento, 2.0))
            p.drawLine(self.a_px(*self.b.coords(inicio)), self.a_px(*cur))
        elif self.clics and cur is not None:
            p.setPen(QPen(acento, 2.0))
            a = self.clics[0][1]
            pts = [c[1] for c in self.clics]
            polis = []
            if h in ("linea", "linea_medio"):
                ini = self.clics[-1][1] if h == "linea" else (2 * a[0] - cur[0], 2 * a[1] - cur[1])
                if h == "linea" and self.inf_actual is not None and self.inf_actual.guias:
                    p.setPen(QPen(acento, 1.5, Qt.DashLine))
                p.drawLine(self.a_px(*ini), self.a_px(*cur))
            elif h == "rectangulo" or (h == "texto" and self.entrada is None):
                self._dibujar_polilinea(p, [a, (cur[0], a[1]), cur, (a[0], cur[1]), a])
            elif h == "rectangulo_centro":
                k = cur
                o = (2 * a[0] - k[0], 2 * a[1] - k[1])
                self._dibujar_polilinea(p, [o, (k[0], o[1]), k, (o[0], k[1]), o])
                p.setPen(QPen(QColor(205, 205, 210) if self._oscuro() else QColor(240, 150, 60), 1.2, Qt.DashLine))
                self._dibujar_polilinea(p, [o, k])                  # diagonales de construcción, como Fusion
                self._dibujar_polilinea(p, [(k[0], o[1]), (o[0], k[1])])
                p.setPen(QPen(acento, 2.0))
            elif h == "rectangulo_3p" and len(pts) == 2:
                ub = _unitario(pts[1][0] - a[0], pts[1][1] - a[1])
                d = (cur[0] - a[0]) * -ub[1] + (cur[1] - a[1]) * ub[0]
                n = (-ub[1] * d, ub[0] * d)
                self._dibujar_polilinea(p, [a, pts[1], (pts[1][0] + n[0], pts[1][1] + n[1]), (a[0] + n[0], a[1] + n[1]), a])
            elif h == "rectangulo_3p":
                self._dibujar_polilinea(p, pts + [cur])
            elif h in ("poligono_inscrito", "poligono_circunscrito") and math.dist(a, cur) > 1e-9:
                tipo = "inscrito" if h == "poligono_inscrito" else "circunscrito"
                r, esquinas = _vertices_poligono(a, cur, self.lados, tipo)
                self._dibujar_polilinea(p, esquinas + esquinas[:1])
                p.setPen(QPen(acento, 1, Qt.DotLine))           # el círculo de construcción
                self._dibujar_polilinea(p, [(a[0] + r * math.cos(2 * math.pi * i / 64), a[1] + r * math.sin(2 * math.pi * i / 64))
                                            for i in range(65)])
            elif h == "arco" and len(pts) == 2:
                polis = self._temporal(lambda t: t.agregar_arco_3_puntos(pts[0], cur, pts[1]))
            elif h == "arco_centro" and len(pts) == 2 and math.dist(a, pts[1]) > 1e-9:
                r = math.dist(a, pts[1])
                ang = math.atan2(cur[1] - a[1], cur[0] - a[0])
                fin = (a[0] + r * math.cos(ang), a[1] + r * math.sin(ang))
                if self._sentido_barrido() > 0:
                    polis = self._temporal(lambda t: t.agregar_arco_centro(a, pts[1], fin))
                else:
                    polis = self._temporal(lambda t: t.agregar_arco_centro(a, fin, pts[1]))
            elif h in ("circulo", "circulo_2p", "poligono_inscrito", "poligono_circunscrito", "espiral"):
                if h == "circulo_2p":
                    centro, r = ((a[0] + cur[0]) / 2, (a[1] + cur[1]) / 2), math.dist(a, cur) / 2
                else:
                    centro, r = a, math.dist(a, cur)
                circ = [(centro[0] + r * math.cos(2 * math.pi * i / 64), centro[1] + r * math.sin(2 * math.pi * i / 64))
                        for i in range(65)]
                self._dibujar_polilinea(p, circ)
            elif h == "elipse" and len(pts) == 2:
                m = pts[1]
                aa = math.dist(a, m) or 1e-9
                b = abs((m[0] - a[0]) * (cur[1] - a[1]) - (m[1] - a[1]) * (cur[0] - a[0])) / aa
                polis = self._temporal(lambda t: t.agregar_elipse(a, m, max(b, 1e-3), ejes=True))
            elif h.startswith("ranura_") and len(pts) >= (2 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 3):
                tipo = h[len("ranura_"):]
                n = 2 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 3
                ancho = 2 * self._ancho_ranura(h, self.clics[:n], cur)
                polis = self._temporal(lambda t: t.agregar_ranura(tipo, pts[:n], max(ancho, 1e-3)))
            elif h in SPLINES:
                todos = pts + [cur]
                if h == "spline_ajuste":
                    polis = self._temporal(lambda t: t.agregar_spline(todos, "ajuste"))
                else:
                    polis = self._temporal(lambda t: t.agregar_spline(todos, "control", self.opciones["grado_spline"]))
                    p.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))
                    self._dibujar_polilinea(p, todos)
                    p.setPen(QPen(acento, 1.5, Qt.DashLine))
            elif h == "conica" and len(pts) >= 2:
                vertice = pts[2] if len(pts) == 3 else cur
                rho = 0.5
                if len(pts) == 3 and self.entrada is not None:
                    try:
                        rho = _numero(self.entrada.campos[0].text() or "0.5")
                    except ValueError:
                        rho = 0.0
                self._dibujar_guias_conica(p, a, vertice, pts[1])
                if 0 < rho < 1:
                    polis = self._temporal(lambda t: t.agregar_conica(a, vertice, pts[1], rho))
                    if len(pts) == 3:
                        medio = ((a[0] + pts[1][0]) / 2, (a[1] + pts[1][1]) / 2)
                        p.setPen(QPen(acento, 1, Qt.DashLine))
                        self._dibujar_polilinea(p, [medio, vertice])
                        asa = self.a_px(medio[0] + rho * (vertice[0] - medio[0]),
                                        medio[1] + rho * (vertice[1] - medio[1]))
                        p.drawRect(QRectF(asa.x() - 4, asa.y() - 4, 8, 8))
                        p.setPen(QPen(acento, 2.0))
            elif h in ("circulo_3p", "arco", "arco_centro", "arco_tangente", "poligono_arista", "conica") \
                    or h.startswith("ranura_"):
                self._dibujar_polilinea(p, pts + [cur])
            for poli in polis:
                self._dibujar_polilinea(p, poli)
        if h == "mover" and self.fase == "destino" and cur is not None:
            base = self._base
            p.setPen(QPen(acento, 1.5, Qt.DashLine))
            for i in self._seleccion_util():
                if i in self.b.curvas:
                    for poli in self._polilineas(self.b.curvas[i], 32):
                        self._dibujar_polilinea(p, [(q[0] + cur[0] - base[0], q[1] + cur[1] - base[1]) for q in poli])
        if cur is not None and self.herramienta not in ("seleccionar",) and self.visor is not None \
                and self.entrada is None:
            q = self.a_px(*cur)
            p.setPen(QPen(acento, 1))
            p.drawEllipse(q, 4, 4)
        elif cur is not None and self.visor is None and self.herramienta != "seleccionar":
            q = self.a_px(*cur)
            p.setPen(QPen(acento, 1))
            p.drawEllipse(q, 4, 4)
            if not self._claves_vivas():           # con cajas de valor, las coordenadas estorban
                p.setPen(QPen(QColor(80, 80, 90), 1))
                p.drawText(q + QPointF(10, -8), f"({cur[0]:.2f}; {cur[1]:.2f})")
        if cur is not None and self.inf_actual is not None and h != "seleccionar" and self.entrada is None:
            p.setPen(QPen(acento, 1, Qt.DashLine))
            for guia in self.inf_actual.guias:
                self._dibujar_polilinea(p, guia)
            q = self.a_px(*cur)
            tipo = self.inf_actual.restriccion[0] if self.inf_actual.restriccion else "coincidente"
            nombre = ICONO_RESTRICCION.get(tipo, "r_coincidente")
            p.drawPixmap(QRectF(q.x() + 10, q.y() + 6, 14, 14), icono(nombre).pixmap(28, 28),
                         QRectF(0, 0, 28, 28))

    def describir(self, ids):
        return ", ".join(f"{NOMBRES_ENTIDAD[self.b.tipo_de(i)]} {i}" for i in ids if i in self.b.puntos or i in self.b.curvas)
