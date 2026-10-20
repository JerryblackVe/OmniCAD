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
from ..timeline.ops_modificar import (OpChaflan, OpDesfaseAristas, OpDesfaseCara, OpDesmoldeo, OpEmpalme, OpQuitarEmpalmes,
                                      OpVaciado)
from ..timeline.ops_solido import OpAgujero, OpRosca
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_boceto import boceto_activo, boceto_resuelto, nombre_nuevo, referencia_plano, texto_expr
from .herramientas_solido import _agregar, _numero_positivo
from .registro import Expr, herramienta

Elementos = str | list[str]

_ELEGIR = ("Se elige con un selector estilo CadQuery (p. ej. '{ej}'; get_guide topic=selectores), con ids de "
           "find_{que} (p. ej. '{id}', válidos hasta el próximo cambio del documento) o con una lista de ambos. ")
_MEDIDA_MINIMA = 1e-4           # mm: un empalme o chaflán más chico no lo distingue el kernel (T-07 de la prueba de tortura)
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
_REDONDEOS = {"both": "ambos", "rounds": "redondeos", "fillets": "empalmes"}


@herramienta("fillet", "solido", "Redondea aristas: empalme de radio constante (por defecto), de longitud de cuerda "
             "(radius_type=chord) o de radio variable entre el inicio y el final de la arista (radius_type=variable, "
             "end_radius). Con faces_a hace un EMPALME DE REGLAS: todas las aristas de esas caras, o solo las que están "
             "entre faces_a y faces_b; rounds elige redondeos (aristas convexas), empalmes (cóncavas) o ambos. "
             + _ELEGIR.format(ej="|Z", que="edges", id="Cuerpo1/E7") + _PERSISTENTE + "Con tangent_chain (por defecto) "
             "el empalme sigue las aristas tangentes encadenadas. Si el radio no cabe, falla con OPERATION_FAILED y el "
             "documento queda igual. radius acepta número (mm) o expresión.", modifica=True)
def fillet(sesion, edges: Elementos | None = None, radius: Expr | None = None, body: str | None = None,
           radius_type: Literal["constant", "chord", "variable"] = "constant", end_radius: Expr | None = None,
           chord_length: Expr | None = None, tangent_chain: bool = True, faces_a: Elementos | None = None,
           faces_b: Elementos | None = None, rounds: Literal["both", "rounds", "fillets"] = "both"):
    """
    edges: aristas a redondear: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores. No se usa con faces_a.
    radius: radio en mm (número o expresión con parámetros, p. ej. "espesor / 2"); con radius_type=variable es el radio inicial; en el empalme de reglas, el radio de las reglas.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    radius_type: "constant", "chord" (se da chord_length en lugar del radio) o "variable" (de radius a end_radius a lo largo de la arista).
    end_radius: radio final en mm (número o expresión); obligatorio con radius_type=variable.
    chord_length: longitud de cuerda en mm (número o expresión); obligatoria con radius_type=chord.
    tangent_chain: true (por defecto) suma las aristas tangentes encadenadas; false empalma solo las elegidas.
    faces_a: empalme de reglas: caras (selector, ids o lista) cuyas aristas se redondean; reemplaza a edges.
    faces_b: empalme de reglas «entre»: segundo grupo de caras; solo se redondean las aristas entre faces_a y faces_b; vacío = todas las aristas de faces_a.
    rounds: empalme de reglas: "both" (por defecto), "rounds" (solo aristas convexas) o "fillets" (solo cóncavas).
    """
    if radius is None and (faces_a is not None or radius_type != "chord"):
        raise error("INVALID_ARGUMENTS", "Falta radius (solo radius_type=chord lo reemplaza con chord_length).")
    if faces_a is not None:
        if edges:
            raise error("INVALID_ARGUMENTS", "Pasá edges o faces_a (empalme de reglas), no los dos.")
        _numero_positivo(radius, "radius", _MEDIDA_MINIMA)
        caras_a, elegidos = _refs(sesion, faces_a, "cara", body)
        caras_b = _refs(sesion, faces_b, "cara", body)[0] if faces_b else []
        doc = sesion.doc
        op = OpEmpalme(doc.nuevo_id(), nombre_nuevo(doc, "Empalme", OpEmpalme), tipo="reglas", caras_a=caras_a,
                       caras_b=caras_b, regla="entre" if caras_b else "todas", redondeos=_REDONDEOS[rounds],
                       radio=texto_expr(radius))
        return _informe(_agregar(sesion, op), elegidos, "faces_used")
    if not edges:
        raise error("INVALID_ARGUMENTS", "Elegí qué redondear: edges (o faces_a para un empalme de reglas).")
    if radius_type == "chord":
        if chord_length is None:
            raise error("INVALID_ARGUMENTS", "radius_type=chord necesita chord_length.")
        _numero_positivo(chord_length, "chord_length", _MEDIDA_MINIMA)
    else:
        _numero_positivo(radius, "radius", _MEDIDA_MINIMA)
    if radius_type == "variable":
        if end_radius is None:
            raise error("INVALID_ARGUMENTS", "radius_type=variable necesita end_radius.")
        _numero_positivo(end_radius, "end_radius", _MEDIDA_MINIMA)
    refs, elegidos = _refs(sesion, edges, "arista", body)
    doc = sesion.doc
    extra = {}
    if chord_length is not None:
        extra["cuerda"] = texto_expr(chord_length)
    if end_radius is not None:
        extra["radio_fin"] = texto_expr(end_radius)
    op = OpEmpalme(doc.nuevo_id(), nombre_nuevo(doc, "Empalme", OpEmpalme), aristas=refs,
                   tipo_radio={"constant": "constante", "chord": "cuerda", "variable": "variable"}[radius_type],
                   radio=texto_expr(1 if radius is None else radius), cadena_tangente=bool(tangent_chain), **extra)
    return _informe(_agregar(sesion, op), elegidos, "edges_used")


