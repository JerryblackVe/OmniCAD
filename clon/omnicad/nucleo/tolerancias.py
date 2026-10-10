# -*- coding: utf-8 -*-
"""
Tolerancias normalizadas en funciones puras (sin Qt ni timeline). Dan los datos de «Clase» que Fusion muestra en
Rosca y Agujero, más el cálculo de ajustes agujero/eje de las tablas de taller.

  - ISO 286-1 / ISO 286-2: grados IT5 a IT11 y desviaciones fundamentales hasta 500 mm. Agujeros D, E, F, G y H
    (regla general de la norma: EI = −es de la misma letra) y ejes d, e, f, g, h, j6, k, n, p y s. Ajuste
    agujero/eje: juego (u apriete) mínimo y máximo y tipo de ajuste.
  - ISO 965-1: clases 6H y 6G (rosca interior) y 6g y 6h (exterior) de la rosca métrica, SOLO en los tamaños
    cuyos valores están verificados (ver `_ISO965_TD2`).
  - ASME B1.1: clases 2A y 3A (exterior) y 2B y 3B (interior) de la rosca unificada, con las fórmulas de la
    norma (largo de enganche = diámetro nominal).

Unidades: los resultados en mm; las tablas internas en micrómetros (µm), como en las normas.
Errores: `geo.ErrorGeometria` con el motivo en español.
"""
import math
import re
from decimal import ROUND_HALF_UP, Decimal

from . import geometria as geo

# ================================================================ ISO 286 (ajustes)
# ISO 286-1 tabla 1: límites superiores de los escalones de medida nominal (mm). Cada escalón es
# «más de a hasta b inclusive»; el primero va de 0 a 3.
_ESCALONES = (3, 6, 10, 18, 30, 50, 80, 120, 180, 250, 315, 400, 500)

# ISO 286-1 tabla 1: tolerancias fundamentales IT5 a IT11 en µm, por escalón de _ESCALONES.
_IT = {
    5: (4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27),
    6: (6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40),
    7: (10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63),
    8: (14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97),
    9: (25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155),
    10: (40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250),
    11: (60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400),
}

# ISO 286-1 tabla 2: desviación superior es (µm) de los ejes d a h, que no depende del grado.
_ES_EJE = {
    "d": (-20, -30, -40, -50, -65, -80, -100, -120, -145, -170, -190, -210, -230),
    "e": (-14, -20, -25, -32, -40, -50, -60, -72, -85, -100, -110, -125, -135),
    "f": (-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68),
    "g": (-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20),
    "h": (0,) * 13,
}

# ISO 286-1 tabla 2: desviación inferior ei (µm) de los ejes j (columna de IT5 e IT6; acá solo se acepta j6),
# k (grados IT4 a IT7; en los demás grados ei = 0), n y p.
_EI_J56 = (-2, -2, -2, -3, -4, -5, -7, -9, -11, -13, -16, -18, -20)
_EI_K4A7 = (0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5)
_EI_EJE = {
    "n": (4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40),
    "p": (6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68),
}
# ISO 286-1 tabla 2, eje s: hasta 50 mm por los escalones generales; desde 50 mm la norma usa subescalones.
_EI_S_HASTA_50 = (14, 19, 23, 28, 35, 43)
_EI_S_DESDE_50 = ((65, 53), (80, 59), (100, 71), (120, 79), (140, 92), (160, 100), (180, 108), (200, 122),
                  (225, 130), (250, 140), (280, 158), (315, 170), (355, 190), (400, 208), (450, 232), (500, 252))

LETRAS_AGUJERO = ("D", "E", "F", "G", "H")
LETRAS_EJE = ("d", "e", "f", "g", "h", "j", "k", "n", "p", "s")
GRADOS_IT = tuple(sorted(_IT))


def _escalon(nominal):
    n = float(nominal)
    if not 0 < n <= _ESCALONES[-1]:
        raise geo.ErrorGeometria(f"ISO 286 cubre medidas nominales de más de 0 hasta 500 mm (llegó {nominal:g}).")
    return next(i for i, b in enumerate(_ESCALONES) if n <= b)


