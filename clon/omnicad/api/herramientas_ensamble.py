# -*- coding: utf-8 -*-
"""
Herramientas del grupo "ensamble" (ENSAMBLAR de Fusion, `timeline/ops_ensamblar.py`): componentes, fijar,
uniones (las 7 de Fusion y la «como está»), orígenes de unión, accionar uniones, límites de movimiento, grupos
rígidos, vínculos de movimiento y el estudio de movimiento.

Modelo: cada cuerpo pertenece a un componente o a la raíz. Una unión MUEVE el componente 1 (el de `origin1`)
hasta que su marco coincide con el del componente 2 y después aplica su movimiento (rotation, slide…), que se
cambia con drive_joint. Los marcos salen de la geometría elegida:
  - cara plana: origen en el centro de su contorno exterior y Z = la normal (las caras quedan enfrentadas);
  - cara cilíndrica o cónica, o arista circular: un marco de EJE (Z = el eje, X del mundo); dos ejes quedan en el
    mismo sentido (perno en agujero); `flip` invierte eso;
  - detalle del marco de eje: Z = el eje del cilindro/círculo, con la componente mayor POSITIVA (empates: Z, Y, X
    del mundo), y X = el eje del mundo MENOS alineado con Z (empates: X, Y, Z); el origen está sobre el eje, en
    el medio de la cara (el inicio o el fin con snap). O sea: en un cilindro a lo largo de Y, «Z» del marco es
    el eje de ese cilindro (gira el perno), y en uno a lo largo de Z, gira alrededor de +Z del mundo (B-51);
  - un origen de unión (create_joint_origin), un plano, eje o punto de construcción: su propio marco.
Las caras y aristas se eligen como en el resto de la API: selector ('>Z', '%CYLINDER', 'edges:%CIRCLE'…, evaluado
sobre `body1` / `body2`) o id de find_faces / find_edges ('Cuerpo1/F3', 'Cuerpo1/E5'). Lo que se guarda en el
paso es la referencia persistente: la unión sigue a su cara cuando cambia un parámetro.

Componentes, uniones y grupos se nombran por id (el del paso que los creó, p. ej. 'op5') o por nombre; un
componente también por el id o el nombre de uno de sus cuerpos.
"""
import copy
import difflib
from typing import Literal

import numpy as np

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from ..timeline import entidades as ent
from ..timeline.operaciones import Contexto
from ..timeline.ops_chapa import cuerpos_del_modelo
from ..timeline.operaciones import ErrorOperacion
from ..timeline.ops_ensamblar import (MOVIMIENTOS, OpAnclar, OpCapturarPosicion, OpComponente, OpCopiarComponente, ruta_componente,
                                      OpGrupoRigido, OpInsertarDiseno, OpOrigenUnion, OpPosicionInicial, OpRevertirPosicion,
                                      OpRestriccion, OpUnion, OpVinculoMovimiento, _mover_componentes, es_fijo, exigir_numero, grupo_rigido,
                                      limites_expr, pose_de_componente, pose_de_reasignar, poses_de_estudio, principal_de, siguiente_accion)
from ..timeline.parametros import ANGULO, LONGITUD, ErrorExpresion, evaluar
from ..timeline.posicion import Arrastre, pendiente_de
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_documento import ESTADOS, TIPOS_UNION, _VALORES_UNION, _r_chico
from .herramientas_solido import _agregar
from .registro import Expr, herramienta

# La tabla de verdad de los tipos de unión es TIPOS_UNION (ES→EN) de herramientas_documento; acá queda la inversa.
TIPOS = {en: es for es, en in TIPOS_UNION.items()}
A_INGLES = {v: k for k, v in TIPOS.items()}
TipoUnion = Literal["rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar", "ball"]
SNAP = {"center": "centro", "start": "inicio", "end": "fin"}
Snap = Literal["center", "start", "end"]
Eje = Literal["X", "Y", "Z"]
MOVIMIENTO = {en: es for es, en in _VALORES_UNION.items()}
A_MOVIMIENTO = {v: k for k, v in MOVIMIENTO.items()}
Movimiento = Literal["rotation", "rotation2", "rotation3", "slide", "slide2"]
ModoPosicion = Literal["simple", "between_faces", "edge_intersection"]
MODO = {"simple": "simple", "between_faces": "entre_caras", "edge_intersection": "interseccion"}
PUBLICO_MODO = {v: k for k, v in MODO.items()}
_PASOS_CONSTRUCCION = {"origen_union": "plano", "plano": "plano", "eje": "eje", "punto": "punto"}
MAX_PASOS_ESTUDIO = 360

_DESC_TIPOS = ("joint_type: rigid (sin movimiento), revolute (gira alrededor de rotation_axis), slider (desliza "
               "sobre slide_axis), cylindrical (gira y desliza sobre rotation_axis), pin_slot (gira sobre "
               "rotation_axis y desliza sobre slide_axis), planar (desliza en el plano normal a rotation_axis y gira "
               "alrededor de él) o ball (tres giros). ")
_DESC_ORIGEN = ("Cada origen es una cara o arista (selector evaluado sobre body1 / body2, o id de find_faces / "
                "find_edges: 'Cuerpo1/F3', 'Cuerpo1/E5'; para aristas con selector, prefijo 'edges:'), un origen de "
                "unión (create_joint_origin), un plano, eje o punto de construcción (id o nombre) o XY, XZ, YZ. ")


def _r(x):
    return None if x is None else round(float(x), 4) + 0.0


# ---------------------------------------------------------------- búsquedas
def nombre_paso(sesion, name, base, clase, filtro=None):
    """Nombre del paso nuevo: el pedido (no vacío, sin repetir otro paso ni tener forma de id) o «<base><n>»."""
    doc = sesion.doc
    if name is None or not str(name).strip():
        return nombre_nuevo(doc, base, clase, filtro)
    nombre = str(name).strip()
    if any(o.nombre.casefold() == nombre.casefold() for o in doc.operaciones):
        raise error("INVALID_ARGUMENTS", f"Ya hay un paso llamado «{nombre}»: elegí otro nombre.",
                    "get_timeline lista los pasos con su nombre.")
    if nombre.lower().startswith("op") and nombre[2:].replace(".c", "", 1).isdigit():
        raise error("INVALID_ARGUMENTS", f"«{nombre}» tiene la forma de un id (op3, op3.c1) y se confundiría con él.")
    return nombre


def _nombre_comp(estado, k):
    return str(estado.componentes.get(k, {}).get("nombre") or k)


def _lista_componentes(estado):
    return ", ".join(f"{_nombre_comp(estado, k)} ({k})" for k in estado.componentes) or "ninguno"


def componente(sesion, ref):
    """Id del componente que nombra `ref`: su id, su nombre (sin distinguir mayúsculas) o el id / nombre de uno de
    sus cuerpos. COMPONENT_NOT_FOUND con la lista de los que hay."""
    estado = sesion.doc.estado_final
    texto = str(ref).strip()
    if texto in estado.componentes:
        return texto
    hallados = [k for k in estado.componentes if _nombre_comp(estado, k).casefold() == texto.casefold()]
    if len(hallados) > 1:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} componentes llamados «{texto}»: "
                    + ", ".join(hallados) + ".")
    if hallados:
        return hallados[0]
    try:
        c = sesion.cuerpo(texto)
    except ErrorAPI:
        c = None
    if c is not None:
        if c.componente:
            return c.componente
        raise error("COMPONENT_NOT_FOUND", f"El cuerpo «{sesion.nombre_cuerpo(c)}» está en la raíz, no en un "
                    "componente.", f"Componentes: {_lista_componentes(estado)}.")
    opciones = list(estado.componentes) + [_nombre_comp(estado, k) for k in estado.componentes]
    parecidos = difflib.get_close_matches(texto, opciones, n=3, cutoff=0.5)
    raise error("COMPONENT_NOT_FOUND", f"No existe el componente «{texto}». Componentes: "
                f"{_lista_componentes(estado)}.",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))


def _paso_de_clase(sesion, ref, clases, kind, que, plural):
    doc = sesion.doc
    texto = str(ref).strip()
    candidatos = [o for o in doc.operaciones if isinstance(o, clases)]
    hallados = [o for o in candidatos if o.id == texto] or \
        [o for o in candidatos if o.nombre.casefold() == texto.casefold()]
    if len(hallados) == 1:
        return hallados[0]
    if hallados:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} {plural} llamadas «{texto}»: "
                    + ", ".join(o.id for o in hallados) + ".")
    otro = next((o for o in doc.operaciones if o.id == texto or o.nombre.casefold() == texto.casefold()), None)
    hay = ", ".join(f"{o.nombre} ({o.id})" for o in candidatos) or "ninguna"
    if otro is not None:
        raise error(kind, f"El paso «{otro.nombre}» ({otro.id}) es de tipo {otro.TIPO}, no {que}. {plural.capitalize()}: "
                    f"{hay}.")
    raise error(kind, f"No existe {que} «{texto}». {plural.capitalize()}: {hay}.")


def union(sesion, ref):
    """`OpUnion` por id o nombre (JOINT_NOT_FOUND con la lista de uniones)."""
    return _paso_de_clase(sesion, ref, OpUnion, "JOINT_NOT_FOUND", "una unión", "uniones")


def _cuerpo_de(sesion, body):
    """Id del cuerpo donde se evalúa un selector: un cuerpo (id o nombre) o un componente de UN solo cuerpo."""
    if body is None or not str(body).strip():
        return None
    try:
        return sesion.cuerpo(body).id
    except ErrorAPI as e:
        if e.error_kind != "BODY_NOT_FOUND":
            raise
        try:
            k = componente(sesion, body)
        except ErrorAPI:
            raise e from None
    cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if c.componente == k]
    if len(cuerpos) != 1:
        raise error("AMBIGUOUS_REFERENCE", f"El componente «{body}» tiene {len(cuerpos)} cuerpos: decí en cuál se "
                    "evalúa el selector (" + ", ".join(f"{sesion.nombre_cuerpo(c)} ({c.id})" for c in cuerpos) + ").")
    return cuerpos[0].id


def _origen(sesion, spec, body=None):
    """Referencia persistente de un origen de unión: cara o arista (selector o id), un paso de construcción (origen de
    unión, plano, eje o punto, por id o nombre) o un plano de origen. Devuelve (referencia, cuerpo o None)."""
    body = _cuerpo_de(sesion, body)
    if sl.es_punto3(spec):                       # un vértice, por sus coordenadas
        c, ref, _v = sl.vertice_cercano(sesion, spec, body)
        return ref, c
    if isinstance(spec, dict) and "tipo" in spec:        # una referencia persistente ya armada (la que guarda el paso)
        try:
            ent.validar(spec)
        except ent.ErrorReferencia as e:
            raise error("INVALID_ARGUMENTS", str(e)) from e
        return spec, sesion.doc.estado_final.cuerpos.get(spec.get("cuerpo"))
    if isinstance(spec, dict) and "sketch" in spec:     # punto o curva de un boceto: {"sketch", "point"|"curve"}
        from .herramientas_avanzado import _de_boceto
        return _de_boceto(sesion, "origen", spec)[0], None
    if not isinstance(spec, str) or not spec.strip():
        raise error("INVALID_ARGUMENTS", "Falta el origen de la unión: una cara o arista (selector o id de find_faces "
                    "/ find_edges) o un origen de unión.")
    texto = spec.strip()
    if texto.upper() in geo.Plano.DEFINICIONES:
        return {"tipo": "plano", "id": texto.upper()}, None
    pasos = [o for o in sesion.doc.operaciones[:sesion.doc.marcador] if o.TIPO in _PASOS_CONSTRUCCION]
    paso = next((o for o in pasos if o.id == texto), None) or next(
        (o for o in pasos if o.nombre.casefold() == texto.casefold()), None)
    if paso is not None:
        return {"tipo": _PASOS_CONSTRUCCION[paso.TIPO], "id": paso.id}, None
    if not (sl.es_id(texto) or sl.parece_selector(texto) or sl._PREFIJO.match(texto)):
        raise error("INVALID_ARGUMENTS", f"«{texto}» no es una cara, una arista ni un paso de construcción.",
                    "Usá un selector ('>Z', '%CYLINDER', 'edges:%CIRCLE'), un id de find_faces / find_edges o el id de "
                    "un origen de unión (create_joint_origin).")
    c, e = sl.elegir_uno(sesion, texto, "cara", body)
    return sl.referencia(c, e), c