@herramienta("chamfer", "solido", "Achaflana aristas: distancia igual en las dos caras (por defecto), dos distancias "
             "(type=two_distances, distance2) o distancia y ángulo (type=distance_angle, angle); flip pasa la primera "
             "distancia a la otra cara. " + _ELEGIR.format(ej="|Z", que="edges", id="Cuerpo1/E7") + _PERSISTENTE +
             "Con tangent_chain (por defecto) sigue las aristas tangentes encadenadas. distance, distance2 y angle "
             "aceptan número (mm o grados) o expresión.", modifica=True)
def chamfer(sesion, edges: Elementos, distance: Expr, body: str | None = None,
            type: Literal["equal", "two_distances", "distance_angle"] = "equal", distance2: Expr | None = None,
            angle: Expr | None = None, flip: bool = False, tangent_chain: bool = True):
    """
    edges: aristas a achaflanar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
    distance: distancia del chaflán en mm sobre cada cara (número o expresión con parámetros); con two_distances o distance_angle, la primera distancia.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    type: "equal" (distancia igual), "two_distances" (distance y distance2) o "distance_angle" (distance y angle).
    distance2: segunda distancia en mm; obligatoria con type=two_distances.
    angle: ángulo en grados (entre 0 y 90, excluidos); obligatorio con type=distance_angle.
    flip: true pasa la primera distancia a la otra cara (no hace nada con type=equal).
    tangent_chain: true (por defecto) suma las aristas tangentes encadenadas; false achaflana solo las elegidas.
    """
    _numero_positivo(distance, "distance", _MEDIDA_MINIMA)
    extra = {}
    if type == "two_distances":
        if distance2 is None:
            raise error("INVALID_ARGUMENTS", "type=two_distances necesita distance2.")
        _numero_positivo(distance2, "distance2", _MEDIDA_MINIMA)
        extra["distancia2"] = texto_expr(distance2)
    elif type == "distance_angle":
        if angle is None:
            raise error("INVALID_ARGUMENTS", "type=distance_angle necesita angle.")
        if isinstance(angle, (int, float)) and not 0 < angle < 90:
            raise error("INVALID_ARGUMENTS", f"angle tiene que estar entre 0 y 90 grados (recibió {angle}).")
        extra["angulo"] = texto_expr(angle)
    refs, elegidos = _refs(sesion, edges, "arista", body)
    doc = sesion.doc
    op = OpChaflan(doc.nuevo_id(), nombre_nuevo(doc, "Chaflán", OpChaflan), aristas=refs,
                   tipo={"equal": "distancia_igual", "two_distances": "dos_distancias",
                         "distance_angle": "distancia_angulo"}[type],
                   distancia=texto_expr(distance), voltear=bool(flip), cadena_tangente=bool(tangent_chain), **extra)
    return _informe(_agregar(sesion, op), elegidos, "edges_used")


