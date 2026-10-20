# -*- coding: utf-8 -*-
"""
Exportación STL / OBJ / 3MF / PLY / glTF (GLB) / STEP / IGES / BREP e importación STEP (glTF: `gltf.py`).

Equivalencia con Fusion 360: `ExportManager.createSTLExportOptions / createOBJExportOptions /
createSTEPExportOptions` y `ImportManager.createSTEPImportOptions` (informe_analisis.md §3.5).
STL y OBJ son mallas (se teselan desde el B-rep); STEP conserva el B-rep exacto.
"""
import math
import struct
from pathlib import Path

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import intercambio

FORMATOS = {"stl": "STL (malla)", "obj": "OBJ (malla)", "3mf": "3MF (malla para impresión 3D)", "ply": "PLY (malla)",
            "glb": "glTF binario (malla con colores: web y realidad aumentada)",
            "gltf": "glTF (JSON con la malla embebida)",
            "step": "STEP (sólido exacto)", "iges": "IGES (superficies exactas)", "brep": "BREP de OpenCascade"}

FORMATOS_MALLA = {"3mf": "3MF", "stl_binario": "STL (binario)", "stl_ascii": "STL (ASCII)", "obj": "OBJ"}
UNIDADES_MALLA = {"mm": "mm", "cm": "cm", "m": "m", "in": "pulgadas", "ft": "pies"}
ANGULO_MALLA = math.degrees(0.3)


class ErrorExportacion(RuntimeError):
    pass


def _cuerpos(cuerpos):
    lista = list(cuerpos)
    if not lista:
        raise ErrorExportacion("No hay cuerpos para exportar.")
    return lista


def _es_malla(forma):
    return hasattr(forma, "vertices") and hasattr(forma, "caras") and not callable(getattr(forma, "caras"))


def cuerpos_de_malla(cuerpos):
    """Los cuerpos de malla de la lista: los formatos B-rep (STEP, IGES, BREP) no los pueden guardar
    (`_forma_brep` los deja afuera); sirve para avisar cuáles quedaron omitidos (B-68)."""
    return [c for c in _cuerpos(cuerpos) if _es_malla(c.forma)]


def _indexados(forma, deflexion):
    """(vértices, índices) de un cuerpo B-rep (teselado) o de malla (tal cual)."""
    if _es_malla(forma):
        return np.asarray(forma.vertices, float), np.asarray(forma.caras, int)
    return geo.triangulos_indexados(forma, deflexion)


def _unir_mallas(mallas):
    from ..nucleo.malla import Malla
    vs, cs, gs, base = [], [], [], 0
    for k, m in enumerate(mallas):
        vs.append(m.vertices)
        cs.append(m.caras + base)
        gs.append(np.full(len(m.caras), k))
        base += len(m.vertices)
    if not base:
        raise ErrorExportacion("La malla quedó vacía.")
    return Malla(np.concatenate(vs), np.concatenate(cs), np.concatenate(gs))


def exportar_stl(cuerpos, ruta, deflexion=0.02, binario=True):
    """STL de todos los cuerpos. deflexion = desvío máximo de la malla respecto del sólido (mm)."""
    cuerpos = _cuerpos(cuerpos)
    triangulos = []
    for c in cuerpos:
        v, i = _indexados(c.forma, deflexion)
        if len(i):
            triangulos.append(np.asarray(v, np.float64)[np.asarray(i, int)])
    if not triangulos:
        raise ErrorExportacion("La malla quedó vacía.")
    tri = np.concatenate(triangulos)
    normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(normales, axis=1, keepdims=True)
    largo[largo == 0] = 1
    normales /= largo
    ruta = Path(ruta)
    if binario:
        with open(ruta, "wb") as f:
            f.write(b"OmniCAD STL".ljust(80, b" "))
            f.write(struct.pack("<I", len(tri)))
            # Todo de una: un registro de 50 bytes por triángulo (struct.pack por triángulo: 1,6 s con 327 k).
            registros = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("atributo", "<u2")])
            registros["n"], registros["v"] = normales, tri
            f.write(registros.tobytes())
    else:
        with open(ruta, "w", encoding="ascii") as f:
            f.write("solid omnicad\n")
            for n, t in zip(normales, tri, strict=True):
                f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n    outer loop\n")
                for p in t:
                    f.write(f"      vertex {p[0]:.6e} {p[1]:.6e} {p[2]:.6e}\n")
                f.write("    endloop\n  endfacet\n")
            f.write("endsolid omnicad\n")
    return len(tri)