def _componente_del_origen(sesion, cuerpo, que):
    if cuerpo is None:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser una cara o arista de un cuerpo del componente que se "
                    "mueve (un plano o eje de construcción no pertenece a ningún componente).")
    if not cuerpo.componente:
        raise error("INVALID_ARGUMENTS", f"«{sesion.nombre_cuerpo(cuerpo)}» está en la raíz: una unión mueve "
                    "componentes.", "create_component crea uno con ese cuerpo.")
    estado = sesion.doc.estado_final
    if es_fijo(estado, cuerpo.componente):
        raise error("INVALID_ARGUMENTS", f"El componente «{_nombre_comp(estado, cuerpo.componente)}» está fijo: una "
                    "unión no puede moverlo.", "Elegí como origin1 la pieza que se mueve, o liberala con "
                    "ground_component(grounded=false).")
    grupo = grupo_rigido(estado, cuerpo.componente)
    fijos = [c for c in grupo if es_fijo(estado, c)]
    if fijos:
        raise error("INVALID_ARGUMENTS", f"El componente «{_nombre_comp(estado, cuerpo.componente)}» está en un grupo "
                    f"rígido con «{_nombre_comp(estado, fijos[0])}», que está fijo: una unión no puede moverlo (el "
                    "grupo se mueve entero).",
                    "Sacá el componente fijo del grupo rígido, o liberalo con ground_component(grounded=false).")
    return cuerpo.componente


# ---------------------------------------------------------------- informes
def _matriz(estado, k):
    return np.asarray(estado.componentes.get(k, {}).get("matriz", np.identity(4).tolist()), float)


def _caja(cuerpos):
    cajas = [geo.caja_envolvente(c.forma) if getattr(c, "tipo", "solido") != "malla" else c.forma.caja()
             for c in cuerpos]
    cajas = [x for x in cajas if x]
    if not cajas:
        return None
    mn = np.min([x[0] for x in cajas], axis=0)
    mx = np.max([x[1] for x in cajas], axis=0)
    return {"min": [_r(v) for v in mn], "max": [_r(v) for v in mx]}


def info_componente(sesion, k, estado=None):
    estado = estado or sesion.doc.estado_final
    datos = estado.componentes.get(k, {})
    cuerpos = [c for c in estado.cuerpos.values() if (c.componente or "") == k]
    m = _matriz(estado, k)
    return {"id": k, "name": _nombre_comp(estado, k), "grounded": bool(datos.get("fijo")),
            "pinned": bool(datos.get("anclado")), "bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c)} for c in cuerpos],
            "parent": datos.get("padre") or "", "path": ruta_componente(estado, k),
            "children": [h for h, d in estado.componentes.items() if d.get("padre") == k],
            "translation": [_r(v) for v in m[:3, 3]], "rotation_matrix": [[_r(v) for v in fila] for fila in m[:3, :3]],
            "bounding_box": _caja(cuerpos),
            **({"origin": [_r(v) for v in (m @ [*datos["origen"], 1.0])[:3]]} if datos.get("origen") else {})}


def _ref_componente(estado, k):
    if not k:
        return {"id": "", "name": "(raíz)"}
    return {"id": k, "name": _nombre_comp(estado, k)}


def _estado_paso(doc, op):
    try:
        r = doc.resultado(op.id)
    except Exception:  # noqa: BLE001 — un paso recién quitado
        return None, ""
    return ESTADOS.get(r.estado, r.estado), r.mensaje


def info_union(sesion, op):
    doc = sesion.doc
    estado = doc.estado_final
    u = estado.uniones.get(op.id)
    tipo = op.p.get("tipo")
    giros, desliz = MOVIMIENTOS.get(tipo, ([], []))
    status, mensaje = _estado_paso(doc, op)
    vinculos = [o.id for o in doc.operaciones if isinstance(o, OpVinculoMovimiento) and o.p.get("union2") == op.id
                and o.p.get("union1") != op.id and not o.suprimida]
    info = {"id": op.id, "name": op.nombre, "type": A_INGLES.get(tipo, tipo), "as_built": bool(op.p.get("como_esta")),
            "status": status, "message": mensaje,
            "component1": _ref_componente(estado, u["comp1"]) if u else None,
            "component2": _ref_componente(estado, u["comp2"]) if u else None,
            "rotation_axis": op.p.get("eje_giro") if tipo in ("revolucion", "cilindrica", "pasador_ranura", "planar")
            else None,
            "slide_axis": op.p.get("eje_desliz") if tipo in ("deslizante", "pasador_ranura") else None,
            "values": {A_MOVIMIENTO[k]: _r(u["valores"].get(k, 0.0)) for k in giros + desliz} if u else None,
            "requested": {A_MOVIMIENTO[k]: op.p.get(k) for k in giros + desliz},
            "limits": None, "driven_by_links": vinculos}
    if giros or desliz:
        info["limits"] = {"motion": "rotation" if giros else "slide",
                          "minimum": str(op.p.get("minimo") or "").strip() or None,
                          "maximum": str(op.p.get("maximo") or "").strip() or None}
        info["limits_by_motion"] = {}
        for k in giros + desliz:
            mn, mx, rs, inv = limites_expr(op.p, k)
            info["limits_by_motion"][A_MOVIMIENTO[k]] = {
                "minimum": str(mn or "").strip() or None, "maximum": str(mx or "").strip() or None,
                "rest": str(rs or "").strip() or None, "flip": inv}
    info["mode1"] = PUBLICO_MODO.get(op.p.get("modo1") or "simple")
    info["mode2"] = None if op.p.get("como_esta") else PUBLICO_MODO.get(op.p.get("modo2") or "simple")
    info["custom_rotation_axis"] = bool(op.p.get("ref_eje_giro"))
    info["custom_slide_axis"] = bool(op.p.get("ref_eje_desliz"))
    if tipo == "bola":
        info["pitch_axis"] = op.p.get("ref_eje_cabeceo") and "custom" or op.p.get("eje_cabeceo") or None
        info["yaw_axis"] = op.p.get("ref_eje_guinada") and "custom" or op.p.get("eje_guinada") or None
    return info


def _info_vinculo(op):
    return {"id": op.id, "name": op.nombre, "joint1": op.p.get("union1"), "joint2": op.p.get("union2"),
            "motion1": A_MOVIMIENTO.get(op.p.get("mov1")), "motion2": A_MOVIMIENTO.get(op.p.get("mov2")),
            "ratio": op.p.get("factor"), "reverse": bool(op.p.get("invertir")), "suppressed": op.suprimida}


def _movidos(sesion, antes):
    """Componentes cuya posición cambió respecto de `antes` ({id: matriz}). Cada uno trae
    `delta_translation`: cuánto se movió su ORIGEN con respecto de antes (B-46: `translation` es la
    posición respecto de donde se modeló; girar sobre un eje que no pasa por el origen la cambia)."""
    estado = sesion.doc.estado_final
    movidos = []
    for k in estado.componentes:
        m = _matriz(estado, k)
        if k in antes and np.allclose(m, antes[k], atol=1e-9):
            continue
        info = info_componente(sesion, k)
        info["delta_translation"] = ([_r(v) for v in (m[:3, 3] - antes[k][:3, 3])] if k in antes else None)
        movidos.append(info)
    return movidos


def _matrices(sesion):
    estado = sesion.doc.estado_final
    return {k: _matriz(estado, k) for k in estado.componentes}


# ---------------------------------------------------------------- consulta
@herramienta("get_assembly", "ensamble", "Ensamble del documento: componentes (id, nombre, fijo, cuerpos, posición: "
             "traslación y rotación respecto de donde se modelaron, caja envolvente), si hay algo arrastrado sin capturar "
             "(uncaptured_position; los componentes se informan sin ese arrastre), uniones (tipo, componentes, "
             "valores actuales de giro en grados y deslizamiento en mm, límites, ejes, estado), orígenes de unión, "
             "grupos rígidos, vínculos de movimiento y los cuerpos sueltos en la raíz.")
def get_assembly(sesion, summary: bool = False):
    """
    summary: true devuelve solo nombres, conteos y las uniones con sus valores, sin la lista de cuerpos.
    """
    doc = sesion.doc
    estado = doc.estado_final
    ops = doc.operaciones[:doc.marcador]
    grupos = []
    for o in ops:
        if isinstance(o, OpGrupoRigido):
            status, mensaje = _estado_paso(doc, o)
            grupos.append({"id": o.id, "name": o.nombre, "components": [str(x) for x in o.p.get("componentes") or []],
                           "status": status, "message": mensaje})
    origenes = []
    for o in ops:
        if isinstance(o, OpOrigenUnion):
            plano = estado.planos.get(o.id)
            origenes.append({"id": o.id, "name": o.nombre, "origin": None if plano is None else [_r(v) for v in plano.origen],
                             "z_axis": None if plano is None else [_r(v) for v in plano.normal]})
    raiz = [c for c in cuerpos_del_modelo(estado) if not c.componente]
    uniones = [o for o in ops if isinstance(o, OpUnion)]
    if summary:
        return {"components": [{"id": k, "name": _nombre_comp(estado, k)} for k in estado.componentes],
                "uncaptured_position": pendiente_de(doc) is not None,
                "joints": [info_union(sesion, o) for o in uniones],
                "joint_origins": [{"id": o.id, "name": o.nombre} for o in ops if isinstance(o, OpOrigenUnion)],
                "rigid_groups": [{"id": g["id"], "name": g["name"]} for g in grupos],
                "motion_links": [{"id": o.id, "name": o.nombre} for o in ops if isinstance(o, OpVinculoMovimiento)],
                "root_bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c)} for c in raiz],
                "counts": {"components": len(estado.componentes), "bodies": len(estado.cuerpos),
                           "joints": len(estado.uniones)},
                "units": {"length": "mm", "angle": "deg"}}
    return {"components": [info_componente(sesion, k) for k in estado.componentes],
            "uncaptured_position": pendiente_de(doc) is not None,
            "joints": [info_union(sesion, o) for o in uniones],
            "joint_origins": origenes, "rigid_groups": grupos,
            "motion_links": [_info_vinculo(o) for o in ops if isinstance(o, OpVinculoMovimiento)],
            "root_bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c)} for c in raiz],
            "units": {"length": "mm", "angle": "deg"}}


# ---------------------------------------------------------------- componentes
@herramienta("create_component", "ensamble", "Crea un componente con los cuerpos dados (ENSAMBLAR › Nuevo componente "
             "desde cuerpos). Las uniones mueven componentes, no cuerpos sueltos. grounded=true lo fija en su lugar "
             "(ninguna unión puede moverlo; suele ser la base). Un cuerpo que ya estaba en otro componente pasa al "
             "nuevo. parent lo cuelga de otro componente (subensamblaje): mover o unir al padre lo mueve con él.",
             modifica=True)
