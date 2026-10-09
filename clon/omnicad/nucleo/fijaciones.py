# -*- coding: utf-8 -*-
"""
INSERTAR › Insertar fijación (Insert Fastener) de Fusion 360 en el núcleo [SLD-FASTENERS,
SLD-INSERT-FASTENER, SLD-REF-INSERT-FASTENER]: biblioteca paramétrica de tornillos, tuercas, arandelas,
varilla roscada y espárragos con las medidas de sus normas (mm), y la colocación sobre la geometría
elegida (arista circular de un agujero, cara cilíndrica o cónica, o punto + dirección).

Posición canónica de `generar`: eje +Z, la cara de apoyo de la cabeza (o de la tuerca/arandela) en z = 0,
el vástago hacia −Z y la cabeza, tuerca o arandela hacia +Z. En los avellanados (ISO 10642) z = 0 es el
borde superior del cono (queda al ras de la cara) y en la varilla y los espárragos, su extremo superior.
`colocar` lleva ese marco al punto de apoyo con +Z saliendo del material.

Rosca "cosmetica": el vástago queda al diámetro nominal y el agujero de la tuerca al diámetro menor
básico, como dibuja Fusion la rosca cosmética; "modelada": se corta el filete helicoidal (perfil básico
ISO de 60°, con las piezas de hélice de `solidos_crear`) hasta el largo roscado de la norma.
"""
import math

import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeWire)
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.GC import GC_MakeArcOfCircle
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Cylinder
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.OCP.collections import List_TopoDS_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_IN
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax1, gp_Dir, gp_Lin, gp_Pnt, gp_Vec

from . import geometria as geo
from . import referencias as rf
from .solidos_crear import _barrido_helicoidal, _helice, _poligono, datos_rosca

FAMILIAS = {"tornillo": "Tornillos", "tuerca": "Tuercas", "arandela": "Arandelas", "varilla": "Varilla roscada",
            "esparrago": "Espárragos (prisioneros)"}
TIPOS_ROSCA = {"cosmetica": "Cosmética", "modelada": "Modelada"}

# Largos nominales preferidos (ISO 888 / tablas de ISO 4762, 4017…). Cada norma y tamaño usa su tramo.
SERIE_LARGOS = (2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100, 110,
                120, 130, 140, 150, 160, 180, 200, 220, 240, 260, 280, 300)
SERIE_VARILLA = (10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300, 500, 1000, 2000)
TAMANOS = ("M2", "M2.5", "M3", "M4", "M5", "M6", "M8", "M10", "M12", "M14", "M16", "M20", "M24")

# Pasos libres ISO 273 (fino, medio, grueso): con ellos se reconoce el tamaño de un agujero pasante.
PASO_LIBRE = {"M2": (2.2, 2.4, 2.6), "M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6), "M4": (4.3, 4.5, 4.8),
              "M5": (5.3, 5.5, 5.8), "M6": (6.4, 6.6, 7.0), "M8": (8.4, 9.0, 10.0), "M10": (10.5, 11.0, 12.0),
              "M12": (13.0, 13.5, 14.5), "M14": (15.0, 15.5, 16.5), "M16": (17.0, 17.5, 18.5),
              "M20": (21.0, 22.0, 24.0), "M24": (25.0, 26.0, 28.0)}


def _tabla(campos, filas):
    return {f[0]: dict(zip(campos, f[1:], strict=True)) for f in filas}


