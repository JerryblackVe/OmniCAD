"""Intercambio CSV de parámetros con el formato que usa la ventana."""
import csv
import io
import os
import tempfile
from pathlib import Path
from typing import Literal

from ..timeline.operaciones import OpBoceto
from ..timeline.parametros import ESCALAR, TEXTO, ErrorExpresion, TablaParametros, tipo_de_unidad, validar_nombre
from .errores import error
from .herramientas_parametros import info_parametros, valor_visible
from .registro import herramienta
from .sesion import borrar_carpetas, crear_carpeta

TOPE_CSV = 2_000_000
TOPE_FILAS = 1000
TOPE_CAMPO = 4096
_COLUMNAS = ["Name", "Unit", "Expression", "Value", "Comments", "Favorite"]


@herramienta("export_parameters", "parametros", "Exporta los parámetros de usuario a CSV (Name, Unit, Expression, Value, "
             "Comments, Favorite), como Fusion. Las cotas y los valores de los pasos no salen: son del modelo.")
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
    cotas = {c.nombre for o in sesion.doc.operaciones if isinstance(o, OpBoceto) for c in o.boceto.cotas.values()}
    propios = [p for p in sesion.doc.parametros if p.nombre not in cotas and p.op is None]    # los dN salen del modelo
    for p in propios:
        escritor.writerow([p.nombre, p.texto_unidad, p.expresion, valor_visible(p, valores), p.comentario,
                           "true" if p.favorito else "false"])
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
    return {"path": str(ruta.resolve()), "count": len(propios), "size_bytes": ruta.stat().st_size}


def leer_csv(path):
    """Las filas de un CSV de parámetros: [{nombre, expresion, tipo, comentario, unidad, favorito}]. Valida la forma del
    archivo, no las expresiones, que pueden citar parámetros del documento."""
    ruta = Path(path).expanduser()
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo CSV: {ruta}")
    with ruta.open("rb") as f:
        contenido = f.read(TOPE_CSV + 1)
    if len(contenido) > TOPE_CSV:
        raise error("INVALID_ARGUMENTS", f"El CSV supera el tope de {TOPE_CSV} bytes.")
    filas = {}
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
            try:
                tipo = tipo_de_unidad(unidad) if unidad else ESCALAR
            except ErrorExpresion:
                raise error("INVALID_ARGUMENTS", f"Fila {i}: unidad desconocida «{unidad}».") from None
            if nombre in filas or not expresion:
                raise error("INVALID_ARGUMENTS", f"Fila {i}: nombre duplicado o expresión vacía.")
            if tipo == TEXTO and len(expresion) > 1 and expresion[0] == expresion[-1] == "'":
                expresion = expresion[1:-1]       # Fusion escribe el texto entre comillas simples
            filas[nombre] = {"nombre": nombre, "expresion": expresion, "tipo": tipo, "comentario": comentario,
                             "favorito": (fila.get("Favorite") or "").strip().lower() == "true"}
            if unidad and tipo != TEXTO:
                filas[nombre]["unidad"] = unidad
    except (UnicodeError, csv.Error, RecursionError) as e:
        raise error("INVALID_ARGUMENTS", f"CSV inválido: {e}") from None
    if not filas:
        raise error("INVALID_ARGUMENTS", "El CSV no contiene parámetros.")
    return list(filas.values())


def importar_filas(doc, filas, reemplazar=False):
    """Agrega o actualiza `filas` por nombre; `reemplazar` saca además los parámetros de usuario que no vienen. Una fila
    tiene que dar la magnitud de su unidad, como lo que se escribe a mano."""
    tabla = {p["nombre"]: p for p in doc.parametros.a_lista()}
    cotas = {c.nombre for o in doc.operaciones if isinstance(o, OpBoceto) for c in o.boceto.cotas.values()}
    if reemplazar:
        tabla = {n: p for n, p in tabla.items() if p.get("op") or n in cotas}
    tabla.update({f["nombre"]: f for f in filas})
    nueva = TablaParametros.desde_lista(list(tabla.values()))
    for f in filas:
        nueva.validar(f["nombre"])
    doc.aplicar_parametros(nueva)


@herramienta("import_parameters", "parametros", "Importa parámetros CSV con validación de expresiones y unidades. "
             "merge agrega o actualiza por nombre; replace reemplaza los de usuario. names elige cuáles, como la lista "
             "Parámetros seleccionados de Fusion; preview solo los lista. Un solo deshacer.", modifica=True)
def import_parameters(sesion, path: str, mode: Literal["merge", "replace"] = "merge", names: list[str] | None = None,
                      preview: bool = False):
    """
    path: archivo CSV UTF-8, hasta 2 MB, 1000 filas y 4096 caracteres por campo; acepta las cabeceras de la ventana y de Fusion.
    mode: merge conserva los parámetros ajenos al CSV; replace los elimina salvo que los use el modelo.
    names: nombres a importar; vacío = todos los del CSV.
    preview: true devuelve las filas del CSV sin importar nada.
    """
    filas = leer_csv(path)
    if preview:
        return {"count": len(filas), "rows": [{"name": f["nombre"], "unit": f.get("unidad", ""), "expression": f["expresion"],
                                               "comment": f["comentario"]} for f in filas]}
    if names:
        faltan = set(names) - {f["nombre"] for f in filas}
        if faltan:
            raise error("INVALID_ARGUMENTS", f"El CSV no tiene: {', '.join(sorted(faltan))}.")
        filas = [f for f in filas if f["nombre"] in names]
    importar_filas(sesion.doc, filas, mode == "replace")
    return {"count": len(filas), "parameters": info_parametros(sesion.doc)}
