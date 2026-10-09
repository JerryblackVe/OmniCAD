# -*- coding: utf-8 -*-
"""Herramientas del grupo "documento": archivo, escena, timeline, deshacer y rehacer."""
import copy
from pathlib import Path
from typing import Literal

from ..io_archivos.exportar import exportar
from ..nucleo import geometria as geo
from .registro import herramienta
from .errores import ErrorAPI, error

# ResultadoPaso.estado → healthState de Fusion (en inglés, como las demás claves).
ESTADOS = {"ok": "ok", "aviso": "warning", "error": "error", "suprimida": "suppressed", "retrocedida": "rolled_back"}
_LARGO_MAXIMO = 200   # textos más largos (B-rep o STEP embebidos) se resumen en get_timeline


def _r(x):
    return None if x is None else round(float(x), 4)


def _info_cuerpo(sesion, c):
    forma, tipo = c.forma, getattr(c, "tipo", "solido")
    if tipo == "malla":
        volumen, area, caja = forma.volumen(), forma.area(), forma.caja()
    else:
        volumen = geo.volumen(forma) if tipo == "solido" else None
        area, caja = geo.area(forma), geo.caja_envolvente(forma)
    info = {"id": c.id, "name": sesion.nombre_cuerpo(c), "type": {"solido": "solid", "superficie": "surface",
                                                                   "malla": "mesh"}.get(tipo, tipo),
            "volume": _r(volumen), "area": _r(area), "bounding_box": None}
    if caja:
        p0, p1 = caja
        info["bounding_box"] = {"min": [_r(v) for v in p0], "max": [_r(v) for v in p1],
                                "size": [_r(b - a) for a, b in zip(p0, p1, strict=True)]}
    return info


def _info_boceto(sesion, b):
    op = next((o for o in sesion.doc.operaciones if o.id == b.op_id), None)
    return {"id": b.op_id, "name": b.nombre, "plane": op.p.get("plano") if op is not None else None,
            "profiles": len(b.perfiles), "solved": bool(getattr(b.solver, "ok", True))}


def _resumen(sesion):
    from .herramientas_parametros import info_parametros   # import diferido: "documento" se registra primero
    doc = sesion.doc
    estado = doc.estado_final
    return {"name": doc.nombre, "path": doc.ruta, "modified": doc.modificado,
            "units": {"length": "mm", "angle": "deg"},
            "bodies": [_info_cuerpo(sesion, c) for c in estado.cuerpos.values()],
            "sketches": [_info_boceto(sesion, b) for b in estado.bocetos.values()],
            "timeline_steps": len(doc.operaciones), "marker": doc.marcador,
            "parameters": info_parametros(doc)}


def _params_json(op):
    params = op.a_dict()["params"]
    for k, v in params.items():
        if isinstance(v, str) and len(v) > _LARGO_MAXIMO:
            params[k] = f"<texto de {len(v)} caracteres>"
        elif k == "cuerpos" and isinstance(v, list) and v and isinstance(v[0], dict) and "brep" in v[0]:
            params[k] = [{c: d for c, d in x.items() if c != "brep"} for x in v]
    return params


def _tiene_referencias(v):
    """True si `v` es una referencia persistente a cara/arista (`nucleo.referencias`) o una lista de ellas."""
    if isinstance(v, dict):
        return "firma" in v and "tipo" in v
    return isinstance(v, list) and bool(v) and all(_tiene_referencias(x) for x in v)


def _paso_info(op):
    return {"id": op.id, "name": op.nombre, "type": op.TIPO}


@herramienta("get_scene_info", "documento", "Resumen del documento: nombre, archivo, cambios sin guardar, unidades, "
             "cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), "
             "cantidad de pasos del timeline y parámetros.")
def get_scene_info(sesion):
    return _resumen(sesion)


@herramienta("new_document", "documento", "Empieza un documento vacío (descarta el actual de la sesión sin guardarlo).",
             modifica=True, transaccion=False)
def new_document(sesion, name: str = "Sin título"):
    """
    name: nombre del documento nuevo.
    """
    sesion.nuevo(name)
    return {"name": sesion.doc.nombre}


