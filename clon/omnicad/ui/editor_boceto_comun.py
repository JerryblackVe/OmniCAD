import copy
import math
import re
import threading
import time
import warnings
from dataclasses import replace

import numpy as np

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFontMetricsF, QKeySequence, QMouseEvent, QPainter, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
                               QToolButton, QToolTip, QWidget)

from ..nucleo import fuentes
from ..restricciones import (Boceto, ErrorBoceto, TIPOS_COTA, TIPOS_RESTRICCION, auto_restringir, grados_de_libertad,
                             resolver)
from ..restricciones.solver import (acomodar_segunda, acomodar_tangente, restricciones_en_conflicto, restricciones_redundantes,
                                     restriccion_quita_grados)
from ..restricciones.inferencia import Indice, TIPOS_INFERENCIA, inferencias, proyectar_bloqueo
from ..restricciones.boceto import (Arco, Circulo, Conica, Cota, Linea, Spline, Texto, agregar_linea_medio, agregar_rectangulo_3p,
                                    aviso_radio_empalme, aviso_tangencias_fuera,
                                    agregar_arco_tangente, agregar_circulo_puntos, agregar_estrella, agregar_poligono,
                                    agregar_rectangulo_centro, cambiar_radio, centro_arco_tangente,
                                    centro_poligono_arista, circunferencia_3_puntos, dominio,
                                    evaluar_primitiva, expresion_sin_signo, fraccion_en_camino, lado_natural, mas_cercano, paradas_cursor,
                                    primitivas_entidad, proporcion_estrella, puntos_espiral, puntos_primitiva,
                                    redondear_estrella, redondeos_estrella, validar_lados_poligono, validar_puntas_estrella,
                                    validar_valor_cota, vertices_estrella, vertices_poligono,
                                    _validar_opciones_texto)
from ..timeline.parametros import (ANGULO, ESCALAR, LONGITUD, ErrorExpresion, nombres_usados, separar_nombre,
                                   validar_nombre)