# ---------------------------------------------------------------- vaciado
_DIRECCION_VACIADO = {"inside": "interior", "outside": "exterior", "both": "ambos"}


@herramienta("shell", "solido", "Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan "
             "(quedan abiertas). " + _ELEGIR.format(ej=">Z", que="faces", id="Cuerpo1/F6") + _PERSISTENTE +
             "direction: inside (las paredes quedan hacia adentro: el cuerpo no crece), outside (hacia afuera) o both. "
             "Con faces=[] (lista vacía) el cuerpo queda hueco y cerrado. Si el espesor es igual o mayor que el radio de un "
             "empalme de las caras vaciadas, el kernel no puede (radio interior cero o negativo): OPERATION_FAILED. "
             "En algunas caras B-spline el vaciado hacia afuera no se puede calcular: el error indica cómo armar "
             "dos solevaciones y restarlas. thickness acepta número (mm) o expresión.",
             modifica=True)
def shell(sesion, body: str, faces: Elementos, thickness: Expr, direction: Literal["inside", "outside", "both"] = "inside",
          tangent_chain: bool = True, outside_thickness: Expr | None = None,
          corners: Literal["sharp", "rounded"] = "sharp"):
    """
    body: id o nombre del cuerpo a vaciar.
    faces: caras a quitar: selector (">Z" = la tapa), id de find_faces ("Cuerpo1/F6") o lista; [] = hueco cerrado.
    thickness: espesor de pared en mm (número o expresión con parámetros); es el interior, y también el exterior si no se da outside_thickness.
    direction: "inside", "outside" o "both".
    tangent_chain: true (por defecto) quita también las caras tangentes encadenadas a las elegidas.
    outside_thickness: espesor exterior en mm distinto del interior (con direction=both u outside); vacío = el mismo que thickness.
    corners: "sharp" (desfase afilado, por defecto) o "rounded" (desfase redondeado en las esquinas).
    """
    _numero_positivo(thickness, "thickness")
    if outside_thickness is not None:
        _numero_positivo(outside_thickness, "outside_thickness")
    cuerpo = sl.cuerpo_objetivo(sesion, body)
    refs, elegidos = _refs(sesion, faces, "cara", cuerpo.id, permitir_vacio=True)
    ajenas = {c.id for c, _ in elegidos} - {cuerpo.id}
    if ajenas:
        raise error("INVALID_ARGUMENTS", f"Las caras elegidas son de otro cuerpo ({', '.join(sorted(ajenas))}), no de "
                    f"«{sesion.nombre_cuerpo(cuerpo)}».")
    espesor = texto_expr(thickness)
    doc = sesion.doc
    op = OpVaciado(doc.nuevo_id(), nombre_nuevo(doc, "Vaciado", OpVaciado), caras=refs, cuerpos=[] if refs else [cuerpo.id],
                   espesor_interior=espesor,
                   espesor_exterior=espesor if outside_thickness is None else texto_expr(outside_thickness),
                   direccion=_DIRECCION_VACIADO[direction], tangente=bool(tangent_chain),
                   tipo="afilado" if corners == "sharp" else "redondeado")
    return _informe(_agregar(sesion, op), elegidos, "faces_removed")


@herramienta("remove_fillets", "solido",
             "Quita de una vez todos los redondeos (empalmes) de un cuerpo con radio hasta max_radius "
             "(«Remove Fillets» de Plasticity: defeaturing + unión de la topología que queda). No toca los "
             "agujeros taladrados. Deja un paso editable en el timeline; si no hay empalmes con ese "
             "filtro, falla con OPERATION_FAILED y el documento queda igual.", modifica=True)
def remove_fillets(sesion, body: str | list[str], max_radius: Expr):
    """
    body: id o nombre del cuerpo (o lista de cuerpos) al que sacarle los empalmes.
    max_radius: radio máximo en mm (número o expresión): se quitan los redondeos con radio hasta ese valor.
    """
    from ..nucleo.solidos_modificar import caras_de_empalme
    _numero_positivo(max_radius, "max_radius")
    pedidos = [body] if isinstance(body, str) else list(body)
    if not pedidos:
        raise error("INVALID_ARGUMENTS", "Elegí al menos un cuerpo en body.")
    cuerpos = list(dict.fromkeys(sl.cuerpo_objetivo(sesion, b).id for b in pedidos))
    doc = sesion.doc
    op = OpQuitarEmpalmes(doc.nuevo_id(), nombre_nuevo(doc, "Quitar empalmes", OpQuitarEmpalmes),
                          cuerpos=cuerpos, radio_max=texto_expr(max_radius))
    try:
        # El conteo del informe se mide con el MISMO contexto con el que se calculará el paso.
        from ..timeline.operaciones import Contexto
        radio = Contexto(doc.parametros.valores()).evaluar(op.p["radio_max"])
        encontrados = sum(len(caras_de_empalme(sesion.cuerpo(c).forma, radio)) for c in cuerpos)
    except Exception:                       # noqa: BLE001 — expresión con parámetros a medias: sin conteo previo
        encontrados = 0
    res = _agregar(sesion, op)
    res["fillets_removed"] = encontrados
    res["bodies_affected"] = cuerpos
    return res


