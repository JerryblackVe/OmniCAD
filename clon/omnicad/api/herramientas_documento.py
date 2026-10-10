# -*- coding: utf-8 -*-
"""Herramientas del grupo "documento": archivo, escena, timeline, deshacer y rehacer."""
import copy
import re
from pathlib import Path
from typing import Literal

from ..io_archivos.exportar import FORMATOS, exportar
from ..nucleo import geometria as geo
from ..timeline import ops_chapa, parametros
from .registro import herramienta
from .errores import ErrorAPI, error
from .sesion import borrar_carpetas, crear_carpeta

# Extensiones que escribe export (las de io_archivos.exportar, sus alias y el .dxf del patrón plano).
FORMATOS_EXPORTACION = {f".{f}" for f in FORMATOS} | {".stp", ".igs", ".brp", ".dxf"}

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


# Tipos de unión (ENSAMBLAR) con los nombres de Fusion en inglés; claves de sus valores (grados y mm).
TIPOS_UNION = {"rigida": "rigid", "revolucion": "revolute", "deslizante": "slider", "cilindrica": "cylindrical",
               "pasador_ranura": "pin_slot", "planar": "planar", "bola": "ball"}
_VALORES_UNION = {"giro": "rotation", "giro2": "rotation2", "giro3": "rotation3", "desliz": "slide",
                  "desliz2": "slide2"}


def _info_componentes(sesion, estado):
    """Componentes (ENSAMBLAR › Nuevo componente, STEP con estructura, Insertar diseño): solo lectura del estado."""
    salida = []
    for k, c in estado.componentes.items():
        matriz = c.get("matriz")
        salida.append({"id": k, "name": c.get("nombre") or k, "parent": c.get("padre") or None,
                       "grounded": bool(c.get("fijo")),
                       "bodies": [b.id for b in estado.cuerpos.values() if (b.componente or "") == k],
                       "transform": [[round(float(v), 6) + 0.0 for v in fila] for fila in matriz]
                       if matriz is not None else None})
    return salida


def _info_uniones(estado):
    """Uniones calculadas (ENSAMBLAR › Unión): tipo, componentes y valores de su movimiento."""
    return [{"id": k, "name": u.get("nombre") or k, "type": TIPOS_UNION.get(u.get("tipo"), u.get("tipo")),
             "component1": u.get("comp1") or None, "component2": u.get("comp2") or None,
             "moves": list(u.get("componentes") or []),
             "values": {_VALORES_UNION.get(n, n): _r(v) for n, v in (u.get("valores") or {}).items()}}
            for k, u in estado.uniones.items()]