# ---------------------------------------------------------------- normas (medidas en mm)
# dk: diámetro de cabeza · k: alto de cabeza · s: entrecaras (hexágono o llave allen) · t: profundidad del
# allen · b: largo roscado · l: (largo mínimo, máximo) · m/h: alto de tuerca · d1/d2/h: arandela.
NORMAS = {
    "ISO 4762": {"familia": "tornillo", "descripcion": "Tornillo cabeza cilíndrica allen", "cabeza": "cilindrica",
                 "tabla": _tabla(("dk", "k", "s", "t", "b", "l"), [
                     ("M2", 3.8, 2, 1.5, 1.0, 16, (3, 20)), ("M2.5", 4.5, 2.5, 2, 1.1, 17, (4, 25)),
                     ("M3", 5.5, 3, 2.5, 1.3, 18, (5, 30)), ("M4", 7, 4, 3, 2, 20, (6, 40)),
                     ("M5", 8.5, 5, 4, 2.5, 22, (8, 50)), ("M6", 10, 6, 5, 3, 24, (10, 60)),
                     ("M8", 13, 8, 6, 4, 28, (12, 80)), ("M10", 16, 10, 8, 5, 32, (16, 100)),
                     ("M12", 18, 12, 10, 6, 36, (20, 120)), ("M14", 21, 14, 12, 7, 40, (25, 140)),
                     ("M16", 24, 16, 14, 8, 44, (25, 160)), ("M20", 30, 20, 17, 10, 52, (30, 200)),
                     ("M24", 36, 24, 19, 12, 60, (40, 200))])},
    "ISO 4014": {"familia": "tornillo", "descripcion": "Tornillo cabeza hexagonal, rosca parcial",
                 "cabeza": "hexagonal", "tabla": _tabla(("s", "k", "l"), [
                     ("M3", 5.5, 2, (20, 30)), ("M4", 7, 2.8, (25, 40)), ("M5", 8, 3.5, (25, 50)),
                     ("M6", 10, 4, (30, 60)), ("M8", 13, 5.3, (40, 80)), ("M10", 16, 6.4, (45, 100)),
                     ("M12", 18, 7.5, (50, 120)), ("M14", 21, 8.8, (60, 140)), ("M16", 24, 10, (65, 160)),
                     ("M20", 30, 12.5, (80, 200)), ("M24", 36, 15, (90, 240))])},
    "ISO 4017": {"familia": "tornillo", "descripcion": "Tornillo cabeza hexagonal, rosca total",
                 "cabeza": "hexagonal", "tabla": _tabla(("s", "k", "l"), [
                     ("M2", 4, 1.4, (4, 20)), ("M2.5", 5, 1.7, (5, 25)), ("M3", 5.5, 2, (6, 30)),
                     ("M4", 7, 2.8, (8, 40)), ("M5", 8, 3.5, (10, 50)), ("M6", 10, 4, (12, 60)),
                     ("M8", 13, 5.3, (16, 80)), ("M10", 16, 6.4, (20, 100)), ("M12", 18, 7.5, (25, 120)),
                     ("M14", 21, 8.8, (30, 140)), ("M16", 24, 10, (30, 160)), ("M20", 30, 12.5, (40, 200)),
                     ("M24", 36, 15, (50, 200))])},
    "ISO 7380": {"familia": "tornillo", "descripcion": "Tornillo cabeza abotonada allen", "cabeza": "abotonada",
                 "tabla": _tabla(("dk", "k", "s", "t", "l"), [
                     ("M3", 5.7, 1.65, 2, 1.04, (6, 12)), ("M4", 7.6, 2.2, 2.5, 1.3, (8, 16)),
                     ("M5", 9.5, 2.75, 3, 1.56, (10, 30)), ("M6", 10.5, 3.3, 4, 2.08, (10, 30)),
                     ("M8", 14, 4.4, 5, 2.6, (10, 40)), ("M10", 17.5, 5.5, 6, 3.12, (16, 40)),
                     ("M12", 21, 6.6, 8, 4.16, (16, 50)), ("M16", 28, 8.8, 10, 5.2, (20, 50))])},
    "ISO 10642": {"familia": "tornillo", "descripcion": "Tornillo cabeza avellanada allen (90°)",
                  "cabeza": "avellanada", "tabla": _tabla(("dk", "s", "t", "b", "l"), [
                      ("M3", 6.72, 2, 1.1, 18, (8, 30)), ("M4", 8.96, 2.5, 1.5, 20, (8, 40)),
                      ("M5", 11.2, 3, 1.9, 22, (8, 50)), ("M6", 13.44, 4, 2.2, 24, (8, 60)),
                      ("M8", 17.92, 5, 3, 28, (10, 80)), ("M10", 22.4, 6, 3.6, 32, (12, 100)),
                      ("M12", 26.88, 8, 4.3, 36, (20, 100)), ("M14", 30.24, 10, 4.5, 40, (25, 100)),
                      ("M16", 33.6, 10, 4.8, 44, (30, 100)), ("M20", 40.32, 12, 5.6, 52, (35, 100))])},
    "ISO 7045": {"familia": "tornillo", "descripcion": "Tornillo cabeza alomada Phillips (simplificada)",
                 "cabeza": "alomada", "tabla": _tabla(("dk", "k", "m", "ph", "l"), [
                     ("M2", 4, 1.6, 1.9, 0, (3, 20)), ("M2.5", 5, 2.1, 2.7, 1, (3, 25)),
                     ("M3", 5.6, 2.4, 3, 1, (4, 30)), ("M4", 8, 3.1, 4.4, 2, (5, 40)),
                     ("M5", 9.5, 3.7, 4.9, 2, (6, 45)), ("M6", 12, 4.6, 6.9, 3, (8, 60)),
                     ("M8", 16, 6, 9, 4, (10, 60)), ("M10", 20, 7.5, 10.1, 4, (12, 60))])},
    "ISO 4032": {"familia": "tuerca", "descripcion": "Tuerca hexagonal", "tabla": _tabla(("s", "m"), [
        ("M2", 4, 1.6), ("M2.5", 5, 2), ("M3", 5.5, 2.4), ("M4", 7, 3.2), ("M5", 8, 4.7), ("M6", 10, 5.2),
        ("M8", 13, 6.8), ("M10", 16, 8.4), ("M12", 18, 10.8), ("M14", 21, 12.8), ("M16", 24, 14.8),
        ("M20", 30, 18), ("M24", 36, 21.5)])},
    "ISO 4035": {"familia": "tuerca", "descripcion": "Tuerca hexagonal baja", "tabla": _tabla(("s", "m"), [
        ("M2", 4, 1.2), ("M2.5", 5, 1.6), ("M3", 5.5, 1.8), ("M4", 7, 2.2), ("M5", 8, 2.7), ("M6", 10, 3.2),
        ("M8", 13, 4), ("M10", 16, 5), ("M12", 18, 6), ("M14", 21, 7), ("M16", 24, 8), ("M20", 30, 10),
        ("M24", 36, 12)])},
    "ISO 10511": {"familia": "tuerca", "descripcion": "Tuerca autoblocante con inserto de nylon (simplificada)",
                  "tabla": _tabla(("s", "m"), [
                      ("M3", 5.5, 3.9), ("M4", 7, 5), ("M5", 8, 5), ("M6", 10, 6), ("M8", 13, 8), ("M10", 16, 10),
                      ("M12", 18, 12), ("M14", 21, 14), ("M16", 24, 16), ("M20", 30, 20), ("M24", 36, 24)])},
    "ISO 7089": {"familia": "arandela", "descripcion": "Arandela plana, serie normal",
                 "tabla": _tabla(("d1", "d2", "h"), [
                     ("M2", 2.2, 5, 0.3), ("M2.5", 2.7, 6, 0.5), ("M3", 3.2, 7, 0.5), ("M4", 4.3, 9, 0.8),
                     ("M5", 5.3, 10, 1), ("M6", 6.4, 12, 1.6), ("M8", 8.4, 16, 1.6), ("M10", 10.5, 20, 2),
                     ("M12", 13, 24, 2.5), ("M14", 15, 28, 2.5), ("M16", 17, 30, 3), ("M20", 21, 37, 3),
                     ("M24", 25, 44, 4)])},
    "ISO 7090": {"familia": "arandela", "descripcion": "Arandela plana achaflanada, serie normal", "chaflan": True,
                 "tabla": _tabla(("d1", "d2", "h"), [
                     ("M5", 5.3, 10, 1), ("M6", 6.4, 12, 1.6), ("M8", 8.4, 16, 1.6), ("M10", 10.5, 20, 2),
                     ("M12", 13, 24, 2.5), ("M14", 15, 28, 2.5), ("M16", 17, 30, 3), ("M20", 21, 37, 3),
                     ("M24", 25, 44, 4)])},
    "ISO 7092": {"familia": "arandela", "descripcion": "Arandela plana, serie pequeña",
                 "tabla": _tabla(("d1", "d2", "h"), [
                     ("M2", 2.2, 4.5, 0.3), ("M2.5", 2.7, 5, 0.5), ("M3", 3.2, 6, 0.5), ("M4", 4.3, 8, 0.5),
                     ("M5", 5.3, 9, 1), ("M6", 6.4, 11, 1.6), ("M8", 8.4, 15, 1.6), ("M10", 10.5, 18, 1.6),
                     ("M12", 13, 20, 2), ("M14", 15, 24, 2.5), ("M16", 17, 28, 2.5), ("M20", 21, 34, 3),
                     ("M24", 25, 39, 4)])},
    "DIN 976": {"familia": "varilla", "descripcion": "Varilla roscada", "tabla": {t: {} for t in TAMANOS}},
    "ISO 4026": {"familia": "esparrago", "descripcion": "Espárrago allen punta plana (prisionero)",
                 "tabla": _tabla(("s", "t", "dp", "l"), [
                     ("M2", 0.9, 0.8, 1, (2, 10)), ("M2.5", 1.3, 1.2, 1.5, (2.5, 12)), ("M3", 1.5, 1.2, 2, (3, 16)),
                     ("M4", 2, 1.5, 2.5, (4, 20)), ("M5", 2.5, 2, 3.5, (5, 25)), ("M6", 3, 2, 4, (6, 30)),
                     ("M8", 4, 3, 5.5, (8, 40)), ("M10", 5, 4, 7, (10, 50)), ("M12", 6, 4.8, 8.5, (12, 60)),
                     ("M16", 8, 6.4, 12, (16, 60)), ("M20", 10, 8, 15, (20, 60)), ("M24", 12, 10, 18, (25, 60))])},
}
_CON_LARGO = ("tornillo", "varilla", "esparrago")