@herramienta("offset_faces", "solido",
             "Mueve caras de un cuerpo a lo largo de su normal (la mitad «cara» del comando Desfase; «Cara de desfase» "
             "de Fusion): distance > 0 agrega material, < 0 lo quita. Con tangent=true la cadena de caras tangentes se "
             "mueve junta. " + _ELEGIR.format(ej=">Z", que="faces", id="Cuerpo1/F6") + _PERSISTENTE +
             "Si el desfase no se puede calcular, falla con OPERATION_FAILED y el documento queda igual.",
             modifica=True)
def offset_faces(sesion, faces: Elementos, distance: Expr, tangent: bool = True, body: str | None = None):
    """
    faces: caras a mover: selector (">Z"), id de find_faces ("Cuerpo1/F6") o lista de ids y selectores.
    distance: desplazamiento en mm sobre la normal exterior (número o expresión); negativo = hacia adentro.
    tangent: true mueve también las caras tangentes encadenadas.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    """
    refs, elegidos = _refs(sesion, faces, "cara", body)
    doc = sesion.doc
    op = OpDesfaseCara(doc.nuevo_id(), nombre_nuevo(doc, "Desfase de cara", OpDesfaseCara), caras=refs,
                       distancia=texto_expr(distance), tangente=bool(tangent))
    return _informe(_agregar(sesion, op), elegidos, "faces_moved")


def _es_plano_de_construccion(sesion, texto):
    """True si `texto` es el id o el nombre de un plano de construcción (ni selector ni id de find_faces)."""
    try:
        referencia_plano(sesion, texto)
    except ErrorAPI:
        return False
    return True


@herramienta("offset_edges", "solido",
             "Desfase de aristas o de curvas de un boceto («Offset Edge» y «Offset Face Loop» de Plasticity): crea un "
             "boceto NUEVO con curvas a `distance` de las elegidas, sin tocar ni cortar el cuerpo. Las aristas (edges: "
             "selector, ids de find_edges o lista) y las curvas de boceto (curves + sketch) se unen en cadenas y se "
             "desfasan sobre un plano: `plane` (\"XY\", \"XZ\", \"YZ\" o UNA cara plana: selector o id de find_faces) "
             "o, si no se da, el plano que las contiene a todas (una recta sola o aristas en línea no lo definen: "
             "falla y pide plane). distance > 0 va a la derecha del recorrido de la cadena (el sentido de la primera "
             "arista elegida) y las cadenas cerradas crecen; negativa, al otro lado; symmetric hace los dos lados. "
             "Las curvas quedan como geometría fija del boceto nuevo (sirve para extruir). " + _PERSISTENTE,
             modifica=True)
