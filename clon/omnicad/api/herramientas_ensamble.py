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
  - un origen de unión (create_joint_origin), un plano, eje o punto de construcción: su propio marco.
Las caras y aristas se eligen como en el resto de la API: selector ('>Z', '%CYLINDER', 'edges:%CIRCLE'…, evaluado
sobre `body1` / `body2`) o id de find_faces / find_edges ('Cuerpo1/F3', 'Cuerpo1/E5'). Lo que se guarda en el
paso es la referencia persistente: la unión sigue a su cara cuando cambia un parámetro.

Componentes, uniones y grupos se nombran por id (el del paso que los creó, p. ej. 'op5') o por nombre; un
componente también por el id o el nombre de uno de sus cuerpos.
"""
import difflib
from typing import Literal

import numpy as np

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from ..timeline.operaciones import Contexto
from ..timeline.ops_chapa import cuerpos_del_modelo
from ..timeline.ops_ensamblar import (MOVIMIENTOS, OpComponente, OpGrupoRigido, OpInsertarDiseno, OpOrigenUnion,
                                      OpUnion, OpVinculoMovimiento)
from ..timeline.parametros import ErrorExpresion
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_documento import ESTADOS
from .herramientas_solido import _agregar
from .registro import Expr, herramienta

TIPOS = {"rigid": "rigida", "revolute": "revolucion", "slider": "deslizante", "cylindrical": "cilindrica",
         "pin_slot": "pasador_ranura", "planar": "planar", "ball": "bola"}
A_INGLES = {v: k for k, v in TIPOS.items()}
TipoUnion = Literal["rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar", "ball"]
SNAP = {"center": "centro", "start": "inicio", "end": "fin"}
Snap = Literal["center", "start", "end"]
Eje = Literal["X", "Y", "Z"]
MOVIMIENTO = {"rotation": "giro", "rotation2": "giro2", "rotation3": "giro3", "slide": "desliz", "slide2": "desliz2"}
A_MOVIMIENTO = {v: k for k, v in MOVIMIENTO.items()}
Movimiento = Literal["rotation", "rotation2", "rotation3", "slide", "slide2"]
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
    if estado.componentes.get(cuerpo.componente, {}).get("fijo"):
        raise error("INVALID_ARGUMENTS", f"El componente «{_nombre_comp(estado, cuerpo.componente)}» está fijo: una "
                    "unión no puede moverlo.", "Elegí como origin1 la pieza que se mueve, o liberala con "
                    "ground_component(grounded=false).")
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
            "bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c)} for c in cuerpos],
            "translation": [_r(v) for v in m[:3, 3]], "rotation_matrix": [[_r(v) for v in fila] for fila in m[:3, :3]],
            "bounding_box": _caja(cuerpos)}


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
                and not o.suprimida]
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
    return info


def _info_vinculo(op):
    return {"id": op.id, "name": op.nombre, "joint1": op.p.get("union1"), "joint2": op.p.get("union2"),
            "ratio": op.p.get("factor"), "reverse": bool(op.p.get("invertir")), "suppressed": op.suprimida}


def _movidos(sesion, antes):
    """Componentes cuya posición cambió respecto de `antes` ({id: matriz})."""
    estado = sesion.doc.estado_final
    return [info_componente(sesion, k) for k in estado.componentes
            if k not in antes or not np.allclose(_matriz(estado, k), antes[k], atol=1e-9)]


def _matrices(sesion):
    estado = sesion.doc.estado_final
    return {k: _matriz(estado, k) for k in estado.componentes}


# ---------------------------------------------------------------- consulta
@herramienta("get_assembly", "ensamble", "Ensamble del documento: componentes (id, nombre, fijo, cuerpos, posición: "
             "traslación y rotación respecto de donde se modelaron, caja envolvente), uniones (tipo, componentes, "
             "valores actuales de giro en grados y deslizamiento en mm, límites, ejes, estado), orígenes de unión, "
             "grupos rígidos, vínculos de movimiento y los cuerpos sueltos en la raíz.")
def get_assembly(sesion):
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
    return {"components": [info_componente(sesion, k) for k in estado.componentes],
            "joints": [info_union(sesion, o) for o in ops if isinstance(o, OpUnion)],
            "joint_origins": origenes, "rigid_groups": grupos,
            "motion_links": [_info_vinculo(o) for o in ops if isinstance(o, OpVinculoMovimiento)],
            "root_bodies": [{"id": c.id, "name": sesion.nombre_cuerpo(c)} for c in raiz],
            "units": {"length": "mm", "angle": "deg"}}


# ---------------------------------------------------------------- componentes
@herramienta("create_component", "ensamble", "Crea un componente con los cuerpos dados (ENSAMBLAR › Nuevo componente "
             "desde cuerpos). Las uniones mueven componentes, no cuerpos sueltos. grounded=true lo fija en su lugar "
             "(ninguna unión puede moverlo; suele ser la base). Un cuerpo que ya estaba en otro componente pasa al "
             "nuevo.", modifica=True)
def create_component(sesion, bodies: list[str], name: str | None = None, grounded: bool = False):
    """
    bodies: ids o nombres de los cuerpos del componente (al menos uno).
    name: nombre del componente; vacío = «Componente<n>».
    grounded: true para fijarlo (Ground): ninguna unión lo mueve.
    """
    if not bodies:
        raise error("INVALID_ARGUMENTS", "Falta elegir los cuerpos del componente.")
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
                      cuerpos=[c.id for c in cuerpos], fijo=grounded)
    resultado = _agregar(sesion, op)
    resultado["component"] = info_componente(sesion, op.id)
    return resultado


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
        salida[k] = texto_expr(valor)
    return salida


def _limites(tipo, minimum, maximum):
    giros, desliz = MOVIMIENTOS[tipo]
    if (minimum is not None or maximum is not None) and not (giros or desliz):
        raise error("INVALID_ARGUMENTS", "Una unión rígida no tiene movimiento que limitar.")
    if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum > maximum:
        raise error("INVALID_ARGUMENTS", f"El mínimo ({minimum:g}) es mayor que el máximo ({maximum:g}).")
    return {"minimo": "" if minimum is None else texto_expr(minimum),
            "maximo": "" if maximum is None else texto_expr(maximum)}


def _desfase(offset):
    if offset is None:
        return {}
    if len(offset) != 3:
        raise error("INVALID_ARGUMENTS", f"offset va como [dx, dy, dz] en mm (recibió {len(offset)} valores).")
    return {k: texto_expr(v) for k, v in zip(("dx", "dy", "dz"), offset, strict=True)}


def _crear_union(sesion, nombre, params):
    antes = _matrices(sesion)
    doc = sesion.doc
    op = OpUnion(doc.nuevo_id(), nombre_paso(sesion, nombre, "Unión", OpUnion), **params)
    resultado = _agregar(sesion, op)
    resultado["joint"] = info_union(sesion, op)
    resultado["moved_components"] = _movidos(sesion, antes)
    return resultado


@herramienta("create_joint", "ensamble", "Une dos componentes (ENSAMBLAR › Unión): mueve el componente de origin1 "
             "hasta que su marco coincide con el de origin2 (caras planas enfrentadas; dos ejes —perno en agujero— en "
             "el mismo sentido) y define cómo se mueve después. " + _DESC_ORIGEN + _DESC_TIPOS +
             "angle gira el componente 1 alrededor del Z del marco, offset lo corre [dx, dy, dz] y flip lo da vuelta. "
             "Los valores (rotation, slide…) y los límites aceptan número (grados o mm) o expresión. Devuelve la unión "
             "y los componentes que se movieron con su traslación y caja envolvente.", modifica=True)
def create_joint(sesion, origin1: str, origin2: str, joint_type: TipoUnion = "rigid", body1: str | None = None,
                 body2: str | None = None, snap1: Snap = "center", snap2: Snap = "center", angle: Expr = 0,
                 offset: list[Expr] | None = None, flip: bool = False, rotation_axis: Eje = "Z", slide_axis: Eje = "X",
                 rotation: Expr | None = None, rotation2: Expr | None = None, rotation3: Expr | None = None,
                 slide: Expr | None = None, slide2: Expr | None = None, minimum: Expr | None = None,
                 maximum: Expr | None = None, name: str | None = None):
    """
    origin1: dónde se toma el componente que SE MUEVE: cara o arista (selector o id), del cuerpo body1.
    origin2: dónde va: cara o arista de otro componente (o de la raíz), origen de unión, plano, eje o punto de construcción.
    joint_type: "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
    body1: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin1; con un id no hace falta.
    body2: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin2.
    snap1: punto del origen 1 en una arista o cilindro: "center" (medio), "start" o "end".
    snap2: punto del origen 2: "center", "start" o "end".
    angle: giro del componente 1 alrededor del eje Z del marco de la unión, en grados.
    offset: desfase [dx, dy, dz] en mm en el marco de la unión (Z = normal o eje).
    flip: true da vuelta el componente 1 (caras en el mismo sentido o ejes opuestos).
    rotation_axis: eje del marco para girar (revolute, cylindrical, pin_slot) o normal del plano (planar).
    slide_axis: eje del marco para deslizar (slider, pin_slot).
    rotation: giro inicial en grados (revolute, cylindrical, pin_slot, planar, ball).
    rotation2: segundo giro (cabeceo) en grados; solo ball.
    rotation3: tercer giro (guiñada) en grados; solo ball.
    slide: deslizamiento inicial en mm (slider, cylindrical, pin_slot, planar).
    slide2: segundo deslizamiento en mm; solo planar.
    minimum: límite mínimo del movimiento principal (grados si gira, mm si solo desliza); vacío = sin límite.
    maximum: límite máximo del movimiento principal; vacío = sin límite.
    name: nombre del paso; vacío = «Unión<n>».
    """
    tipo = TIPOS[joint_type]
    ref1, c1 = _origen(sesion, origin1, body1)
    _componente_del_origen(sesion, c1, "origin1")
    ref2, c2 = _origen(sesion, origin2, body2)
    if c2 is not None and (c2.componente or "") == c1.componente:
        raise error("INVALID_ARGUMENTS", "Los dos orígenes están en el mismo componente: origin2 tiene que ser de otro "
                    "componente (o de la raíz).")
    params = {"tipo": tipo, "origen1": ref1, "origen2": ref2, "clave1": SNAP[snap1], "clave2": SNAP[snap2],
              "angulo": texto_expr(angle), "voltear": bool(flip), "como_esta": False, "eje_giro": rotation_axis,
              "eje_desliz": slide_axis}
    params.update(_desfase(offset))
    params.update(_valores(tipo, {"rotation": rotation, "rotation2": rotation2, "rotation3": rotation3,
                                  "slide": slide, "slide2": slide2}))
    params.update(_limites(tipo, minimum, maximum))
    return _crear_union(sesion, name, params)


@herramienta("create_as_built_joint", "ensamble", "Unión como está (ENSAMBLAR › Unión como está): liga el componente "
             "de `origin` al componente `component2` SIN moverlo de donde está y define su movimiento alrededor del "
             "marco de `origin` (p. ej. el eje de un agujero para una bisagra). Cuando el componente 2 se mueve, el 1 "
             "lo sigue. Sin component2, la unión es contra la raíz. " + _DESC_TIPOS, modifica=True)
def create_as_built_joint(sesion, origin: str, component2: str | None = None, joint_type: TipoUnion = "revolute",
                          body: str | None = None, snap: Snap = "center", rotation_axis: Eje = "Z",
                          slide_axis: Eje = "X", rotation: Expr | None = None, rotation2: Expr | None = None,
                          rotation3: Expr | None = None, slide: Expr | None = None, slide2: Expr | None = None,
                          minimum: Expr | None = None, maximum: Expr | None = None, name: str | None = None):
    """
    origin: cara o arista del componente que se mueve (selector evaluado sobre body, o id); define el marco del movimiento.
    component2: componente al que queda ligado (id, nombre o uno de sus cuerpos); vacío = la raíz.
    joint_type: "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
    body: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin.
    snap: punto del origen en una arista o cilindro: "center", "start" o "end".
    rotation_axis: eje del marco para girar (o normal del plano en planar).
    slide_axis: eje del marco para deslizar (slider, pin_slot).
    rotation: giro en grados.
    rotation2: segundo giro en grados (ball).
    rotation3: tercer giro en grados (ball).
    slide: deslizamiento en mm.
    slide2: segundo deslizamiento en mm (planar).
    minimum: límite mínimo del movimiento principal; vacío = sin límite.
    maximum: límite máximo del movimiento principal; vacío = sin límite.
    name: nombre del paso; vacío = «Unión<n>».
    """
    tipo = TIPOS[joint_type]
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
              "eje_giro": rotation_axis, "eje_desliz": slide_axis}
    params.update(_valores(tipo, {"rotation": rotation, "rotation2": rotation2, "rotation3": rotation3,
                                  "slide": slide, "slide2": slide2}))
    params.update(_limites(tipo, minimum, maximum))
    return _crear_union(sesion, name, params)


@herramienta("create_joint_origin", "ensamble", "Origen de unión (ENSAMBLAR › Origen de la unión): guarda un marco "
             "(punto con orientación) sobre una cara o arista, con giro y desfase, para usarlo después como origin2 de "
             "create_joint. Sobre un cilindro o una arista circular sigue siendo un marco de eje.", modifica=True)
def create_joint_origin(sesion, geometry: str, body: str | None = None, snap: Snap = "center", angle: Expr = 0,
                        offset: list[Expr] | None = None, name: str | None = None):
    """
    geometry: cara o arista donde va el origen (selector evaluado sobre body, o id de find_faces / find_edges).
    body: cuerpo (o componente de un solo cuerpo) donde se evalúa el selector.
    snap: punto en una arista o cilindro: "center", "start" o "end".
    angle: giro del marco alrededor de su Z, en grados.
    offset: desfase [dx, dy, dz] en mm en el marco.
    name: nombre del paso; vacío = «Origen de unión<n>».
    """
    ref, _c = _origen(sesion, geometry, body)
    doc = sesion.doc
    op = OpOrigenUnion(doc.nuevo_id(), nombre_paso(sesion, name, "Origen de unión", OpOrigenUnion), origen=ref,
                       clave=SNAP[snap], angulo=texto_expr(angle), **_desfase(offset))
    resultado = _agregar(sesion, op)
    plano = sesion.doc.estado_final.planos.get(op.id)
    if plano is not None:
        resultado["joint_origin"] = {"id": op.id, "name": op.nombre, "origin": [_r(v) for v in plano.origen],
                                     "x_axis": [_r(v) for v in plano.u], "z_axis": [_r(v) for v in plano.normal]}
    return resultado


@herramienta("drive_joint", "ensamble", "Acciona una unión (ENSAMBLAR › Accionar uniones): cambia su giro o "
             "deslizamiento y el mecanismo se recalcula (las uniones y vínculos que dependen de ella la siguen). Los "
             "límites recortan el valor y avisan. Cada valor acepta número (grados o mm) o expresión.", modifica=True)
def drive_joint(sesion, joint: str, rotation: Expr | None = None, slide: Expr | None = None,
                rotation2: Expr | None = None, rotation3: Expr | None = None, slide2: Expr | None = None):
    """
    joint: id o nombre de la unión.
    rotation: giro en grados (revolute, cylindrical, pin_slot, planar, ball).
    slide: deslizamiento en mm (slider, cylindrical, pin_slot, planar).
    rotation2: segundo giro en grados (ball).
    rotation3: tercer giro en grados (ball).
    slide2: segundo deslizamiento en mm (planar).
    """
    op = union(sesion, joint)
    pedidos = {"rotation": rotation, "slide": slide, "rotation2": rotation2, "rotation3": rotation3, "slide2": slide2}
    if all(v is None for v in pedidos.values()):
        raise error("INVALID_ARGUMENTS", "Falta el valor a accionar: rotation (grados) o slide (mm).")
    tipo = op.p.get("tipo")
    nuevos = _valores(tipo, pedidos)
    vinculos = [o for o in sesion.doc.operaciones if isinstance(o, OpVinculoMovimiento) and not o.suprimida
                and o.p.get("union2") == op.id]
    if vinculos:
        sesion.avisar(f"La unión «{op.nombre}» la mueve el vínculo «{vinculos[0].nombre}»: su valor sale de la otra "
                      "unión. Accioná esa.")
    antes = _matrices(sesion)
    sesion.doc.reemplazar(op.id, OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, **nuevos)))
    return {"joint": info_union(sesion, sesion.doc.operacion(op.id)), "moved_components": _movidos(sesion, antes)}


@herramienta("set_joint_limits", "ensamble", "Límites de movimiento de una unión (Joint Limits de Fusion) sobre su "
             "movimiento principal: el giro (grados) si gira, si no el deslizamiento (mm). Un valor vacío quita ese "
             "límite. Si el valor actual queda afuera, la unión se recorta al límite y avisa.", modifica=True)
def set_joint_limits(sesion, joint: str, minimum: Expr | None = None, maximum: Expr | None = None):
    """
    joint: id o nombre de la unión.
    minimum: límite mínimo (número o expresión); vacío = sin límite mínimo.
    maximum: límite máximo (número o expresión); vacío = sin límite máximo.
    """
    op = union(sesion, joint)
    limites = _limites(op.p.get("tipo"), minimum, maximum)
    antes = _matrices(sesion)
    sesion.doc.reemplazar(op.id, OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, **limites)))
    return {"joint": info_union(sesion, sesion.doc.operacion(op.id)), "moved_components": _movidos(sesion, antes)}


# ---------------------------------------------------------------- grupos y vínculos
@herramienta("create_rigid_group", "ensamble", "Grupo rígido (ENSAMBLAR › Grupo rígido): los componentes se mueven "
             "juntos; una unión que mueve a uno mueve a todos.", modifica=True)
def create_rigid_group(sesion, components: list[str], name: str | None = None):
    """
    components: componentes del grupo (id, nombre o uno de sus cuerpos); al menos dos distintos.
    name: nombre del paso; vacío = «Grupo rígido<n>».
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
    op = OpGrupoRigido(doc.nuevo_id(), nombre_paso(sesion, name, "Grupo rígido", OpGrupoRigido), componentes=ids)
    resultado = _agregar(sesion, op)
    estado = sesion.doc.estado_final
    resultado["rigid_group"] = {"id": op.id, "name": op.nombre, "components": [_ref_componente(estado, k) for k in ids]}
    return resultado


