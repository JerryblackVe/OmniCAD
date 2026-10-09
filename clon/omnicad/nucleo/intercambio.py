# -*- coding: utf-8 -*-
"""Lectura/escritura STEP y BREP a nivel kernel (la capa io_archivos los usa para archivos de usuario)."""
import os
import tempfile

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Message import Message
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.TopoDS import TopoDS_Shape

from .geometria import ErrorGeometria


def _silenciar_kernel():
    """OpenCascade imprime estadísticas de STEP por consola; se quitan los impresores por defecto."""
    mensajero = Message.DefaultMessenger_s()
    impresoras = mensajero.Printers()
    for i in range(impresoras.Size(), 0, -1):
        try:
            mensajero.RemovePrinter(impresoras.Value(i))
        except Exception:  # noqa: BLE001 — si la API cambia, solo queda el ruido en consola
            break


_silenciar_kernel()


def escribir_step(forma, ruta):
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    w = STEPControl_Writer()
    if w.Transfer(forma, STEPControl_AsIs) != IFSelect_RetDone:
        raise ErrorGeometria("No se pudo convertir la geometría a STEP.")
    if w.Write(str(ruta)) != IFSelect_RetDone:
        raise ErrorGeometria(f"No se pudo escribir el archivo STEP: {ruta}")


def leer_step(ruta):
    r = STEPControl_Reader()
    if r.ReadFile(str(ruta)) != IFSelect_RetDone:
        raise ErrorGeometria(f"No se pudo leer el archivo STEP: {ruta}")
    r.TransferRoots()
    forma = r.OneShape()
    if forma is None or forma.IsNull():
        raise ErrorGeometria("El archivo STEP no contiene geometría.")
    return forma


def leer_step_texto(texto):
    """Lee un STEP guardado como texto (la operación de importación lo embebe en la receta)."""
    fd, ruta = tempfile.mkstemp(suffix=".step")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        return leer_step(ruta)
    finally:
        os.remove(ruta)


def escribir_brep(forma, ruta):
    if not BRepTools.Write_s(forma, str(ruta)):
        raise ErrorGeometria(f"No se pudo escribir el BREP: {ruta}")


def leer_brep(ruta):
    forma = TopoDS_Shape()
    if not BRepTools.Read_s(forma, str(ruta), BRep_Builder()):
        raise ErrorGeometria(f"No se pudo leer el BREP: {ruta}")
    return forma


def brep_a_texto(forma):
    """Forma OCC → texto BREP comprimido (zlib + base64) para guardarla dentro de la receta."""
    import base64
    import zlib
    fd, ruta = tempfile.mkstemp(suffix=".brep")
    os.close(fd)
    try:
        escribir_brep(forma, ruta)
        with open(ruta, "rb") as f:
            return base64.b64encode(zlib.compress(f.read(), 6)).decode("ascii")
    finally:
        os.remove(ruta)


def forma_de_texto(texto):
    import base64
    import zlib
    fd, ruta = tempfile.mkstemp(suffix=".brep")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(zlib.decompress(base64.b64decode(texto)))
        return leer_brep(ruta)
    finally:
        os.remove(ruta)