def create_component(sesion, bodies: list[str], name: str | None = None, grounded: bool = False,
                     parent: str | None = None):
    """
    bodies: ids o nombres de los cuerpos del componente (al menos uno).
    name: nombre del componente; vacío = «Componente<n>».
    grounded: true para fijarlo (Ground): ninguna unión lo mueve.
    parent: componente padre (id, nombre o uno de sus cuerpos); vacío = la raíz (Parent de Fusion).
    """
    if not bodies:
        raise error("INVALID_ARGUMENTS", "Falta elegir los cuerpos del componente.")
    padre = componente(sesion, parent) if parent else ""
    cuerpos = []
    for b in bodies:
        c = sesion.cuerpo(b)
        if c not in cuerpos:
            cuerpos.append(c)
    estado = sesion.doc.estado_final
    for c in cuerpos:
        if c.componente:
            sesion.avisar(f"«{sesion.nombre_cuerpo(c)}» pasa del componente «{_nombre_comp(estado, c.componente)}» "
                          "al nuevo.")
    doc = sesion.doc
    op = OpComponente(doc.nuevo_id(), nombre_paso(sesion, name, "Componente", OpComponente),
                      cuerpos=[c.id for c in cuerpos], fijo=grounded, padre=padre,
                      pose=pose_de_reasignar(estado, [c.id for c in cuerpos]).tolist(),
                      pose_padre=pose_de_componente(estado, padre).tolist())
    resultado = _agregar(sesion, op)
    resultado["component"] = info_componente(sesion, op.id)
    return resultado


@herramienta("cycle_component_color", "ensamble", "Color del componente de ciclo: pasa el componente al siguiente color de "
             "la paleta, el de component_colors de get_viewport_image y de Mostrar colores de componente.", modifica=True)
def cycle_component_color(sesion, component: str):
    """
    component: componente (id o nombre).
    """
    from ..timeline.aspectos_doc import colores_componentes
    doc, c = sesion.doc, componente(sesion, component)
    doc.set_propiedad([c], "ciclo_color", int(doc.propiedad(c, "ciclo_color", 0)) + 1)
    return {"component": c, "color": "#%02x%02x%02x" % colores_componentes(doc)[c]}


@herramienta("ground_component", "ensamble", "Fija o libera un componente (ENSAMBLAR › Fijar). Un componente fijo no se "
             "mueve con ninguna unión.", modifica=True)
def ground_component(sesion, component: str, grounded: bool = True):
    """
    component: id, nombre o un cuerpo del componente.
    grounded: true lo fija; false lo libera.
    """
    k = componente(sesion, component)
    op = sesion.doc.operacion(k)
    if not isinstance(op, (OpComponente, OpInsertarDiseno)):
        raise error("COMPONENT_NOT_FOUND", f"El componente «{k}» no lo creó un paso de componente.")
    nueva = op.__class__(op.id, op.nombre, op.suprimida, **dict(op.p, fijo=bool(grounded)))
    sesion.doc.reemplazar(op.id, nueva)
    return {"component": info_componente(sesion, k)}


# ---------------------------------------------------------------- uniones
def _valores(tipo, valores):
    """Params del movimiento pedido ({"giro": "30.0"…}). Un valor que el tipo no tiene es un error."""
    giros, desliz = MOVIMIENTOS[tipo]
    salida = {}
    for clave, valor in valores.items():
        if valor is None:
            continue
        k = MOVIMIENTO[clave]
        if k not in giros + desliz:
            validos = ", ".join(A_MOVIMIENTO[x] for x in giros + desliz) or "ninguno (es rígida)"
            raise error("INVALID_ARGUMENTS", f"Una unión {A_INGLES[tipo]} no tiene «{clave}». Movimientos de este "
                        f"tipo: {validos}.")
        salida[k] = _expr(valor)
    return salida


def _expr(valor):
    """Texto de expresión de un número (mm o grados) o una expresión; «nan» e «inf» se rechazan con su mensaje."""
    texto = texto_expr(valor)
    try:
        exigir_numero(texto)
    except ErrorOperacion as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    return texto


def _comprobar_limites(sesion, clave, minimum, maximum):
    # Se comparan los VALORES (expresiones también): solo con números, "100 deg" > "20 deg" pasaba (B-64)
    unidad = ANGULO if clave.startswith("giro") else LONGITUD
    valores = sesion.doc.parametros.valores()

    def _numero(v):
        if v is None:
            return None
        try:
            return evaluar(_expr(v), unidad, valores)
        except (ErrorExpresion, ValueError, ZeroDivisionError):
            return None                    # ilegible ahora: que lo valide quien lo use al calcular

    mn, mx = _numero(minimum), _numero(maximum)
    if mn is not None and mx is not None and mn > mx:
        raise error("INVALID_ARGUMENTS", f"El mínimo ({mn:g}) es mayor que el máximo ({mx:g}).")


def _movimiento_de(tipo, nombre):
    """Clave interna del movimiento «rotation», «slide»… de ese tipo de unión (error si no lo tiene)."""
    giros, desliz = MOVIMIENTOS[tipo]
    clave = MOVIMIENTO.get(nombre)
    if clave is None or clave not in giros + desliz:
        validos = ", ".join(A_MOVIMIENTO[x] for x in giros + desliz) or "ninguno (es rígida)"
        raise error("INVALID_ARGUMENTS", f"Una unión {A_INGLES[tipo]} no tiene «{nombre}». Movimientos de este "
                    f"tipo: {validos}.")
    return clave


def _limites(sesion, tipo, minimum, maximum, motion_limits=None, rest=None, flip=False):
    """Params de los límites: `minimo` y `maximo` del movimiento principal más `limites_dof` con los de los otros
    movimientos, el reposo y «invertir» (ASM-12). `motion_limits` = {"rotation2": {"minimum", "maximum", "rest",
    "flip"}}; `rest` y `flip` son los del movimiento principal."""
    giros, desliz = MOVIMIENTOS[tipo]
    pedidos = {k: dict(v or {}) for k, v in (motion_limits or {}).items()}
    if not (giros or desliz) and (minimum is not None or maximum is not None or pedidos or rest is not None or flip):
        raise error("INVALID_ARGUMENTS", "Una unión rígida no tiene movimiento que limitar.")
    principal = principal_de(tipo)
    if rest is not None or flip:
        pedidos.setdefault(A_MOVIMIENTO[principal], {}).update({k: v for k, v in (("rest", rest), ("flip", flip))
                                                                if v is not None and v is not False})
    dof = {}
    for nombre, datos in pedidos.items():
        clave = _movimiento_de(tipo, nombre)
        if set(datos) - {"minimum", "maximum", "rest", "flip"}:
            raise error("INVALID_ARGUMENTS", f"Los límites de «{nombre}» aceptan minimum, maximum, rest y flip "
                        f"(recibió {', '.join(sorted(datos))}).")
        mn, mx = datos.get("minimum"), datos.get("maximum")
        entrada = {}
        if clave == principal:
            minimum, maximum = (minimum if mn is None else mn), (maximum if mx is None else mx)
        else:
            _comprobar_limites(sesion, clave, mn, mx)
            entrada = {"minimo": "" if mn is None else _expr(mn), "maximo": "" if mx is None else _expr(mx)}
        if datos.get("rest") is not None and str(datos["rest"]).strip():
            entrada["reposo"] = _expr(datos["rest"])
        if datos.get("flip"):
            entrada["invertir"] = True
        if entrada:
            dof[clave] = entrada
    if giros or desliz:
        _comprobar_limites(sesion, principal, minimum, maximum)
    return {"minimo": "" if minimum is None else _expr(minimum), "maximo": "" if maximum is None else _expr(maximum),
            "limites_dof": dof}


def _aplicar_reposo(params, tipo):
    """El reposo de un movimiento es su valor inicial si no se pidió otro (el resto no se toca)."""
    for clave, entrada in (params.get("limites_dof") or {}).items():
        if entrada.get("reposo") and clave not in params and clave in sum(MOVIMIENTOS[tipo], []):
            params[clave] = entrada["reposo"]


def _desfase(offset):
    if offset is None:
        return {}
    if len(offset) != 3:
        raise error("INVALID_ARGUMENTS", f"offset va como [dx, dy, dz] en mm (recibió {len(offset)} valores).")
    return {k: _expr(v) for k, v in zip(("dx", "dy", "dz"), offset, strict=True)}


def _origen_b(sesion, modo, spec_b, body, que):
    """Segunda selección del modo «entre dos caras» o «intersección de dos aristas» (None en el modo simple)."""
    if modo == "simple":
        if spec_b is not None:
            raise error("INVALID_ARGUMENTS", f"{que} solo se usa con el modo between_faces o edge_intersection.")
        return None
    if spec_b is None:
        raise error("INVALID_ARGUMENTS", f"El modo {PUBLICO_MODO[modo]} necesita la segunda selección ({que}): "
                    f"{'otra cara' if modo == 'entre_caras' else 'otra arista (con selector, prefijo edges:)'}.")
    ref, _c = _origen(sesion, spec_b, body)
    return ref


def _ejes_propios(sesion, tipo, rotation_axis_from, slide_axis_from, axis_body):
    """Referencias de los ejes de movimiento propios (una arista, un eje o un cilindro): {"ref_eje_giro": …}."""
    salida = {}
    if rotation_axis_from is not None:
        if tipo not in ("revolucion", "cilindrica", "pasador_ranura", "planar", "bola"):
            raise error("INVALID_ARGUMENTS", f"Una unión {A_INGLES[tipo]} no gira: rotation_axis_from no se usa.")
        salida["ref_eje_giro"] = _origen(sesion, rotation_axis_from, axis_body)[0]
    if slide_axis_from is not None:
        if tipo not in ("deslizante", "pasador_ranura"):
            raise error("INVALID_ARGUMENTS", f"En una unión {A_INGLES[tipo]} se desliza sobre el eje de giro: "
                        "slide_axis_from es de slider y pin_slot.")
        salida["ref_eje_desliz"] = _origen(sesion, slide_axis_from, axis_body)[0]
    return salida


def _ejes_bola(sesion, tipo, pitch_axis, yaw_axis, pitch_axis_from, yaw_axis_from, axis_body):
    """Cabeceo (Pitch) y guiñada (Yaw) de la bola (ASM-11): {"eje_cabeceo": "Y", "ref_eje_guinada": …}."""
    pedidos = {"pitch_axis": pitch_axis, "yaw_axis": yaw_axis, "pitch_axis_from": pitch_axis_from,
               "yaw_axis_from": yaw_axis_from}
    if tipo != "bola":
        dados = ", ".join(k for k, v in pedidos.items() if v is not None)
        if dados:
            raise error("INVALID_ARGUMENTS", f"Una unión {A_INGLES[tipo]} no tiene cabeceo ni guiñada: {dados} es solo "
                        "de ball.")
        return {}
    for eje, ref, nombre in ((pitch_axis, pitch_axis_from, "el cabeceo"), (yaw_axis, yaw_axis_from, "la guiñada")):
        if eje is not None and ref is not None:
            raise error("INVALID_ARGUMENTS", f"Para {nombre} pasá el eje del marco o el propio, no los dos.")
    salida = {}
    for clave, eje in (("eje_cabeceo", pitch_axis), ("eje_guinada", yaw_axis)):
        if eje is not None:
            salida[clave] = eje
    for clave, ref in (("ref_eje_cabeceo", pitch_axis_from), ("ref_eje_guinada", yaw_axis_from)):
        if ref is not None:
            salida[clave] = _origen(sesion, ref, axis_body)[0]
    return salida


def _avisar_uniones_previas(sesion, params):
    """Si el componente que se va a mover ya tiene otra unión, la nueva lo lleva a su marco y la vieja deja de
    cumplirse sin decirlo (T-09 de la prueba de tortura): se avisa con el nombre de cada una."""
    estado = sesion.doc.estado_final
    cuerpo = estado.cuerpos.get((params.get("origen1") or {}).get("cuerpo"))
    if cuerpo is None or not cuerpo.componente:
        return
    previas = [o.nombre for o in sesion.doc.operaciones if isinstance(o, OpUnion) and not o.suprimida
               and (estado.uniones.get(o.id) or {}).get("comp1") == cuerpo.componente]
    if previas:
        sesion.avisar(f"El componente «{_nombre_comp(estado, cuerpo.componente)}» ya tiene {', '.join(previas)}: la unión "
                      "nueva lo lleva a su marco y esa deja de cumplirse. Suprimila o borrala si no la querés.")


