# -*- coding: utf-8 -*-
"""
Visor 3D interactivo (QOpenGLWidget + PyOpenGL, perfil de compatibilidad).

Navegación como la de Fusion 360 (ver docs/investigacion_boceto_fusion.md):
  - Esquemas de ratón (Preferencias › General): OmniCAD (izquierdo = órbita), Fusion
    (medio = encuadre) y Tinkercad (derecho = órbita). En todos, Mayús + medio orbita, la rueda
    hace zoom hacia el cursor (invertible) y doble clic del medio ajusta la vista.
  - Órbita libre (gira sobre los ejes de la pantalla y puede inclinar la vista) o restringida
    (plato giratorio sobre el eje Z del mundo, la vista nunca se inclina).
  - Modos de la barra de navegación con el botón izquierdo: órbita, encuadre, zoom, ventana de zoom
    y "Mirar a" (clic en una cara o un plano). Esc sale del modo.
  - Cámara perspectiva, ortográfica o perspectiva con caras ortográficas (ortográfica solo al mirar
    de frente a una cara o a un plano).
  - Elección de planos de origen, planos de construcción y caras planas con el ratón
    ("Crear boceto" y "Mirar a").
Dibujo: 6 estilos visuales, entornos (fondo + luz), efectos (cúpula, plano del suelo, sombra y
reflejo en el suelo, anti-aliasing), visibilidad del origen y de los planos de construcción,
rejilla del diseño o del boceto activo, sombreado azul de perfiles y "Corte" por el plano del boceto.
Eje Z hacia arriba (como la opción "Z hacia arriba" de Fusion; práctico para impresión 3D).
"""
import ctypes
import math
import time
import weakref

import numpy as np
from OpenGL import GL
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from ..nucleo.render_cpu import ACERO, COLOR_MALLA, COLOR_SUPERFICIE, es_malla  # noqa: F401 — se re-exportan
from . import temas


