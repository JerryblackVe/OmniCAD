# -*- coding: utf-8 -*-
"""Herramientas del grupo "documento": archivo, escena, timeline, deshacer y rehacer."""
import copy
import re
from pathlib import Path
from typing import Literal

from ..io_archivos.exportar import FORMATOS, cuerpos_de_malla, exportar
from ..nucleo import geometria as geo
from ..nucleo import motor
from ..timeline import ops_chapa, parametros
from ..timeline.documento import ErrorDocumento
from .registro import herramienta
from .errores import ErrorAPI, desde_mensaje, error
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


def _resumen(sesion, resumido=False):
    from .herramientas_calcomania import info_calcomanias
    from .herramientas_parametros import info_parametros   # import diferido: "documento" se registra primero
    doc = sesion.doc
    estado = doc.estado_final
    if resumido:         # solo nombres y cantidades: con decenas de cuerpos el resumen entero pasa de los 100 KB (T-18)
        tipos = {"solido": "solid", "superficie": "surface", "malla": "mesh"}
        return {"name": doc.nombre, "path": doc.ruta, "modified": doc.modificado,
                "units": {"length": "mm", "angle": "deg"},
                "display_units": {"length": doc.unidades["longitud"], "mass": doc.unidades["masa"]},
                "bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c), "type": tipos.get(getattr(c, "tipo", "solido"))}
                           for c in estado.cuerpos.values()],
                "sketches": [{"id": b.op_id, "name": b.nombre} for b in estado.bocetos.values()],
                "decals": [{"id": d["id"], "name": d["name"], "body": d["body"]} for d in info_calcomanias(sesion)],
                "counts": {"bodies": len(estado.cuerpos), "sketches": len(estado.bocetos),
                           "components": len(estado.componentes), "joints": len(estado.uniones),
                           "parameters": len(doc.parametros)},
                "timeline_steps": len(doc.operaciones), "marker": doc.marcador}
    return {"name": doc.nombre, "path": doc.ruta, "modified": doc.modificado,
            "units": {"length": "mm", "angle": "deg"},          # en lo que vienen TODOS los números de la API
            "display_units": {"length": doc.unidades["longitud"], "mass": doc.unidades["masa"]},   # lo que muestra la app
            "bodies": [_info_cuerpo(sesion, c) for c in estado.cuerpos.values()],
            "sketches": [_info_boceto(sesion, b) for b in estado.bocetos.values()],
            "decals": info_calcomanias(sesion),
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
             "parámetros. Con summary=true devuelve solo nombres y cantidades (corto, para modelos grandes).")
def get_scene_info(sesion, summary: bool = False):
    """
    summary: true devuelve solo nombre, ruta, unidades, cuerpos (id, nombre, tipo), bocetos (id, nombre) y cantidades.
    """
    return _resumen(sesion, summary)


@herramienta("select_bodies", "documento", "Selecciona cuerpos en la ventana y los revela en el navegador. "
             "Solo en vivo; una lista vacía limpia la selección. No cambia el documento.")
def select_bodies(sesion, bodies: list[str]):
    """bodies: ids o nombres de los cuerpos a seleccionar; [] limpia la selección."""
    seleccionar = getattr(sesion, "seleccionar_cuerpos", None)
    if seleccionar is None:
        raise error("APP_NOT_RUNNING", "select_bodies necesita la ventana de OmniCAD en vivo.")
    ids = list(dict.fromkeys(sesion.cuerpo(c).id for c in bodies))
    seleccionar(ids)
    return {"selected_bodies": ids}


@herramienta("set_document_units", "documento", "Elige las unidades con que la app MUESTRA las medidas del documento "
             "(el menú «Unidades» de la barra de abajo): longitud en mm, cm, m, in o ft y masa en g, kg o lb. Se guardan "
             "con el proyecto. No cambia el modelo ni los números de la API, que siguen en mm y g; get_scene_info las "
             "informa en display_units. Sin parámetros solo las consulta.", modifica=True, transaccion=False)
