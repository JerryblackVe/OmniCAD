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

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from ..timeline import entidades as ent

NOMBRES = {"seccion": "Análisis de sección", "cebra": "Análisis cebra", "mapa_entorno": "Análisis de mapas de entorno",
           "desmoldeo": "Análisis de ángulo de desmoldeo", "curvatura": "Análisis del mapa de curvatura",
           "peine": "Análisis de curvatura en peine", "isocurva": "Análisis de la isocurva",
           "accesibilidad": "Análisis de accesibilidad", "radio_minimo": "Análisis de radio mínimo"}
_cache = {}


def _cuerpos(params, estado):
    ids = params.get("cuerpos") or [c for c, cu in estado.cuerpos.items() if getattr(cu, "tipo", "solido") != "malla"]
    return {c: estado.cuerpos[c].forma for c in ids if c in estado.cuerpos}


def _direccion(params, estado, defecto=(0.0, 0.0, 1.0)):
    if not params.get("direccion"):
        return np.array(defecto, float)
    e = ent.resolver(params["direccion"], estado)
    d = ent.direccion(e)
    if e.tipo == "cara":
        d = -d                              # una cara: la extracción es hacia afuera del material que limita
    return -d if params.get("invertir") else d


def _con_cache(clave, funcion):
    if clave not in _cache:
        if len(_cache) > 200:
            _cache.clear()
        _cache[clave] = funcion()
    return _cache[clave]


def calcular(tipo, params, estado):
    salida = {"mallas": {}, "colores": None, "capas": [], "cortes": []}
    if tipo == "cebra":
        frecuencia, vertical = int(params.get("frecuencia", 8)), params.get("orientacion") == "vertical"
        salida["colores"] = lambda n, d: an.colores_cebra(n, d, frecuencia=frecuencia, vertical=vertical)
        return salida
    if tipo == "mapa_entorno":
        salida["colores"] = lambda n, d: an.colores_mapa_entorno(n, d)
        return salida
    cuerpos = _cuerpos(params, estado)
    if tipo == "seccion":
        e = ent.resolver(params["plano"], estado)
        plano = ent.como_plano(e)
        d = float(params.get("desfase_mm", 0.0))
        plano = plano.desplazado(d)
        if params.get("invertir"):
            plano = geo.Plano.desde_marco(plano.origen, -plano.normal, plano.u)
        salida["cortes"].append((plano.normal, plano.origen))
        for cid, forma in cuerpos.items():
            datos = _con_cache(("seccion", id(forma), tuple(plano.origen), tuple(plano.normal)),
                               lambda f=forma: an.seccion(f, plano))
            tris = np.asarray(datos["triangulos"], np.float32).reshape(-1, 3)
            if len(tris):
                salida["capas"].append(("tris", tris, (0.85, 0.30, 0.25), 0.85))
            from .visor3d import _segmentos
            salida["capas"].append(("lineas", _segmentos(datos["polilineas"]), (0.15, 0.15, 0.15), 2.0))
        return salida
    for cid, forma in cuerpos.items():
        if tipo == "desmoldeo":
            d = _direccion(params, estado)
            a0, a1 = float(params.get("angulo_min", 0.0)), float(params.get("angulo_max", 3.0))
            v, n, c = _con_cache(("desmoldeo", id(forma), tuple(d), a0, a1),
                                 lambda f=forma, d=d, a0=a0, a1=a1: an.colores_desmoldeo(f, d, a0, a1))
        elif tipo == "curvatura":
            t = params.get("tipo_curvatura", "gaussiana")
            v, n, c = _con_cache(("curvatura", id(forma), t), lambda f=forma, t=t: an.colores_curvatura(f, tipo=t))
        elif tipo == "accesibilidad":
            d = _direccion(params, estado)
            v, n, c = _con_cache(("accesibilidad", id(forma), tuple(d)),
                                 lambda f=forma, d=d: an.colores_accesibilidad(f, d))
        elif tipo == "radio_minimo":
            r = float(params.get("radio", 3.0))
            v, n, c = _con_cache(("radio_minimo", id(forma), r), lambda f=forma, r=r: an.colores_radio_minimo(f, r))
        elif tipo == "isocurva":
            datos = _con_cache(("isocurva", id(forma), int(params.get("densidad", 10))),
                               lambda f=forma: an.isocurvas(f, n_u=int(params.get("densidad", 10)),
                                                            n_v=int(params.get("densidad", 10))))
            from .visor3d import _segmentos
            salida["capas"].append(("lineas", _segmentos(datos["u"]), (0.85, 0.25, 0.25), 1.2))
            salida["capas"].append(("lineas", _segmentos(datos["v"]), (0.25, 0.45, 0.90), 1.2))
            continue
        elif tipo == "peine":
            continue
        else:
            raise ValueError(f"Análisis desconocido: {tipo}")
        salida["mallas"][cid] = (np.asarray(v, np.float32).reshape(-1, 3), np.asarray(n, np.float32).reshape(-1, 3),
                                 np.asarray(c, np.float32).reshape(-1, 3))
    if tipo == "peine":
        aristas = [ent.resolver(r, estado).forma for r in params.get("aristas") or []]
        if aristas:
            datos = an.peine_curvatura(aristas, densidad=int(params.get("densidad", 30)),
                                       escala=float(params.get("escala", 1.0)))
            puas = np.asarray(datos["puas"], np.float32).reshape(-1, 3)
            from .visor3d import _segmentos
            salida["capas"].append(("lineas", puas, (0.55, 0.30, 0.85), 1.0))
            salida["capas"].append(("lineas", _segmentos(datos["envolventes"]), (0.85, 0.30, 0.65), 1.5))
    return salida


def combinar(resultados):
    """Junta varios análisis visibles en una sola descripción para el visor."""
    total = {"mallas": {}, "colores": None, "capas": [], "cortes": []}
    for r in resultados:
        total["mallas"].update(r["mallas"])
        total["capas"].extend(r["capas"])
        total["cortes"].extend(r["cortes"])
        total["colores"] = r["colores"] or total["colores"]
    return total


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