from .. import registro_uso as _ru
from . import formato, temas
from .campo_expresion import autocompletar
from .iconos import icono
from .patron_boceto import ControlPatron, dibujar_casilla
from .transformar_boceto import ControlTransformar

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
    "estrella": ("Estrella", "Clic en el centro y clic en una punta (o escribí el radio, Tab, la cantidad de "
                 "puntas). Interior y redondeos, en la tarjeta."),
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
    "simetria": ("Simetría", "Elegí la geometría y la línea de simetría en el panel. Aceptar o Enter crea la copia."),
    "patron_rectangular": ("Patrón rectangular", "Seleccioná la geometría y Enter; escribí cantidad y distancia "
                           "en cada dirección (X e Y del boceto)."),
    "patron_circular": ("Patrón circular", "Seleccioná la geometría, Enter y clic en el centro; escribí la "
                        "cantidad y el ángulo total."),
    "proyectar": ("Proyectar", "Elegí aristas, caras, vértices o cuerpos del modelo y revisá la vista previa. Aceptar o "
                  "Enter los proyecta sobre el plano del boceto (violeta, fijos); Esc cancela."),
    "intersecar": ("Intersecar", "Elegí caras, aristas o cuerpos y revisá la vista previa. Aceptar o Enter agrega las "
                   "curvas donde cortan el plano del boceto; Esc cancela."),
    "incluir_3d": ("Incluir geometría 3D", "Clic en aristas o vértices del modelo: quedan en el boceto donde están, "
                   "como curvas y puntos 3D (para llevarlos al plano, Proyectar)."),
    "proyectar_eje": ("Proyectar eje", "Proyecta el eje del perfil giratorio elegido en la tarjeta sobre el plano "
                      "del boceto, con el vínculo de proyección elegido."),
    "isoparametrica": ("Curva isoparamétrica", "Clic en un punto de una cara del modelo: saca sus curvas U, V o ambas "
                       "(una sola o distribuidas) como curvas 3D del boceto. Opciones en la tarjeta."),
    "perfil_giratorio": ("Perfil giratorio", "Clic en aristas, caras o cuerpos del modelo: se giran alrededor del "
                         "eje de la tarjeta y su perfil queda en el boceto. Con eje «Arista», el primer clic elige "
                         "una arista recta como eje."),
    "cota": ("Cota de boceto", "Clic en una línea, círculo o arco (o en dos entidades) y clic para ubicar; "
             "escribí el valor o una expresión y Enter. Mayús + doble clic en una cota: de referencia ↔ driving."),
    "empalme": ("Empalme", "Clic en un vértice o dos curvas; escribí el radio y Enter."),
    "chaflan": ("Chaflán de distancias iguales", "Clic en un vértice o dos líneas; escribí la distancia y Enter."),
    "chaflan_dist_angulo": ("Chaflán de distancia y ángulo", "Clic en un vértice o dos líneas; escribí distancia y ángulo."),
    "chaflan_dos_dist": ("Chaflán de dos distancias", "Clic en un vértice o dos líneas; escribí las dos distancias."),
    "curva_fusion": ("Curva de fusión", "Clic cerca del extremo de una curva y cerca del extremo de otra "
                     "(G1 o G2 en la tarjeta)."),
    "desfase": ("Desfase", "Clic en una curva (se toma la cadena conectada), arrastrá el asa o escribí la distancia "
                "(negativa = al otro lado) y Enter."),
    "recortar": ("Recortar", "Clic en el tramo a quitar (hasta las intersecciones más cercanas)."),
    "alargar": ("Alargar", "Clic cerca del extremo de una línea o un arco para llevarlo a la próxima intersección."),
    "partir": ("Partir", "Clic en una curva para partirla en las intersecciones más cercanas."),
    "escala": ("Escala del boceto", "Elegí la geometría y el punto base; escribí el factor (o tirá del asa) y Aceptar."),
    "mover": ("Mover/copiar", "Elegí la geometría y el punto base; clic en el destino o escribí ΔX, ΔY y el ángulo, y "
              "Aceptar. «Crear copia» deja el original."),
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
                       "r_simetria": "Simetría", "r_curvatura": "Curvatura", "r_poligono": "Polígono regular"}
# Qué pedir en cada herramienta: sale en el cartel del botón y en el mensaje de la barra al activarla
AYUDA_RESTRICCION = {
    "r_horizontal_vertical": "líneas o dos puntos.",
    "r_coincidente": "elegí un punto y otro punto, o un punto y una curva: quedan unidos.",
    "r_tangente": "elegí dos curvas (línea, círculo, arco, elipse, spline): se tocan en un solo punto sin cruzarse.",
    "r_igual": "elegí dos líneas, dos círculos o arcos, o dos elipses: miden lo mismo.",
    "r_paralela": "elegí dos líneas: quedan en la misma dirección.",
    "r_perpendicular": "elegí dos líneas, o una línea y una spline: forman 90°.",
    "r_fijo": "elegí geometría para dejarla fija en su lugar; sobre algo ya fijo se anula la fijación.",
    "r_punto_medio": "elegí un punto y una línea (o un arco): el punto queda justo en el medio.",
    "r_concentrica": "elegí dos círculos, arcos o elipses: comparten el centro.",
    "r_colineal": "elegí dos líneas: quedan sobre la misma recta.",
    "r_simetria": "elegí dos puntos (o dos curvas del mismo tipo) y al final la línea de simetría.",
    "r_curvatura": "elegí una spline y la curva que se une a ella por un extremo: la unión queda suave (G2).",
    "r_poligono": "elegí un lado de una cadena cerrada de líneas: queda un polígono regular (lados y vértices iguales).",
}
# Detalle que no cabe en el cartel de 1 renglón: va en el tooltip / Ctrl+/ del botón (regla 14, P-158g)
DETALLE_RESTRICCION = {
    "r_tangente": AYUDA_RESTRICCION["r_tangente"] + " Si el contacto cae fuera del tramo dibujado del arco, la tangencia vale para "
                  "su círculo entero: mové la línea o alargá el arco para que se toquen.",
    "r_horizontal_vertical": "elegí una o más líneas, o dos puntos: quedan horizontales o verticales, según lo que "
                             "tengan más cerca."}