def set_document_units(sesion, length: Literal["mm", "cm", "m", "in", "ft"] | None = None,
                       mass: Literal["g", "kg", "lb"] | None = None):
    """
    length: unidad de longitud para mostrar (omitido o null = no cambia).
    mass: unidad de masa para mostrar (omitido o null = no cambia).
    """
    try:
        sesion.doc.fijar_unidades(length, mass)
    except ErrorDocumento as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
    return {"display_units": {"length": sesion.doc.unidades["longitud"], "mass": sesion.doc.unidades["masa"]}}


@herramienta("set_geometry_engine", "documento", "Elige el motor geométrico (Preferencias › Geometría): "
             "«opencascade» (el de siempre) u «omnikernel» (nativo, en Rust). Al cambiarlo el documento se recalcula "
             "entero con el motor nuevo; lo que OmniKernel no hace todavía queda con error MOTOR_SIN_SOPORTE en su "
             "paso. Sin parámetros solo informa el motor activo y la versión de OmniKernel.", modifica=True,
             transaccion=False)
def set_geometry_engine(sesion, engine: Literal["opencascade", "omnikernel"] | None = None):
    """
    engine: motor a usar desde ahora (omitido o null = no cambia).
    """
    if engine is not None and engine != motor.motor_activo():
        try:
            motor.elegir_motor(engine)
        except ValueError as e:
            raise error("INVALID_ARGUMENTS", str(e)) from None
        sesion.doc.recalcular(0)
    fallidos = [{"id": op.id, "name": op.nombre, "message": r.mensaje}
                for op, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False) if r.estado == "error"]
    return {"engine": motor.motor_activo(), "omnikernel_version": motor.version_omnikernel(),
            "failed_steps": fallidos}


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
             "como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base, cada "
             "componente en su lugar del ensamblaje y con una copia ligera por cada repetición; el historial, los "
             "parámetros y los nombres de los cuerpos no se leen; inspect_f3d cuenta qué trae). Si el actual tiene cambios "
             "sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta). Para meter el archivo en el "
             "documento actual: insert_file.", modifica=True,
             transaccion=False)
def open_document(sesion, path: str, mesh_units: Literal["mm", "cm", "m", "in", "ft"] = "mm", discard: bool = False,
                  summary: bool = False):
    """
    path: ruta del archivo.
    mesh_units: unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
    discard: true para descartar los cambios sin guardar del documento actual.
    summary: true devuelve solo nombres y cantidades (como get_scene_info con summary=true), no el detalle de todo.
    """
    _exigir_sin_cambios(sesion, discard)
    sesion.abrir(path, _UNIDADES_MALLA[mesh_units])
    from ..io_archivos import proyecto
    if sesion.doc.ruta and proyecto.autoguardado_pendiente(sesion.doc.ruta):
        sesion.avisar("Este proyecto tiene un autoguardado más nuevo que el archivo (cambios que no se guardaron): "
                      "se abrió el guardado. list_recoverable_documents con recent lo muestra y recover_document "
                      "lo abre.")
    for op, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False):
        if r.estado in ("error", "aviso"):
            sesion.avisar(f"{op.nombre} ({op.id}) [{ESTADOS[r.estado]}]: {r.mensaje}")
    return _resumen(sesion, summary)


@herramienta("insert_file", "documento", "Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline "
             "(Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla "
             ".stl/.obj/.3mf/.ply, B-rep de OpenCascade .brep/.brp, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion y con cada componente en su lugar) u otro diseño "
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
                    "Un .dxf se abre como documento nuevo con open_document.")
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
    doc = sesion.doc
    op = abrir_externo.operacion_para_insertar(ruta, doc.nuevo_id(), _UNIDADES_MALLA[mesh_units])
    if name and name.strip():
        op.nombre = name.strip()
    antes = set(doc.estado_final.cuerpos)
    r = doc.agregar(op)
    nuevos = [c for c in doc.estado_final.cuerpos if c not in antes]
    if ruta.suffix.lower() == ".3mf" and nuevos:
        grupos = len({int(g) for g in getattr(doc.estado_final.cuerpos[nuevos[0]].forma, "grupos", [])})
        if grupos > 1:
            sesion.avisar(f"El 3MF tiene {grupos} objetos: entran como UN cuerpo de malla con un grupo de caras por "
                          "objeto. separate_mesh con by=face_groups los separa en cuerpos.")
    return {"id": op.id, "name": op.nombre, "type": op.TIPO, "status": r.estado, "message": r.mensaje,
            "new_bodies": nuevos, "bodies": list(doc.estado_final.cuerpos)}


