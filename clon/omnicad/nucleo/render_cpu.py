# -*- coding: utf-8 -*-
"""
Render de software (Fusion › RENDERIZAR › Renderizar con el «Renderizador local»), sin Qt ni OpenGL.

Rasteriza los triángulos con un z-buffer vectorizado en numpy (los triángulos se procesan en tandas
del mismo tamaño en pantalla) y sombrea cada píxel con el MISMO modelo que el lienzo GLSL de
`ui/render.py`: entorno procedural (el degradado de los ENTORNOS del visor + tres «softboxes»), luz
principal con mapa de sombras (PCF 3×3), luces de relleno y de contorno, Fresnel de Schlick, brillo
Blinn-Phong según la rugosidad, reflejo del entorno, barniz, transparencia de una capa, oclusión
ambiental en espacio de pantalla, plano de suelo que recibe sombras y reflejos (planos, desenfocados
según la rugosidad), exposición, mapeo de tonos ACES y anti-alias por supermuestreo. La imagen se
calcula por mosaicos, así la memoria no crece con la resolución.
No es un trazador de rayos: las sombras salen de un mapa de sombras y los reflejos son del entorno y
del suelo (no hay reflejos entre cuerpos ni iluminación global).

Aspectos (Fusion › CONFIGURAR › Aspecto): `BIBLIOTECA_ASPECTOS` reproduce las familias de la
biblioteca de Fusion (Metal, Plástico, Vidrio, Goma, Madera, Pintura). Cada aspecto es un color sRGB
0..1 más un «acabado»: metálico, rugosidad, transparencia, barniz y patrón ("madera" = vetas 3D).
"""
import math

import numpy as np

from . import geometria as geo

# ---------------------------------------------------------------- aspectos
CATEGORIAS = ("Metal", "Plástico", "Vidrio", "Goma", "Madera", "Pintura")
ACABADO_DEFECTO = {"nombre": "", "categoria": "", "metalico": 0.0, "rugosidad": 0.4, "transparencia": 0.0,
                   "barniz": 0.0, "patron": "", "color2": None}


def _asp(categoria, nombre, color, metalico=0.0, rugosidad=0.4, transparencia=0.0, barniz=0.0, patron="",
         color2=None):
    return nombre, {"categoria": categoria, "color": tuple(color),
                    "acabado": {"nombre": nombre, "categoria": categoria, "metalico": metalico,
                                "rugosidad": rugosidad, "transparencia": transparencia, "barniz": barniz,
                                "patron": patron, "color2": list(color2) if color2 else None}}


BIBLIOTECA_ASPECTOS = dict([
    _asp("Metal", "Acero - Satinado", (0.74, 0.76, 0.79), 1.0, 0.32),
    _asp("Metal", "Acero - Pulido", (0.80, 0.81, 0.83), 1.0, 0.08),
    _asp("Metal", "Acero inoxidable - Cepillado", (0.70, 0.71, 0.72), 1.0, 0.45),
    _asp("Metal", "Aluminio - Pulido", (0.91, 0.92, 0.92), 1.0, 0.10),
    _asp("Metal", "Aluminio - Anodizado (negro)", (0.09, 0.09, 0.10), 0.85, 0.40),
    _asp("Metal", "Aluminio - Anodizado (rojo)", (0.62, 0.06, 0.07), 0.85, 0.35),
    _asp("Metal", "Aluminio - Anodizado (azul)", (0.10, 0.25, 0.62), 0.85, 0.35),
    _asp("Metal", "Cromo - Pulido", (0.95, 0.95, 0.96), 1.0, 0.03),
    _asp("Metal", "Latón - Pulido", (0.89, 0.73, 0.38), 1.0, 0.12),
    _asp("Metal", "Cobre - Satinado", (0.93, 0.62, 0.48), 1.0, 0.30),
    _asp("Metal", "Oro - Pulido", (1.00, 0.78, 0.34), 1.0, 0.07),
    _asp("Metal", "Titanio - Satinado", (0.62, 0.60, 0.58), 1.0, 0.35),
    _asp("Metal", "Hierro - Fundido", (0.36, 0.36, 0.37), 0.75, 0.70),
    _asp("Plástico", "Plástico - Brillante (Blanco)", (0.92, 0.92, 0.91), 0.0, 0.10),
    _asp("Plástico", "Plástico - Brillante (Negro)", (0.04, 0.04, 0.045), 0.0, 0.10),
    _asp("Plástico", "Plástico - Brillante (Rojo)", (0.80, 0.07, 0.06), 0.0, 0.10),
    _asp("Plástico", "Plástico - Brillante (Amarillo)", (0.97, 0.78, 0.08), 0.0, 0.10),
    _asp("Plástico", "Plástico - Brillante (Azul)", (0.07, 0.30, 0.78), 0.0, 0.10),
    _asp("Plástico", "Plástico - Brillante (Verde)", (0.10, 0.62, 0.25), 0.0, 0.10),
    _asp("Plástico", "Plástico - Mate (Blanco)", (0.88, 0.88, 0.86), 0.0, 0.60),
    _asp("Plástico", "Plástico - Mate (Gris)", (0.45, 0.46, 0.47), 0.0, 0.60),
    _asp("Plástico", "Plástico - Mate (Negro)", (0.05, 0.05, 0.055), 0.0, 0.62),
    _asp("Plástico", "Plástico - Mate (Naranja)", (0.95, 0.42, 0.07), 0.0, 0.60),
    _asp("Plástico", "Plástico - Translúcido mate (Azul)", (0.30, 0.55, 0.90), 0.0, 0.40, 0.55),
    _asp("Plástico", "Plástico - Transparente", (0.95, 0.96, 0.97), 0.0, 0.05, 0.85),
    _asp("Vidrio", "Vidrio - Transparente", (0.96, 0.99, 0.99), 0.0, 0.0, 0.93),
    _asp("Vidrio", "Vidrio - Ahumado", (0.33, 0.35, 0.36), 0.0, 0.0, 0.78),
    _asp("Vidrio", "Vidrio - Esmerilado", (0.92, 0.94, 0.95), 0.0, 0.45, 0.65),
    _asp("Vidrio", "Vidrio - Azul", (0.50, 0.72, 0.95), 0.0, 0.0, 0.85),
    _asp("Goma", "Goma - Negra", (0.05, 0.05, 0.05), 0.0, 0.85),
    _asp("Goma", "Goma - Gris", (0.32, 0.33, 0.34), 0.0, 0.85),
    _asp("Goma", "Goma - Roja", (0.55, 0.08, 0.06), 0.0, 0.80),
    _asp("Madera", "Madera - Pino", (0.86, 0.67, 0.42), 0.0, 0.55, patron="madera", color2=(0.62, 0.40, 0.20)),
    _asp("Madera", "Madera - Roble", (0.74, 0.55, 0.33), 0.0, 0.50, patron="madera", color2=(0.47, 0.31, 0.16)),
    _asp("Madera", "Madera - Nogal", (0.42, 0.27, 0.16), 0.0, 0.45, patron="madera", color2=(0.22, 0.13, 0.07)),
    _asp("Madera", "Madera - Arce barnizado", (0.90, 0.76, 0.55), 0.0, 0.35, 0.0, 0.8, "madera", (0.72, 0.55, 0.33)),
    _asp("Pintura", "Pintura - Brillante (Rojo)", (0.78, 0.05, 0.05), 0.0, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Brillante (Azul)", (0.05, 0.20, 0.62), 0.0, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Brillante (Blanco)", (0.93, 0.93, 0.92), 0.0, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Brillante (Negro)", (0.03, 0.03, 0.035), 0.0, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Metalizada (Plata)", (0.75, 0.76, 0.78), 0.6, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Metalizada (Azul)", (0.12, 0.28, 0.65), 0.6, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Metalizada (Rojo)", (0.65, 0.06, 0.08), 0.6, 0.30, barniz=1.0),
    _asp("Pintura", "Pintura - Mate (Negro)", (0.04, 0.04, 0.045), 0.0, 0.75),
])
ASPECTO_DEFECTO = "Acero - Satinado"        # el de los cuerpos sin aspecto, como en Fusion

