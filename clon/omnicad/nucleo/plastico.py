# -*- coding: utf-8 -*-
"""
Reglas de plástico [Plastic > Setup > Assign / Manage Plastic Rules de Fusion]: un conjunto de valores que se
asigna a un componente y fija el material físico y los valores de diseño del plástico inyectado.

Una regla es un dict (va a JSON): nombre, material (de la tabla de materiales, o None), espesor de pared, ángulo de
desmoldeo y radio nominal (los valores físicos que usan Extruir, Nervio, Red, Saliente, Vaciado, Desmoldeo…), y los
valores de Design Advice: rango de espesor [mínimo, máximo], variación de espesor (%), ángulo de desmoldeo mínimo y
umbral de filo. Hay reglas de fábrica y reglas propias, que se guardan en `reglas_plastico.json` (carpeta de datos de
la app, o la variable OMNICAD_REGLAS_PLASTICO) como las de chapa.
"""
import math
import os
from pathlib import Path

from . import geometria as geo
from .chapa import escribir_biblioteca_json, leer_biblioteca_json

VAR_REGLAS = "OMNICAD_REGLAS_PLASTICO"      # otra ruta para el .json (pruebas, carpeta compartida)
REGLA_DEFECTO = "ABS 2 mm"
CAMPOS = ("nombre", "material", "espesor", "angulo_desmoldeo", "radio_nominal", "espesor_min", "espesor_max",
          "variacion_espesor", "angulo_minimo", "umbral_filo")


def _fabrica(nombre, material, espesor, angulo=1.0, variacion=25.0):
    return {"nombre": nombre, "material": material, "espesor": espesor, "angulo_desmoldeo": angulo,
            "radio_nominal": espesor / 2, "espesor_min": round(espesor * 0.5, 4), "espesor_max": round(espesor * 1.5, 4),
            "variacion_espesor": variacion, "angulo_minimo": 0.5, "umbral_filo": round(espesor * 0.25, 4)}


REGLAS = {r["nombre"]: r for r in (
    _fabrica("ABS 2 mm", "ABS", 2.0), _fabrica("Policarbonato 2.5 mm", "Policarbonato", 2.5),
    _fabrica("Polipropileno 1.5 mm", "Polipropileno", 1.5, angulo=1.5), _fabrica("Nylon 2 mm", "Nylon", 2.0),
    _fabrica("Acrílico (PMMA) 3 mm", "Acrílico (PMMA)", 3.0), _fabrica("POM (acetal) 2 mm", "POM (acetal)", 2.0))}
REGLAS_USUARIO = {}


def ruta_reglas_propias():
    """El .json de las reglas propias: la variable OMNICAD_REGLAS_PLASTICO o «reglas_plastico.json» en la carpeta de datos."""
    from .. import carpeta_datos
    return Path(os.environ[VAR_REGLAS]) if os.environ.get(VAR_REGLAS) else carpeta_datos() / "reglas_plastico.json"


def _numero(d, clave, minimo=None, maximo=None, defecto=None):
    valor = d.get(clave, defecto)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise geo.ErrorGeometria(f"«{clave}» tiene que ser un número finito (llegó {valor!r}).")
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise geo.ErrorGeometria(f"«{clave}» tiene que estar entre {minimo} y {maximo} (llegó {valor:g}).")
    return float(valor)


def definicion(**datos):
    """Valida una regla y completa lo que falta con valores que siguen al espesor, como las de fábrica. Lanza
    `geo.ErrorGeometria` con un mensaje claro si algo no sirve."""
    nombre = str(datos.get("nombre") or "").strip()
    if not nombre:
        raise geo.ErrorGeometria("La regla necesita un nombre.")
    if len(nombre) > 80:
        raise geo.ErrorGeometria("El nombre de la regla es demasiado largo (máximo 80 caracteres).")
    espesor = _numero(datos, "espesor", 0.01, 100)
    d = {"nombre": nombre, "material": datos.get("material") or None, "espesor": espesor,
         "angulo_desmoldeo": _numero(datos, "angulo_desmoldeo", 0, 45, 1.0),
         "radio_nominal": _numero(datos, "radio_nominal", 0, 1000, espesor / 2),
         "espesor_min": _numero(datos, "espesor_min", 0.001, 100, round(espesor * 0.5, 4)),
         "espesor_max": _numero(datos, "espesor_max", 0.001, 100, round(espesor * 1.5, 4)),
         "variacion_espesor": _numero(datos, "variacion_espesor", 0, 100, 25.0),
         "angulo_minimo": _numero(datos, "angulo_minimo", 0, 45, 0.5),
         "umbral_filo": _numero(datos, "umbral_filo", 0, 100, round(espesor * 0.25, 4))}
    if d["espesor_min"] > d["espesor_max"]:
        raise geo.ErrorGeometria("El espesor mínimo no puede superar al máximo.")
    return d


def regla(nombre):
    """La regla (de fábrica o propia) con ese nombre, sin distinguir mayúsculas. Lanza si no existe."""
    texto = str(nombre or "").strip()
    for tabla in (REGLAS, REGLAS_USUARIO):
        for n, d in tabla.items():
            if n.casefold() == texto.casefold():
                return dict(d)
    raise geo.ErrorGeometria(f"No existe la regla de plástico «{texto}».")


def definir_regla(datos, guardar=True):
    """Suma (o reemplaza) una regla propia. No pisa las de fábrica. Devuelve la regla validada."""
    d = definicion(**datos)
    if any(d["nombre"].casefold() == n.casefold() for n in REGLAS):
        raise geo.ErrorGeometria(f"«{d['nombre']}» es una regla de fábrica: elegí otro nombre para la regla propia.")
    REGLAS_USUARIO[d["nombre"]] = d
    if guardar:
        escribir_biblioteca_json(ruta_reglas_propias(), "reglas", d["nombre"], d)
    return d


def quitar_regla(nombre, guardar=True):
    """Saca una regla propia de la biblioteca (los componentes que ya la tienen asignada conservan su copia)."""
    if nombre not in REGLAS_USUARIO:
        raise geo.ErrorGeometria(f"No hay una regla propia llamada «{nombre}».")
    del REGLAS_USUARIO[nombre]
    if guardar:
        escribir_biblioteca_json(ruta_reglas_propias(), "reglas", nombre, None)


def cargar_reglas_propias(ruta=None):
    """Lee las reglas propias del .json (las inválidas se saltean). Devuelve los nombres cargados."""
    cargadas = []
    for nombre, d in leer_biblioteca_json(ruta or ruta_reglas_propias(), "reglas").items():
        try:
            d = definicion(**dict(d, nombre=nombre))
        except (geo.ErrorGeometria, TypeError):
            continue
        if nombre not in REGLAS:
            REGLAS_USUARIO[nombre] = d
            cargadas.append(nombre)
    return cargadas


try:
    cargar_reglas_propias()
except Exception:  # noqa: BLE001 — una biblioteca dañada no tiene que impedir abrir la app
    pass
