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


def aplicar(visor, datos):
    visor.mallas_analisis = datos["mallas"]
    visor.funcion_colores = datos["colores"]
    visor._cache_dinamico = {}
    visor.cortes = datos["cortes"]
    visor.set_capa("analisis", datos["capas"])