# Acabado según el material físico (Modificar › Material físico) cuando el cuerpo no tiene aspecto.
_ACABADO_MATERIAL = {"Acero": (1.0, 0.35, 0.0), "Acero inoxidable": (1.0, 0.30, 0.0),
                     "Aluminio 6061": (1.0, 0.30, 0.0), "Latón": (1.0, 0.20, 0.0), "Cobre": (1.0, 0.28, 0.0),
                     "Titanio": (1.0, 0.35, 0.0), "Hierro fundido": (0.75, 0.70, 0.0),
                     "Vidrio": (0.0, 0.02, 0.90), "Policarbonato": (0.0, 0.10, 0.40)}


def aspecto(nombre):
    """(color [r, g, b], acabado dict) de un aspecto de la biblioteca."""
    if nombre not in BIBLIOTECA_ASPECTOS:
        raise geo.ErrorGeometria(f"No existe el aspecto «{nombre}» en la biblioteca.")
    a = BIBLIOTECA_ASPECTOS[nombre]
    return list(a["color"]), dict(a["acabado"])


def acabado_normalizado(acabado=None, material=None):
    """Acabado completo (con todas las claves y valores acotados). Sin acabado se usa el del material
    físico o, si tampoco hay, el de «Acero - Satinado»."""
    base = dict(ACABADO_DEFECTO)
    if acabado:
        base.update({k: v for k, v in acabado.items() if k in ACABADO_DEFECTO})
    elif material in _ACABADO_MATERIAL:
        m, r, t = _ACABADO_MATERIAL[material]
        base.update(metalico=m, rugosidad=r, transparencia=t, nombre=material)
    elif material == "Madera (pino)":
        base.update(BIBLIOTECA_ASPECTOS["Madera - Pino"]["acabado"])
    elif material:
        base.update(rugosidad=0.35, nombre=material)                # plásticos
    else:
        base.update(BIBLIOTECA_ASPECTOS[ASPECTO_DEFECTO]["acabado"])
    for k in ("metalico", "rugosidad", "transparencia", "barniz"):
        base[k] = float(min(1.0, max(0.0, float(base[k]))))
    return base


# ---------------------------------------------------------------- escena (Configuración de escena)
ESCENA_DEFECTO = {
    "entorno": "fotomaton",        # clave de visor3d.ENTORNOS
    "brillo": 1.0,                 # intensidad de las luces del entorno («Brillo»)
    "rotacion": 0.0,               # grados: giro de las luces alrededor de Z («Posición»)
    "fondo": "entorno",            # "entorno" | "color"
    "color_fondo": [1.0, 1.0, 1.0],
    "suelo": True,                 # «Plano de suelo»: recibe sombras
    "reflejos": True,              # reflejos de los cuerpos en el suelo
    "rugosidad_suelo": 0.2,
    "sombras": True,
    "oclusion": True,              # oclusión ambiental aproximada
    "camara": "perspectiva",       # "perspectiva" | "ortografica"
    "focal": 35.0,                 # mm (equivalente 35 mm)
    "exposicion": 0.0,             # EV
}
CIELO_DEFECTO = ((0.93, 0.93, 0.94), (0.70, 0.71, 0.73), 0.95)       # «Fotomatón»: arriba, abajo, luz


def escena_normalizada(datos=None):
    """Configuración de escena completa con los valores acotados (para guardar o renderizar)."""
    e = dict(ESCENA_DEFECTO)
    e.update({k: v for k, v in (datos or {}).items() if k in ESCENA_DEFECTO})
    e["brillo"] = float(min(4.0, max(0.0, float(e["brillo"]))))
    e["rotacion"] = float(e["rotacion"]) % 360.0
    e["rugosidad_suelo"] = float(min(1.0, max(0.0, float(e["rugosidad_suelo"]))))
    e["focal"] = float(min(300.0, max(8.0, float(e["focal"]))))
    e["exposicion"] = float(min(6.0, max(-6.0, float(e["exposicion"]))))
    e["color_fondo"] = [float(min(1.0, max(0.0, float(c)))) for c in list(e["color_fondo"])[:3]]
    if e["fondo"] not in ("entorno", "color"):
        e["fondo"] = "entorno"
    if e["camara"] not in ("perspectiva", "ortografica"):
        e["camara"] = "perspectiva"
    for k in ("suelo", "reflejos", "sombras", "oclusion"):
        e[k] = bool(e[k])
    return e


def focal_a_fov(focal):
    """Campo de visión vertical (grados) de una distancia focal en mm (sensor de 24 mm de alto)."""
    return math.degrees(2 * math.atan(12.0 / max(float(focal), 1e-3)))


def fov_a_focal(fov):
    return 12.0 / math.tan(math.radians(float(fov)) / 2)