ICONO_RESTRICCION = {"horizontal": "r_horizontal", "vertical": "r_vertical",
                     "coincidente": "r_coincidente", "paralela": "r_paralela", "perpendicular": "r_perpendicular",
                     "igual": "r_igual", "tangente": "r_tangente", "concentrica": "r_concentrica",
                     "punto_medio": "r_punto_medio", "fijo": "r_fijo", "colineal": "r_colineal",
                     "simetrica": "r_simetria", "curvatura": "r_curvatura", "poligono": "r_poligono",
                     "desfase": "desfase", "patron": "patron_rectangular"}
LADO_SIMBOLO = 18      # px: el cuadrito de cada restricción. A 14 px el dibujo quedaba en 10 px y una de las dos rayas de «=» se veía a medio tono
# Relaciones entre dos curvas: el símbolo aparece junto a cada una (Fusion), no solo junto a la primera
RELACION_ENTRE_DOS = ("paralela", "perpendicular", "igual", "colineal", "tangente", "concentrica", "curvatura")
NOMBRES_ENTIDAD = {"punto": "punto", "linea": "línea", "circulo": "círculo", "arco": "arco", "elipse": "elipse",
                   "arco_elipse": "arco de elipse", "spline": "spline", "conica": "cónica", "texto": "texto"}
# Herramientas que piden curvas (clic sobre la geometría): cuántas y de qué tipos.
PICKS = {"circulo_2t": (2, ("linea",)), "circulo_3t": (3, ("linea",)), "empalme": (2, ("linea", "arco", "circulo")),
         "chaflan": (2, ("linea",)), "chaflan_dist_angulo": (2, ("linea",)), "chaflan_dos_dist": (2, ("linea",)),
         "curva_fusion": (2, None), "desfase": (1, None), "recortar": (1, None), "alargar": (1, None),
         "partir": (1, None), "desglosar_texto": (1, ("texto",))}
SELECCION = ("simetria", "patron_rectangular", "patron_circular", "escala", "mover")
PATRON = ("patron_rectangular", "patron_circular")     # los maneja `ControlPatron` (ui/patron_boceto.py)
TRANSFORMAR = ("escala", "mover")                      # los maneja `ControlTransformar` (ui/transformar_boceto.py)
SPLINES = ("spline_ajuste", "spline_control")
PROYECCION = ("proyectar", "intersecar", "incluir_3d", "perfil_giratorio", "isoparametrica")
COMANDO_PROYECCION = ("proyectar", "intersecar")        # con tarjeta: se elige, se revisa la vista previa y se acepta
CAPA_PROYECCION = "proyeccion_elegida"                  # capa del visor con lo elegido en la tarjeta
CURVA_TEXTO = ("camino_lado", "camino_colocacion", "camino_desfase", "camino_ajustar")      # opciones del texto sobre una curva
MODIFICAN = tuple(PICKS) + SELECCION + PROYECCION       # no aplican el tipo de línea a lo que crean
PORTAPAPELES = {}         # Ctrl+C / Ctrl+V entre bocetos: {"boceto": copia del origen, "ids": [...]}
VIOLETA = QColor(170, 90, 230)
TOL_PX = 8.0
TOL_PUNTO = 11.0          # radio (px) para agarrar un punto: más grande que lo que se ve
TOL_MANIJA = 12.0         # radio (px) de las manijas del marco de control
RADIO_INTERIOR_PX = 80.0  # círculos de hasta este radio en pantalla se agarran también desde adentro
TOL_INFERENCIA = math.radians(3.0)
EJES_ORIGEN = {Boceto.EJE_X: ((0.0, 0.0), (1.0, 0.0)), Boceto.EJE_Y: ((0.0, 0.0), (0.0, 1.0))}   # extremos de los ejes del origen
# Ayudas de dibujo (Preferencias › Boceto): `inferencias` y `restricciones_auto` apagan las ayudas y las restricciones
# que dejan al confirmar; `tipos` elige las familias de TIPOS_INFERENCIA; `sensibilidad_px` es el radio de captura.
AJUSTES_INFERENCIA = {"inferencias": True, "restricciones_auto": True, "tipos": TIPOS_INFERENCIA,
                      "sensibilidad_px": TOL_PX, "guias": True, "indicadores": True, "etiquetas": True}


