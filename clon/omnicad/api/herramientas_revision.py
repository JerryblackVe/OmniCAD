# -*- coding: utf-8 -*-
"""Herramientas del grupo "inspeccion" para revisar y reparar cuerpos (INSPECCIONAR › Revisar geometría):
`check_geometry` (validez del kernel, estanqueidad, aristas libres y no manifold, autointersecciones, tolerancias),
`check_printability` (espesor mínimo, voladizos, aristas filosas) y `repair_body` (deja un paso «Reparar cuerpo»).

El cálculo está en `nucleo.revision`; acá se traduce el informe a claves en inglés. Unidades: mm, mm², mm³ y grados.
"""
import math

from ..nucleo import revision as rv
from ..timeline.ops_revision import OpReparar
from .errores import error
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_inspeccion import _cuerpos
from .herramientas_solido import _agregar
from .registro import Expr, herramienta

# Tipos de problema del núcleo → kind estable del resultado.
_TIPOS = {"invalido": "invalid_shape", "cara_invalida": "invalid_face", "cascara_invalida": "invalid_shell",
          "solido_invalido": "invalid_solid", "arista_libre": "free_edge", "arista_no_manifold": "non_manifold_edge",
          "autointerseccion": "self_intersection", "cara_degenerada": "degenerate_face", "arista_diminuta": "tiny_edge",
          "tolerancia_alta": "high_tolerance", "normales_invertidas": "inverted_normals",
          "volumen_negativo": "negative_volume", "abierto": "not_closed", "espesor_fino": "thin_wall",
          "voladizo": "overhang", "arista_filosa": "sharp_edge"}
_TIPO_CUERPO = {"solido": "solid", "superficie": "surface", "malla": "mesh"}


def _r(x):
    return None if x is None else round(float(x), 6) + 0.0


def _caja(caja):
    if not caja:
        return None
    return {"min": [_r(v) for v in caja[0]], "max": [_r(v) for v in caja[1]],
            "size": [_r(b - a) for a, b in zip(caja[0], caja[1], strict=True)]}


def _problemas(informe):
    salida = []
    for p in informe["problemas"]:
        item = {"kind": _TIPOS.get(p["tipo"], p["tipo"]), "severity": "error" if p["gravedad"] == "error" else "warning",
                "message": p["mensaje"], "position": None if p["punto"] is None else [_r(x) for x in p["punto"]]}
        if "valor" in p:
            item["value"] = _r(p["valor"])
        salida.append(item)
    return salida


def _elegidos(sesion, body):
    cuerpos = _cuerpos(sesion, [body] if body else None)
    if not cuerpos:
        raise error("NOTHING_TO_MEASURE", "No hay cuerpos para revisar.")
    return cuerpos


def _encabezado(sesion, c):
    return {"id": c.id, "name": sesion.nombre_cuerpo(c), "type": _TIPO_CUERPO.get(getattr(c, "tipo", "solido"), "solid")}


def _exigir_max_issues(max_issues):
    if max_issues < 0:
        raise error("INVALID_ARGUMENTS", f"max_issues no puede ser negativo (recibió {max_issues}).")


# ---------------------------------------------------------------- revisar geometría
def _informe_geometria(sesion, c, informe):
    tol = informe["tolerancias"]
    salida = _encabezado(sesion, c)
    salida.update({
        "valid": informe["valido"], "closed": informe["cerrado"], "solids": informe["solidos"],
        "shells": informe["cascaras"], "open_shells": informe["cascaras_abiertas"], "faces": informe["caras"],
        "edges": informe["aristas"], "vertices": informe["vertices"], "free_edges": informe["aristas_libres"],
        "non_manifold_edges": informe["aristas_no_manifold"], "self_intersections": informe["autointersecciones"],
        "degenerate_faces": informe["caras_degeneradas"], "tiny_edges": informe["aristas_diminutas"],
        "high_tolerances": informe["tolerancias_altas"],
        "max_tolerance": None if tol is None else {"vertex": _r(tol["vertice"]), "edge": _r(tol["arista"]),
                                                   "face": _r(tol["cara"])},
        "volume": _r(informe["volumen"]), "area": _r(informe["area"]), "bounding_box": _caja(informe["caja"]),
        "errors": informe["errores"], "warnings": informe["avisos"], "issues": _problemas(informe),
        "issues_truncated": informe["truncado"], "summary": rv.resumen(informe)})
    if informe["tipo_cuerpo"] == "malla":
        salida.update(inverted_normals=informe["normales_invertidas"], negative_volume=informe["volumen_negativo"])
    return salida


