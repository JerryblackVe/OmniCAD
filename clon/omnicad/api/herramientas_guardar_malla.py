# -*- coding: utf-8 -*-
"""Guardar como malla con los mismos controles que el diálogo."""
from pathlib import Path
from typing import Literal

from ..io_archivos import exportar as ex
from ..timeline.ops_chapa import cuerpos_del_modelo
from .errores import error
from .registro import herramienta
from .sesion import borrar_carpetas, crear_carpeta


@herramienta("export_mesh", "documento", "Guardar como malla: 3MF, STL binario/ASCII u OBJ, unidades, un archivo "
             "o uno por cuerpo y refinado con recuento de triángulos. Las mallas existentes conservan sus facetas; "
             "los controles personalizados de arista y aspecto también las subdividen.")
def export_mesh(sesion, path: str, bodies: list[str] | None = None,
                format: Literal["3mf", "stl_binario", "stl_ascii", "obj"] = "stl_binario",
                units: Literal["mm", "cm", "m", "in", "ft"] = "mm",
                structure: Literal["un_archivo", "uno_por_cuerpo"] = "un_archivo",
                refinement: Literal["bajo", "medio", "alto", "personalizado"] = "personalizado",
                surface_deviation: float = 0.02, normal_deviation: float = ex.ANGULO_MALLA,
                maximum_edge_length: float = 0.0, aspect_ratio: float = 0.0,
                overwrite: bool = False, create_folders: bool = True):
    """
    path: archivo de destino con extensión correspondiente al formato (.3mf, .stl u .obj).
    bodies: ids o nombres de los cuerpos; vacío = todos los del modelo, sin patrones planos.
    format: 3mf, stl_binario, stl_ascii u obj.
    units: unidad del archivo: mm, cm, m, in o ft; el modelo sigue en mm.
    structure: un_archivo o uno_por_cuerpo; los separados llevan índice y nombre del cuerpo.
    refinement: bajo, medio, alto o personalizado; solo este último usa los cuatro controles numéricos.
    surface_deviation: desviación máxima de superficie en mm (por defecto 0,02).
    normal_deviation: desviación angular en grados (por defecto 0,3 radianes expresados en grados).
    maximum_edge_length: longitud máxima de arista en mm; 0 = sin límite.
    aspect_ratio: arista mayor / altura menor, mayor que 1,154701; 0 = sin límite.
    overwrite: true permite reemplazar archivos existentes; se comprueban todos antes de escribir.
    create_folders: true crea las carpetas que faltan; false falla si la carpeta no existe.
    """
    if not path.strip() or Path(path).is_dir():
        raise error("INVALID_ARGUMENTS", "path debe ser un archivo de destino con extensión.")
    cuerpos = ([sesion.cuerpo(b) for b in dict.fromkeys(bodies)] if bodies
               else cuerpos_del_modelo(sesion.doc.estado_final))
    ruta = Path(path)
    rutas = ex.rutas_malla(cuerpos, ruta, formato=format, estructura=structure)
    for destino in rutas:
        if destino.exists() and not overwrite:
            raise error("FILE_EXISTS", f"Ya existe el archivo: {destino}")
    nuevas = crear_carpeta(ruta.parent) if create_folders else []
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
    try:
        n = ex.exportar_malla(cuerpos, ruta, formato=format, unidades=units, estructura=structure,
                              refinamiento=refinement, desviacion=surface_deviation, angulo=normal_deviation,
                              longitud_maxima=maximum_edge_length, relacion_aspecto=aspect_ratio,
                              sobrescribir=overwrite)
    except BaseException:
        borrar_carpetas(nuevas)
        raise
    if nuevas:
        sesion.avisar(f"Se creó la carpeta {ruta.parent}.")
    return {"paths": [str(p.resolve()) for p in rutas], "format": format, "units": units,
            "bodies": [c.id for c in cuerpos], "triangles": n,
            "size_bytes": sum(p.stat().st_size for p in rutas)}