@herramienta("insert_derive", "documento", "Deriva de OTRO proyecto .omnicad al documento actual (Insert Derive "
             "de Fusion): los cuerpos, bocetos y parámetros elegidos entran como UN paso del timeline que guarda "
             "la ruta del origen y qué se derivó; al recalcular vuelve a leer el origen (si cambió, se actualiza; "
             "si falta, el paso queda con error). Los parámetros derivados se copian también al documento. "
             "A diferencia de insert_file con un .omnicad (que copia el diseño adentro), la derivación queda "
             "asociada al archivo de origen.", modifica=True)
def insert_derive(sesion, source_path: str, bodies: list[str] | None = None, sketches: list[str] | None = None,
                  parameters: list[str] | None = None, name: str | None = None):
    """
    source_path: ruta del proyecto .omnicad (o .fclone) de origen.
    bodies: ids o nombres de los cuerpos del origen a derivar (get_scene_info del origen los lista).
    sketches: ids o nombres de los bocetos del origen a derivar.
    parameters: nombres de los parámetros del origen a derivar; quedan también como parámetros del documento.
    name: nombre del paso en el timeline; vacío = «Derivación de <archivo>».
    """
    from ..io_archivos import proyecto
    from ..timeline.ops_derivacion import OpDerivacion
    ruta = Path(source_path).expanduser().resolve()
    if ruta.suffix.lower() not in proyecto.EXTENSIONES:
        raise error("UNSUPPORTED_FILE_TYPE", f"insert_derive deriva de un proyecto {proyecto.EXTENSION} (o "
                    f"{'/'.join(proyecto.EXTENSIONES)}); llegó {ruta.suffix or '(sin extensión)'}.",
                    "Para copiar un archivo de otro formato al documento: insert_file.")
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
    try:
        otro = proyecto.abrir(ruta)
    except proyecto.ErrorProyecto as e:
        raise error("IMPORT_FAILED", f"No se pudo leer el proyecto de origen: {e}") from e
    from ..timeline.ops_derivacion import boceto_origen, cuerpo_origen
    bodies, sketches, parameters = list(bodies or []), list(sketches or []), list(parameters or [])
    if not (bodies or sketches or parameters):
        raise error("INVALID_ARGUMENTS", "Elegí al menos un cuerpo, boceto o parámetro del origen "
                    "(bodies, sketches, parameters).")
    for ref in bodies:
        if cuerpo_origen(otro.estado_final, ref) is None:
            raise error("ENTITY_NOT_FOUND", f"El origen no tiene el cuerpo '{ref}'.",
                        "get_scene_info sobre el documento de origen lista sus cuerpos.")
    for ref in sketches:
        if boceto_origen(otro.estado_final, ref) is None:
            raise error("ENTITY_NOT_FOUND", f"El origen no tiene el boceto '{ref}'.")
    for nombre in parameters:
        if nombre not in otro.parametros:
            raise error("ENTITY_NOT_FOUND", f"El origen no tiene el parámetro '{nombre}'.",
                        ", ".join(p.nombre for p in otro.parametros) or "El origen no tiene parámetros.")
    doc = sesion.doc
    op = OpDerivacion(doc.nuevo_id(), name or f"Derivación de {ruta.stem}", archivo=str(ruta), cuerpos=bodies,
                      bocetos=sketches, parametros=parameters)
    antes = set(doc.estado_final.cuerpos)
    r = doc.agregar(op)
    if r.estado == "error":
        raise desde_mensaje(r.mensaje, f"El paso «{op.nombre}» quedó con error: ")
    nuevos = [c for c in doc.estado_final.cuerpos if c not in antes]
    return {"id": op.id, "name": op.nombre, "type": op.TIPO, "status": r.estado, "message": r.mensaje,
            "new_bodies": nuevos, "bodies": list(doc.estado_final.cuerpos), "parameters": parameters,
            "source": str(ruta)}


