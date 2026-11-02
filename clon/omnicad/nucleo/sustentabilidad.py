# -*- coding: utf-8 -*-
"""INSPECCIONAR › Sustainability Insights, versión local: estima el CO₂ de una pieza por su material, sin cuenta ni internet.

En Fusion es un complemento de un tercero. Acá el cálculo está a la vista: masa × kg de CO₂e por kg de material (de la
materia prima a la salida de fábrica; no cuenta la fabricación de la pieza). Cada factor lleva su fuente y un material sin
fuente queda vacío. Región y país se guardan para el informe: todavía no cambian el resultado.
"""
import json
import math
import os
from pathlib import Path

from . import geometria as geo
from .chapa import escribir_biblioteca_json, leer_biblioteca_json

VAR_MATERIALES = "OMNICAD_MATERIALES_CO2"
TOPE_IMPORTAR = 1_000_000                 # bytes: un .json de materiales es de otro; no se lee entero si es enorme
_ICE2 = "ICE V2.0 (Circular Ecology, tablas resumen)"
_ICE16 = "ICE v1.6a (Univ. de Bath)"
_PTFE = "Carbonfact (base propia, sector textil)"
PERSONALIZADO = "Personalizado"

# Nombre → kg CO₂e por kg, densidad en g/cm³ y fuente del factor (consultadas el 2026-11-01; enlaces en
# docs/auditorias/inspeccionar_2026-11-01.md).
MATERIALES = {
    "ABS": {"co2": 3.76, "densidad": 1.06, "fuente": _ICE2},
    "ASA": {"co2": None, "densidad": 1.07, "fuente": ""},
    "Aluminio": {"co2": 9.16, "densidad": 2.70, "fuente": _ICE2},
    "Cobre": {"co2": 2.71, "densidad": 8.96, "fuente": _ICE2 + ", tubo y chapa UE"},
    "Nylon": {"co2": 9.14, "densidad": 1.14, "fuente": _ICE2 + ", nylon 6"},
    "PTFE": {"co2": 133.0, "densidad": 2.20, "fuente": _PTFE},
    "PVC": {"co2": 3.10, "densidad": 1.40, "fuente": _ICE2},
    "Policarbonato": {"co2": 7.62, "densidad": 1.20, "fuente": _ICE2},
    "Polietileno": {"co2": 2.54, "densidad": 0.95, "fuente": _ICE2},
    "Polipropileno": {"co2": 4.49, "densidad": 0.90, "fuente": _ICE2 + ", inyección"},
    "Acero inoxidable": {"co2": 6.15, "densidad": 8.00, "fuente": _ICE16},
    "Acero": {"co2": 1.77, "densidad": 7.85, "fuente": _ICE16},
    "Titanio": {"co2": 31.55, "densidad": 4.51, "fuente": _ICE2 + ", virgen: punto medio de 20,6 a 42,5 (datos viejos)"},
}
REGIONES = {
    "África": ("Egipto", "Kenia", "Marruecos", "Nigeria", "Sudáfrica"),
    "Asia": ("China", "Corea del Sur", "India", "Indonesia", "Japón", "Tailandia", "Turquía", "Vietnam"),
    "Australia": ("Australia", "Nueva Zelanda"),
    "Europa": ("Alemania", "España", "Francia", "Italia", "Países Bajos", "Polonia", "Reino Unido", "Suecia"),
    "Norteamérica": ("Canadá", "Estados Unidos", "México"),
    "Sudamérica": ("Argentina", "Brasil", "Chile", "Colombia", "Perú", "Uruguay"),
}


def ruta_materiales():
    """El .json de los materiales propios: la variable OMNICAD_MATERIALES_CO2 o «sostenibilidad.json» en la carpeta de
    datos de la app (se comparte entre documentos, como en Fusion)."""
    from .. import carpeta_datos
    return Path(os.environ[VAR_MATERIALES]) if os.environ.get(VAR_MATERIALES) else carpeta_datos() / "sostenibilidad.json"


def materiales_propios():
    return leer_biblioteca_json(ruta_materiales(), "materiales")


def _positivo(valor, que):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
        raise geo.ErrorGeometria(f"{que} tiene que ser un número mayor que cero: llegó {valor!r}.")
    return float(valor)


