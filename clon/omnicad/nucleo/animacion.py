# -*- coding: utf-8 -*-
"""
Espacio ANIMACIÓN, lógica pura (sin Qt): la parte de `ui/animacion.py` que no toca la interfaz.

Guiones gráficos (storyboards) con su línea de tiempo y las acciones de Fusion — Transformar componentes
(mover/girar), Restaurar posición inicial, Explosión automática de un nivel o de todos los niveles,
Mostrar/Ocultar, Vista (cámara) y Anotación —, evaluar el estado en un instante, invertir un guion y exportar
el video (GIF animado o secuencia PNG). La interfaz (ventana, línea de tiempo, diálogos) vive en `ui/animacion.py`
y usa este módulo; las herramientas para agentes, en `api/herramientas_animacion.py`.

Formato de los guiones (JSON, el mismo que guarda la ventana en `doc.espacios["animacion"]`):
    {"version": 1, "actual": índice del guion visible, "guiones": [guion, …]} con
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
"""
import copy
import math

import numpy as np

from . import geometria as geo
from . import render_cpu as rc

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
    from scipy.spatial.transform import Rotation   # diferido: cargar scipy cuesta ~0,8 s de arranque
    rv = np.asarray(giro, float).reshape(3)
    if float(np.linalg.norm(rv)) < 1e-12:
        return np.identity(3)
    return Rotation.from_rotvec(np.deg2rad(rv)).as_matrix()


def vector_rotacion(R):
    """Vector de rotación (grados) de una matriz 3x3 (logaritmo)."""
    from scipy.spatial.transform import Rotation   # diferido, como arriba
    return np.rad2deg(Rotation.from_matrix(np.asarray(R, float)).as_rotvec())


def euler_a_giro(ax, ay, az):
    """Ángulos X, Y, Z del diálogo (girar en X, después en Y, después en Z) → vector de rotación.
    'xyz' (minúsculas: ejes fijos, extrínseca) de scipy da la misma matriz que la composición Rz @ Ry @ Rx (medido en tests/test_animacion.py)."""
    from scipy.spatial.transform import Rotation   # diferido, como arriba
    return np.rad2deg(Rotation.from_euler('xyz', [ax, ay, az], degrees=True).as_rotvec())


def matriz_movimiento(pivote, traslacion, giro, f=1.0):
    """4x4 de girar `f`·giro alrededor de `pivote` y trasladar `f`·traslacion."""
    p = np.asarray(pivote, float)
    R = matriz_rotacion(np.asarray(giro, float) * f)
    m = np.identity(4)
    m[:3, :3] = R
    m[:3, 3] = p + np.asarray(traslacion, float) * f - R @ p
    return m


def slerp(R0, R1, f):
    """Interpolación esférica entre dos matrices de rotación."""
    from scipy.spatial.transform import Rotation, Slerp   # diferido: cargar scipy cuesta ~0,8 s de arranque
    par = Rotation.concatenate([Rotation.from_matrix(np.asarray(R0, float)),
                                Rotation.from_matrix(np.asarray(R1, float))])
    return Slerp([0.0, 1.0], par)([f]).as_matrix()[0]


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
    salida = {}
    for cid, c in estado.cuerpos.items():
        if rc.es_malla(c.forma):
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
            raise geo.ErrorGeometria(f"Tipo de acción desconocido: {a.get('tipo')}.")
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
        raise geo.ErrorGeometria(f"No existe la acción «{ident}».")

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
            fin = float(a["inicio"]) + (float(a.get("duracion", 0.0)) if float(a.get("duracion", 0.0)) > 1e-9 else total)
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
        raise geo.ErrorGeometria("No hay cuadros para el video.")
    imgs = [c if hasattr(c, "save") else cuadro_gif(c) for c in cuadros]
    try:
        imgs[0].save(str(ruta), save_all=True, append_images=imgs[1:], duration=max(20, int(round(1000 / fps))),
                     loop=0, optimize=False)
    except OSError as e:
        raise geo.ErrorGeometria(f"No se pudo guardar el GIF: {e}") from e