# ---------------------------------------------------------------- consultas de la biblioteca
def _norma(norma):
    if norma not in NORMAS:
        raise geo.ErrorGeometria(f"Norma de fijación desconocida: {norma}")
    return NORMAS[norma]


def diametro_nominal(tamano):
    try:
        return float(str(tamano).strip().upper().lstrip("M"))
    except ValueError:
        raise geo.ErrorGeometria(f"Tamaño desconocido: {tamano}") from None


def normas(familia):
    """Normas de una familia ("tornillo", "tuerca", "arandela", "varilla", "esparrago")."""
    if familia not in FAMILIAS:
        raise geo.ErrorGeometria(f"Familia de fijación desconocida: {familia}")
    return [n for n, d in NORMAS.items() if d["familia"] == familia]


def tamanos(norma):
    return list(_norma(norma)["tabla"])


def lleva_largo(norma):
    return _norma(norma)["familia"] in _CON_LARGO


def largos(norma, tamano):
    """Largos nominales de la norma para ese tamaño ([] para tuercas y arandelas)."""
    info = _norma(norma)
    if info["familia"] not in _CON_LARGO:
        return []
    if info["familia"] == "varilla":
        return [float(x) for x in SERIE_VARILLA]
    lmin, lmax = datos(norma, tamano)["l"]
    return [float(x) for x in SERIE_LARGOS if lmin <= x <= lmax]


def datos(norma, tamano):
    """Medidas de la norma para un tamaño, más `d` (nominal), `paso` y `rosca` (designación de la rosca)."""
    info = _norma(norma)
    if tamano not in info["tabla"]:
        raise geo.ErrorGeometria(f"{norma} no tiene el tamaño {tamano}.")
    r = datos_rosca(tamano)
    return dict(info["tabla"][tamano], d=diametro_nominal(tamano), paso=r["paso"], rosca=r["designacion"],
                diametro_menor=r["diametro_menor"], broca=r["broca"])


def designacion(norma, tamano, largo=None):
    """Nombre como el de Fusion: «ISO 4762 M6x20», «ISO 4032 M8»."""
    if lleva_largo(norma) and largo is not None:
        return f"{norma} {tamano}x{float(largo):g}"
    return f"{norma} {tamano}"


def _mas_cercano(valores, objetivo, clave=float):
    return min(valores, key=lambda v: (abs(clave(v) - objetivo), clave(v)))


def corregir(norma, tamano, largo=None):
    """(tamaño, largo, avisos): lleva un tamaño o largo que la norma no tiene al más cercano disponible
    (en el diálogo las listas son fijas: lo que no corresponde se corrige y se informa)."""
    avisos = []
    lista = tamanos(norma)
    if tamano not in lista:
        nuevo = _mas_cercano(lista, diametro_nominal(tamano), diametro_nominal)
        avisos.append(f"{norma} no tiene {tamano}: se usó {nuevo}.")
        tamano = nuevo
    if not lleva_largo(norma):
        return tamano, None, avisos
    opciones = largos(norma, tamano)
    if largo is None:
        return tamano, None, avisos
    largo = float(largo)
    if not any(abs(largo - x) < 1e-9 for x in opciones):
        nuevo = _mas_cercano(opciones, largo)
        avisos.append(f"{norma} {tamano} no viene de {largo:g} mm: se usó {nuevo:g} mm.")
        largo = nuevo
    return tamano, largo, avisos