def offset_edges(sesion, distance: Expr, edges: Elementos | None = None, curves: list[int] | None = None,
                 sketch: str | None = None, plane: str | None = None, symmetric: bool = False,
                 corners: Literal["round", "sharp"] = "round", body: str | None = None):
    """
    distance: separación en mm (número o expresión con parámetros); negativa = al lado contrario.
    edges: aristas a desfasar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista; vacío = ninguna.
    curves: ids de curvas de un boceto (get_sketch) a desfasar; piden `sketch`.
    sketch: id o nombre del boceto de `curves`; vacío = el último boceto del timeline.
    plane: plano del desfase: "XY", "XZ", "YZ", el id o nombre de un plano de construcción o una cara plana (selector o id); vacío = el que contiene a todas.
    symmetric: true hace el desfase a los dos lados (distance se toma en valor absoluto).
    corners: round (arcos en las esquinas) o sharp (las esquinas se prolongan hasta cortarse).
    body: cuerpo donde se evalúan los selectores de edges y de plane; vacío = el único cuerpo.
    """
    referencias = []
    if edges:
        referencias += _refs(sesion, edges, "arista", body)[0]
    if curves:
        op_b, br_b = boceto_activo(sesion, sketch)
        faltan = [c for c in curves if c not in br_b.boceto.curvas]
        if faltan:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{op_b.nombre}» no tiene las curvas {faltan} (get_sketch las lista).")
        referencias += [{"tipo": "curva_boceto", "boceto": op_b.id, "curva": int(c)} for c in dict.fromkeys(curves)]
    if not referencias:
        raise error("INVALID_ARGUMENTS", "Elegí qué desfasar: edges o curves.")
    ref_plano = None
    if plane is not None and str(plane).strip():
        texto = str(plane).strip()
        if texto.upper() in ("XY", "XZ", "YZ"):
            ref_plano = {"tipo": "plano", "id": texto.upper()}
        elif _es_plano_de_construccion(sesion, texto):
            ref_plano = {"tipo": "plano", "id": referencia_plano(sesion, texto)}
        else:
            caras = _refs(sesion, texto, "cara", body)[0]
            if len(caras) != 1:
                raise error("INVALID_ARGUMENTS", f"plane «{texto}» elige {len(caras)} caras: tiene que ser una sola cara "
                            "plana (o XY, XZ, YZ).")
            ref_plano = caras[0]
    doc = sesion.doc
    op = OpDesfaseAristas(doc.nuevo_id(), nombre_nuevo(doc, "Desfase de aristas", OpDesfaseAristas),
                          referencias=referencias, plano=ref_plano, distancia=texto_expr(distance),
                          simetrico=bool(symmetric), esquinas="redondas" if corners == "round" else "vivas")
    doc.agregar(op)
    br = boceto_resuelto(sesion, op)
    return {"sketch": {"id": op.id, "name": op.nombre, "type": op.TIPO}, "profiles": None if br is None else len(br.perfiles),
            "curves": None if br is None else len(br.boceto.curvas)}


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


@herramienta("create_hole", "solido", "Hace agujeros redondos hacia adentro del material: simples, abocardados "
             "(counterbore) o avellanados (countersink), ciegos (depth), pasantes (through_all) o hasta una cara, "
             "plano o cuerpo (to). Tres formas de ubicarlos: (1) ASOCIATIVA, en puntos de un boceto: sketch + "
             "sketch_points (ids de get_sketch, p. ej. el centro de un círculo); el agujero sigue al punto si el boceto "
             "o sus cotas cambian, perpendicular al plano del boceto y hacia el lado del material (flip lo invierte); "
             "face es opcional (elige el cuerpo). (2) FIJA, sobre una cara plana: face con un selector (p. ej. '>Z') o "
             "un id de find_faces ('Cuerpo1/F6'; UNA cara plana) y points: [u, v] en mm en los ejes x,y de un boceto "
             "sobre esa cara (find_faces da el center_uv) o [x, y, z] del mundo (se proyecta sobre la cara); sin "
             "points, el centro de la cara. Esos puntos quedan fijos en el espacio aunque la cara se mueva. (3) "
             "REFERENCIAS: face + reference_edges y reference_distances ubican el agujero a esas distancias de dos "
             "aristas rectas (paramétrico). hole_tap: simple, clearance (agujero de paso ISO 273 para el tornillo "
             "thread='M8' con fit close/normal/loose), cosmetic (rosca solo informativa; diámetro = diameter o la broca "
             "de roscar), modeled (rosca real: thread, thread_class '6H', '2B', 'auto' o '' y print_clearance para "
             "imprimir en 3D) o taper (rosca cónica de tubería R/NPT: agujero cónico 1:16, rosca cosmética). El fondo "
             "es plano salvo drill_tip=true (cono de tip_angle, 118° por defecto). Una cuarta forma, ASOCIATIVA: "
             "positions con vértices [x, y, z] del modelo o puntos de construcción (el agujero entra hacia −Z; flip lo "
             "invierte). flip vale en todas las formas y bodies agujerea varios cuerpos a la vez. Medidas en número "
             "(mm) o expresión.", modifica=True)