def ajustes_inferencia(prefs):
    """Los ajustes de ayudas de dibujo a partir de las preferencias de la aplicación (claves «boceto/…»)."""
    familias = ("medio", "interseccion", "tangente", "perpendicular", "curva", "alineacion", "paralela", "igual")
    tipos = [t for t in familias if prefs[f"boceto/inf_{t}"]]
    if prefs["boceto/inf_horizontal_vertical"]:
        tipos += ["horizontal", "vertical"]
    return {"inferencias": prefs["boceto/inferencias"], "restricciones_auto": prefs["boceto/restricciones_auto"],
            "tipos": tuple(tipos), "sensibilidad_px": float(prefs["boceto/sensibilidad_px"]),
            "guias": prefs["boceto/guias_inferencia"], "indicadores": prefs["boceto/indicadores_inferencia"],
            "etiquetas": prefs["boceto/etiquetas_inferencia"]}
# Cotas en vivo mientras se dibuja (las cajas de valor de Fusion): herramientas que las muestran.
RANURAS_RECTAS = ("ranura_centro", "ranura_total", "ranura_punto")
VIVAS = ("linea", "rectangulo", "rectangulo_3p", "rectangulo_centro", "circulo", "arco", "arco_centro",
         "poligono_inscrito", "poligono_circunscrito", "circulo_2p", "linea_medio", "elipse", "arco_tangente",
         "poligono_arista", "estrella") + RANURAS_RECTAS + ("ranura_arco_3p", "ranura_arco_centro")
ANGULARES = ("angulo", "barrido")
# Colores de Fusion: cotas verde oliva sobre el fondo oscuro (#2d323f); gris oscuro sobre fondo claro.
COTA_OSCURO, COTA_CLARO = QColor(0xa9, 0xc4, 0x6c), QColor(70, 72, 78)
REFERENCIA = QColor(140, 140, 146)        # cota de referencia (driven): gris medio, legible en los dos temas
AZUL_CAJA = QColor(0, 120, 215)
FONDO_LIENZO = QColor(250, 250, 252)      # lienzo 2D (sin visor)
CAPA_PREVIA_ISO = "iso_previa"              # capa del visor con las curvas isoparamétricas que saldrían con un clic
COLOR_PREVIA_ISO = (1.0, 0.55, 0.1)
TOPE_DIAGNOSTICO_S = 3.0                 # B-111: el diagnóstico de qué choca (un resolver por vínculo) se abandona a los 3 s
CONFLICTO = QColor(225, 45, 45)           # BOC-7: restricciones, cotas y geometría en choque, en rojo como Fusion
# Ventana de selección: de izquierda a derecha (adentro) y de derecha a izquierda (lo que toca).
VENTANA_RELLENO, VENTANA_BORDE = QColor(237, 120, 0, 70), QColor(140, 150, 180)
VENTANA_CRUCE = QColor(193, 191, 0, 70)
AVISO_BORRADAS = "Las restricciones o las cotas se han eliminado durante la operación."
YA_PROYECTADA = "Ya estaba proyectada: no cambia nada."