def tamano_para_agujero(norma, diametro, *, interior=True, tol=0.05):
    """Tamaño automático según el diámetro del agujero (como «Automático» en el tamaño nominal de Fusion).

    Interior (agujero): paso libre ISO 273 medio, fino o grueso, broca de roscar, diámetro menor de la rosca
    o el nominal; en los avellanados además el diámetro de la cabeza (arista del cono). Exterior (perno o
    saliente): el diámetro nominal. Devuelve (tamaño, coincidencia); coincidencia None = no hubo calce exacto
    y se eligió el mayor tamaño que entra."""
    lista = tamanos(norma)
    D = float(diametro)
    criterios = []
    if interior:
        if _norma(norma).get("cabeza") == "avellanada":
            criterios.append(("avellanado", lambda t: datos(norma, t)["dk"], 0.06))
        criterios += [("paso libre medio", lambda t: PASO_LIBRE[t][1], 0),
                      ("paso libre fino", lambda t: PASO_LIBRE[t][0], 0),
                      ("paso libre grueso", lambda t: PASO_LIBRE[t][2], 0),
                      ("broca de roscar", lambda t: datos(norma, t)["broca"], 0),
                      ("rosca (diámetro menor)", lambda t: datos(norma, t)["diametro_menor"], 0)]
    criterios.append(("nominal", diametro_nominal, 0))
    for nombre, medida, relativa in criterios:
        for t in lista:
            if abs(medida(t) - D) <= max(tol, relativa * D):
                return t, nombre
    entran = [t for t in lista if diametro_nominal(t) <= D + tol] if interior else \
        [t for t in lista if diametro_nominal(t) >= D - tol]
    if not entran:
        return (lista[0] if interior else lista[-1]), None
    return (entran[-1] if interior else entran[0]), None


def largo_para_espesor(norma, tamano, espesor):
    """Largo automático: el menor largo de la norma que atraviesa `espesor` (None = un largo de ~2·d)."""
    opciones = largos(norma, tamano)
    if not opciones:
        return None
    if espesor is None or espesor <= 0:
        objetivo = 2 * diametro_nominal(tamano)
        return next((x for x in opciones if x >= objetivo), opciones[-1])
    return next((x for x in opciones if x >= espesor - 1e-6), opciones[-1])


def largo_roscado(norma, tamano, largo):
    """Largo roscado desde la punta: `b` de la tabla o la fórmula de ISO 4014; total en las de rosca total."""
    info, dt = _norma(norma), datos(norma, tamano)
    if norma == "ISO 4014":
        d = dt["d"]
        b = 2 * d + 6 if largo <= 125 else (2 * d + 12 if largo <= 200 else 2 * d + 25)
    elif norma == "ISO 7045":
        b = 38.0
    else:
        b = dt.get("b")
    if info.get("cabeza") == "avellanada" and b is not None:
        b = min(b, largo - (dt["dk"] - dt["d"]) / 2)
    return float(largo) if b is None or b >= largo else float(b)


def propiedades(norma, tamano, largo=None):
    """Texto de solo lectura con las medidas principales (las «Propiedades» del diálogo de Fusion)."""
    dt, info = datos(norma, tamano), _norma(norma)
    partes = [designacion(norma, tamano, largo), info["descripcion"]]
    if "dk" in dt and "k" in dt:
        partes.append(f"cabeza Ø{dt['dk']:g} × {dt['k']:g}")
    elif "dk" in dt:
        partes.append(f"cabeza Ø{dt['dk']:g} a 90°")
    elif "s" in dt and info["familia"] in ("tornillo", "tuerca"):
        partes.append(f"entrecaras {dt['s']:g}" + (f" × {dt['k']:g}" if "k" in dt else f" × {dt['m']:g}"))
    if "t" in dt:
        partes.append(f"allen {dt['s']:g}")
    if "ph" in dt:
        partes.append(f"Phillips PH{dt['ph']}")
    if "d1" in dt:
        partes.append(f"Ø{dt['d1']:g} / Ø{dt['d2']:g} × {dt['h']:g}")
    if info["familia"] != "arandela":
        partes.append(f"rosca {dt['rosca']}")
    if largo is not None and info["familia"] == "tornillo":
        partes.append(f"largo roscado {largo_roscado(norma, tamano, largo):g}")
    return " · ".join(partes)


# ---------------------------------------------------------------- construcción de la geometría
def _p(r, z):
    return gp_Pnt(float(r), 0.0, float(z))


def _revolucion(puntos):
    """Sólido de revolución alrededor de Z de un perfil (r, z) cerrado. Un elemento ("arco", medio, fin)
    agrega un arco por tres puntos desde el punto anterior."""
    mk = BRepBuilderAPI_MakeWire()
    actual = puntos[0]
    for item in list(puntos[1:]) + [puntos[0]]:
        if isinstance(item[0], str):
            _, medio, fin = item
            arco = GC_MakeArcOfCircle(_p(*actual), _p(*medio), _p(*fin)).Value()
            mk.Add(BRepBuilderAPI_MakeEdge(arco).Edge())
            actual = fin
        elif math.dist(actual, item) > 1e-9:
            mk.Add(BRepBuilderAPI_MakeEdge(_p(*actual), _p(*item)).Edge())
            actual = item
    cara = BRepBuilderAPI_MakeFace(mk.Wire(), True).Face()
    return BRepPrimAPI_MakeRevol(cara, gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 2 * math.pi).Shape()