# ---------------------------------------------------------------- color
def srgb_a_lineal(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lineal_a_srgb(c):
    c = np.clip(np.asarray(c, np.float64), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def mapa_tonos(c, exposicion=0.0):
    """Exposición (EV) + curva ACES (aproximación de Narkowicz) + sRGB. Entrada lineal, salida 0..1."""
    x = np.asarray(c, np.float64) * (2.0 ** exposicion) * 0.8
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return lineal_a_srgb(y)


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n < 1e-15, 1.0, n)


def _rot_z(grados):
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


# ---------------------------------------------------------------- luces y entorno
def luces(rotacion=0.0):
    """Direcciones (hacia la luz, unitarias) de la luz principal, de relleno y de contorno, giradas con la
    «Posición» del entorno. Las mismas usa el shader del lienzo."""
    r = _rot_z(rotacion)
    base = np.array([[-0.45, -0.75, 0.95], [0.85, -0.30, 0.35], [0.25, 0.90, 0.55]])
    return _unit(base @ r.T)


INTENSIDAD_LUCES = (2.1, 0.55, 0.65)        # principal (con sombra), relleno, contorno
# Tiras verticales del estudio (acimut en grados, intensidad): dan brillos alargados en cilindros y metales.
TIRAS = ((-75.0, 2.0), (-160.0, 1.2), (15.0, 1.5))
SOMBRA_BLANDO = 0.014                       # penumbra (fracción del radio de la escena)
OSCURIDAD_SOMBRA = 0.55                     # cuánto oscurece la sombra sobre el suelo


def radiancia_entorno(d, cielo, rotacion=0.0, brillo=1.0):
    """Luz que llega desde las direcciones `d` (Nx3 unitarias): degradado del entorno (arriba/abajo) más
    tres «softboxes» alineadas con las luces. Lineal (sin mapa de tonos)."""
    d = np.asarray(d, np.float64).reshape(-1, 3)
    arriba, abajo = srgb_a_lineal(cielo[0]), srgb_a_lineal(cielo[1])
    t = _smooth(-0.25, 0.85, d[:, 2])[:, None]
    c = (abajo * (1 - t) + arriba * t) * (1 - 0.55 * _smooth(0.05, -0.35, d[:, 2]))[:, None]  # piso del estudio
    caja = np.zeros(len(d))
    for L, k, (a, b) in zip(luces(rotacion), (5.0, 2.2, 2.6), ((0.93, 0.975), (0.95, 0.985), (0.955, 0.988)),
                            strict=True):
        caja += k * _smooth(a, b, d @ L)
    caja += 1.4 * _smooth(0.90, 0.97, d[:, 2])
    hxy = np.linalg.norm(d[:, :2], axis=1)
    h = d[:, :2] / np.maximum(hxy, 1e-9)[:, None]
    banda = _smooth(-0.75, -0.45, d[:, 2]) * (1 - _smooth(0.55, 0.8, d[:, 2])) * (hxy > 1e-6)
    for acimut, k in TIRAS:
        a = math.radians(acimut + rotacion)
        caja += k * _smooth(0.985, 0.997, h @ np.array([math.cos(a), math.sin(a)])) * banda
    return (c + caja[:, None] * 0.55 * float(cielo[2])) * brillo


def irradiancia(n, cielo, brillo=1.0):
    """Luz difusa del entorno sobre normales `n` (hemisférica: abajo → arriba)."""
    n = np.asarray(n, np.float64).reshape(-1, 3)
    arriba, abajo = srgb_a_lineal(cielo[0]), srgb_a_lineal(cielo[1])
    t = (0.5 + 0.5 * n[:, 2])[:, None]
    return (abajo * (1 - t) + arriba * t + 0.18 * float(cielo[2])) * brillo * 0.9


def color_fondo_entorno(d, cielo):
    """Color de fondo (sRGB, sin mapa de tonos) cuando el fondo es el entorno: el degradado de la cúpula."""
    d = np.asarray(d, np.float64).reshape(-1, 3)
    t = _smooth(-0.35, 0.65, d[:, 2])[:, None]
    return np.asarray(cielo[1], np.float64) * (1 - t) + np.asarray(cielo[0], np.float64) * t


def veta_madera(local, color, color2):
    """Vetas 3D de madera maciza (anillos alrededor del eje Y del cuerpo) en coordenadas propias."""
    q = np.asarray(local, np.float64).reshape(-1, 3)
    r = np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2)
    w = r * 0.42 + 1.3 * np.sin(q[:, 1] * 0.07 + q[:, 0] * 0.05) + 0.4 * np.sin(q[:, 1] * 0.29 + q[:, 2] * 0.11)
    anillo = (0.5 + 0.5 * np.sin(2 * math.pi * w)) ** 3
    fibra = 0.5 + 0.5 * np.sin(q[:, 1] * 2.1 + np.sin(q[:, 0] * 0.9) * 3.0)
    t = np.clip(anillo * 0.45 + fibra * 0.10, 0.0, 1.0)[:, None]
    return np.asarray(color, np.float64) * (1 - t) + np.asarray(color2, np.float64) * t


# ---------------------------------------------------------------- normales suaves
def normales_suaves(tris, grupos=None, angulo=45.0):
    """(vértices Nx3, normales Nx3) float32 de triángulos sueltos `tris` (Tx3x3) con normales promediadas
    (por área) en los vértices compartidos del mismo grupo (cara B-rep); si la normal promedio se aparta más
    de `angulo` grados de la del triángulo, queda la del triángulo (aristas vivas)."""
    tris = np.asarray(tris, np.float64).reshape(-1, 3, 3)
    if not len(tris):
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])        # largo = 2 × área
    unit = _unit(fn)
    grupos = np.zeros(len(tris), np.int64) if grupos is None else np.asarray(grupos, np.int64)
    escala = max(float(np.ptp(tris.reshape(-1, 3), axis=0).max()), 1e-9)
    claves = np.round(tris.reshape(-1, 3) / (escala * 1e-6)).astype(np.int64)
    claves = np.c_[np.repeat(grupos, 3), claves]
    _, inv = np.unique(claves, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    suma = np.zeros((inv.max() + 1, 3))
    np.add.at(suma, inv, np.repeat(fn, 3, axis=0))
    n = _unit(suma[inv])
    facet = np.repeat(unit, 3, axis=0)
    viva = np.einsum("ij,ij->i", n, facet) < math.cos(math.radians(angulo))
    n[viva] = facet[viva]
    return tris.reshape(-1, 3).astype(np.float32), n.astype(np.float32)


# ---------------------------------------------------------------- cuerpos del diseño → objetos de render
# Fuente única (sin Qt) de cómo se pinta un cuerpo: la usan el visor, el render y la API de agentes.
ACERO = (0.72, 0.72, 0.73)                  # "Acero - Satinado", el aspecto por defecto de Fusion (gris neutro)
COLOR_SUPERFICIE = (0.93, 0.78, 0.52)       # cuerpos de superficie: tono arena como en Fusion
COLOR_MALLA = (0.66, 0.72, 0.74)


def es_malla(forma):
    """Los cuerpos de malla guardan un objeto `Malla` (vértices + caras) en vez de una forma OCC."""
    return hasattr(forma, "vertices") and hasattr(forma, "caras") and not callable(getattr(forma, "caras"))


def malla_suave(forma, deflexion=0.05):
    """(vértices, normales) float32 de triángulos sueltos. B-rep: en cada vértice, la normal EXACTA de la
    superficie (hacia afuera del material), como la del análisis de cebra; promediar los triángulos torcía
    la normal en las caras B-spline (teselado irregular) y los brillos salían como franjas dentadas. Una cara
    sin superficie (solo triangulación, p. ej. de un STEP teselado) usa la normal promediada. Cuerpos de
    malla: normales promediadas con ángulo de pliegue."""
    if es_malla(forma):
        tris = np.asarray(forma.vertices, float)[np.asarray(forma.caras, int)]
        return normales_suaves(tris, None, 35.0)
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location

    from .analisis import _indices, _props_nodos
    verts, norms = [], []
    for cara, tris in geo.teselar_por_cara(forma, deflexion, 0.25):
        if BRep_Tool.Surface_s(cara) is None:
            n = normales_suaves(tris, None, 60.0)[1]
        else:
            tri = BRep_Tool.Triangulation_s(cara, TopLoc_Location())
            idx = _indices(tri, cara)
            n = _props_nodos(cara, tri, idx, tris, False)[0][idx].reshape(-1, 3)
        verts.append(tris.reshape(-1, 3))
        norms.append(n)
    if not verts:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)
    return np.concatenate(verts).astype(np.float32), _unit(np.concatenate(norms)).astype(np.float32)


