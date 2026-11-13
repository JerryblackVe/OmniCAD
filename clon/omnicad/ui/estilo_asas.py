# -*- coding: utf-8 -*-
"""
P-149 · Estilo de lo que se dibuja sobre el visor (Preferencias › Asas y superposiciones): color, tamaño y opacidad
de cada grupo. Sin Qt: lo leen `manipuladores.py`, `visor3d.py`, `render.py` y la ventana, y lo ven también la API
(`api/herramientas_preferencias.py`) y las pruebas. Es la ÚNICA tabla de colores de fábrica de esos dibujos.

Claves de preferencias (una por grupo y propiedad que le aplique):
  asas/<grupo>_color         «#rrggbb» o vacío (el de fábrica)
  asas/<grupo>_tamano_pct    50 a 200: 100 es el tamaño de siempre
  asas/<grupo>_opacidad_pct  10 a 100: 100 es opaco
"""

# grupo → (título, color de fábrica, ¿tiene tamaño?, ¿tiene opacidad?, qué es)
GRUPOS = {
    "flechas": ("Flechas de las asas", "#ffb400", True, True,
                "Las flechas de distancia y las asas de ángulo de los comandos."),
    "anillo": ("Anillo del ángulo", "#2c4157", True, True,
               "El anillo de la conicidad de Extruir, del giro del Barrido y de Revolución."),
    "puntos": ("Puntos de las asas", "#ffb400", True, True,
               "Los discos y puntos que se arrastran (radios, cantidades, recorridos)."),
    "cajas": ("Cajas de valor", "#ffb400", True, False,
              "La caja que sale junto al asa: color del borde al escribir y tamaño de la letra."),
    "previa": ("Vista previa del cuerpo nuevo", "#9eccff", False, True,
               "El cuerpo que se ve antes de aceptar un comando."),
    "previa_corte": ("Vista previa de lo que se corta", "#e02e26", False, True,
                     "Lo que se va a cortar (agujeros)."),
    "seleccion": ("Selección", "#2680ff", False, True, "Lo que está elegido en el visor."),
    "resaltado": ("Resaltado al pasar el cursor", "#73b3ff", False, True,
                  "Lo que se ilumina bajo el cursor antes de elegirlo."),
    "viewcube": ("ViewCube (cara resaltada)", "#8fc3ee", False, True,
                 "La cara del cubo bajo el cursor. Se conecta cuando entre el ViewCube nuevo (CF-15)."),
}
TAMANO = (50, 200)
OPACIDAD = (10, 100)


def clave(grupo, propiedad):
    return f"asas/{grupo}_{propiedad}"


def _defectos():
    salida = {}
    for grupo, (_t, _c, tam, op, _d) in GRUPOS.items():
        salida[clave(grupo, "color")] = ""
        if tam:
            salida[clave(grupo, "tamano_pct")] = 100
        if op:
            salida[clave(grupo, "opacidad_pct")] = 100
    return salida


DEFECTOS = _defectos()              # valores de fábrica de todas las claves (Preferencias y API los toman de acá)
CLAVES = tuple(DEFECTOS)
_ACTUAL = dict(DEFECTOS)            # lo que está aplicado; `aplicar` lo reemplaza desde las preferencias


def aplicar(prefs):
    """Toma los valores de las preferencias (objeto con `prefs[clave]`)."""
    for k in CLAVES:
        _ACTUAL[k] = prefs[k]


def hex_a_rgb(hexa):
    h = hexa.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def fabrica(grupo):
    """Color de fábrica del grupo, (r, g, b) de 0 a 1."""
    return hex_a_rgb(GRUPOS[grupo][1])


def rgb(grupo):
    """Color vigente del grupo: el elegido, o el de fábrica si está vacío o no es un «#rrggbb» válido."""
    elegido = str(_ACTUAL.get(clave(grupo, "color"), ""))
    try:
        return hex_a_rgb(elegido) if len(elegido) == 7 and elegido[0] == "#" else fabrica(grupo)
    except ValueError:
        return fabrica(grupo)


def propio(grupo):
    """¿El grupo tiene un color elegido (distinto del de fábrica)?"""
    return rgb(grupo) != fabrica(grupo)


def tamano(grupo):
    """Factor de tamaño del grupo: 1.0 es el de siempre."""
    return _entre(_ACTUAL.get(clave(grupo, "tamano_pct"), 100), *TAMANO) / 100


def opacidad(grupo):
    """Opacidad del grupo, de 0.1 a 1.0."""
    return _entre(_ACTUAL.get(clave(grupo, "opacidad_pct"), 100), *OPACIDAD) / 100


def _entre(v, minimo, maximo):
    try:
        return max(minimo, min(maximo, int(v)))
    except (TypeError, ValueError):
        return 100