def exportar_obj(cuerpos, ruta, deflexion=0.02):
    """OBJ con un grupo por cuerpo (vértices compartidos dentro de cada cuerpo)."""
    cuerpos = _cuerpos(cuerpos)
    total, base = 0, 1
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# OmniCAD OBJ — unidades: mm\n")
        for c in cuerpos:
            v, idx = _indexados(c.forma, deflexion)
            nombre = "".join(ch if ch.isalnum() else "_" for ch in c.nombre)
            f.write(f"o {nombre}\n")
            for p in v:
                f.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
            for t in idx:
                f.write(f"f {t[0] + base} {t[1] + base} {t[2] + base}\n")
            base += len(v)
            total += len(idx)
    if total == 0:
        raise ErrorExportacion("La malla quedó vacía.")
    return total


def _forma_brep(cuerpos):
    formas = [c.forma for c in _cuerpos(cuerpos) if not _es_malla(c.forma)]
    if not formas:
        raise ErrorExportacion("Los cuerpos de malla no se pueden guardar en un formato B-rep: convertilos antes.")
    return formas[0] if len(formas) == 1 else geo.compuesto(formas)


def exportar_step(cuerpos, ruta):
    intercambio.escribir_step(_forma_brep(cuerpos), ruta)


def exportar_iges(cuerpos, ruta):
    if not intercambio.escribir_iges(_forma_brep(cuerpos), ruta):
        raise ErrorExportacion(f"No se pudo escribir el IGES: {ruta}")


def exportar_brep(cuerpos, ruta):
    if not intercambio.escribir_brep_exportacion(_forma_brep(cuerpos), ruta):
        raise ErrorExportacion(f"No se pudo escribir el BREP: {ruta}")


def preparar_mallas(cuerpos, *, refinamiento="personalizado", desviacion=0.02, angulo=ANGULO_MALLA,
                    longitud_maxima=0.0, relacion_aspecto=0.0):
    """Mallas por cuerpo para Guardar como malla y su recuento; nunca modifica la geometría del documento."""
    from ..nucleo import malla
    if refinamiento not in ("bajo", "medio", "alto", "personalizado"):
        raise ErrorExportacion(f"Refinamiento desconocido: {refinamiento}")
    opciones = {"refinamiento": refinamiento, "longitud_maxima": longitud_maxima,
                "relacion_aspecto": relacion_aspecto}
    if refinamiento == "personalizado":
        opciones.update(desviacion=desviacion, angulo=angulo)
    else:
        opciones.update(longitud_maxima=0.0, relacion_aspecto=0.0)
    resultado = []
    for c in _cuerpos(cuerpos):
        if _es_malla(c.forma):
            m = malla.refinar_triangulos(c.forma, longitud_maxima=opciones["longitud_maxima"],
                                         relacion_aspecto=opciones["relacion_aspecto"])
        else:
            m = malla.desde_brep(c.forma, **opciones)
        if not len(m.caras):
            raise ErrorExportacion("La malla quedó vacía.")
        resultado.append(m)
    return resultado


def rutas_malla(cuerpos, ruta, *, formato=None, estructura="un_archivo"):
    """Destinos de Guardar como malla, con nombres seguros y únicos aun con cuerpos homónimos."""
    lista, ruta = _cuerpos(cuerpos), Path(ruta)
    formato = formato or {"stl": "stl_binario"}.get(ruta.suffix[1:].lower(), ruta.suffix[1:].lower())
    if formato not in (*FORMATOS_MALLA, "ply"):
        raise ErrorExportacion(f"Formato no soportado: {formato}")
    extension = ".stl" if formato.startswith("stl_") else f".{formato}"
    if ruta.suffix.lower() != extension:
        raise ErrorExportacion(f"El formato {formato} necesita la extensión {extension}.")
    if estructura == "un_archivo":
        return [ruta]
    if estructura != "uno_por_cuerpo":
        raise ErrorExportacion(f"Estructura desconocida: {estructura}")
    return [ruta.with_name(f"{ruta.stem}_{i}_{''.join(ch if ch.isalnum() else '_' for ch in c.nombre)[:80]}{extension}")
            for i, c in enumerate(lista, 1)]