class BandaSeleccion(QWidget):
    """Rectángulo de la ventana de selección, con los colores de Fusion: de izquierda a derecha naranja con
    borde (elige lo que queda adentro); de derecha a izquierda amarillo (elige lo que toca)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cruce = False
        self.zoom = False
        self.hide()

    def paintEvent(self, _e):
        p = QPainter(self)
        if self.zoom:
            p.fillRect(self.rect(), QColor(120, 160, 230, 50))
            p.setPen(QPen(QColor(150, 185, 240), 1))
        elif self.cruce:
            p.fillRect(self.rect(), QColor(193, 191, 0, 70))
            p.setPen(Qt.NoPen)
        else:
            p.fillRect(self.rect(), QColor(237, 120, 0, 70))
            p.setPen(QPen(QColor(140, 150, 180), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))


PALETA = [(0.62, 0.68, 0.76), (0.80, 0.62, 0.45), (0.55, 0.75, 0.58), (0.75, 0.58, 0.78),
          (0.85, 0.80, 0.50), (0.55, 0.72, 0.82)]
VISTAS = {"frente": (-90.0, 0.0), "atras": (90.0, 0.0), "derecha": (0.0, 0.0), "izquierda": (180.0, 0.0),
          "arriba": (-90.0, 89.9), "abajo": (-90.0, -89.9), "iso": (-45.0, 35.264)}
VISTAS_CARAS = {"frente", "atras", "derecha", "izquierda", "arriba", "abajo"}
ESTILOS = {"sombreado": "Sombreado", "sombreado_ocultas": "Sombreado con aristas ocultas",
           "sombreado_aristas": "Sombreado con solo aristas visibles", "alambrico": "Estructura alámbrica",
           "alambrico_ocultas": "Representación alámbrica con aristas ocultas",
           "alambrico_visibles": "Estructura alámbrica solo con aristas visibles"}
def _entorno_tema():
    """El entorno «Tema»: el fondo de la vista 3D del tema ACTIVO (ui/temas.py)."""
    c = temas.activo()
    return ("Tema (por defecto)", temas.rgb_f(c["visor_arriba"]), temas.rgb_f(c["visor_abajo"]), 0.26)


# Entornos: Fusion usa imágenes HDR; acá cada uno es un degradado de fondo (la "cúpula") con su
# intensidad de luz. Los nombres son los del menú de Fusion; el aspecto es una aproximación.
ENTORNOS = {
    "tema": _entorno_tema(),
    "fotomaton": ("Fotomatón", (0.93, 0.93, 0.94), (0.70, 0.71, 0.73), 0.95),
    "rubicon": ("Rubicon River", (0.72, 0.81, 0.90), (0.42, 0.47, 0.40), 0.90),
    "cielo_oscuro": ("Cielo oscuro", (0.14, 0.17, 0.27), (0.03, 0.03, 0.06), 0.80),
    "infinito": ("Grupo de infinito", (0.97, 0.97, 0.98), (0.84, 0.86, 0.90), 0.95),
    "habitacion_gris": ("Habitación gris", (0.62, 0.62, 0.63), (0.40, 0.40, 0.41), 0.90),
    "azul_tranquilidad": ("Azul tranquilidad", (0.62, 0.75, 0.90), (0.26, 0.36, 0.56), 0.90),
}
temas.observar(lambda: ENTORNOS.__setitem__("tema", _entorno_tema()))      # al cambiar de tema, cambia el fondo
# Con el tema oscuro Fusion ilumina con el entorno: los cuerpos se ven gris medio, con poco contraste entre
# caras y brillos marcados en las curvas (medido en el video: arriba #666, costados #393939–#5f5f5f).
LUZ_AMBIENTE = {"tema": 0.11}            # el resto de los entornos: 0.30
LUZ_BRILLO = {"tema": (1.0, 20.0)}       # (intensidad especular de la luz, shininess); el resto: (0.35, 48)
COLOR_EJE = ((0.86, 0.26, 0.26), (0.32, 0.72, 0.32), (0.30, 0.45, 0.95))
NARANJA_PLANO = (0.95, 0.66, 0.30)
AZUL_PERFIL = (0.30, 0.55, 0.95)
AZUL_HOVER = (0.45, 0.70, 1.0)
AZUL_SELECCION = (0.15, 0.50, 1.0)
# Etiqueta del valor de una cota guía (Medir): va sobre la vista 3D, así que lleva fondo y texto propios (se lee
# igual con cualquier tema y cualquier fondo del visor).
QSS_ETIQUETA = ("QLabel#etiqueta_cota { background: rgba(40, 40, 44, 225); color: #ffffff; padding: 2px 6px;"
                " border: 1px solid #f29a1f; border-radius: 3px; }")
TOL_PX_ARISTA, TOL_PX_VERTICE = 9.0, 11.0     # zonas de agarre generosas (antes 7 y 9)
# Filtros de selección que entiende `elegir_entidad` (los diálogos de comando piden uno o varios).
FILTROS = ("cara", "cara_plana", "arista", "arista_lineal", "arista_circular", "vertice", "cuerpo", "perfil",
           "curva_boceto", "punto_boceto", "boceto", "plano", "eje", "punto")


def _normalizar(v):
    n = np.linalg.norm(v)
    return v / n if n else v


def perspectiva(fov, aspecto, cerca, lejos):
    f = 1.0 / math.tan(math.radians(fov) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspecto, f
    m[2, 2] = (lejos + cerca) / (cerca - lejos)
    m[2, 3] = 2 * lejos * cerca / (cerca - lejos)
    m[3, 2] = -1
    return m


def ortografica(medio_ancho, medio_alto, cerca, lejos):
    m = np.identity(4)
    m[0, 0], m[1, 1] = 1 / medio_ancho, 1 / medio_alto
    m[2, 2] = -2 / (lejos - cerca)
    m[2, 3] = -(lejos + cerca) / (lejos - cerca)
    return m


def rotacion(eje, angulo):
    """Matriz de rotación (Rodrigues) alrededor de un eje unitario, ángulo en radianes."""
    x, y, z = _normalizar(np.asarray(eje, float))
    c, s = math.cos(angulo), math.sin(angulo)
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.identity(3) + s * k + (1 - c) * (k @ k)


def paso_lindo(bruto):
    """Primer paso 1-2-5 × 10^k mayor o igual que `bruto`."""
    e = 10 ** math.floor(math.log10(max(bruto, 1e-9)))
    for m in (1, 2, 5, 10):
        if m * e >= bruto:
            return m * e
    return 10 * e


def rayo_triangulos(origen, direccion, tris):
    """Möller–Trumbore vectorizado: distancia t a cada triángulo (inf si no lo toca)."""
    v0, e1, e2 = tris[:, 0], tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    p = np.cross(direccion, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = 1.0 / np.where(ok, det, 1.0)
    tv = origen - v0
    u = np.einsum("ij,ij->i", tv, p) * inv
    q = np.cross(tv, e1)
    v = (q @ direccion) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    toca = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-9)
    return np.where(toca, t, np.inf)



def teselar_cuerpo(forma, deflexion, angular=0.3):
    """(vértices, normales) de triángulos sueltos para dibujar un cuerpo B-rep o de malla."""
    if es_malla(forma):
        v = np.asarray(forma.vertices, float)[np.asarray(forma.caras, int)]
        n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        largo = np.linalg.norm(n, axis=1, keepdims=True)
        n = n / np.where(largo == 0, 1.0, largo)
        return v.reshape(-1, 3).astype(np.float32), np.repeat(n, 3, axis=0).astype(np.float32)
    return geo.teselar(forma, deflexion, angular, rehacer=True)    # el detalle elegido manda, aunque haya otra malla


# Detalle «Automático»: la deflexión sigue al tamaño de cada pieza (diagonal de su caja × factor), entre estos topes.
FACTOR_DETALLE_AUTO, DEFLEXION_MIN, DEFLEXION_MAX = 3e-4, 0.01, 0.5
# Orden en que «Dinámico» apaga cosas al navegar (Fusion: «reduced or toggled off in priority order»).
DEGRADACION = (("reflejo",), ("suelo", "sombra_suelo"), ("aa",))


# Detalle a la distancia (paso 4 de rendimiento): una pieza que se ve chica se dibuja con una malla más gruesa.
# Por nivel: (factor de la deflexión, factor del ángulo, diámetro máximo en pantalla en px). El error de una malla es
# a lo sumo su deflexión: el nivel vale solo si esa deflexión en pantalla queda bajo ERROR_LOD_PX (no se nota).
NIVELES_LOD = ((4.0, 2.0, 96.0), (16.0, 4.0, 24.0))
ERROR_LOD_PX, ANGULO_LOD_MAX = 0.5, 1.0
PRESUPUESTO_LOD_S = 0.012          # tiempo por vuelta para calcular mallas gruesas sin trabar la interfaz


def nivel_lod(diametro_px, deflexion_px):
    """Nivel de detalle (0 = la malla de siempre) de piezas que en pantalla miden `diametro_px` y cuya malla fina
    tiene una deflexión de `deflexion_px`. Acepta números o arrays (una pieza por elemento)."""
    d, e = np.asarray(diametro_px, float), np.asarray(deflexion_px, float)
    nivel = np.zeros(d.shape, int)
    for k, (f_defl, _f_ang, max_px) in enumerate(NIVELES_LOD, 1):   # cada nivel pide más que el anterior
        nivel = np.where((d <= max_px) & (e * f_defl <= ERROR_LOD_PX), k, nivel)
    return nivel


def lineas_rejilla(plano, paso, centro_uv, rgb, oscuro, n=40):
    """(vértices, colores RGBA) float32 para GL_LINES de la rejilla: 2n+1 líneas por eje alrededor de `centro_uv`,
    más marcadas cada 5. Con numpy: punto por punto en Python costaba ~1,5 ms por cuadro."""
    cu, cv = centro_uv
    ext = paso * n
    i = np.arange(-n, n + 1)
    u, v = cu + i * paso, cv + i * paso
    uv = np.empty((len(i), 2, 2, 2))               # [i, línea de u fija / de v fija, extremo, (u, v)]
    uv[:, 0, :, 0] = u[:, None]
    uv[:, 0, 0, 1], uv[:, 0, 1, 1] = cv - ext, cv + ext
    uv[:, 1, 0, 0], uv[:, 1, 1, 0] = cu - ext, cu + ext
    uv[:, 1, :, 1] = v[:, None]
    uv = uv.reshape(-1, 2)
    vertices = plano.origen + np.outer(uv[:, 0], plano.u) + np.outer(uv[:, 1], plano.v)
    mayor = np.stack([np.round(u / paso).astype(int) % 5 == 0, np.round(v / paso).astype(int) % 5 == 0], axis=1)
    alfa = np.where(mayor, 0.40, 0.16) if oscuro else np.where(mayor, 0.45, 0.22)
    colores = np.empty((len(uv), 4))
    colores[:, :3] = rgb
    colores[:, 3] = np.repeat(alfa.reshape(-1), 2)
    return vertices.astype(np.float32), colores.astype(np.float32)


def deflexion_automatica(forma):
    """Deflexión (mm) para teselar `forma` con el detalle «Automático»: fina en piezas chicas, gruesa en grandes."""
    try:
        mn, mx = geo.caja_envolvente(forma)
        diag = float(np.linalg.norm(np.asarray(mx, float) - np.asarray(mn, float)))
    except Exception:  # noqa: BLE001 — una forma rara no debe impedir dibujar: se usa el medio
        return 0.05
    return min(max(diag * FACTOR_DETALLE_AUTO, DEFLEXION_MIN), DEFLEXION_MAX)


def aristas_cuerpo(forma):
    if es_malla(forma):
        caras = np.asarray(forma.caras, int)
        if len(caras) > 30000:
            return np.zeros((0, 3), np.float32)
        v = np.asarray(forma.vertices, float)
        pares = np.sort(np.concatenate([caras[:, [0, 1]], caras[:, [1, 2]], caras[:, [2, 0]]]), axis=1)
        pares = np.unique(pares, axis=0)
        return v[pares].reshape(-1, 3).astype(np.float32)
    return _segmentos(geo.polilineas_aristas(forma))


def _segmentos(polilineas):
    """Polilíneas → pares de vértices para GL_LINES."""
    pares = [np.repeat(p, 2, axis=0)[1:-1] for p in polilineas if len(p) >= 2]
    return np.concatenate(pares).astype(np.float32) if pares else np.zeros((0, 3), np.float32)


def _muestrear_basico(prim, pasos_circulo=72):
    """Puntos (u, v) de una línea, círculo o arco del boceto."""
    if prim[0] == "linea":
        return [prim[2], prim[3]]
    if prim[0] not in ("circulo", "arco"):
        return []
    (cu, cv), r = prim[2], prim[3]
    a0, a1 = (0.0, 2 * math.pi) if prim[0] == "circulo" else (prim[4], prim[5])
    while a1 <= a0:
        a1 += 2 * math.pi
    n = max(8, int(pasos_circulo * (a1 - a0) / (2 * math.pi)))
    return [(cu + r * math.cos(a), cv + r * math.sin(a)) for a in np.linspace(a0, a1, n + 1)]


def muestrear_primitiva(prim):
    """Puntos (u, v) de cualquier primitiva de `Boceto.geometria()` (las nuevas las muestrea el boceto)."""
    from ..restricciones import boceto as mod_boceto
    funcion = getattr(mod_boceto, "puntos_primitiva", None)
    return funcion(prim) if funcion is not None else _muestrear_basico(prim)


def polilineas_boceto(boceto_resuelto):
    """Curvas de un boceto resuelto en 3D (para dibujarlas sobre el modelo)."""
    pl, salida = boceto_resuelto.plano, []
    for prim in boceto_resuelto.boceto.geometria(incluir_construccion=False):
        uv = muestrear_primitiva(prim)
        if len(uv) >= 2:
            salida.append(np.array([pl.a_3d(u, v) for u, v in uv], np.float32))
    return salida


class ConfigVista:
    """Opciones de visualización compartidas por todas las ventanas gráficas (vistas múltiples)."""

    def __init__(self):
        self.estilo_visual = "sombreado_aristas"
        self.entorno = "tema"
        self.aspecto = "acero"
        self.efectos = {"cupula": True, "suelo": False, "sombra_suelo": False, "reflejo": False, "aa": True}
        self.desfase_suelo = False
        self.rejilla = True                 # rejilla de esbozo (la del diseño, sobre el suelo)
        self.rejilla_bloqueada = False      # el paso deja de adaptarse al zoom
        self.paso_bloqueado = None
        self.rejilla_fija = None            # None = adaptativa; (espaciado mayor, subdivisiones)
        self.visibilidad = {"planos_origen": True, "ejes_origen": True, "punto_origen": True,
                            "planos_usuario": True, "bocetos": True}
        self.origen = {}                    # "o", "x", "y", "z", "xy", "xz", "yz" → visible (navegador)
        self.planos_usuario = []            # [(id, nombre, geo.Plano)] visibles
        self.lienzos = []                   # [(id, datos)] imágenes de INSERTAR › Lienzo / Calcomanía visibles
        self.esquema_raton = "fusion"
        self.invertir_zoom = False
        self.tipo_orbita = "libre"
        self.camara = "perspectiva"         # perspectiva | ortografica | persp_orto_caras
        self.teselado = None                # deflexión en mm (más chica = más fina); None = automática por pieza
        self.angular = 0.3                  # ángulo del teselado en radianes (manda en las piezas redondas)
        # Preferencias › Gráficos, como Fusion: «Dinámico» baja efectos mientras se navega si un cuadro tarda más que
        # 1/fps_minimo; `limite_fps` (0 = sin límite) espacia los cuadros para ahorrar batería.
        self.dinamico = True
        self.fps_minimo = 30
        self.limite_fps = 0
        # Menos detalle a la distancia (NIVELES_LOD). Fusion lo hace por dentro, sin opción: acá tampoco se muestra;
        # el interruptor sirve para medir con y sin (bench).
        self.detalle_distancia = True

    def colores_fondo(self):
        _, arriba, abajo, _ = ENTORNOS.get(self.entorno, ENTORNOS["tema"])
        return (arriba, abajo) if self.efectos.get("cupula", True) else (arriba, arriba)

    def oscuro(self):
        arriba, abajo = self.colores_fondo()
        return sum(arriba) + sum(abajo) < 6 * 0.45


class Visor3D(QOpenGLWidget):
    camara_cambiada = Signal()
    modo_cambiado = Signal(object)
    plano_elegido = Signal(object)      # {"ref", "plano", "marco", "cara_ref"} al elegir un plano o una cara
    eleccion_cancelada = Signal()
    entidad_elegida = Signal(object)    # clic con un filtro de selección activo: dict de `elegir_entidad`
    clic_vacio = Signal()               # clic sin nada debajo (deselecciona)
    menu_contextual = Signal(object, object)   # (entidad o None, posición global)
    seleccion_region = Signal(object, bool)    # (polígono en píxeles, por cruce): selección en ventana / libre
    entidad_pintada = Signal(object)           # selección de pintura: lo que hay bajo el cursor al arrastrar
    seleccion_otra = Signal(object, object)    # pulsación larga: (entidades bajo el cursor, posición global)
    gesto_radial = Signal(int)                 # clic derecho + arrastre: sector 0..7 del menú radial (N, NE, …)
    entidad_sobre = Signal(object)             # con un filtro activo: lo que quedó bajo el cursor (o None) al cambiar

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setMinimumSize(160, 120)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.config = config or ConfigVista()
        self.objetivo = np.zeros(3)
        self.distancia = 250.0
        self.R = np.identity(3)            # filas: derecha, arriba, atrás (hacia el ojo)
        self._orto_cara = False
        self.forzar_orto = False           # vistas fijas de "Vistas múltiples" (superior, frontal, derecha)
        self.fov = 40.0
        self.modo = None   # None | orbita | encuadre | zoom | ventana | mirar | elegir_plano
        self._mallas = []                  # [dict(v, n, seg, indice, id, color, tipo)] de los cuerpos visibles
        self._formas = {}                  # id_cuerpo → forma visible (para elegir caras)
        self._pick = {}                    # id(forma) → (caras, triángulos, índice de cara)
        self._pick_aristas = {}            # id(forma) → (aristas, polilíneas, vértices, puntos)
        self._estado = None                # estado del modelo que se muestra (para elegir perfiles y bocetos)
        self._ocultos = frozenset()
        self._excluir_bocetos = ()
        self.filtro = None                 # conjunto de FILTROS activos o None (sin selección en la vista)
        self._hover_ent = None             # entidad bajo el cursor con el filtro activo
        self._capas = {}                   # nombre → [primitivas a dibujar encima: ("tris"|"lineas"|"puntos", …)]
        self._colores_vertice = {}         # id_cuerpo → colores por vértice (análisis: cebra, curvatura…)
        self.opacidad = {}                 # id_cuerpo → opacidad (navegador › Opacidad)
        self.mallas_analisis = {}          # id_cuerpo → (vértices, normales, colores) que reemplazan su sombreado
        self.funcion_colores = None        # (normales, dirección de vista) → colores: cebra / mapa de entorno
        self._cache_dinamico = {}
        self.cortes = []                   # [(normal, punto)]: planos de recorte del análisis de sección
        self.transformaciones = {}         # id_cuerpo → matriz 4x4 solo de dibujo (animar uniones)
        self._texturas = {}                # clave de imagen → id de textura OpenGL (lienzos)
        self._presion = None               # posición del botón izquierdo al presionar (para detectar clic)
        self._lazo = None                  # puntos de la selección de forma libre mientras se arrastra
        self._bocetos = np.zeros((0, 3), np.float32)
        self._resalte = np.zeros((0, 3), np.float32)
        self._perfiles = np.zeros((0, 3), np.float32)
        self._hover = None                 # ("plano", ref) | ("cara", triángulos)
        self._cache = {}                   # id(forma) → (forma, v, n, aristas, centro, radio, deflexión)
        self._buffers = {}                 # id(array) → (búfer en la placa de video, weakref al array): se sube 1 vez
        self._lod = {}                     # (id(forma), nivel) → (forma, v, n) o None: mallas gruesas para lejos
        self._lod_pendientes = {}          # (id(forma), nivel) → (forma, deflexión fina, nivel), a calcular
        self._lod_datos = (np.zeros((0, 3)), np.zeros(0), np.zeros(0))   # centros, radios y deflexiones de _mallas
        self._niveles = np.zeros(0, int)   # nivel de detalle de cada malla en el cuadro actual
        self._t_lod = QTimer(self, singleShot=True, interval=0)
        self._t_lod.timeout.connect(self._calcular_lod)
        self._rejilla_cache = (None, None)  # (clave, (vértices, colores)) de la última rejilla
        self._caja_cache = (None, None, None)   # (_mallas, _bocetos, caja) de `_caja_escena`
        self._ultimo, self._boton, self._accion = None, None, None
        self._banda, self._banda_inicio = None, None
        self._banda_pendiente = None       # clic izquierdo en vacío: si se arrastra, ventana de selección
        self._gesto_inicio = None          # clic derecho: si se arrastra y se suelta, gesto del menú radial
        self._t_largo = QTimer(self, singleShot=True, interval=550)   # mantener apretado: "Seleccionar otro"
        self._t_largo.timeout.connect(self._pulsacion_larga)
        self._largo_hecho = False
        self._banda_libre = False          # ventana empezada arrastrando, sin elegir antes la herramienta
        self.ventana_libre = True          # la ventana pone False mientras hay un comando abierto
        self._stencil = False
        self.plano_boceto = None
        self.opciones_boceto = {"rejilla": True, "corte": False}
        self.paso_boceto = None            # paso de la rejilla del boceto (lo fija el modo boceto)
        self.info_gl = ""
        self._navegando = False            # orbitando, desplazando o haciendo zoom (para «Dinámico»)
        self._degradado = 0                # cuántos escalones de DEGRADACION están apagados ahora
        self._ms_cuadro = 0.0              # lo que tardó el último paintGL (CPU)
        self._t_cuadro = 0.0               # cuándo empezó el último paintGL (para el límite de cuadros)
        self._t_fin_nav = QTimer(self, singleShot=True, interval=250)
        self._t_fin_nav.timeout.connect(self._fin_navegacion)
        self._t_limite = QTimer(self, singleShot=True)
        self._t_limite.timeout.connect(lambda: QOpenGLWidget.update(self))
        self._etiquetas = {}               # nombre → [(punto 3D, QLabel)]: valores de las cotas guía de Medir
        self.camara_cambiada.connect(self._ubicar_etiquetas)
        self._fijar_direccion(*VISTAS["iso"])

    # ------------------------------------------------------------ rendimiento (Preferencias › Gráficos)
    def update(self, *args):
        """Con «Límite de cuadros por segundo», junta los pedidos de redibujo para no pasar de ese ritmo."""
        limite = self.config.limite_fps
        if args or not limite:
            return QOpenGLWidget.update(self, *args)
        espera = self._t_cuadro + 1.0 / limite - time.perf_counter()
        if espera <= 0:
            QOpenGLWidget.update(self)
        elif not self._t_limite.isActive():
            self._t_limite.start(int(espera * 1000) + 1)

    def _navegar(self):
        self._navegando = True
        self._t_fin_nav.start()

    def _fin_navegacion(self):
        """Al soltar (250 ms sin moverse): vuelve todo el detalle."""
        self._navegando = False
        if self._degradado:
            self._degradado = 0
            self.update()

    def _ajustar_degradado(self):
        cfg = self.config
        if not (self._navegando and cfg.dinamico):
            self._degradado = 0
            return
        presupuesto = 1000.0 / max(cfg.fps_minimo, 1)
        if self._ms_cuadro > presupuesto and self._degradado < len(DEGRADACION) + 1:
            self._degradado += 1           # el último escalón (len + 1) además saca las aristas
        elif self._ms_cuadro < presupuesto * 0.5 and self._degradado:
            self._degradado -= 1

    def efectos_visibles(self):
        """Los efectos de la configuración menos los que «Dinámico» apagó mientras se navega."""
        efectos = dict(self.config.efectos)
        for grupo in DEGRADACION[:self._degradado]:
            for k in grupo:
                efectos[k] = False
        return efectos

    # ------------------------------------------------------------ datos de la escena
    def set_modelo(self, estado, ocultos=frozenset(), excluir_bocetos=(), apariencias=None):
        """Muestra un estado del modelo. `apariencias`: id de cuerpo → color que pisa el del cuerpo
        (Aspecto y Material físico del documento)."""
        nuevas, cache, formas, lod = [], {}, {}, []
        apariencias = apariencias or {}
        self._estado, self._ocultos, self._excluir_bocetos = estado, frozenset(ocultos), tuple(excluir_bocetos)
        for i, c in enumerate(estado.cuerpos.values()):
            clave = id(c.forma)
            if clave in self._cache:
                datos = self._cache[clave]
            else:
                defl = self._deflexion(c.forma)
                v, n = teselar_cuerpo(c.forma, defl, self.config.angular)
                mn, mx = (v.min(axis=0), v.max(axis=0)) if len(v) else (np.zeros(3), np.zeros(3))
                datos = (c.forma, v, n, aristas_cuerpo(c.forma), (mn + mx) / 2, float(np.linalg.norm(mx - mn)) / 2,
                         defl)
            cache[clave] = datos
            if c.id not in ocultos:
                tipo = getattr(c, "tipo", "solido")
                color = apariencias.get(c.id, getattr(c, "apariencia", None))
                if color is None:
                    color = COLOR_SUPERFICIE if tipo == "superficie" else COLOR_MALLA if tipo == "malla" else None
                nuevas.append({"v": datos[1], "n": datos[2], "seg": datos[3], "indice": i, "id": c.id,
                               "color": tuple(color) if color is not None else None, "tipo": tipo,
                               "forma": None if es_malla(c.forma) else c.forma})   # las mallas no tienen niveles
                lod.append(datos[4:7])
                formas[c.id] = c.forma
        self._pick = {k: v for k, v in self._pick.items() if k in cache}
        self._pick_aristas = {k: v for k, v in self._pick_aristas.items() if k in cache}
        self._lod = {k: v for k, v in self._lod.items() if k[0] in cache}
        self._lod_pendientes = {k: v for k, v in self._lod_pendientes.items() if k[0] in cache}
        self._lod_datos = (np.array([d[0] for d in lod], float).reshape(-1, 3), np.array([d[1] for d in lod], float),
                           np.array([d[2] for d in lod], float))
        self._cache, self._mallas, self._formas = cache, nuevas, formas
        self._hover_ent = None
        polis = []
        for br in estado.bocetos.values():
            if br.op_id not in ocultos and br.op_id not in excluir_bocetos:
                polis.extend(polilineas_boceto(br))
        self._bocetos = _segmentos(polis)
        self.update()

    def _deflexion(self, forma):
        """Deflexión del detalle elegido (Preferencias › Gráficos); con «Automático», según el tamaño de la pieza."""
        if self.config.teselado is not None or es_malla(forma):
            return self.config.teselado or 0.05
        return deflexion_automatica(forma)

    def invalidar_teselado(self):
        """Tras cambiar la calidad del teselado ("Valor predefinido de gráficos")."""
        self._cache, self._pick, self._lod, self._lod_pendientes = {}, {}, {}, {}

    # ------------------------------------------------------------ mallas en la placa de video y detalle a la distancia
    def _buffer_gl(self, arr):
        """Búfer de la placa de video con los datos de `arr`: se sube UNA vez y se reusa en cada cuadro mientras el
        array viva (antes se mandaba toda la malla en cada cuadro). Pide el contexto OpenGL activo."""
        clave = id(arr)
        entrada = self._buffers.get(clave)
        if entrada is not None and entrada[1]() is arr:
            return entrada[0]
        buf = entrada[0] if entrada is not None else int(GL.glGenBuffers(1))   # otro array con el mismo id: se pisa
        datos = np.ascontiguousarray(arr, np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buf)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, datos.nbytes, datos, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        self._buffers[clave] = (buf, weakref.ref(arr))
        return buf

    def _barrer_buffers(self):
        """Libera en la placa los búferes de arrays que ya no existen (otro modelo, otro detalle, cuerpo borrado)."""
        muertos = [k for k, (_b, ref) in self._buffers.items() if ref() is None]
        if muertos:
            GL.glDeleteBuffers(len(muertos), [self._buffers.pop(k)[0] for k in muertos])

    def _apuntar(self, v, n=None):
        """Vértices (y normales) para el próximo glDrawArrays, desde su búfer en la placa. Lo que no es un array de
        numpy (raro) va como antes, desde la memoria."""
        if not isinstance(v, np.ndarray):
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, np.asarray(v, np.float32))
            if n is not None:
                GL.glNormalPointer(GL.GL_FLOAT, 0, np.asarray(n, np.float32))
            return
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer_gl(v))
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, ctypes.c_void_p(0))
        if n is not None:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer_gl(n))
            GL.glNormalPointer(GL.GL_FLOAT, 0, ctypes.c_void_p(0))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def _elegir_niveles(self):
        """Nivel de detalle de cada malla en este cuadro, según lo grande que se ve (en perspectiva, según su
        distancia a la cámara)."""
        n = len(self._mallas)
        centros, radios, defl = self._lod_datos
        if not n or not self.config.detalle_distancia or len(radios) != n:
            self._niveles = np.zeros(n, int)
            return
        k = max(self.height(), 1) * self.devicePixelRatioF() / (2 * math.tan(math.radians(self.fov) / 2))
        with np.errstate(divide="ignore", invalid="ignore"):
            if self.ortografica:
                px_mm = np.full(n, k / self.distancia)
            else:
                prof = (self.ojo() - centros) @ self.R[2]          # distancia de cada pieza a lo largo de la vista
                px_mm = np.where(prof > radios, k / np.maximum(prof, 1e-9), np.inf)   # cámara adentro: detalle total
            self._niveles = nivel_lod(2 * radios * px_mm, defl * px_mm)

    def _malla_dibujo(self, i, m):
        """(v, n) con que se dibuja la malla `m` (la i-ésima) en este cuadro: la de su nivel de detalle si ya está
        calculada; si no, la fina, y ese nivel queda pendiente para después del cuadro."""
        nivel = int(self._niveles[i]) if i < len(self._niveles) else 0
        forma = m.get("forma")
        if not nivel or forma is None or m["id"] in self.transformaciones:
            return m["v"], m["n"]
        clave = (id(forma), nivel)
        if clave not in self._lod:
            if clave not in self._lod_pendientes:
                self._lod_pendientes[clave] = (forma, float(self._lod_datos[2][i]), nivel)
                if not self._t_lod.isActive():
                    self._t_lod.start()
            return m["v"], m["n"]
        datos = self._lod[clave]
        return (datos[1], datos[2]) if datos is not None else (m["v"], m["n"])

    def _calcular_lod(self):
        """Calcula mallas gruesas pendientes, con un tope de tiempo por vuelta para no trabar la interfaz."""
        fin = time.perf_counter() + PRESUPUESTO_LOD_S
        while self._lod_pendientes and time.perf_counter() < fin:
            clave, (forma, defl, nivel) = self._lod_pendientes.popitem()
            f_defl, f_ang, _ = NIVELES_LOD[nivel - 1]
            try:
                v, n = geo.teselar_aparte(forma, defl * f_defl, min(self.config.angular * f_ang, ANGULO_LOD_MAX))
            except Exception:  # noqa: BLE001 — si una pieza no se puede mallar más gruesa, sigue con la fina
                v = None
            fina = self._cache.get(clave[0])
            # Solo vale si ahorra triángulos (en una pieza de caras planas sale igual: no gasta memoria de la placa).
            self._lod[clave] = (forma, v, n) if v is not None and fina and 0 < len(v) < len(fina[1]) else None
        if self._lod_pendientes:
            self._t_lod.start()
        self.update()

    def triangulos_dibujados(self):
        """Triángulos de los cuerpos que se dibujan en el cuadro actual (con el detalle a la distancia)."""
        self._elegir_niveles()
        return sum(len(self._malla_dibujo(i, m)[0]) for i, m in enumerate(self._mallas)) // 3

    def set_resaltado(self, caras):
        caras = list(caras or [])
        self._resalte = (np.concatenate([geo.teselar(c)[0] for c in caras]) if caras
                         else np.zeros((0, 3), np.float32))
        self.update()

    def set_perfiles(self, caras):
        """Sombreado azul de los perfiles cerrados del boceto activo (como "Mostrar perfil" de Fusion)."""
        caras = list(caras or [])
        self._perfiles = (np.concatenate([geo.teselar(c)[0] for c in caras]) if caras
                          else np.zeros((0, 3), np.float32))
        self.update()

    def set_plano_boceto(self, plano, opciones=None):
        self.plano_boceto = plano
        if opciones is not None:
            self.opciones_boceto = dict(opciones)
        if plano is None:
            self._perfiles = np.zeros((0, 3), np.float32)
        self.update()

    def _color(self, indice):
        return ACERO if self.config.aspecto == "acero" else PALETA[indice % len(PALETA)]

    def _puntos_escena(self):
        partes = [m["v"] for m in self._mallas if len(m["v"])] + ([self._bocetos] if len(self._bocetos) else [])
        return np.concatenate(partes) if partes else None

    def _caja_escena(self):
        """(mínimo, máximo) de lo que se muestra (cuerpos y bocetos), o None. Se calcula una vez por modelo: los
        efectos del suelo la piden en cada cuadro y recorrer todos los vértices costaba ~6 ms con 55 000 triángulos."""
        mallas, bocetos, caja = self._caja_cache
        if mallas is not self._mallas or bocetos is not self._bocetos:   # las dos listas se reemplazan, no se tocan
            pts = self._puntos_escena()
            caja = None if pts is None else (pts.min(axis=0), pts.max(axis=0))
            self._caja_cache = (self._mallas, self._bocetos, caja)
        return caja

    # ------------------------------------------------------------ cámara
    def _fijar_direccion(self, azimut, elevacion):
        a, e = math.radians(azimut), math.radians(elevacion)
        atras = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        derecha = np.cross((0.0, 0.0, 1.0), atras)
        if np.linalg.norm(derecha) < 1e-9:
            derecha = self.R[0]
        derecha = _normalizar(derecha)
        self.R = np.array([derecha, np.cross(atras, derecha), atras])

    @property
    def azimut(self):
        b = self.R[2]
        return math.degrees(math.atan2(b[1], b[0]))

    @azimut.setter
    def azimut(self, valor):
        self._fijar_direccion(valor, self.elevacion)

    @property
    def elevacion(self):
        return math.degrees(math.asin(max(-1.0, min(1.0, self.R[2][2]))))

    @elevacion.setter
    def elevacion(self, valor):
        self._fijar_direccion(self.azimut, valor)

    @property
    def ortografica(self):
        c = self.config.camara
        return self.forzar_orto or c == "ortografica" or (c == "persp_orto_caras" and self._orto_cara)

    def set_ortografica(self, valor):
        self.config.camara = "ortografica" if valor else "perspectiva"
        self.update()

    def set_camara(self, modo):
        self.config.camara = modo
        self.update()

    def vista(self, nombre):
        self._fijar_direccion(*VISTAS[nombre])
        self._orto_cara = nombre in VISTAS_CARAS
        self.encuadrar()

    def mirar_a_plano(self, plano):
        """Cámara perpendicular al plano, con su eje u a la derecha y v hacia arriba ("Mirar a")."""
        self.R = np.array([plano.u, plano.v, plano.normal], float)
        self.objetivo = self.objetivo - plano.normal * float((self.objetivo - plano.origen) @ plano.normal)
        self._orto_cara = True
        self.update()

    def set_modo(self, modo):
        if modo != self.modo:
            self.modo = modo
            self._hover = None
            cursores = {"encuadre": Qt.OpenHandCursor, "orbita": Qt.SizeAllCursor, "zoom": Qt.SizeVerCursor,
                        "ventana": Qt.CrossCursor, "mirar": Qt.PointingHandCursor, "elegir_plano": Qt.PointingHandCursor,
                        "sel_ventana": Qt.CrossCursor, "sel_libre": Qt.CrossCursor, "sel_pintura": Qt.PointingHandCursor}
            self.setCursor(cursores.get(modo, Qt.ArrowCursor))
            self.modo_cambiado.emit(modo)
            self.update()

    def encuadrar(self):
        caja = self._caja_escena()
        if caja is None:
            self.objetivo, self.distancia = np.zeros(3), 250.0
        else:
            mn, mx = caja
            self.objetivo = (mn + mx) / 2
            radio = max(float(np.linalg.norm(mx - mn)) / 2, 1.0)
            self.distancia = radio / math.sin(math.radians(self.fov) / 2) * 1.1
        self.update()

    def orbitar(self, dx, dy):
        k = math.radians(0.4)
        self._orto_cara = False
        if self.config.tipo_orbita == "restringida":
            self._fijar_direccion(self.azimut - dx * 0.4, max(-89.9, min(89.9, self.elevacion + dy * 0.4)))
        else:
            # Órbita libre: girar el marco de la cámara sobre sus propios ejes (arriba y derecha).
            q = rotacion(self.R[1], -dx * k) @ rotacion(self.R[0], -dy * k)
            self.R = self.R @ q.T
            u, b = self.R[1], _normalizar(self.R[2])
            d = _normalizar(np.cross(u, b))
            self.R = np.array([d, np.cross(b, d), b])
        self.update()

    def px_por_mm(self):
        return max(self.height(), 1) / (2 * self.distancia * math.tan(math.radians(self.fov) / 2))

    def desplazar(self, dx, dy):
        escala = 1.0 / self.px_por_mm()
        self.objetivo = self.objetivo - self.R[0] * dx * escala + self.R[1] * dy * escala
        self.update()

    def acercar(self, pasos, pos=None):
        if self.config.invertir_zoom:
            pasos = -pasos
        factor = 0.88 ** pasos
        nueva = max(0.5, min(1e6, self.distancia * factor))
        if pos is not None:   # zoom hacia el cursor, como Fusion
            p = self.punto_focal(pos)
            if p is not None:
                self.objetivo = self.objetivo + (p - self.objetivo) * (1 - nueva / self.distancia)
        self.distancia = nueva
        self.update()

    def ojo(self):
        return self.objetivo + self.R[2] * self.distancia

    def matriz_vista(self):
        m = np.identity(4)
        m[:3, :3] = self.R
        m[:3, 3] = -self.R @ self.ojo()
        return m

    def _matrices(self):
        w, h = max(self.width(), 1), max(self.height(), 1)
        aspecto = w / h
        cerca, lejos = self.distancia * 0.01, self.distancia * 20 + 1000
        if self.ortografica:
            medio_alto = self.distancia * math.tan(math.radians(self.fov) / 2)
            proy = ortografica(medio_alto * aspecto, medio_alto, -lejos, lejos)
        else:
            proy = perspectiva(self.fov, aspecto, cerca, lejos)
        return proy, self.matriz_vista()

    def matriz_mvp(self):
        proy, vista = self._matrices()
        return proy @ vista

    # ------------------------------------------------------------ pantalla ↔ mundo
    def proyectar(self, p, mvp=None):
        """Punto 3D → posición en el widget (QPointF), o None si queda detrás de la cámara."""
        c = (mvp if mvp is not None else self.matriz_mvp()) @ np.array([p[0], p[1], p[2], 1.0])
        if c[3] <= 1e-9:
            return None
        return QPointF((c[0] / c[3] + 1) / 2 * self.width(), (1 - c[1] / c[3]) / 2 * self.height())

    def rayo(self, pos):
        inv = np.linalg.inv(self.matriz_mvp())
        x = 2 * pos.x() / max(self.width(), 1) - 1
        y = 1 - 2 * pos.y() / max(self.height(), 1)
        a, b = inv @ np.array([x, y, -1.0, 1.0]), inv @ np.array([x, y, 1.0, 1.0])
        a, b = a[:3] / a[3], b[:3] / b[3]
        return a, _normalizar(b - a)

    def interseccion_plano(self, pos, plano):
        o, d = self.rayo(pos)
        den = float(d @ plano.normal)
        if abs(den) < 1e-9:
            return None
        return o + d * float((plano.origen - o) @ plano.normal) / den

    def punto_focal(self, pos):
        """Punto bajo el cursor en el plano perpendicular a la vista que pasa por el objetivo."""
        return self.interseccion_plano(pos, geo.Plano.desde_marco(self.objetivo, self.R[2], self.R[0]))

    def paso_rejilla(self, minimo_px=14):
        cfg = self.config
        if cfg.rejilla_fija:
            mayor, sub = cfg.rejilla_fija
            return mayor / max(1, sub)
        if cfg.rejilla_bloqueada and cfg.paso_bloqueado:
            return cfg.paso_bloqueado
        return paso_lindo(minimo_px / self.px_por_mm())

    # ------------------------------------------------------------ elegir planos y caras
    def _tam_planos(self):
        return self.distancia * 0.22

    def eligiendo_planos(self):
        """True cuando se pide un plano (Crear boceto o un comando con campo de plano): ahí se muestran y se
        pueden elegir también los planos del origen ocultos. Sin comando, solo los visibles (como Fusion)."""
        return self.modo == "elegir_plano" or bool(self.filtro and "plano" in self.filtro and not self.ventana_libre)

    def plano_visible(self, ref):
        cfg, vis = self.config, self.config.visibilidad
        if ref in ("XY", "XZ", "YZ"):
            return bool(vis["planos_origen"] and cfg.origen.get(ref.lower()))
        return bool(vis["planos_usuario"])

    def planos_elegibles(self):
        """Planos que se pueden elegir: (ref, plano, rectángulo en uv)."""
        L = self._tam_planos()
        salida = [(n, geo.Plano(n), (0.0, 0.0, L, L)) for n in ("XY", "XZ", "YZ")]
        for ident, _nombre, pl in self.config.planos_usuario:
            cu, cv = pl.a_uv(self.objetivo)
            salida.append((ident, pl, (cu - L, cv - L, cu + L, cv + L)))
        return salida

    def _datos_pick(self, cid):
        forma = self._formas[cid]
        if id(forma) not in self._pick and es_malla(forma):
            # Las mallas se eligen enteras (cuerpo): no tienen caras B-rep para referenciar.
            tris = np.asarray(forma.vertices, float)[np.asarray(forma.caras, int)]
            self._pick[id(forma)] = ([], tris, np.zeros(len(tris), int))
        if id(forma) not in self._pick:
            caras = geo.teselar_por_cara(forma, self._deflexion(forma), self.config.angular)   # la misma malla que se ve
            if caras:
                tris = np.concatenate([t for _, t in caras])
                indice = np.concatenate([np.full(len(t), i) for i, (_, t) in enumerate(caras)])
            else:
                tris, indice = np.zeros((0, 3, 3)), np.zeros(0, int)
            self._pick[id(forma)] = ([c for c, _ in caras], tris, indice)
        return self._pick[id(forma)]

    def elegir(self, pos, planos=True, caras=True):
        """Lo que hay bajo el cursor: {"ref", "plano", "marco", "tris"} (plano None = cara no plana); en una cara
        plana además "cara_ref", su referencia persistente (el boceto sobre la cara la sigue con ella)."""
        o, d = self.rayo(pos)
        mejor_t, mejor = np.inf, None
        if planos:
            for ref, pl, (u0, v0, u1, v1) in self.planos_elegibles():
                den = float(d @ pl.normal)
                if abs(den) < 1e-9:
                    continue
                t = float((pl.origen - o) @ pl.normal) / den
                u, v = pl.a_uv(o + d * t)
                if u0 <= u <= u1 and v0 <= v <= v1 and t < mejor_t:
                    mejor_t, mejor = t, {"ref": ref, "plano": pl, "marco": None, "tris": None}
        if caras:
            for cid in self._formas:
                lista, tris, indice = self._datos_pick(cid)
                if not len(tris):
                    continue
                ts = rayo_triangulos(o, d, tris)
                i = int(np.argmin(ts))
                if ts[i] < mejor_t - 1e-6:
                    cara = lista[indice[i]]
                    pl = geo.plano_de_cara(cara)
                    mejor_t = ts[i]
                    mejor = {"ref": "cara" if pl is not None else None, "plano": pl,
                             "marco": pl.marco() if pl is not None else None,
                             "cara_ref": refs.referencia(cid, cara, caja=self._caja(cid)) if pl is not None else None,
                             "tris": tris[indice == indice[i]].reshape(-1, 3).astype(np.float32), "cuerpo": cid}
        return mejor

    # ------------------------------------------------------------ selección de entidades (diálogos de comando)
    def set_filtro(self, filtros):
        """Activa la selección en la vista con esos filtros (None la apaga). Con filtro, un clic emite
        `entidad_elegida` y lo que está bajo el cursor se resalta en celeste, como en Fusion."""
        self.filtro = set(filtros) if filtros else None
        self._hover_ent = None
        self.update()

    def set_capa(self, nombre, primitivas):
        """Capas de dibujo encima del modelo: [("tris", Nx3, color, alfa) | ("lineas", segmentos Nx3, color,
        ancho) | ("puntos", Nx3, color, tamaño)]. Lista vacía o None borra la capa."""
        if primitivas:
            self._capas[nombre] = list(primitivas)
        else:
            self._capas.pop(nombre, None)
        self.update()

    def set_etiquetas(self, nombre, etiquetas):
        """Textos anclados a puntos 3D encima del modelo (el valor de una cota guía de Medir): [(punto, texto)].
        Siguen al punto al mover la cámara; lista vacía o None las borra. Van en un QLabel hijo del visor, como las
        cajas de valor de los manipuladores, porque el dibujo OpenGL del visor no tiene texto."""
        for _p, etiqueta in self._etiquetas.pop(nombre, []):
            etiqueta.hide()
            etiqueta.setParent(None)              # deja de ser hija ya mismo (no espera al bucle de eventos)
            etiqueta.deleteLater()
        if etiquetas:
            from PySide6.QtWidgets import QLabel
            lista = []
            for punto, texto in etiquetas:
                etiqueta = QLabel(str(texto), self, objectName="etiqueta_cota")
                etiqueta.setAttribute(Qt.WA_TransparentForMouseEvents)
                etiqueta.setStyleSheet(QSS_ETIQUETA)
                etiqueta.adjustSize()
                lista.append((np.asarray(punto, float).reshape(3), etiqueta))
            self._etiquetas[nombre] = lista
        self._ubicar_etiquetas()

    def textos_etiquetas(self, nombre):
        """Textos de las etiquetas de una capa (para las pruebas y la API en vivo)."""
        return [etiqueta.text() for _p, etiqueta in self._etiquetas.get(nombre, [])]

    def _ubicar_etiquetas(self):
        """Cada etiqueta, centrada sobre su punto proyectado; se oculta si el punto queda detrás o fuera."""
        filas = [(p, e) for lista in self._etiquetas.values() for p, e in lista]
        if not filas:
            return
        s, ok = self.puntos_pantalla(np.array([p for p, _e in filas], float))
        w, h = self.width(), self.height()
        for (_p, e), (x, y), visible in zip(filas, np.asarray(s, float), np.asarray(ok, bool), strict=True):
            if not visible or not (-20 <= x <= w + 20 and -20 <= y <= h + 20):
                e.hide()
                continue
            e.move(int(min(max(2, x - e.width() / 2), max(2, w - e.width() - 2))),
                   int(min(max(2, y - e.height() - 8), max(2, h - e.height() - 2))))
            e.show()
            e.raise_()

    def set_colores_vertice(self, colores_por_cuerpo):
        """Colores por vértice para los análisis (cebra, curvatura, desmoldeo…). {} vuelve al aspecto normal."""
        self._colores_vertice = {k: np.asarray(v, np.float32) for k, v in (colores_por_cuerpo or {}).items()}
        self.update()

    def triangulos_cuerpo(self, cid):
        m = next((m for m in self._mallas if m["id"] == cid), None)
        return m["v"] if m else np.zeros((0, 3), np.float32)

    def _caja(self, cid):
        forma = self._formas[cid]
        clave = ("caja", id(forma))
        if clave not in self._pick:
            self._pick[clave] = None if es_malla(forma) else geo.caja_envolvente(forma)
        return self._pick[clave]

    def _datos_aristas(self, cid):
        forma = self._formas[cid]
        clave = id(forma)
        if clave not in self._pick_aristas:
            if es_malla(forma):
                self._pick_aristas[clave] = ([], [], [], np.zeros((0, 3)))
            else:
                aristas = refs.subformas(forma, "arista")
                polis = [geo.polilinea_arista(a) for a in aristas]
                vertices = refs.subformas(forma, "vertice")
                pts = np.array([refs.punto_de_vertice(v) for v in vertices]) if vertices else np.zeros((0, 3))
                self._pick_aristas[clave] = (aristas, polis, vertices, pts)
        return self._pick_aristas[clave]

    def _a_pantalla(self, puntos, mvp):
        p = np.asarray(puntos, float).reshape(-1, 3)
        h = np.c_[p, np.ones(len(p))] @ mvp.T
        w = h[:, 3]
        ok = w > 1e-9
        w = np.where(ok, w, 1.0)
        return np.c_[(h[:, 0] / w + 1) / 2 * self.width(), (1 - h[:, 1] / w) / 2 * self.height()], ok

    def _dist_polilinea(self, q, poli, mvp, rayo=None):
        """Distancia en píxeles del cursor a una polilínea 3D y el punto 3D más cercano."""
        if len(poli) < 2:
            return math.inf, None
        s, ok = self._a_pantalla(poli, mvp)
        if not ok.all():
            return math.inf, None
        a, b = s[:-1], s[1:]
        ab = b - a
        L2 = np.einsum("ij,ij->i", ab, ab)
        t = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.where(L2 > 0, L2, 1.0), 0.0, 1.0)
        cerca = a + ab * t[:, None]
        d = np.linalg.norm(cerca - q, axis=1)
        i = int(np.argmin(d))
        a3, b3 = np.asarray(poli[i], float), np.asarray(poli[i + 1], float)
        if rayo is None:
            return float(d[i]), a3 + (b3 - a3) * t[i]
        # Punto de la arista más cercano al rayo (en 3D: interpolar en pantalla falla con perspectiva).
        o, dr = rayo
        u = b3 - a3
        uu, ud = float(u @ u), float(u @ dr)
        w = a3 - o
        den = uu - ud * ud
        s = float(np.clip((ud * float(w @ dr) - float(w @ u)) / den, 0.0, 1.0)) if den > 1e-12 else 0.0
        return float(d[i]), a3 + u * s

    def _curvas_boceto(self, br):
        """[(id de curva, polilínea 3D)] de un boceto resuelto (cacheado por objeto)."""
        clave = ("curvas", id(br))
        if clave not in self._pick:
            salida = []
            for prim in br.boceto.geometria(incluir_construccion=True):
                uv = muestrear_primitiva(prim)
                if len(uv) >= 2:
                    salida.append((prim[1], np.array([br.plano.a_3d(u, v) for u, v in uv], float)))
            self._pick[clave] = salida
        return self._pick[clave]

    def _tris_perfil(self, cara):
        clave = ("perfil", id(cara))
        if clave not in self._pick:
            self._pick[clave] = geo.teselar(cara)[0].reshape(-1, 3, 3).astype(float)
        return self._pick[clave]

    def _bocetos_visibles(self):
        if self._estado is None or not self.config.visibilidad.get("bocetos", True):
            return []
        return [br for br in self._estado.bocetos.values() if br.op_id not in self._ocultos]

    def elegir_entidad(self, pos, filtros=None, a_traves=False):
        """Entidad bajo el cursor según los filtros (FILTROS). Devuelve un dict con "tipo", "ref"
        (referencia serializable de `timeline.entidades`), "dibujo" (primitivas para resaltar), "t"
        (profundidad), "punto" (punto 3D del clic) y, si corresponde, "cuerpo" y "forma" (subforma OCC).
        Prioridad como en Fusion: vértices y puntos, después aristas, ejes y curvas, después perfiles,
        caras y planos."""
        filtros = set(filtros if filtros is not None else (self.filtro or ()))
        if not filtros:
            return None
        o, d = self.rayo(pos)
        q = np.array([pos.x(), pos.y()], float)
        mvp = self.matriz_mvp()
        tol_t = max(self.distancia * 3e-3, 1e-3)

        # 1) cara más cercana (oculta lo que esté detrás)
        t_cara, cara_hit = math.inf, None
        for cid in self._formas:
            lista, tris, indice = self._datos_pick(cid)
            if not len(tris):
                continue
            ts = rayo_triangulos(o, d, tris)
            i = int(np.argmin(ts))
            if ts[i] < t_cara:
                t_cara = float(ts[i])
                cara_hit = (cid, lista[indice[i]] if lista else None, tris[indice == indice[i]].reshape(-1, 3))
        if a_traves:                        # "Seleccionar otro": también lo que está tapado por las caras
            t_cara = math.inf
        visible = lambda p: float((np.asarray(p) - o) @ d) <= t_cara + tol_t  # noqa: E731

        def _hit(tipo, ref, dibujo, t, punto, **extra):
            h = {"tipo": tipo, "ref": ref, "dibujo": dibujo, "t": t, "punto": punto}
            h.update(extra)
            return h

        # 2) vértices y puntos
        if filtros & {"vertice", "punto"}:
            mejor = (TOL_PX_VERTICE, None)
            for cid in self._formas:
                _, _, vertices, pts = self._datos_aristas(cid)
                if not len(pts):
                    continue
                s, ok = self._a_pantalla(pts, mvp)
                dist = np.where(ok, np.linalg.norm(s - q, axis=1), np.inf)
                i = int(np.argmin(dist))
                if dist[i] < mejor[0] and visible(pts[i]):
                    v = vertices[i]
                    mejor = (dist[i], _hit("vertice", refs.referencia(cid, v, caja=self._caja(cid)), [("puntos", pts[i:i + 1], None, 9)],
                                          float((pts[i] - o) @ d), pts[i], cuerpo=cid, forma=v))
            if "punto" in filtros:
                candidatos = [("O", np.zeros(3), {"tipo": "punto", "id": "O"})] if self.config.origen.get("o") else []
                candidatos += [(i, np.asarray(p), {"tipo": "punto", "id": i}) for i, _n, p in
                               getattr(self.config, "puntos_usuario", [])]
                for br in self._bocetos_visibles():
                    for pid, pt in br.boceto.puntos.items():
                        candidatos.append((pid, br.plano.a_3d(pt.x, pt.y),
                                           {"tipo": "punto_boceto", "boceto": br.op_id, "punto": pid}))
                for _i, p, ref in candidatos:
                    s, ok = self._a_pantalla(p, mvp)
                    dist = float(np.linalg.norm(s[0] - q)) if ok[0] else math.inf
                    if dist < mejor[0] and visible(p):
                        mejor = (dist, _hit(ref["tipo"], ref, [("puntos", np.array([p]), None, 9)],
                                            float((p - o) @ d), p))
            if mejor[1] is not None:
                return mejor[1]

        # 3) aristas, ejes y curvas de boceto
        filtros_arista = filtros & {"arista", "arista_lineal", "arista_circular", "eje"}
        if filtros_arista or "curva_boceto" in filtros:
            mejor = (TOL_PX_ARISTA, None)
            if filtros_arista:
                for cid in self._formas:
                    aristas, polis, _, _ = self._datos_aristas(cid)
                    for arista, poli in zip(aristas, polis, strict=True):
                        dist, p = self._dist_polilinea(q, poli, mvp, (o, d))
                        if dist >= mejor[0] or p is None or not visible(p):
                            continue
                        f = refs.firma_arista(arista)
                        if not ({"arista"} & filtros or ("arista_lineal" in filtros or "eje" in filtros)
                                and f["geom"] == "linea" or "arista_circular" in filtros and f["geom"] == "circulo"):
                            continue
                        mejor = (dist, _hit("arista", refs.referencia(cid, arista, caja=self._caja(cid)), [("lineas", _segmentos([poli]),
                                            None, 3.5)], float((p - o) @ d), p, cuerpo=cid, forma=arista))
            if "eje" in filtros:
                L = self._tam_planos() * 1.4
                ejes = [(k, np.zeros(3), np.identity(3)[i]) for i, k in enumerate("XYZ")
                        if self.config.origen.get(k.lower())]
                ejes += [(i, np.asarray(p, float), np.asarray(dd, float)) for i, _n, (p, dd) in
                         getattr(self.config, "ejes_usuario", [])]
                for ident, p0, dd in ejes:
                    poli = np.array([p0 - dd * (L if ident not in "XYZ" else 0), p0 + dd * L])
                    dist, p = self._dist_polilinea(q, poli, mvp, (o, d))
                    if dist < mejor[0] and p is not None:
                        mejor = (dist, _hit("eje", {"tipo": "eje", "id": ident}, [("lineas", poli, None, 3.5)],
                                            float((p - o) @ d), p))
            if "curva_boceto" in filtros or "eje" in filtros:
                for br in self._bocetos_visibles():
                    for curva_id, poli in self._curvas_boceto(br):
                        if "curva_boceto" not in filtros and br.boceto.tipo_de(curva_id) != "linea":
                            continue
                        dist, p = self._dist_polilinea(q, poli, mvp, (o, d))
                        if dist < mejor[0] and p is not None:
                            mejor = (dist, _hit("curva_boceto", {"tipo": "curva_boceto", "boceto": br.op_id,
                                                                 "curva": curva_id},
                                                [("lineas", _segmentos([poli]), None, 3.5)], float((p - o) @ d), p))
            if mejor[1] is not None:
                return mejor[1]

        # 4) perfiles de boceto (están sobre el plano del boceto; ganan a la cara que tengan detrás)
        if filtros & {"perfil", "boceto"}:
            mejor_t, mejor = math.inf, None
            for br in self._bocetos_visibles():
                for perfil in br.perfiles:
                    tris = self._tris_perfil(perfil.cara)
                    if not len(tris):
                        continue
                    ts = rayo_triangulos(o, d, tris)
                    t = float(ts.min())
                    if t < mejor_t and t <= t_cara + tol_t:
                        from ..timeline.operaciones import OpExtrusion
                        ref = ({"tipo": "perfil", "boceto": br.op_id, **OpExtrusion.referencia_perfil(perfil)}
                               if "perfil" in filtros else {"tipo": "boceto", "boceto": br.op_id})
                        mejor_t, mejor = t, _hit(ref["tipo"], ref, [("tris", tris.reshape(-1, 3), None, 0.45)], t,
                                                 o + d * t)
            if mejor is not None:
                return mejor

        # 5) caras, cuerpos y planos
        planos = []
        if "plano" in filtros:
            todos = self.eligiendo_planos()
            for ref, pl, (u0, v0, u1, v1) in self.planos_elegibles():
                if not (todos or self.plano_visible(ref)):
                    continue                       # un plano oculto no se elige con un clic suelto
                den = float(d @ pl.normal)
                if abs(den) < 1e-9:
                    continue
                t = float((pl.origen - o) @ pl.normal) / den
                u, v = pl.a_uv(o + d * t)
                if u0 <= u <= u1 and v0 <= v <= v1 and 0 < t < t_cara - tol_t:
                    esquinas = [pl.a_3d(u0, v0), pl.a_3d(u1, v0), pl.a_3d(u1, v1), pl.a_3d(u0, v1)]
                    tris = np.array([esquinas[0], esquinas[1], esquinas[2], esquinas[0], esquinas[2], esquinas[3]])
                    planos.append((t, _hit("plano", {"tipo": "plano", "id": ref}, [("tris", tris, None, 0.40)], t,
                                           o + d * t, plano=pl)))
        if planos:
            return min(planos, key=lambda x: x[0])[1]
        if cara_hit is not None:
            cid, cara, tris = cara_hit
            if "cuerpo" in filtros and not (filtros & {"cara", "cara_plana"}):
                return _hit("cuerpo", {"tipo": "cuerpo", "cuerpo": cid},
                            [("tris", self.triangulos_cuerpo(cid), None, 0.35)], t_cara, o + d * t_cara, cuerpo=cid,
                            forma=self._formas[cid])
            if cara is None:
                return None
            plano = geo.plano_de_cara(cara)
            acepta = ("cara" in filtros or ("cara_plana" in filtros or "plano" in filtros) and plano is not None
                      or "eje" in filtros and "eje" in refs.firma_cara(cara))
            if acepta:
                return _hit("cara", refs.referencia(cid, cara, caja=self._caja(cid)), [("tris", tris, None, 0.45)], t_cara,
                            o + d * t_cara, cuerpo=cid, forma=cara, plano=plano)
            if "cuerpo" in filtros:
                return _hit("cuerpo", {"tipo": "cuerpo", "cuerpo": cid},
                            [("tris", self.triangulos_cuerpo(cid), None, 0.35)], t_cara, o + d * t_cara, cuerpo=cid,
                            forma=self._formas[cid])
        return None

    def _dibujar_primitivas(self, prims, color_defecto, alfa_defecto=None):
        for prim in prims:
            tipo, datos, color, extra = prim[0], prim[1], prim[2] or color_defecto, prim[3]
            datos = np.asarray(datos, np.float32)
            if not len(datos):
                continue
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, datos)
            if tipo == "tris":
                GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                GL.glPolygonOffset(-2.0, -2.0)
                GL.glDepthMask(GL.GL_FALSE)
                GL.glColor4f(*color[:3], alfa_defecto if alfa_defecto is not None else extra)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(datos))
                GL.glDepthMask(GL.GL_TRUE)
                GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
            elif tipo == "lineas":
                GL.glDisable(GL.GL_DEPTH_TEST)
                GL.glLineWidth(float(extra))
                GL.glColor4f(*color[:3], 1.0)
                GL.glDrawArrays(GL.GL_LINES, 0, len(datos) - len(datos) % 2)
                GL.glEnable(GL.GL_DEPTH_TEST)
            elif tipo == "puntos":
                GL.glDisable(GL.GL_DEPTH_TEST)
                GL.glPointSize(float(extra))
                GL.glColor4f(*color[:3], 1.0)
                GL.glDrawArrays(GL.GL_POINTS, 0, len(datos))
                GL.glEnable(GL.GL_DEPTH_TEST)

    @staticmethod
    def esquinas_lienzo(datos):
        """Las 4 esquinas 3D de un lienzo (en orden: abajo-izq, abajo-der, arriba-der, arriba-izq)."""
        pl, w, h = datos["plano"], datos["ancho"], datos["alto"]
        a = math.radians(datos.get("angulo", 0.0))
        c, s = math.cos(a), math.sin(a)
        salida = []
        for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            u, v = c * x - s * y + datos.get("dx", 0.0), s * x + c * y + datos.get("dy", 0.0)
            p = pl.a_3d(u, v)
            if datos.get("calcomania"):
                p = p + pl.normal * 0.02           # apenas por encima de la cara: no parpadea con ella
            salida.append(p)
        return salida

    def _textura(self, imagen_b64):
        clave = (len(imagen_b64), hash(imagen_b64))
        if clave not in self._texturas:
            import base64

            from PySide6.QtGui import QImage
            img = QImage.fromData(base64.b64decode(imagen_b64))
            if img.isNull():
                self._texturas[clave] = None
                return None
            img = img.convertToFormat(QImage.Format_RGBA8888).mirrored(False, True)
            tex = int(GL.glGenTextures(1))
            GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            datos = bytes(img.constBits())[: img.width() * img.height() * 4]
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, img.width(), img.height(), 0, GL.GL_RGBA,
                            GL.GL_UNSIGNED_BYTE, datos)
            self._texturas[clave] = tex
        return self._texturas[clave]

    def _dibujar_lienzos(self):
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
        for _ident, datos in self.config.lienzos:
            tex = self._textura(datos["imagen"])
            if tex is None:
                continue
            GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            GL.glColor4f(1, 1, 1, 1.0 if datos.get("calcomania") else datos.get("opacidad", 0.5))
            if not datos.get("calcomania"):
                GL.glDepthMask(GL.GL_FALSE)
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            if datos.get("voltear"):
                uvs = [(1, 0), (0, 0), (0, 1), (1, 1)]
            GL.glBegin(GL.GL_QUADS)
            for (tu, tv), p in zip(uvs, self.esquinas_lienzo(datos), strict=True):
                GL.glTexCoord2f(tu, tv)
                GL.glVertex3f(*map(float, p))
            GL.glEnd()
            GL.glDepthMask(GL.GL_TRUE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glDisable(GL.GL_TEXTURE_2D)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

    def _construccion_usuario(self):
        """Ejes y puntos de construcción del usuario (naranja, como Fusion)."""
        cfg = self.config
        if not cfg.visibilidad.get("planos_usuario", True):
            return
        L = self._tam_planos() * 1.4
        ejes = getattr(cfg, "ejes_usuario", [])
        if ejes:
            GL.glLineWidth(2.0)
            GL.glColor4f(*NARANJA_PLANO, 0.95)
            GL.glBegin(GL.GL_LINES)
            for _i, _n, (p, dd) in ejes:
                p, dd = np.asarray(p, float), np.asarray(dd, float)
                GL.glVertex3f(*(p - dd * L))
                GL.glVertex3f(*(p + dd * L))
            GL.glEnd()
        pts = getattr(cfg, "puntos_usuario", [])
        if pts:
            GL.glPointSize(8.0)
            GL.glColor4f(*NARANJA_PLANO, 1.0)
            GL.glBegin(GL.GL_POINTS)
            for _i, _n, p in pts:
                GL.glVertex3f(*map(float, p))
            GL.glEnd()

    # ------------------------------------------------------------ OpenGL
    def initializeGL(self):
        # Contexto nuevo (también al cambiar de ventana): los búferes y texturas del anterior ya no existen.
        self._buffers, self._texturas = {}, {}
        self.info_gl = f"OpenGL {GL.glGetString(GL.GL_VERSION).decode()} — {GL.glGetString(GL.GL_RENDERER).decode()}"
        self._stencil = int(GL.glGetIntegerv(GL.GL_STENCIL_BITS)) > 0
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_NORMALIZE)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.35, 0.35, 0.35, 1))
        GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, 48.0)
        # Mezcla separada: el color se mezcla con transparencia pero el ALFA del framebuffer queda en 1.
        # Con glBlendFunc simple, la grilla semitransparente dejaba alfa < 1 y Qt, al componer el
        # widget, mostraba puntos amarillos en los cruces (visto en evidencias/capturas).
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA, GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)

    def _fondo(self):
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        arriba, abajo = self.config.colores_fondo()
        GL.glBegin(GL.GL_QUADS)
        GL.glColor3f(*arriba)
        GL.glVertex2f(-1, 1)
        GL.glVertex2f(1, 1)
        GL.glColor3f(*abajo)
        GL.glVertex2f(1, -1)
        GL.glVertex2f(-1, -1)
        GL.glEnd()
        GL.glEnable(GL.GL_DEPTH_TEST)

    def _z_suelo(self):
        if self.config.desfase_suelo:
            caja = self._caja_escena()
            if caja is not None:
                return float(caja[0][2])
        return 0.0

    def _rejilla(self, plano, paso, color_ejes=True):
        """Rejilla sobre un plano, centrada en la zona que se está mirando (líneas mayores cada 5)."""
        oscuro = self.config.oscuro()
        if self.config.entorno == "tema":           # el color de la rejilla lo da el tema; los otros entornos, el suyo
            rojo, verde, azul = temas.rgb_f(temas.color("rejilla"))
        else:
            rojo, verde, azul = (0.62, 0.66, 0.74) if oscuro else (0.35, 0.38, 0.45)
        n = 40
        ext = paso * n
        cu, cv = plano.a_uv(self.objetivo)
        cu, cv = round(cu / (5 * paso)) * 5 * paso, round(cv / (5 * paso)) * 5 * paso
        clave = (tuple(plano.origen), tuple(plano.u), tuple(plano.v), paso, cu, cv, rojo, verde, azul, oscuro)
        if self._rejilla_cache[0] != clave:     # cambia al desplazar o al cambiar el paso, no en cada cuadro
            self._rejilla_cache = (clave, lineas_rejilla(plano, paso, (cu, cv), (rojo, verde, azul), oscuro, n))
        vertices, colores = self._rejilla_cache[1]
        GL.glLineWidth(1.0)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(4, GL.GL_FLOAT, 0, colores)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, vertices)
        GL.glDrawArrays(GL.GL_LINES, 0, len(vertices))
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        if color_ejes:   # ejes del plano (X rojo, Y verde, Z azul según hacia dónde apuntan)
            GL.glLineWidth(1.5)
            GL.glBegin(GL.GL_LINES)
            for eje, (a, b) in ((plano.u, ((cu - ext, 0), (cu + ext, 0))), (plano.v, ((0, cv - ext), (0, cv + ext)))):
                GL.glColor4f(*COLOR_EJE[int(np.argmax(np.abs(eje)))], 0.85)
                GL.glVertex3f(*plano.a_3d(*a))
                GL.glVertex3f(*plano.a_3d(*b))
            GL.glEnd()

    def _cuadro_plano(self, plano, rect, color, alfa, resaltado=False):
        u0, v0, u1, v1 = rect
        esquinas = [plano.a_3d(u0, v0), plano.a_3d(u1, v0), plano.a_3d(u1, v1), plano.a_3d(u0, v1)]
        GL.glDepthMask(GL.GL_FALSE)
        GL.glColor4f(*((0.45, 0.70, 1.0) if resaltado else color), 0.40 if resaltado else alfa)
        GL.glBegin(GL.GL_QUADS)
        for p in esquinas:
            GL.glVertex3f(*p)
        GL.glEnd()
        GL.glColor4f(*((0.45, 0.70, 1.0) if resaltado else color), 0.9)
        GL.glLineWidth(1.2)
        GL.glBegin(GL.GL_LINE_LOOP)
        for p in esquinas:
            GL.glVertex3f(*p)
        GL.glEnd()
        GL.glDepthMask(GL.GL_TRUE)

    def _origen_y_planos(self):
        cfg, vis, L = self.config, self.config.visibilidad, self._tam_planos()
        eligiendo = self.eligiendo_planos()
        hover = self._hover[1] if self._hover and self._hover[0] == "plano" else None
        for ref, pl, rect in self.planos_elegibles():
            if eligiendo or self.plano_visible(ref):
                self._cuadro_plano(pl, rect, NARANJA_PLANO, 0.22 if eligiendo else 0.12, ref == hover)
        if vis["ejes_origen"]:
            GL.glLineWidth(2.5)
            GL.glBegin(GL.GL_LINES)
            for i, clave in enumerate("xyz"):
                if cfg.origen.get(clave):
                    GL.glColor3f(*COLOR_EJE[i])
                    GL.glVertex3f(0, 0, 0)
                    GL.glVertex3f(*(np.identity(3)[i] * L * 1.4))
            GL.glEnd()
        if vis["punto_origen"] and (cfg.origen.get("o") or eligiendo):
            GL.glPointSize(7.0)
            GL.glColor3f(1, 1, 1)
            GL.glBegin(GL.GL_POINTS)
            GL.glVertex3f(0, 0, 0)
            GL.glEnd()

    def _dibujar_caras(self, alfa=1.0, transparentes=False):
        """Caras de los cuerpos: primero los opacos; los de opacidad < 1 en una segunda pasada."""
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        for i, m in enumerate(self._mallas):
            v, n = m["v"], m["n"]
            op = self.opacidad.get(m["id"], 1.0) * alfa
            if not len(v) or (op < 0.999 and alfa >= 0.999) != transparentes:
                continue
            colores = self._colores_vertice.get(m["id"])
            if m["id"] in self.mallas_analisis:
                v, n, colores = self.mallas_analisis[m["id"]]
            elif self.funcion_colores is not None:
                clave = (m["id"], id(v), self.R.tobytes())
                if clave not in self._cache_dinamico:
                    if len(self._cache_dinamico) > 64:
                        self._cache_dinamico.clear()
                    self._cache_dinamico[clave] = np.asarray(self.funcion_colores(n, self.R[2]), np.float32)
                colores = self._cache_dinamico[clave]
            elif colores is None:               # los colores por vértice (análisis) van con la malla fina
                v, n = self._malla_dibujo(i, m)
            if colores is not None and len(colores) == len(v):
                GL.glEnableClientState(GL.GL_COLOR_ARRAY)
                GL.glColorPointer(3, GL.GL_FLOAT, 0, colores)
            else:
                GL.glColor4f(*(m["color"] or self._color(m["indice"])), op)
            if transparentes:
                GL.glDepthMask(GL.GL_FALSE)
            t = self.transformaciones.get(m["id"])
            if t is not None:
                GL.glPushMatrix()
                GL.glMultMatrixf(np.asarray(t, float).T.astype(np.float32))
            self._apuntar(v, n)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(v))
            if t is not None:
                GL.glPopMatrix()
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

    def _dibujar_aristas(self):
        for m in self._mallas:
            seg = m["seg"]
            if len(seg) and self.opacidad.get(m["id"], 1.0) > 0.05:
                t = self.transformaciones.get(m["id"])
                if t is not None:
                    GL.glPushMatrix()
                    GL.glMultMatrixf(np.asarray(t, float).T.astype(np.float32))
                self._apuntar(seg)
                GL.glDrawArrays(GL.GL_LINES, 0, len(seg))
                if t is not None:
                    GL.glPopMatrix()

    def _cuerpos(self):
        estilo = self.config.estilo_visual
        con_color = estilo.startswith("sombreado")
        solo_profundidad = estilo in ("alambrico_ocultas", "alambrico_visibles")
        oscuro = self.config.oscuro()
        if con_color or solo_profundidad:
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(1.0, 1.0)
            GL.glEnable(GL.GL_LIGHTING)
            if solo_profundidad:
                GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)
            self._dibujar_caras()
            if not solo_profundidad:
                self._dibujar_caras(transparentes=True)
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
            GL.glDisable(GL.GL_LIGHTING)
            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
        claro = not con_color and oscuro
        if estilo != "sombreado" and not (estilo == "sombreado_aristas" and self._degradado > len(DEGRADACION)):
            GL.glLineWidth(1.4 if not con_color else 1.2)
            GL.glColor3f(*((0.88, 0.90, 0.94) if claro else (0.10, 0.11, 0.13)))
            if estilo == "alambrico":
                GL.glDisable(GL.GL_DEPTH_TEST)
            self._dibujar_aristas()
            GL.glEnable(GL.GL_DEPTH_TEST)
        if estilo in ("sombreado_ocultas", "alambrico_ocultas"):
            GL.glDepthFunc(GL.GL_GREATER)
            GL.glEnable(GL.GL_LINE_STIPPLE)
            GL.glLineStipple(2, 0x3333)
            GL.glLineWidth(1.0)
            GL.glColor4f(*((0.70, 0.73, 0.80) if claro else (0.30, 0.32, 0.36)), 0.75)
            self._dibujar_aristas()
            GL.glDisable(GL.GL_LINE_STIPPLE)
            GL.glDepthFunc(GL.GL_LESS)

    def _efectos_suelo(self, z):
        ef, oscuro = self.config.efectos, self.config.oscuro()
        caja = self._caja_escena()
        radio = 50.0 if caja is None else max(float(np.linalg.norm(caja[1] - caja[0])), 10.0)
        c = self.objetivo
        if ef.get("reflejo") and self._mallas:
            GL.glPushMatrix()
            GL.glTranslatef(0, 0, 2 * z)
            GL.glScalef(1, 1, -1)
            GL.glEnable(GL.GL_LIGHTING)
            self._dibujar_caras(alfa=0.28)
            GL.glDisable(GL.GL_LIGHTING)
            GL.glPopMatrix()
        if ef.get("suelo") or ef.get("reflejo"):
            ext = radio * 2.5
            GL.glDepthMask(GL.GL_FALSE)
            GL.glColor4f(*((0.20, 0.22, 0.26) if oscuro else (0.86, 0.87, 0.89)), 0.75 if ef.get("reflejo") else 0.9)
            GL.glBegin(GL.GL_QUADS)
            for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                GL.glVertex3f(c[0] + dx * ext, c[1] + dy * ext, z)
            GL.glEnd()
            GL.glDepthMask(GL.GL_TRUE)
        if ef.get("sombra_suelo") and self._mallas:
            luz = _normalizar(np.array([0.35, 0.45, 1.0]))
            m = np.identity(4)
            m[0, 2], m[1, 2], m[2, 2] = -luz[0] / luz[2], -luz[1] / luz[2], 0.0
            m[0, 3], m[1, 3], m[2, 3] = luz[0] / luz[2] * z, luz[1] / luz[2] * z, z + radio * 1e-3
            if self._stencil:   # cada píxel se oscurece una sola vez aunque se pisen triángulos
                GL.glClear(GL.GL_STENCIL_BUFFER_BIT)
                GL.glEnable(GL.GL_STENCIL_TEST)
                GL.glStencilFunc(GL.GL_EQUAL, 0, 0xFF)
                GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR)
            GL.glPushMatrix()
            GL.glMultMatrixf(m.T.astype(np.float32))
            GL.glDepthMask(GL.GL_FALSE)
            GL.glColor4f(0, 0, 0, 0.30)
            for i, m in enumerate(self._mallas):
                v = self._malla_dibujo(i, m)[0]
                if len(v):
                    self._apuntar(v)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(v))
            GL.glDepthMask(GL.GL_TRUE)
            GL.glPopMatrix()
            GL.glDisable(GL.GL_STENCIL_TEST)

    def _triangulos_planos(self, tris, color, alfa):
        if not len(tris):
            return
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(-2.0, -2.0)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glColor4f(*color, alfa)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, tris)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(tris))
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    def paintGL(self):
        inicio = self._t_cuadro = time.perf_counter()
        self._ajustar_degradado()
        cfg = self.config
        efectos_cfg, cfg.efectos = cfg.efectos, self.efectos_visibles()
        try:
            self._pintar_vista(cfg)
        finally:
            cfg.efectos = efectos_cfg
            self._ms_cuadro = (time.perf_counter() - inicio) * 1000

    def _pintar_vista(self, cfg):
        # No se llama `_pintar`: LienzoRender (render.py) tiene su propio `_pintar` con otra firma, y sin GLSL cae acá.
        self._barrer_buffers()
        self._elegir_niveles()
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)
        (GL.glEnable if cfg.efectos.get("aa", True) else GL.glDisable)(GL.GL_MULTISAMPLE)
        self._fondo()
        proy, vista = self._matrices()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixf(proy.T.astype(np.float32))
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        luz = ENTORNOS.get(cfg.entorno, ENTORNOS["tema"])[3]
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (luz, luz, luz, 1))
        amb = LUZ_AMBIENTE.get(cfg.entorno, 0.30)
        brillo, dureza = LUZ_BRILLO.get(cfg.entorno, (0.35, 48.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (amb, amb, amb * 1.04, 1))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (brillo, brillo, brillo, 1))
        GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, dureza)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (0.3, 0.6, 1.0, 0.0))   # luz fija respecto de la cámara
        GL.glLoadMatrixf(vista.T.astype(np.float32))
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisable(GL.GL_LIGHTING)

        z = self._z_suelo()
        if any(cfg.efectos.get(k) for k in ("suelo", "sombra_suelo", "reflejo")):
            self._efectos_suelo(z)
        if self.plano_boceto is not None:
            if self.opciones_boceto.get("rejilla", True):
                self._rejilla(self.plano_boceto, self.paso_boceto or self.paso_rejilla())
        elif cfg.rejilla:
            self._rejilla(geo.Plano("XY"), self.paso_rejilla())
        self._origen_y_planos()

        corte = self.plano_boceto is not None and self.opciones_boceto.get("corte")
        if corte:
            n, o = self.plano_boceto.normal, self.plano_boceto.origen
            GL.glClipPlane(GL.GL_CLIP_PLANE0, (-float(n[0]), -float(n[1]), -float(n[2]), float(n @ o)))
            GL.glEnable(GL.GL_CLIP_PLANE0)
        for i, (n, o) in enumerate(self.cortes[:4], 1):     # análisis de sección: se ve lo de detrás del plano
            n, o = np.asarray(n, float), np.asarray(o, float)
            GL.glClipPlane(GL.GL_CLIP_PLANE0 + i, (-float(n[0]), -float(n[1]), -float(n[2]), float(n @ o)))
            GL.glEnable(GL.GL_CLIP_PLANE0 + i)
        self._cuerpos()
        for i in range(5):
            GL.glDisable(GL.GL_CLIP_PLANE0 + i)
        if cfg.lienzos:
            self._dibujar_lienzos()

        if cfg.visibilidad.get("bocetos", True) and len(self._bocetos):
            GL.glLineWidth(2.0)
            GL.glColor3f(*((0.35, 0.62, 1.0) if cfg.oscuro() else (0.10, 0.35, 0.85)))
            self._apuntar(self._bocetos)
            GL.glDrawArrays(GL.GL_LINES, 0, len(self._bocetos))
        if self.plano_boceto is not None and self.opciones_boceto.get("perfil", True):
            self._triangulos_planos(self._perfiles, AZUL_PERFIL, 0.22)
        self._triangulos_planos(self._resalte, (1.0, 0.55, 0.1), 0.55)
        if self._hover and self._hover[0] == "cara":
            self._triangulos_planos(self._hover[1], (0.45, 0.70, 1.0), 0.45)
        self._construccion_usuario()
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        for nombre, prims in self._capas.items():
            self._dibujar_primitivas(prims, AZUL_SELECCION if nombre == "seleccion" else NARANJA_PLANO)
        if self._hover_ent is not None:
            self._dibujar_primitivas(self._hover_ent["dibujo"], AZUL_HOVER)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        self.camara_cambiada.emit()

    # ------------------------------------------------------------ ratón y teclado
    def accion_raton(self, boton, mods):
        """Qué hace un arrastre según el modo activo y el esquema de Preferencias."""
        mayus = bool(mods & Qt.ShiftModifier)
        if self.modo in ("orbita", "encuadre", "zoom") and boton == Qt.LeftButton:
            return self.modo
        if boton == Qt.MiddleButton and mayus:
            return "orbita"
        esquema = self.config.esquema_raton
        if esquema == "fusion":
            return "encuadre" if boton == Qt.MiddleButton else None
        if esquema == "tinkercad":
            if boton == Qt.RightButton:
                return "encuadre" if mayus else "orbita"
            return "encuadre" if boton == Qt.MiddleButton else None
        if boton == Qt.LeftButton:
            return "encuadre" if mayus else "orbita"
        return "encuadre" if boton in (Qt.MiddleButton, Qt.RightButton) else None

    def mousePressEvent(self, e):
        pos = e.position()
        self._presion = (pos, e.button())
        if e.button() == Qt.LeftButton and self.modo in ("elegir_plano", "mirar"):
            hit = self.elegir(pos)
            if hit is not None and hit["plano"] is not None:
                if self.modo == "mirar":
                    self.mirar_a_plano(hit["plano"])
                    self.set_modo(None)
                else:
                    self.plano_elegido.emit(hit)
            return
        if e.button() == Qt.LeftButton and self.modo == "sel_libre":
            self._lazo = [pos]
            return
        if e.button() == Qt.LeftButton and self.modo == "sel_pintura":
            self._lazo = []
            hit = self.elegir_entidad(pos)
            if hit is not None:
                self.entidad_pintada.emit(hit)
            return
        if e.button() == Qt.LeftButton and self.modo in ("ventana", "sel_ventana"):
            self._empezar_banda(pos.toPoint())
            return
        self._ultimo, self._boton = pos, e.button()
        self._accion = self.accion_raton(e.button(), e.modifiers())
        if e.button() == Qt.RightButton and self._accion is None:
            self._gesto_inicio = pos
        if e.button() == Qt.LeftButton and self._accion is None and self.modo is None and self.filtro:
            self._largo_hecho = False
            self._t_largo.start()
        if (e.button() == Qt.LeftButton and self._accion is None and self.modo is None and self.filtro
                and self.ventana_libre):
            self._banda_pendiente = pos.toPoint()     # en Fusion, arrastrar en la vista hace la ventana

    def _empezar_banda(self, inicio):
        self._banda_inicio = inicio
        if self._banda is None:
            self._banda = BandaSeleccion(self)
        self._banda.zoom = self.modo == "ventana"
        self._banda.cruce = False
        self._banda.setGeometry(QRect(inicio, QSize()))
        self._banda.show()
        self._banda.raise_()

    def mouseReleaseEvent(self, e):
        if self._banda_inicio is not None:
            inicio, fin = self._banda_inicio, e.position().toPoint()
            rect = QRect(inicio, fin).normalized()
            self._banda.hide()
            self._banda_inicio = None
            libre, self._banda_libre = self._banda_libre, False
            self._presion = None
            if self.modo == "sel_ventana" or libre:
                # De izquierda a derecha: lo que queda adentro; de derecha a izquierda: lo que toca (como Fusion).
                poli = [(rect.left(), rect.top()), (rect.right(), rect.top()), (rect.right(), rect.bottom()),
                        (rect.left(), rect.bottom())]
                if rect.width() > 3 and rect.height() > 3:
                    self.seleccion_region.emit(poli, fin.x() < inicio.x())
            else:
                self.zoom_ventana(rect)
            return
        if self._lazo is not None:
            puntos, self._lazo = self._lazo, None
            self._capas.pop("lazo", None)
            self.update()
            if self.modo == "sel_libre" and len(puntos) >= 3:
                self.seleccion_region.emit([(p.x(), p.y()) for p in puntos], False)
            return
        self._boton, self._accion = None, None
        self._banda_pendiente = None
        self._t_largo.stop()
        if self._largo_hecho and e.button() == Qt.LeftButton:
            self._largo_hecho, self._presion = False, None
            return
        gesto, self._gesto_inicio = self._gesto_inicio, None
        if e.button() == Qt.RightButton and gesto is not None:
            d = e.position() - gesto
            if math.hypot(d.x(), d.y()) > 40:          # gesto: clic derecho, arrastrar hacia el comando y soltar
                from .menu_radial import sector
                self._presion = None
                self.gesto_radial.emit(sector(d.x(), d.y()))
                return
        presion, self._presion = self._presion, None
        if presion is None or presion[1] != e.button():
            return
        movido = (e.position() - presion[0]).manhattanLength() > 4
        if movido or self.modo not in (None,):
            return
        if e.button() == Qt.LeftButton and self.filtro:
            hit = self.elegir_entidad(e.position())
            if hit is None:
                self.clic_vacio.emit()
            else:
                self.entidad_elegida.emit(hit)
        elif e.button() == Qt.RightButton:
            filtros = self.filtro or {"cara", "arista", "cuerpo", "perfil", "boceto"}
            self.menu_contextual.emit(self.elegir_entidad(e.position(), filtros), e.globalPosition().toPoint())

    def _pulsacion_larga(self):
        """Mantener apretado el botón izquierdo sin moverlo: lista de lo que hay bajo el cursor (incluido lo
        tapado), como el "Seleccionar otro" de Fusion."""
        if self._presion is None or self._presion[1] != Qt.LeftButton:
            return
        pos = self._presion[0]
        entidades = self.entidades_bajo_cursor(pos)
        if not entidades:
            return
        self._largo_hecho = True
        self._banda_pendiente = None
        self.seleccion_otra.emit(entidades, self.mapToGlobal(pos.toPoint()))

    def entidades_bajo_cursor(self, pos, filtros=None):
        """Todo lo elegible bajo el cursor, de adelante hacia atrás: vértices, aristas, curvas y perfiles de
        boceto, planos y ejes (aunque estén tapados), cada cara que atraviesa el rayo y los cuerpos."""
        filtros = set(filtros if filtros is not None else (self.filtro or ()))
        salida = []
        for f in ("vertice", "punto", "arista", "eje", "curva_boceto", "perfil", "plano"):
            if f in filtros:
                h = self.elegir_entidad(pos, {f}, a_traves=True)
                if h is not None and all(h["ref"] != x["ref"] for x in salida):
                    salida.append(h)
        if filtros & {"cara", "cuerpo"}:
            o, d = self.rayo(pos)
            for cid in self._formas:
                lista, tris, indice = self._datos_pick(cid)
                if not len(tris):
                    continue
                ts = rayo_triangulos(o, d, tris)
                vistas, t_min = set(), math.inf
                for i in np.argsort(ts):
                    t = float(ts[i])
                    if not math.isfinite(t):
                        break
                    t_min = min(t_min, t)
                    k = int(indice[i])
                    if k in vistas or "cara" not in filtros or not lista:
                        continue
                    vistas.add(k)
                    cara = lista[k]
                    salida.append({"tipo": "cara", "ref": refs.referencia(cid, cara, caja=self._caja(cid)),
                                   "dibujo": [("tris", tris[indice == k].reshape(-1, 3), None, 0.45)], "t": t,
                                   "punto": o + d * t, "cuerpo": cid, "forma": cara, "plano": geo.plano_de_cara(cara)})
                if "cuerpo" in filtros and math.isfinite(t_min):
                    salida.append({"tipo": "cuerpo", "ref": {"tipo": "cuerpo", "cuerpo": cid},
                                   "dibujo": [("tris", self.triangulos_cuerpo(cid), None, 0.35)], "t": t_min,
                                   "punto": o + d * t_min, "cuerpo": cid, "forma": self._formas[cid]})
        salida.sort(key=lambda h: h["t"])
        return salida[:14]

    def zoom_ventana(self, rect):
        """Ventana de zoom: el rectángulo dibujado pasa a llenar la vista."""
        if rect.width() < 6 or rect.height() < 6:
            return
        p = self.punto_focal(QPointF(rect.center()))
        if p is not None:
            self.objetivo = p
        self.distancia *= max(rect.width() / max(self.width(), 1), rect.height() / max(self.height(), 1))
        self.update()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self.encuadrar()

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._t_largo.isActive() and self._presion is not None and \
                (pos - self._presion[0]).manhattanLength() > 6:
            self._t_largo.stop()
        if self._banda_pendiente is not None and e.buttons() & Qt.LeftButton:
            if (pos.toPoint() - self._banda_pendiente).manhattanLength() > 6:
                self._empezar_banda(self._banda_pendiente)
                self._banda_pendiente, self._banda_libre = None, True
            else:
                return
        if self._banda_inicio is not None:
            self._banda.cruce = pos.x() < self._banda_inicio.x()
            self._banda.setGeometry(QRect(self._banda_inicio, pos.toPoint()).normalized())
            self._banda.update()
            return
        if self._lazo is not None and e.buttons() & Qt.LeftButton:
            if self.modo == "sel_pintura":
                hit = self.elegir_entidad(pos)
                if hit is not None:
                    self.entidad_pintada.emit(hit)
            else:
                self._lazo.append(pos)
                self._dibujar_lazo()
            return
        if self.modo in ("elegir_plano", "mirar") and not e.buttons():
            hit = self.elegir(pos)
            nuevo = None
            if hit is not None and hit["plano"] is not None:
                nuevo = ("cara", hit["tris"]) if hit["tris"] is not None else ("plano", hit["ref"])
            if (nuevo is None) != (self._hover is None) or (nuevo and self._hover and
                                                            (nuevo[0] != self._hover[0] or nuevo[1] is not self._hover[1])):
                self._hover = nuevo
                self.update()
            return
        if self.filtro and not e.buttons() and self.modo is None:
            hit = self.elegir_entidad(pos)
            anterior = self._hover_ent
            if (hit is None) != (anterior is None) or (hit and anterior and hit["ref"] != anterior["ref"]):
                self._hover_ent = hit
                self.entidad_sobre.emit(hit)       # Medir: valor en vivo de lo que está bajo el cursor
                self.update()
            return
        if self._ultimo is None or self._accion is None:
            return
        d = pos - self._ultimo
        self._ultimo = pos
        self._navegar()
        if self._accion == "orbita":
            self.orbitar(d.x(), d.y())
        elif self._accion == "zoom":
            self.acercar(-d.y() / 30.0)
        else:
            self.desplazar(d.x(), d.y())

    def wheelEvent(self, e):
        self._navegar()
        self.acercar(e.angleDelta().y() / 120.0, e.position())

    def _dibujar_lazo(self):
        """El lazo de la selección libre se dibuja en 3D sobre el plano focal (sigue al cursor)."""
        pts = [self.punto_focal(p) for p in self._lazo]
        pts = [p for p in pts if p is not None]
        if len(pts) >= 2:
            segs = np.repeat(np.array(pts + [pts[0]], np.float32), 2, axis=0)[1:-1]
            self._capas["lazo"] = [("lineas", segs, (0.15, 0.55, 1.0), 1.5)]
            self.update()

    def puntos_pantalla(self, puntos):
        """Proyección de puntos 3D a píxeles del widget (Nx2) y máscara de los que están delante."""
        return self._a_pantalla(np.asarray(puntos, float), self.matriz_mvp())

    def leaveEvent(self, e):
        if self._hover_ent is not None:
            self._hover_ent = None
            self.entidad_sobre.emit(None)
            self.update()
        super().leaveEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.modo:
            if self.modo == "elegir_plano":
                self.eleccion_cancelada.emit()
            self.set_modo(None)
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------ captura
    def captura_png(self, ancho=320):
        img = self.grabFramebuffer()
        if img.isNull():
            return None
        img = img.scaledToWidth(ancho, Qt.SmoothTransformation)
        datos = QByteArray()
        buf = QBuffer(datos)
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        return bytes(datos)