def create_hole(sesion, diameter: Expr | None = None, face: str | None = None, points: list[list[float]] | None = None,
                depth: Expr | None = None, through_all: bool = False,
                hole_type: Literal["simple", "counterbore", "countersink"] = "simple",
                counterbore_diameter: Expr | None = None, counterbore_depth: Expr | None = None,
                countersink_diameter: Expr | None = None, countersink_angle: Expr = 90, drill_tip: bool = False,
                body: str | None = None, sketch: str | None = None, sketch_points: list[int] | None = None,
                flip: bool = False,
                hole_tap: Literal["simple", "clearance", "cosmetic", "modeled", "taper"] = "simple",
                thread: str | None = None, thread_class: str | None = "auto",
                fit: Literal["close", "normal", "loose"] = "normal", print_clearance: Expr = 0,
                left_hand: bool = False, to: str | None = None, to_offset: Expr = 0,
                reference_edges: list[str] | None = None, reference_distances: list[Expr] | None = None,
                positions: list[str | dict | list[float]] | None = None, tip_angle: Expr = 118,
                bodies: list[str] | None = None):
    """
    diameter: diámetro del agujero en mm (número o expresión); obligatorio con hole_tap simple, opcional con cosmetic.
    face: la cara plana donde se empieza: selector (">Z"), id de find_faces ("Cuerpo1/F6"). Tiene que dar UNA cara.
        Obligatoria con points, con reference_edges o sin sketch_points; con sketch_points es opcional y solo elige
        el cuerpo.
    points: posiciones fijas sobre face: lista de [u, v] (ejes x,y de un boceto sobre la cara) o [x, y, z] (mundo);
        vacío = centro de la cara. No se combina con sketch_points ni con reference_edges.
    depth: profundidad en mm hasta el fondo plano; obligatoria salvo con through_all o to.
    through_all: true atraviesa todo el cuerpo (ignora depth).
    hole_type: "simple", "counterbore" (abocardado) o "countersink" (avellanado).
    counterbore_diameter: diámetro del abocardado en mm (mayor que diameter); solo con counterbore.
    counterbore_depth: profundidad del abocardado en mm; solo con counterbore.
    countersink_diameter: diámetro del avellanado en la superficie en mm; solo con countersink.
    countersink_angle: ángulo total del avellanado en grados; solo con countersink.
    drill_tip: true deja el fondo en cono como una broca (ángulo tip_angle); false, fondo plano.
    body: cuerpo sobre el que se evalúan los selectores (y que se agujerea con sketch_points); vacío = el único cuerpo
        del documento.
    sketch: id o nombre del boceto de sketch_points; vacío = el último boceto.
    sketch_points: ids de puntos del boceto (get_sketch los lista; el centro de un círculo también es un punto): un
        agujero asociativo en cada uno.
    flip: true invierte el sentido del agujero: con sketch_points el automático (hacia el material); con las demás formas, el normal (hacia adentro de la cara, o −Z con positions).
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
    positions: posición asociativa en puntos del modelo: vértices [x, y, z] (a menos de 0,001 mm de un vértice), puntos de construcción (id o nombre) o {"sketch", "point"}; el agujero va hacia −Z. No se combina con points, sketch_points ni reference_edges.
    tip_angle: ángulo total de la punta de broca en grados (con drill_tip); 118 por defecto.
    bodies: cuerpos extra que se agujerean con el mismo agujero (ids o nombres), además del de face/body; vacío = solo ese.
    """
    referencias = reference_edges is not None or reference_distances is not None
    comunes = _opciones_agujero(sesion, diameter, depth, through_all, hole_type, counterbore_diameter,
                                counterbore_depth, countersink_diameter, countersink_angle, drill_tip, hole_tap, thread,
                                thread_class, fit, print_clearance, left_hand, to, to_offset, body)
    if drill_tip:
        comunes["angulo_punta"] = texto_expr(tip_angle)
    extras = [sesion.cuerpo(b).id for b in bodies or []]
    if positions:
        if points or referencias or sketch_points:
            raise error("INVALID_ARGUMENTS", "positions no se combina con points, sketch_points ni reference_edges.")
        from .herramientas_construccion import _PUNTO, _referencia
        refs = [_referencia(sesion, p, _PUNTO, body) for p in positions]
        principal = sl.cuerpo_objetivo(sesion, body).id if not extras else extras[0]
        op = OpAgujero(sesion.doc.nuevo_id(), nombre_nuevo(sesion.doc, "Agujero", OpAgujero), posiciones=refs,
                       invertir=bool(flip), objetivos=list(dict.fromkeys([principal, *extras])), **comunes)
        res = _agregar(sesion, op, combina=True)
        res["holes"] = len(refs)
        if hole_tap != "simple":
            res["thread"] = comunes["designacion"]
        return res
    if sketch_points:
        if points or referencias:
            raise error("INVALID_ARGUMENTS", "sketch_points (puntos de un boceto) no se combina con points ni con "
                        "reference_edges en un mismo agujero.", "Hacé dos llamadas a create_hole.")
        return _agujero_en_boceto(sesion, comunes, face, body, sketch, sketch_points, flip, hole_tap, extras)
    if sketch is not None and str(sketch).strip():
        raise error("INVALID_ARGUMENTS", "Con sketch hay que decir en qué puntos: sketch_points (ids de get_sketch).")
    if face is None or not str(face).strip():
        raise error("INVALID_ARGUMENTS", "Falta dónde: face (una cara plana, con points o reference_edges opcionales) o "
                    "sketch_points (puntos de un boceto).")
    (cuerpo, elem), = _unica_cara(sesion, face, body)
    plano = sl.plano_de_cara(elem)
    if referencias:
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
    doc = sesion.doc
    op = OpAgujero(doc.nuevo_id(), nombre_nuevo(doc, "Agujero", OpAgujero),
                   objetivos=list(dict.fromkeys([cuerpo.id, *extras])), invertir=bool(flip), **ubicacion, **comunes)
    res = _agregar(sesion, op, combina=True)
    res.update(holes=cantidad, face=sl.emitir_id(sesion, cuerpo, elem))
    if hole_tap != "simple":
        res["thread"] = comunes["designacion"]
    return res


