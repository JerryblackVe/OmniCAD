# -*- coding: utf-8 -*-
"""
Herramientas del grupo "solido" que modifican un cuerpo usando caras o aristas: empalme (fillet), chaflán
(chamfer), vaciado (shell), agujero (create_hole) y desmoldeo (draft).

Las caras y aristas se eligen con un selector estilo CadQuery (">Z", "|Z", "%CYLINDER"…, ver
`selectores.py` y la guía `get_guide(topic="selectores")`), con ids de find_faces / find_edges ("Cuerpo1/F3")
o con una lista que mezcle ambos. Los ids valen hasta el próximo cambio del documento; lo que se guarda en el
paso del timeline es SIEMPRE la referencia persistente de `nucleo.referencias` (firma geométrica relativa a la
caja del cuerpo), así el empalme sigue en "su" arista cuando después cambia un parámetro. Si la geometría
cambia tanto que la referencia se pierde, el paso falla con `REFERENCE_LOST` y el documento queda como estaba.

Cada herramienta devuelve lo de las demás de "solido": `feature`, `bodies_created`, `bodies_modified` (con
volumen y `previous_volume`) y `bodies_removed`.
"""
import math
from typing import Literal

import numpy as np

from ..timeline.ops_modificar import OpChaflan, OpDesmoldeo, OpEmpalme, OpVaciado
from ..timeline.ops_solido import OpAgujero
from . import selectores as sl
from .errores import error
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_solido import _agregar, _numero_positivo
from .registro import Expr, herramienta

Elementos = str | list[str]

_ELEGIR = ("Se elige con un selector estilo CadQuery (p. ej. '{ej}'; get_guide topic=selectores), con ids de "
           "find_{que} (p. ej. '{id}', válidos hasta el próximo cambio del documento) o con una lista de ambos. ")
_PERSISTENTE = "Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. "


def _refs(sesion, spec, tipo, body=None, permitir_vacio=False):
    """([referencias persistentes], [(cuerpo, elemento)]) de lo elegido."""
    elegidos = sl.elegir(sesion, spec, tipo, body, permitir_vacio)
    return [sl.referencia(c, e) for c, e in elegidos], elegidos


def _informe(res, elegidos, clave):
    res[clave] = len(elegidos)
    res["bodies_affected"] = sorted({c.id for c, _ in elegidos})
    return res


# ---------------------------------------------------------------- empalme y chaflán
@herramienta("fillet", "solido", "Redondea aristas (empalme de radio constante). " + _ELEGIR.format(
    ej="|Z", que="edges", id="Cuerpo1/E7") + _PERSISTENTE + "El empalme sigue las aristas tangentes encadenadas. Si el "
             "radio no cabe, falla con OPERATION_FAILED y el documento queda igual. radius acepta número (mm) o expresión.",
             modifica=True)
def fillet(sesion, edges: Elementos, radius: Expr, body: str | None = None):
    """
    edges: aristas a redondear: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
    radius: radio en mm (número o expresión con parámetros, p. ej. "espesor / 2").
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    _numero_positivo(radius, "radius")
    refs, elegidos = _refs(sesion, edges, "arista", body)
    doc = sesion.doc
    op = OpEmpalme(doc.nuevo_id(), nombre_nuevo(doc, "Empalme", OpEmpalme), aristas=refs, tipo_radio="constante",
                   radio=texto_expr(radius))
    return _informe(_agregar(sesion, op), elegidos, "edges_used")


@herramienta("chamfer", "solido", "Achaflana aristas (distancia igual en las dos caras). " + _ELEGIR.format(
    ej="|Z", que="edges", id="Cuerpo1/E7") + _PERSISTENTE + "distance acepta número (mm) o expresión.", modifica=True)
def chamfer(sesion, edges: Elementos, distance: Expr, body: str | None = None):
    """
    edges: aristas a achaflanar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
    distance: distancia del chaflán en mm sobre cada cara (número o expresión con parámetros).
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    _numero_positivo(distance, "distance")
    refs, elegidos = _refs(sesion, edges, "arista", body)
    doc = sesion.doc
    op = OpChaflan(doc.nuevo_id(), nombre_nuevo(doc, "Chaflán", OpChaflan), aristas=refs, tipo="distancia_igual",
                   distancia=texto_expr(distance))
    return _informe(_agregar(sesion, op), elegidos, "edges_used")


# ---------------------------------------------------------------- vaciado
_DIRECCION_VACIADO = {"inside": "interior", "outside": "exterior", "both": "ambos"}


