# -*- coding: utf-8 -*-
"""
Herramientas del grupo "solido" que modifican un cuerpo usando caras o aristas: empalme (fillet), chaflán
(chamfer), vaciado (shell), agujero (create_hole), rosca (create_thread) y desmoldeo (draft); más las consultas de
roscas y ajustes normalizados (thread_info, fit_tolerance), que no tocan el documento.

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

from ..nucleo import geometria as geo
from ..timeline.operaciones import OpPlano
from ..timeline.ops_modificar import OpChaflan, OpDesmoldeo, OpEmpalme, OpVaciado
from ..timeline.ops_solido import OpAgujero, OpRosca
from . import selectores as sl
from .errores import ErrorAPI, error
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
_ROSCA_AGUJERO = {"simple": "simple", "clearance": "holgura", "cosmetic": "cosmetica", "modeled": "modelada",
                  "taper": "conico"}
_AJUSTE = {"close": "fino", "normal": "normal", "loose": "grueso"}
# familias de rosca: nombre en la API (inglés) → clave del núcleo (nucleo.solidos_crear.FAMILIAS_ROSCA)
_FAMILIA = {"iso_metric": "iso_metrica", "unified": "unificada", "trapezoidal": "trapezoidal", "acme": "acme",
            "bsp_parallel": "bsp_paralela", "bsp_taper": "bsp_conica", "npt": "npt"}
_FAMILIA_API = {v: k for k, v in _FAMILIA.items()}
Familia = Literal["iso_metric", "unified", "trapezoidal", "acme", "bsp_parallel", "bsp_taper", "npt"]
_VER_ROSCAS = "thread_info lista los tipos de rosca; thread_info(family=...) sus tamaños y designaciones."


def _sc():
    from ..nucleo import solidos_crear      # local: el núcleo se carga recién al usarlo
    return solidos_crear


def _tol():
    from ..nucleo import tolerancias
    return tolerancias


def _datos_rosca(thread):
    try:
        return _sc().datos_rosca(thread)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", f"Rosca desconocida: «{thread}».", _VER_ROSCAS,
                    "Ejemplos: 'M8', 'M8x1', '1/4-20 UNC', 'Tr20x4', '1/2-10 ACME', 'G1/2', 'R1/2', '1/2 NPT'.") from e


def _validar_clase(datos, clase, interna=None):
    """La clase existe para esa rosca (y es del lado correcto si se sabe); "" o "auto" valen siempre."""
    if clase in (None, "", "auto"):
        return
    tol = _tol()
    clases = tol.CLASES_POR_FAMILIA.get(datos["familia"], {})
    if clase not in clases:
        raise error("INVALID_ARGUMENTS", f"La clase «{clase}» no existe para {datos['designacion']}: hay "
                    f"{', '.join(clases) or 'ninguna (solo perfil básico)'}.", "thread_class='auto' elige la de "
                    "Fusion (6H/6g, 2B/2A) y '' modela el perfil básico.")
    try:
        if interna is not None:
            tol.resolver_clase(datos["familia"], datos["diametro"], datos["paso"], clase, interna)
        else:
            tol.limites_rosca(datos["familia"], datos["diametro"], datos["paso"], clase)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e), "thread_class='auto' usa el perfil básico cuando no hay datos.") from e


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


def _ref_hasta(sesion, to, body):
    """Referencia del «hasta» de un agujero: plano XY/XZ/YZ o de construcción, un cuerpo o UNA cara."""
    texto = str(to).strip()
    if texto.upper() in ("XY", "XZ", "YZ"):
        return {"tipo": "plano", "id": texto.upper()}
    for buscar, armar in ((sesion.paso, lambda o: {"tipo": "plano", "id": o.id} if isinstance(o, OpPlano) else None),
                          (sesion.cuerpo, lambda c: {"tipo": "cuerpo", "cuerpo": c.id})):
        try:
            ref = armar(buscar(texto))
        except ErrorAPI:
            continue
        if ref is not None:
            return ref
    (cuerpo, elem), = _unica_cara(sesion, texto, body)
    return sl.referencia(cuerpo, elem)


def _referencias_agujero(sesion, edges, distances, body):
    """(ref_aristas, [distancias]) de la posición por referencias: dos aristas rectas y dos distancias."""
    if not isinstance(edges, list) or len(edges) != 2 or not isinstance(distances, list) or len(distances) != 2:
        raise error("INVALID_ARGUMENTS", "La posición por referencias necesita reference_edges con DOS aristas y "
                    "reference_distances con DOS distancias.")
    refs = []
    for spec in edges:
        elegidos = sl.elegir(sesion, spec, "arista", body)
        if len(elegidos) != 1 or elegidos[0][1].geom != "LINE":
            raise error("INVALID_ARGUMENTS", f"«{spec}» tiene que dar UNA arista recta (dio {len(elegidos)}).",
                        "find_edges(selector='%LINE') lista las aristas rectas con su id.")
        refs.append(sl.referencia(*elegidos[0]))
    for d in distances:
        _numero_positivo(d, "reference_distances")
    return refs, [texto_expr(d) for d in distances]


@herramienta("create_hole", "solido", "Hace agujeros redondos desde una cara plana hacia adentro del material: "
             "simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth), pasantes "
             "(through_all) o hasta una cara, plano o cuerpo (to). La cara se elige con un selector (p. ej. '>Z'), un "
             "id de find_faces o 'Cuerpo1/F6'; tiene que ser UNA sola cara plana. points son las posiciones: [u, v] en "
             "mm en los ejes x,y de un boceto sobre esa cara (find_faces da el center_uv de la cara; create_sketch "
             "describe los ejes) o [x, y, z] del mundo (se proyecta sobre la cara); sin points, un agujero en el "
             "centro de la cara. Con reference_edges y reference_distances el agujero se ubica a esas distancias de "
             "dos aristas rectas (posición «Referencias» de Fusion, paramétrica). hole_tap: simple, clearance (agujero "
             "de paso ISO 273 para el tornillo thread='M8' con fit close/normal/loose), cosmetic (rosca solo "
             "informativa; diámetro = diameter o la broca de roscar), modeled (rosca real: thread, thread_class "
             "'6H', '2B', 'auto' o '' y print_clearance para imprimir en 3D) o taper (rosca cónica de tubería R/NPT: "
             "agujero cónico 1:16, rosca cosmética). El fondo es plano salvo drill_tip=true (cono de 118°). Medidas "
             "en número (mm) o expresión. La cara se guarda como referencia persistente; los points son fijos en el "
             "espacio.", modifica=True)
def create_hole(sesion, face: str, diameter: Expr | None = None, points: list[list[float]] | None = None,
                depth: Expr | None = None, through_all: bool = False,
                hole_type: Literal["simple", "counterbore", "countersink"] = "simple",
                counterbore_diameter: Expr | None = None, counterbore_depth: Expr | None = None,
                countersink_diameter: Expr | None = None, countersink_angle: Expr = 90, drill_tip: bool = False,
                body: str | None = None,
                hole_tap: Literal["simple", "clearance", "cosmetic", "modeled", "taper"] = "simple",
                thread: str | None = None, thread_class: str | None = "auto",
                fit: Literal["close", "normal", "loose"] = "normal", print_clearance: Expr = 0,
                left_hand: bool = False, to: str | None = None, to_offset: Expr = 0,
                reference_edges: list[str] | None = None, reference_distances: list[Expr] | None = None):
    """
    face: la cara plana donde se empieza: selector (">Z"), id de find_faces ("Cuerpo1/F6"). Tiene que dar UNA cara.
    diameter: diámetro del agujero en mm (número o expresión); obligatorio con hole_tap simple, opcional con cosmetic.
    points: posiciones: lista de [u, v] (ejes x,y de un boceto sobre la cara) o [x, y, z] (mundo); vacío = centro de la cara.
    depth: profundidad en mm hasta el fondo plano; obligatoria salvo con through_all o to.
    through_all: true atraviesa todo el cuerpo (ignora depth).
    hole_type: "simple", "counterbore" (abocardado) o "countersink" (avellanado).
    counterbore_diameter: diámetro del abocardado en mm (mayor que diameter); solo con counterbore.
    counterbore_depth: profundidad del abocardado en mm; solo con counterbore.
    countersink_diameter: diámetro del avellanado en la superficie en mm; solo con countersink.
    countersink_angle: ángulo total del avellanado en grados; solo con countersink.
    drill_tip: true deja el fondo en cono de 118° como una broca; false, fondo plano.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    hole_tap: "simple", "clearance" (paso libre ISO 273), "cosmetic", "modeled" (rosca real) o "taper" (tubería cónica).
    thread: rosca: "M8", "M8x1", "1/4-20 UNC", "Tr20x4", "G1/2" (taper: "R1/2" o "1/2 NPT"); con clearance, el tornillo ("M8").
    thread_class: clase de la rosca modelada: "6H"/"6G" (métrica), "2B"/"3B" (unificada), "auto" (6H o 2B si hay datos) o "" (perfil básico).
    fit: ajuste del agujero de paso (clearance): "close" (serie fina), "normal" (media) o "loose" (gruesa).
    print_clearance: holgura radial extra en mm de la rosca modelada (flancos y agujero), para imprimir en 3D.
    left_hand: true = rosca a izquierdas (solo modeled).
    to: extensión «hasta»: "XY"/"XZ"/"YZ" o un plano de construcción, un cuerpo (id o nombre) o UNA cara (selector o id).
    to_offset: desfase en mm sobre el «hasta» (positivo = más hondo).
    reference_edges: posición por referencias: DOS aristas rectas (selector o id de find_edges), no paralelas.
    reference_distances: las DOS distancias en mm del centro del agujero a cada arista de reference_edges.
    """
    rosca = _ROSCA_AGUJERO[hole_tap]
    if diameter is not None:
        _numero_positivo(diameter, "diameter")
    elif hole_tap == "simple":
        raise error("INVALID_ARGUMENTS", "Falta diameter (con hole_tap='simple' es obligatorio).")
    if not through_all and depth is None and to is None:
        raise error("INVALID_ARGUMENTS", "Falta la profundidad: pasá depth (mm), through_all=true o to (una cara).")
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
    designacion, clase = "M6", ""
    if hole_tap != "simple":
        if not thread:
            raise error("INVALID_ARGUMENTS", f"Con hole_tap='{hole_tap}' falta thread (p. ej. 'M8').", _VER_ROSCAS)
        if hole_tap == "clearance":
            try:
                _sc().diametro_paso_libre(thread, _AJUSTE[fit])
            except geo.ErrorGeometria as e:
                raise error("INVALID_ARGUMENTS", str(e)) from e
            designacion = thread.strip()
        else:
            datos = _datos_rosca(thread)
            designacion = datos["designacion"]
            if (hole_tap == "taper") != datos["conica"]:
                raise error("INVALID_ARGUMENTS", f"{designacion} es una rosca {'cónica' if datos['conica'] else 'paralela'}: "
                            f"{'usá hole_tap=taper' if datos['conica'] else 'taper es para R/Rc y NPT'}.", _VER_ROSCAS)
            if hole_tap == "modeled":
                _validar_clase(datos, thread_class, interna=True)
                clase = thread_class or ""
            elif hole_tap == "cosmetic" and diameter is None:
                diameter = datos.get("broca") or round(datos["diametro_menor"], 3)
    (cuerpo, elem), = _unica_cara(sesion, face, body)
    plano = sl.plano_de_cara(elem)
    ubicacion = {}
    if reference_edges is not None or reference_distances is not None:
        if points:
            raise error("INVALID_ARGUMENTS", "Usá points o reference_edges/reference_distances, no los dos.")
        aristas, distancias = _referencias_agujero(sesion, reference_edges, reference_distances, body)
        ubicacion = {"ref_cara": sl.referencia(cuerpo, elem), "ref_aristas": aristas,
                     "ref_distancia1": distancias[0], "ref_distancia2": distancias[1]}
        cantidad = 1
    else:
        puntos = _puntos_agujero(plano, elem.centro, points)
        ubicacion = {"puntos_cara": [{"cara": sl.referencia(cuerpo, elem), "punto": [float(c) for c in p]}
                                     for p in puntos]}
        cantidad = len(puntos)
    extension = "todo" if through_all else ("hasta" if to is not None else "distancia")
    if extension == "hasta":
        extra.update(hasta=_ref_hasta(sesion, to, body), desfase_hasta=texto_expr(to_offset))
    doc = sesion.doc
    op = OpAgujero(doc.nuevo_id(), nombre_nuevo(doc, "Agujero", OpAgujero), tipo=_TIPO_AGUJERO[hole_type],
                   diametro=texto_expr(diameter if diameter is not None else 6), extension=extension,
                   profundidad=texto_expr(depth if depth is not None else 10), punta="angulo" if drill_tip else "plana",
                   objetivos=[cuerpo.id], rosca=rosca, designacion=designacion, clase_rosca=clase,
                   ajuste=_AJUSTE[fit], holgura_3d=texto_expr(print_clearance),
                   mano="izquierda" if left_hand else "derecha", **ubicacion, **extra)
    res = _agregar(sesion, op, combina=True)
    res.update(holes=cantidad, face=sl.emitir_id(sesion, cuerpo, elem))
    if hole_tap != "simple":
        res["thread"] = designacion
    return res


def _unica_cara(sesion, face, body):
    elegidos = sl.elegir(sesion, face, "cara", body)
    if len(elegidos) != 1:
        ids = ", ".join(sl.emitir_id(sesion, c, e) for c, e in elegidos[:6])
        raise error("AMBIGUOUS_REFERENCE", f"«{face}» eligió {len(elegidos)} caras ({ids}) y hace falta exactamente una.",
                    "Afiná el selector (p. ej. con and) o usá nearest:[x,y,z] o un id de find_faces.")
    return elegidos


# ---------------------------------------------------------------- rosca y tolerancias
@herramienta("create_thread", "solido", "Rosca sobre caras cilíndricas (ejes o agujeros: se detecta solo), como el "
             "comando Rosca de Fusion. " + _ELEGIR.format(ej="%CYLINDER", que="faces", id="Cuerpo1/F3") +
             _PERSISTENTE + "thread: designación ('M10', 'M10x1.25', '1/4-20 UNC', 'Tr20x4', '1/2-10 ACME', 'G1/2'); "
             "vacío = el tamaño de family más cercano al diámetro de la cara. thread_class: '6g'/'6h'/'6H'/'6G' "
             "(métrica, ISO 965-1), '2A'/'3A'/'2B'/'3B' (unificada, ASME B1.1), 'auto' (la de Fusion: 6H/6g o "
             "2B/2A, si hay datos del tamaño) o '' (perfil básico): corre los flancos al centro de la tolerancia. "
             "print_clearance agrega holgura radial para imprimir en 3D. modeled=false = cosmética (no cambia la "
             "geometría; las roscas cónicas R/NPT siempre quedan cosméticas sobre una cara cilíndrica). length "
             "vacío = largo completo; offset corre el inicio. Perfil según el tipo: 60° (M, UN), 55° (G), 30° (Tr) "
             "o 29° (ACME).", modifica=True)
def create_thread(sesion, faces: Elementos, thread: str | None = None, family: Familia = "iso_metric",
                  thread_class: str | None = "auto", modeled: bool = True, length: Expr | None = None,
                  offset: Expr = 0, left_hand: bool = False, reverse: bool = False, print_clearance: Expr = 0,
                  body: str | None = None):
    """
    faces: caras cilíndricas a roscar: selector ("%CYLINDER"), id de find_faces ("Cuerpo1/F3") o lista.
    thread: designación de la rosca ("M10", "M10x1.25", "1/4-20 UNC", "Tr20x4", "G1/2"…); vacío = automática según la cara.
    family: tipo de rosca para el tamaño automático: iso_metric, unified, trapezoidal, acme, bsp_parallel, bsp_taper o npt.
    thread_class: clase de tolerancia: "6g", "6H", "2A", "2B"…, "auto" (la de Fusion) o "" (perfil básico).
    modeled: true corta el filete real; false = rosca cosmética (la geometría no cambia).
    length: largo roscado en mm (número o expresión); vacío = toda la cara.
    offset: distancia en mm desde el extremo de la cara hasta donde empieza la rosca (con length).
    left_hand: true = rosca a izquierdas.
    reverse: true mide length y offset desde el otro extremo de la cara.
    print_clearance: holgura radial extra en mm (flancos), para piezas impresas en 3D.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    if length is not None:
        _numero_positivo(length, "length")
    refs, elegidos = _refs(sesion, faces, "cara", body)
    malas = [sl.emitir_id(sesion, c, e) for c, e in elegidos if e.geom != "CYLINDER"]
    if malas:
        raise error("UNSUPPORTED_ELEMENT", f"La rosca va sobre caras cilíndricas: {', '.join(malas[:6])} no lo son.",
                    "find_faces(selector='%CYLINDER') lista las caras cilíndricas.")
    familia = _FAMILIA[family]
    designacion = ""
    if thread:
        datos = _datos_rosca(thread)
        designacion, familia = datos["designacion"], datos["familia"]
        _validar_clase(datos, thread_class)
    elif thread_class not in (None, "", "auto") and thread_class not in _tol().CLASES_POR_FAMILIA.get(familia, {}):
        raise error("INVALID_ARGUMENTS", f"La clase «{thread_class}» no existe para el tipo {family}.",
                    "thread_class='auto' elige la de Fusion; '' modela el perfil básico.")
    doc = sesion.doc
    op = OpRosca(doc.nuevo_id(), nombre_nuevo(doc, "Rosca", OpRosca), caras=refs, designacion=designacion,
                 familia=familia, clase_rosca=thread_class or "", modelada=modeled, largo_completo=length is None,
                 longitud=texto_expr(length if length is not None else 10), desfase=texto_expr(offset),
                 mano="izquierda" if left_hand else "derecha", invertir=reverse,
                 holgura_3d=texto_expr(print_clearance))
    res = _agregar(sesion, op, combina=modeled)
    res["threads"] = [{"body": sesion.nombre_cuerpo(sesion.cuerpo(r["cuerpo"])), "designation": r["designacion"],
                       "class": r["clase"] or None, "internal": r["interna"], "modeled": r["modelada"]}
                      for r in getattr(op, "roscas", [])]
    return _informe(res, elegidos, "faces_used")