def _crear_union(sesion, nombre, params):
    _avisar_uniones_previas(sesion, params)
    antes = _matrices(sesion)
    doc = sesion.doc
    op = OpUnion(doc.nuevo_id(), nombre_paso(sesion, nombre, "Unión", OpUnion), **params)
    resultado = _agregar(sesion, op)
    resultado["joint"] = info_union(sesion, op)
    resultado["moved_components"] = _movidos(sesion, antes)
    # B-50: con deslizamiento, el snap al centro de cada cara puede correr el componente sobre el eje: se avisa.
    if not params["como_esta"] and MOVIMIENTOS[params["tipo"]][1]:
        for c in resultado["moved_components"]:
            d = c["delta_translation"]
            if d is not None and np.linalg.norm(d) > 1e-6:
                sesion.avisar(f"El componente «{c['name']}» se movió [{d[0]}, {d[1]}, {d[2]}] mm para que los "
                              "centros de las caras coincidan (snap al centro); con caras de distinto largo queda "
                              "corrido sobre el eje de deslizamiento. Para conservar su posición usá "
                              "create_as_built_joint, o ajustá offset / snap1 / snap2.")
    return resultado


_DESC_MODOS = ("mode1 / mode2: simple, between_faces (centro entre dos caras paralelas) o edge_intersection (cruce "
               "de dos aristas rectas); la segunda va en origin1b / origin2b. ")
_DESC_EJES = ("rotation_axis_from / slide_axis_from: arista recta o circular, eje de construcción o cara cilíndrica en "
              "vez de X/Y/Z (axis_body: cuerpo del selector). motion_limits: {'rotation2': {'minimum': -30, "
              "'maximum': 30, 'rest': 0, 'flip': false}}; rest y flip_limits son los del movimiento principal. ")


def _modo(sesion, modo, spec_b, body, que):
    return MODO[modo], _origen_b(sesion, MODO[modo], spec_b, body, que)


@herramienta("create_joint", "ensamble", "Une dos componentes (ENSAMBLAR › Unión): mueve el componente de origin1 "
             "hasta que su marco coincide con el de origin2 (caras planas enfrentadas; dos ejes —perno en agujero— en "
             "el mismo sentido) y define cómo se mueve después. " + _DESC_ORIGEN + _DESC_MODOS + _DESC_TIPOS +
             "angle gira el componente 1 alrededor del Z del marco, offset lo corre [dx, dy, dz] y flip lo da vuelta. "
             "Los valores (rotation, slide…) y los límites aceptan número (grados o mm) o expresión. " + _DESC_EJES +
             "Devuelve la unión y los componentes que se movieron con su traslación y caja envolvente. En uniones con "
             "deslizamiento avisa si el componente se movió (snap al centro de cada cara).", modifica=True)
def create_joint(sesion, origin1: str | list[float], origin2: str | list[float] | dict, joint_type: TipoUnion = "rigid", body1: str | None = None,
                 body2: str | None = None, snap1: Snap = "center", snap2: Snap = "center", angle: Expr = 0,
                 offset: list[Expr] | None = None, flip: bool = False, rotation_axis: Eje = "Z", slide_axis: Eje = "X",
                 rotation: Expr | None = None, rotation2: Expr | None = None, rotation3: Expr | None = None,
                 slide: Expr | None = None, slide2: Expr | None = None, minimum: Expr | None = None,
                 maximum: Expr | None = None, name: str | None = None, mode1: ModoPosicion = "simple",
                 origin1b: str | list[float] | None = None, mode2: ModoPosicion = "simple",
                 origin2b: str | list[float] | None = None, rotation_axis_from: str | None = None,
                 slide_axis_from: str | None = None, axis_body: str | None = None, rest: Expr | None = None,
                 flip_limits: bool = False, motion_limits: dict | None = None, pitch_axis: Eje | None = None,
                 yaw_axis: Eje | None = None, pitch_axis_from: str | None = None, yaw_axis_from: str | None = None):
    """
    origin1: dónde se toma el componente que SE MUEVE: cara o arista (selector o id), o un vértice por sus coordenadas [x, y, z], del cuerpo body1.
    origin2: dónde va: cara o arista de otro componente (o de la raíz), un vértice [x, y, z], un punto o una curva de boceto {"sketch", "point" | "curve"}, origen de unión, plano, eje o punto de construcción.
    joint_type: "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
    body1: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin1; con un id no hace falta.
    body2: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin2.
    snap1: punto del origen 1 en una arista o cilindro: "center" (medio), "start" o "end".
    snap2: punto del origen 2: "center", "start" o "end".
    angle: giro del componente 1 alrededor del eje Z del marco de la unión, en grados.
    offset: desfase [dx, dy, dz] en mm en el marco de la unión (Z = normal o eje).
    flip: true da vuelta el componente 1 (caras en el mismo sentido o ejes opuestos).
    rotation_axis: eje del marco para girar (revolute, cylindrical, pin_slot) o normal del plano (planar);
        "Z" es el eje de un marco de cilindro/arista circular (ver el módulo: marcos de eje).
    slide_axis: eje del marco para deslizar (slider, pin_slot).
    rotation: giro inicial en grados (revolute, cylindrical, pin_slot, planar, ball).
    rotation2: segundo giro (cabeceo) en grados; solo ball.
    rotation3: tercer giro (guiñada) en grados; solo ball.
    slide: deslizamiento inicial en mm (slider, cylindrical, pin_slot, planar).
    slide2: segundo deslizamiento en mm; solo planar.
    minimum: límite mínimo del movimiento principal (grados si gira, mm si solo desliza); vacío = sin límite.
    maximum: límite máximo del movimiento principal; vacío = sin límite.
    name: nombre del paso; vacío = «Unión<n>».
    mode1: modo del origen 1 (ver mode1 / mode2 arriba).
    origin1b: segunda cara (between_faces) o segunda arista (edge_intersection) del origen 1, del cuerpo body1.
    mode2: modo del origen 2.
    origin2b: segunda cara o arista del origen 2, del cuerpo body2.
    rotation_axis_from: eje de giro propio (arista, eje de construcción o cilindro) en lugar de rotation_axis.
    slide_axis_from: eje de deslizamiento propio en lugar de slide_axis (slider, pin_slot).
    axis_body: cuerpo donde se evalúan los selectores de los ejes propios.
    rest: reposo del movimiento principal: su valor inicial si no se pide otro (grados o mm).
    flip_limits: true invierte los límites del movimiento principal.
    motion_limits: límites por movimiento ("rotation", "rotation2", "rotation3", "slide", "slide2"), cada uno con minimum, maximum, rest y flip.
    pitch_axis: eje de cabeceo de la bola: "X", "Y" o "Z" del marco; vacío = Y. rotation2 gira sobre él. Solo ball.
    yaw_axis: eje de guiñada de la bola: "X", "Y" o "Z"; vacío = X. rotation3 gira sobre él. El balanceo (rotation) sale de los dos ejes (con Y y X, el Z del marco); sin ninguno, de rotation_axis_from o Z. Solo ball.
    pitch_axis_from: eje de cabeceo propio (arista, eje de construcción o cilindro) en lugar de pitch_axis. Solo ball.
    yaw_axis_from: eje de guiñada propio en lugar de yaw_axis. Solo ball.
    """
    tipo = TIPOS[joint_type]
    modo1, ref1b = _modo(sesion, mode1, origin1b, body1, "origin1b")
    modo2, ref2b = _modo(sesion, mode2, origin2b, body2, "origin2b")
    ref1, c1 = _origen(sesion, origin1, body1)
    _componente_del_origen(sesion, c1, "origin1")
    ref2, c2 = _origen(sesion, origin2, body2)
    if c2 is not None and (c2.componente or "") == c1.componente:
        raise error("INVALID_ARGUMENTS", "Los dos orígenes están en el mismo componente: origin2 tiene que ser de otro "
                    "componente (o de la raíz).")
    params = {"tipo": tipo, "origen1": ref1, "origen2": ref2, "clave1": SNAP[snap1], "clave2": SNAP[snap2],
              "angulo": _expr(angle), "voltear": bool(flip), "como_esta": False, "eje_giro": rotation_axis,
              "eje_desliz": slide_axis, "modo1": modo1, "modo2": modo2, "origen1b": ref1b, "origen2b": ref2b}
    params.update(_desfase(offset))
    params.update(_valores(tipo, {"rotation": rotation, "rotation2": rotation2, "rotation3": rotation3,
                                  "slide": slide, "slide2": slide2}))
    params.update(_ejes_propios(sesion, tipo, rotation_axis_from, slide_axis_from, axis_body))
    params.update(_ejes_bola(sesion, tipo, pitch_axis, yaw_axis, pitch_axis_from, yaw_axis_from, axis_body))
    params.update(_limites(sesion, tipo, minimum, maximum, motion_limits, rest, flip_limits))
    _aplicar_reposo(params, tipo)
    return _crear_union(sesion, name, params)


@herramienta("create_as_built_joint", "ensamble", "Unión como está (ENSAMBLAR › Unión como está): liga el componente "
             "de `origin` al componente `component2` SIN moverlo de donde está y define su movimiento alrededor del "
             "marco de `origin` (p. ej. el eje de un agujero para una bisagra). Cuando el componente 2 se mueve, el 1 "
             "lo sigue. Sin component2, la unión es contra la raíz. " + _DESC_TIPOS + _DESC_MODOS + _DESC_EJES,
             modifica=True)