def _validado(nombre, co2, densidad, parecido=""):
    nombre = str(nombre).strip()
    if not nombre:
        raise geo.ErrorGeometria("El material necesita un nombre.")
    if nombre in MATERIALES or nombre == PERSONALIZADO:
        raise geo.ErrorGeometria(f"«{nombre}» es un material de fábrica: elegí otro nombre.")
    if parecido and (not isinstance(parecido, str) or parecido not in MATERIALES):       # puede venir de un archivo de otro
        raise geo.ErrorGeometria(f"Material más parecido desconocido: «{parecido}».")
    return nombre, {"co2": _positivo(co2, "CO2 por kg"), "densidad": _positivo(densidad, "La densidad"),
                    "parecido": parecido, "fuente": "Dato propio"}


def definir_material(nombre, co2, densidad, parecido=""):
    """Suma (o reemplaza) un material propio; devuelve su nombre. Pestaña Materiales personalizados › Crear material."""
    nombre, datos = _validado(nombre, co2, densidad, parecido)
    escribir_biblioteca_json(ruta_materiales(), "materiales", nombre, datos)
    return nombre


def borrar_material(nombre):
    if nombre not in materiales_propios():
        raise geo.ErrorGeometria(f"No existe el material propio «{nombre}».")
    escribir_biblioteca_json(ruta_materiales(), "materiales", nombre, None)


def exportar_materiales(ruta):
    """Exportar materiales: el mismo formato que el archivo de la app. Devuelve cuántos se escribieron."""
    propios = materiales_propios()
    Path(ruta).write_text(json.dumps({"version": 1, "materiales": propios}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(propios)


def importar_materiales(ruta):
    """Suma los materiales de un archivo; lo que no se pueda leer se saltea. Devuelve (importados, salteados)."""
    ruta = Path(ruta)
    if ruta.stat().st_size > TOPE_IMPORTAR:
        raise geo.ErrorGeometria("El archivo de materiales es demasiado grande.")
    importados, salteados = [], []
    for nombre, d in leer_biblioteca_json(ruta, "materiales").items():
        try:
            d = d if isinstance(d, dict) else {}
            importados.append(definir_material(nombre, d.get("co2"), d.get("densidad"), d.get("parecido") or ""))
        except geo.ErrorGeometria:
            salteados.append(nombre)
    return importados, salteados


def datos_material(nombre):
    """{co2, densidad, fuente} de un material de fábrica o propio (co2 None si no tiene fuente)."""
    if nombre in MATERIALES:
        return MATERIALES[nombre]
    propios = materiales_propios()
    if nombre not in propios:
        raise geo.ErrorGeometria(f"Material desconocido: «{nombre}».")
    return propios[nombre]


def material_cercano(nombre):
    """El material de la lista más parecido a un Material físico («Aluminio 6061» → Aluminio), o "" si no hay."""
    texto = str(nombre or "").casefold()
    return max((m for m in MATERIALES if m.casefold() in texto), key=len, default="")


def tipo_manufactura(cuerpo):
    """Texto de la fila Tipo de manufactura, por lo que se sabe del cuerpo."""
    m = getattr(cuerpo, "chapa", None)
    if m and not m.get("patron_de"):
        return "Chapa metálica"
    return {"solido": "Pieza sólida", "superficie": "Superficie", "malla": "Malla"}.get(getattr(cuerpo, "tipo", "solido"), "Pieza sólida")


def estimar(volumen_mm3, material):
    """Estimación de un volumen de `material`: {material, volumen_mm3, densidad, masa_kg, co2_por_kg, co2_kg, fuente}.
    Sin factor con fuente, ErrorGeometria: nunca se inventa un número."""
    d = datos_material(material)
    if d.get("co2") is None:
        raise geo.ErrorGeometria(f"{material} no tiene un factor de CO₂ con fuente: elegí otro material o creá uno propio.")
    masa = _positivo(volumen_mm3, "El volumen") * d["densidad"] * 1e-6     # mm³ × g/cm³ → kg
    return {"material": material, "volumen_mm3": float(volumen_mm3), "densidad": d["densidad"], "masa_kg": masa,
            "co2_por_kg": d["co2"], "co2_kg": masa * d["co2"], "fuente": d["fuente"]}