def _resumen(sesion):
    from .herramientas_parametros import info_parametros   # import diferido: "documento" se registra primero
    doc = sesion.doc
    estado = doc.estado_final
    return {"name": doc.nombre, "path": doc.ruta, "modified": doc.modificado,
            "units": {"length": "mm", "angle": "deg"},
            "bodies": [_info_cuerpo(sesion, c) for c in estado.cuerpos.values()],
            "sketches": [_info_boceto(sesion, b) for b in estado.bocetos.values()],
            "components": _info_componentes(sesion, estado), "joints": _info_uniones(estado),
            "rigid_groups": [list(g) for g in estado.grupos_rigidos],
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


def _nombres_parametros(doc):
    try:
        return doc.parametros.valores()
    except parametros.ErrorExpresion:
        return {}


def _valores_json(op, nombres):
    """Cuánto da cada expresión del paso (mm o grados, según la unidad que escribió): `params` guarda el texto
    («5 * placa») para ver de qué parámetro depende; esto, el valor con los parámetros actuales."""
    claves = [k for k in op.EXPRESIONES if k in op.p]
    campos = getattr(op, "CAMPOS", None)
    if isinstance(campos, dict):                         # primitiva: las medidas de su forma y la posición
        claves += [k for k in campos.get(op.p.get("forma"), []) + ["x", "y", "z"] if k in op.p and k not in claves]
    valores = {}
    for k in claves:
        v = op.p[k]
        if isinstance(v, bool) or not isinstance(v, (str, int, float)) or v == "":
            continue
        try:
            valores[k] = round(parametros.evaluar(v, parametros.ESCALAR, nombres), 6)
        except (parametros.ErrorExpresion, TypeError, ValueError):
            continue
    return valores


def _tiene_referencias(v):
    """True si `v` es una referencia persistente a cara/arista (`nucleo.referencias`) o una lista de ellas."""
    if isinstance(v, dict):
        return "firma" in v and "tipo" in v
    return isinstance(v, list) and bool(v) and all(_tiene_referencias(x) for x in v)


def _paso_info(op):
    return {"id": op.id, "name": op.nombre, "type": op.TIPO}


@herramienta("get_scene_info", "documento", "Resumen del documento: nombre, archivo, cambios sin guardar, unidades, "
             "cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), "
             "componentes (id, nombre, fijo, cuerpos, matriz 4×4 en mm), uniones (tipo, componente 1 que se mueve "
             "y 2, valores: rotation en grados, slide en mm), grupos rígidos, cantidad de pasos del timeline y "
             "parámetros.")
def get_scene_info(sesion):
    return _resumen(sesion)


def _exigir_sin_cambios(sesion, discard):
    """Misma regla con y sin ventana: no se tira trabajo sin guardar salvo que se pida (Document.close(False))."""
    if sesion.doc.modificado and not discard:
        raise error("UNSAVED_CHANGES", f"«{sesion.doc.nombre}» tiene cambios sin guardar.")


@herramienta("new_document", "documento", "Empieza un documento vacío en lugar del actual. Si el actual tiene cambios "
             "sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta).", modifica=True,
             transaccion=False)
def new_document(sesion, name: str = "Sin título", discard: bool = False):
    """
    name: nombre del documento nuevo.
    discard: true para descartar los cambios sin guardar del documento actual.
    """
    _exigir_sin_cambios(sesion, discard)
    sesion.nuevo(name)
    return {"name": sesion.doc.nombre}


_UNIDADES_MALLA = {"mm": "mm", "cm": "cm", "m": "m", "in": "pulgadas", "ft": "pies"}


@herramienta("open_document", "documento", "Abre un archivo y lo deja como documento activo: proyecto .omnicad (o "
             ".fclone), o como documento nuevo con un paso de importación STEP (.step/.stp, con nombres, colores y "
             "componentes), IGES (.iges/.igs), malla (.stl, .obj, .3mf, .ply), DXF (boceto en XY), BREP (.brep/.brp, "
             "como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base; "
             "el historial, los parámetros y los nombres de los cuerpos no se leen). Si el actual tiene cambios "
             "sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta). Para meter el archivo en el "
             "documento actual: insert_file.", modifica=True,
             transaccion=False)
def open_document(sesion, path: str, mesh_units: Literal["mm", "cm", "m", "in", "ft"] = "mm", discard: bool = False):
    """
    path: ruta del archivo.
    mesh_units: unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
    discard: true para descartar los cambios sin guardar del documento actual.
    """
    _exigir_sin_cambios(sesion, discard)
    sesion.abrir(path, _UNIDADES_MALLA[mesh_units])
    for op, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False):
        if r.estado in ("error", "aviso"):
            sesion.avisar(f"{op.nombre} ({op.id}) [{ESTADOS[r.estado]}]: {r.mensaje}")
    return _resumen(sesion)


@herramienta("insert_file", "documento", "Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline "
             "(Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla "
             ".stl/.obj/.3mf/.ply, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion) u otro diseño "
             ".omnicad/.fclone (entra como componente). El contenido se copia "
             "dentro de la receta. Para abrirlo como documento nuevo: open_document.", modifica=True)
def insert_file(sesion, path: str, mesh_units: Literal["mm", "cm", "m", "in", "ft"] = "mm", name: str | None = None):
    """
    path: ruta del archivo a insertar.
    mesh_units: unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
    name: nombre del paso en el timeline; vacío = «Importar archivo.ext» / «Insertar archivo».
    """
    from ..io_archivos import abrir_externo
    ruta = Path(path).expanduser()
    if ruta.suffix.lower() not in abrir_externo.INSERTABLES:
        raise error("UNSUPPORTED_FILE_TYPE", f"Formato no soportado para insertar: {ruta.suffix or '(sin extensión)'}."
                    f" Se insertan: {', '.join(abrir_externo.INSERTABLES)}.",
                    "Un .dxf o .brep se abre como documento nuevo con open_document.")
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
    doc = sesion.doc
    op = abrir_externo.operacion_para_insertar(ruta, doc.nuevo_id(), _UNIDADES_MALLA[mesh_units])
    if name and name.strip():
        op.nombre = name.strip()
    antes = set(doc.estado_final.cuerpos)
    r = doc.agregar(op)
    nuevos = [c for c in doc.estado_final.cuerpos if c not in antes]
    return {"id": op.id, "name": op.nombre, "type": op.TIPO, "status": r.estado, "message": r.mensaje,
            "new_bodies": nuevos, "bodies": list(doc.estado_final.cuerpos)}