def _hexagono(s, z0, alto):
    """Prisma hexagonal de entrecaras `s` (caras planas perpendiculares a X) entre z0 y z0 + alto."""
    R = s / math.sqrt(3)
    mk = BRepBuilderAPI_MakePolygon()
    for i in range(6):
        a = math.radians(30 + 60 * i)
        mk.Add(gp_Pnt(R * math.cos(a), R * math.sin(a), float(z0)))
    mk.Close()
    cara = BRepBuilderAPI_MakeFace(mk.Wire(), True).Face()
    return BRepPrimAPI_MakePrism(cara, gp_Vec(0, 0, float(alto))).Shape()


def _caja(x0, y0, z0, dx, dy, dz):
    return geo.caja(dx, dy, dz, (x0, y0, z0))


def _unificar(forma):
    try:
        u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
        u.Build()
        return u.Shape()
    except Exception:  # noqa: BLE001 — si no se puede simplificar, se devuelve tal cual
        return forma


def _hex_achaflanado(s, z0, alto, abajo=True, arriba=True):
    """Hexágono de tuerca o cabeza con el chaflán de 30° en las esquinas (círculo de apoyo de 0,95·s)."""
    e2, rt = s / math.sqrt(3), 0.95 * s / 2
    rb = e2 + 0.5
    dz = (rb - rt) * math.tan(math.radians(30))
    perfil = [(0, z0), (rt if abajo else rb, z0)]
    if abajo:
        perfil.append((rb, z0 + dz))
    if arriba:
        perfil += [(rb, z0 + alto - dz), (rt, z0 + alto)]
    else:
        perfil.append((rb, z0 + alto))
    perfil.append((0, z0 + alto))
    return geo.booleano(_hexagono(s, z0, alto), _revolucion(perfil), "intersecar")


def _allen(s, t, z_tope):
    """Cavidad hexagonal (llave allen `s`, profundidad `t` desde z_tope hacia −Z) con el fondo cónico de 118°
    de la broca (Ø 0,98·s, apenas dentro del hexágono para que la unión no quede tangente)."""
    rb = 0.98 * s / 2
    z_fondo = z_tope - t
    cono = _revolucion([(0, z_fondo - rb / math.tan(math.radians(59))), (rb, z_fondo), (rb, z_fondo + 0.2 * t),
                        (0, z_fondo + 0.2 * t)])
    return geo.booleano(_hexagono(s, z_fondo, t + 1.0), cono, "unir")


def _phillips(m, q, z_tope):
    """Cruz Phillips simplificada: dos ranuras de largo m, ancho 0,22·m y profundidad q."""
    w = 0.22 * m
    a = _caja(-m / 2, -w / 2, z_tope - q, m, w, q + 1.0)
    b = _caja(-w / 2, -m / 2, z_tope - q, w, m, q + 1.0)
    return geo.booleano(a, b, "unir")


def _chaflan_punta(dt):
    """Alto del chaflán de 45° de la punta (llega al diámetro del núcleo de la rosca exterior)."""
    return 0.61343 * dt["paso"]


def _tornillo(norma, dt, L):
    """Tornillo canónico (sin rosca: el vástago al diámetro nominal)."""
    d, c = dt["d"], _chaflan_punta(dt)
    r = d / 2
    cabeza = NORMAS[norma]["cabeza"]
    punta = [(r, -L + c), (r - c, -L), (0, -L)]
    if cabeza == "cilindrica":
        solido = _revolucion([(0, dt["k"]), (dt["dk"] / 2, dt["k"]), (dt["dk"] / 2, 0), (r, 0)] + punta)
        return geo.booleano(solido, _allen(dt["s"], dt["t"], dt["k"]), "cortar")
    if cabeza == "abotonada":
        rk, k = dt["dk"] / 2, dt["k"]
        R = (rk * rk + k * k) / (2 * k)
        a = math.atan2(rk, R - k) / 2           # punto medio del arco (ángulo desde el eje, centro en z = k − R)
        medio = (R * math.sin(a), k - R + R * math.cos(a))
        solido = _revolucion([(0, k), ("arco", medio, (rk, 0)), (r, 0)] + punta)
        return geo.booleano(solido, _allen(dt["s"], dt["t"], k), "cortar")
    if cabeza == "alomada":
        rk, k = dt["dk"] / 2, dt["k"]
        k1 = 0.55 * k                           # flanco recto y casquete esférico arriba
        hc = k - k1
        R = (rk * rk + hc * hc) / (2 * hc)
        a = math.atan2(rk, R - hc) / 2
        medio = (R * math.sin(a), k - R + R * math.cos(a))
        solido = _revolucion([(0, k), ("arco", medio, (rk, k1)), (rk, 0), (r, 0)] + punta)
        return geo.booleano(solido, _phillips(dt["m"], 0.55 * k, k), "cortar")
    if cabeza == "avellanada":
        kc = (dt["dk"] - d) / 2                 # cono de 90°: del diámetro de cabeza al nominal
        if L <= kc + c:
            raise geo.ErrorGeometria("El largo no alcanza para la cabeza avellanada.")
        solido = _revolucion([(0, 0), (dt["dk"] / 2, 0), (r, -kc)] + punta)
        return geo.booleano(solido, _allen(dt["s"], dt["t"], 0.0), "cortar")
    if cabeza == "hexagonal":
        vastago = _revolucion([(0, 0.0), (r, 0.0)] + punta)
        hexa = _hex_achaflanado(dt["s"], 0.0, dt["k"], abajo=False)
        return _unificar(geo.booleano(vastago, hexa, "unir"))
    raise geo.ErrorGeometria(f"Cabeza desconocida: {cabeza}")