@herramienta("open_document", "documento", "Abre un proyecto .omnicad (o .fclone) y lo deja como documento activo.",
             modifica=True, transaccion=False)
def open_document(sesion, path: str):
    """
    path: ruta del archivo de proyecto.
    """
    sesion.abrir(path)
    for op, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False):
        if r.estado in ("error", "aviso"):
            sesion.avisar(f"{op.nombre} ({op.id}) [{ESTADOS[r.estado]}]: {r.mensaje}")
    return _resumen(sesion)


@herramienta("save_document", "documento", "Guarda el documento como proyecto .omnicad. Sin path, guarda en su "
             "archivo actual. No reemplaza otro archivo existente salvo con overwrite=true.")
def save_document(sesion, path: str | None = None, overwrite: bool = False):
    """
    path: ruta del archivo; si no termina en .omnicad se le agrega. Vacío = el archivo actual del documento.
    overwrite: true para reemplazar un archivo existente que no es el actual.
    """
    final = sesion.guardar(path, overwrite)
    return {"path": str(final.resolve()), "name": sesion.doc.nombre}


@herramienta("export", "documento", "Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, "
             ".ply (mallas) o .step/.stp, .iges/.igs, .brep (sólidos exactos).")
def export(sesion, path: str, bodies: list[str] | None = None, overwrite: bool = False):
    """
    path: ruta del archivo a escribir.
    bodies: ids o nombres de los cuerpos; vacío = todos los cuerpos del final del timeline.
    overwrite: true para reemplazar el archivo si ya existe.
    """
    ruta = Path(path)
    cuerpos = [sesion.cuerpo(b) for b in bodies] if bodies else list(sesion.doc.estado_final.cuerpos.values())
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
    n = exportar(cuerpos, ruta)
    resultado = {"path": str(ruta.resolve()), "format": ruta.suffix.lower().lstrip("."),
                 "bodies": [c.id for c in cuerpos], "size_bytes": ruta.stat().st_size}
    if isinstance(n, int):
        resultado["triangles"] = n
    return resultado


def _pila(sesion):
    doc = sesion.doc
    return {"timeline_steps": len(doc.operaciones), "bodies": len(doc.estado_final.cuerpos),
            "can_undo": doc.puede_deshacer(), "can_redo": doc.puede_rehacer()}


@herramienta("undo", "documento", "Deshace el último cambio del documento (cada herramienta que modifica es un paso).",
             modifica=True, transaccion=False)
def undo(sesion):
    if not sesion.doc.puede_deshacer():
        raise error("NOTHING_TO_UNDO", "No hay nada para deshacer.")
    sesion.doc.deshacer()
    return _pila(sesion)


@herramienta("redo", "documento", "Rehace el último cambio deshecho.", modifica=True, transaccion=False)
def redo(sesion):
    if not sesion.doc.puede_rehacer():
        raise error("NOTHING_TO_REDO", "No hay nada para rehacer.")
    sesion.doc.rehacer()
    return _pila(sesion)


@herramienta("get_timeline", "documento", "Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está "
             "suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje y parámetros.")
def get_timeline(sesion, include_params: bool = True):
    """
    include_params: false para omitir los parámetros de cada paso (respuesta más corta).
    """
    doc = sesion.doc
    pasos = []
    for i, (op, r) in enumerate(zip(doc.operaciones, doc.resultados, strict=False)):
        paso = dict(_paso_info(op), index=i, suppressed=op.suprimida, status=ESTADOS.get(r.estado, r.estado),
                    message=r.mensaje)
        if include_params:
            paso["params"] = _params_json(op)
        pasos.append(paso)
    return {"steps": pasos, "marker": doc.marcador}


@herramienta("edit_feature", "documento", "Cambia parámetros de un paso del timeline (conserva su id) y recalcula. "
             "Si el paso u otro posterior queda con error, el cambio se descarta.", modifica=True)