def _opciones_agujero(sesion, diameter, depth, through_all, hole_type, counterbore_diameter, counterbore_depth,
                      countersink_diameter, countersink_angle, drill_tip, hole_tap, thread, thread_class, fit,
                      print_clearance, left_hand, to, to_offset, body):
    """Valida medidas, tipo y rosca; devuelve los campos de OpAgujero que no dependen de dónde va el agujero."""
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
    extension = "todo" if through_all else ("hasta" if to is not None else "distancia")
    if extension == "hasta":
        extra.update(hasta=_ref_hasta(sesion, to, body), desfase_hasta=texto_expr(to_offset))
    return dict(tipo=_TIPO_AGUJERO[hole_type], diametro=texto_expr(diameter if diameter is not None else 6),
                extension=extension, profundidad=texto_expr(depth if depth is not None else 10),
                punta="angulo" if drill_tip else "plana", rosca=rosca, designacion=designacion, clase_rosca=clase,
                ajuste=_AJUSTE[fit], holgura_3d=texto_expr(print_clearance),
                mano="izquierda" if left_hand else "derecha", **extra)


def _dentro(solidos, punto):
    from ..nucleo.consultas import dentro_solidos
    return dentro_solidos(solidos, punto)


def _hacia_el_material(forma, punto, normal):
    """True si el material está del lado +normal del punto (el agujero de un boceto va hacia −normal, así que
    entonces hay que invertirlo). Sobre una cara: del lado que tiene material; en el aire o adentro: hacia donde
    está el centro de la caja del cuerpo."""
    n = np.asarray(normal, float) / (np.linalg.norm(normal) or 1.0)
    p = np.asarray(punto, float)
    solidos = geo.solidos(forma) or [forma]
    arriba, abajo = _dentro(solidos, p + 1e-3 * n), _dentro(solidos, p - 1e-3 * n)
    if arriba != abajo:
        return arriba
    caja = geo.caja_envolvente(forma)
    centro = (np.asarray(caja[0], float) + np.asarray(caja[1], float)) / 2 if caja else p - n
    return float((centro - p) @ n) > 0