def _tuerca(norma, dt):
    m, rh = dt["m"], dt["diametro_menor"] / 2
    if norma == "ISO 10511":
        h_hex = 0.65 * m                         # cuerpo hexagonal + collar del inserto (simplificado)
        rc = 0.95 * dt["s"] / 2
        ch = 0.15 * (m - h_hex)
        collar = _revolucion([(0, h_hex - 0.01), (rc, h_hex - 0.01), (rc, m - ch), (rc - ch, m), (0, m)])
        cuerpo = geo.booleano(_hex_achaflanado(dt["s"], 0.0, h_hex, arriba=False), collar, "unir")
    else:
        cuerpo = _hex_achaflanado(dt["s"], 0.0, m)
    agujero = geo.cilindro(rh, m + 2.0, base=(0, 0, -1.0))
    return _unificar(geo.booleano(cuerpo, agujero, "cortar"))


def _arandela(norma, dt):
    r1, r2, h = dt["d1"] / 2, dt["d2"] / 2, dt["h"]
    if NORMAS[norma].get("chaflan"):
        c = h / 4                                # chaflán exterior a 30° (ISO 7090, de h/4 a h/2)
        return _revolucion([(r1, 0), (r2, 0), (r2, h - c), (r2 - c / math.tan(math.radians(30)), h), (r1, h)])
    return _revolucion([(r1, 0), (r2, 0), (r2, h), (r1, h)])


def _varilla(dt, L):
    r, c = dt["d"] / 2, _chaflan_punta(dt)
    if L <= 2 * c:
        raise geo.ErrorGeometria("La varilla es demasiado corta.")
    return _revolucion([(0, 0), (r - c, 0), (r, -c), (r, -L + c), (r - c, -L), (0, -L)])


def _esparrago(dt, L):
    r, c = dt["d"] / 2, _chaflan_punta(dt)
    cp = r - dt["dp"] / 2                        # punta plana con chaflán de 45° hasta dp
    if L <= c + cp + dt["t"] * 0.5:
        raise geo.ErrorGeometria("El espárrago es demasiado corto.")
    solido = _revolucion([(0, 0), (r - c, 0), (r, -c), (r, -L + cp), (dt["dp"] / 2, -L), (0, -L)])
    return geo.booleano(solido, _allen(dt["s"], dt["t"], 0.0), "cortar")


def _por_mm(dt, interna):
    """Volumen que saca el surco básico por mm de rosca: área del hueco entre filetes dentro del material
    (trapecio de alto 5H/8) por la vuelta en su baricentro, dividido el paso."""
    P, D = dt["paso"], dt["d"]
    prof = 5 / 8 * math.sqrt(3) / 2 * P
    if interna:      # anchos P/8 en el diámetro mayor y 3P/4 en el menor
        area, r_c = 0.4375 * P * prof, D / 2 - prof + prof * (0.75 + 0.25) / (3 * 0.875)
    else:            # anchos P/4 en el núcleo y 7P/8 en el diámetro mayor
        area, r_c = 0.5625 * P * prof, D / 2 - prof + prof * (0.25 + 1.75) / (3 * 1.125)
    return area * 2 * math.pi * r_c / P


def _cortar(forma, herramienta, difuso=0.0):
    """Corte booleano de un intento (sin reintentos: si falla se prueba otra variante del surco)."""
    op = BRepAlgoAPI_Cut()
    args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(forma)
    herr.Append(herramienta)
    op.SetArguments(args)
    op.SetTools(herr)
    if difuso:
        op.SetFuzzyValue(difuso)
    op.Build()
    if not op.IsDone() or not geo.es_valida(op.Shape()) or len(geo.solidos(op.Shape())) != 1:
        return None
    return op.Shape()


def _filete(forma, dt, z_material, z_fin, largo_material, interna=False):
    """Corta la rosca modelada (perfil básico ISO de 60°, mano derecha) desde z_material (inicio del material,
    la hélice arranca uno o dos pasos antes) hasta z_fin del eje Z.

    El surco se barre por una hélice que solo cubre ese tramo y termina "en fuga" (sin recortarlo con un
    plano): el recorte plano de `solidos_crear.rosca` deja caras coplanares que en algunos largos hacen
    fallar la booleana. Aun así, la booleana con hélices a veces corta de menos o deja un hueco de más sin
    avisar: se compara lo que sacó con lo que debe sacar en `largo_material` mm de rosca y, si no da, se
    prueba otra variante (arranque más abajo, otro ángulo)."""
    P, D = dt["paso"], dt["d"]
    prof = 5 / 8 * math.sqrt(3) / 2 * P               # 5H/8: alto del filete básico
    pend, extra = 2 * math.tan(math.radians(30)), 0.1 * P
    if interna:
        r_out, w_out = D / 2, P / 8
        r_in, w_in = D / 2 - prof - extra, 3 * P / 4 + pend * extra
    else:
        r_in, w_in = D / 2 - prof, P / 4
        r_out, w_out = D / 2 + extra, 7 * P / 8 + pend * extra
    if (z_fin - z_material) / P > 300:
        raise geo.ErrorGeometria("Demasiadas vueltas para una rosca modelada: usá la rosca cosmética.")
    w = max(w_in, w_out)
    esperado = _por_mm(dt, interna) * largo_material
    v0 = geo.volumen(forma)
    z = np.array([0.0, 0.0, 1.0])
    variantes = [(k, d, dif) for dif in (0.0, 1e-5) for k in (1, 2) for d in (0.0, 25.0, -25.0)]
    for antes, delta, difuso in variantes:
        z_ini = z_material - antes * P
        altura = (z_fin - z_ini) - w
        if altura <= P / 4:
            raise geo.ErrorGeometria("El tramo roscado es demasiado corto para modelar la rosca.")
        # Las caras de revolución tienen la costura en el ángulo 0 (+X): el arranque se gira para que las dos
        # puntas del surco queden lo más lejos posible de ella.
        giro = (altura / P % 1.0) * 360.0
        a = math.radians((-(360.0 + giro) / 2 if giro <= 180 else -giro / 2) + delta)
        x = np.array([math.cos(a), math.sin(a), 0.0])
        base = np.array([0.0, 0.0, z_ini + w / 2])     # el perfil arranca con su borde inferior en z_ini
        perfil = _poligono([base + x * r_in - z * w_in / 2, base + x * r_out - z * w_out / 2,
                            base + x * r_out + z * w_out / 2, base + x * r_in + z * w_in / 2])
        try:
            surco = _barrido_helicoidal(perfil, _helice(base, z, x, (r_in + r_out) / 2, P, altura))
            if interna:                              # sin la parte que cae en el agujero (como en `rosca`)
                hueco = geo.cilindro(dt["diametro_menor"] / 2, z_fin - z_ini + 2, base=(0, 0, z_ini - 1))
                surco = geo.booleano(surco, hueco, "cortar")
        except geo.ErrorGeometria:
            continue
        res = _cortar(forma, surco, difuso)
        if res is not None and abs((v0 - geo.volumen(res)) / esperado - 1) < 0.025:
            return res
    raise geo.ErrorGeometria("El kernel no pudo modelar esta rosca: usá la rosca cosmética.")