@herramienta("check_geometry", "inspeccion", "Revisa la geometría de un cuerpo (o de todos), como Check Geometry de "
             "FreeCAD: si el kernel lo da por válido (y qué falla si no), si es estanco, aristas libres (abiertas) y no "
             "manifold, autointersecciones, caras degeneradas, aristas diminutas y tolerancias máximas; en mallas, bordes "
             "abiertos, no manifold, normales invertidas y triángulos degenerados. Cada problema trae kind, severity "
             "(error o warning), un mensaje y su posición [x, y, z]; max_tolerance es la mayor tolerancia del kernel "
             "por tipo. No cambia el documento: para arreglar, repair_body.")
def check_geometry(sesion, body: str | None = None, self_intersection: bool = True, tolerance_limit: float = 0.01,
                   max_issues: int = 50):
    """
    body: id o nombre del cuerpo; vacío = todos los cuerpos del modelo.
    self_intersection: true busca caras que se cortan entre sí (análisis booleano, lo más lento en piezas grandes).
    tolerance_limit: tolerancia en mm de vértice, arista o cara por encima de la cual se avisa (high_tolerance).
    max_issues: cuántos problemas devolver por cuerpo como máximo; los conteos son siempre completos.
    """
    _exigir_max_issues(max_issues)
    if not tolerance_limit > 0 or not math.isfinite(tolerance_limit):
        raise error("INVALID_ARGUMENTS", f"tolerance_limit tiene que ser un número mayor que cero en mm (recibió "
                    f"{tolerance_limit}).")
    informes = []
    for c in _elegidos(sesion, body):
        informe = rv.revisar(c.forma, autointersecciones=self_intersection, tolerancia_maxima=tolerance_limit,
                             max_problemas=max_issues)
        informes.append(_informe_geometria(sesion, c, informe))
    return {"bodies": informes, "count": len(informes), "all_valid": all(i["valid"] for i in informes),
            "all_closed": all(i["closed"] for i in informes)}


# ---------------------------------------------------------------- revisión de impresión 3D
@herramienta("check_printability", "inspeccion", "Revisión de impresión 3D de un cuerpo (o de todos), como la caja de "
             "herramientas de impresión 3D de Blender: si es estanco, espesor mínimo de pared (rayos hacia adentro desde "
             "la superficie; zonas más finas que min_thickness), zonas en voladizo que necesitan soportes (más de "
             "overhang_angle desde la vertical, sin contar la cara apoyada en la cama: el plano Z más bajo del cuerpo) y "
             "aristas filosas (ángulo interior menor que sharp_angle). printable = estanco y sin paredes finas. Cada zona "
             "trae su posición. No cambia el documento.")