def _limites_api(lim):
    return {"class": lim["clase"], "internal": lim["interna"], "standard": lim["norma"],
            "major_diameter": lim["diametro_mayor"], "pitch_diameter": lim["diametro_flancos"],
            "minor_diameter": lim["diametro_menor"], "fundamental_deviation": lim["desviacion_fundamental"]}


@herramienta("thread_info", "inspeccion", "Datos de roscas normalizadas (no cambia el documento). Sin argumentos: los tipos "
             "(familias) con su norma, ángulo de perfil y clases. Con family: sus tamaños y designaciones. Con thread: "
             "diámetro mayor, paso, diámetros de flancos y menor básicos, broca para roscar, agujero de paso ISO 273 "
             "(métricas) y, con thread_class, los diámetros límite de la clase (ISO 965-1 o ASME B1.1; 'auto' da los "
             "de las dos clases por defecto). Todo en mm.")
def thread_info(sesion, thread: str | None = None, family: Familia | None = None, thread_class: str | None = None):
    """
    thread: designación ("M10", "M10x1.25", "1/4-20 UNC", "Tr20x4", "1/2-10 ACME", "G1/2", "R1/2", "1/2 NPT").
    family: tipo de rosca cuyos tamaños listar: iso_metric, unified, trapezoidal, acme, bsp_parallel, bsp_taper o npt.
    thread_class: clase para los diámetros límite: "6g", "6H", "2A", "2B"…, o "auto" (las dos por defecto).
    """
    sc, tol = _sc(), _tol()
    if thread:
        d = _datos_rosca(thread)
        res = {"designation": d["designacion"], "family": _FAMILIA_API[d["familia"]],
               "standard": sc.FAMILIAS_ROSCA[d["familia"]]["norma"], "profile_angle": d["angulo"],
               "taper": d["conica"], "major_diameter": round(d["diametro"], 4), "pitch": round(d["paso"], 4),
               "pitch_diameter": round(d["diametro_flancos"], 4), "minor_diameter": round(d["diametro_menor"], 4),
               "tap_drill": d["broca"], "classes": list(tol.CLASES_POR_FAMILIA.get(d["familia"], {}))}
        if d["conica"]:
            res["note"] = "Diámetros en el plano de calibre; conicidad 1:16 en el diámetro."
        if d["familia"] == "iso_metrica":
            try:
                res["clearance_holes"] = {k: sc.diametro_paso_libre(d["tamano"], v) for k, v in _AJUSTE.items()}
            except geo.ErrorGeometria:
                pass
        if thread_class:
            if thread_class == "auto":
                clases = tol.CLASE_AUTOMATICA.get(d["familia"], ())
            else:
                _validar_clase(d, thread_class)
                clases = (thread_class,)
            res["limits"] = []
            for c in clases:
                try:
                    res["limits"].append(_limites_api(tol.limites_rosca(d["familia"], d["diametro"], d["paso"], c)))
                except geo.ErrorGeometria as e:
                    sesion.avisar(str(e))
        return res
    if family:
        fam = _FAMILIA[family]
        return {"family": family, "standard": sc.FAMILIAS_ROSCA[fam]["norma"],
                "sizes": [{"size": t, "designations": sc.designaciones_rosca(fam, t)} for t in sc.tamanos_rosca(fam)]}
    return {"families": [{"family": _FAMILIA_API[k], "name": f["nombre"], "standard": f["norma"],
                          "profile_angle": f["angulo"], "taper": f["conica"],
                          "classes": list(tol.CLASES_POR_FAMILIA.get(k, {})),
                          "sizes": len(sc.tamanos_rosca(k))} for k, f in sc.FAMILIAS_ROSCA.items()]}