def generar(familia, norma, tamano, largo=None, *, rosca="cosmetica"):
    """Sólido de la fijación en la posición canónica (ver el docstring del módulo).

    `familia`: "tornillo" | "tuerca" | "arandela" | "varilla" | "esparrago"; `norma`: clave de NORMAS
    ("ISO 4762"…); `tamano`: "M6"; `largo`: mm (tornillos, varilla y espárragos); `rosca`: "cosmetica" |
    "modelada"."""
    info = _norma(norma)
    if info["familia"] != familia:
        raise geo.ErrorGeometria(f"{norma} no es de la familia «{FAMILIAS.get(familia, familia)}».")
    if rosca not in TIPOS_ROSCA:
        raise geo.ErrorGeometria(f"Tipo de rosca desconocido: {rosca}")
    dt = datos(norma, tamano)
    if familia in _CON_LARGO:
        if largo is None or float(largo) <= 0:
            raise geo.ErrorGeometria("El largo de la fijación debe ser positivo.")
        L = float(largo)
    P = dt["paso"]
    c = _chaflan_punta(dt)
    if familia == "tornillo":
        forma = _tornillo(norma, dt, L)
        if rosca == "modelada":
            tope = (dt["dk"] - dt["d"]) / 2 if info["cabeza"] == "avellanada" else 0.0
            arriba = min(-L + largo_roscado(norma, tamano, L), -tope - P / 2)   # salida de rosca bajo la cabeza
            w = 7 * P / 8 + 0.2 * P * math.tan(math.radians(30))
            forma = _filete(forma, dt, -L, arriba, arriba - w / 2 + L - c / 2)
    elif familia == "tuerca":
        forma = _tuerca(norma, dt)
        if rosca == "modelada":
            forma = _filete(forma, dt, 0.0, dt["m"] + P, dt["m"], interna=True)
    elif familia == "arandela":
        forma = _arandela(norma, dt)
    elif familia == "varilla":
        forma = _varilla(dt, L)
        if rosca == "modelada":
            forma = _filete(forma, dt, -L, P, L - c)
    else:
        forma = _esparrago(dt, L)
        if rosca == "modelada":
            forma = _filete(forma, dt, -L, P, L - c / 2 - (dt["d"] - dt["dp"]) / 4)
    sols = geo.solidos(forma)
    if len(sols) != 1 or not geo.es_valida(sols[0]):
        raise geo.ErrorGeometria(f"No se pudo construir {designacion(norma, tamano, largo)}.")
    return sols[0]


# ---------------------------------------------------------------- colocación
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria("La dirección de la fijación no puede ser nula.")
    return v / n


def _perpendicular(n):
    aux = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    return _unit(np.cross(n, aux))


def matriz_colocacion(punto, direccion):
    """Matriz 4x4 que lleva el marco canónico (origen, +Z) al punto de apoyo con +Z = `direccion`."""
    z = _unit(direccion)
    x = _perpendicular(z)
    y = np.cross(z, x)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, np.asarray(punto, float)
    return m


def colocar(forma, punto, direccion):
    return geo.transformar(forma, matriz_colocacion(punto, direccion))


def _dentro(cuerpo, punto):
    c = BRepClass3d_SolidClassifier(cuerpo, gp_Pnt(*map(float, punto)), 1e-7)
    return c.State() == TopAbs_IN


def _muestras(centro, n, radio, desplazamiento, k=8):
    u = _perpendicular(n)
    v = np.cross(n, u)
    return [centro + n * desplazamiento + radio * (math.cos(a) * u + math.sin(a) * v)
            for a in np.linspace(0, 2 * math.pi, k, endpoint=False)]


def _delta(radio):
    return max(min(0.1 * radio, 0.25), 0.01)


def _material(cuerpo, centro, n, radio, desplazamiento):
    """(puntos dentro del material por fuera del radio, por dentro del radio) a `desplazamiento` sobre n."""
    dlt = _delta(radio)
    fuera = sum(_dentro(cuerpo, p) for p in _muestras(centro, n, radio + dlt, desplazamiento))
    adentro = sum(_dentro(cuerpo, p) for p in _muestras(centro, n, max(radio - dlt, radio * 0.5), desplazamiento))
    return fuera, adentro