@herramienta("inspect_f3d", "documento", "Mira un archivo de Fusion 360 (.f3d o .f3z) SIN abrirlo: cuántos cuerpos "
             "guarda su geometría tal cual (bodies_stored, cada uno en las coordenadas de su componente) y cuántos "
             "salen al poner cada componente en su lugar del ensamblaje (bodies_placed), con el volumen de uno y otro "
             "(mm³), qué componentes se mueven y cuáles tienen copias (instancias que comparten la geometría), y lo que "
             "se vio en la escena del archivo. open_document e insert_file abren el archivo con los cuerpos ya "
             "ubicados. Los cuerpos que no se pueden ubicar quedan donde están guardados (unplaced_bodies); los "
             "cuerpos viejos del historial que Fusion deja en el archivo y la escena no muestra no se importan "
             "(discarded_bodies). components[].name es el nombre del componente, si el archivo lo dice.")
def inspect_f3d(sesion, path: str):
    """
    path: ruta del archivo .f3d o .f3z.
    """
    import numpy as np

    from ..io_archivos import f3d_nativo
    ruta = Path(path).expanduser()
    if ruta.suffix.lower() not in (".f3d", ".f3z"):
        raise error("UNSUPPORTED_FILE_TYPE", f"inspect_f3d lee .f3d y .f3z; llegó {ruta.suffix or '(sin extensión)'}.")
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el archivo: {ruta}")
    visto = {}
    try:
        componentes, avisos = f3d_nativo.leer_componentes(ruta, visto)
    except f3d_nativo.ErrorF3D as e:
        raise error("IMPORT_FAILED", str(e)) from e
    filas, guardado, colocado = [], 0.0, 0.0
    for c in componentes:
        vol = geo.volumen(c["forma"]) if c["tipo"] == "solido" else 0.0
        marcos = c["marcos"]
        movido = any(not np.allclose(M, np.eye(4), atol=1e-6) for M in marcos)
        guardado += vol
        colocado += vol * len(marcos)
        filas.append({"block": c["bloque"], "name": c.get("nombre"), "type": c["tipo"], "volume_mm3": _r(vol),
                      "copies": len(marcos),
                      "moved": movido, "positions_mm": [[_r(x) for x in M[:3, 3]] for M in marcos],
                      "rotated": any(not np.allclose(M[:3, :3], np.eye(3), atol=1e-6) for M in marcos)})
    return {"path": str(ruta), "bodies_stored": len(componentes), "bodies_placed": sum(f["copies"] for f in filas),
            "volume_stored_mm3": _r(guardado), "volume_placed_mm3": _r(colocado),
            "components_moved": sum(1 for f in filas if f["moved"]),
            "components_with_copies": sum(1 for f in filas if f["copies"] > 1),
            "unplaced_bodies": visto.get("sin_ubicar", 0), "discarded_bodies": visto.get("descartados", 0),
            "scene": {"nodes": visto.get("nodos", 0), "copies": visto.get("copias", 0),
                      "bodies": visto.get("cuerpos_escena", 0), "bodies_with_mesh": visto.get("cuerpos_con_malla", 0),
                      "blocks": visto.get("bloques", 0), "blocks_placed": visto.get("bloques_ubicados", 0)},
            "components": filas, "warnings": avisos}


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
    if not str(path).strip():
        raise error("INVALID_ARGUMENTS", "path está vacío: tiene que ser la ruta del archivo a escribir, con extensión.")
    ruta = Path(path)
    if ruta.is_dir():
        raise error("INVALID_ARGUMENTS", f"path es una carpeta ({ruta}): tiene que ser un archivo, con extensión.")
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
    formato = {"stp": "step"}.get(ruta.suffix.lower().lstrip("."), ruta.suffix.lower().lstrip("."))
    if formato in ("step", "iges", "brep"):   # B-68: los formatos B-rep dejan afuera las mallas: avisarlo
        omitidas = cuerpos_de_malla(cuerpos)
        if omitidas:
            sesion.avisar(f"{len(omitidas)} cuerpo(s) de malla no se pueden guardar en .{formato} "
                          f"(solo B-rep): {', '.join(sesion.nombre_cuerpo(c) for c in omitidas)} quedaron afuera; "
                          "convertilos antes con convert_mesh si los querés.")
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