def create_as_built_joint(sesion, origin: str | list[float], component2: str | None = None, joint_type: TipoUnion = "revolute",
                          body: str | None = None, snap: Snap = "center", rotation_axis: Eje = "Z",
                          slide_axis: Eje = "X", rotation: Expr | None = None, rotation2: Expr | None = None,
                          rotation3: Expr | None = None, slide: Expr | None = None, slide2: Expr | None = None,
                          minimum: Expr | None = None, maximum: Expr | None = None, name: str | None = None,
                          mode: ModoPosicion = "simple", origin_b: str | list[float] | None = None,
                          rotation_axis_from: str | None = None, slide_axis_from: str | None = None,
                          axis_body: str | None = None, rest: Expr | None = None, flip_limits: bool = False,
                          motion_limits: dict | None = None, pitch_axis: Eje | None = None,
                          yaw_axis: Eje | None = None, pitch_axis_from: str | None = None,
                          yaw_axis_from: str | None = None):
    """
    origin: cara o arista del componente que se mueve (selector evaluado sobre body, o id), o un vértice por sus coordenadas [x, y, z]; define el marco del movimiento.
    component2: componente al que queda ligado (id, nombre o uno de sus cuerpos); vacío = la raíz.
    joint_type: "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
    body: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin.
    snap: punto del origen en una arista o cilindro: "center", "start" o "end".
    rotation_axis: eje del marco para girar (o normal del plano en planar); "Z" es el eje de un marco de
        cilindro/arista circular (ver el módulo: marcos de eje).
    slide_axis: eje del marco para deslizar (slider, pin_slot).
    rotation: giro en grados.
    rotation2: segundo giro en grados (ball).
    rotation3: tercer giro en grados (ball).
    slide: deslizamiento en mm.
    slide2: segundo deslizamiento en mm (planar).
    minimum: límite mínimo del movimiento principal; vacío = sin límite.
    maximum: límite máximo del movimiento principal; vacío = sin límite.
    name: nombre del paso; vacío = «Unión<n>».
    mode: modo del origen: simple, between_faces o edge_intersection.
    origin_b: segunda cara (between_faces) o segunda arista (edge_intersection) del origen, del cuerpo body.
    rotation_axis_from: eje de giro propio (arista, eje de construcción o cilindro) en lugar de rotation_axis.
    slide_axis_from: eje de deslizamiento propio en lugar de slide_axis (slider, pin_slot).
    axis_body: cuerpo donde se evalúan los selectores de los ejes propios.
    rest: reposo del movimiento principal: su valor inicial si no se pide otro (grados o mm).
    flip_limits: true invierte los límites del movimiento principal.
    motion_limits: límites por movimiento ("rotation", "rotation2", "rotation3", "slide", "slide2"), cada uno con minimum, maximum, rest y flip.
    pitch_axis: eje de cabeceo de la bola: "X", "Y" o "Z" del marco; vacío = Y. rotation2 gira sobre él. Solo ball.
    yaw_axis: eje de guiñada de la bola: "X", "Y" o "Z"; vacío = X. rotation3 gira sobre él; el balanceo (rotation) sale de los dos. Solo ball.
    pitch_axis_from: eje de cabeceo propio (arista, eje de construcción o cilindro) en lugar de pitch_axis. Solo ball.
    yaw_axis_from: eje de guiñada propio en lugar de yaw_axis. Solo ball.
    """
    tipo = TIPOS[joint_type]
    modo, refb = _modo(sesion, mode, origin_b, body, "origin_b")
    ref1, c1 = _origen(sesion, origin, body)
    comp1 = _componente_del_origen(sesion, c1, "origin")
    ref2 = None
    if component2 is not None and str(component2).strip():
        k2 = componente(sesion, component2)
        if k2 == comp1:
            raise error("INVALID_ARGUMENTS", "component2 es el mismo componente que el de origin.")
        estado = sesion.doc.estado_final
        cuerpo2 = next((c for c in estado.cuerpos.values() if c.componente == k2), None)
        if cuerpo2 is None:
            raise error("COMPONENT_NOT_FOUND", f"El componente «{_nombre_comp(estado, k2)}» no tiene cuerpos.")
        ref2 = {"tipo": "cuerpo", "cuerpo": cuerpo2.id}
    params = {"tipo": tipo, "origen1": ref1, "origen2": ref2, "clave1": SNAP[snap], "como_esta": True,
              "eje_giro": rotation_axis, "eje_desliz": slide_axis, "modo1": modo, "origen1b": refb}
    params.update(_valores(tipo, {"rotation": rotation, "rotation2": rotation2, "rotation3": rotation3,
                                  "slide": slide, "slide2": slide2}))
    params.update(_ejes_propios(sesion, tipo, rotation_axis_from, slide_axis_from, axis_body))
    params.update(_ejes_bola(sesion, tipo, pitch_axis, yaw_axis, pitch_axis_from, yaw_axis_from, axis_body))
    params.update(_limites(sesion, tipo, minimum, maximum, motion_limits, rest, flip_limits))
    _aplicar_reposo(params, tipo)
    return _crear_union(sesion, name, params)


def _a_la_copia(ref, mapa):
    """La referencia a un cuerpo del componente original, puesta en su copia (`mapa`: cuerpo original → copia)."""
    return dict(ref, cuerpo=mapa[ref["cuerpo"]]) if isinstance(ref, dict) and ref.get("cuerpo") in mapa else ref


@herramienta("duplicate_with_joints", "ensamble", "Duplicar con uniones (ENSAMBLAR › Duplicar con uniones): repite el "
             "componente que mueve una unión en cada destino. Por cada uno agrega un paso «Copiar componente» (un "
             "componente nuevo con copias de todos sus cuerpos) y una unión como la original —mismo tipo, ejes, "
             "límites y valores— que lleva la copia al destino. Las copias son independientes: no hay instancias "
             "asociativas de componentes, y se copia un componente por vez. Todo o nada, en un solo deshacer.",
             modifica=True)
def duplicate_with_joints(sesion, joint: str, destinations: list[str | list[float] | dict],
                          flip: list[bool] | bool = False, snap: Snap | None = None, body: str | None = None):
    """
    joint: unión (id o nombre) cuyo componente 1 se copia y cuya configuración se repite; no puede ser una unión «como está».
    destinations: dónde va cada copia, una por destino: lo mismo que origin2 de create_joint (cara o arista —selector o id de find_faces / find_edges—, vértice [x, y, z], punto o curva de boceto, origen de unión, plano, eje o punto de construcción) o una referencia persistente ya armada ({"tipo": "cara", "cuerpo", "firma"}, la que usa la ventana).
    flip: true da vuelta todas las copias respecto de la unión original; con una lista, una por destino.
    snap: punto del destino en una arista o cilindro: "center", "start" o "end"; vacío = el de la unión original.
    body: cuerpo (o componente de un solo cuerpo) donde se evalúan los selectores de los destinos.
    """
    doc = sesion.doc
    j = union(sesion, joint)
    if j.p.get("como_esta"):
        raise error("INVALID_ARGUMENTS", f"«{j.nombre}» es una unión «como está»: no tiene un destino que repetir.",
                    "Elegí una unión hecha con create_joint.")
    cuerpo = doc.estado_final.cuerpos.get((j.p.get("origen1") or {}).get("cuerpo"))
    if cuerpo is None or not cuerpo.componente:
        raise error("INVALID_ARGUMENTS", f"El origen 1 de la unión «{j.nombre}» ya no está en un componente en este "
                    "punto del timeline (¿cuerpo borrado o fuera del componente?).")
    if not destinations:
        raise error("INVALID_ARGUMENTS", "Indicá al menos un destino.")
    vueltas = list(flip) if isinstance(flip, list) else [bool(flip)] * len(destinations)
    if len(vueltas) != len(destinations):
        raise error("INVALID_ARGUMENTS", "flip tiene que ser true / false o una lista con un valor por destino.")
    destinos = [_origen(sesion, d, body)[0] for d in destinations]       # se validan todos antes de tocar el documento
    origen, copias = cuerpo.componente, []
    for dest, voltear in zip(destinos, vueltas, strict=True):
        paso = OpCopiarComponente(doc.nuevo_id(), nombre_paso(sesion, None, "Copiar componente", OpCopiarComponente),
                                  componente=origen)
        _agregar(sesion, paso)
        cuerpos = list(doc.estado_final.cuerpos.values())
        mapa = dict(zip([c.id for c in cuerpos if c.componente == origen],
                        [c.id for c in cuerpos if c.componente == paso.id], strict=True))
        params = copy.deepcopy(j.p)
        for clave in ("origen1", "origen1b", "ref_eje_giro", "ref_eje_desliz", "ref_eje_cabeceo", "ref_eje_guinada"):
            params[clave] = _a_la_copia(params.get(clave), mapa)
        params.update(origen2=dest, origen2b=None, modo2="simple", voltear=bool(j.p.get("voltear")) != voltear,
                      clave2=SNAP[snap] if snap else j.p.get("clave2", "centro"),
                      accionada=siguiente_accion(doc.operaciones))
        union_nueva = _crear_union(sesion, None, params)
        copias.append({"component": info_componente(sesion, paso.id), "copy_step": paso.id,
                       "joint": union_nueva["joint"]})
    return {"source_joint": j.id, "source_component": _ref_componente(doc.estado_final, origen), "copies": copias,
            "count": len(copias)}


@herramienta("create_joint_origin", "ensamble", "Origen de unión (ENSAMBLAR › Origen de la unión): guarda un marco "
             "(punto con orientación) sobre una cara o arista, con giro y desfase, para usarlo después como origin2 de "
             "create_joint. Sobre un cilindro o una arista circular sigue siendo un marco de eje. " + _DESC_MODOS,
             modifica=True)
def create_joint_origin(sesion, geometry: str | list[float] | dict, body: str | None = None, snap: Snap = "center", angle: Expr = 0,
                        offset: list[Expr] | None = None, name: str | None = None, mode: ModoPosicion = "simple",
                        geometry_b: str | list[float] | None = None):
    """
    geometry: cara o arista donde va el origen (selector evaluado sobre body, o id de find_faces / find_edges), un vértice [x, y, z] o un punto o una curva de boceto {"sketch", "point" | "curve"}.
    body: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector.
    snap: punto en una arista o cilindro: "center", "start" o "end".
    angle: giro del marco alrededor de su Z, en grados.
    offset: desfase [dx, dy, dz] en mm en el marco.
    name: nombre del paso; vacío = «Origen de unión<n>».
    mode: modo del origen: "simple", "between_faces" (centrado entre dos caras paralelas) o "edge_intersection" (en el cruce de dos aristas rectas).
    geometry_b: la segunda cara o arista de los modos between_faces y edge_intersection.
    """
    modo, refb = _modo(sesion, mode, geometry_b, body, "geometry_b")
    ref, _c = _origen(sesion, geometry, body)
    doc = sesion.doc
    op = OpOrigenUnion(doc.nuevo_id(), nombre_paso(sesion, name, "Origen de unión", OpOrigenUnion), origen=ref,
                       clave=SNAP[snap], angulo=_expr(angle), modo=modo, origen_b=refb, **_desfase(offset))
    resultado = _agregar(sesion, op)
    plano = sesion.doc.estado_final.planos.get(op.id)
    if plano is not None:
        resultado["joint_origin"] = {"id": op.id, "name": op.nombre, "origin": [_r(v) for v in plano.origen],
                                     "x_axis": [_r(v) for v in plano.u], "z_axis": [_r(v) for v in plano.normal]}
    return resultado


_CLAVES_FILA = ("geometry1", "geometry2", "type", "offset", "flip", "body1", "body2", "angle_reference", "reference_body",
                "geometry1b", "geometry2b", "body1b", "body2b", "all_faces", "name", "offset_min", "offset_max", "offset_as_rest")


def _fila_restriccion(sesion, geometry1, geometry2, type="align", offset=0, flip=False, body1=None, body2=None, angle_reference=None,
                      reference_body=None, geometry1b=None, geometry2b=None, body1b=None, body2b=None, all_faces=True, name="", offset_min=None,
                      offset_max=None, offset_as_rest=False):
    """Los parámetros de una fila de OpRestriccion a partir de los argumentos de `constrain_components` (valida cada combinación)."""
    if type not in ("align", "angle", "center", "tangent"):
        raise error("INVALID_ARGUMENTS", f"La restricción «{type}» no existe: 'align', 'angle', 'center' o 'tangent'.")
    if angle_reference is not None and type != "angle":
        raise error("INVALID_ARGUMENTS", "angle_reference solo se usa con type='angle'.")
    if not all_faces and type != "tangent":
        raise error("INVALID_ARGUMENTS", "all_faces solo se usa con type='tangent'.")
    if (geometry1b is not None or geometry2b is not None) and type != "center":
        raise error("INVALID_ARGUMENTS", "geometry1b y geometry2b solo se usan con type='center'.")
    if (offset_min is not None or offset_max is not None or offset_as_rest) and type not in ("align", "angle"):
        raise error("INVALID_ARGUMENTS", "offset_min, offset_max y offset_as_rest solo se usan con type='align' o 'angle'.")
    if offset_as_rest and offset_min is None and offset_max is None:
        raise error("INVALID_ARGUMENTS", "offset_as_rest necesita offset_min u offset_max.")
    ref1, _ = _origen(sesion, geometry1, body1)
    ref2, _ = _origen(sesion, geometry2, body2)
    ref_angulo = _origen(sesion, angle_reference, reference_body)[0] if angle_reference is not None else None
    ref1b = _origen(sesion, geometry1b, body1b)[0] if geometry1b is not None else None
    ref2b = _origen(sesion, geometry2b, body2b)[0] if geometry2b is not None else None
    return dict(tipo={"align": "alinear", "angle": "angulo", "center": "centro", "tangent": "tangente"}[type], ref1=ref1, ref2=ref2,
                desfase=_expr(offset), voltear=bool(flip), ref_angulo=ref_angulo, ref1b=ref1b, ref2b=ref2b,
                modo1="entre_caras" if ref1b else "simple", modo2="entre_caras" if ref2b else "simple", todas_caras=bool(all_faces), nombre_fila=str(name or ""),
                minimo="" if offset_min is None else _expr(offset_min), maximo="" if offset_max is None else _expr(offset_max),
                apoyo=bool(offset_as_rest))