def apoyo_arista(cuerpo, arista):
    """Apoyo de una fijación en una arista circular: {"punto": centro, "direccion": eje saliendo del material,
    "diametro", "interior": True si es un agujero (material por fuera del círculo)}."""
    curva = BRepAdaptor_Curve(TopoDS.Edge(arista))
    if curva.GetType() != GeomAbs_Circle:
        raise geo.ErrorGeometria("La fijación se coloca en una arista circular.")
    circ = curva.Circle()
    loc, ax = circ.Location(), circ.Axis().Direction()
    centro, n, r = np.array([loc.X(), loc.Y(), loc.Z()]), np.array([ax.X(), ax.Y(), ax.Z()]), circ.Radius()
    dlt = _delta(r)
    arriba, abajo = _material(cuerpo, centro, n, r, dlt), _material(cuerpo, centro, n, r, -dlt)
    if sum(arriba) > sum(abajo):                 # el material está del lado +n: la fijación sale por −n
        n, lado = -n, arriba
    else:
        lado = abajo
    return {"punto": centro, "direccion": n, "diametro": 2 * r, "interior": lado[0] >= lado[1]}


def _extremos_cara(cara, o, z):
    """[(altura sobre el eje, radio)] de los puntos de las aristas de una cara de revolución."""
    pts = []
    for e in rf.subformas(cara, "arista"):
        c = BRepAdaptor_Curve(e)
        a, b = c.FirstParameter(), c.LastParameter()
        for k in range(9):
            p = c.Value(a + (b - a) * k / 8)
            q = np.array([p.X(), p.Y(), p.Z()]) - o
            h = float(q @ z)
            pts.append((h, float(np.linalg.norm(q - z * h))))
    return pts


def apoyo_cara(cuerpo, cara, otro_extremo=False):
    """Apoyo en una cara cilíndrica o cónica: el extremo abierto de la cara (la boca del agujero; en un
    avellanado, el lado ancho). `otro_extremo` usa el extremo opuesto (Voltear)."""
    sup = BRepAdaptor_Surface(TopoDS.Face(cara))
    if sup.GetType() == GeomAbs_Cylinder:
        eje = sup.Cylinder().Axis()
    elif sup.GetType() == GeomAbs_Cone:
        eje = sup.Cone().Axis()
    else:
        raise geo.ErrorGeometria("La fijación se coloca en una cara cilíndrica o cónica.")
    lo, di = eje.Location(), eje.Direction()
    o, z = np.array([lo.X(), lo.Y(), lo.Z()]), np.array([di.X(), di.Y(), di.Z()])
    pts = _extremos_cara(cara, o, z)
    hmin, hmax = min(p[0] for p in pts), max(p[0] for p in pts)
    tol = max(1e-6, 1e-4 * (hmax - hmin))
    extremos = []
    for h, s in ((hmax, 1.0), (hmin, -1.0)):
        r = float(np.mean([p[1] for p in pts if abs(p[0] - h) <= tol]))
        centro = o + z * h
        dlt = _delta(r)
        mas_alla = _material(cuerpo, centro, z * s, r, dlt)
        antes = _material(cuerpo, centro, z * s, r, -dlt)
        extremos.append({"punto": centro, "direccion": z * s, "diametro": 2 * r, "interior": antes[0] >= antes[1],
                         "abierto": sum(mas_alla) < 8, "radio": r})
    if sup.GetType() == GeomAbs_Cone:
        orden = sorted(extremos, key=lambda e: -e["radio"])          # avellanado: primero el lado ancho
    else:
        orden = sorted(extremos, key=lambda e: not e["abierto"])     # primero la boca abierta (estable: arriba)
    elegido = orden[1] if otro_extremo else orden[0]
    return {k: elegido[k] for k in ("punto", "direccion", "diametro", "interior")}


def aristas_similares(cuerpo, arista, tol=1e-4):
    """Aristas circulares del cuerpo iguales a `arista` (mismo radio, eje paralelo y en el mismo plano):
    «Seleccionar similares» de Fusion, para poner una fijación en cada agujero de un patrón."""
    c0 = BRepAdaptor_Curve(TopoDS.Edge(arista))
    if c0.GetType() != GeomAbs_Circle:
        return [arista]
    ci = c0.Circle()
    r0 = ci.Radius()
    p0 = np.array([ci.Location().X(), ci.Location().Y(), ci.Location().Z()])
    d = ci.Axis().Direction()
    n0 = np.array([d.X(), d.Y(), d.Z()])
    salida, centros = [], []
    for e in rf.subformas(cuerpo, "arista"):
        c = BRepAdaptor_Curve(e)
        if c.GetType() != GeomAbs_Circle:
            continue
        cc = c.Circle()
        if abs(cc.Radius() - r0) > tol:
            continue
        dd = cc.Axis().Direction()
        if abs(abs(dd.X() * n0[0] + dd.Y() * n0[1] + dd.Z() * n0[2]) - 1) > 1e-6:
            continue
        p = np.array([cc.Location().X(), cc.Location().Y(), cc.Location().Z()])
        if abs(float((p - p0) @ n0)) > tol or any(np.linalg.norm(p - q) < tol for q in centros):
            continue
        centros.append(p)
        salida.append(e)
    return salida or [arista]


def espesor_material(cuerpo, punto, direccion, radio=0.0):
    """Espesor de material que atraviesa la fijación desde el apoyo hacia −`direccion`, medido sobre una
    recta paralela al eje justo por fuera del agujero (None si ahí no hay material)."""
    z = _unit(direccion)
    q = np.asarray(punto, float) + _perpendicular(z) * (radio + _delta(max(radio, 1.0))) + z * 1e-3
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(cuerpo, 1e-7)
    inter.Perform(gp_Lin(gp_Pnt(*map(float, q)), gp_Dir(*map(float, -z))), 0.0, 1e5)
    if not inter.IsDone():
        return None
    ws = []
    for w in sorted(inter.WParameter(i) for i in range(1, inter.NbPnt() + 1)):
        if not ws or w - ws[-1] > 1e-6:          # el rayo que pasa por una arista la cuenta dos veces
            ws.append(w)
    if len(ws) < 2 or ws[0] > 2e-3 + 1e-6 or not _dentro(cuerpo, q - z * (ws[0] + ws[1]) / 2):
        return None
    return float(ws[1] - 1e-3)