@herramienta("fit_tolerance", "inspeccion", "Ajuste ISO 286 entre un agujero y un eje (no cambia el documento): "
             "desviaciones y medidas límite de cada uno, juego máximo y mínimo (negativo = apriete) y tipo de ajuste "
             "(clearance, transition o interference). Hay grados IT5 a IT11 hasta 500 mm; agujeros D, E, F, G, H y "
             "ejes d, e, f, g, h, j6, k, n, p, s. Ej.: nominal=25, hole='H7', shaft='g6'. Todo en mm.")
def fit_tolerance(sesion, nominal: float, hole: str = "H7", shaft: str = "g6"):
    """
    nominal: medida nominal en mm (más de 0 y hasta 500).
    hole: clase del agujero, letra mayúscula y grado: "H7", "H8", "H11", "G7", "F8"…
    shaft: clase del eje, letra minúscula y grado: "g6", "h6", "h7", "f7", "k6", "n6", "p6", "s6", "j6"…
    """
    try:
        a = _tol().ajuste(nominal, hole, shaft)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e), "Ejemplos: hole='H7' con shaft='g6' (juego), 'k6' (transición) o "
                    "'p6' (apriete).") from e

    def pieza(x):
        return {"class": x["clase"], "upper_deviation": x["superior"], "lower_deviation": x["inferior"],
                "max": x["maximo"], "min": x["minimo"], "tolerance": x["tolerancia"]}
    tipos = {"juego": "clearance", "transicion": "transition", "apriete": "interference"}
    return {"nominal": a["nominal"], "standard": a["norma"], "hole": pieza(a["agujero"]), "shaft": pieza(a["eje"]),
            "max_clearance": a["juego_maximo"], "min_clearance": a["juego_minimo"],
            "max_interference": a["apriete_maximo"], "min_interference": a["apriete_minimo"],
            "fit_type": tipos[a["tipo"]]}


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