@herramienta("create_motion_link", "ensamble", "Vínculo de movimiento (ENSAMBLAR › Vínculo de movimiento): la unión 2 "
             "se mueve en proporción a la 1 (engranajes, cremallera y piñón). El valor de la unión 2 pasa a ser "
             "ratio × el de la unión 1 (con reverse, el opuesto); se acciona la unión 1 con drive_joint.", modifica=True)
def create_motion_link(sesion, joint1: str, joint2: str, ratio: Expr = 1, reverse: bool = False,
                       name: str | None = None):
    """
    joint1: unión que manda (id o nombre).
    joint2: unión que la sigue (id o nombre).
    ratio: relación unión 2 / unión 1 (número o expresión): grados por grado, mm por grado, etc.
    reverse: true invierte el sentido de la unión 2.
    name: nombre del paso; vacío = «Vínculo de movimiento<n>».
    """
    u1, u2 = union(sesion, joint1), union(sesion, joint2)
    if u1.id == u2.id:
        raise error("INVALID_ARGUMENTS", "Elegí dos uniones distintas.")
    for u in (u1, u2):
        if not any(MOVIMIENTOS[u.p.get("tipo")]):
            raise error("INVALID_ARGUMENTS", f"La unión «{u.nombre}» es rígida: no tiene movimiento para vincular.")
    doc = sesion.doc
    op = OpVinculoMovimiento(doc.nuevo_id(), nombre_paso(sesion, name, "Vínculo de movimiento", OpVinculoMovimiento),
                             union1=u1.id, union2=u2.id, factor=texto_expr(ratio), invertir=bool(reverse))
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
    for j in range(i, doc.marcador):
        o = OpUnion(op.id, op.nombre, op.suprimida, **dict(op.p, **params)) if j == i else doc.operaciones[j].copia()
        if o.suprimida:
            continue
        nuevo, ctx = estado.copia(), Contexto(valores)
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
    for v in lista:
        estado, avisos, fallo = _simular(doc, op, {clave: repr(v)})
        u = estado.uniones.get(op.id)
        paso = {"value": _r(v), "applied_value": _r(u["valores"].get(clave)) if u else None, "warnings": avisos,
                "error": fallo}
        if u:
            movidos = sorted(set(u["componentes"]))
            paso["components"] = [{"id": k, "name": _nombre_comp(estado, k),
                                   "translation": [_r(x) for x in _matriz(estado, k)[:3, 3]],
                                   "bounding_box": _caja([c for c in estado.cuerpos.values() if c.componente == k])}
                                  for k in movidos]
        if check_interference:
            solidos = {c.id: c.forma for c in cuerpos_del_modelo(estado) if getattr(c, "tipo", "solido") == "solido"
                       and (revisar is None or c.id in revisar)}
            pares = [{"a": i["a"], "b": i["b"], "volume": _r(i["volumen"])} for i in an.interferencias(solidos)]
            paso["interference"] = pares
            if pares:
                choques.append(_r(v))
        pasos.append(paso)
    resultado = {"joint": {"id": op.id, "name": op.nombre, "type": A_INGLES.get(tipo, tipo)},
                 "motion": A_MOVIMIENTO[clave], "unit": unidad, "steps": pasos, "document_changed": False}
    if check_interference:
        resultado["collision_values"] = choques
    return resultado
