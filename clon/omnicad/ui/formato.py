# -*- coding: utf-8 -*-
"""
Formato de números en pantalla según Preferencias → Visualización de unidad y valor
(precisión general, precisión angular y "ocultar ceros finales", como en Fusion).
Es estado de la interfaz: la ventana lo configura al aplicar las preferencias.
"""
from ..timeline.parametros import LONGITUDES as _FACTOR_LONGITUD, MASAS as _FACTOR_MASA

_config = {"lineal": 3, "angular": 1, "ocultar_ceros": True}


def configurar(lineal=3, angular=1, ocultar_ceros=True):
    _config.update(lineal=int(lineal), angular=int(angular), ocultar_ceros=bool(ocultar_ceros))


def numero(valor, angular=False, miles=False):
    decimales = _config["angular" if angular else "lineal"]
    texto = f"{valor:,.{decimales}f}" if miles else f"{valor:.{decimales}f}"
    if _config["ocultar_ceros"] and decimales > 0:
        texto = texto.rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto


# ---------------------------------------------------------------- unidades de pantalla del documento
# El modelo va siempre en mm y g; el documento elige con qué unidades se MUESTRAN las medidas (menú «Unidades»).
# La ventana lo configura al abrir un documento y al cambiar sus unidades.
_unidades = {"longitud": "mm", "masa": "g"}
_POTENCIAS = {1: "", 2: "²", 3: "³"}


def configurar_unidades(longitud="mm", masa="g"):
    _unidades.update(longitud=longitud if longitud in _FACTOR_LONGITUD else "mm", masa=masa if masa in _FACTOR_MASA else "g")


def unidad_longitud():
    return _unidades["longitud"]


def unidad_masa():
    return _unidades["masa"]


def sufijo(potencia=1, caret=False):
    """La unidad de longitud elevada a `potencia` (1, 2 o 3): «mm», «in²» o «mm^3» (con caret)."""
    u = _unidades["longitud"]
    return u if potencia == 1 else (f"{u}^{potencia}" if caret else u + _POTENCIAS[potencia])


def longitud(mm, potencia=1):
    """Un valor en mm (potencia 1), mm² (2) o mm³ (3) pasado a la unidad de longitud del documento."""
    return mm / _FACTOR_LONGITUD[_unidades["longitud"]] ** potencia


def masa(gramos):
    """Gramos pasados a la unidad de masa del documento."""
    return gramos / _FACTOR_MASA[_unidades["masa"]]


def tooltip_valor(valor, angulo=False, escalar=False):
    """Globo de un campo de expresión: «= 25.4 mm»; con otra unidad en el documento, «= 1 in (25.4 mm)»."""
    if angulo:
        return f"= {valor:.4g}°"
    if escalar:
        return f"= {valor:.4g}"
    if _unidades["longitud"] == "mm":
        return f"= {valor:.4g} mm"
    return f"= {longitud(valor):.4g} {sufijo()} ({valor:.4g} mm)"