def color_y_acabado(cuerpo, props):
    """Color sRGB y acabado de un cuerpo con la misma prioridad que el visor del diseño: Aspecto del documento,
    Material físico del documento, aspecto/material del propio cuerpo y, si no hay nada, acero satinado.
    `props` son las propiedades del cuerpo en el documento (`doc.propiedades.get(id)`)."""
    from .analisis import TABLA_MATERIALES
    props = props or {}
    material = props.get("material") or getattr(cuerpo, "material", None)
    if props.get("apariencia"):
        color = props["apariencia"]
    elif props.get("material") in TABLA_MATERIALES:
        color = TABLA_MATERIALES[props["material"]]["color"]
    elif getattr(cuerpo, "apariencia", None):
        color = cuerpo.apariencia
    elif material in TABLA_MATERIALES:
        color = TABLA_MATERIALES[material]["color"]
    else:
        tipo = getattr(cuerpo, "tipo", "solido")
        color = COLOR_SUPERFICIE if tipo == "superficie" else COLOR_MALLA if tipo == "malla" else ACERO
    return [float(c) for c in color][:3], acabado_normalizado(props.get("acabado"), material)


# ---------------------------------------------------------------- cámara
def camara(R, objetivo, distancia, fov=40.0, ortografica=False):
    """Cámara como la del visor: R (filas: derecha, arriba, atrás), objetivo, distancia, fov vertical."""
    return {"R": np.asarray(R, float).tolist(), "objetivo": [float(c) for c in objetivo],
            "distancia": float(distancia), "fov": float(fov), "ortografica": bool(ortografica)}


def matrices_camara(cam, aspecto):
    """(proyección 4x4, vista 4x4) con las mismas convenciones que `Visor3D._matrices`."""
    R = np.asarray(cam["R"], float)
    d = float(cam["distancia"])
    ojo = np.asarray(cam["objetivo"], float) + R[2] * d
    vista = np.identity(4)
    vista[:3, :3] = R
    vista[:3, 3] = -R @ ojo
    fov = float(cam.get("fov", 40.0))
    cerca, lejos = d * 0.01, d * 20 + 1000
    m = np.zeros((4, 4))
    if cam.get("ortografica"):
        mh = d * math.tan(math.radians(fov) / 2)
        m[0, 0], m[1, 1] = 1 / (mh * aspecto), 1 / mh
        m[2, 2], m[2, 3], m[3, 3] = -1 / lejos, 0.0, 1.0
    else:
        f = 1.0 / math.tan(math.radians(fov) / 2)
        m[0, 0], m[1, 1] = f / aspecto, f
        m[2, 2] = (lejos + cerca) / (cerca - lejos)
        m[2, 3] = 2 * lejos * cerca / (cerca - lejos)
        m[3, 2] = -1
    return m, vista


# ---------------------------------------------------------------- rasterizador (z-buffer vectorizado)
_LIMITE = 1 << 21          # muestras por tanda (acota la memoria)


def _merge(zbuf, idbuf, pix, z, tid):
    if not len(pix):
        return
    orden = np.lexsort((z, pix))
    p = pix[orden]
    primero = np.r_[True, p[1:] != p[:-1]]
    p, zz, tt = p[primero], z[orden][primero], tid[orden][primero]
    mejor = zz < zbuf[p]
    zbuf[p[mejor]] = zz[mejor]
    idbuf[p[mejor]] = tt[mejor]