def grado_it(nominal, grado):
    """Tolerancia fundamental ITn (mm) de ISO 286-1 para una medida nominal (grados 5 a 11, hasta 500 mm)."""
    if grado not in _IT:
        raise geo.ErrorGeometria(f"Grado IT{grado} sin datos: hay IT{GRADOS_IT[0]} a IT{GRADOS_IT[-1]}.")
    return _IT[grado][_escalon(nominal)] / 1000


def _partir_clase(clase):
    m = re.fullmatch(r"\s*([A-Za-z])\s*(\d{1,2})\s*", str(clase or ""))
    if not m:
        raise geo.ErrorGeometria(f"Clase de tolerancia no válida: «{clase}» (ejemplos: H7, g6, k6).")
    return m.group(1), int(m.group(2))


def _desviaciones_um(nominal, clase):
    """(superior, inferior) en µm enteros de una clase ISO 286 («H7», «g6»…)."""
    letra, grado = _partir_clase(clase)
    i = _escalon(nominal)
    if grado not in _IT:
        raise geo.ErrorGeometria(f"Grado IT{grado} sin datos: hay IT{GRADOS_IT[0]} a IT{GRADOS_IT[-1]}.")
    it = _IT[grado][i]
    if letra.isupper():                                       # agujero
        if letra not in LETRAS_AGUJERO:
            raise geo.ErrorGeometria(f"Agujero {letra}: solo hay datos de {', '.join(LETRAS_AGUJERO)}.")
        ei = -_ES_EJE[letra.lower()][i]                       # regla general: EI = −es de la misma letra
        return ei + it, ei
    if letra not in LETRAS_EJE:
        raise geo.ErrorGeometria(f"Eje {letra}: solo hay datos de {', '.join(LETRAS_EJE)}.")
    if letra in _ES_EJE:
        es = _ES_EJE[letra][i]
        return es, es - it
    if letra == "j":
        if grado != 6:
            raise geo.ErrorGeometria("Del eje j solo hay datos de j6.")
        ei = _EI_J56[i]
    elif letra == "k":
        ei = _EI_K4A7[i] if 4 <= grado <= 7 else 0
    elif letra == "s":
        n = float(nominal)
        ei = _EI_S_HASTA_50[i] if n <= 50 else next(v for b, v in _EI_S_DESDE_50 if n <= b)
    else:
        ei = _EI_EJE[letra][i]
    return ei + it, ei


def desviaciones(nominal, clase):
    """(desviación superior, desviación inferior) en mm de una clase ISO 286-2: mayúscula = agujero («H7»),
    minúscula = eje («g6»). Ej.: Ø25 H7 → (0.021, 0.0); Ø25 g6 → (−0.007, −0.020)."""
    sup, inf = _desviaciones_um(nominal, clase)
    return sup / 1000, inf / 1000


def ajuste(nominal, agujero, eje):
    """Ajuste ISO 286 agujero/eje (p. ej. Ø25 H7/g6): límites de cada pieza, juego máximo y mínimo (negativo =
    apriete) y tipo: «juego» (siempre hay holgura), «apriete» (siempre interferencia) o «transicion»."""
    letra_a, _ = _partir_clase(agujero)
    letra_e, _ = _partir_clase(eje)
    if not letra_a.isupper():
        raise geo.ErrorGeometria(f"La clase del agujero va en mayúscula (H7), llegó «{agujero}».")
    if not letra_e.islower():
        raise geo.ErrorGeometria(f"La clase del eje va en minúscula (g6), llegó «{eje}».")
    n = float(nominal)
    es_a, ei_a = _desviaciones_um(n, agujero)
    es_e, ei_e = _desviaciones_um(n, eje)
    juego_max, juego_min = es_a - ei_e, ei_a - es_e        # en µm, exactos
    tipo = "juego" if juego_min >= 0 else ("apriete" if juego_max <= 0 else "transicion")

    def pieza(clase, sup, inf):
        return {"clase": str(clase).strip(), "superior": sup / 1000, "inferior": inf / 1000,
                "maximo": round(n + sup / 1000, 6), "minimo": round(n + inf / 1000, 6),
                "tolerancia": (sup - inf) / 1000}

    res = {"nominal": n, "norma": "ISO 286-2", "agujero": pieza(agujero, es_a, ei_a), "eje": pieza(eje, es_e, ei_e),
           "juego_maximo": juego_max / 1000, "juego_minimo": juego_min / 1000, "tipo": tipo}
    res["apriete_maximo"] = max(0, -juego_min) / 1000
    res["apriete_minimo"] = max(0, -juego_max) / 1000 if tipo == "apriete" else 0.0
    return res