def _agujero_en_boceto(sesion, comunes, face, body, sketch, sketch_points, flip, hole_tap, extras=()):
    """create_hole con sketch_points: posiciones = referencias a puntos del boceto (siguen al boceto)."""
    sop, br = boceto_activo(sesion, sketch)
    ids = list(dict.fromkeys(sketch_points))
    faltan = [i for i in ids if i not in br.boceto.puntos]
    if faltan:
        raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» ({sop.id}) no tiene los puntos: "
                    f"{', '.join(map(str, faltan))}.", f"Puntos del boceto: {', '.join(map(str, br.boceto.puntos))}.")
    cuerpo = _unica_cara(sesion, face, body)[0][0] if face and face.strip() else sl.cuerpo_objetivo(sesion, body)
    if getattr(cuerpo, "tipo", "solido") != "solido":
        raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(cuerpo)}» no es un sólido: un agujero necesita "
                    "material.")
    primero = br.plano.a_3d(*br.boceto.coords(ids[0]))
    invertir = _hacia_el_material(cuerpo.forma, primero, br.plano.normal) != bool(flip)
    doc = sesion.doc
    op = OpAgujero(doc.nuevo_id(), nombre_nuevo(doc, "Agujero", OpAgujero),
                   posiciones=[{"tipo": "punto_boceto", "boceto": sop.id, "punto": i} for i in ids],
                   invertir=invertir, objetivos=list(dict.fromkeys([cuerpo.id, *extras])), **comunes)
    res = _agregar(sesion, op, combina=True)
    direccion = -np.asarray(br.plano.normal, float) * (-1 if invertir else 1)
    res.update(holes=len(ids), sketch=sop.id, sketch_points=ids, direction=[round(float(c), 6) + 0.0 for c in direccion])
    if hole_tap != "simple":
        res["thread"] = comunes["designacion"]
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
               "tap_drill": d["broca"]}
        # B-31: classes = las que tienen límites verificados para ESTE tamaño (si no, el modo «auto»
        # avisaba que no hay datos mientras el catálogo las listaba como disponibles).
        disponibles, sin_datos = [], []
        for clase in tol.CLASES_POR_FAMILIA.get(d["familia"], {}):
            try:
                tol.limites_rosca(d["familia"], d["diametro"], d["paso"], clase)
            except geo.ErrorGeometria:
                sin_datos.append(clase)
            else:
                disponibles.append(clase)
        res["classes"] = disponibles
        if sin_datos:
            res["classes_without_data"] = sin_datos
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
def draft(sesion, faces: Elementos, angle: Expr, neutral: str = "XY", reverse: bool = False, body: str | None = None,
          sides: Literal["one", "two", "symmetric"] = "one", angle2: Expr | None = None):
    """
    faces: caras a inclinar: selector ("#Z" = las laterales de una caja), id de find_faces o lista.
    angle: ángulo de desmoldeo en grados (número o expresión), p. ej. 3.
    neutral: plano neutro: "XY", "XZ", "YZ", el id o nombre de un plano de construcción, o una cara plana (selector o id, p. ej. "<Z"); define la dirección de extracción.
    reverse: true invierte la dirección de extracción.
    body: cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
    sides: "one" (un lado, por defecto), "two" (dos lados: angle y angle2) o "symmetric" (simétrico: el mismo ángulo a los dos lados del plano neutro).
    angle2: ángulo del segundo lado en grados; obligatorio con sides=two.
    """
    if sides == "two":
        if angle2 is None:
            raise error("INVALID_ARGUMENTS", "sides=two necesita angle2.")
        if isinstance(angle2, (int, float)) and not 0 < abs(angle2) < 90:
            raise error("INVALID_ARGUMENTS", f"angle2 tiene que estar entre 0 y 90 grados (recibió {angle2}).")
    if isinstance(angle, (int, float)) and not 0 < abs(angle) < 90:
        raise error("INVALID_ARGUMENTS", f"angle tiene que estar entre 0 y 90 grados (recibió {angle}).")
    refs, elegidos = _refs(sesion, faces, "cara", body)
    if neutral.strip().upper() in ("XY", "XZ", "YZ"):
        plano = {"tipo": "plano", "id": neutral.strip().upper()}
    else:
        try:
            plano = {"tipo": "plano", "id": referencia_plano(sesion, neutral)}      # plano de construcción
        except ErrorAPI as e:
            if e.error_kind != "PLANE_NOT_FOUND" or not (sl.es_id(neutral) or sl.parece_selector(neutral)):
                raise
            c, e = _unica_cara(sesion, neutral, body)[0]
            sl.plano_de_cara(e)
            plano = sl.referencia(c, e)
    doc = sesion.doc
    op = OpDesmoldeo(doc.nuevo_id(), nombre_nuevo(doc, "Desmoldeo", OpDesmoldeo), plano=plano, caras=refs,
                     angulo=texto_expr(angle), voltear=reverse,
                     lados={"one": "uno", "two": "dos", "symmetric": "simetrico"}[sides],
                     **({"angulo2": texto_expr(angle2)} if angle2 is not None else {}))
    return _informe(_agregar(sesion, op), elegidos, "faces_used")