@herramienta("save_document", "documento", "Guarda el documento como proyecto .omnicad. Sin path, guarda en su "
             "archivo actual. Crea las carpetas que falten (create_folders=false para que falle con FILE_NOT_FOUND). "
             "No reemplaza otro archivo existente salvo con overwrite=true.")
def save_document(sesion, path: str | None = None, overwrite: bool = False, create_folders: bool = True):
    """
    path: ruta del archivo; si no termina en .omnicad se le agrega. Vacío = el archivo actual del documento.
    overwrite: true para reemplazar un archivo existente que no es el actual.
    create_folders: true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
    """
    final = sesion.guardar(path, overwrite, crear_carpetas=create_folders)
    return {"path": str(final.resolve()), "name": sesion.doc.nombre}


def _cuerpo_chapa(sesion, bodies):
    """El cuerpo cuyo patrón plano va al .dxf: el elegido (de chapa o su patrón plano) o el único de chapa."""
    if bodies:
        cuerpos = [sesion.cuerpo(b) for b in bodies]
    else:
        cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if ops_chapa.es_chapa(c)]
        if not cuerpos:
            raise error("NOTHING_TO_EXPORT", "No hay cuerpos de chapa: el .dxf exporta el patrón plano de uno.")
    if len(cuerpos) > 1:
        raise error("INVALID_ARGUMENTS", "El .dxf lleva el patrón plano de UN cuerpo de chapa: elegí uno en bodies.")
    c = cuerpos[0]
    if getattr(c, "chapa", None) is None:
        raise error("INVALID_FORMAT", f"«{sesion.nombre_cuerpo(c)}» no es de chapa: el .dxf exporta el patrón plano "
                    "de un cuerpo de chapa (o de su patrón plano).", "Para un sólido común usá .step o .stl.")
    return c


@herramienta("export", "documento", "Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, "
             ".ply (mallas), .glb/.gltf (glTF 2.0 para web y realidad aumentada: malla con el color y el acabado de "
             "cada cuerpo como material PBR, en metros y con Y arriba), .step/.stp, .iges/.igs, .brep (sólidos "
             "exactos) o .dxf (patrón plano de un cuerpo de chapa). Crea las carpetas que falten "
             "(create_folders=false para que falle con FILE_NOT_FOUND).")
def export(sesion, path: str, bodies: list[str] | None = None, overwrite: bool = False, create_folders: bool = True):
    """
    path: ruta del archivo a escribir.
    bodies: ids o nombres de los cuerpos; vacío = todos los cuerpos del final del timeline. En .dxf, un solo
        cuerpo de chapa o su patrón plano (vacío = el único cuerpo de chapa que haya).
    overwrite: true para reemplazar el archivo si ya existe.
    create_folders: true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
    """
    ruta = Path(path)
    dxf = ruta.suffix.lower() == ".dxf"
    if dxf:
        cuerpos = [_cuerpo_chapa(sesion, bodies)]
    else:
        cuerpos = ([sesion.cuerpo(b) for b in bodies] if bodies
                   else ops_chapa.cuerpos_del_modelo(sesion.doc.estado_final))   # sin patrones planos
    if ruta.exists() and not overwrite:
        raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
    if ruta.suffix.lower() not in FORMATOS_EXPORTACION:    # antes de crear carpetas para nada
        raise error("INVALID_FORMAT", f"Formato no soportado: {ruta.suffix or '(sin extensión)'} (usá "
                    f"{', '.join(sorted(FORMATOS_EXPORTACION))}).")
    nuevas = crear_carpeta(ruta.parent) if create_folders else []
    if not ruta.parent.is_dir():
        raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}",
                    "export crea las carpetas que faltan con create_folders=true.")
    try:
        resultado = _exportar_a(sesion, cuerpos, ruta, dxf)
    except BaseException:
        borrar_carpetas(nuevas)
        raise
    if nuevas:
        sesion.avisar(f"Se creó la carpeta {ruta.parent}.")
    return resultado


