# -*- coding: utf-8 -*-
"""INSPECCIONAR › Sustainability Insights: estimación local de CO₂ por material (`nucleo/sustentabilidad.py`), sin servicios
externos. Cada resultado es una estimación con su cálculo y su fuente."""
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import sustentabilidad as su
from ..timeline.operaciones import propiedades_cuerpo
from .errores import error
from .registro import herramienta


def _lista():
    fabrica = [{"name": n, "co2_per_kg": d["co2"], "density": d["densidad"], "source": d["fuente"], "custom": False}
               for n, d in su.MATERIALES.items()]
    propios = [{"name": n, "co2_per_kg": d.get("co2"), "density": d.get("densidad"), "similar_to": d.get("parecido", ""),
                "source": d.get("fuente", ""), "custom": True} for n, d in su.materiales_propios().items()]
    return {"materials": fabrica + propios, "regions": {r: list(p) for r, p in su.REGIONES.items()}}


def _solido(sesion, ref):
    c = sesion.cuerpo(ref)
    if getattr(c, "tipo", "solido") != "solido":
        raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» no es un sólido: no tiene volumen para estimar.")
    return c


@herramienta("estimate_carbon_footprint", "inspeccion", "Sustainability Insights local: estima los kg de CO₂e de un cuerpo "
             "con masa × factor del material, sin internet. Devuelve el cálculo y la fuente del factor. Sin material usa el "
             "más parecido a su Material físico. Región y país solo se informan: no cambian el resultado. Un material sin "
             "fuente da error: nunca se inventa un factor.")
def estimate_carbon_footprint(sesion, body: str, material: str | None = None, stock_volume: float | None = None,
                              stock_body: str | None = None, region: str | None = None, country: str | None = None):
    """
    body: cuerpo sólido a estimar (id o nombre).
    material: material de la lista (manage_carbon_materials) o uno propio; vacío = el más parecido al Material físico del cuerpo.
    stock_volume: Sobrescritura de volumen del stock: volumen en mm³ en lugar del de la pieza.
    stock_body: Sobrescritura de volumen del stock: cuerpo cuyo volumen se usa en lugar del de la pieza.
    region: Región de manufactura (ver manage_carbon_materials).
    country: País de manufactura; necesita region.
    """
    c = _solido(sesion, body)
    if stock_volume is not None and stock_body is not None:
        raise error("INVALID_ARGUMENTS", "stock_volume y stock_body son excluyentes: dale uno solo.")
    if region is not None and region not in su.REGIONES:
        raise error("INVALID_ARGUMENTS", f"Región desconocida «{region}».", f"Regiones: {', '.join(su.REGIONES)}.")
    if country is not None and country not in su.REGIONES.get(region, ()):
        raise error("INVALID_ARGUMENTS", f"País «{country}» fuera de la región {region}.",
                    f"Países: {', '.join(su.REGIONES.get(region, ())) or 'dar region antes'}.")
    fisico = propiedades_cuerpo(sesion.doc.propiedades, c).get("material") or getattr(c, "material", None)
    material = material or su.material_cercano(fisico)
    if not material:
        raise error("INVALID_ARGUMENTS", f"No se sabe el material de «{sesion.nombre_cuerpo(c)}»: pasá material.")
    volumen = (float(stock_volume) if stock_volume is not None
               else geo.volumen(_solido(sesion, stock_body).forma if stock_body else c.forma))
    try:
        e = su.estimar(volumen, material)
    except geo.ErrorGeometria as ex:
        raise error("INVALID_ARGUMENTS", str(ex)) from None
    return {"estimate": True, "body": c.id, "manufacturing_type": su.tipo_manufactura(c), "material": e["material"],
            "body_material": fisico, "volume_mm3": round(e["volumen_mm3"], 3), "density_g_cm3": e["densidad"],
            "mass_kg": round(e["masa_kg"], 6), "co2_per_kg": e["co2_por_kg"], "co2_kg": round(e["co2_kg"], 6),
            "formula": "mass_kg × co2_per_kg", "source": e["fuente"], "region": region, "country": country}


@herramienta("manage_carbon_materials", "inspeccion", "Materiales de Sustainability Insights: lista los de fábrica con su "
             "fuente, las regiones y los propios; agrega o quita propios, y los importa o exporta a un .json. Los propios "
             "se comparten entre documentos.")
def manage_carbon_materials(sesion, action: Literal["list", "add", "remove", "import", "export"] = "list",
                            name: str | None = None, co2_per_kg: float | None = None, density: float | None = None,
                            similar_to: str | None = None, path: str | None = None):
    """
    action: list, add (crea o reemplaza uno propio), remove, import o export.
    name: nombre del material propio, con add y remove.
    co2_per_kg: add: kg de CO₂e por kg de material.
    density: add: densidad en g/cm³.
    similar_to: add: material de fábrica más parecido.
    path: import y export: ruta del archivo .json.
    """
    try:
        if action == "add":
            su.definir_material(name or "", co2_per_kg, density, similar_to or "")
        elif action == "remove":
            su.borrar_material(name or "")
        elif action in ("import", "export"):
            if not path:
                raise error("INVALID_ARGUMENTS", f"{action} necesita path.")
            if action == "export":
                return {"exported": su.exportar_materiales(path), "path": path}
            importados, salteados = su.importar_materiales(path)
            return {"imported": importados, "skipped": salteados, **_lista()}
    except (geo.ErrorGeometria, OSError) as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
    return _lista()
