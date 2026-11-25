"""Sólidos › Crear: roscas."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
from . import revision as rv
from . import tablas_rosca
import itertools
import functools
import re
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import _aristas_de, _caras_de, _gdir, _perpendicular, _pnt, _poligono, _unit, _xyz
from .solidos_crear_repujado import _normal_orientada
from .solidos_crear_patrones import aplicar

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Curve, BRepAdaptor_Surface, BRepAlgoAPI_Cut, BRepAlgoAPI_Splitter, BRepBuilderAPI_Copy,
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire, BRepBuilderAPI_Sewing, BRepLib,
        BRepOffsetAPI_MakePipeShell, BRep_Tool, Geom2d_Line, GeomAPI_Interpolate, GeomAbs_BSplineSurface,
        GeomAbs_Cylinder, Geom_ConicalSurface, Geom_CylindricalSurface, HArray1_gp_Pnt, List_TopoDS_Shape,
        TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_SHELL, TopAbs_VERTEX, TopExp, TopExp_Explorer,
        TopLoc_Location, TopoDS, gp_Ax1, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Dir2d, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf,
        gp_Vec,
    )


# ================================================================ 8. roscas
# Familias de rosca (el «Tipo» del diálogo de Fusion, en su orden): nombre, norma de la que salen los datos, ángulo entre
# flancos del perfil (grados), si es cónica (las de tubería cónicas no se modelan: Roscado cónico cosmético) y si es solo
# exterior (no se ofrece en una cara interior). Las que vienen de `tablas_rosca` se suman en `_ordenar_familias`.
FAMILIAS_ROSCA = {
    "iso_metrica": {"nombre": "Perfil métrico ISO", "norma": "ISO 261 / ISO 262 / ISO 724 (perfil ISO 68-1)",
                    "angulo": 60.0, "conica": False},
    "unificada": {"nombre": "Roscas de tornillo unificadas ANSI", "norma": "ASME B1.1", "angulo": 60.0, "conica": False},
    "trapezoidal": {"nombre": "Roscas trapezoidales métricas ISO", "norma": "ISO 2904 / ISO 2902", "angulo": 30.0,
                    "conica": False},
    "acme": {"nombre": "Roscas de tornillo ACME", "norma": "ASME B1.5", "angulo": 29.0, "conica": False},
    "bsp_paralela": {"nombre": "Roscas de tubería BSP", "norma": "ISO 228-1", "angulo": 55.0, "conica": False},
    "bsp_conica": {"nombre": "BSP", "norma": "ISO 7-1", "angulo": 55.0, "conica": True},
    "npt": {"nombre": "NPT", "norma": "ASME B1.20.1", "angulo": 60.0, "conica": True},
}
_ORDEN_FAMILIAS = ("ansi_metrica", "gb_metrica", "iso_metrica", "gost_autorroscante", "din_madera", "pulgadas_autorroscante",
                   "pulgadas_plasticos", "metrica_plasticos", "acme", "unificada", "bsp_paralela", "din_tuberia", "gb_tuberia",
                   "iso_tuberia", "jis_tuberia", "metrica_formado", "trapezoidal", "afbma",
                   "bsp_conica", "din_conica", "iso_conica", "jis_conica", "npt", "npt_pvc")


def _ordenar_familias():
    """Suma las familias de `tablas_rosca` y deja el orden del desplegable de Fusion."""
    todas = FAMILIAS_ROSCA | tablas_rosca.FAMILIAS
    FAMILIAS_ROSCA.clear()
    FAMILIAS_ROSCA.update({k: todas[k] for k in _ORDEN_FAMILIAS})


_ordenar_familias()

# Métrica ISO (ISO 261 / ISO 724, perfil básico de 60°) y unificada UNC/UNF (ASME B1.1). Broca para roscar:
# en métrica D − P redondeado como en las tablas de taller; en UN, la broca de número/letra/fracción usual.
_ISO_GRUESA = [(1.6, 0.35, 1.25), (2, 0.4, 1.6), (2.5, 0.45, 2.05), (3, 0.5, 2.5), (3.5, 0.6, 2.9), (4, 0.7, 3.3),
               (5, 0.8, 4.2), (6, 1.0, 5.0), (8, 1.25, 6.8), (10, 1.5, 8.5), (12, 1.75, 10.2), (14, 2.0, 12.0),
               (16, 2.0, 14.0), (18, 2.5, 15.5), (20, 2.5, 17.5), (22, 2.5, 19.5), (24, 3.0, 21.0), (27, 3.0, 24.0),
               (30, 3.5, 26.5), (33, 3.5, 29.5), (36, 4.0, 32.0), (39, 4.0, 35.0), (42, 4.5, 37.5), (45, 4.5, 40.5),
               (48, 5.0, 43.0), (52, 5.0, 47.0), (56, 5.5, 50.5), (60, 5.5, 54.5), (64, 6.0, 58.0)]
_ISO_FINA = [(1.6, 0.2), (2, 0.25), (2.5, 0.35), (3, 0.35), (4, 0.5), (5, 0.5), (6, 0.75), (8, 1.0), (10, 1.25),
             (10, 1.0), (12, 1.5), (12, 1.25), (14, 1.5), (16, 1.5), (18, 2.0), (18, 1.5), (20, 2.0), (20, 1.5),
             (22, 2.0), (22, 1.5), (24, 2.0), (27, 2.0), (30, 2.0), (33, 2.0), (36, 3.0), (39, 3.0), (42, 3.0),
             (45, 3.0), (48, 3.0), (52, 4.0), (56, 4.0), (60, 4.0), (64, 4.0)]
# Unificada (ASME B1.1): (tamaño, diámetro nominal en pulgadas, hilos por pulgada, broca para roscar en pulgadas).
# Los números (#0 a #12) valen 0.060 + 0.013·N pulgadas.
_UNC = [("#1", 0.073, 64, 0.0595), ("#2", 0.086, 56, 0.0700), ("#3", 0.099, 48, 0.0785),
        ("#4", 0.112, 40, 0.0890), ("#5", 0.125, 40, 0.1015), ("#6", 0.138, 32, 0.1065), ("#8", 0.164, 32, 0.1360),
        ("#10", 0.190, 24, 0.1495), ("#12", 0.216, 24, 0.1770),
        ("1/4", 0.250, 20, 0.2010), ("5/16", 0.3125, 18, 0.2570), ("3/8", 0.375, 16, 0.3125),
        ("7/16", 0.4375, 14, 0.3680), ("1/2", 0.500, 13, 0.4219), ("9/16", 0.5625, 12, 0.4844),
        ("5/8", 0.625, 11, 0.5312), ("3/4", 0.750, 10, 0.6562), ("7/8", 0.875, 9, 0.7656), ("1", 1.000, 8, 0.8750),
        ("1-1/8", 1.125, 7, 0.9844), ("1-1/4", 1.250, 7, 1.1094), ("1-3/8", 1.375, 6, 1.2188),
        ("1-1/2", 1.500, 6, 1.3438)]
_UNF = [("#0", 0.060, 80, 0.0469), ("#1", 0.073, 72, 0.0595), ("#2", 0.086, 64, 0.0700), ("#3", 0.099, 56, 0.0820),
        ("#4", 0.112, 48, 0.0935), ("#5", 0.125, 44, 0.1040), ("#6", 0.138, 40, 0.1130), ("#8", 0.164, 36, 0.1360),
        ("#10", 0.190, 32, 0.1590), ("#12", 0.216, 28, 0.1820),
        ("1/4", 0.250, 28, 0.2130), ("5/16", 0.3125, 24, 0.2720), ("3/8", 0.375, 24, 0.3320),
        ("7/16", 0.4375, 20, 0.3906), ("1/2", 0.500, 20, 0.4531), ("9/16", 0.5625, 18, 0.5156),
        ("5/8", 0.625, 18, 0.5781), ("3/4", 0.750, 16, 0.6875), ("7/8", 0.875, 14, 0.8125), ("1", 1.000, 12, 0.9219),
        ("1-1/8", 1.125, 12, 1.0469), ("1-1/4", 1.250, 12, 1.1719), ("1-3/8", 1.375, 12, 1.2969),
        ("1-1/2", 1.500, 12, 1.4219)]
# Trapezoidal métrica, perfil ISO 2904 (30°), serie de pasos media de ISO 2902 en los diámetros de primera
# elección: (diámetro nominal, paso) en mm.
_TRAPEZOIDAL = [(8, 1.5), (10, 2), (12, 3), (14, 3), (16, 4), (18, 4), (20, 4), (22, 5), (24, 5), (26, 5), (28, 5),
                (30, 6), (32, 6), (36, 6), (40, 7), (44, 7), (48, 8), (50, 8), (52, 8), (60, 9), (70, 10), (80, 10),
                (90, 12), (100, 12)]
# ACME de uso general (ASME B1.5, 29°), combinaciones recomendadas: (tamaño, diámetro en pulgadas, hilos/pulgada).
_ACME = [("1/4", 0.25, 16), ("5/16", 0.3125, 14), ("3/8", 0.375, 12), ("7/16", 0.4375, 12), ("1/2", 0.5, 10),
         ("5/8", 0.625, 8), ("3/4", 0.75, 6), ("7/8", 0.875, 6), ("1", 1.0, 5), ("1-1/8", 1.125, 5), ("1-1/4", 1.25, 5),
         ("1-3/8", 1.375, 4), ("1-1/2", 1.5, 4), ("1-3/4", 1.75, 4), ("2", 2.0, 4), ("2-1/4", 2.25, 3),
         ("2-1/2", 2.5, 3), ("2-3/4", 2.75, 3), ("3", 3.0, 2), ("3-1/2", 3.5, 2), ("4", 4.0, 2), ("4-1/2", 4.5, 2),
         ("5", 5.0, 2)]
# Tubería BSP (perfil Whitworth de 55°): (tamaño, hilos por pulgada, diámetro mayor en mm). Paralela G: ISO 228-1.
# La cónica R/Rc (ISO 7-1) tiene el mismo diámetro en el plano de calibre y solo los tamaños de _BSP_CONICA.
_BSP = [("1/16", 28, 7.723), ("1/8", 28, 9.728), ("1/4", 19, 13.157), ("3/8", 19, 16.662), ("1/2", 14, 20.955),
        ("5/8", 14, 22.911), ("3/4", 14, 26.441), ("7/8", 14, 30.201), ("1", 11, 33.249), ("1-1/8", 11, 37.897),
        ("1-1/4", 11, 41.910), ("1-1/2", 11, 47.803), ("1-3/4", 11, 53.746), ("2", 11, 59.614), ("2-1/4", 11, 65.710),
        ("2-1/2", 11, 75.184), ("2-3/4", 11, 81.534), ("3", 11, 87.884), ("3-1/2", 11, 100.330), ("4", 11, 113.030)]
_BSP_CONICA = ("1/16", "1/8", "1/4", "3/8", "1/2", "3/4", "1", "1-1/4", "1-1/2", "2", "2-1/2", "3", "4")
# NPT (ASME B1.20.1, 60°, conicidad 1:16): (tamaño, diámetro exterior del tubo D en pulgadas, hilos por pulgada,
# enganche a mano L1 en pulgadas). Flancos en el extremo chico E0 = D − (0.05·D + 1.1)·p; en el plano de calibre
# (la boca de la rosca interior) E1 = E0 + L1/16. Alto del filete h = 0,8·p.
_NPT = [("1/16", 0.3125, 27, 0.160), ("1/8", 0.405, 27, 0.180), ("1/4", 0.540, 18, 0.200), ("3/8", 0.675, 18, 0.240),
        ("1/2", 0.840, 14, 0.320), ("3/4", 1.050, 14, 0.339), ("1", 1.315, 11.5, 0.400), ("1-1/4", 1.660, 11.5, 0.420),
        ("1-1/2", 1.900, 11.5, 0.420), ("2", 2.375, 11.5, 0.436)]
_WHITWORTH_H = 0.960491     # altura del triángulo fundamental de 55° por mm de paso; filete = 2/3 de eso


def _fila(familia, norma, tamano, d, p, broca, d2, d1, conicidad=0.0):
    return {"norma": norma, "familia": familia, "tamano": tamano, "diametro": d, "paso": p, "broca": broca,
            "diametro_flancos": d2, "diametro_menor": d1, "angulo": FAMILIAS_ROSCA[familia]["angulo"],
            "conica": FAMILIAS_ROSCA[familia]["conica"], "conicidad": conicidad,
            "solo_exterior": bool(FAMILIAS_ROSCA[familia].get("solo_exterior"))}


_SUMADAS = set()                                        # designaciones que vienen de `tablas_rosca`


def _armar_tabla():
    tabla = {}
    h60 = math.sqrt(3) / 2
    for d, p, b in _ISO_GRUESA:
        tabla[f"M{d:g}x{p:g}"] = _fila("iso_metrica", "ISO métrica gruesa", f"M{d:g}", float(d), p, b,
                                       d - 2 * (3 / 8) * h60 * p, d - 2 * (5 / 8) * h60 * p)
    for d, p in _ISO_FINA:
        tabla[f"M{d:g}x{p:g}"] = _fila("iso_metrica", "ISO métrica fina", f"M{d:g}", float(d), p, round(d - p, 2),
                                       d - 2 * (3 / 8) * h60 * p, d - 2 * (5 / 8) * h60 * p)
    for serie, filas in (("UNC", _UNC), ("UNF", _UNF)):
        for t, d, tpi, b in filas:
            D, P = round(d * 25.4, 4), 25.4 / tpi
            tabla[f"{t}-{tpi} {serie}"] = _fila("unificada", f"Unificada {serie}", t, D, P, round(b * 25.4, 3),
                                               D - 2 * (3 / 8) * h60 * P, D - 2 * (5 / 8) * h60 * P)
    for d, p in _TRAPEZOIDAL:
        tabla[f"Tr{d:g}x{p:g}"] = _fila("trapezoidal", "Trapezoidal ISO 2904", f"Tr{d:g}", float(d), float(p),
                                        float(d - p), d - p / 2, float(d - p))
    for t, d, tpi in _ACME:
        D, P = round(d * 25.4, 4), 25.4 / tpi
        tabla[f"{t}-{tpi} ACME"] = _fila("acme", "ACME ASME B1.5", t, D, P, None, D - P / 2, D - P)
    for t, tpi, D in _BSP:
        P, hw = 25.4 / tpi, 2 / 3 * _WHITWORTH_H * 25.4 / tpi
        tabla[f"G{t}"] = _fila("bsp_paralela", "BSP paralela ISO 228-1", t, D, P, None, D - hw, D - 2 * hw)
    for t, tpi, D in _BSP:
        if t in _BSP_CONICA:
            P, hw = 25.4 / tpi, 2 / 3 * _WHITWORTH_H * 25.4 / tpi
            tabla[f"R{t}"] = _fila("bsp_conica", "BSPT ISO 7-1", t, D, P, None, D - hw, D - 2 * hw, 1 / 16)
    for t, D, tpi, L1 in _NPT:
        p = 1 / tpi
        e1 = (D - (0.05 * D + 1.1) * p + L1 / 16) * 25.4
        P = 25.4 / tpi
        tabla[f"{t}-{tpi:g} NPT"] = _fila("npt", "NPT ASME B1.20.1", t, round(e1 + 0.8 * P, 4), P, None, round(e1, 4),
                                         round(e1 - 0.8 * P, 4), 1 / 16)
    for familia, filas in tablas_rosca.FILAS.items():     # lo que ya estaba arriba no se toca: se suma lo que falta
        for t, nombre, p, d, d2, d1, broca in filas:
            if nombre not in tabla:
                _SUMADAS.add(nombre)
                tabla[nombre] = _fila(familia, FAMILIAS_ROSCA[familia]["norma"], t, d, p, broca, d2, d1,
                                      1 / 16 if FAMILIAS_ROSCA[familia]["conica"] else 0.0)
    return tabla


TABLA_ROSCAS = _armar_tabla()
_GRUESA_POR_D = {f"M{d:g}": f"M{d:g}x{p:g}" for d, p, _b in _ISO_GRUESA}
for _clave, _f in TABLA_ROSCAS.items():               # los tamaños sin serie gruesa (M0.25…): el primer paso de la tabla
    if _f["familia"] == "iso_metrica":
        _GRUESA_POR_D.setdefault(_f["tamano"], _clave)
_POR_TEXTO = {k.lower().replace(" ", ""): k for k in TABLA_ROSCAS}
_POR_FAMILIA = {}                                     # familia → {tamaño: [designaciones]} en el orden de la tabla
for _clave, _f in TABLA_ROSCAS.items():
    _POR_FAMILIA.setdefault(_f["familia"], {}).setdefault(_f["tamano"], []).append(_clave)
_FRACCION = r"(\d+(?:-\d+/\d+|/\d+)?)"           # tamaño en pulgadas: 1, 1/2, 1-1/4


def _primera(prefijo, sufijo=""):
    """Primera clave de la tabla (en su orden: la serie preferida primero) que empieza y termina así."""
    return next((k for k in TABLA_ROSCAS if k.startswith(prefijo) and k.endswith(sufijo)), None)


def _clave_rosca(texto):
    t = texto.strip().replace("×", "x").replace("X", "x")
    clave = _POR_TEXTO.get(t.lower().replace(" ", ""))
    if clave:
        return clave
    m = re.fullmatch(r"[Mm]\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?", t)
    if m:
        d = float(m.group(1))
        return f"M{d:g}x{float(m.group(2)):g}" if m.group(2) else _GRUESA_POR_D.get(f"M{d:g}")
    m = re.fullmatch(r"(#?\d+(?:-\d+/\d+|/\d+)?)\s*-\s*(\d+)\s*(UNC|UNF|unc|unf)?", t)
    if m:
        serie = (m.group(3) or "").upper()
        candidatas = [f"{m.group(1)}-{m.group(2)} {s}" for s in ((serie,) if serie else ("UNC", "UNF"))]
        return next((c for c in candidatas if c in TABLA_ROSCAS), None)
    m = re.fullmatch(r"[Tt][Rr]\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?", t)
    if m:
        d = float(m.group(1))
        return f"Tr{d:g}x{float(m.group(2)):g}" if m.group(2) else _primera(f"Tr{d:g}x")
    m = re.fullmatch(_FRACCION + r"(?:\s*-\s*(\d+))?\s*(?:ACME|acme|Acme)", t)
    if m:
        return f"{m.group(1)}-{m.group(2)} ACME" if m.group(2) else _primera(f"{m.group(1)}-", " ACME")
    m = re.fullmatch(_FRACCION + r"(?:\s*-\s*(\d+(?:\.\d+)?))?\s*(?:NPT|npt)", t)
    if m:
        return f"{m.group(1)}-{float(m.group(2)):g} NPT" if m.group(2) else _primera(f"{m.group(1)}-", " NPT")
    m = re.fullmatch(r"(G|g|R|Rc|RC|rc|r)\s*" + _FRACCION, t)
    if m:
        return f"{'G' if m.group(1) in ('G', 'g') else 'R'}{m.group(2)}"
    return None


def datos_rosca(designacion):
    """Datos de una rosca de TABLA_ROSCAS: 'M6' (gruesa), 'M6x0.75', '1/4-20 UNC', '#10-32 UNF' (sin serie,
    prueba UNC y UNF), 'Tr20x4' (o 'Tr20': serie media), '1/2-10 ACME', 'G1/2', 'R1/2' o 'Rc1/2', '1/2-14 NPT'
    (o '1/2 NPT'). Devuelve la fila con `designacion` canónica, `familia`, `diametro` (mayor), `paso`,
    `diametro_flancos` y `diametro_menor` básicos (interior), `angulo` del perfil y `conica`. En las cónicas los
    diámetros son los del plano de calibre."""
    clave = _clave_rosca(str(designacion or ""))
    if clave is None or clave not in TABLA_ROSCAS:
        raise geo.ErrorGeometria(f"Rosca desconocida: {designacion}")
    return dict(TABLA_ROSCAS[clave], designacion=clave)


def tamanos_rosca(familia):
    """Tamaños nominales de una familia en orden (los del desplegable «Tamaño»)."""
    if familia not in FAMILIAS_ROSCA:
        raise geo.ErrorGeometria(f"Familia de rosca desconocida: {familia}")
    return sorted(_POR_FAMILIA.get(familia, ()), key=lambda t: TABLA_ROSCAS[_POR_FAMILIA[familia][t][0]]["diametro"])


def designaciones_rosca(familia, tamano):
    """Designaciones de un tamaño (las del desplegable «Designación»): la de paso grueso o preferido primero."""
    return list(_POR_FAMILIA.get(familia, {}).get(tamano, ()))


def familia_de(designacion):
    """Familia (clave de FAMILIAS_ROSCA) de una designación."""
    return datos_rosca(designacion)["familia"]


def _desfases_clase(datos, clase, interna):
    """Corrimientos de modelado de la clase (ver tolerancias.desfases_rosca) para una fila de datos_rosca."""
    from . import tolerancias as tol
    clase, _ = tol.resolver_clase(datos["familia"], datos["diametro"], datos["paso"], clase, interna)
    return tol.desfases_rosca(datos["familia"], datos["diametro"], datos["paso"], clase, interna,
                              datos["diametro_flancos"], datos["diametro_menor"])


def _holgura_rosca(holgura):
    holgura = float(holgura)
    if holgura < 0:
        raise geo.ErrorGeometria("⚠ La holgura de impresión 3D no va negativa.")
    return holgura


def diametro_taladro_rosca(designacion, clase="", holgura=0.0):
    """Diámetro del agujero de una rosca interior modelada: el menor básico, al centro de la tolerancia de la
    `clase` (6H: D1 + TD1/2) y agrandado por la `holgura` radial de impresión 3D. M10 sin clase: 8,376 mm."""
    datos = datos_rosca(designacion)
    return datos["diametro_menor"] + 2 * (_desfases_clase(datos, clase, True)["menor"] + _holgura_rosca(holgura))


def _perfil_surco(datos, desfase=0.0, fondo=None, cresta=None):
    """Argumentos de perfil de `_surco_rosca` para una fila de datos_rosca."""
    return {"angulo": datos["angulo"], "diametro_flancos": datos["diametro_flancos"],
            "diametro_menor": datos["diametro_menor"], "desfase": float(desfase), "fondo": fondo, "cresta": cresta}


def _perfil_clase(datos, clase, interna, holgura, tabla):
    """Perfil de `_surco_rosca` con la clase y la holgura de impresión. `tabla` (B-122, Fusion real): las clases de las
    tablas de Fusion modelan sus Ø mayor y menor (Tr12×3 7e: 8,3175 y 11,882; 7H: 9,1575 y 12,5); `False` deja esos
    diámetros como quedaban en las recetas viejas. Sin tabla, la cresta exterior va al centro de tolerancia (B-250)."""
    a, holgura = _desfases_clase(datos, clase, interna), _holgura_rosca(holgura)
    if not interna and a["cresta"] is None and a["limites"] is not None:
        minimo, maximo = a["limites"]["diametro_mayor"]
        a["cresta"] = (minimo + maximo) / 2
    corrido = lambda d: None if d is None or not tabla else d + 2 * (holgura if interna else -holgura)  # noqa: E731
    return _perfil_surco(datos, a["flancos"] + holgura, corrido(a["fondo"]), corrido(a["cresta"]))


def _helice(origen, eje, x, radio, paso, altura, mano="derecha", angulo=0.0):
    """Hélice como recta en el espacio (u, v) de un cilindro (o de un cono, con `angulo` en grados)."""
    if mano not in ("derecha", "izquierda"):
        raise geo.ErrorGeometria(f"Mano desconocida: {mano}")
    ax3 = gp_Ax3(_pnt(origen), _gdir(eje), _gdir(x))
    du = 2 * math.pi * (altura / paso) * (1 if mano == "derecha" else -1)
    if abs(angulo) > 1e-9:
        if abs(angulo) >= 89:
            raise geo.ErrorGeometria("⚠ Ángulo de la bobina: de -89° a 89°.")
        a = math.radians(angulo)
        sup, dv = Geom_ConicalSurface(ax3, a, radio), altura / math.cos(a)
    else:
        sup, dv = Geom_CylindricalSurface(ax3, radio), altura
    arista = BRepBuilderAPI_MakeEdge(Geom2d_Line(gp_Pnt2d(0.0, 0.0), gp_Dir2d(du, dv)), sup,
                                     0.0, math.hypot(du, dv)).Edge()
    BRepLib.BuildCurves3d_s(arista, 1e-6)
    return BRepBuilderAPI_MakeWire(arista).Wire()


def _barrido_helicoidal(perfil, helice):
    ps = BRepOffsetAPI_MakePipeShell(helice)
    ps.SetMode(True)      # Frenet: sobre una hélice es un movimiento helicoidal exacto del perfil
    ps.Add(perfil, False, False)
    ps.Build()
    if not ps.IsDone() or not ps.MakeSolid():
        raise geo.ErrorGeometria("No se pudo barrer la hélice.")
    return ps.Shape()


def _surco_rosca(origen, eje, diametro, paso, z0, largo, interna, mano, radio_cara=None, *, angulo=60.0,
                 diametro_flancos=None, diametro_menor=None, desfase=0.0, partes=False, extra=0.1, fondo=None, cresta=None,
                 tramo_torno=None, trozos=True, solo_trapecio=False):
    """Sólido helicoidal con la forma del hueco entre filetes recortado al tramo [z0, z0 + largo] del eje. Rosca
    exterior: se le resta al cilindro; interior: al cuerpo agujereado. Perfil por defecto: el básico ISO/UN de
    60°; `angulo` (entre flancos), `diametro_flancos` y `diametro_menor` dan el de otras familias (55°, 30°,
    29°). `desfase` (mm, radial) corre los flancos hacia afuera del material: clase de tolerancia y holgura.
    `partes=True` devuelve (surco, torneado o None) por separado: restar primero el torneado (un cilindro o un
    anillo) y después el surco es más rápido que unirlos (M3 con holgura 0,1: 3,6 s → menos de la mitad).
    `extra` (en pasos) es cuánto sobresale el surco del material; ver `_cortar_rosca`. `fondo` y `cresta` (Ø, con la
    holgura incluida) fijan el fondo del surco y la cresta del filete; sin ellos, el fondo sale de `desfase` y la
    cresta queda en la cara. `tramo_torno=(zmin, zmax)` ajusta el diámetro en ese tramo del eje sin alargar el surco.
    `trozos=False`: sin `_en_tramos` (quien va a copiar el surco con otra geometría, como el espejo, no podría reunir
    las caras partidas). `solo_trapecio=True`: (r_in, w_in, r_out, w_out, r_torno, torno) sin barrer (`_rosca_directa`)."""
    z = _unit(eje)
    o = np.asarray(origen, float)
    h60 = math.sqrt(3) / 2
    d2 = diametro - 2 * (3 / 8) * h60 * paso if diametro_flancos is None else float(diametro_flancos)
    d1 = diametro - 2 * (5 / 8) * h60 * paso if diametro_menor is None else float(diametro_menor)
    desfase = float(desfase)
    rel_extra, extra = extra, extra * paso         # el surco sobresale del material para cortar limpio
    if not 0 < angulo < 90 or not d1 < d2 < diametro:
        raise geo.ErrorGeometria("Perfil de rosca inválido.")
    if abs(desfase) >= (diametro - d1) / 4:
        raise geo.ErrorGeometria("La holgura de la rosca es demasiado grande.")
    r_fondo = (diametro / 2 + desfase if interna else d1 / 2 - desfase) if fondo is None else float(fondo) / 2
    if interna:
        if radio_cara is not None and radio_cara >= r_fondo - 1e-6:
            raise geo.ErrorGeometria("⚠ El agujero supera el diámetro de la rosca.")
    else:
        if radio_cara is not None and cresta is None and radio_cara > diametro / 2 + extra - 0.01 * paso:
            raise geo.ErrorGeometria("⚠ El cilindro es más grueso que la rosca.")
        if radio_cara is not None and radio_cara <= r_fondo:
            raise geo.ErrorGeometria("⚠ El cilindro es más fino que la rosca.")
    eje_r = tuple(round(float(c), 12) for c in z)
    iso = (angulo == 60 and desfase == 0 and abs(d2 - (diametro - 2 * (3 / 8) * h60 * paso)) < 1e-9
           and abs(d1 - (diametro - 2 * (5 / 8) * h60 * paso)) < 1e-9 and fondo is None and cresta is None)
    tabla = tuple(None if v is None else round(float(v), 9) for v in (fondo, cresta))
    perfil = (60.0, None, None, 0.0, None, None) if iso else (round(float(angulo), 9), round(d2, 9), round(d1, 9),
                                                              round(desfase, 9), *tabla)
    tramo_torno = None if tramo_torno is None else tuple(round(float(v - z0), 9) for v in tramo_torno)
    if solo_trapecio:     # B-461: el perfil de la varilla de `_rosca_directa` y el torneado ya en su lugar
        *trapecio, r_torno = _trapecio_surco(diametro, paso, interna, radio_cara, *perfil, rel_extra)
        material = radio_cara if radio_cara is not None else d1 / 2 if interna else diametro / 2
        torno = None if r_torno is None else _torno_surco(r_torno, material, interna, extra, paso, largo, tramo_torno,
                                                          z, o + z * z0)
        return (*trapecio, r_torno, torno)
    base = _surco_en_origen(round(float(diametro), 9), round(float(paso), 9), round(float(largo), 9), bool(interna),
                            mano, None if radio_cara is None else round(float(radio_cara), 9), eje_r, *perfil,
                            round(float(rel_extra), 9), tramo_torno, bool(trozos))
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(*map(float, o + z * z0)))
    giro = _fase_rosca(z)
    if giro:
        rot = gp_Trsf()
        rot.SetRotation(gp_Ax1(gp_Pnt(0.0, 0.0, 0.0), _gdir(z)), giro)
        trsf.Multiply(rot)                         # primero gira sobre su eje, después se traslada
    # copias trasladadas: el corte no toca lo guardado en la caché. Comparten la geometría (B-461: así las caras de
    # `_en_tramos` siguen sobre la misma superficie y se unifican después del corte)
    lugar = TopLoc_Location(trsf)
    surco, torno = (None if f is None else BRepBuilderAPI_Copy(f, False).Shape().Moved(lugar) for f in base)
    if partes:
        return surco, torno
    return surco if torno is None else geo.booleano(surco, torno, "unir")


def _fase_rosca(eje):
    """Giro (rad) del surco alrededor de su eje para que su arranque no dependa del sentido del eje de la cara:
    `_perpendicular(−z) = −_perpendicular(z)`, así que con el eje al revés va media vuelta (B-79). Con eso, macho y
    hembra sobre el mismo eje encajan si sus arranques están a un número entero de pasos (el mismo plano, o la otra
    punta de una cara de largo entero). Una fase cualquiera no: la punta del surco puede caer en la costura de la
    cara cilíndrica y el corte falla (M5 y la rosca con holgura de los tests); con 0 o media vuelta queda a 90°."""
    k = next(i for i in (2, 1, 0) if abs(eje[i]) > 1e-9)
    return math.pi if eje[k] < 0 else 0.0


_ANCHO_LIMITE, _ANCHO_TOPE, _ANCHO_TORNO = 0.995, 0.97, 0.93     # anchos del surco en pasos (ver _surco_en_origen)


@functools.lru_cache(maxsize=16)
def _surco_en_origen(diametro, paso, largo, interna, mano, radio_cara, eje, angulo=60.0, d2=None, d1=None,
                     desfase=0.0, fondo=None, cresta=None, rel_extra=0.1, tramo_torno=None, trozos=True):
    """Surco de `_surco_rosca` con el tramo empezando en el origen. Se guarda por (tamaño, largo, eje, mano,
    perfil): roscar varios agujeros iguales arma el barrido helicoidal UNA vez y lo copia trasladado (hallazgo
    L138: M3 en 4 agujeros tardaba 30 s).

    El perfil es un trapecio: a la distancia ρ del eje, el surco exterior mide P/2 + 2·(ρ − d2/2 + desfase)·tan(α/2)
    a lo largo del eje (el interior, lo que ocupa el filete del tornillo, P/2 − 2·(ρ − d2/2 − desfase)·tan(α/2)).
    Si con el desfase el surco llegara a medir un paso (las vueltas se tocarían y el barrido sale inválido), se
    corta a 0,97·P y la cresta que quedaría más fina se tornea (se quita en todo el tramo). `cresta` también tornea:
    la cara queda en el Ø de la tabla aunque el cilindro o el agujero de partida no lo tengan.
    d2 = d1 = None: perfil básico ISO/UN de 60° sin desfase, con las mismas cuentas que antes de las familias (las
    recetas viejas dan exactamente la misma geometría)."""
    z = np.asarray(eje, float)
    x = _perpendicular(z)
    r_in, w_in, r_out, w_out, r_torno = _trapecio_surco(diametro, paso, interna, radio_cara, angulo, d2, d1, desfase,
                                                        fondo, cresta, rel_extra)
    torno = None
    if r_torno is not None:
        material = radio_cara if radio_cara is not None else d1 / 2 if interna else diametro / 2
        torno = _torno_surco(r_torno, material, interna, rel_extra * paso, paso, largo, tramo_torno, z, np.zeros(3))
    # B-371: el barrido largo también sale incompleto en el perfil básico (M20x2.5×100: 57 %); verificado, cae al
    # corte por mitades de `rosca`
    return _barrer_surco(diametro, paso, largo, interna, mano, radio_cara, z, x, r_in, w_in, r_out, w_out, torno,
                         r_torno, verificar=True, trozos=trozos)


def _torno_surco(r_torno, material, interna, extra, paso, largo, tramo_torno, z, origen):
    """Torneado de la cresta de `_surco_en_origen` con el tramo empezando en `origen`: un cilindro (agujero) o un anillo
    (eje) que llega al radio `r_torno`."""
    # el torneado pasa de largo un pelo en las puntas: si terminara justo donde termina el surco, sus caras planas
    # coincidirían con las del surco y el corte del surco falla (pasó con M3 y holgura 0,1). B-249: con 0,02 pasos
    # la franja de cresta de la punta quedaba de 0,016 mm en AFBMA (paso 0,79), con aristas de tolerancia 0,01, y
    # el STEP de ida y vuelta cambiaba el volumen 3·10⁻⁵; con 0,1 pasos, 3·10⁻⁹
    eps = 0.1 * paso
    inicio, fin = (0.0, largo) if tramo_torno is None else tramo_torno
    base, alto = tuple(origen + z * (inicio - eps)), fin - inicio + 2 * eps
    if interna:
        return geo.cilindro(r_torno, alto, base=base, eje=tuple(z))
    grande = geo.cilindro(material + extra + 1.0, alto, base=base, eje=tuple(z))
    return geo.booleano(grande, geo.cilindro(r_torno, alto, base=base, eje=tuple(z)), "cortar")


def _trapecio_surco(diametro, paso, interna, radio_cara, angulo, d2, d1, desfase, fondo, cresta, rel_extra):
    """(r_in, w_in, r_out, w_out, r_torno) del surco de `_surco_en_origen` (ver allí el perfil); r_torno None: sin
    torneado."""
    extra = rel_extra * paso                       # el surco sobresale del material para cortar limpio
    if d2 is None and d1 is None:
        prof = 5 / 8 * math.sqrt(3) / 2 * paso     # 5H/8: altura del filete básico
        pend = 2 * math.tan(math.radians(30))      # ancho que gana el surco por mm radial (flancos a 60°)
        if interna:
            return diametro / 2 - prof - extra, 3 * paso / 4 + pend * extra, diametro / 2, paso / 8, None
        return diametro / 2 - prof, paso / 4, diametro / 2 + extra, 7 * paso / 8 + pend * extra, None
    t = math.tan(math.radians(angulo / 2))

    def ancho(rho):
        if interna:
            return paso / 2 - 2 * (rho - (d2 / 2 + desfase)) * t
        return paso / 2 + 2 * (rho - (d2 / 2 - desfase)) * t

    def radio_de_ancho(fraccion):                  # radio al que el surco mide fraccion·paso
        delta = (fraccion - 0.5) * paso / (2 * t)
        return d2 / 2 + desfase - delta if interna else d2 / 2 - desfase + delta

    if interna:
        r_out, r_in = diametro / 2 + desfase if fondo is None else fondo / 2, d1 / 2 - extra
    else:
        r_in, r_out = d1 / 2 - desfase if fondo is None else fondo / 2, diametro / 2 + extra
    r_torno = None
    material = radio_cara if radio_cara is not None else d1 / 2 if interna else diametro / 2
    if interna and ancho(r_in) > _ANCHO_LIMITE * paso:
        r_in = radio_de_ancho(_ANCHO_TOPE)
        if r_in > material - 0.01 * paso:
            r_torno = radio_de_ancho(_ANCHO_TORNO)
    elif not interna and ancho(r_out) > _ANCHO_LIMITE * paso:
        r_out = radio_de_ancho(_ANCHO_TOPE)
        if r_out < material + 0.01 * paso:
            r_torno = radio_de_ancho(_ANCHO_TORNO)
    if cresta is not None:
        r_cresta = cresta / 2
        if interna and r_cresta > max(material, r_torno or 0.0) + 1e-6:
            r_torno = r_cresta
        elif not interna and r_cresta < min(material, r_torno or math.inf) - 1e-6:
            r_torno = r_cresta
    return r_in, ancho(r_in), r_out, ancho(r_out), r_torno


def _barrer_surco(diametro, paso, largo, interna, mano, radio_cara, z, x, r_in, w_in, r_out, w_out, torno=None,
                  r_torno=None, verificar=False, trozos=True):
    """Barre el trapecio (r_in, w_in)–(r_out, w_out) por la hélice, lo recorta al tramo [0, largo] y, en un
    agujero, le saca lo que cae dentro del agujero. Devuelve (surco, torno): el torneado de la cresta va aparte.
    En un agujero, el surco se recorta al radio del torneado `r_torno` (su cara coincide con la del agujero
    torneado): si los flancos cruzan ese cilindro, el corte falla sin avisar (M3 interior con holgura 0,12 no
    cortaba nada). En la exterior es al revés: recortar el surco con el cilindro del torneado devuelve el cilindro
    entero (falla del kernel), y sin recortarlo el corte sale bien.
    `verificar`: compara el volumen del surco (y, en un agujero, el de lo que queda después del recorte) con la
    cuenta exacta del barrido helicoidal (`_volumen_surco`). Tr12x3 y Tr20x4 interiores salían mal sin avisar con
    algunos largos (el recorte no hacía nada o se comía de más); con otro `extra` salen bien (`_EXTRAS`)."""
    o = np.zeros(3)
    z_ini = -paso                                  # la hélice pasa de largo un paso en cada punta
    # el surco exterior (hueco del tornillo) va centrado a P/2 y el interior (lugar del filete del tornillo) a 0:
    # con la fase de `_fase_rosca`, tornillo y tuerca encajan sin girar ninguno (B-79: chocaban medio paso)
    base = o + z * (z_ini + (0.0 if interna else paso / 2))
    perfil = _poligono([base + x * r_in - z * w_in / 2, base + x * r_out - z * w_out / 2,
                        base + x * r_out + z * w_out / 2, base + x * r_in + z * w_in / 2])
    barrido = _barrido_helicoidal(perfil, _helice(base, z, x, (r_in + r_out) / 2, paso, largo + 2 * paso, mano))
    trapecio = (r_in, w_in, r_out, w_out, largo, paso)
    if verificar:     # B-461: un barrido incompleto (B-371) se descarta antes de recortarlo (M2×30: ~3 s perdidos)
        _exigir_volumen(barrido, _volumen_surco(r_in, r_out, *trapecio[:4], largo + 2 * paso, paso))
    esperado = _volumen_surco(r_in, r_out, *trapecio)
    # en un agujero, los trozos hacen lento el recorte de lo que cae adentro (M10 6H: 1,6 → 6 s)
    surco = _en_tramos(barrido, z, largo, paso, r_out + 1.0) if trozos and not interna else None
    if surco is None or not _volumen_ok(surco, esperado):    # vía rápida fallida o que no conviene: el recorte de siempre
        surco = geo.booleano(barrido, geo.cilindro(r_out + 1.0, largo, base=(0.0, 0.0, 0.0), eje=tuple(z)), "intersecar")
        if verificar:
            _exigir_volumen(surco, esperado)
    adentro = r_torno if (r_torno is not None and interna) else radio_cara
    if interna and adentro is not None:
        # Se le saca al surco la parte que cae dentro del agujero: cortar el cuerpo con el surco entero falla
        # sin avisar en varios tamaños (M10, M12, M20), y con este paso previo sale bien en todos.
        hueco = geo.cilindro(adentro, largo + 2.0, base=tuple(z * -1.0), eje=tuple(z))
        surco = geo.booleano(surco, hueco, "cortar")
        if verificar:
            _exigir_volumen(surco, _volumen_surco(max(adentro, r_in), r_out, *trapecio))
    return surco, torno


def _volumen_surco(r_a, r_b, r_in, w_in, r_out, w_out, largo, paso):
    """Volumen exacto de la parte del surco entre los radios r_a y r_b: un barrido helicoidal de una sección del
    plano del eje recortado a un largo L encierra (L / paso) · ∫ w(ρ)·2πρ dρ, con el ancho w lineal en ρ entre
    (r_in, w_in) y (r_out, w_out) (Simpson es exacto: el integrando es cuadrático)."""
    if r_b <= r_a:
        return 0.0
    f = lambda r: (w_in + (w_out - w_in) * (r - r_in) / (r_out - r_in)) * 2 * math.pi * r  # noqa: E731
    return largo / paso * (r_b - r_a) / 6 * (f(r_a) + 4 * f((r_a + r_b) / 2) + f(r_b))


_EPS_ROSCA = 1e-6     # B-249: la integración por defecto erra en las hélices largas (AFBMA×30: 414 en vez de 484)


def _en_tramos(barrido, z, largo, paso, radio):
    """B-461: el barrido recortado al tramo [0, largo] del eje y partido con planos en trozos de unas 5 vueltas
    (hasta 4). Cortar el cuerpo con UNA cara helicoidal larga es lento y falla más (M10×30: 1 a 2,7 s el corte; M2×15
    quitaba 0,6 % de menos); en trozos el kernel cruza cada cara aparte y en paralelo. Las caras partidas comparten
    la superficie del barrido: `geo.unificar_caras` las vuelve a juntar después del corte. None con menos de 7,5
    vueltas (no conviene) o si el kernel falla."""
    n = min(4, round(largo / paso / 5))
    if n < 2:
        return None
    op, args, planos = BRepAlgoAPI_Splitter(), List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(barrido)
    for k in range(n + 1):
        planos.Append(BRepBuilderAPI_MakeFace(gp_Pln(_pnt(z * (largo * k / n)), _gdir(z)),
                                              -radio, radio, -radio, radio).Face())
    op.SetArguments(args)
    op.SetTools(planos)
    op.SetRunParallel(geo.PARALELO)
    op.Build()
    if not op.IsDone():
        return None
    trozos = [s for s in geo.solidos(op.Shape()) if 0 < float(np.dot(geo.centro_masa(s), z)) < largo]
    return geo.compuesto(trozos) if len(trozos) == n else None


def _volumen_ok(forma, esperado, tolerancia=0.01):
    return not (forma is None or geo.esta_vacia(forma)
                or abs(geo.volumen_exacto(forma, _EPS_ROSCA) - esperado) > tolerancia * esperado)


def _exigir_volumen(forma, esperado, tolerancia=0.01):
    if not _volumen_ok(forma, esperado, tolerancia):
        raise geo.ErrorGeometria("⚠ Probá otro tamaño o la rosca cosmética.")


_EXTRAS = (0.1, 0.13, 0.07)     # cuánto sobresale el surco (en pasos): el primero es el de siempre; los otros, reintentos


def _armar_surco(armar, variante=0):
    """`armar(extra)` con cada margen de `_EXTRAS` hasta que el kernel no falle (ver `_barrer_surco`). `variante` empieza
    por otro margen: el agujero roscado lo usa cuando el corte con el primero deja una arista de más (B-373)."""
    error = None
    k = variante % len(_EXTRAS)
    for extra in _EXTRAS[k:] + _EXTRAS[:k]:
        try:
            return armar(extra)
        except geo.ErrorGeometria as e:
            error = e
    raise error


def _caras_cilindricas(cuerpo):
    return [c for c in geo.caras(cuerpo) if BRepAdaptor_Surface(c).GetType() == GeomAbs_Cylinder]


def _radio_cilindro(cara):
    return BRepAdaptor_Surface(cara).Cylinder().Radius()


def _candidatas_auto(familia, todas=False):
    """Tamaños que compiten en el automático. `todas` (B-497, como Fusion): también las filas sumadas de sus tablas
    (Ø9,3 → M9×1,25, Ø100 → M100); sin él, solo las de antes, para que una receta vieja elija lo mismo."""
    familia = familia or "iso_metrica"
    if familia not in FAMILIAS_ROSCA:
        raise geo.ErrorGeometria(f"Familia de rosca desconocida: {familia}")
    if FAMILIAS_ROSCA[familia]["conica"]:
        raise geo.ErrorGeometria("⚠ Rosca cónica: sin tamaño automático.")
    filas = [k for t in _POR_FAMILIA[familia].values() for k in t]
    return [datos_rosca(k) for k in (filas if todas else [k for k in filas if k not in _SUMADAS] or filas)]


def analizar_rosca(cuerpo, cara=None, *, designacion=None, familia=None, interna=None, todas=False):
    """Lo que la Rosca de Fusion deduce de la cara antes de cortar: {"cara", "datos" (datos_rosca: el tamaño
    elegido o el automático de `familia` según el diámetro de la cara), "interna", "radio", "origen", "eje",
    "zmin", "zmax" (tramo axial de la cara)}. `cara=None`: la cilíndrica que mejor calza con la designación (o
    la de mayor área). `todas`: ver `_candidatas_auto`."""
    if cara is None:
        candidatas = _caras_cilindricas(cuerpo)
        if not candidatas:
            raise geo.ErrorGeometria("⚠ No hay caras cilíndricas para roscar.")
        if designacion:
            dat = datos_rosca(designacion)
            cara = min(candidatas, key=lambda c: min(abs(2 * _radio_cilindro(c) - dat["diametro"]),
                                                     abs(2 * _radio_cilindro(c) - dat["diametro_menor"])))
        else:
            cara = max(candidatas, key=geo.area)
    cara = TopoDS.Face(cara)
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Cylinder:
        raise geo.ErrorGeometria("La rosca se aplica a una cara cilíndrica.")
    radio = _radio_cilindro(cara)
    eje = sup.Cylinder().Axis()
    o, z = _xyz(eje.Location()), _xyz(eje.Direction())
    p, nrm = _normal_orientada(cara, (sup.FirstUParameter() + sup.LastUParameter()) / 2,
                               (sup.FirstVParameter() + sup.LastVParameter()) / 2)
    es_interna = (float(nrm @ (p - o - z * float((p - o) @ z))) < 0) if interna is None else bool(interna)
    if familia and FAMILIAS_ROSCA.get(familia, {}).get("solo_exterior") and es_interna:
        raise geo.ErrorGeometria(f"⚠ «{FAMILIAS_ROSCA[familia]['nombre']}»: rosca externa, no va en agujero.")
    if designacion:
        datos = datos_rosca(designacion)
        if datos["solo_exterior"] and es_interna:
            raise geo.ErrorGeometria(f"⚠ «{FAMILIAS_ROSCA[datos['familia']]['nombre']}»: rosca externa.")
    else:
        clave_diam = "diametro_menor" if es_interna else "diametro"
        preferida = {"iso_metrica": "ISO métrica gruesa", "unificada": "Unificada UNC"}.get(familia or "iso_metrica")
        datos = min(_candidatas_auto(familia, todas),
                    key=lambda dt: (round(abs(2 * radio - dt[clave_diam]), 6), dt["norma"] != preferida,
                                    dt["designacion"] in _SUMADAS))     # empate (Ø16 interior): la fila de siempre
    zmin, zmax = _tramo_axial(cara, o, z)
    return {"cara": cara, "datos": datos, "interna": es_interna, "radio": radio, "origen": o, "eje": z,
            "zmin": zmin, "zmax": zmax}


def _tramo_axial(cara, o, z):
    """(zmin, zmax) de la cara sobre el eje (o, z): se proyectan puntos de sus aristas."""
    alturas = []
    for e in _aristas_de(cara):
        curva = BRepAdaptor_Curve(e)
        a, b = curva.FirstParameter(), curva.LastParameter()
        alturas += [float((_xyz(curva.Value(a + (b - a) * k / 8)) - o) @ z) for k in range(9)]
    return min(alturas), max(alturas)


def caras_sobre_cilindro(cuerpo, cara, tol=1e-6):
    """Caras cilíndricas de `cuerpo` con el eje de `cara` y dentro de su tramo axial: en un cuerpo ya roscado, lo
    que quedó de la cara elegida (los tramos de afuera y las crestas, con cualquier Ø). Fusion las sigue resaltando
    como la cara elegida, y las crestas en azul dejan ver la hélice (P-145)."""
    sup = BRepAdaptor_Surface(TopoDS.Face(cara))
    eje = sup.Cylinder().Axis()
    o, z = _xyz(eje.Location()), _xyz(eje.Direction())
    zmin, zmax = _tramo_axial(cara, o, z)
    vecinas = geo.IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(cuerpo, TopAbs_EDGE, TopAbs_FACE, vecinas)
    radio = lambda p: float(np.linalg.norm(np.cross(_xyz(p) - o, z)))  # noqa: E731

    def es_fondo(c, cil):     # B-461: el fondo de la varilla directa (solo exterior) es un cilindro; sus flancos suben
        r = cil.Radius()      # a la cresta. En un agujero la normal mira al eje y las crestas son las de adentro.
        return cil.Direct() == (c.Orientation() == TopAbs_FORWARD) and any(BRepAdaptor_Surface(TopoDS.Face(f)).GetType() == GeomAbs_BSplineSurface
                   and any(radio(BRep_Tool.Pnt_s(TopoDS.Vertex(v))) > r + tol for v in geo._explorar(f, TopAbs_VERTEX))
                   for e in _aristas_de(c) for f in geo.lista_occ(vecinas.FindFromKey(e)))

    salida = []
    for c in _caras_cilindricas(cuerpo):
        cil = BRepAdaptor_Surface(c).Cylinder()
        e = cil.Axis()
        oc, zc = _xyz(e.Location()) - o, _xyz(e.Direction())
        if abs(abs(float(zc @ z)) - 1) > tol or np.linalg.norm(oc - z * float(oc @ z)) > tol:
            continue
        a, b = _tramo_axial(c, o, z)
        if a >= zmin - tol and b <= zmax + tol and not es_fondo(c, cil):
            salida.append(c)
    return salida


def rosca(cuerpo, cara=None, *, designacion=None, longitud=None, desfase=0.0, modelada=True, mano="derecha",
          interna=None, invertir=False, familia=None, clase="", holgura=0.0, tabla=True):
    """Rosca (Thread) de Fusion [GUID-7BD8CD24…, GUID-C37E8172…] sobre una cara cilíndrica del cuerpo.

    `cara=None`: la cara cilíndrica que mejor calza con la designación (o la de mayor área).
    `designacion=None`: tamaño automático de `familia` (por defecto la métrica ISO) según el diámetro de la cara,
    como Fusion. `longitud=None` = largo completo; `desfase` corre el inicio desde el extremo inferior del eje de
    la cara (el superior con `invertir`). `interna=None` detecta si la cara es un agujero. `modelada=False` =
    rosca cosmética (la geometría no cambia). `clase` ("6g", "6H", "2A", "auto"…; "" = perfil básico) corre los
    flancos al centro de la tolerancia de la clase (ISO 965-1 / ASME B1.1) y `holgura` (mm, radial) los corre
    más, para imprimir en 3D. El perfil es el de la familia: 60° (M, UN), 55° (G), 30° (Tr) o 29° (ACME); las
    cónicas (R, NPT) solo van cosméticas. `tabla`: ver `_perfil_clase`. Devuelve el cuerpo roscado."""
    info = analizar_rosca(cuerpo, cara, designacion=designacion, familia=familia, interna=interna, todas=True)  # B-520
    datos, o, z, radio = info["datos"], info["origen"], info["eje"], info["radio"]
    zmin, zmax = info["zmin"], info["zmax"]
    largo = (zmax - zmin - desfase) if longitud is None else float(longitud)
    if largo <= 1e-6 or desfase < 0 or desfase + largo > zmax - zmin + 1e-6:
        raise geo.ErrorGeometria("⚠ El largo y desfase de la rosca no entran.")
    if not modelada:
        return cuerpo
    if datos["conica"]:
        raise geo.ErrorGeometria(f"⚠ {datos['designacion']} es cónica: solo va cosmética aquí.")
    paso = datos["paso"]
    vueltas = largo / paso
    if vueltas > 300:     # mismo límite que fijaciones._filete
        raise geo.ErrorGeometria(f"⚠ {vueltas:g} vueltas: mucho para rosca modelada.")
    if paso > largo + 1e-6:
        raise geo.ErrorGeometria(f"Paso {paso:g} mm > largo roscado {largo:g} mm.")
    perfil = _perfil_clase(datos, clase, info["interna"], holgura, tabla)
    tol = 0.01 * datos["paso"]     # un Ø apenas distinto no se tornea ni se rellena: dejaría una lámina casi sin espesor
    if tabla and perfil["cresta"] is None:
        # B-247, como Fusion: una cara más gruesa que la rosca (o un agujero más chico) se tornea a su Ø de cresta.
        # Dispara el Ø básico, no la holgura (una cara justa sigue como antes); las recetas viejas (sin `tabla`), igual.
        basico, h = datos["diametro_menor" if info["interna"] else "diametro"], float(holgura)
        if (2 * radio < basico - tol) if info["interna"] else (2 * radio > basico + tol):
            # agujero: Ø menor al centro de la tolerancia de la clase (6H: D1 + TD1/2), como el taladro del Agujero
            perfil["cresta"] = diametro_taladro_rosca(datos["designacion"], clase, h) if info["interna"] else basico - 2 * h
    z0 = zmax - desfase - largo if invertir else zmin + desfase
    # B-248/B-251/B-367, como Fusion: el tamaño pone el Ø de toda la cara, aunque la rosca sea parcial. Un eje más fino
    # que el Ø mayor (o un agujero más ancho que el del taladro) se rellena; el anillo se mete un poco en el material.
    D, meter = datos["diametro"], 0.1 * datos["paso"]
    taladro = diametro_taladro_rosca(datos["designacion"], clase, holgura) if tabla and info["interna"] else None
    if tabla and (2 * radio > taladro + tol if info["interna"] else 2 * radio < D - tol):
        if info["interna"]:      # hasta el Ø menor con la clase, como el taladro del Agujero (6H: D1 + TD1/2)
            r_a, r_b, radio = taladro / 2, radio + meter, taladro / 2
        else:
            r_a, r_b, radio = radio - meter, D / 2, D / 2
        base = tuple(o + z * zmin)
        anillo = geo.booleano(geo.cilindro(r_b, zmax - zmin, base=base, eje=tuple(z)),
                              geo.cilindro(r_a, zmax - zmin, base=base, eje=tuple(z)), "cortar")
        cuerpo = geo.booleano(cuerpo, anillo, "unir")

    if not info["interna"] and mano == "derecha":
        directa = _rosca_directa(cuerpo, o, z, z0, largo, radio, datos, perfil, (zmin, zmax) if tabla else None)
        if directa is not None:
            return directa

    def cortar(extra):
        def armar_tramo(za, la, trozos=True):
            # a izquierdas en un eje el kernel falla (SOL-1): se barre a derechas y el surco se refleja en un plano del eje
            espejar = mano == "izquierda" and not info["interna"]
            surco, torno = _surco_rosca(o, z, datos["diametro"], datos["paso"], za, la, info["interna"],
                                        "derecha" if espejar else mano, radio, partes=True, extra=extra,
                                        tramo_torno=(zmin, zmax) if tabla else None, trozos=trozos and not espejar, **perfil)
            if espejar:
                t = gp_Trsf()
                t.SetMirror(gp_Ax2(_pnt(o), _gdir(_perpendicular(z))))
                surco = aplicar(surco, t)
            return surco, torno

        def por_mitades():
            mitad = largo / 2
            s1, t1 = armar_tramo(z0, mitad)
            s2, t2 = armar_tramo(z0 + mitad, largo - mitad)
            torno_d = None
            if t1 is not None and t2 is not None:
                torno_d = geo.booleano(t1, t2, "unir")
            return (s1, s2), torno_d

        def tornear_y_cortar(surcos, torno):
            resultado = cuerpo if torno is None else geo.booleano(cuerpo, torno, "cortar")   # cresta sin espesor: se tornea
            if len(surcos) > 1:     # B-461: las mitades en UNA pasada (M20x2.5×100: 6,7 → 2,8 s); si falla, de a una
                try:
                    return _cortar_helicoidal(resultado, geo.compuesto(surcos), o, z)
                except geo.ErrorGeometria:
                    pass
            for surco in surcos:     # P-78: un corte por mitad; unir las mitades antes tardaba 5,7 s (M20x2.5×100)
                resultado = _cortar_helicoidal(resultado, surco, o, z)   # sale validado y con el surco cortado
            return resultado

        partido = False
        try:
            surco, torno = armar_tramo(z0, largo)
            surcos = (surco,)
        except geo.ErrorGeometria:
            # Una rosca larga puede superar la tolerancia del kernel en un barrido (M5 6g×50 no salía): se barre a
            # la mitad; el torno con el largo total conduce con sus caras a las puntas.
            surcos, torno = por_mitades()
            partido = True
        resultado = None
        if not partido and len(geo.solidos(surco)) > 1:
            # Si falla el corte por tramos en su fase, probar entero antes de recurrir a girar el cuerpo.
            cuerpo_torneado = cuerpo if torno is None else geo.booleano(cuerpo, torno, "cortar")
            try:
                resultado = _cortar_helicoidal(cuerpo_torneado, surco, o, z, fase_fija=True)
            except geo.ErrorGeometria:
                try:
                    entero, _ = armar_tramo(z0, largo, trozos=False)
                    resultado = _cortar_helicoidal(cuerpo_torneado, entero, o, z, fase_fija=True)
                except geo.ErrorGeometria:
                    pass
        if resultado is None:
            resultado = tornear_y_cortar(surcos, torno)
        if not partido and rv._topologia(resultado)["no_manifold"]:
            # Un barrido chico y corrido puede dejar la arista de contacto entre la cresta torneada y el surco
            # compartida por 3 caras (M5×0,8 con holgura): el corte por mitades reubica esa arista.
            resultado = tornear_y_cortar(*por_mitades())
        return resultado

    return _armar_surco(cortar)


def _cortar_helicoidal(cuerpo, herramienta, origen, eje, *, fase_fija=False):
    """Corte con una herramienta helicoidal. El corte exacto a veces no hace nada sin avisar (las caras del
    surco rozan el cilindro del agujero: pasó con M10 y M20 interiores); con tolerancia difusa sale bien.
    Según el largo, las puntas del surco caen sobre la costura del cilindro y el corte falla, no saca nada o saca de
    más (M8×1,25 de 15 mm, M12×1,75 de 12 mm): el último recurso gira solo el cuerpo y devuelve el resultado a su lugar,
    lo cual cambia la fase del surco. `fase_fija=True` no permite ese respaldo. P-78: el difuso va antes que el exacto,
    que donde falla tarda más (M3×20: 7,4 s fallado contra 1,9 s bien); después de 0°, 229° acertó en los 21 casos
    medidos (M40x3×30 y M12×1,75×12 tiraban 3 y 4 cortes de ~0,4 s; ahora 2). 229° primero ahorraría otro corte,
    pero mueve la costura del eje y B-308 (cortar la tapa con ese eje y partirla) pierde la tapa.
    Éxito = forma válida que sacó material sin pasarse del volumen del surco (hay que medirlo: sin esto el corte salía vacío)."""
    base, surco = geo.volumen_exacto(cuerpo, _EPS_ROSCA), geo.volumen_exacto(herramienta, _EPS_ROSCA)
    eje_giro = gp_Ax1(_pnt(origen), _gdir(eje))
    caras_por_solido = [geo.caras(s) for s in geo.solidos(herramienta)]
    for difuso in (1e-4, 0.0, 1e-5):
        for giro in ((0.0,) if fase_fija else (0.0, 229.0, 61.0, 137.0)):
            t = gp_Trsf()
            t.SetRotation(eje_giro, math.radians(-giro))
            op = BRepAlgoAPI_Cut()
            args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
            args.Append(cuerpo.Moved(TopLoc_Location(t)) if giro else cuerpo)
            herr.Append(herramienta)
            op.SetArguments(args)
            op.SetTools(herr)
            op.SetRunParallel(geo.PARALELO)
            op.SetNonDestructive(True)   # B-48: no escribir en las entradas
            if difuso:
                op.SetFuzzyValue(difuso)
            op.Build()
            # B-461: con varios sólidos (trozos, mitades) uno salteado igual sacaría más del 20 %: se exige cada uno
            if not op.IsDone() or any(all(op.IsDeleted(f) for f in caras) for caras in caras_por_solido):
                continue
            hecho = op.Shape().Moved(TopLoc_Location(t.Inverted())) if giro else op.Shape()
            hecho = geo.unificar_caras(hecho)   # B-461: junta las caras que partió `_en_tramos`
            if geo.es_valida(hecho) and 0.2 * surco < base - geo.volumen_exacto(hecho, _EPS_ROSCA) <= 1.01 * surco:
                return hecho
    raise geo.ErrorGeometria("⚠ El kernel no pudo cortar la rosca.")


def _rosca_directa(cuerpo, o, z, z0, largo, radio, datos, perfil, tramo_torno):
    """B-461: rosca exterior a derechas sin booleana helicoidal: tornea la cresta si hace falta (un anillo), saca del
    cuerpo el tramo cilíndrico y pega en su lugar la varilla roscada armada cara por cara (`_varilla_roscada`; M10×30:
    2,1 → 0,4 s). None si el resultado no es válido o no da el volumen exacto: `rosca` sigue con el corte de siempre."""
    from OCP.BOPAlgo import BOPAlgo_GlueShift
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    if largo / datos["paso"] > 100:     # tamaño extremo (M0.3 en 10 mm: 125 vueltas): el corte da su mensaje (B-299)
        return None
    try:
        paso = datos["paso"]
        r_in, w_in, r_out, w_out, r_torno, torno = _surco_rosca(o, z, datos["diametro"], paso, z0, largo, False,
                                                                "derecha", radio, tramo_torno=tramo_torno,
                                                                solo_trapecio=True, **perfil)
        if torno is not None:     # la cresta se tornea en toda la cara, como en el corte de siempre
            cuerpo, radio = geo.booleano(cuerpo, torno, "cortar"), r_torno
        x = _perpendicular(z) * (-1.0 if _fase_rosca(z) else 1.0)     # la misma fase que el surco (B-79)
        lugar = gp_Trsf()
        lugar.SetDisplacement(gp_Ax3(), gp_Ax3(_pnt(o + z * z0), _gdir(z), _gdir(x)))
        cilindro = geo.cilindro(radio, largo, base=tuple(o + z * z0), eje=tuple(z))
        vacio = geo.booleano(cilindro, cuerpo, "cortar")     # B-547: el hueco de un cuello vaciado no se rellena
        hueco = _radio_hueco(vacio, o + z * z0, z, largo, r_in)     # un tubo: la varilla ya sale hueca
        varilla = _varilla_roscada(radio, largo, paso, r_in, w_in, r_out, w_out, hueco).Moved(TopLoc_Location(lugar))
        if hueco:
            vacio = None
        resto = geo.booleano(cuerpo, cilindro, "cortar")
        if geo.esta_vacia(resto):
            hecho = varilla
        else:     # sin `geo.booleano`: unificaría las caras de una vuelta (ver `_varilla_roscada`)
            op, args, herr = BRepAlgoAPI_Fuse(), List_TopoDS_Shape(), List_TopoDS_Shape()
            args.Append(resto)
            herr.Append(varilla)
            op.SetArguments(args)
            op.SetTools(herr)
            op.SetRunParallel(geo.PARALELO)
            op.SetNonDestructive(True)
            op.SetGlue(BOPAlgo_GlueShift)     # solo se tocan en las tapas: no busca cruces (si no, lo atajan los controles)
            op.Build()
            if not op.IsDone():
                return None
            hecho = op.Shape()
        if vacio is not None and not geo.esta_vacia(vacio):     # otro hueco: se corta (sin `geo.booleano`, como el pegado)
            corte = BRepAlgoAPI_Cut(hecho, vacio)
            if not corte.IsDone():
                return None
            hecho = corte.Shape()
        base, surco = geo.volumen_exacto(cuerpo, _EPS_ROSCA), _volumen_surco(r_in, radio, r_in, w_in, r_out, w_out,
                                                                              largo, paso)
        if (len(geo.solidos(hecho)) == len(geo.solidos(cuerpo)) and geo.es_valida(hecho)
                and abs(geo.volumen_exacto(hecho, _EPS_ROSCA) - (base - surco)) <= 1e-3 * surco + 1e-6 * base):
            return hecho
    except Exception:     # vía rápida: cualquier falla del kernel cae al corte de siempre, sin mostrarla (CLAUDE.md)
        pass
    return None


def _radio_hueco(vacio, base, eje, largo, r_in):
    """B-547: el radio del hueco si `vacio` (lo que falta del cuerpo dentro del cilindro de la rosca) es un cilindro
    coaxial de largo completo y más fino que el fondo del filete (el cuello vaciado de una botella); si no, 0."""
    if geo.esta_vacia(vacio):
        return 0.0
    v = geo.volumen(vacio)
    rb = math.sqrt(v / (math.pi * largo))
    if not 1e-3 < rb < r_in - 1e-3:
        return 0.0
    cil = geo.cilindro(rb, largo, base=tuple(base), eje=tuple(eje))
    sobra = geo.booleano(vacio, cil, "cortar")
    return rb if geo.esta_vacia(sobra) or geo.volumen(sobra) < 1e-6 * v else 0.0


_MUESTRAS_HELICE = 128     # por vuelta: con 48 quedaban huecos de 2e-5 mm entre caras y la tapa no cerraba


def _varilla_roscada(R, largo, paso, r_in, w_in, r_out, w_out, hueco=0.0):
    """Varilla de radio R y largo `largo` sobre +Z (desde z = 0) con el surco exterior a derechas de `_barrer_surco`
    (trapecio (r_in, w_in)–(r_out, w_out) centrado en z = −P/2 sobre +X), armada cara por cara: fondo y cresta en
    cilindros exactos, flancos reglados entre dos hélices B-spline con el mismo parámetro y tapas planas. Los
    cilindros van de a una vuelta con u de 0 a 2π (una cara cilíndrica de varias vueltas hace mentir al volumen de
    GProp); los flancos, de a 1,5–3 vueltas por superficie: uno de 20 vueltas en una sola B-spline (2560 polos) hacía
    lenta cada booleana posterior (un agujero en M10×30: 7 s), uno de 1 vuelta no lo reconoce `_es_filete` y uno de 4 hace
    fallar a `BRepClass3d_SolidClassifier` (un rayo lo cruza varias veces: B-531). `hueco` > 0: un tubo, con un hueco
    coaxial de ese radio (B-547: el cuello vaciado de una botella), sin booleana."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.GeomFill import GeomFill
    from OCP.OCP.collections import HArray1_double
    k, zc = paso / (2 * math.pi), -paso / 2
    ancho = lambda rho: w_in + (w_out - w_in) * (rho - r_in) / (r_out - r_in)  # noqa: E731
    ejes = gp_Ax3(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0), gp_Dir(1.0, 0.0, 0.0))

    def helice(rho, z_off, a, b):     # la hélice de t = a a t = b y un poco más a cada lado
        t0, t1 = a - 0.1, b + 0.1
        n = math.ceil(_MUESTRAS_HELICE * (t1 - t0) / (2 * math.pi)) + 1
        pts, par = HArray1_gp_Pnt(1, n), HArray1_double(1, n)
        for i in range(n):
            t = t0 + (t1 - t0) * i / (n - 1)
            pts.SetValue(i + 1, gp_Pnt(rho * math.cos(t), rho * math.sin(t), k * t + z_off))
            par.SetValue(i + 1, t)
        interp = GeomAPI_Interpolate(pts, par, False, 1e-9)
        interp.Perform()
        return interp.Curve()

    def recortar(poligono, lo, hi):     # polígono convexo recortado a lo <= u <= hi (Sutherland-Hodgman)
        for dentro, corte in ((lambda q: q[0] >= lo, lo), (lambda q: q[0] <= hi, hi)):
            salida = []
            for a, b in zip(poligono, poligono[1:] + poligono[:1], strict=True):
                if dentro(a):
                    salida.append(a)
                if dentro(a) != dentro(b):
                    salida.append((corte, a[1] + (corte - a[0]) / (b[0] - a[0]) * (b[1] - a[1])))
            poligono = salida
        return [q for i, q in enumerate(poligono) if math.dist(q, poligono[i - 1]) > 1e-9]

    def cara_uv(sup, puntos):     # cara de `sup` limitada por segmentos rectos en (u, v)
        hilo = BRepBuilderAPI_MakeWire()
        for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True):
            arista = BRepBuilderAPI_MakeEdge(Geom2d_Line(gp_Pnt2d(*a), gp_Dir2d(b[0] - a[0], b[1] - a[1])), sup,
                                             0.0, math.dist(a, b)).Edge()
            BRepLib.BuildCurves3d_s(arista, 1e-7)
            hilo.Add(arista)
        return BRepBuilderAPI_MakeFace(sup, hilo.Wire(), True).Face()

    def por_tramos(superficie, poligono, periodica):     # superficie(a, b): la del tramo a <= u <= b
        us = [q[0] for q in poligono]
        if periodica:     # en un cilindro, cada vuelta con u de 0 a 2π (ver el docstring)
            cortes = [2 * math.pi * j for j in range(math.floor(min(us) / (2 * math.pi)), math.ceil(max(us) / (2 * math.pi)) + 1)]
        else:     # flancos de 1,5 a 3 vueltas: `_es_filete` pide más de 1,5 y con 4 el clasificador de puntos falla (B-531)
            n = max(1, math.floor((max(us) - min(us)) / (3 * math.pi)))
            cortes = [min(us) + (max(us) - min(us)) * i / n for i in range(n + 1)]
        salida = []
        for a, b in itertools.pairwise(cortes):
            q = recortar(poligono, a, b)
            if len(q) >= 3:
                salida.append(cara_uv(superficie(a, b), [(u - a * periodica, v) for u, v in q]))
        return salida

    caras = []
    for rho, b1, b2 in ((r_in, zc - w_in / 2, zc + w_in / 2), (R, zc + ancho(R) / 2, zc - ancho(R) / 2 + paso)):
        # fondo y cresta: la tira helicoidal b1 + k·u <= v <= b2 + k·u recortada a 0 <= v <= largo
        caras += por_tramos(lambda a, b, sup=Geom_CylindricalSurface(ejes, rho): sup,
                            [(-b2 / k, 0.0), (-b1 / k, 0.0), ((largo - b1) / k, largo), ((largo - b2) / k, largo)], True)
    for s in (-1, 1):     # flancos z = zc + k·t + s·w(ρ)/2: regla entre la hélice de r_in y la de R
        za, zb = zc + s * w_in / 2, zc + s * ancho(R) / 2
        ta0, ta1, tb0, tb1 = -za / k, -zb / k, (largo - za) / k, (largo - zb) / k     # z = 0 y z = largo
        caras += por_tramos(lambda a, b, za=za, zb=zb: GeomFill.Surface_s(helice(r_in, za, a, b), helice(R, zb, a, b)),
                            [(ta0, 0.0), (tb0, 0.0), (tb1, 1.0), (ta1, 1.0)], False)
    for zt in (0.0, largo):     # tapas con las aristas de los costados que caen en el plano (en lista: de a una
        lista, hilo = List_TopoDS_Shape(), BRepBuilderAPI_MakeWire()     # descarta las que llegan fuera de orden)
        for c in list(caras):
            for e in _aristas_de(c):
                if all(abs(BRep_Tool.Pnt_s(v).Z() - zt) < 1e-6 for v in (TopExp.FirstVertex_s(e), TopExp.LastVertex_s(e))):
                    lista.Append(e)
        hilo.Add(lista)
        tapa = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0.0, 0.0, zt), gp_Dir(0.0, 0.0, 1.0)), hilo.Wire(), True)
        if hueco > 0:     # una corona: la tapa menos el círculo del hueco (un corte plano, barato)
            disco = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0.0, 0.0, zt), gp_Dir(0.0, 0.0, 1.0)), BRepBuilderAPI_MakeWire(
                BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(0.0, 0.0, zt), gp_Dir(0.0, 0.0, 1.0)), hueco)).Edge()).Wire(),
                True).Face()
            caras += _caras_de(BRepAlgoAPI_Cut(tapa.Face(), disco).Shape())
        else:
            caras.append(tapa.Face())
    if hueco > 0:
        caras.append(BRepBuilderAPI_MakeFace(Geom_CylindricalSurface(ejes, hueco), 0.0, 2 * math.pi, 0.0, largo, 1e-7).Face())
    cosido = BRepBuilderAPI_Sewing(1e-5)
    for c in caras:
        cosido.Add(c)
    cosido.Perform()
    cascara = TopExp_Explorer(cosido.SewedShape(), TopAbs_SHELL)
    solido = BRepBuilderAPI_MakeSolid(TopoDS.Shell(cascara.Current())).Solid()
    BRepLib.OrientClosedSolid_s(solido)
    return solido


_registrar_tema(globals())
