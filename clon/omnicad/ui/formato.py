# -*- coding: utf-8 -*-
"""
Formato de números en pantalla según Preferencias → Visualización de unidad y valor
(precisión general, precisión angular y "ocultar ceros finales", como en Fusion).
Es estado de la interfaz: la ventana lo configura al aplicar las preferencias.
"""
_config = {"lineal": 3, "angular": 1, "ocultar_ceros": True}


def configurar(lineal=3, angular=1, ocultar_ceros=True):
    _config.update(lineal=int(lineal), angular=int(angular), ocultar_ceros=bool(ocultar_ceros))


def numero(valor, angular=False, miles=False):
    decimales = _config["angular" if angular else "lineal"]
    texto = f"{valor:,.{decimales}f}" if miles else f"{valor:.{decimales}f}"
    if _config["ocultar_ceros"] and decimales > 0:
        texto = texto.rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto
