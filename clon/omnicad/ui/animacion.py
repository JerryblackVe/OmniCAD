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

La primera parte del módulo (Guion, evaluar, explosión, interpolación, exportar cuadros) es lógica pura: no usa Qt.
"""
import copy
import json
import math
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
from ..nucleo.geometria import ErrorGeometria
from . import estilo
from .render import SEP, CintaEspacio, LienzoRender, _Oyente, icono_render
from .superposiciones import AreaVisor

TIPOS = {"transformar": "Transformar", "restaurar": "Restaurar posición", "explosion": "Explosión",
         "visibilidad": "Mostrar/Ocultar", "vista": "Vista", "anotacion": "Anotación"}
DURACION_DEFECTO = 1.0


# =============================================================== rotaciones e interpolación
def suavizado(f):
    """Entrada y salida suaves (smoothstep) de un avance 0..1."""
    f = min(1.0, max(0.0, float(f)))
    return f * f * (3 - 2 * f)


def matriz_rotacion(giro):
    """Matriz 3x3 de un vector de rotación (eje × ángulo, en grados) — Rodrigues."""
    rv = np.asarray(giro, float).reshape(3)
    ang = math.radians(float(np.linalg.norm(rv)))
    if ang < 1e-12:
        return np.identity(3)
    k = rv / np.linalg.norm(rv)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.identity(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def vector_rotacion(R):
    """Vector de rotación (grados) de una matriz 3x3 (logaritmo)."""
    R = np.asarray(R, float)
    c = min(1.0, max(-1.0, (np.trace(R) - 1) / 2))
    ang = math.acos(c)
    if ang < 1e-9:
        return np.zeros(3)
    if math.pi - ang < 1e-6:
        M = (R + np.identity(3)) / 2
        i = int(np.argmax(np.diag(M)))
        eje = M[:, i] / math.sqrt(max(M[i, i], 1e-15))
    else:
        eje = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(ang))
    return math.degrees(ang) * eje / np.linalg.norm(eje)


def euler_a_giro(ax, ay, az):
    """Ángulos X, Y, Z del diálogo (girar en X, después en Y, después en Z) → vector de rotación."""
    def rot(eje, a):
        v = np.zeros(3)
        v[eje] = a
        return matriz_rotacion(v)
    return vector_rotacion(rot(2, az) @ rot(1, ay) @ rot(0, ax))


def matriz_movimiento(pivote, traslacion, giro, f=1.0):
    """4x4 de girar `f`·giro alrededor de `pivote` y trasladar `f`·traslacion."""
    p = np.asarray(pivote, float)
    R = matriz_rotacion(np.asarray(giro, float) * f)
    m = np.identity(4)
    m[:3, :3] = R
    m[:3, 3] = p + np.asarray(traslacion, float) * f - R @ p
    return m


def _quat(R):
    R = np.asarray(R, float)
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def _matriz_quat(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(R0, R1, f):
    """Interpolación esférica entre dos matrices de rotación."""
    q0, q1 = _quat(R0), _quat(R1)
    d = float(q0 @ q1)
    if d < 0:
        q1, d = -q1, -d
    if d > 0.9995:
        q = q0 + (q1 - q0) * f
    else:
        th = math.acos(d)
        q = (math.sin((1 - f) * th) * q0 + math.sin(f * th) * q1) / math.sin(th)
    return _matriz_quat(q)


def interpolar_matriz(A, B, f, centro=(0.0, 0.0, 0.0)):
    """Entre dos posiciones rígidas (4x4): el centro del cuerpo va en línea recta y el giro por el camino corto."""
    A, B, c = np.asarray(A, float), np.asarray(B, float), np.asarray(centro, float)
    R = slerp(A[:3, :3], B[:3, :3], f)
    ca, cb = A[:3, :3] @ c + A[:3, 3], B[:3, :3] @ c + B[:3, 3]
    m = np.identity(4)
    m[:3, :3] = R
    m[:3, 3] = ca + (cb - ca) * f - R @ c
    return m


def interpolar_camara(c0, c1, f):
    """Cámara intermedia: giro esférico, objetivo lineal y distancia geométrica."""
    if c0 is None:
        return copy.deepcopy(c1)
    R = slerp(np.asarray(c0["R"], float).T, np.asarray(c1["R"], float).T, f).T
    o = np.asarray(c0["objetivo"], float) + (np.asarray(c1["objetivo"], float) - np.asarray(c0["objetivo"], float)) * f
    d = math.exp(math.log(max(c0["distancia"], 1e-9)) * (1 - f) + math.log(max(c1["distancia"], 1e-9)) * f)
    fov = float(c0.get("fov", 40.0)) + (float(c1.get("fov", 40.0)) - float(c0.get("fov", 40.0))) * f
    return {"R": R.tolist(), "objetivo": o.tolist(), "distancia": d, "fov": fov,
            "ortografica": bool(c1.get("ortografica", False))}


# =============================================================== modelo
def centros_de(estado):
    """Centro de la caja envolvente de cada cuerpo (posición del diseño): pivote de giros y explosiones."""
    from ..nucleo import geometria as geo
    from .visor3d import es_malla
    salida = {}
    for cid, c in estado.cuerpos.items():
        if es_malla(c.forma):
            v = np.asarray(c.forma.vertices, float)
            caja = (v.min(0), v.max(0)) if len(v) else None
        else:
            caja = geo.caja_envolvente(c.forma)
        salida[cid] = (np.asarray(caja[0], float) + np.asarray(caja[1], float)) / 2 if caja else np.zeros(3)
    return salida


def grupos_explosion(estado, ids, nivel="uno"):
    """Piezas que se mueven juntas: con «todos los niveles», cada cuerpo; con «un nivel», los cuerpos de un mismo
    componente de primer nivel van juntos y los de la raíz, cada uno por su lado."""
    ids = [c for c in (ids or list(estado.cuerpos)) if c in estado.cuerpos]
    if nivel == "todos":
        return [[c] for c in ids]
    comps = getattr(estado, "componentes", {}) or {}

    def raiz(comp):
        vistos = set()
        while comp and comps.get(comp, {}).get("padre") and comp not in vistos:
            vistos.add(comp)
            comp = comps[comp]["padre"]
        return comp
    grupos = {}
    for c in ids:
        comp = getattr(estado.cuerpos[c], "componente", "") or ""
        clave = ("cuerpo", c) if not comp else ("comp", raiz(comp))
        grupos.setdefault(clave, []).append(c)
    return list(grupos.values())


def calcular_explosion(centros, grupos, distancia):
    """Desplazamiento de cada pieza hacia afuera del centro del conjunto: la más alejada se mueve `distancia` y las
    demás en proporción. Las que están en el centro suben por +Z escalonadas. Devuelve (desplazamientos {id: xyz},
    orden [[ids], …] de la pieza más alejada a la más cercana, para la explosión secuencial)."""
    grupos = [list(g) for g in grupos if g]
    if not grupos:
        return {}, []
    cs = np.array([np.mean([centros[c] for c in g], axis=0) for g in grupos])
    C = cs.mean(axis=0)
    d = cs - C
    largo = np.linalg.norm(d, axis=1)
    escala = max(float(np.ptp(cs, axis=0).max()) if len(cs) > 1 else 0.0, 1e-9)
    centrales = [i for i in range(len(grupos)) if largo[i] < escala * 1e-6]
    maximo = max(float(largo.max()), 1e-12)
    despl = {}
    for i, g in enumerate(grupos):
        if i in centrales:
            k = centrales.index(i)
            off = np.array([0.0, 0.0, distancia * (k + 1) / len(centrales)])
        else:
            off = d[i] / maximo * distancia
        for c in g:
            despl[c] = [float(x) for x in off]
    orden = [grupos[i] for i in sorted(range(len(grupos)), key=lambda i: -largo[i])]
    return despl, orden


class Guion:
    """Guion gráfico (storyboard): acciones en una línea de tiempo y el estado inicial de los cuerpos."""

    def __init__(self, nombre="Guion gráfico1", acciones=None, inicial=None):
        self.nombre = nombre
        self.acciones = [dict(a) for a in (acciones or [])]
        self.inicial = {"matrices": {}, "opacidad": {}, "camara": None}
        self.inicial.update(copy.deepcopy(inicial or {}))
        self._contador = len(self.acciones)

    @property
    def duracion(self):
        return max([float(a["inicio"]) + max(0.0, float(a.get("duracion", 0.0))) for a in self.acciones] or [0.0])

    def nuevo_id(self):
        ids = {a.get("id") for a in self.acciones}
        while True:
            self._contador += 1
            if f"a{self._contador}" not in ids:
                return f"a{self._contador}"

    def agregar(self, accion):
        a = dict(accion)
        if a.get("tipo") not in TIPOS:
            raise ErrorGeometria(f"Tipo de acción desconocido: {a.get('tipo')}.")
        a["inicio"] = max(0.0, float(a.get("inicio", 0.0)))
        a["duracion"] = max(0.0, float(a.get("duracion", DURACION_DEFECTO)))
        if not a.get("id") or a["id"] in {b.get("id") for b in self.acciones}:
            a["id"] = self.nuevo_id()
        self.acciones.append(a)
        return a

    def accion(self, ident):
        for a in self.acciones:
            if a.get("id") == ident:
                return a
        raise ErrorGeometria(f"No existe la acción «{ident}».")

    def quitar(self, ident):
        self.acciones = [a for a in self.acciones if a.get("id") != ident]

    def a_dict(self):
        ini = self.inicial
        return {"nombre": self.nombre,
                "inicial": {"matrices": {k: [float(x) for x in np.asarray(m, float).reshape(16)]
                                         for k, m in ini.get("matrices", {}).items()},
                            "opacidad": {k: float(v) for k, v in ini.get("opacidad", {}).items()},
                            "camara": copy.deepcopy(ini.get("camara"))},
                "acciones": copy.deepcopy(self.acciones)}

    @classmethod
    def desde_dict(cls, datos):
        datos = datos or {}
        ini = datos.get("inicial") or {}
        inicial = {"matrices": {k: np.asarray(m, float).reshape(4, 4) for k, m in (ini.get("matrices") or {}).items()},
                   "opacidad": dict(ini.get("opacidad") or {}), "camara": ini.get("camara")}
        g = cls(datos.get("nombre", "Guion gráfico1"), None, inicial)
        for a in datos.get("acciones") or []:
            g.agregar(a)
        return g


def _avance(a, t):
    """Avance 0..1 de una acción en el instante t, o None si todavía no empezó."""
    ini, dur = float(a["inicio"]), float(a.get("duracion", 0.0))
    if t < ini - 1e-9:
        return None
    return 1.0 if dur <= 1e-9 else min(1.0, max(0.0, (t - ini) / dur))


def evaluar(guion, t, centros):
    """Estado de la escena en el instante t: {"matrices": {id: 4x4}, "opacidad": {id: 0..1}, "camara": dict | None,
    "notas": [{"texto", "punto", "id"}]}. `centros`: centro de cada cuerpo en la posición del diseño."""
    ids = list(centros)
    M = {c: np.asarray(guion.inicial.get("matrices", {}).get(c, np.identity(4)), float).reshape(4, 4) for c in ids}
    op = {c: float(guion.inicial.get("opacidad", {}).get(c, 1.0)) for c in ids}
    cam = copy.deepcopy(guion.inicial.get("camara"))
    notas = []
    total = guion.duracion
    orden = sorted(range(len(guion.acciones)), key=lambda i: (float(guion.acciones[i]["inicio"]), i))
    for i in orden:
        a = guion.acciones[i]
        f = _avance(a, t)
        if f is None:
            continue
        tipo = a["tipo"]
        cuerpos = [c for c in a.get("cuerpos", []) if c in M]
        if tipo == "transformar" and cuerpos:
            piv = np.mean([M[c][:3, :3] @ centros[c] + M[c][:3, 3] for c in cuerpos], axis=0)
            D = matriz_movimiento(piv, a.get("traslacion", (0, 0, 0)), a.get("giro", (0, 0, 0)), suavizado(f))
            for c in cuerpos:
                M[c] = D @ M[c]
        elif tipo == "restaurar":
            destinos = a.get("destinos") or {}
            for c in cuerpos:
                destino = np.asarray(destinos.get(c, np.identity(4)), float).reshape(4, 4)
                M[c] = interpolar_matriz(M[c], destino, suavizado(f), centros[c])
        elif tipo == "explosion":
            orden_piezas = a.get("orden") or [[c] for c in a.get("desplazamientos", {})]
            n = max(1, len(orden_piezas))
            for k, pieza in enumerate(orden_piezas):
                fk = min(1.0, max(0.0, f * n - k)) if a.get("secuencial") else f
                for c in pieza:
                    if c in M and c in a.get("desplazamientos", {}):
                        D = np.identity(4)
                        D[:3, 3] = np.asarray(a["desplazamientos"][c], float) * suavizado(fk)
                        M[c] = D @ M[c]
        elif tipo == "visibilidad":
            objetivo = 1.0 if a.get("visible", True) else 0.0
            for c in cuerpos:
                op[c] = op[c] + (objetivo - op[c]) * f
        elif tipo == "vista" and a.get("camara"):
            cam = interpolar_camara(cam, a["camara"], suavizado(f))
        elif tipo == "anotacion":
            fin = float(a["inicio"]) + (float(a.get("duracion", 0.0)) if a.get("duracion", 0.0) > 1e-9 else total)
            if t <= fin + 1e-9:
                p = np.asarray(a.get("punto", (0, 0, 0)), float)
                c = a.get("cuerpo") or ""
                if c in M:
                    p = M[c][:3, :3] @ p + M[c][:3, 3]
                notas.append({"texto": a.get("texto", ""), "punto": p, "id": a.get("id")})
    return {"matrices": M, "opacidad": op, "camara": cam, "notas": notas}


def estado_final(guion, centros):
    """Estado del final del guion como `inicial` de otro (Nuevo guion › Comenzar desde el final del anterior)."""
    fr = evaluar(guion, guion.duracion, centros)
    return {"matrices": fr["matrices"], "opacidad": fr["opacidad"], "camara": fr["camara"]}


def invertir(guion, centros):
    """Guion invertido (clic derecho › Invertir): empieza donde terminaba y hace las acciones al revés."""
    D = guion.duracion
    nuevo = Guion(guion.nombre, None, estado_final(guion, centros))
    for a in sorted(guion.acciones, key=lambda a: float(a["inicio"])):
        b = copy.deepcopy(a)
        dur = float(a.get("duracion", 0.0))
        b["inicio"] = max(0.0, D - (float(a["inicio"]) + dur))
        antes = evaluar(guion, float(a["inicio"]) - 1e-6, centros)
        tipo = a["tipo"]
        if tipo == "transformar":
            b["traslacion"] = [-float(x) for x in a.get("traslacion", (0, 0, 0))]
            b["giro"] = [-float(x) for x in a.get("giro", (0, 0, 0))]
        elif tipo == "explosion":
            b["desplazamientos"] = {c: [-float(x) for x in v] for c, v in a.get("desplazamientos", {}).items()}
            b["orden"] = list(reversed(a.get("orden", [])))
        elif tipo == "restaurar":
            b["destinos"] = {c: [float(x) for x in antes["matrices"][c].reshape(16)] for c in a.get("cuerpos", [])
                             if c in antes["matrices"]}
        elif tipo == "visibilidad":
            por_valor = {}
            for c in a.get("cuerpos", []):
                if c in antes["opacidad"]:
                    por_valor.setdefault(antes["opacidad"][c] > 0.5, []).append(c)
            for visible, cuerpos in por_valor.items():
                c2 = copy.deepcopy(b)
                c2.update(cuerpos=cuerpos, visible=bool(visible), id="")
                nuevo.agregar(c2)
            continue
        elif tipo == "vista":
            if antes["camara"] is None:
                continue
            b["camara"] = antes["camara"]
        elif tipo == "anotacion" and dur <= 1e-9:
            b["inicio"], b["duracion"] = 0.0, max(0.0, D - float(a["inicio"]))
        b["id"] = ""
        nuevo.agregar(b)
    return nuevo


# =============================================================== cuadros y exportación
def tiempos(duracion, fps):
    """Instantes de los cuadros de un video (incluye el primero y el último)."""
    n = max(1, int(math.floor(float(duracion) * fps + 1e-9)) + 1)
    return [min(float(duracion), i / float(fps)) for i in range(n)]


def proyectar_notas(notas, cam, ancho, alto):
    """[(x, y, texto)] en píxeles de una imagen ancho × alto con la cámara `cam`."""
    proy, vista = rc.matrices_camara(cam, ancho / max(alto, 1))
    salida = []
    for n in notas:
        h = proy @ vista @ np.r_[np.asarray(n["punto"], float), 1.0]
        if h[3] <= 1e-9:
            continue
        salida.append(((h[0] / h[3] + 1) / 2 * ancho, (1 - h[1] / h[3]) / 2 * alto, n["texto"]))
    return salida


def _fuente(tam):
    from PIL import ImageFont
    for nombre in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


def dibujar_notas(imagen, notas_px, escala=1.0):
    """Anotaciones (globo con texto, línea guía y alfiler) sobre una imagen RGBA/RGB uint8 (con Pillow)."""
    from PIL import Image, ImageDraw
    if not notas_px:
        return imagen
    img = Image.fromarray(np.asarray(imagen, np.uint8))
    d = ImageDraw.Draw(img)
    fuente = _fuente(max(10, int(14 * escala)))
    for x, y, texto in notas_px:
        bx, by = x + 40 * escala, y - 46 * escala
        caja = d.textbbox((0, 0), texto or " ", font=fuente)
        w, h = caja[2] - caja[0] + 16 * escala, caja[3] - caja[1] + 12 * escala
        d.line([(x, y), (bx, by + h / 2)], fill=(43, 120, 194, 255), width=max(1, int(2 * escala)))
        d.rectangle([bx, by, bx + w, by + h], fill=(255, 255, 255, 255), outline=(43, 120, 194, 255),
                    width=max(1, int(1.5 * escala)))
        d.text((bx + 8 * escala - caja[0], by + 6 * escala - caja[1]), texto, fill=(40, 40, 40, 255), font=fuente)
        r = 4 * escala
        d.ellipse([x - r, y - r, x + r, y + r], fill=(214, 69, 69, 255), outline=(255, 255, 255, 255))
    return np.asarray(img)


def cuadro_gif(imagen):
    """Cuadro RGB(A) → imagen de paleta para el GIF."""
    from PIL import Image
    rgb = Image.fromarray(np.asarray(imagen, np.uint8)[..., :3])
    return rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)


def guardar_gif(cuadros, ruta, fps):
    """GIF animado que se repite. `cuadros`: arrays RGB(A) o imágenes de `cuadro_gif`."""
    if not cuadros:
        raise ErrorGeometria("No hay cuadros para el video.")
    imgs = [c if hasattr(c, "save") else cuadro_gif(c) for c in cuadros]
    try:
        imgs[0].save(str(ruta), save_all=True, append_images=imgs[1:], duration=max(20, int(round(1000 / fps))),
                     loop=0, optimize=False)
    except OSError as e:
        raise ErrorGeometria(f"No se pudo guardar el GIF: {e}") from e


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
        p.fillRect(self.rect(), QColor("#ffffff"))
        filas = self.filas()
        for i, (clave, nombre) in enumerate(filas):
            y = self.REGLA + i * self.FILA
            p.fillRect(QRectF(0, y, w, self.FILA), QColor("#f7f9fb" if i % 2 else "#ffffff"))
            sel = clave in self.v.seleccion
            p.fillRect(QRectF(0, y, self.NOMBRES, self.FILA), QColor("#d6eaf8" if sel else "#f2f2f2"))
            p.setPen(QColor("#3c3c3c" if not clave.startswith("__") else "#5a5a5a"))
            f = p.font()
            f.setItalic(clave.startswith("__"))
            p.setFont(f)
            p.drawText(QRectF(8, y, self.NOMBRES - 12, self.FILA), Qt.AlignVCenter | Qt.AlignLeft,
                       p.fontMetrics().elidedText(nombre, Qt.ElideRight, self.NOMBRES - 14))
        f = p.font()
        f.setItalic(False)
        p.setFont(f)
        p.setPen(QColor("#d4d4d4"))
        p.drawLine(QPointF(self.NOMBRES, 0), QPointF(self.NOMBRES, h))
        # regla
        p.fillRect(QRectF(self.NOMBRES + 1, 0, w, self.REGLA), QColor("#f5f5f5"))
        paso = next(s for s in (0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60) if s * self.escala >= 40)
        t, fin = 0.0, self.t_de(w)
        while t <= fin + 1e-9:
            x = self.x_de(t)
            p.setPen(QColor("#9a9a9a"))
            p.drawLine(QPointF(x, self.REGLA - 7), QPointF(x, self.REGLA))
            p.setPen(QColor("#e8e8e8"))
            p.drawLine(QPointF(x, self.REGLA), QPointF(x, h))
            p.setPen(QColor("#5a5a5a"))
            p.drawText(QRectF(x - 30, 2, 60, 14), Qt.AlignCenter, f"{t:g} s")
            t += paso
        dur = self.v.guion.duracion
        p.fillRect(QRectF(self.x_de(dur), self.REGLA, 2, h), QColor("#c8c8c8"))
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
        titulo.setStyleSheet("font-size: 8pt; letter-spacing: 0.4px; color: #5a5a5a;")
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
            app.setStyleSheet(estilo.QSS)
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
        QTimer.singleShot(0, self._encuadrar_inicial)
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
        prims = [("tris", m["v"], None, 0.30) for m in self.lienzo._mallas if m["id"] in self.seleccion]
        self.lienzo.set_capa("seleccion", prims)

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
        d = DialogoAccion(self, tipo, valores, len(self.seleccion) if tipo != "explosion" else len(self.seleccion))
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