def _exportar_a(sesion, cuerpos, ruta, dxf):
    if dxf:                                  # como CHAPA › Exportar DXF del patrón plano, con sus valores por defecto
        ops_chapa.exportar_dxf(sesion.doc.estado_final, cuerpos[0].id, ruta, centros=True, extensiones=False)
        return {"path": str(ruta.resolve()), "format": "dxf", "bodies": [cuerpos[0].id],
                "size_bytes": ruta.stat().st_size}
    n = exportar(cuerpos, ruta, propiedades=sesion.doc.propiedades)
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
             "suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje, parámetros tal como se guardaron "
             "(params: expresiones como «5 * placa»), cuánto da cada expresión con los parámetros actuales (values, "
             "en mm o grados) y, en primitivas y Mover, qué campo guardado corresponde a cada argumento de la "
             "herramienta (aliases: length → ancho = X, width → largo = Y…), que edit_feature también acepta.")
def get_timeline(sesion, include_params: bool = True):
    """
    include_params: false para omitir los parámetros de cada paso (respuesta más corta).
    """
    doc = sesion.doc
    nombres = _nombres_parametros(doc) if include_params else {}
    pasos = []
    for i, (op, r) in enumerate(zip(doc.operaciones, doc.resultados, strict=False)):
        paso = dict(_paso_info(op), index=i, suppressed=op.suprimida, status=ESTADOS.get(r.estado, r.estado),
                    message=r.mensaje)
        if include_params:
            paso["params"] = _params_json(op)
            paso["values"] = _valores_json(op, nombres)
            alias = _alias_del_paso(op)
            if alias:
                paso["aliases"] = alias
        pasos.append(paso)
    return {"steps": pasos, "marker": doc.marcador}


# Nombres de las herramientas que edit_feature acepta además de los de la receta (que no cambian).
_ALIAS = {
    "primitiva": {"length": "ancho", "width": "largo", "height": "alto", "radius": "radio",
                  "major_radius": "radio_mayor", "minor_radius": "radio_menor"},
    "mover": {"pivot": "pivote"},
}
_PIVOTE_ORIGEN = {"tipo": "punto", "id": "O"}


def _alias_del_paso(op):
    """{argumento de la herramienta: campo guardado} que valen para ESTE paso (en una caja, length → ancho, que es
    el tamaño en X). Así get_timeline dice qué campo es qué sin tener que conocer la receta."""
    alias = _ALIAS.get(op.TIPO, {})
    if op.TIPO == "primitiva":
        campos = getattr(op, "CAMPOS", {}).get(op.p.get("forma"), [])
        alias = {a: c for a, c in alias.items() if c in campos}
    return dict(alias)


def _traducir_alias(op, params):
    alias = _ALIAS.get(op.TIPO, {})
    salida = {}
    for k, v in params.items():
        clave = alias.get(k, k)
        if clave in salida:
            otro = next(a for a, c in alias.items() if c == clave)
            raise error("INVALID_ARGUMENTS", f"{otro} y {clave} son el mismo campo: indicá uno solo.")
        salida[clave] = v
    return salida


def _pivote(valor):
    """Valor de 'pivote' de un paso Mover: None (centro), el origen o una referencia a un punto o vértice. Las
    demás formas cortas (punto de construcción, de boceto…) las traduce `traducir_referencias`."""
    if valor is None or (isinstance(valor, str) and valor.strip().lower() in ("center", "centro", "")):
        return None
    if isinstance(valor, str) and valor.strip().lower() in ("origin", "origen"):
        return dict(_PIVOTE_ORIGEN)
    if isinstance(valor, dict) and "tipo" in valor and valor.get("tipo") not in ("punto", "vertice", "punto_boceto"):
        raise error("INVALID_ARGUMENTS", f"pivote no acepta {valor!r}: tiene que ser un punto.",
                    "pivote acepta 'center', 'origin', un punto de construcción, {'sketch': …, 'point': n} o una "
                    "referencia {'tipo': 'punto', 'id': 'O'}.")
    return valor