def _avisar_duplicado(sesion, nuevo, id_propio, cuerpos):
    """B-54: renombrar a un nombre que ya existe deja dos iguales y la búsqueda por nombre pasa a dar
    AMBIGUOUS_REFERENCE. Se avisa (no se rechaza: las copias de un patrón comparten nombre a propósito)."""
    if cuerpos:
        repetidos = [c.id for c in sesion.doc.estado_final.cuerpos.values()
                     if c.id != id_propio and sesion.nombre_cuerpo(c).casefold() == nuevo.casefold()]
    else:
        repetidos = [o.id for o in sesion.doc.operaciones
                     if o.id != id_propio and o.nombre.casefold() == nuevo.casefold()]
    if repetidos:
        sesion.avisar(f"Ya hay {'un cuerpo' if cuerpos else 'un paso'} llamado «{nuevo}» "
                      f"({', '.join(repetidos)}): buscarlo por nombre va a dar AMBIGUOUS_REFERENCE; usá el id.")


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
            _avisar_duplicado(sesion, nuevo, op.id, cuerpos=False)
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
    _avisar_duplicado(sesion, nuevo, c.id, cuerpos=True)
    anterior = sesion.nombre_cuerpo(c)
    sesion.doc.set_propiedad([c.id], "nombre", nuevo)
    return {"kind": "body", "id": c.id, "old_name": anterior, "new_name": nuevo}


# ---------------------------------------------------------------- recuperación (P21)
@herramienta("list_recoverable_documents", "documento", "Lista los autoguardados pendientes de recuperar "
             "(cambios que no se llegaron a guardar): los de documentos «Sin título» y, si se pasan "
             "`recent`, el autoguardado más nuevo de cada uno de esos proyectos.", modifica=False)
def list_recoverable_documents(sesion, recent: list[str] | None = None):
    """
    recent: rutas de proyectos propios que también revisar; vacío = solo los «Sin título» huérfanos.
    """
    from ..io_archivos import proyecto
    return {"pending": proyecto.pendientes_de_recuperacion(recent or [])}


@herramienta("recover_document", "documento", "Recupera una copia de autoguardado y la deja como documento "
             "activo, como el botón Abrir de «Documentos recuperados»: huérfanos entran como «Recuperado» sin "
             "ruta; con project, guardar a mano pisa el proyecto original. Si el actual tiene cambios sin "
             "guardar falla con UNSAVED_CHANGES, salvo discard=true.", modifica=True, transaccion=False)
def recover_document(sesion, path: str, project: str | None = None, discard: bool = False):
    """
    path: ruta de la copia de autoguardado (de list_recoverable_documents).
    project: ruta del proyecto original si la copia era de un proyecto con ruta; vacío = huérfano.
    discard: true para descartar los cambios sin guardar del documento actual.
    """
    from ..io_archivos import proyecto
    if not Path(path).is_file():
        raise error("FILE_NOT_FOUND", f"No existe el autoguardado: {path}")
    if project is not None and not Path(project).is_file():
        raise error("FILE_NOT_FOUND", f"No existe el proyecto original: {project}")
    _exigir_sin_cambios(sesion, discard)
    try:
        sesion.doc = proyecto.abrir_recuperado(path, project or None)
    except (proyecto.ErrorProyecto, OSError, ValueError) as e:
        raise error("OPERATION_FAILED", f"No se pudo recuperar el autoguardado: {e}") from None
    return _resumen(sesion)


@herramienta("discard_recoverable_document", "documento", "Suprime una copia de autoguardado de la lista de "
             "documentos recuperables (el botón Suprimir de «Documentos recuperados»). Borra SOLO la copia "
             "(*.autoguardado.omnicad), nunca el proyecto guardado ni otro archivo; no cambia el documento abierto.",
             modifica=False)
def discard_recoverable_document(sesion, path: str):
    """
    path: ruta de la copia de autoguardado (de list_recoverable_documents).
    """
    from ..io_archivos import proyecto
    ruta = Path(path)
    if not proyecto.es_copia_de_autoguardado(ruta):
        raise error("INVALID_ARGUMENTS", f"«{ruta.name}» no es una copia de autoguardado (*.autoguardado.omnicad): "
                    "no se borra.", "Las copias salen de list_recoverable_documents (campo backup).")
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", f"No existe el autoguardado: {path}")
    try:
        proyecto.suprimir_copia(ruta)
    except OSError as e:
        raise error("OPERATION_FAILED", f"No se pudo suprimir el autoguardado: {e}") from None
    return {"discarded": str(ruta)}
