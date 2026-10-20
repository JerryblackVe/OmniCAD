"""Configuraciones, comentarios y proyectos recientes del documento."""
import copy
from datetime import datetime
from pathlib import Path
from typing import Literal

from ..timeline.parametros import TablaParametros
from .errores import error
from .registro import herramienta


def _tabla_publica(datos):
    return {"columns": [({"type": "parameter", "name": c["nombre"]} if c["tipo"] == "parametro"
                         else {"type": "suppress", "feature": c["op"]}) for c in datos.get("columnas", [])],
            "rows": [{"name": f["nombre"], "values": list(f["valores"])} for f in datos.get("filas", [])],
            "active": datos.get("activa", "")}


def _validar_tabla(sesion, columns, rows, active):
    columnas, claves = [], set()
    for c in columns:
        if not isinstance(c, dict):
            raise error("INVALID_ARGUMENTS", "Cada columna debe ser un objeto con type y name o feature.")
        if c.get("type") == "parameter" and set(c) == {"type", "name"} and isinstance(c["name"], str):
            if c["name"] not in sesion.doc.parametros:
                raise error("PARAMETER_NOT_FOUND", f"No existe el parámetro «{c['name']}» de la configuración.")
            col = {"tipo": "parametro", "nombre": c["name"]}
        elif c.get("type") == "suppress" and set(c) == {"type", "feature"} and isinstance(c["feature"], str):
            col = {"tipo": "suprimir", "op": sesion.paso(c["feature"]).id}
        else:
            raise error("INVALID_ARGUMENTS", "Columna inválida: usá {type: parameter, name} o {type: suppress, feature}.")
        clave = tuple(col.values())
        if clave in claves:
            raise error("INVALID_ARGUMENTS", "No se puede repetir una columna de configuración.")
        claves.add(clave)
        columnas.append(col)
    filas, nombres = [], set()
    for f in rows:
        if (not isinstance(f, dict) or set(f) != {"name", "values"} or not isinstance(f["name"], str)
                or not f["name"].strip() or not isinstance(f["values"], list)
                or len(f["values"]) != len(columnas)):
            raise error("INVALID_ARGUMENTS", "Cada fila necesita name no vacío y un values por columna.")
        nombre = f["name"].strip()
        if nombre in nombres:
            raise error("INVALID_ARGUMENTS", f"Se repite la configuración «{nombre}».")
        nombres.add(nombre)
        tabla = {p["nombre"]: p for p in sesion.doc.parametros.a_lista()}
        valores = []
        for c, v in zip(columnas, f["values"], strict=True):
            if not isinstance(v, (str, int, float, bool)):
                raise error("INVALID_ARGUMENTS", "Las celdas deben ser expresiones o valores de supresión.")
            texto = str(v).strip()
            if c["tipo"] == "parametro" and texto:
                if isinstance(v, bool) or len(texto) > 4096:
                    raise error("INVALID_ARGUMENTS", "Expresión de configuración inválida o demasiado larga.")
                tabla[c["nombre"]]["expresion"] = texto
            elif c["tipo"] == "suprimir" and texto.lower() not in ("", "sí", "si", "1", "true", "x", "s", "no", "0", "false", "n"):
                raise error("INVALID_ARGUMENTS", "Una supresión debe indicar sí/no o true/false.")
            valores.append(texto)
        TablaParametros.desde_lista(list(tabla.values())).valores()
        filas.append({"nombre": nombre, "valores": valores})
    if active and active not in nombres:
        raise error("INVALID_ARGUMENTS", f"No existe la fila activa «{active}».")
    return {"columnas": columnas, "filas": filas, "activa": active}


@herramienta("manage_configurations", "documento", "Consulta y edita la tabla de variantes de CONFIGURAR. "
             "Solo apply aplica parámetros y supresiones; cada edición o aplicación es un deshacer.", modifica=True)
def manage_configurations(sesion, action: Literal["get", "set", "add_row", "delete_row", "apply", "clear"] = "get",
                          columns: list[dict] | None = None, rows: list[dict] | None = None,
                          row: str | None = None, values: list | None = None, active: str | None = None):
    """
    action: get consulta; set reemplaza; add_row agrega; delete_row borra; apply activa; clear vacía la tabla.
    columns: columnas para set: {"type": "parameter", "name": parámetro} o {"type": "suppress", "feature": id o nombre de paso}.
    rows: filas para set: [{"name": nombre, "values": [expresión o sí/no por columna]}].
    row: nombre de la fila a agregar, borrar o aplicar.
    values: valores por columna para add_row.
    active: nombre activo al guardar set; omitido = sin fila activa. set solo guarda la tabla, no aplica la fila.
    """
    doc = sesion.doc
    actual = _tabla_publica(doc.configuraciones)
    if action == "get":
        return actual
    if action == "set":
        if columns is None or rows is None:
            raise error("INVALID_ARGUMENTS", "set requiere columns y rows.")
        actual = {"columns": columns, "rows": rows, "active": active or ""}
    elif action == "clear":
        actual = {"columns": [], "rows": [], "active": ""}
    elif action == "add_row":
        if row is None or values is None:
            raise error("INVALID_ARGUMENTS", "add_row requiere row y values.")
        actual["rows"].append({"name": row, "values": values})
    else:
        if row is None or not any(f["name"] == row for f in actual["rows"]):
            raise error("INVALID_ARGUMENTS", f"No existe la configuración «{row}».")
        if action == "delete_row":
            actual["rows"] = [f for f in actual["rows"] if f["name"] != row]
            if actual["active"] == row:
                actual["active"] = ""
        else:
            actual["active"] = row
    datos = _validar_tabla(sesion, actual["columns"], actual["rows"], actual["active"])
    if action == "apply":
        doc.aplicar_configuracion(datos, row)
    else:
        doc._guardar_para_deshacer()
        doc.configuraciones = copy.deepcopy(datos)
        doc.modificado = True
        doc._notificar()
    return _tabla_publica(doc.configuraciones)


@herramienta("manage_comments", "documento", "Lista, agrega o borra comentarios del proyecto. "
             "Se guardan con el diseño, pero no entran en deshacer.", modifica=True, transaccion=False)
def manage_comments(sesion, action: Literal["list", "add", "delete"] = "list", text: str | None = None,
                    index: int | None = None):
    """
    action: list consulta, add agrega texto y delete borra por índice.
    text: texto no vacío del comentario para add.
    index: índice del comentario para delete (desde cero).
    """
    doc = sesion.doc
    if action == "add":
        if text is None or not text.strip():
            raise error("INVALID_ARGUMENTS", "El comentario no puede estar vacío.")
        doc.agregar_comentario(text.strip())
    elif action == "delete":
        if index is None or not 0 <= index < len(doc.comentarios):
            raise error("INVALID_ARGUMENTS", "El índice del comentario no existe.")
        doc.borrar_comentario(index)
    return {"comments": [{"index": i, "text": c["texto"], "date": c["fecha"]}
                         for i, c in enumerate(doc.comentarios)]}


@herramienta("list_recent_documents", "documento", "Lista los proyectos recientes existentes, en el orden del panel de datos.")
def list_recent_documents(sesion):
    """
    """
    from .herramientas_preferencias import _ajustes
    rutas = _ajustes().value("recientes", [])
    if isinstance(rutas, str):
        rutas = [rutas] if rutas else []
    documentos = []
    for ruta in rutas or []:
        p = Path(str(ruta))
        if p.is_file():
            documentos.append({"path": str(p), "name": p.stem,
                               "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()})
    return {"documents": documentos}