# ================================================================ ISO 965-1 (rosca métrica)
# Desviación fundamental de g (es, µm, negativa) y de G (EI = +|es|), por paso P (mm). ISO 965-1 tabla 3.
_ISO965_G = {0.5: 20, 0.7: 22, 0.8: 24, 1.0: 26, 1.25: 28, 1.5: 32, 1.75: 34, 2.0: 38, 2.5: 42, 3.0: 48, 3.5: 53,
             4.0: 60}
# Tolerancia del diámetro mayor exterior Td, grado 6 (µm), por paso. ISO 965-1 tabla 4.
_ISO965_TD = {0.5: 106, 0.7: 140, 0.8: 150, 1.0: 180, 1.25: 212, 1.5: 236, 1.75: 265, 2.0: 280, 2.5: 335, 3.0: 375,
              3.5: 425, 4.0: 475}
# Tolerancia del diámetro menor interior TD1, grado 6 (µm), por paso. ISO 965-1 tabla 5.
_ISO965_TD1 = {0.5: 140, 0.7: 180, 0.8: 200, 1.0: 236, 1.25: 265, 1.5: 300, 1.75: 335, 2.0: 375, 2.5: 450,
               3.0: 500, 3.5: 560, 4.0: 600}
# Tolerancias del diámetro de flancos, grado 6 (µm): (Td2 exterior, TD2 interior) por (diámetro, paso).
# ISO 965-1 tablas 6 y 7 (dependen del escalón de diámetro y del paso). Solo los tamaños verificados contra
# las tablas de límites publicadas de M3 a M39 gruesa (y las finas del mismo escalón y paso que una gruesa
# verificada); los demás tamaños no tienen clase (se modela el perfil básico).
_ISO965_TD2 = {
    (3, 0.5): (75, 100), (4, 0.7): (90, 118), (5, 0.8): (95, 125), (6, 1.0): (112, 150), (8, 1.25): (118, 160),
    (8, 1.0): (112, 150), (10, 1.5): (132, 180), (10, 1.25): (118, 160), (10, 1.0): (112, 150),
    (12, 1.75): (150, 200), (14, 2.0): (160, 212), (16, 2.0): (160, 212), (18, 2.5): (170, 224),
    (20, 2.5): (170, 224), (22, 2.5): (170, 224), (24, 3.0): (200, 265), (27, 3.0): (200, 265),
    (30, 3.5): (212, 280), (33, 3.5): (212, 280), (36, 4.0): (224, 300), (39, 4.0): (224, 300),
}
CLASES_ISO965 = {"6H": True, "6G": True, "6g": False, "6h": False}       # clase → ¿es de rosca interior?

# ================================================================ ASME B1.1 (rosca unificada)
CLASES_UN = {"2B": True, "3B": True, "2A": False, "3A": False}
# Tolerancia de flancos de cada clase respecto de la 2A y holgura (allowance) de la exterior: ASME B1.1.
_UN_FACTOR = {"2A": 1.0, "3A": 0.75, "2B": 1.30, "3B": 0.975}