@herramienta("constrain_components", "ensamble", "Restricción de componentes (ENSAMBLAR › Restricción de componentes, ASM-17): "
             "posiciona el componente de geometry1 respecto del de geometry2. Hoy type='align' (Alinear) y type='angle' (Ángulo). "
             "Alinear: dos caras "
             "planas o planos quedan coplanares (al ras si miran hacia el mismo lado, enfrentadas si miran opuesto; flip invierte), dos ejes "
             "(cara cilíndrica o cónica, arista circular o recta, eje de construcción) concéntricos o colineales, y dos "
             "puntos coincidentes. Ángulo: gira el componente 1 (sin trasladarlo) hasta que la geometría 1 y la 2 forman el "
             "ángulo pedido en offset (grados): entre caras, el de sus normales; sin angle_reference va de 0 a 180° por el "
             "camino más corto, y con una arista o eje de referencia es con signo alrededor de él. Centro: deja una cara (o el plano medio "
             "de dos caras) del componente 1 a medio camino de las dos caras del componente 2 (o al revés), sin deslizarlo "
             "en el plano; hace falta geometry1b o geometry2b (al menos un componente «entre dos caras»). Tangente: deja tangente "
             "la superficie de geometry1 a la de geometry2 (cara plana, cilíndrica, esférica, cónica o toroidal, plano, arista recta o circular, eje o "
             "vértice): plano–plano enfrentados, plano–curva rozando del lado en que ya está (el cono, solo si el plano ya tiene "
             "su inclinación; el toro y el círculo, solo con el eje perpendicular o paralelo al plano), cilindro y esfera entre sí por fuera; flip pasa al otro lado. Con all_faces=false las caras elegidas "
             "tienen que llegar a tocarse. Si el componente 1 está fijo o es la raíz, se mueve el 2. " + _DESC_ORIGEN + "Devuelve el paso y los componentes que se movieron.", modifica=True)
def constrain_components(sesion, geometry1: str | list[float] | dict, geometry2: str | list[float] | dict,
                         type: Literal["align", "angle", "center", "tangent"] = "align", offset: Expr = 0, flip: bool = False,
                         body1: str | None = None, body2: str | None = None, name: str | None = None,
                         angle_reference: str | list[float] | dict | None = None, reference_body: str | None = None,
                         geometry1b: str | list[float] | dict | None = None, geometry2b: str | list[float] | dict | None = None,
                         body1b: str | None = None, body2b: str | None = None, all_faces: bool = True,
                         rows: list[dict] | None = None, row_name: str = "", offset_min: Expr | None = None,
                         offset_max: Expr | None = None, offset_as_rest: bool = False):
    """
    geometry1: la geometría del componente que se mueve: cara o arista (selector sobre body1 o id de find_faces / find_edges), vértice [x, y, z], plano, eje o punto de construcción.
    geometry2: la geometría del otro componente (o de la raíz) a la que se alinea la primera.
    type: tipo de restricción: "align", "angle", "center" o "tangent".
    offset: con align, el desfase en mm (número o expresión): entre dos planos, la distancia; entre dos ejes, el corrimiento sobre el eje. Con angle, el ángulo en grados.
    flip: true invierte la orientación que sale sola (la que menos gira el componente): al ras pasa a enfrentadas y al revés; con tangent, pasa al otro lado (planos al ras, cilindros por dentro).
    body1: cuerpo donde se evalúa el selector de geometry1; con un id no hace falta.
    body2: cuerpo donde se evalúa el selector de geometry2.
    name: nombre del paso; vacío = «Restricción<n>».
    angle_reference: solo con angle: arista recta o eje que da el sentido del ángulo («Angle Reference»); con él el ángulo es con signo y no queda ambiguo.
    reference_body: cuerpo donde se evalúa el selector de angle_reference.
    geometry1b: solo con center: la segunda cara del componente 1 («Entre dos caras»); sin ella el componente 1 usa solo geometry1 («Simple»).
    geometry2b: solo con center: la segunda cara del componente 2.
    body1b: cuerpo donde se evalúa el selector de geometry1b.
    body2b: cuerpo donde se evalúa el selector de geometry2b.
    rows: más restricciones entre los mismos dos componentes (el conjunto de la tabla de Fusion). Cada una es un objeto con las claves de esta herramienta (geometry1 y geometry2 obligatorias; type, offset (su propio desfase), name (su nombre), offset_min, offset_max, offset_as_rest (sus límites), flip, body1, body2, angle_reference, reference_body, geometry1b, geometry2b, body1b, body2b, all_faces). Se resuelven todas a la vez; si se contradicen, error.
    offset_min: límite mínimo del desfase (mm, o grados con angle; angle pide angle_reference): con límites, un offset fuera del rango se recorta y avisa. Vacío = sin tope (Offset Limits › Min).
    offset_max: límite máximo del desfase, igual que offset_min (Offset Limits › Max).
    offset_as_rest: true («Use Offset as Rest»): el offset es la posición de reposo y tiene que estar dentro de los límites; si no, error en vez de recortar.
    row_name: nombre de la restricción principal dentro del conjunto (lo usa el error de contradicción); vacío = sin nombre.
    all_faces: solo con tangent («All Faces»): true usa la superficie entera de la cara; false pide que la cara del componente 1, ya movida, toque la del componente 2.
    """
    antes = _matrices(sesion)
    principal = _fila_restriccion(sesion, geometry1, geometry2, type, offset, flip, body1, body2, angle_reference, reference_body,
                                  geometry1b, geometry2b, body1b, body2b, all_faces, row_name, offset_min, offset_max, offset_as_rest)
    extra = []
    for i, f in enumerate(rows or [], 2):
        sobran = set(f) - set(_CLAVES_FILA)
        if sobran or "geometry1" not in f or "geometry2" not in f:
            raise error("INVALID_ARGUMENTS", f"La fila {i} de rows necesita geometry1 y geometry2 y solo admite: {', '.join(_CLAVES_FILA)}."
                        + (f" Sobra: {', '.join(sorted(sobran))}." if sobran else ""))
        extra.append(_fila_restriccion(sesion, **f))
    op = OpRestriccion(sesion.doc.nuevo_id(), nombre_paso(sesion, name, "Restricción", OpRestriccion), filas=extra, **principal)
    resultado = _agregar(sesion, op)
    resultado["moved_components"] = _movidos(sesion, antes)
    return resultado


@herramienta("drive_joint", "ensamble", "Acciona una unión (ENSAMBLAR › Accionar uniones): cambia su giro o "
             "deslizamiento y el mecanismo se recalcula (las uniones y vínculos que dependen de ella la siguen). Los "
             "límites recortan el valor y avisan. Cada valor acepta número (grados o mm) o expresión.", modifica=True)
def drive_joint(sesion, joint: str, rotation: Expr | None = None, slide: Expr | None = None,
                rotation2: Expr | None = None, rotation3: Expr | None = None, slide2: Expr | None = None,
                to_rest: bool = False):
    """
    joint: id o nombre de la unión.
    rotation: giro en grados (revolute, cylindrical, pin_slot, planar, ball).
    slide: deslizamiento en mm (slider, cylindrical, pin_slot, planar).
    rotation2: segundo giro en grados (ball).
    rotation3: tercer giro en grados (ball).
    slide2: segundo deslizamiento en mm (planar).
    to_rest: true lleva cada movimiento que tenga un reposo (set_joint_limits) a ese valor.
    """
    op = union(sesion, joint)
    pedidos = {"rotation": rotation, "slide": slide, "rotation2": rotation2, "rotation3": rotation3, "slide2": slide2}
    tipo = op.p.get("tipo")
    if to_rest:
        for clave in sum(MOVIMIENTOS[tipo], []):
            reposo = limites_expr(op.p, clave)[2]
            if reposo and str(reposo).strip() and pedidos[A_MOVIMIENTO[clave]] is None:
                pedidos[A_MOVIMIENTO[clave]] = str(reposo).strip()
    if all(v is None for v in pedidos.values()):
        raise error("INVALID_ARGUMENTS", "Falta el valor a accionar: rotation (grados) o slide (mm)."
                    + (" Ningún movimiento de la unión tiene un reposo." if to_rest else ""))
    nuevos = _valores(tipo, pedidos)
    vinculos = [o for o in sesion.doc.operaciones if isinstance(o, OpVinculoMovimiento) and not o.suprimida
                and o.p.get("union2") == op.id and o.p.get("union1") != op.id]
    if vinculos:        # no se guarda el valor pedido: el vínculo lo ignora y, si se lo suprimiera, la unión lo usaría
        sesion.avisar(f"La unión «{op.nombre}» la mueve el vínculo «{vinculos[0].nombre}»: su valor sale de la otra "
                      "unión y no se cambió nada. Accioná esa.")
        return {"joint": info_union(sesion, op), "moved_components": []}
    antes = _matrices(sesion)
    nuevos["accionada"] = siguiente_accion(sesion.doc.operaciones)
    sesion.doc.reemplazar(op.id, OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, **nuevos)))
    return {"joint": info_union(sesion, sesion.doc.operacion(op.id)), "moved_components": _movidos(sesion, antes)}


@herramienta("set_joint_limits", "ensamble", "Límites de movimiento de una unión (Joint Limits de Fusion): los de un "
             "movimiento a elección (por defecto el principal: el giro en grados si gira, si no el deslizamiento en mm), "
             "su valor de reposo (rest) y si se invierten (flip). Un valor vacío quita ese límite. Si el valor actual "
             "queda afuera, la unión se recorta al límite y avisa.", modifica=True)
def set_joint_limits(sesion, joint: str, minimum: Expr | None = None, maximum: Expr | None = None,
                     motion: Movimiento | None = None, rest: Expr | None = None, flip: bool | None = None):
    """
    joint: id o nombre de la unión.
    minimum: límite mínimo (número o expresión); vacío = sin límite mínimo.
    maximum: límite máximo (número o expresión); vacío = sin límite máximo.
    motion: movimiento al que se ponen los límites ("rotation", "rotation2", "rotation3", "slide" o "slide2"); vacío = el principal.
    rest: valor de reposo de ese movimiento (número o expresión); vacío o "" lo quita; sin pasarlo queda el que había.
    flip: true invierte los límites (el mínimo pasa a ser −máximo y al revés); sin pasarlo queda como estaba.
    Con rest o flip y sin minimum ni maximum, los límites que había quedan como estaban.
    """
    op = union(sesion, joint)
    tipo = op.p.get("tipo")
    if not any(MOVIMIENTOS[tipo]):
        raise error("INVALID_ARGUMENTS", "Una unión rígida no tiene movimiento que limitar.")
    clave = _movimiento_de(tipo, motion) if motion else principal_de(tipo)
    todos = dict(op.p.get("limites_dof") or {})
    if minimum is None and maximum is None and (rest is not None or flip is not None):     # solo ajusta reposo o invertir
        previo = todos.get(clave) or {}
        minimum, maximum = ((op.p.get("minimo"), op.p.get("maximo")) if clave == principal_de(tipo)
                            else (previo.get("minimo"), previo.get("maximo")))
    _comprobar_limites(sesion, clave, minimum, maximum)
    entrada = {k: v for k, v in (todos.get(clave) or {}).items() if k in ("reposo", "invertir")}
    if rest is not None:
        entrada.pop("reposo", None)
        if str(rest).strip():
            entrada["reposo"] = _expr(rest)
    if flip is not None:
        entrada.pop("invertir", None)
        if flip:
            entrada["invertir"] = True
    nuevos = {}
    if clave == principal_de(tipo):
        nuevos.update(minimo="" if minimum is None else _expr(minimum), maximo="" if maximum is None else _expr(maximum))
    else:
        entrada.update(minimo="" if minimum is None else _expr(minimum), maximo="" if maximum is None else _expr(maximum))
    todos.pop(clave, None)
    if entrada:
        todos[clave] = entrada
    antes = _matrices(sesion)
    sesion.doc.reemplazar(op.id, OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, limites_dof=todos, **nuevos)))
    return {"joint": info_union(sesion, sesion.doc.operacion(op.id)), "moved_components": _movidos(sesion, antes)}