def _cantidad(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def texto_proyeccion(r):
    """Qué hace una proyección, según lo que da `Boceto.simular_proyecciones` (lo dicen la tarjeta y la barra de estado)."""
    partes = []
    if r["curvas"] or r["puntos"]:
        nuevas = [_cantidad(len(r["curvas"]), "curva", "curvas")] if r["curvas"] else []
        nuevas += [_cantidad(len(r["puntos"]), "punto", "puntos")] if r["puntos"] else []
        partes.append("Agrega " + " y ".join(nuevas))
    if r["visibles"]:
        partes.append(f"Muestra {_cantidad(len(r['visibles']), 'curva oculta', 'curvas ocultas')} del contorno, sin duplicar")
    if r["vinculadas"]:
        partes.append(f"Vincula {_cantidad(len(r['vinculadas']), 'curva existente', 'curvas existentes')}")
    return ". ".join(partes) + "." if partes else "Actualiza lo que ya estaba proyectado."


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
    validar_lados_poligono(lados)
    if tipo == "circunscrito":       # el cursor marca el punto medio de una arista
        a0 -= math.pi / lados
    return r, vertices_poligono(centro, r, lados, a0, tipo == "circunscrito")


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


def _espaciado_cien(altura, o):
    return fuentes.espaciado_cien(o["fuente"], altura, o["negrita"], o["cursiva"])


def _espaciado_mm(porcentaje, altura, o):
    """Lo escrito en «Espaciado (%)», como Character Spacing de Fusion (`espaciado_cien`). El boceto guarda mm; `o`: las
    opciones del texto. Un % sin tocar deja los mm como estaban: el campo los redondea."""
    if str(porcentaje) == _espaciado_porcentaje(o["espaciado"], altura, o):
        return o["espaciado"]
    return _numero(str(porcentaje).replace("%", "") or "0") * _espaciado_cien(altura, o) / 100


def _espaciado_porcentaje(mm, altura, o):
    return formato.numero(100 * mm / max(_espaciado_cien(altura, o), 1e-9))


_CACHE_MUESTRAS = {}


def pasos_segun_zoom(prim, px_por_mm, base=64):
    """B-661: muestras por vuelta de un círculo, arco o elipse para que la cuerda se aparte a lo sumo 0,25 px de la curva
    con el zoom de ahora (Fusion lo redibuja según el zoom; con 64 fijos, de cerca se veía facetado). Potencia de 2
    entre `base` y 4096, así la caché de `_muestras` sirve para muchos zooms; el resto de las primitivas, `base`."""
    if prim[0] in ("circulo", "arco"):
        radio = prim[3]
    elif prim[0] in ("elipse", "arco_elipse"):
        radio = max(prim[3], prim[4])
    else:
        return base
    r_px = abs(radio) * px_por_mm
    if r_px <= 0.5:
        return base
    n = math.pi / math.acos(1 - 0.25 / r_px)
    return int(min(4096, max(base, 2 ** math.ceil(math.log2(n)))))


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


PEDIR_DISTANCIA = "Escribí la distancia: positiva (hacia el asa) o negativa (al otro lado)."
PISTA_DESFASE = "Arrastrá el asa o escribí el valor · Enter acepta · Esc cancela"


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
            if getattr(parent, "nombres_parametros", None):
                autocompletar(c, parent.nombres_parametros)
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
        self.reubicar()
        self.show()
        self.raise_()
        self.campos[0].setFocus()
        self.campos[0].selectAll()
        QTimer.singleShot(0, self, self._tomar_foco)

    def _tomar_foco(self):
        """B-664: el clic que ubica una cota deja el foco en el visor (en Windows el lienzo lo recupera después de
        abrir la caja): si pasó, la caja lo vuelve a tomar para que se pueda teclear sin otro clic. El cuadro de Texto
        escribe en el lienzo a propósito y no entra acá."""
        try:
            lz = self.parent()
            if (self.isVisible() and getattr(lz, "_previa_texto", None) is None
                    and lz.window().focusWidget() in (None, lz)):
                self.campos[0].setFocus()
                self.campos[0].selectAll()
        except RuntimeError:                      # la caja ya se cerró
            pass

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self, self._remedir)
        QTimer.singleShot(60, self, self._remedir)

    def _remedir(self):
        """El estilo de la app recién se aplica al mostrarse: la barra, medida antes, quedaba más angosta que su
        contenido y cortaba las etiquetas («Dista»). Se mide de nuevo y se vuelve a acomodar."""
        try:
            self.layout().invalidate()
            self.layout().activate()
            self.adjustSize()
            self.reubicar()
        except RuntimeError:                      # la barra ya se cerró
            pass

    def reubicar(self):
        """Deja la barra entera dentro de la zona útil del lienzo (sin lo que tapan la paleta y los paneles)."""
        padre = self.parentWidget()
        if padre is None:
            return
        zona = padre._zona_util() if hasattr(padre, "_zona_util") else padre.rect()
        self.move(max(zona.left() + 4, min(self.x(), zona.right() - self.width() - 4)),
                  max(zona.top() + 4, min(self.y(), zona.bottom() - self.height() - 4)))

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

    def marcar_error(self, i=0, malo=True):
        self.campos[i].setStyleSheet(f"background: {temas.color('campo_error')};" if malo else "")