def check_printability(sesion, body: str | None = None, min_thickness: float = 0.8, overhang_angle: float = 45.0,
                       sharp_angle: float = 20.0, samples: int = 2000, max_issues: int = 50):
    """
    body: id o nombre del cuerpo; vacío = todos los cuerpos del modelo.
    min_thickness: espesor de pared mínimo en mm (p. ej. 2 veces el diámetro de la boquilla); 0 no marca paredes.
    overhang_angle: ángulo de voladizo en grados desde la vertical que se imprime sin soportes (0 a 90; 45 es lo habitual).
    sharp_angle: ángulo interior en grados por debajo del cual una arista convexa es filosa (0 a 180).
    samples: cantidad de rayos para medir el espesor (1 a 20000; más = más lento y más fino).
    max_issues: cuántos problemas devolver por cuerpo como máximo; los conteos son siempre completos.
    """
    _exigir_max_issues(max_issues)
    if not min_thickness >= 0 or not math.isfinite(min_thickness):
        raise error("INVALID_ARGUMENTS", f"min_thickness tiene que ser un número mayor o igual que cero en mm "
                    f"(recibió {min_thickness}).")
    if not 0 < overhang_angle < 90:
        raise error("INVALID_ARGUMENTS", f"overhang_angle tiene que estar entre 0 y 90 grados (recibió {overhang_angle}).")
    if not 0 <= sharp_angle < 180:
        raise error("INVALID_ARGUMENTS", f"sharp_angle tiene que estar entre 0 y 180 grados (recibió {sharp_angle}).")
    if not 1 <= samples <= 20000:
        raise error("INVALID_ARGUMENTS", f"samples tiene que estar entre 1 y 20000 (recibió {samples}).")
    informes = []
    for c in _elegidos(sesion, body):
        i = rv.revisar_impresion(c.forma, espesor_minimo=min_thickness, angulo_voladizo=overhang_angle,
                                 angulo_filoso=sharp_angle, muestras=samples, max_problemas=max_issues)
        salida = _encabezado(sesion, c)
        salida.update({
            "closed": i["cerrado"], "printable": i["imprimible"], "min_thickness_measured": _r(i["espesor_minimo"]),
            "thin_regions": i["zonas_finas"], "overhang_area": _r(i["area_voladizo"]),
            "overhang_regions": i["zonas_voladizo"], "sharp_edges": i["aristas_filosas"], "samples": i["muestras"],
            "volume": _r(i["volumen"]), "area": _r(i["area"]), "bounding_box": _caja(i["caja"]),
            "errors": i["errores"], "warnings": i["avisos"], "issues": _problemas(i),
            "issues_truncated": i["truncado"], "summary": rv.resumen(i)})
        informes.append(salida)
    return {"bodies": informes, "count": len(informes), "all_printable": all(i["printable"] for i in informes),
            "settings": {"min_thickness": min_thickness, "overhang_angle": overhang_angle, "sharp_angle": sharp_angle}}


# ---------------------------------------------------------------- reparar
def _estado(forma):
    i = rv.revisar(forma, autointersecciones=False, max_problemas=0)
    tol = i["tolerancias"]
    return {"valid": i["valido"], "closed": i["cerrado"], "free_edges": i["aristas_libres"],
            "non_manifold_edges": i["aristas_no_manifold"],
            "max_tolerance": None if tol is None else _r(max(tol.values()))}


@herramienta("repair_body", "inspeccion", "Repara un cuerpo y deja un paso «Reparar cuerpo» en el timeline (editable; "
             "un paso de deshacer): cose las aristas abiertas (si queda estanco pasa a sólido), baja las tolerancias "
             "mayores que tolerance, corrige con ShapeFix (orientación de caras, contornos) y refina (une caras "
             "coplanares). En mallas: une vértices a menos de tolerance, corrige triángulos degenerados, orienta las "
             "normales y cierra agujeros. Devuelve el estado antes y después (valid, closed, free_edges, "
             "non_manifold_edges, max_tolerance); si sigue con problemas, lo dice en avisos.", modifica=True)
def repair_body(sesion, body: str, tolerance: Expr = "0.01 mm", sew: bool = True, refine: bool = True,
                fix: bool = True):
    """
    body: id o nombre del cuerpo a reparar.
    tolerance: tolerancia de reparación en mm (número o expresión): distancia para coser y tope de las tolerancias; 0 = sin tope.
    sew: true cose las aristas libres (abiertas); en mallas siempre se cose.
    refine: true une las caras coplanares y las aristas colineales (Refine Shape).
    fix: true corrige con ShapeFix (orientación de caras, contornos, curvas sobre las caras).
    """
    if isinstance(tolerance, (int, float)) and (tolerance < 0 or not math.isfinite(tolerance)):
        raise error("INVALID_ARGUMENTS", f"tolerance no puede ser negativa (recibió {tolerance}).")
    c = sesion.cuerpo(body)
    antes = _estado(c.forma)
    doc = sesion.doc
    op = OpReparar(doc.nuevo_id(), nombre_nuevo(doc, "Reparar", OpReparar), cuerpos=[c.id],
                   tolerancia=texto_expr(tolerance), coser=sew, refinar=refine, arreglar=fix)
    resultado = _agregar(sesion, op)
    resultado.update(before=antes, after=_estado(sesion.cuerpo(c.id).forma))
    return resultado