# ---------------------------------------------------------------- grupos y vínculos
@herramienta("create_rigid_group", "ensamble", "Grupo rígido (ENSAMBLAR › Grupo rígido): los componentes se mueven "
             "juntos; una unión que mueve a uno mueve a todos.", modifica=True)
def create_rigid_group(sesion, components: list[str], name: str | None = None, include_children: bool = False):
    """
    components: componentes del grupo (id, nombre o uno de sus cuerpos); al menos dos distintos.
    name: nombre del paso; vacío = «Grupo rígido<n>».
    include_children: true suma al grupo los subcomponentes de cada uno («Incluir componentes secundarios»); false los
        deja libres dentro de su padre.
    """
    ids = []
    for ref in components or []:
        k = componente(sesion, ref)
        if k not in ids:
            ids.append(k)
    if len(ids) < 2:
        raise error("INVALID_ARGUMENTS", "Un grupo rígido necesita al menos dos componentes distintos. Componentes: "
                    f"{_lista_componentes(sesion.doc.estado_final)}.")
    doc = sesion.doc
    op = OpGrupoRigido(doc.nuevo_id(), nombre_paso(sesion, name, "Grupo rígido", OpGrupoRigido), componentes=ids,
                       incluir_hijos=bool(include_children))
    resultado = _agregar(sesion, op)
    estado = sesion.doc.estado_final
    miembros = estado.grupos_rigidos[-1] if estado.grupos_rigidos else ids
    resultado["rigid_group"] = {"id": op.id, "name": op.nombre, "components": [_ref_componente(estado, k) for k in miembros]}
    return resultado


@herramienta("create_motion_link", "ensamble", "Vínculo de movimiento (ENSAMBLAR › Vínculo de movimiento): la unión 2 "
             "se mueve en proporción a la 1 (engranajes, cremallera y piñón). El valor de la unión 2 pasa a ser "
             "ratio × el de la unión 1 (con reverse, el opuesto); se acciona la unión 1 con drive_joint.", modifica=True)
def create_motion_link(sesion, joint1: str, joint2: str, ratio: Expr = 1, reverse: bool = False,
                       name: str | None = None, motion1: Movimiento | None = None, motion2: Movimiento | None = None):
    """
    joint1: unión que manda (id o nombre).
    joint2: unión que la sigue (id o nombre).
    ratio: relación unión 2 / unión 1 (número o expresión): grados por grado, mm por grado, etc.
    reverse: true invierte el sentido de la unión 2.
    name: nombre del paso; vacío = «Vínculo de movimiento<n>».
    motion1: movimiento de la unión 1 que se relaciona ("rotation", "rotation2", "rotation3", "slide" o "slide2"); vacío = el giro si gira, si no el deslizamiento.
    motion2: movimiento de la unión 2 que sigue; vacío = el giro si gira, si no el deslizamiento. Con joint1 = joint2 (dos movimientos de la misma unión, p. ej. el giro y el deslizamiento de una cilíndrica: un tornillo) motion1 y motion2 son obligatorios y distintos.
    """
    u1, u2 = union(sesion, joint1), union(sesion, joint2)
    if u1.id == u2.id and (not motion1 or not motion2 or motion1 == motion2):
        raise error("INVALID_ARGUMENTS", "Con la misma unión en joint1 y joint2 hay que elegir dos movimientos distintos "
                    "de ella (motion1 y motion2: por ejemplo rotation y slide de una cilíndrica).",
                    "Para dos uniones distintas, joint1 y joint2 son los ids o nombres de cada una.")
    for u in (u1, u2):
        if not any(MOVIMIENTOS[u.p.get("tipo")]):
            raise error("INVALID_ARGUMENTS", f"La unión «{u.nombre}» es rígida: no tiene movimiento para vincular.")
    doc = sesion.doc
    # ASM-2: una unión no puede seguir a dos vínculos y la cadena no puede volver al que manda.
    enlaces = {o.p.get("union2"): o for o in doc.operaciones
               if isinstance(o, OpVinculoMovimiento) and not o.suprimida}
    if u2.id in enlaces:
        raise error("INVALID_ARGUMENTS", f"La unión «{u2.nombre}» ya la mueve el vínculo «{enlaces[u2.id].nombre}»: "
                    "una unión solo puede seguir a un vínculo.",
                    "Elegí otra unión para joint2 o borrá el vínculo que ya la mueve.")
    actual, vistos = u1.id, set()
    while actual in enlaces and actual not in vistos:
        vistos.add(actual)
        actual = enlaces[actual].p.get("union1")
        if actual == u2.id:
            raise error("INVALID_ARGUMENTS", f"El vínculo «{u1.nombre}» → «{u2.nombre}» armaría un círculo: "
                        f"«{u2.nombre}» ya mueve a «{u1.nombre}».", "Elegí las uniones en el otro sentido.")
    for u, m in ((u1, motion1), (u2, motion2)):
        if m:
            _movimiento_de(u.p.get("tipo"), m)
    cero = ratio == 0 if not isinstance(ratio, str) else False
    if isinstance(ratio, str):
        try:
            cero = float(ratio.strip()) == 0
        except ValueError:
            pass                                              # expresión: la valida el paso al calcular
    if cero:
        raise error("INVALID_ARGUMENTS", "La relación del vínculo no puede ser cero: la unión 2 no se movería.",
                    "Usá reverse=true para invertir el sentido.")
    op = OpVinculoMovimiento(doc.nuevo_id(), nombre_paso(sesion, name, "Vínculo de movimiento", OpVinculoMovimiento),
                             union1=u1.id, union2=u2.id, factor=_expr(ratio), invertir=bool(reverse),
                             mov1=MOVIMIENTO[motion1] if motion1 else "", mov2=MOVIMIENTO[motion2] if motion2 else "")
    antes = _matrices(sesion)
    resultado = _agregar(sesion, op)
    resultado["motion_link"] = _info_vinculo(op)
    resultado["joint2"] = info_union(sesion, u2)
    resultado["moved_components"] = _movidos(sesion, antes)
    return resultado


# ---------------------------------------------------------------- estudio de movimiento
def _simular(doc, op, params):
    """Estado final del timeline con la unión `op` cambiada por `params`, sin tocar el documento (como el recálculo,
    pero sobre copias). Devuelve (estado, avisos de la unión, error de la unión o None)."""
    i = doc.indice(op.id)
    try:
        valores = doc.parametros.valores()
    except ErrorExpresion:
        valores = {}
    estado = doc.estado_en(i)
    avisos, fallo = [], None
    params = dict(params, accionada=siguiente_accion(doc.operaciones))
    for j in range(i, doc.marcador):
        o = OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, **params)) if j == i else doc.operaciones[j].copia()
        if o.suprimida:
            continue
        nuevo, ctx = estado.copia(), Contexto(valores, o.id not in doc._sin_partir)
        try:
            o.calcular(nuevo, ctx)
        except Exception as e:  # noqa: BLE001 — un paso que falla queda como en el recálculo (sin cambiar el estado)
            if j == i:
                fallo = str(e)
            continue
        if j == i:
            avisos = list(ctx.avisos)
        estado = nuevo
    return estado, avisos, fallo


@herramienta("motion_study", "ensamble", "Estudio de movimiento (ENSAMBLAR › Estudio de movimiento): recorre una unión "
             "por varios valores y, para cada uno, dice dónde quedan los componentes y, con check_interference, qué "
             "cuerpos chocan. NO cambia el documento. values da los valores (grados o mm); si no, de start a end en "
             "steps pasos (una unión que gira va de 0 a 360 si no se dan).")
def motion_study(sesion, joint: str, values: list[float] | None = None, start: float | None = None,
                 end: float | None = None, steps: int = 13, motion: Movimiento | None = None,
                 check_interference: bool = False, bodies: list[str] | None = None):
    """
    joint: id o nombre de la unión a recorrer.
    values: valores a probar (grados si es un giro, mm si es un deslizamiento); vacío = de start a end.
    start: primer valor (con values vacío); en una unión que gira, 0 si no se da.
    end: último valor (con values vacío); en una unión que gira, 360 si no se da.
    steps: cantidad de valores entre start y end, ambos incluidos (2 a 360).
    motion: movimiento a recorrer: "rotation", "slide", "rotation2", "rotation3" o "slide2"; vacío = el principal.
    check_interference: true busca choques entre los cuerpos sólidos en cada valor (más lento).
    bodies: con check_interference, los cuerpos a revisar (ids o nombres); vacío = todos los sólidos del modelo.
    """
    op = union(sesion, joint)
    doc = sesion.doc
    if doc.indice(op.id) >= doc.marcador or op.suprimida:
        raise error("INVALID_ARGUMENTS", f"La unión «{op.nombre}» está suprimida o después del marcador: no se calcula.")
    tipo = op.p.get("tipo")
    giros, desliz = MOVIMIENTOS[tipo]
    if not giros and not desliz:
        raise error("INVALID_ARGUMENTS", "Una unión rígida no tiene movimiento para recorrer.")
    clave = MOVIMIENTO[motion] if motion else ("giro" if giros else "desliz")
    if clave not in giros + desliz:
        raise error("INVALID_ARGUMENTS", f"Una unión {A_INGLES[tipo]} no tiene «{motion}». Movimientos: "
                    f"{', '.join(A_MOVIMIENTO[k] for k in giros + desliz)}.")
    gira = clave.startswith("giro")
    if values:
        lista = [float(v) for v in values]
    else:
        if not gira and (start is None or end is None):
            raise error("INVALID_ARGUMENTS", "Para un deslizamiento pasá values o start y end (mm).")
        if not 2 <= steps <= MAX_PASOS_ESTUDIO:
            raise error("INVALID_ARGUMENTS", f"steps va de 2 a {MAX_PASOS_ESTUDIO}.")
        lista = [float(v) for v in np.linspace(0.0 if start is None else start, 360.0 if end is None else end, steps)]
    if len(lista) > MAX_PASOS_ESTUDIO:
        raise error("INVALID_ARGUMENTS", f"Como mucho {MAX_PASOS_ESTUDIO} valores por estudio.")
    if not all(np.isfinite(lista)):
        raise error("INVALID_ARGUMENTS", "Los valores tienen que ser números finitos.")
    revisar = None
    if check_interference and bodies:
        revisar = {sesion.cuerpo(b).id for b in bodies}
    unidad = "deg" if gira else "mm"
    pasos, choques = [], []
    base = _matrices(sesion)
    for v in lista:
        estado, avisos, fallo = _simular(doc, op, {clave: repr(v)})
        u = estado.uniones.get(op.id)
        paso = {"value": _r(v), "applied_value": _r(u["valores"].get(clave)) if u else None, "warnings": avisos,
                "error": fallo}
        if u:
            movidos = sorted(set(u["componentes"]) | {k for k in estado.componentes       # también los que sigue un vínculo
                                                      if k in base and not np.allclose(_matriz(estado, k), base[k])})
            paso["components"] = [{"id": k, "name": _nombre_comp(estado, k),
                                   "translation": [_r(x) for x in _matriz(estado, k)[:3, 3]],
                                   "bounding_box": _caja([c for c in estado.cuerpos.values() if c.componente == k])}
                                  for k in movidos]
        if check_interference:
            solidos = {c.id: c.forma for c in cuerpos_del_modelo(estado) if getattr(c, "tipo", "solido") == "solido"
                       and (revisar is None or c.id in revisar)}
            pares = [{"a": i["a"], "b": i["b"], "volume": _r_chico(i["volumen"])} for i in an.interferencias(solidos)]
            paso["interference"] = pares
            if pares:
                choques.append(_r(v))
        pasos.append(paso)
    resultado = {"joint": {"id": op.id, "name": op.nombre, "type": A_INGLES.get(tipo, tipo)},
                 "motion": A_MOVIMIENTO[clave], "unit": unidad, "steps": pasos, "document_changed": False}
    if check_interference:
        resultado["collision_values"] = choques
    return resultado