def _registro_uso(tipo, datos):
    """Evento del boceto en el registro local; ninguna costo si está apagado (no interfiere con el dibujo)."""
    r = _ru.activo
    if r is not None:
        r.emitir(tipo, datos)


def _diff_uso(lienzo, antes):
    """Qué cambiaron en el boceto respecto de una foto previa: entidades, restricciones y cotas."""
    salientes = set(lienzo.b.curvas) - set(antes["curvas"])
    por_borrar = set(antes["curvas"]) - set(lienzo.b.curvas)
    for i in list(salientes)[:16]:
        _registro_uso("boceto_entidad", {"accion": "creada", "tipo": lienzo.b.curvas[i].tipo})
    for i in list(por_borrar)[:16]:
        _registro_uso("boceto_entidad", {"accion": "borrada", "tipo": antes["curvas"][i].tipo})
    nuevos_r = set(lienzo.b.restricciones) - set(antes["restricciones"])
    quitados_r = set(antes["restricciones"]) - set(lienzo.b.restricciones)
    for i in list(nuevos_r)[:16]:
        _registro_uso("boceto_restriccion", {"accion": "agregada", "tipo": lienzo.b.restricciones[i].tipo})
    for i in list(quitados_r)[:16]:
        _registro_uso("boceto_restriccion", {"accion": "borrada", "tipo": antes["restricciones"][i].tipo})
    nuevos_c = set(lienzo.b.cotas) - set(antes["cotas"])
    quitados_c = set(antes["cotas"]) - set(lienzo.b.cotas)
    for i in list(nuevos_c)[:16]:
        c = lienzo.b.cotas[i]
        _registro_uso("boceto_cota", {"accion": "agregada", "tipo": c.tipo, "valor": c.expresion})
    for i in list(quitados_c)[:16]:
        _registro_uso("boceto_cota", {"accion": "borrada", "tipo": antes["cotas"][i].tipo})


def _foto_uso(lienzo):
    return {"curvas": dict(lienzo.b.curvas), "restricciones": dict(lienzo.b.restricciones),
            "cotas": dict(lienzo.b.cotas)} if _ru.activo is not None else None

def _suelta_aislada(b, cid):
    """Durante un aislamiento (navegador › Aislar) la geometría suelta tampoco se ve ni se captura."""
    from ..restricciones import objetos
    return objetos.aislamiento_activo(b) and cid not in objetos.indice(b)