@herramienta("shell", "solido", "Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan "
             "(quedan abiertas). " + _ELEGIR.format(ej=">Z", que="faces", id="Cuerpo1/F6") + _PERSISTENTE +
             "direction: inside (las paredes quedan hacia adentro: el cuerpo no crece), outside (hacia afuera) o both. "
             "Con faces=[] (lista vacía) el cuerpo queda hueco y cerrado. Si el espesor es igual o mayor que el radio de un "
             "empalme de las caras vaciadas, el kernel no puede (radio interior cero o negativo): OPERATION_FAILED. "
             "thickness acepta número (mm) o expresión.",
             modifica=True)
def shell(sesion, body: str, faces: Elementos, thickness: Expr, direction: Literal["inside", "outside", "both"] = "inside"):
    """
    body: id o nombre del cuerpo a vaciar.
    faces: caras a quitar: selector (">Z" = la tapa), id de find_faces ("Cuerpo1/F6") o lista; [] = hueco cerrado.
    thickness: espesor de pared en mm (número o expresión con parámetros).
    direction: "inside", "outside" o "both".
    """
    _numero_positivo(thickness, "thickness")
    cuerpo = sl.cuerpo_objetivo(sesion, body)
    refs, elegidos = _refs(sesion, faces, "cara", cuerpo.id, permitir_vacio=True)
    ajenas = {c.id for c, _ in elegidos} - {cuerpo.id}
    if ajenas:
        raise error("INVALID_ARGUMENTS", f"Las caras elegidas son de otro cuerpo ({', '.join(sorted(ajenas))}), no de "
                    f"«{sesion.nombre_cuerpo(cuerpo)}».")
    espesor = texto_expr(thickness)
    doc = sesion.doc
    op = OpVaciado(doc.nuevo_id(), nombre_nuevo(doc, "Vaciado", OpVaciado), caras=refs, cuerpos=[] if refs else [cuerpo.id],
                   espesor_interior=espesor, espesor_exterior=espesor, direccion=_DIRECCION_VACIADO[direction])
    return _informe(_agregar(sesion, op), elegidos, "faces_removed")


# ---------------------------------------------------------------- agujero
_TIPO_AGUJERO = {"simple": "simple", "counterbore": "abocardado", "countersink": "avellanado"}


def _puntos_agujero(plano, centro, points):
    """Posiciones 3D (sobre el plano de la cara) de los agujeros: [u, v] en los ejes de un boceto sobre la cara, o
    [x, y, z] del mundo (se proyecta sobre la cara). Sin puntos, el centro de la cara."""
    if not points:
        return [np.asarray(centro, float)]
    salida = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) not in (2, 3) or not all(
                isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in p):
            raise error("INVALID_ARGUMENTS", f"Cada punto tiene que ser [u, v] (mm, ejes de un boceto sobre la cara) "
                        f"o [x, y, z] (mm, mundo): {p!r}.")
        salida.append(plano.a_3d(*p) if len(p) == 2 else np.asarray(p, float))
    return salida


@herramienta("create_hole", "solido", "Hace agujeros redondos desde una cara plana hacia adentro del material: "
             "simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth) o pasantes "
             "(through_all). La cara se elige con un selector (p. ej. '>Z'), un id de find_faces o 'Cuerpo1/F6'; tiene "
             "que ser UNA sola cara plana. points son las posiciones: [u, v] en mm en los ejes x,y de un boceto sobre "
             "esa cara (find_faces da el center_uv de la cara; create_sketch describe los ejes) o [x, y, z] del mundo "
             "(se proyecta sobre la cara); sin points, un agujero en el centro de la cara. El fondo es plano salvo "
             "drill_tip=true (cono de 118°). diameter y depth aceptan número (mm) o expresión. La cara se guarda como "
             "referencia persistente, pero la posición de los puntos es fija en el espacio.", modifica=True)