def rasterizar(sx, sy, sz, ancho, alto, validos=None, zbuf=None, idbuf=None, base=0):
    """z-buffer de triángulos ya proyectados: sx, sy (píxeles, y hacia abajo) y sz (profundidad, menor = más
    cerca), arrays Tx3. Muestrea el centro de cada píxel. Devuelve (zbuf, idbuf) planos (alto·ancho), con
    idbuf = índice del triángulo + `base` o -1. Si se pasan zbuf/idbuf se actualizan (otra capa)."""
    sx, sy, sz = (np.asarray(a, np.float64) for a in (sx, sy, sz))
    if zbuf is None:
        zbuf = np.full(ancho * alto, np.inf)
        idbuf = np.full(ancho * alto, -1, np.int64)
    if not len(sx):
        return zbuf, idbuf
    x0 = np.clip(np.ceil(sx.min(1) - 0.5), 0, ancho - 1).astype(np.int64)
    x1 = np.clip(np.floor(sx.max(1) - 0.5), -1, ancho - 1).astype(np.int64)
    y0 = np.clip(np.ceil(sy.min(1) - 0.5), 0, alto - 1).astype(np.int64)
    y1 = np.clip(np.floor(sy.max(1) - 0.5), -1, alto - 1).astype(np.int64)
    area = (sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0]) - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0])
    ok = (x1 >= x0) & (y1 >= y0) & (np.abs(area) > 1e-12) & np.isfinite(sz).all(1)
    ok &= (sx.max(1) >= 0) & (sx.min(1) <= ancho) & (sy.max(1) >= 0) & (sy.min(1) <= alto)
    if validos is not None:
        ok &= validos
    idx = np.nonzero(ok)[0]
    if not len(idx):
        return zbuf, idbuf
    cw = 1 << np.ceil(np.log2(x1[idx] - x0[idx] + 1)).astype(np.int64)
    ch = 1 << np.ceil(np.log2(y1[idx] - y0[idx] + 1)).astype(np.int64)
    clave = cw * 65536 + ch
    orden = np.argsort(clave, kind="stable")
    idx, clave = idx[orden], clave[orden]
    cortes = np.r_[np.nonzero(np.diff(clave))[0] + 1, len(clave)]
    inicio = 0
    for fin in cortes:
        sel = idx[inicio:fin]
        w, h = int(clave[inicio] // 65536), int(clave[inicio] % 65536)
        inicio = fin
        filas = max(1, min(h, _LIMITE // w))
        tanda = max(1, _LIMITE // (w * filas))
        for k in range(0, len(sel), tanda):
            s = sel[k:k + tanda]
            for f0 in range(0, h, filas):
                _rasterizar_tanda(s, w, f0, min(filas, h - f0), sx, sy, sz, x0, x1, y0, y1, area, ancho,
                                  zbuf, idbuf, base)
    return zbuf, idbuf


def _rasterizar_tanda(s, w, f0, h, sx, sy, sz, x0, x1, y0, y1, area, ancho, zbuf, idbuf, base):
    px = x0[s, None, None] + np.arange(w)[None, None, :]
    py = y0[s, None, None] + f0 + np.arange(h)[None, :, None]
    caja = (px <= x1[s, None, None]) & (py <= y1[s, None, None])
    cx, cy = px + 0.5, py + 0.5
    ax, ay, bx, by, kx, ky = (a[:, None, None] for a in (sx[s, 0], sy[s, 0], sx[s, 1], sy[s, 1], sx[s, 2], sy[s, 2]))
    ar = area[s, None, None]
    la = ((bx - cx) * (ky - cy) - (by - cy) * (kx - cx)) / ar
    lb = ((kx - cx) * (ay - cy) - (ky - cy) * (ax - cx)) / ar
    lc = 1.0 - la - lb
    m = caja & (la >= -1e-7) & (lb >= -1e-7) & (lc >= -1e-7)
    if not m.any():
        return
    z = la * sz[s, 0, None, None] + lb * sz[s, 1, None, None] + lc * sz[s, 2, None, None]
    pix = np.broadcast_to(py * ancho + px, m.shape)[m]
    tid = np.broadcast_to(s[:, None, None] + base, m.shape)[m]
    _merge(zbuf, idbuf, pix, z[m], tid)


def baricentricas(sx, sy, idbuf, ancho):
    """(píxeles con triángulo, ids, λ Nx3) en el centro de cada píxel (coordenadas de pantalla)."""
    pix = np.nonzero(idbuf >= 0)[0]
    t = idbuf[pix]
    cx, cy = pix % ancho + 0.5, pix // ancho + 0.5
    ax, ay, bx, by, kx, ky = sx[t, 0], sy[t, 0], sx[t, 1], sy[t, 1], sx[t, 2], sy[t, 2]
    ar = (bx - ax) * (ky - ay) - (kx - ax) * (by - ay)
    la = ((bx - cx) * (ky - cy) - (by - cy) * (kx - cx)) / ar
    lb = ((kx - cx) * (ay - cy) - (ky - cy) * (ax - cx)) / ar
    return pix, t, np.c_[la, lb, 1.0 - la - lb]


def _proyectar(v, mvp, ancho, alto):
    h = np.c_[v, np.ones(len(v))] @ mvp.T
    w = h[:, 3]
    ws = np.where(np.abs(w) < 1e-12, 1e-12, w)
    return (h[:, 0] / ws + 1) * 0.5 * ancho, (1 - h[:, 1] / ws) * 0.5 * alto, h[:, 2] / ws, w


# ---------------------------------------------------------------- mapa de sombras
# Disco de Poisson (16 muestras, radio 1) del filtrado de sombras; el shader GLSL usa el mismo.
DISCO_PCF = ((-0.942, -0.399), (0.946, -0.769), (-0.094, -0.929), (0.345, 0.294), (-0.916, 0.458),
             (-0.815, -0.879), (-0.383, 0.277), (0.975, 0.756), (0.443, -0.975), (0.537, -0.474),
             (-0.265, -0.419), (0.792, 0.191), (-0.242, 0.997), (-0.814, 0.914), (0.200, 0.786),
             (0.144, -0.141))


class MapaSombras:
    """Profundidad de la escena vista desde la luz principal (proyección ortográfica ajustada a la esfera
    que envuelve los triángulos). `visibilidad(p, n)` → 0 (sombra) … 1 (iluminado), filtrada con un disco
    de Poisson (penumbra = `blando` × radio de la escena)."""

    def __init__(self, tris, direccion, resolucion=2048, blando=SOMBRA_BLANDO):
        self.blando = float(blando)
        tris = np.asarray(tris, np.float64).reshape(-1, 3, 3)
        pts = tris.reshape(-1, 3)
        self.centro = (pts.min(0) + pts.max(0)) / 2 if len(pts) else np.zeros(3)
        self.radio = max(float(np.linalg.norm(pts - self.centro, axis=1).max()) if len(pts) else 1.0, 1e-6) * 1.02
        self.atras = _unit(direccion)
        arriba = (0.0, 0.0, 1.0) if abs(self.atras[2]) < 0.95 else (0.0, 1.0, 0.0)
        self.der = _unit(np.cross(arriba, self.atras))
        self.arr = np.cross(self.atras, self.der)
        self.n = int(resolucion)
        self.texel = 2 * self.radio / self.n
        sx, sy, sz = self._a_mapa(pts)
        self.z, _ = rasterizar(sx.reshape(-1, 3), sy.reshape(-1, 3), sz.reshape(-1, 3), self.n, self.n)
        self.z = self.z.reshape(self.n, self.n)

    def _a_mapa(self, p):
        q = np.asarray(p, np.float64) - self.centro
        u, v, d = q @ self.der, q @ self.arr, q @ self.atras
        return (u / self.radio * 0.5 + 0.5) * self.n, (0.5 - v / self.radio * 0.5) * self.n, -d / self.radio

    def visibilidad(self, p, n):
        p = np.asarray(p, np.float64) + np.asarray(n, np.float64) * self.texel * 1.5
        sx, sy, sz = self._a_mapa(p)
        sesgo = 1.5 * self.texel / self.radio
        fuera = (sx < 0) | (sy < 0) | (sx >= self.n) | (sy >= self.n)
        radio = max(1.0, self.blando * self.radio / self.texel)        # penumbra en texeles
        luz = np.zeros(len(sx))
        for ox, oy in DISCO_PCF:
            jx = np.clip(np.floor(sx + ox * radio).astype(np.int64), 0, self.n - 1)
            jy = np.clip(np.floor(sy + oy * radio).astype(np.int64), 0, self.n - 1)
            luz += sz <= self.z[jy, jx] + sesgo * (1 + radio * 0.15)
        luz /= len(DISCO_PCF)
        luz[fuera] = 1.0
        return luz


# ---------------------------------------------------------------- sombreado
def sombrear(p, n, v, albedo, met, rug, barniz, cielo, rotacion, brillo, sombra, ao):
    """Modelo de sombreado (lineal). Devuelve (difuso Nx3, especular Nx3, Fresnel medio N): el color de una
    superficie opaca es difuso + especular. Igual que el shader GLSL del lienzo."""
    n = _unit(n)
    nv = np.clip(np.einsum("ij,ij->i", n, v), 1e-4, 1.0)
    f0 = 0.04 * (1 - met[:, None]) + albedo * met[:, None]
    fr = f0 + (np.maximum(1 - rug[:, None], f0) - f0) * ((1 - nv) ** 5)[:, None]
    alfa = np.maximum(rug * rug, 0.002)
    s = np.clip(2.0 / (alfa * alfa) - 2.0, 1.0, 4096.0)
    dif = irradiancia(n, cielo, brillo) * ao[:, None]
    esp = np.zeros_like(dif)
    for i, (L, k) in enumerate(zip(luces(rotacion), INTENSIDAD_LUCES, strict=True)):
        nl = np.clip(n @ L, 0.0, 1.0)
        vis = sombra if i == 0 else 1.0
        intensidad = k * float(cielo[2]) * brillo * nl * vis
        dif += intensidad[:, None]
        h = _unit(v + L)
        nh = np.clip(np.einsum("ij,ij->i", n, h), 0.0, 1.0)
        esp += fr * (intensidad * (s + 2) / (8 * math.pi) * nh ** s)[:, None]
    r = 2 * nv[:, None] * n - v
    nitido = radiancia_entorno(r, cielo, rotacion, brillo)
    difuso_r = irradiancia(r, cielo, brillo)
    k = np.clip(rug * 1.6, 0.0, 1.0)[:, None]
    env = nitido * (1 - k) + difuso_r * k
    occl = (0.5 + 0.5 * ao)[:, None]
    esp += fr * env * occl
    if np.any(barniz > 0):
        fc = (0.04 + 0.96 * (1 - nv) ** 5) * barniz
        esp = esp * (1 - fc[:, None]) + fc[:, None] * nitido * occl
        dif = dif * (1 - fc[:, None])
    dif = dif * albedo * (1 - met[:, None])
    return dif, esp, fr.mean(1)


def _ssao(pv, nv, zvista, proy, ancho, alto, radio, muestras=12):
    """Oclusión ambiental en espacio de pantalla: posiciones/normales de vista de los píxeles cubiertos y la
    profundidad de vista (z negativa hacia adelante; -inf donde no hay nada) de todo el mosaico."""
    rng = np.random.default_rng(7)
    dirs = _unit(rng.normal(size=(muestras, 3)))
    escalas = 0.25 + 0.75 * (np.arange(1, muestras + 1) / muestras) ** 2
    giro = (np.arange(len(pv)) * 2654435761 % 4096) / 4096.0 * 2 * math.pi
    c, s = np.cos(giro), np.sin(giro)
    ocl = np.zeros(len(pv))
    for d, e in zip(dirs, escalas, strict=True):
        dd = np.c_[c * d[0] - s * d[1], s * d[0] + c * d[1], np.full(len(pv), d[2])]
        dd *= np.where(np.einsum("ij,ij->i", dd, nv) < 0, -1.0, 1.0)[:, None]
        q = pv + dd * radio * e
        h = np.c_[q, np.ones(len(q))] @ proy.T
        w = np.where(np.abs(h[:, 3]) < 1e-12, 1e-12, h[:, 3])
        ix = np.floor((h[:, 0] / w + 1) * 0.5 * ancho).astype(np.int64)
        iy = np.floor((1 - h[:, 1] / w) * 0.5 * alto).astype(np.int64)
        dentro = (ix >= 0) & (iy >= 0) & (ix < ancho) & (iy < alto)
        zq = np.full(len(q), -np.inf)
        zq[dentro] = zvista[iy[dentro] * ancho + ix[dentro]]
        delante = zq > q[:, 2] + radio * 0.02
        rango = _smooth(0.0, 1.0, radio / np.maximum(np.abs(zq - pv[:, 2]), 1e-9))
        ocl += np.where(delante & np.isfinite(zq), rango, 0.0)
    return np.clip(1.0 - ocl / muestras * 1.1, 0.25, 1.0)


def _desenfocar(img, mascara, radio):
    """Caja separable (con máscara) para los reflejos del suelo según su rugosidad."""
    if radio < 1:
        return img
    a = np.concatenate([img * mascara[..., None], mascara[..., None]], axis=-1)
    for eje in (0, 1):
        c = np.cumsum(np.pad(a, [(radio + 1, radio) if k == eje else (0, 0) for k in range(3)], mode="edge"), axis=eje)
        n = a.shape[eje]
        a = (np.take(c, np.arange(2 * radio + 1, 2 * radio + 1 + n), axis=eje) -
             np.take(c, np.arange(0, n), axis=eje)) / (2 * radio + 1)
    return a[..., :3] / np.maximum(a[..., 3:], 1e-6)


# ---------------------------------------------------------------- escena preparada
class RenderCancelado(Exception):
    pass


class _Escena:
    def __init__(self, objetos, escena, cielo, z_suelo, res_sombras):
        self.e = escena_normalizada(escena)
        self.cielo = cielo or CIELO_DEFECTO
        tris, nors, locs, albedo, mats = [], [], [], [], []
        for o in objetos:
            op = float(o.get("opacidad", 1.0))
            v = np.asarray(o["v"], np.float64).reshape(-1, 3)
            if op <= 0.01 or not len(v):
                continue
            ac = acabado_normalizado(o.get("acabado"), o.get("material"))
            k = len(v) // 3
            tris.append(v[:k * 3].reshape(k, 3, 3))
            nors.append(np.asarray(o["n"], np.float64).reshape(-1, 3)[:k * 3].reshape(k, 3, 3))
            loc = o.get("local")
            locs.append((np.asarray(loc, np.float64).reshape(-1, 3) if loc is not None else v)[:k * 3].reshape(k, 3, 3))
            color = srgb_a_lineal(o.get("color") or BIBLIOTECA_ASPECTOS[ASPECTO_DEFECTO]["color"])
            c2 = srgb_a_lineal(ac["color2"]) if ac.get("color2") else color * 0.6
            albedo.append(np.tile(np.r_[color, c2], (k, 1)))
            transp = max(ac["transparencia"], 1.0 - op)
            fundido = 1.0 if ac["transparencia"] < 0.02 and op < 0.999 else 0.0     # opaco que se desvanece
            mats.append(np.tile([ac["metalico"], ac["rugosidad"], transp, ac["barniz"],
                                 1.0 if ac["patron"] == "madera" else 0.0, fundido], (k, 1)))
        vacio = np.zeros((0, 3, 3))
        self.tris = np.concatenate(tris) if tris else vacio
        self.nors = np.concatenate(nors) if nors else vacio
        self.locs = np.concatenate(locs) if locs else vacio
        self.albedo = np.concatenate(albedo) if albedo else np.zeros((0, 6))
        self.mats = np.concatenate(mats) if mats else np.zeros((0, 6))
        self.opacos = self.mats[:, 2] < 0.02
        pts = self.tris.reshape(-1, 3)
        self.min = pts.min(0) if len(pts) else np.zeros(3)
        self.max = pts.max(0) if len(pts) else np.zeros(3)
        self.centro = (self.min + self.max) / 2
        self.radio = max(float(np.linalg.norm(self.max - self.min)) / 2, 1.0)
        self.z_suelo = float(self.min[2]) if z_suelo is None else float(z_suelo)
        self.res_sombras = res_sombras
        self._sombras = None

    @property
    def sombras(self):
        if self._sombras is None and self.e["sombras"] and len(self.tris):
            casters = self.tris[self.mats[:, 2] < 0.6]
            if len(casters):
                self._sombras = MapaSombras(casters, luces(self.e["rotacion"])[0], self.res_sombras)
        return self._sombras

    def visibilidad(self, p, n):
        s = self.sombras
        return s.visibilidad(p, n) if s is not None else np.ones(len(p))


def _sub_proyeccion(proy, x0, y0, x1, y1, ancho, alto):
    """Proyección del mosaico [x0, x1) × [y0, y1) (píxeles de la imagen completa)."""
    nx0, nx1 = 2 * x0 / ancho - 1, 2 * x1 / ancho - 1
    ny1, ny0 = 1 - 2 * y0 / alto, 1 - 2 * y1 / alto
    s = np.identity(4)
    s[0, 0], s[0, 3] = 2 / (nx1 - nx0), -(nx1 + nx0) / (nx1 - nx0)
    s[1, 1], s[1, 3] = 2 / (ny1 - ny0), -(ny1 + ny0) / (ny1 - ny0)
    return s @ proy


def _rayos(proy, vista, ancho, alto):
    """Origen y dirección (mundo) del rayo de cada píxel del mosaico."""
    inv = np.linalg.inv(proy @ vista)
    xs = (np.arange(ancho) + 0.5) / ancho * 2 - 1
    ys = 1 - (np.arange(alto) + 0.5) / alto * 2
    gx, gy = np.meshgrid(xs, ys)
    a = np.c_[gx.ravel(), gy.ravel(), -np.ones(gx.size), np.ones(gx.size)] @ inv.T
    b = np.c_[gx.ravel(), gy.ravel(), np.ones(gx.size), np.ones(gx.size)] @ inv.T
    a, b = a[:, :3] / a[:, 3:], b[:, :3] / b[:, 3:]
    return a, _unit(b - a)


def _capa(esc, mvp, ancho, alto, seleccion, zbuf=None, espejo=None):
    tris = esc.tris if espejo is None else espejo
    v = tris.reshape(-1, 3)
    sx, sy, sz, w = _proyectar(v, mvp, ancho, alto)
    sx, sy, sz, w = (a.reshape(-1, 3) for a in (sx, sy, sz, w))
    validos = seleccion & (w > 1e-9).all(1)
    idbuf = None if zbuf is None else np.full(ancho * alto, -1, np.int64)
    zbuf, idbuf = rasterizar(sx, sy, sz, ancho, alto, validos, None if zbuf is None else zbuf.copy(), idbuf)
    pix, t, lam = baricentricas(sx, sy, idbuf, ancho)
    lw = lam / w[t]                         # baricéntricas con corrección de perspectiva
    lw /= lw.sum(1, keepdims=True)
    return zbuf, pix, t, lw


def _gbuffer(esc, t, lw, espejo=None):
    tris = esc.tris if espejo is None else espejo
    p = np.einsum("ij,ijk->ik", lw, tris[t])
    nors = esc.nors[t] * (np.array([1.0, 1.0, -1.0]) if espejo is not None else 1.0)
    n = _unit(np.einsum("ij,ijk->ik", lw, nors))
    return p, n


def _sombrear_pixeles(esc, p, n, v, t, lw, sombra, ao):
    m = esc.mats[t]
    alb = esc.albedo[t]
    color = alb[:, :3].copy()
    madera = m[:, 4] > 0.5
    if madera.any():
        loc = np.einsum("ij,ijk->ik", lw[madera], esc.locs[t[madera]])
        color[madera] = veta_madera(loc, alb[madera, :3], alb[madera, 3:])
    n = np.where((np.einsum("ij,ij->i", n, v) < 0)[:, None], -n, n)       # doble cara
    dif, esp, fr = sombrear(p, n, v, color, m[:, 0], m[:, 1], m[:, 3], esc.cielo, esc.e["rotacion"],
                            esc.e["brillo"], sombra, ao)
    return dif, esp, fr, color, m[:, 2]


def _render_mosaico(esc, cam, proy_total, vista, ancho_t, alto_t, x0, y0, x1, y1, fondo_transparente):
    """Imagen premultiplicada (alto, ancho, 4) del mosaico [x0, x1) × [y0, y1)."""
    w, h = x1 - x0, y1 - y0
    proy = _sub_proyeccion(proy_total, x0, y0, x1, y1, ancho_t, alto_t)
    mvp = proy @ vista
    e = esc.e
    orig, dirs = _rayos(proy, vista, w, h)
    if fondo_transparente:
        rgb, alfa = np.zeros((w * h, 3)), np.zeros(w * h)
    elif e["fondo"] == "color":
        rgb, alfa = np.tile(np.asarray(e["color_fondo"], np.float64), (w * h, 1)), np.ones(w * h)
    else:
        rgb, alfa = color_fondo_entorno(dirs, esc.cielo), np.ones(w * h)

    zbuf, pix, t, lw = _capa(esc, mvp, w, h, esc.opacos)
    ojo = np.asarray(cam["objetivo"], float) + np.asarray(cam["R"], float)[2] * float(cam["distancia"])
    # suelo: sombra y reflejo sobre el fondo (un «captador de sombras», como el suelo del render de Fusion)
    if e["suelo"] and len(esc.tris):
        den = np.where(np.abs(dirs[:, 2]) < 1e-9, -1e-9, dirs[:, 2])
        tg = (esc.z_suelo - orig[:, 2]) / den
        pg = orig + dirs * tg[:, None]
        hg = np.c_[pg, np.ones(len(pg))] @ mvp.T
        zg = hg[:, 2] / np.where(np.abs(hg[:, 3]) < 1e-12, 1e-12, hg[:, 3])
        suelo = (dirs[:, 2] < -1e-6) & (tg > 0) & (zg < zbuf)
        dist = np.linalg.norm(pg[:, :2] - esc.centro[:2], axis=1)
        rxy = max(float(np.linalg.norm(esc.max[:2] - esc.min[:2])) / 2, esc.radio * 0.3)
        fade = np.where(suelo, 1 - _smooth(rxy * 0.9, rxy * 3.2, dist), 0.0)
        if e["reflejos"]:
            espejo = esc.tris * np.array([1.0, 1.0, -1.0]) + np.array([0.0, 0.0, 2 * esc.z_suelo])
            arriba = esc.tris[:, :, 2].max(1) >= esc.z_suelo - 1e-4 * esc.radio     # lo de abajo del suelo no se refleja
            zr, pr_, tr, lr = _capa(esc, mvp, w, h, esc.opacos & arriba, espejo=espejo)
            if len(pr_):
                p, n = _gbuffer(esc, tr, lr, espejo)
                v = _unit(ojo - p) if not cam.get("ortografica") else np.tile(np.asarray(cam["R"])[2], (len(p), 1))
                dif, esp, _fr, _c, _t = _sombrear_pixeles(esc, p, n, v, tr, lr, np.ones(len(p)), np.ones(len(p)))
                img = np.zeros((h, w, 3))
                mask = np.zeros((h, w))
                img.reshape(-1, 3)[pr_] = mapa_tonos(dif + esp, e["exposicion"])
                mask.reshape(-1)[pr_] = 1.0
                img = _desenfocar(img, mask, int(round(e["rugosidad_suelo"] * 0.012 * max(ancho_t, alto_t))))
                fuerza = 0.42 * (1 - e["rugosidad_suelo"]) ** 1.5 * fade * mask.reshape(-1)
                fuerza = np.where(suelo, fuerza, 0.0)
                rgb = rgb * (1 - fuerza[:, None]) + img.reshape(-1, 3) * fuerza[:, None]
                alfa = alfa * (1 - fuerza) + fuerza
        if e["sombras"]:
            sel = np.nonzero(suelo & (fade > 0.002))[0]
            if len(sel):
                vis = esc.visibilidad(pg[sel], np.tile([0.0, 0.0, 1.0], (len(sel), 1)))
                osc = OSCURIDAD_SOMBRA * (1 - vis) * fade[sel]
                rgb[sel] *= (1 - osc)[:, None]
                alfa[sel] = alfa[sel] + osc * (1 - alfa[sel])

    def _vista(p):
        return _unit(ojo - p) if not cam.get("ortografica") else np.tile(np.asarray(cam["R"], float)[2], (len(p), 1))

    # cuerpos opacos
    if len(pix):
        p, n = _gbuffer(esc, t, lw)
        v = _vista(p)
        ao = np.ones(len(p))
        if e["oclusion"]:
            R = np.asarray(cam["R"], float)
            pv = (p - ojo) @ R.T
            nvista = n @ R.T
            nvista = np.where((np.einsum("ij,ij->i", nvista, -pv) < 0)[:, None] if not cam.get("ortografica")
                              else (nvista[:, 2] < 0)[:, None], -nvista, nvista)
            zv = np.full(w * h, -np.inf)
            zv[pix] = pv[:, 2]
            ao = _ssao(pv, nvista, zv, proy, w, h, esc.radio * 0.07)
        sombra = esc.visibilidad(p, np.where((np.einsum("ij,ij->i", n, v) < 0)[:, None], -n, n))
        dif, esp, _fr, _c, _t = _sombrear_pixeles(esc, p, n, v, t, lw, sombra, ao)
        rgb[pix] = mapa_tonos(dif + esp, e["exposicion"])
        alfa[pix] = 1.0

    # cuerpos transparentes (la capa más cercana delante de lo opaco)
    transp = ~esc.opacos
    if transp.any():
        _z, pix2, t2, lw2 = _capa(esc, mvp, w, h, transp, zbuf=zbuf)
        if len(pix2):
            p, n = _gbuffer(esc, t2, lw2)
            v = _vista(p)
            sombra = esc.visibilidad(p, n)
            dif, esp, fr, color, tr = _sombrear_pixeles(esc, p, n, v, t2, lw2, sombra, np.ones(len(p)))
            frente = mapa_tonos((1 - tr)[:, None] * (dif + esp) + tr[:, None] * esp, e["exposicion"])
            paso = (tr * (1 - fr))[:, None]
            tinte = 1 - tr[:, None] + tr[:, None] * lineal_a_srgb(color)
            fundido = esc.mats[t2, 5] > 0.5                  # opaco que se desvanece: mezcla simple
            if fundido.any():
                op = (1 - tr[fundido])[:, None]
                frente[fundido] = mapa_tonos(dif[fundido] + esp[fundido], e["exposicion"]) * op
                paso[fundido] = 1 - op
                tinte[fundido] = 1.0
            rgb[pix2] = frente + paso * tinte * rgb[pix2]
            alfa[pix2] = (1 - paso[:, 0]) + paso[:, 0] * alfa[pix2]
    return np.concatenate([rgb.reshape(h, w, 3), alfa.reshape(h, w, 1)], axis=2)


def renderizar(objetos, cam, escena=None, ancho=800, alto=600, supermuestreo=2, cielo=None,
               fondo_transparente=False, z_suelo=None, res_sombras=2048, progreso=None, mosaico=1024):
    """Imagen RGBA uint8 (alto, ancho, 4) de la escena.

    objetos: [{"v": triángulos sueltos Nx3 (mundo), "n": normales Nx3, "color": sRGB 0..1, "acabado": dict,
    "material": nombre del material físico (si no hay acabado), "opacidad": 0..1, "local": Nx3 (opcional,
    coordenadas propias para las vetas)}]. cam: dict de `camara()`. escena: Configuración de escena
    (`ESCENA_DEFECTO`). cielo: (arriba, abajo, intensidad) del entorno, en sRGB (visor3d.ENTORNOS).
    progreso(fracción) puede devolver False para cancelar (lanza RenderCancelado)."""
    ancho, alto, ss = int(ancho), int(alto), max(1, int(supermuestreo))
    if ancho < 1 or alto < 1:
        raise geo.ErrorGeometria("La imagen tiene que medir al menos 1 × 1 píxel.")
    esc = _Escena(objetos, escena, cielo, z_suelo, res_sombras)
    W, H = ancho * ss, alto * ss
    proy, vista = matrices_camara(cam, W / H)
    salida = np.zeros((alto, ancho, 4))
    paso = max(ss, (mosaico // ss) * ss)
    margen = 32 * ss if (esc.e["oclusion"] or esc.e["reflejos"]) else 0
    total = math.ceil(W / paso) * math.ceil(H / paso)
    hechos = 0
    if progreso is not None and progreso(0.0) is False:
        raise RenderCancelado()
    for ty in range(0, H, paso):
        for tx in range(0, W, paso):
            x0, y0 = max(0, tx - margen), max(0, ty - margen)
            x1, y1 = min(W, tx + paso + margen), min(H, ty + paso + margen)
            img = _render_mosaico(esc, cam, proy, vista, W, H, x0, y0, x1, y1, fondo_transparente)
            cx1, cy1 = min(W, tx + paso), min(H, ty + paso)
            img = img[ty - y0:ty - y0 + (cy1 - ty), tx - x0:tx - x0 + (cx1 - tx)]
            hh, ww = img.shape[0] // ss, img.shape[1] // ss
            img = img[:hh * ss, :ww * ss]
            red = img.reshape(hh, ss, ww, ss, 4).mean(axis=(1, 3))      # con fondo transparente: premultiplicada
            salida[ty // ss:ty // ss + hh, tx // ss:tx // ss + ww] = red
            hechos += 1
            if progreso is not None and progreso(hechos / total) is False:
                raise RenderCancelado()
    if fondo_transparente:
        a = salida[..., 3:]
        salida[..., :3] = np.where(a > 1e-6, salida[..., :3] / np.maximum(a, 1e-6), 0.0)
    else:
        salida[..., 3] = 1.0
    return (np.clip(salida, 0, 1) * 255 + 0.5).astype(np.uint8)


def guardar_png(imagen, ruta):
    """Guarda una imagen RGBA/RGB uint8 (alto, ancho, 3|4) como PNG."""
    from PIL import Image
    imagen = np.asarray(imagen, np.uint8)
    modo = "RGBA" if imagen.ndim == 3 and imagen.shape[2] == 4 else "RGB"
    try:
        Image.fromarray(imagen, modo).save(str(ruta), "PNG")
    except OSError as e:
        raise geo.ErrorGeometria(f"No se pudo guardar la imagen: {e}") from e