def edit_feature(sesion, feature: str, params: dict):
    """
    feature: id (p. ej. "op3") o nombre del paso.
    params: parámetros a cambiar, con los nombres que muestra get_timeline, p. ej. {"distancia": "15 mm"}.
    """
    op = sesion.paso(feature)
    desconocidos = [k for k in params if k not in op.PARAMS]
    if desconocidos:
        raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» ({op.TIPO}) no tiene: {', '.join(desconocidos)}.",
                    f"Parámetros de '{op.TIPO}': {', '.join(op.PARAMS)}.")
    if not params:
        raise error("INVALID_ARGUMENTS", "No se indicó ningún parámetro para cambiar.",
                    f"Parámetros de '{op.TIPO}': {', '.join(op.PARAMS)}.")
    # Las caras/aristas de un paso son referencias PERSISTENTES (dicts con firma), no selectores. Un selector no se
    # puede traducir acá: se evaluaría sobre la pieza terminada y no sobre la de antes del paso. Sin este control el
    # paso fallaba con un error interno («string indices must be integers»), visto en la prueba real del 2026-10-09.
    for k, v in params.items():
        if _tiene_referencias(op.p.get(k)) and not _tiene_referencias(v):
            raise error("INVALID_ARGUMENTS", f"«{k}» del paso «{op.nombre}» guarda referencias a caras o aristas, no "
                        "texto: con edit_feature no se cambia.",
                        "Borrá el paso (delete_feature) y crealo de nuevo con su herramienta eligiendo con selectores "
                        "(p. ej. shell con faces=\">Z\"), o deshacelo con undo si recién lo creaste.")
    nueva = op.copia()
    nueva.p.update(copy.deepcopy(params))
    sesion.doc.reemplazar(op.id, nueva)
    return dict(_paso_info(nueva), params=_params_json(nueva))


@herramienta("suppress_feature", "documento", "Suprime o reactiva un paso del timeline (suprimido = no se calcula).",
             modifica=True)
def suppress_feature(sesion, feature: str, suppressed: bool = True):
    """
    feature: id o nombre del paso.
    suppressed: true para suprimir, false para reactivar.
    """
    op = sesion.paso(feature)
    if op.suprimida == suppressed:
        sesion.avisar(f"«{op.nombre}» ya estaba {'suprimido' if suppressed else 'activo'}: no cambió nada.")
    else:
        sesion.doc.suprimir(op.id, suppressed)
    return dict(_paso_info(op), suppressed=suppressed)


@herramienta("delete_feature", "documento", "Borra un paso del timeline. No se puede si otro paso lo usa.",
             modifica=True)
def delete_feature(sesion, feature: str):
    """
    feature: id o nombre del paso.
    """
    op = sesion.paso(feature)
    sesion.doc.eliminar(op.id)
    return dict(_paso_info(op), deleted=True)


@herramienta("rename", "documento", "Renombra un paso del timeline o un cuerpo.", modifica=True)
def rename(sesion, target: str, new_name: str, kind: Literal["auto", "feature", "body"] = "auto"):
    """
    target: id o nombre actual del paso o del cuerpo.
    new_name: nombre nuevo (no vacío).
    kind: "feature" o "body" para desambiguar; "auto" busca primero entre los pasos y después entre los cuerpos.
    """
    nuevo = new_name.strip()
    if not nuevo:
        raise error("INVALID_ARGUMENTS", "El nombre nuevo está vacío.")
    if kind in ("auto", "feature"):
        try:
            op = sesion.paso(target)
        except ErrorAPI as e:
            if kind == "feature" or e.error_kind != "FEATURE_NOT_FOUND":
                raise
        else:
            anterior = op.nombre
            sesion.doc.renombrar(op.id, nuevo)
            return {"kind": "feature", "id": op.id, "old_name": anterior, "new_name": nuevo}
    try:
        c = sesion.cuerpo(target)
    except ErrorAPI as e:
        if kind == "body" or e.error_kind != "BODY_NOT_FOUND":
            raise
        raise error("NOT_FOUND", f"No existe un paso ni un cuerpo '{target}'.") from None
    anterior = sesion.nombre_cuerpo(c)
    sesion.doc.set_propiedad([c.id], "nombre", nuevo)
    return {"kind": "body", "id": c.id, "old_name": anterior, "new_name": nuevo}