CLASES_POR_FAMILIA = {"iso_metrica": CLASES_ISO965, "unificada": CLASES_UN}
CLASE_AUTOMATICA = {"iso_metrica": ("6H", "6g"), "unificada": ("2B", "2A")}   # (interior, exterior), como Fusion


def _r4(x):
    """Redondeo de las tablas de ASME B1.1 (pulgadas): a 5 decimales y después a 4, «mitad hacia arriba».
    Con este redondeo salen exactos los límites publicados de 1/4-20 UNC, 1/2-13 UNC y 1/4-28 UNF (clases 2A, 3A,
    2B y 3B); con un solo redondeo, la 2B de 1/4-20 da 0.2223 en vez de 0.2224."""
    cinco = Decimal(repr(x)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
    return float(cinco.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _clave_paso(paso):
    return round(float(paso), 4)


def _limites_iso965(diametro, paso, clase):
    d, p = float(diametro), _clave_paso(paso)
    td2 = _ISO965_TD2.get((round(d, 4), p))
    if td2 is None or p not in _ISO965_G:
        raise geo.ErrorGeometria(f"No hay datos verificados de ISO 965-1 para M{d:g}x{p:g} (se cargaron M3 a M39 "
                                 "gruesa y algunas finas): usá la rosca sin clase.")
    h = math.sqrt(3) / 2 * p                        # altura del triángulo fundamental (ISO 68-1)
    d2, d1 = d - 0.75 * h, d - 1.25 * h             # diámetros de flancos y menor básicos (ISO 724)
    interna = CLASES_ISO965[clase]
    if interna:
        ei = _ISO965_G[p] if clase == "6G" else 0
        return {"diametro_mayor": [d + ei / 1000, None],
                "diametro_flancos": [d2 + ei / 1000, d2 + (ei + td2[1]) / 1000],
                "diametro_menor": [d1 + ei / 1000, d1 + (ei + _ISO965_TD1[p]) / 1000],
                "desviacion_fundamental": ei / 1000}
    es = -_ISO965_G[p] if clase == "6g" else 0
    return {"diametro_mayor": [d + (es - _ISO965_TD[p]) / 1000, d + es / 1000],
            "diametro_flancos": [d2 + (es - td2[0]) / 1000, d2 + es / 1000],
            "diametro_menor": [None, None],
            "desviacion_fundamental": es / 1000}


def _limites_un(diametro, paso, clase):
    """ASME B1.1 en pulgadas (redondeo a 4 decimales como sus tablas), devuelto en mm."""
    D, P = float(diametro) / 25.4, float(paso) / 25.4
    td2_2a = 0.0015 * D ** (1 / 3) + 0.0015 * math.sqrt(D) + 0.015 * P ** (2 / 3)   # largo de enganche = D
    holgura = _r4(0.3 * td2_2a)                     # allowance de la 2A (la 3A no tiene)
    E = _r4(D - 0.649519 * P)                       # diámetro de flancos básico
    tol = _r4(_UN_FACTOR[clase] * td2_2a)
    mm = 25.4
    if CLASES_UN[clase]:
        menor = _r4(D - 1.082532 * P)
        return {"diametro_mayor": [D * mm, None], "diametro_flancos": [E * mm, (E + tol) * mm],
                "diametro_menor": [menor * mm, None], "desviacion_fundamental": 0.0}
    es = holgura if clase == "2A" else 0.0
    mayor_max = _r4(D - es)
    return {"diametro_mayor": [(mayor_max - _r4(0.060 * P ** (2 / 3))) * mm, mayor_max * mm],
            "diametro_flancos": [(E - es - tol) * mm, (E - es) * mm], "diametro_menor": [None, None],
            "desviacion_fundamental": -es * mm}


def limites_rosca(familia, diametro, paso, clase):
    """Diámetros límite (mm) de una rosca con su clase: ISO 965-1 (6H, 6G, 6g, 6h) para la métrica y ASME B1.1
    (2A, 3A, 2B, 3B) para la unificada. Devuelve {"clase", "interna", "norma", "diametro_mayor": [mín, máx],
    "diametro_flancos": [...], "diametro_menor": [...], "desviacion_fundamental"}; None = la norma no lo
    limita (o no se cargó). Ej.: M10×1,5 6g → diámetro mayor [9.732, 9.968]."""
    clases = CLASES_POR_FAMILIA.get(familia)
    if not clases:
        raise geo.ErrorGeometria("Esta familia de rosca no tiene clases cargadas (solo la métrica ISO y la unificada).")
    if clase not in clases:
        raise geo.ErrorGeometria(f"Clase «{clase}» desconocida para esta rosca: hay {', '.join(clases)}.")
    lim = _limites_iso965(diametro, paso, clase) if familia == "iso_metrica" else _limites_un(diametro, paso, clase)
    for k in ("diametro_mayor", "diametro_flancos", "diametro_menor"):
        lim[k] = [None if v is None else round(v, 4) for v in lim[k]]
    lim["desviacion_fundamental"] = round(lim["desviacion_fundamental"], 4)
    return dict(lim, clase=clase, interna=clases[clase],
                norma="ISO 965-1" if familia == "iso_metrica" else "ASME B1.1")


def resolver_clase(familia, diametro, paso, clase, interna):
    """Clase efectiva de una rosca: "" = perfil básico; "auto" = la de Fusion por defecto (6H/6g, 2B/2A) si hay
    datos para ese tamaño. Devuelve (clase, aviso o None). Una clase de exterior en un agujero (o al revés)
    es un error."""
    clase = (clase or "").strip()
    if not clase:
        return "", None
    clases = CLASES_POR_FAMILIA.get(familia, {})
    if clase.lower() in ("auto", "automatica", "automática"):
        if familia not in CLASE_AUTOMATICA:
            return "", None
        clase = CLASE_AUTOMATICA[familia][0 if interna else 1]
        try:
            limites_rosca(familia, diametro, paso, clase)
        except geo.ErrorGeometria:
            return "", (f"Sin datos verificados de tolerancia para este tamaño: se modela el perfil básico, sin la "
                        f"clase {clase}.")
        return clase, None
    if clase not in clases:
        disponibles = ", ".join(clases) or "ninguna"
        raise geo.ErrorGeometria(f"Clase «{clase}» desconocida para esta rosca (hay: {disponibles}).")
    if clases[clase] != bool(interna):
        lado = "interior (agujero)" if interna else "exterior (eje)"
        otras = ", ".join(k for k, v in clases.items() if v == bool(interna))
        raise geo.ErrorGeometria(f"La clase {clase} no es de rosca {lado}: usá {otras}.")
    limites_rosca(familia, diametro, paso, clase)              # sin datos para el tamaño: error claro
    return clase, None


def desfases_rosca(familia, diametro, paso, clase, interna, diametro_flancos_basico, diametro_menor_basico):
    """Corrimientos radiales (mm) para MODELAR la rosca al centro de la zona de tolerancia de su clase:
    {"flancos": cuánto se corren los flancos hacia afuera del material (+ = más juego), "menor": cuánto crece el
    radio del agujero (solo interior), "limites": limites_rosca o None}. Clase "" → todo 0."""
    if not clase:
        return {"flancos": 0.0, "menor": 0.0, "limites": None}
    lim = limites_rosca(familia, diametro, paso, clase)
    f0, f1 = lim["diametro_flancos"]
    medio = (f0 + f1) / 2
    if interna:
        m0, m1 = lim["diametro_menor"]
        menor = ((m0 + m1) / 2 - diametro_menor_basico) / 2 if m1 is not None else (m0 - diametro_menor_basico) / 2
        return {"flancos": (medio - diametro_flancos_basico) / 2, "menor": menor, "limites": lim}
    return {"flancos": (diametro_flancos_basico - medio) / 2, "menor": 0.0, "limites": lim}
