"""Intercambio CSV de parámetros con el formato que usa la ventana."""
import csv
import io
import os
import tempfile
from pathlib import Path
from typing import Literal

from ..timeline.parametros import ESCALAR, UNIDADES, TablaParametros, validar_nombre
from .errores import error
from .herramientas_parametros import _UNIDAD, info_parametros
from .registro import herramienta
from .sesion import borrar_carpetas, crear_carpeta

TOPE_CSV = 2_000_000
TOPE_FILAS = 1000
TOPE_CAMPO = 4096
_COLUMNAS = ["Name", "Unit", "Expression", "Value", "Comments"]


@herramienta("export_parameters", "parametros", "Exporta parámetros a CSV (Name, Unit, Expression, Value, Comments), "
             "compatible con la tabla de parámetros de la ventana.")
def export_parameters(sesion, path: str, overwrite: bool = False, create_folders: bool = True):
    """
    path: ruta del archivo CSV a escribir.
    overwrite: true para reemplazar un archivo existente.
    create_folders: true crea las carpetas que falten; false devuelve FILE_NOT_FOUND.
    """
    ruta = Path(path).expanduser()
    if not path.strip() or not ruta.name or ruta.is_dir() or ruta.suffix.lower() != ".csv":
        raise error("INVALID_ARGUMENTS", "path debe indicar un archivo .csv.")
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    valores = sesion.doc.parametros.valores()
    buf = io.StringIO(newline="")
    escritor = csv.writer(buf)
    escritor.writerow(_COLUMNAS)
    for p in sesion.doc.parametros:
        escritor.writerow([p.nombre, _UNIDAD[p.tipo], p.expresion, repr(valores[p.nombre]), p.comentario])
    nuevas = crear_carpeta(ruta.parent) if create_folders else []
    temporal = None
    try:
        if not ruta.parent.is_dir():
            raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
        datos = buf.getvalue().encode("utf-8")
        if overwrite:
            with tempfile.NamedTemporaryFile(dir=ruta.parent, delete=False) as f:
                temporal = Path(f.name)
                f.write(datos)
            os.replace(temporal, ruta)
        else:
            with ruta.open("xb") as f:                 # exclusivo: no pisa un archivo creado después del control inicial
                f.write(datos)
    except FileExistsError:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}") from None
    except BaseException:
        borrar_carpetas(nuevas)
        raise
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    return {"path": str(ruta.resolve()), "count": len(sesion.doc.parametros), "size_bytes": ruta.stat().st_size}


@herramienta("import_parameters", "parametros", "Importa parámetros CSV con validación de expresiones y unidades. "
             "merge agrega o actualiza por nombre; replace reemplaza la tabla. Un solo deshacer.", modifica=True)
def import_parameters(sesion, path: str, mode: Literal["merge", "replace"] = "merge"):
    """
    path: archivo CSV UTF-8, hasta 2 MB, 1000 filas y 4096 caracteres por campo; acepta las cabeceras de la ventana.
    mode: merge conserva los parámetros ajenos al CSV; replace los elimina salvo que los use el modelo.
    """
    ruta = Path(path).expanduser()
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo CSV: {ruta}")
    with ruta.open("rb") as f:
        contenido = f.read(TOPE_CSV + 1)
    if len(contenido) > TOPE_CSV:
        raise error("INVALID_ARGUMENTS", f"El CSV supera el tope de {TOPE_CSV} bytes.")
    tabla = {p["nombre"]: p for p in sesion.doc.parametros.a_lista()} if mode == "merge" else {}
    vistos = set()
    try:
        lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig"), newline=""), strict=True)
        cabeceras = lector.fieldnames or []
        if (not ("Name" in cabeceras or "Nombre" in cabeceras)
                or not ("Expression" in cabeceras or "Expresión" in cabeceras)
                or len(cabeceras) != len(set(cabeceras))):
            raise error("INVALID_ARGUMENTS", "El CSV requiere columnas Name y Expression (o Nombre y Expresión), sin duplicados.")
        for i, fila in enumerate(lector, 1):
            if i > TOPE_FILAS or None in fila or any(v is None or len(v) > TOPE_CAMPO for v in fila.values()):
                raise error("INVALID_ARGUMENTS", "El CSV tiene demasiadas filas, campos largos o columnas incompletas.")
            nombre = (fila.get("Name") or fila.get("Nombre") or "").strip()
            expresion = (fila.get("Expression") or fila.get("Expresión") or "").strip()
            unidad = (fila.get("Unit") or fila.get("Unidad") or "").strip().lower()
            comentario = (fila.get("Comments") or fila.get("Comentario") or "").strip()
            validar_nombre(nombre)
            if nombre in vistos or not expresion or (unidad and unidad not in UNIDADES):
                raise error("INVALID_ARGUMENTS", f"Fila {i}: nombre duplicado, expresión vacía o unidad desconocida.")
            vistos.add(nombre)
            tipo = UNIDADES[unidad][0] if unidad else ESCALAR
            # Como la ventana, Unit define la magnitud; las expresiones sin unidad usan mm/grados internos.
            tabla[nombre] = {"nombre": nombre, "expresion": expresion, "tipo": tipo, "comentario": comentario}
    except (UnicodeError, csv.Error, RecursionError) as e:
        raise error("INVALID_ARGUMENTS", f"CSV inválido: {e}") from None
    if not vistos:
        raise error("INVALID_ARGUMENTS", "El CSV no contiene parámetros.")
    nueva = TablaParametros.desde_lista(list(tabla.values()))
    sesion.doc.aplicar_parametros(nueva)
    return {"count": len(vistos), "parameters": info_parametros(sesion.doc)}