def _exigir_tipos(op, params):
    """Un campo que guarda una referencia o una lista (por defecto None o lista, y no es una expresión) no acepta un
    texto ni un número: sin este control el paso fallaba con «Error inesperado: string indices must be integers»."""
    for k, v in params.items():
        defecto = op.PARAMS.get(k)
        if k in op.EXPRESIONES or v is None or not (defecto is None or isinstance(defecto, list)):
            continue
        if isinstance(v, (dict, list)) if defecto is None else isinstance(v, list):
            continue
        raise error("INVALID_ARGUMENTS", f"«{k}» del paso «{op.nombre}» guarda "
                    f"{'una referencia (punto, eje, plano, cara…)' if defecto is None else 'una lista'}, "
                    f"no {v!r}.", "Mirá el formato con get_timeline o describe_operation; null = valor por defecto.")


@herramienta("edit_feature", "documento", "Cambia parámetros de un paso del timeline (conserva su id) y recalcula. "
             "Si el paso u otro posterior queda con error, el cambio se descarta. Usa los nombres de get_timeline; "
             "en primitivas también acepta los de las herramientas: length (= ancho, X), width (= largo, Y), "
             "height (= alto, Z), radius (= radio), major_radius, minor_radius. En pasos Mover, pivot/pivote acepta "
             "'center' u 'origin'. Devuelve params (lo guardado, con sus expresiones) y values (cuánto da cada una, en mm o "
             "grados). Los campos que guardan una referencia (pivote, eje, plano, cara…) aceptan la referencia guardada "
             "o las formas cortas que no dependen de la pieza terminada: \"XY\", \"Z\", \"O\", construcción y bocetos "
             "por id o nombre, {\"sketch\": …, \"point\" | \"curve\" | \"profile\": …}, {\"body\": …} y nombres de "
             "cuerpo en los campos de ids de cuerpo; no aceptan ids de find_faces ni selectores.", modifica=True)
def edit_feature(sesion, feature: str, params: dict):
    """
    feature: id (p. ej. "op3") o nombre del paso.
    params: parámetros a cambiar, con los nombres que muestra get_timeline, p. ej. {"distancia": "15 mm"}.
    """
    from .herramientas_avanzado import traducir_referencias     # diferido: no cambia el orden del catálogo
    op = sesion.paso(feature)
    params = _traducir_alias(op, params)
    desconocidos = [k for k in params if k not in op.PARAMS]
    if desconocidos:
        alias = _ALIAS.get(op.TIPO)
        extra = f" También acepta: {', '.join(f'{a} (= {c})' for a, c in alias.items())}." if alias else ""
        raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» ({op.TIPO}) no tiene: {', '.join(desconocidos)}.",
                    f"Parámetros de '{op.TIPO}': {', '.join(op.PARAMS)}.{extra}")
    if op.TIPO == "mover" and "pivote" in params:
        params["pivote"] = _pivote(params["pivote"])
    params, _ = traducir_referencias(sesion, type(op), params, actuales=op.p, elementos=False)
    _exigir_tipos(op, params)
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
    if nueva.TIPO == "patron" and {"d1", "d2", "angulo", "distribucion"} & set(params):
        sesion.avisar(f"«{nueva.nombre}»: {nueva.aclaracion_distancias()}")
    return dict(_paso_info(nueva), params=_params_json(nueva),
                values=_valores_json(nueva, _nombres_parametros(sesion.doc)))


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


def _exigir_no_id(nombre, id_propio):
    """Un nombre con forma de id (op3, op3.c1) taparía al paso o cuerpo con ese id: la búsqueda mira ids primero."""
    if re.fullmatch(r"op\d+(\.c\d+)?", nombre, re.IGNORECASE) and nombre.casefold() != id_propio.casefold():
        raise error("INVALID_ARGUMENTS", f"«{nombre}» tiene la forma de un id de paso o de cuerpo (op3, op3.c1) y se "
                    "confundiría con él.", "Elegí otro nombre, p. ej. «Brazo izquierdo».")


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
            _exigir_no_id(nuevo, op.id)
            anterior = op.nombre
            sesion.doc.renombrar(op.id, nuevo)
            return {"kind": "feature", "id": op.id, "old_name": anterior, "new_name": nuevo}
    try:
        c = sesion.cuerpo(target)
    except ErrorAPI as e:
        if kind == "body" or e.error_kind != "BODY_NOT_FOUND":
            raise
        raise error("NOT_FOUND", f"No existe un paso ni un cuerpo '{target}'.") from None
    _exigir_no_id(nuevo, c.id)
    anterior = sesion.nombre_cuerpo(c)
    sesion.doc.set_propiedad([c.id], "nombre", nuevo)
    return {"kind": "body", "id": c.id, "old_name": anterior, "new_name": nuevo}