def exportar_malla(cuerpos, ruta, deflexion=0.02, *, formato=None, unidades="mm", estructura="un_archivo",
                   refinamiento="personalizado", desviacion=None, angulo=ANGULO_MALLA,
                   longitud_maxima=0.0, relacion_aspecto=0.0, sobrescribir=True):
    """Guardar como malla: 3MF, STL binario/ASCII u OBJ; conserva PLY para los llamadores anteriores.
    Devuelve los triángulos escritos; unidades mm/cm/m/in/ft. 0 desactiva arista/aspecto.
    Por defecto conserva 0,02 mm, 0,3 radianes y un archivo; 3MF conserva un objeto por cuerpo."""
    from ..nucleo import malla
    lista = _cuerpos(cuerpos)
    rutas = rutas_malla(lista, ruta, formato=formato, estructura=estructura)
    if unidades not in UNIDADES_MALLA:
        raise ErrorExportacion(f"Unidad desconocida: {unidades}")
    for destino in rutas:
        if destino.is_dir():
            raise ErrorExportacion(f"El destino es una carpeta: {destino}")
        if destino.exists() and not sobrescribir:
            raise FileExistsError(f"Ya existe el archivo: {destino}")
    mallas = preparar_mallas(lista, refinamiento=refinamiento,
                            desviacion=deflexion if desviacion is None else desviacion, angulo=angulo,
                            longitud_maxima=longitud_maxima, relacion_aspecto=relacion_aspecto)
    lotes = [[m] for m in mallas] if estructura == "uno_por_cuerpo" else [mallas]
    for destino, lote in zip(rutas, lotes, strict=True):
        opciones = {"unidades": UNIDADES_MALLA[unidades]}
        if destino.suffix.lower() == ".3mf":
            malla.escribir_3mf(lote, destino, **opciones)
        else:
            total = _unir_mallas(lote)
            if destino.suffix.lower() == ".stl":
                opciones["binario"] = formato != "stl_ascii"
            malla.escribir(total, destino, **opciones)
    return sum(len(m.caras) for m in mallas)


def exportar_gltf(cuerpos, ruta, propiedades=None):
    """glTF 2.0 (.glb binario o .gltf con el búfer embebido), con el color y el acabado de cada cuerpo."""
    from .gltf import escribir_gltf
    return escribir_gltf(_cuerpos(cuerpos), ruta, propiedades=propiedades)


def exportar(cuerpos, ruta, propiedades=None):
    """Elige el formato por la extensión del archivo. `propiedades` (las del documento: aspecto, acabado, opacidad y
    nombre de cada cuerpo) solo las usa glTF, el único formato que guarda materiales."""
    ext = Path(ruta).suffix.lower().lstrip(".")
    ext = {"stp": "step", "igs": "iges", "brp": "brep"}.get(ext, ext)
    funciones = {"stl": exportar_stl, "obj": exportar_obj, "step": exportar_step, "3mf": exportar_malla,
                 "ply": exportar_malla, "iges": exportar_iges, "brep": exportar_brep}
    if ext in ("glb", "gltf"):
        return exportar_gltf(cuerpos, ruta, propiedades)
    if ext not in funciones:
        raise ErrorExportacion(f"Formato no soportado: .{ext} (usá {', '.join('.' + f for f in FORMATOS)})")
    return funciones[ext](cuerpos, ruta)


def leer_texto_step(ruta):
    """Contenido de un STEP para embeberlo en la operación de importación (valida que se pueda leer)."""
    texto = Path(ruta).read_text(encoding="utf-8", errors="replace")
    if "ISO-10303-21" not in texto[:200]:
        raise ErrorExportacion("El archivo no parece un STEP (falta la cabecera ISO-10303-21).")
    intercambio.leer_step_texto(texto)
    return texto