def create_hole(sesion, face: str, diameter: Expr, points: list[list[float]] | None = None, depth: Expr | None = None,
                through_all: bool = False, hole_type: Literal["simple", "counterbore", "countersink"] = "simple",
                counterbore_diameter: Expr | None = None, counterbore_depth: Expr | None = None,
                countersink_diameter: Expr | None = None, countersink_angle: Expr = 90, drill_tip: bool = False,
                body: str | None = None):
    """
    face: la cara plana donde se empieza: selector (">Z"), id de find_faces ("Cuerpo1/F6"). Tiene que dar UNA cara.
    diameter: diámetro del agujero en mm (número o expresión).
    points: posiciones: lista de [u, v] (ejes x,y de un boceto sobre la cara) o [x, y, z] (mundo); vacío = centro de la cara.
    depth: profundidad en mm hasta el fondo plano; obligatoria salvo con through_all.
    through_all: true atraviesa todo el cuerpo (ignora depth).
    hole_type: "simple", "counterbore" (abocardado) o "countersink" (avellanado).
    counterbore_diameter: diámetro del abocardado en mm (mayor que diameter); solo con counterbore.
    counterbore_depth: profundidad del abocardado en mm; solo con counterbore.
    countersink_diameter: diámetro del avellanado en la superficie en mm; solo con countersink.
    countersink_angle: ángulo total del avellanado en grados; solo con countersink.
    drill_tip: true deja el fondo en cono de 118° como una broca; false, fondo plano.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    _numero_positivo(diameter, "diameter")
    if not through_all and depth is None:
        raise error("INVALID_ARGUMENTS", "Falta la profundidad: pasá depth (mm) o through_all=true.")
    if depth is not None:
        _numero_positivo(depth, "depth")
    extra = {}
    if hole_type == "counterbore":
        if counterbore_diameter is None or counterbore_depth is None:
            raise error("INVALID_ARGUMENTS", "El abocardado necesita counterbore_diameter y counterbore_depth.")
        extra = {"diam_abocardado": texto_expr(counterbore_diameter), "prof_abocardado": texto_expr(counterbore_depth)}
    elif hole_type == "countersink":
        if countersink_diameter is None:
            raise error("INVALID_ARGUMENTS", "El avellanado necesita countersink_diameter.")
        extra = {"diam_avellanado": texto_expr(countersink_diameter), "angulo_avellanado": texto_expr(countersink_angle)}
    (cuerpo, elem), = _unica_cara(sesion, face, body)
    plano = sl.plano_de_cara(elem)
    puntos = _puntos_agujero(plano, elem.centro, points)
    doc = sesion.doc
    op = OpAgujero(doc.nuevo_id(), nombre_nuevo(doc, "Agujero", OpAgujero), tipo=_TIPO_AGUJERO[hole_type],
                   diametro=texto_expr(diameter), extension="todo" if through_all else "distancia",
                   profundidad=texto_expr(depth if depth is not None else 10), punta="angulo" if drill_tip else "plana",
                   puntos_cara=[{"cara": sl.referencia(cuerpo, elem), "punto": [float(c) for c in p]} for p in puntos],
                   objetivos=[cuerpo.id], **extra)
    res = _agregar(sesion, op, combina=True)
    res.update(holes=len(puntos), face=sl.emitir_id(sesion, cuerpo, elem))
    return res


def _unica_cara(sesion, face, body):
    elegidos = sl.elegir(sesion, face, "cara", body)
    if len(elegidos) != 1:
        ids = ", ".join(sl.emitir_id(sesion, c, e) for c, e in elegidos[:6])
        raise error("AMBIGUOUS_REFERENCE", f"«{face}» eligió {len(elegidos)} caras ({ids}) y hace falta exactamente una.",
                    "Afiná el selector (p. ej. con and) o usá nearest:[x,y,z] o un id de find_faces.")
    return elegidos


# ---------------------------------------------------------------- desmoldeo
@herramienta("draft", "solido", "Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano "
             "que no se mueve), para poder sacar la pieza del molde. Las caras que se alejan del plano neutro "
             "se angostan (ángulo positivo). " + _ELEGIR.format(ej="#Z", que="faces", id="Cuerpo1/F2") +
             _PERSISTENTE + "angle acepta número (grados) o expresión.", modifica=True)
def draft(sesion, faces: Elementos, angle: Expr, neutral: str = "XY", reverse: bool = False, body: str | None = None):
    """
    faces: caras a inclinar: selector ("#Z" = las laterales de una caja), id de find_faces o lista.
    angle: ángulo de desmoldeo en grados (número o expresión), p. ej. 3.
    neutral: plano neutro: "XY", "XZ", "YZ" o una cara plana (selector o id, p. ej. "<Z"); define la dirección de extracción.
    reverse: true invierte la dirección de extracción.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    if isinstance(angle, (int, float)) and not 0 < abs(angle) < 90:
        raise error("INVALID_ARGUMENTS", f"angle tiene que estar entre 0 y 90 grados (recibió {angle}).")
    refs, elegidos = _refs(sesion, faces, "cara", body)
    if neutral.strip().upper() in ("XY", "XZ", "YZ"):
        plano = {"tipo": "plano", "id": neutral.strip().upper()}
    else:
        c, e = _unica_cara(sesion, neutral, body)[0]
        sl.plano_de_cara(e)
        plano = sl.referencia(c, e)
    doc = sesion.doc
    op = OpDesmoldeo(doc.nuevo_id(), nombre_nuevo(doc, "Desmoldeo", OpDesmoldeo), plano=plano, caras=refs,
                     angulo=texto_expr(angle), voltear=reverse)
    return _informe(_agregar(sesion, op), elegidos, "faces_used")