# ---------------------------------------------------------------- anclar, posición inicial, capturar y revertir
def _paso_componentes(sesion, clase, base, components, name):
    ids = [componente(sesion, c) for c in components] if components else []
    doc = sesion.doc
    op = clase(doc.nuevo_id(), nombre_paso(sesion, name, base, clase), componentes=ids)
    resultado = _agregar(sesion, op)
    estado = doc.estado_final
    resultado["components"] = [info_componente(sesion, k, estado) for k in (ids or estado.componentes)]
    return resultado


@herramienta("pin_component", "ensamble", "Ancla o desancla un componente a la raíz (ENSAMBLAR › Anclar / Desanclar, "
             "Pin / Unpin): queda como un paso del timeline, que se puede suprimir o borrar. Una unión no puede mover un "
             "componente anclado (como uno fijo con ground_component).", modifica=True)
def pin_component(sesion, component: str, pinned: bool = True, name: str | None = None):
    """
    component: id, nombre o un cuerpo del componente.
    pinned: true lo ancla; false lo desancla.
    name: nombre del paso; vacío = «Anclar<n>» o «Desanclar<n>».
    """
    k = componente(sesion, component)
    doc = sesion.doc
    op = OpAnclar(doc.nuevo_id(), nombre_paso(sesion, name, "Anclar" if pinned else "Desanclar", OpAnclar),
                  componente=k, anclado=bool(pinned))
    resultado = _agregar(sesion, op)
    resultado["component"] = info_componente(sesion, k)
    return resultado


@herramienta("set_component_initial_position", "ensamble", "Posición inicial de un componente (ENSAMBLAR › Editar "
             "posición inicial): lo gira alrededor del centro de su caja envolvente (X, luego Y, luego Z) y lo "
             "desplaza. Devuelve el componente con su traslación y su caja.", modifica=True)
def set_component_initial_position(sesion, component: str, offset: list[Expr] | None = None,
                                   rotation: list[Expr] | None = None, name: str | None = None):
    """
    component: id, nombre o un cuerpo del componente.
    offset: desplazamiento [x, y, z] en mm (número o expresión); vacío = ninguno.
    rotation: giro [rx, ry, rz] en grados alrededor del centro de la caja del componente; vacío = ninguno.
    name: nombre del paso; vacío = «Posición inicial<n>».
    """
    k = componente(sesion, component)
    for valor, que in ((offset, "offset"), (rotation, "rotation")):
        if valor is not None and len(valor) != 3:
            raise error("INVALID_ARGUMENTS", f"{que} va como [x, y, z] (recibió {len(valor)} valores).")
    p = {}
    for claves, valor in ((("x", "y", "z"), offset), (("rx", "ry", "rz"), rotation)):
        if valor is not None:
            p.update({c: _expr(v) for c, v in zip(claves, valor, strict=True)})
    doc = sesion.doc
    op = OpPosicionInicial(doc.nuevo_id(), nombre_paso(sesion, name, "Posición inicial", OpPosicionInicial),
                           componente=k, **p)
    resultado = _agregar(sesion, op)
    resultado["component"] = info_componente(sesion, k)
    return resultado


def _capturar_arrastres(sesion):
    """Pasa lo arrastrado sin capturar al timeline: el valor de cada unión y un paso de posición por componente libre,
    antes de la primera unión que cuelga de él para que esa unión y su marco lo sigan."""
    doc = sesion.doc
    p = pendiente_de(doc)
    if p is None:
        return
    for uid, valores in p.valores.items():
        op = doc.operacion(uid)
        nuevos = {c: f"{v:.9g} deg" if c.startswith("giro") else f"{v:.9g} mm" for c, v in valores.items()}
        doc.reemplazar(uid, OpUnion(op.id, op.nombre, op.suprimida, **dict(
            op.p, **nuevos, accionada=siguiente_accion(doc.operaciones))))
    for comp, d in p.libres.items():
        op = OpPosicionInicial(doc.nuevo_id(), nombre_paso(sesion, None, "Posición inicial", OpPosicionInicial), componente=comp,
                               **{c: f"{v:.9g} mm" for c, v in zip("xyz", d, strict=True)})
        doc.agregar(op)
        cuelga = (i for i, o in enumerate(doc.operaciones) if p.estado.uniones.get(o.id, {}).get("comp2") == comp)
        primera = next(cuelga, None)
        if primera is not None:
            doc.mover(op.id, primera)


@herramienta("capture_position", "ensamble", "Captura la posición actual de los componentes (ENSAMBLAR › Posición › "
             "Capturar posición): queda como la de referencia a la que vuelve revert_position. Lo arrastrado con "
             "drag_component pasa al timeline: el valor de cada unión y un paso de posición por componente libre.",
             modifica=True)
def capture_position(sesion, components: list[str] | None = None, name: str | None = None):
    """
    components: componentes a capturar (id, nombre o un cuerpo); vacío = todos.
    name: nombre del paso; vacío = «Capturar posición<n>».
    """
    _capturar_arrastres(sesion)
    return _paso_componentes(sesion, OpCapturarPosicion, "Capturar posición", components, name)


@herramienta("revert_position", "ensamble", "Revierte los componentes a su última posición capturada con "
             "capture_position (ENSAMBLAR › Posición › Revertir) o, si nunca se capturó, a donde se modelaron. Si hay "
             "algo arrastrado sin capturar, solo descarta eso: no agrega ningún paso.", modifica=True)
def revert_position(sesion, components: list[str] | None = None, name: str | None = None):
    """
    components: componentes a revertir (id, nombre o un cuerpo); vacío = todos.
    name: nombre del paso; vacío = «Revertir posición<n>».
    """
    if pendiente_de(sesion.doc) is not None:
        sesion.doc.posicion_pendiente = None
        return {"reverted_uncaptured": True,
                "components": [info_componente(sesion, k) for k in sesion.doc.estado_final.componentes]}
    return _paso_componentes(sesion, OpRevertirPosicion, "Revertir posición", components, name)


def _componentes_en_poses(sesion, estado, poses):
    """Información de cada componente como si sus cuerpos estuvieran en `poses`, con la traslación que tiene hoy."""
    movido = estado.copia()
    for k in estado.componentes:
        m = next((poses[c.id] for c in estado.cuerpos.values() if c.componente == k and c.id in poses), None)
        if m is not None:
            _mover_componentes(movido, {k}, m)
    return [dict(info_componente(sesion, k, movido), previous_translation=info_componente(sesion, k)["translation"])
            for k in estado.componentes]


@herramienta("drag_component", "ensamble", "Arrastra un componente como con el mouse en el visor (ENSAMBLAR › "
             "Posición): con una unión sigue sus grados de libertad y sus límites; sin unión se traslada libre. NO cambia "
             "el documento: la posición queda sin capturar hasta capture_position o revert_position, y cualquier otro "
             "cambio del documento la descarta. Devuelve dónde quedó cada componente.")
def drag_component(sesion, component: str, offset: list[float], point: list[float] | None = None):
    """
    component: id, nombre o un cuerpo del componente.
    offset: hacia dónde se lleva el punto agarrado [x, y, z] en mm.
    point: punto agarrado [x, y, z] en mm; vacío = el centro de la caja de un cuerpo del componente.
    """
    k = componente(sesion, component)
    estado = sesion.doc.estado_final
    if len(offset) != 3 or (point is not None and len(point) != 3):
        raise error("INVALID_ARGUMENTS", "offset y point van como [x, y, z].")
    if not np.isfinite([*offset, *(point or ())]).all():
        raise error("INVALID_ARGUMENTS", "offset y point tienen que ser números finitos.")
    cuerpo = next((c for c in estado.cuerpos.values() if c.componente == k), None)
    if cuerpo is None:
        raise error("INVALID_ARGUMENTS", f"El componente «{component}» no tiene cuerpos que arrastrar.")
    if point is None:
        p = pendiente_de(sesion.doc)
        centro = np.mean(geo.caja_envolvente(cuerpo.forma) if cuerpo.tipo != "malla" else cuerpo.forma.caja(), axis=0)
        pose = p.poses().get(cuerpo.id, np.identity(4)) if p is not None else np.identity(4)
        point = (pose @ np.r_[centro, 1.0])[:3]
    try:
        arrastre = Arrastre(sesion.doc, cuerpo.id, point)
    except ErrorOperacion as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None
    arrastre.mover(np.add(point, offset))
    arrastre.soltar()
    p = pendiente_de(sesion.doc)
    return {"components": _componentes_en_poses(sesion, estado, p.poses() if p is not None else {}),
            "uncaptured": p is not None, "document_changed": False}


@herramienta("motion_study_pose", "ensamble", "Estudio de movimiento con varias uniones a la vez (ENSAMBLAR › Estudio de "
             "movimiento): dónde quedan los componentes si cada unión de values tiene ese valor. Una unión que sigue a "
             "un vínculo toma el valor de la otra. NO cambia el documento. (Reproducir, modo y velocidad son de la "
             "ventana: ver docs/brechas_mcp.md.)")
def motion_study_pose(sesion, values: dict):
    """
    values: valor de cada unión: {"Unión1": 90, "Unión2:slide": 12.5}; la clave es la unión (id o nombre) y, tras ":", el movimiento ("rotation", "rotation2", "rotation3", "slide" o "slide2"; vacío = el principal). Grados o mm.
    """
    estado = sesion.doc.estado_final
    if not values:
        raise error("INVALID_ARGUMENTS", "Falta values: el valor de al menos una unión.")
    pedidos = {}
    for ref, v in values.items():
        nombre, _, mov = str(ref).partition(":")
        op = union(sesion, nombre.strip())
        if op.id not in estado.uniones:
            raise error("INVALID_ARGUMENTS", f"La unión «{op.nombre}» no está calculada (¿suprimida o después del "
                        "marcador?).")
        tipo = op.p.get("tipo")
        if not any(MOVIMIENTOS[tipo]):
            raise error("INVALID_ARGUMENTS", f"La unión «{op.nombre}» es rígida: no tiene movimiento.")
        clave = _movimiento_de(tipo, mov.strip()) if mov.strip() else principal_de(tipo)
        try:
            valor = float(v)
        except (TypeError, ValueError):
            raise error("INVALID_ARGUMENTS", f"El valor de «{ref}» tiene que ser un número (recibió {v!r}).") from None
        if not np.isfinite(valor):
            raise error("INVALID_ARGUMENTS", f"El valor de «{ref}» tiene que ser finito.")
        pedidos.setdefault(op.id, {})[clave] = valor
    return {"components": _componentes_en_poses(sesion, estado, poses_de_estudio(estado, pedidos)),
            "document_changed": False}