__all__ = [
    "copy",
    "math",
    "re",
    "threading",
    "time",
    "warnings",
    "replace",
    "np",
    "QEvent",
    "QEventLoop",
    "QPoint",
    "QPointF",
    "QRectF",
    "Qt",
    "QTimer",
    "Signal",
    "QColor",
    "QFontMetricsF",
    "QKeySequence",
    "QMouseEvent",
    "QPainter",
    "QPen",
    "QPixmap",
    "QPolygonF",
    "QApplication",
    "QDialog",
    "QFrame",
    "QHBoxLayout",
    "QInputDialog",
    "QLabel",
    "QLineEdit",
    "QMenu",
    "QToolButton",
    "QToolTip",
    "QWidget",
    "fuentes",
    "Boceto",
    "ErrorBoceto",
    "TIPOS_COTA",
    "TIPOS_RESTRICCION",
    "auto_restringir",
    "grados_de_libertad",
    "resolver",
    "acomodar_segunda",
    "acomodar_tangente",
    "restricciones_en_conflicto",
    "restricciones_redundantes",
    "restriccion_quita_grados",
    "Indice",
    "TIPOS_INFERENCIA",
    "inferencias",
    "proyectar_bloqueo",
    "Arco",
    "Circulo",
    "Conica",
    "Cota",
    "Linea",
    "Spline",
    "Texto",
    "agregar_linea_medio",
    "agregar_rectangulo_3p",
    "aviso_radio_empalme",
    "aviso_tangencias_fuera",
    "agregar_arco_tangente",
    "agregar_circulo_puntos",
    "agregar_estrella",
    "agregar_poligono",
    "agregar_rectangulo_centro",
    "cambiar_radio",
    "centro_arco_tangente",
    "centro_poligono_arista",
    "circunferencia_3_puntos",
    "dominio",
    "evaluar_primitiva",
    "expresion_sin_signo",
    "fraccion_en_camino",
    "lado_natural",
    "mas_cercano",
    "paradas_cursor",
    "primitivas_entidad",
    "proporcion_estrella",
    "puntos_espiral",
    "puntos_primitiva",
    "redondear_estrella",
    "redondeos_estrella",
    "validar_lados_poligono",
    "validar_puntas_estrella",
    "validar_valor_cota",
    "vertices_estrella",
    "vertices_poligono",
    "_validar_opciones_texto",
    "ANGULO",
    "ESCALAR",
    "LONGITUD",
    "ErrorExpresion",
    "nombres_usados",
    "separar_nombre",
    "validar_nombre",
    "_ru",
    "formato",
    "temas",
    "autocompletar",
    "icono",
    "ControlPatron",
    "dibujar_casilla",
    "ControlTransformar",
    "HERRAMIENTAS",
    "RESTRICCIONES_HERRAMIENTA",
    "NOMBRES_RESTRICCION",
    "AYUDA_RESTRICCION",
    "DETALLE_RESTRICCION",
    "ICONO_RESTRICCION",
    "LADO_SIMBOLO",
    "RELACION_ENTRE_DOS",
    "NOMBRES_ENTIDAD",
    "PICKS",
    "SELECCION",
    "PATRON",
    "TRANSFORMAR",
    "SPLINES",
    "PROYECCION",
    "COMANDO_PROYECCION",
    "CAPA_PROYECCION",
    "CURVA_TEXTO",
    "MODIFICAN",
    "PORTAPAPELES",
    "VIOLETA",
    "TOL_PX",
    "TOL_PUNTO",
    "TOL_MANIJA",
    "RADIO_INTERIOR_PX",
    "TOL_INFERENCIA",
    "EJES_ORIGEN",
    "AJUSTES_INFERENCIA",
    "ajustes_inferencia",
    "RANURAS_RECTAS",
    "VIVAS",
    "ANGULARES",
    "COTA_OSCURO",
    "COTA_CLARO",
    "REFERENCIA",
    "AZUL_CAJA",
    "FONDO_LIENZO",
    "CAPA_PREVIA_ISO",
    "COLOR_PREVIA_ISO",
    "TOPE_DIAGNOSTICO_S",
    "CONFLICTO",
    "VENTANA_RELLENO",
    "VENTANA_BORDE",
    "VENTANA_CRUCE",
    "AVISO_BORRADAS",
    "YA_PROYECTADA",
    "_cantidad",
    "texto_proyeccion",
    "_tipo_valor",
    "_unitario",
    "_distancia_a_raya",
    "_rotar",
    "_tenido",
    "_es_numero",
    "texto_valor",
    "_vertices_poligono",
    "_segmento_en_rect",
    "CampoVivo",
    "_dist_px",
    "_barrido",
    "_numero",
    "_espaciado_cien",
    "_espaciado_mm",
    "_espaciado_porcentaje",
    "_CACHE_MUESTRAS",
    "_muestras",
    "_inicio_palabra",
    "_fin_palabra",
    "_palabra_en",
    "PEDIR_DISTANCIA",
    "PISTA_DESFASE",
    "EntradaValor",
    "_registro_uso",
    "_diff_uso",
    "_foto_uso",
    "_suelta_aislada",
]
