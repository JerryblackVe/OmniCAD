# -*- coding: utf-8 -*-
"""
Cómo se dibujan los análisis de INSPECCIONAR en la vista 3D (sección, cebra, mapa de entorno, desmoldeo,
curvatura, peine, isocurvas, accesibilidad y radio mínimo).

Un análisis es {"tipo", "params"} (los guarda el documento, como la carpeta «Análisis» del navegador
de Fusion). `calcular` lo convierte en lo que el visor sabe dibujar:
  - "mallas": id de cuerpo → (vértices, normales, colores) que reemplazan su sombreado;
  - "colores": función (normales, dirección de vista) → colores, para los que dependen de la cámara;
  - "capas": primitivas extra (líneas, triángulos, puntos);
  - "cortes": planos de recorte [(normal, punto)].
Los resultados se guardan en caché por forma: recalcular un mapa de colores tarda hasta medio segundo.
También arma las cotas guía de Medir (`cota_guia`, `cota_diametro`): líneas con flechas y la etiqueta del valor.
"""
import numpy as np

from ..timeline.analisis_vista import _cache, _con_cache, calcular, combinar  # noqa: F401 — los usa la ventana y las pruebas

# ---------------------------------------------------------------- cotas guía de Medir
COLOR_COTA = (0.95, 0.55, 0.10)          # naranja, como la cota de Medir de Fusion
COLOR_COTA_PREVIA = (0.45, 0.70, 1.0)    # celeste: lo que se mediría con lo que está bajo el cursor


def _perpendicular(d, vista=None):
    """Unitario perpendicular a `d`, en el plano de la pantalla si se conoce la dirección de la vista."""
    d = np.asarray(d, float)
    for candidato in ([vista] if vista is not None else []) + [(0.0, 0.0, 1.0), (1.0, 0.0, 0.0)]:
        w = np.cross(d, np.asarray(candidato, float))
        n = float(np.linalg.norm(w))
        if n > 1e-6:
            return w / n
    return np.array([0.0, 1.0, 0.0])


def _flecha(punta, sentido, ancho, largo, color):
    """Punta de flecha plana (triángulo + contorno en líneas, que se ve aunque la tape el modelo)."""
    base = punta - sentido * largo
    a, b = base + ancho * largo * 0.35, base - ancho * largo * 0.35
    return [("tris", np.array([punta, a, b], float), color, 1.0),
            ("lineas", np.array([punta, a, punta, b, a, b], float), color, 2.0)]


def cota_guia(pa, pb, texto, tam=3.0, vista=None, color=COLOR_COTA):
    """Cota guía entre dos puntos 3D, como la que dibuja Medir de Fusion: línea con flechas en los dos
    extremos y el valor en una etiqueta sobre el punto medio. `tam`: largo de cada flecha en mm (el que da
    ~12 px en pantalla); `vista`: dirección hacia el ojo, para que las flechas queden de frente. Si la
    distancia es corta para dos flechas adentro, van afuera apuntando hacia adentro.
    Devuelve {"capas": primitivas para `visor.set_capa`, "etiquetas": [(punto, texto)] para `set_etiquetas`}."""
    pa, pb = np.asarray(pa, float).reshape(3), np.asarray(pb, float).reshape(3)
    largo = float(np.linalg.norm(pb - pa))
    medio = (pa + pb) / 2
    if largo < 1e-9:                                  # se tocan: solo el punto y el valor
        return {"capas": [("puntos", np.array([pa]), color, 8)], "etiquetas": [(medio, texto)]}
    d = (pb - pa) / largo
    w = _perpendicular(d, vista)
    tam = float(tam) if tam and tam > 0 else largo * 0.15
    capas = [("lineas", np.array([pa, pb]), color, 2.0), ("puntos", np.array([pa, pb]), color, 7)]
    if largo >= 2.4 * tam:                            # flechas adentro, con la punta en cada extremo
        capas += _flecha(pa, -d, w, tam, color) + _flecha(pb, d, w, tam, color)
    else:                                             # corta: flechas afuera que apuntan hacia los extremos
        capas.append(("lineas", np.array([pa - d * tam * 1.8, pa, pb, pb + d * tam * 1.8]), color, 2.0))
        capas += _flecha(pa, d, w, tam, color) + _flecha(pb, -d, w, tam, color)
    return {"capas": capas, "etiquetas": [(medio, texto)]}


def cota_diametro(centro, radio, eje, texto, tam=3.0, vista=None, color=COLOR_COTA):
    """Cota de diámetro de un círculo o un cilindro: atraviesa el centro, perpendicular al eje (y de frente a la
    cámara si se puede), con las flechas tocando el borde."""
    centro = np.asarray(centro, float).reshape(3)
    eje = np.asarray(eje if eje is not None else (0.0, 0.0, 1.0), float)
    d = _perpendicular(eje, vista)
    return cota_guia(centro - d * float(radio), centro + d * float(radio), texto, tam, vista, color)


def aplicar(visor, datos):
    visor.mallas_analisis = datos["mallas"]
    visor.funcion_colores = datos["colores"]
    visor._cache_dinamico = {}
    visor.cortes = datos["cortes"]
    visor.set_capa("analisis", datos["capas"])
