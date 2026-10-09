# -*- coding: utf-8 -*-
"""
Exportación STL / OBJ / STEP e importación STEP.

Equivalencia con Fusion 360: `ExportManager.createSTLExportOptions / createOBJExportOptions /
createSTEPExportOptions` y `ImportManager.createSTEPImportOptions` (informe_analisis.md §3.5).
STL y OBJ son mallas (se teselan desde el B-rep); STEP conserva el B-rep exacto.
"""
import struct
from pathlib import Path

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import intercambio

FORMATOS = {"stl": "STL (malla)", "obj": "OBJ (malla)", "3mf": "3MF (malla para impresión 3D)", "ply": "PLY (malla)",
            "step": "STEP (sólido exacto)", "iges": "IGES (superficies exactas)", "brep": "BREP de OpenCascade"}


class ErrorExportacion(RuntimeError):
    pass


def _cuerpos(cuerpos):
    lista = list(cuerpos)
    if not lista:
        raise ErrorExportacion("No hay cuerpos para exportar.")
    return lista


def _es_malla(forma):
    return hasattr(forma, "vertices") and hasattr(forma, "caras") and not callable(getattr(forma, "caras"))


def _indexados(forma, deflexion):
    """(vértices, índices) de un cuerpo B-rep (teselado) o de malla (tal cual)."""
    if _es_malla(forma):
        return np.asarray(forma.vertices, float), np.asarray(forma.caras, int)
    return geo.triangulos_indexados(forma, deflexion)


def _malla_total(cuerpos, deflexion):
    from ..nucleo.malla import Malla
    vs, cs, base = [], [], 0
    for c in cuerpos:
        v, i = _indexados(c.forma, deflexion)
        vs.append(v)
        cs.append(np.asarray(i, int) + base)
        base += len(v)
    if not base:
        raise ErrorExportacion("La malla quedó vacía.")
    return Malla(np.concatenate(vs), np.concatenate(cs))


def exportar_stl(cuerpos, ruta, deflexion=0.02, binario=True):
    """STL de todos los cuerpos. deflexion = desvío máximo de la malla respecto del sólido (mm)."""
    cuerpos = _cuerpos(cuerpos)
    triangulos = []
    for c in cuerpos:
        v, i = _indexados(c.forma, deflexion)
        triangulos.extend(v[t] for t in i)
    if not triangulos:
        raise ErrorExportacion("La malla quedó vacía.")
    tri = np.array(triangulos, dtype=np.float64)
    normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(normales, axis=1, keepdims=True)
    largo[largo == 0] = 1
    normales /= largo
    ruta = Path(ruta)
    if binario:
        with open(ruta, "wb") as f:
            f.write(b"OmniCAD STL".ljust(80, b" "))
            f.write(struct.pack("<I", len(tri)))
            for n, t in zip(normales, tri, strict=True):
                f.write(struct.pack("<12fH", *n, *t[0], *t[1], *t[2], 0))
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
    from OCP.IGESControl import IGESControl_Writer
    w = IGESControl_Writer("MM", 1)
    w.AddShape(_forma_brep(cuerpos))
    w.ComputeModel()
    if not w.Write(str(ruta)):
        raise ErrorExportacion(f"No se pudo escribir el IGES: {ruta}")


def exportar_brep(cuerpos, ruta):
    from OCP.BRepTools import BRepTools
    if not BRepTools.Write_s(_forma_brep(cuerpos), str(ruta)):
        raise ErrorExportacion(f"No se pudo escribir el BREP: {ruta}")


def exportar_malla(cuerpos, ruta, deflexion=0.02):
    """3MF o PLY (también sirve para STL/OBJ) con todos los cuerpos juntos."""
    from ..nucleo import malla
    m = _malla_total(_cuerpos(cuerpos), deflexion)
    malla.escribir(m, ruta)
    return len(m.caras)


def exportar(cuerpos, ruta):
    """Elige el formato por la extensión del archivo."""
    ext = Path(ruta).suffix.lower().lstrip(".")
    ext = {"stp": "step", "igs": "iges", "brp": "brep"}.get(ext, ext)
    funciones = {"stl": exportar_stl, "obj": exportar_obj, "step": exportar_step, "3mf": exportar_malla,
                 "ply": exportar_malla, "iges": exportar_iges, "brep": exportar_brep}
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
