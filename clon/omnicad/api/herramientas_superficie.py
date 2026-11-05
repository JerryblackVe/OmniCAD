"""Herramientas de SUPERFICIE: referencias cortas y las mismas operaciones que la ventana."""
import math
from typing import Literal

from ..timeline import entidades as ent
from ..timeline import ops_superficie as ops
from . import selectores as sl
from .errores import error
from .herramientas_avanzado import traducir_referencias
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_construccion import _referencia
from .herramientas_solido import _agregar, _ids_cuerpos, _numero_positivo, _plano_primitiva, _radio_o_diametro
from .registro import Expr, herramienta

Seleccion = str | dict | list[str | dict]
Referencia = str | dict


def _seleccion(sesion, clase, clave, valor, body=None, tipo="arista", curvas=False):
    """Traduce referencias y selectores; los cuerpos usados como curvas aportan sus caras."""
    items = valor if isinstance(valor, list) else [valor]
    if not items:
        raise error("INVALID_ARGUMENTS", f"Elegí al menos un elemento en {clave}.")
    salida = []
    for item in items:
        if isinstance(item, str):
            prefijo, texto = sl._separar_prefijo(item)
            if prefijo is not None or sl.parece_selector(texto):
                item = {"body": body, "faces" if (prefijo or tipo) == "cara" else "edges": texto}
        # El traductor común ya resuelve bocetos, construcción, ids efímeros y dicts cortos.
        defecto = clase.PARAMS[clave]
        traducido, _ = traducir_referencias(sesion, clase, {clave: [item] if isinstance(defecto, list) else item})
        refs = traducido[clave] if isinstance(defecto, list) else [traducido[clave]]
        for ref in refs:
            if isinstance(ref, str):
                ref = {"tipo": "cuerpo", "cuerpo": sesion.cuerpo(ref).id}
            try:
                ent.validar(ref)
            except ent.ErrorReferencia as exc:
                raise error("INVALID_ARGUMENTS", str(exc)) from None
            if curvas and ref["tipo"] == "cuerpo":
                cuerpo = sesion.cuerpo(ref["cuerpo"])
                salida.extend(sl.referencia(cuerpo, e) for e in sl.listar(cuerpo.forma, "cara"))
            else:
                salida.append(ref)
    if not salida:
        raise error("INVALID_ARGUMENTS", f"La selección de {clave} está vacía.")
    return salida


def _una(sesion, clase, clave, valor, body=None):
    refs = _seleccion(sesion, clase, clave, valor, body, tipo="cara")
    if len(refs) != 1:
        raise error("INVALID_ARGUMENTS", f"{clave} necesita exactamente una referencia.")
    return refs[0]


def _crear(sesion, clase, **params):
    doc = sesion.doc
    return _agregar(sesion, clase(doc.nuevo_id(), nombre_nuevo(doc, clase.ETIQUETA, clase), **params))


def _cuerpos(sesion, bodies):
    ids = list(dict.fromkeys(_ids_cuerpos(sesion, bodies)))
    if not ids:
        raise error("INVALID_ARGUMENTS", "Elegí al menos un cuerpo en bodies.")
    return ids


@herramienta("create_surface_extrude", "solido",
             "Extruye curvas abiertas o cerradas (o un texto de una línea) en una superficie. Opciones de Extruir de "
             "Fusion: start (profile_plane, offset u object), sides (one_side, two_sides con distance2 o symmetric con "
             "symmetric_measure) y extent (distance, to_object hasta una cara, plano o cuerpo con to y to_offset, o all).",
             modifica=True)
def create_surface_extrude(sesion, profiles: Seleccion, distance: Expr = "10 mm",
                           direction: Referencia | None = None, symmetric: bool = False,
                           taper_angle: Expr = 0, body: str | None = None,
                           sides: Literal["one_side", "two_sides", "symmetric"] = "one_side",
                           distance2: Expr | None = None, symmetric_measure: Literal["total", "half"] = "total",
                           start: Literal["profile_plane", "offset", "object"] = "profile_plane",
                           start_offset: Expr = 0, start_object: Referencia | None = None,
                           extent: Literal["distance", "to_object", "all"] = "distance",
                           to: Referencia | None = None, to_offset: Expr = 0, flip: bool = False,
                           chain: bool = True):
    """
    profiles: curvas {"sketch": "Boceto1", "curve": [1, 2]} (un texto de una línea da todos sus trazos), perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas o cuerpos; admite listas, ids y selectores.
    distance: distancia en mm o expresión; negativa invierte el sentido (con sides=one_side).
    direction: eje, plano, cara plana o arista lineal; vacío = normal del boceto (o Z).
    symmetric: lo mismo que sides=symmetric (reparte la distancia total a ambos lados).
    taper_angle: ángulo de conicidad en grados o expresión.
    body: cuerpo sobre el que evaluar selectores sin cuerpo explícito.
    sides: one_side, two_sides (distance hacia un lado y distance2 hacia el otro) o symmetric.
    distance2: distancia del segundo lado con sides=two_sides; vacío = igual a distance.
    symmetric_measure: con sides=symmetric, total (distance es el largo total) o half (distance es la mitad, a cada lado).
    start: dónde empieza la extrusión: profile_plane (el plano de las curvas), offset (a start_offset de él) o object (en la cara plana o plano start_object).
    start_offset: desfase del inicio en mm (número o expresión); con start=offset.
    start_object: cara plana (selector o id) o plano donde empieza; con start=object.
    extent: hasta dónde llega: distance (por defecto), to_object (hasta to) o all (atraviesa todos los cuerpos).
    to: con extent=to_object: cara (selector o id), plano o cuerpo hasta donde llega.
    to_offset: desfase en mm sobre el «hasta» (positivo = más lejos); con extent=to_object.
    flip: true invierte el sentido de la extrusión (el de la normal del boceto o de direction).
    chain: true toma la cadena tangente entera de cada arista o curva de boceto de profiles (Chaining de Fusion, encendido por defecto); false usa solo las elegidas.
    """
    clase = ops.OpSupExtruir
    params = {"lados": "simetrica" if symmetric else {"one_side": "un_lado", "two_sides": "dos_lados",
                                                      "symmetric": "simetrica"}[sides],
              "medida": "mitad" if symmetric_measure == "half" else "total",
              "distancia2": texto_expr(distance if distance2 is None else distance2), "invertir": flip,
              "cadena": chain}
    if start == "offset":
        params.update(inicio="desfase", desfase_inicio=texto_expr(start_offset))
    elif start == "object":
        if start_object is None:
            raise error("INVALID_ARGUMENTS", "start=object necesita start_object (una cara plana o un plano).")
        params.update(inicio="objeto", inicio_objeto=_referencia(sesion, start_object, {"cara", "plano"}, body, "plano"))
    if extent == "to_object":
        if to is None:
            raise error("INVALID_ARGUMENTS", "extent=to_object necesita to (una cara, un plano o un cuerpo).")
        params.update(extension="objeto", desfase_hasta=texto_expr(to_offset),
                      hasta=_referencia(sesion, to, {"cara", "plano", "cuerpo"}, body))
    elif extent == "all":
        params["extension"] = "todo"
    return _crear(sesion, clase, curvas=_seleccion(sesion, clase, "curvas", profiles, body, curvas=True),
                  distancia=texto_expr(distance), direccion=_una(sesion, clase, "direccion", direction, body)
                  if direction is not None else None, conicidad=texto_expr(taper_angle), **params)


@herramienta("create_surface_revolve", "solido",
             "Gira curvas alrededor de un eje para crear una superficie. direction: one_side, two_sides (angle y angle2) "
             "o symmetric. to_object (Extent Type › To Object) gira hasta un vértice, un plano, una cara plana o un "
             "cuerpo en lugar de un ángulo (solo con one_side). project_axis lleva el eje al plano del perfil.",
             modifica=True)
def create_surface_revolve(sesion, profiles: Seleccion, axis: Referencia, angle: Expr = "360 deg",
                           body: str | None = None,
                           direction: Literal["one_side", "two_sides", "symmetric"] = "one_side",
                           angle2: Expr | None = None, to_object: Referencia | list[float] | None = None,
                           project_axis: bool = False, chain: bool = True):
    """
    profiles: curvas o perfiles de boceto ({"sketch": "Boceto1", "curve": 1} o "profile": 0), caras, aristas o cuerpos; admite listas, ids y selectores.
    axis: eje X, Y, Z, eje de construcción o referencia a una línea de boceto/arista lineal.
    angle: ángulo en grados o expresión.
    body: cuerpo sobre el que evaluar selectores.
    direction: one_side, two_sides (angle hacia un lado y angle2 hacia el otro) o symmetric (angle es el total, mitad a cada lado).
    angle2: ángulo del segundo lado con direction=two_sides; vacío = igual a angle.
    to_object: vértice ([x, y, z] o selector), plano, cara plana o cuerpo hasta donde gira el perfil; reemplaza a angle.
    project_axis: true proyecta el eje al plano del perfil (curvas de boceto); false lo deja donde está.
    chain: true toma la cadena tangente entera de cada arista o curva de boceto de profiles (Chaining de Fusion, encendido por defecto); false usa solo las elegidas.
    """
    clase = ops.OpSupRevolucion
    params = {"lados": {"one_side": "un_lado", "two_sides": "dos_lados", "symmetric": "simetrica"}[direction],
              "angulo2": texto_expr(angle if angle2 is None else angle2), "proyectar_eje": project_axis,
              "cadena": chain}
    if to_object is not None:
        if direction != "one_side":
            raise error("INVALID_ARGUMENTS", "to_object gira hacia un solo lado: usá direction=one_side.")
        params.update(extension="objeto", hasta=_referencia(
            sesion, to_object, {"vertice", "punto", "punto_boceto", "plano", "cara", "cuerpo"}, body))
    return _crear(sesion, clase, curvas=_seleccion(sesion, clase, "curvas", profiles, body, curvas=True),
                  eje=_una(sesion, clase, "eje", axis, body), angulo=texto_expr(angle), **params)


@herramienta("create_surface_sweep", "solido",
             "Barre curvas por una ruta. Tipos de Sweep de Fusion: ruta sola (orientation, twist_angle y taper_angle), ruta + "
             "riel (guide_rail, con profile_scaling scale, stretch o none y extent perpendicular_to_path o full_extents) y ruta "
             "+ superficie (guide_surface: el perfil sigue su normal). path_distance es la fracción de la ruta, de 0 a 1.",
             modifica=True)
def create_surface_sweep(sesion, profiles: Seleccion, path: Seleccion,
                         orientation: Literal["perpendicular", "parallel"] = "perpendicular",
                         twist_angle: Expr = 0, body: str | None = None, path_distance: Expr = 1, taper_angle: Expr = 0,
                         guide_rail: Seleccion | None = None,
                         profile_scaling: Literal["scale", "stretch", "none"] = "scale",
                         extent: Literal["perpendicular_to_path", "full_extents"] = "perpendicular_to_path",
                         rail_distance: Expr = 1, guide_surface: Seleccion | None = None, chain: bool = False):
    """
    profiles: curvas o perfiles {"sketch": "Boceto1", "curve": 1} o {"sketch": "Boceto1", "profile": 0}; también caras, aristas o cuerpos.
    path: cadena de curvas de boceto, aristas (ids o selectores), caras o cuerpos.
    orientation: perpendicular sigue la ruta; parallel mantiene la orientación.
    twist_angle: torsión total en grados o expresión; solo con orientación perpendicular.
    body: cuerpo sobre el que evaluar selectores.
    path_distance: hasta dónde llega el barrido sobre la ruta, fracción de 0 (sin incluir) a 1 (toda la ruta).
    taper_angle: conicidad en grados o expresión: positiva abre el perfil a lo largo de la ruta y negativa lo cierra; solo con ruta sola y perpendicular.
    guide_rail: riel guía (curvas de boceto o aristas): orienta el perfil y, según profile_scaling, lo escala.
    profile_scaling: con guide_rail: scale (crece en las dos direcciones con la distancia ruta-riel), stretch (solo hacia el riel, conserva la altura) o none (el riel solo orienta).
    extent: con guide_rail: perpendicular_to_path (termina en un plano perpendicular a la ruta) o full_extents (path_distance sobre la ruta y rail_distance sobre el riel).
    rail_distance: con extent=full_extents, fracción del riel que se usa, de 0 (sin incluir) a 1.
    guide_surface: caras (ids o selectores) sobre las que va la ruta; el perfil sigue su normal; no se combina con guide_rail.
    chain: true suma a la ruta, al perfil y al riel las aristas o curvas que les siguen tangentes (Chain Selection).
    """
    if guide_rail is not None and guide_surface is not None:
        raise error("INVALID_ARGUMENTS", "Pasá guide_rail o guide_surface, no los dos.")
    clase = ops.OpSupBarrido
    params = {"escala_carril": {"scale": "escalar", "stretch": "estirar", "none": "ninguna"}[profile_scaling],
              "extension": "completa" if extent == "full_extents" else "perpendicular",
              "distancia_carril": texto_expr(rail_distance), "cadena": chain}
    if guide_rail is not None:
        params["carril"] = _seleccion(sesion, clase, "carril", guide_rail, body, curvas=True)
    if guide_surface is not None:
        params["superficie_guia"] = _seleccion(sesion, clase, "superficie_guia", guide_surface, body, tipo="cara")
    return _crear(sesion, clase, perfil=_seleccion(sesion, clase, "perfil", profiles, body, curvas=True),
                  ruta=_seleccion(sesion, clase, "ruta", path, body, curvas=True),
                  orientacion="paralela" if orientation == "parallel" else "perpendicular",
                  torsion=texto_expr(twist_angle), distancia=texto_expr(path_distance),
                  conicidad=texto_expr(taper_angle), **params)


def _condicion(cond, sesion, body):
    """{"type", "angle", "weight", "face", "edge_alignment"} de la API → la condición que guarda el paso."""
    tipos = {"free": "libre", "direction": "direccion", "tangent": "tangente", "smooth": "suave",
             "point_tangent": "punto_tangente"}
    alineaciones = {"free": "libre", "align": "alinear", "surface": "superficie"}
    if not isinstance(cond, dict) or set(cond) - {"type", "angle", "weight", "face", "edge_alignment"} or \
            cond.get("type", "free") not in tipos or cond.get("edge_alignment", "free") not in alineaciones:
        raise error("INVALID_ARGUMENTS", 'La condición de borde es {"type": "free" | "direction" | "tangent" | "smooth" | '
                                         '"point_tangent", "angle": grados, "weight": número, "face": cara, '
                                         '"edge_alignment": "free" | "align" | "surface"}.')
    angulo, peso = cond.get("angle", 90), cond.get("weight", 1)
    if isinstance(angulo, (int, float)) and not 0 < angulo < 180:
        raise error("INVALID_ARGUMENTS", "angle está entre 0 y 180 grados.")
    if isinstance(peso, (int, float)) and peso <= 0:
        raise error("INVALID_ARGUMENTS", "weight tiene que ser positivo.")
    salida = {"tipo": tipos[cond.get("type", "free")], "angulo": texto_expr(angulo), "peso": texto_expr(peso),
              "alineacion": alineaciones[cond.get("edge_alignment", "free")]}
    if cond.get("face") is not None:
        salida["cara"] = _referencia(sesion, cond["face"], {"cara"}, body)
    return salida


@herramienta("create_surface_loft", "solido",
             "Crea una superficie entre secciones ordenadas, abiertas o cerradas. start_condition y end_condition fijan cómo "
             "sale de la primera y la última: free, direction (ángulo y peso), tangent y smooth (G1 y G2 contra una cara, con "
             "alineación de bordes), o point_tangent (cúpula en un punto; sin condición un punto queda agudo). rails (cualquier "
             "cantidad, tocan cada sección; con closed, lazos cerrados) y center_line guían la forma y se combinan con las "
             "condiciones: entre rieles manda la condición y sobre cada riel, el riel.", modifica=True)
def create_surface_loft(sesion, profiles: list[str | dict], closed: bool = False, ruled: bool = False,
                        body: str | None = None, rails: list[str | dict] | None = None,
                        center_line: list[str | dict] | None = None, start_condition: dict | None = None,
                        end_condition: dict | None = None, section_conditions: dict | None = None,
                        merge_tangent_edges: bool = False, chain: bool = False):
    """
    profiles: secciones ordenadas: curvas o perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas, cuerpos o puntos de boceto {"sketch": "Boceto1", "point": 1}.
    closed: une la última sección con la primera.
    ruled: usa tramos rectos entre secciones.
    body: cuerpo sobre el que evaluar selectores.
    rails: rieles, uno por elemento (con chain, los tramos tangentes de un mismo riel cuentan como uno): curvas de boceto {"sketch": "Boceto1", "curve": 1} o aristas; cada uno toca todas las secciones.
    center_line: línea central: curvas de boceto o aristas; las secciones se mantienen normales a ella; no se combina con rails.
    start_condition: condición de la primera sección: {"type": "free" | "direction" | "tangent" | "smooth" | "point_tangent", "angle": grados desde el plano del perfil (90 = perpendicular; con direction), "weight": peso de despegue o de tangencia (1 por defecto), "face": cara (con tangent y smooth; vacío = la de la arista elegida como sección), "edge_alignment": "free" | "align" | "surface" (con tangent y smooth en un perfil abierto)}.
    end_condition: lo mismo para la última sección.
    section_conditions: condiciones direction en secciones intermedias: {"2": {"type": "direction", "angle": 60}} (el número es la posición, 1 = la primera).
    merge_tangent_edges: true une las caras que quedan tangentes entre sí (Tangent Edges › Merge).
    chain: true suma a cada arista o curva de profiles y de rails las que le siguen tangentes (Chain Selection).
    """
    clase = ops.OpSupSolevacion
    refs = _seleccion(sesion, clase, "secciones", profiles, body, curvas=True)
    if len(refs) < 2:
        raise error("INVALID_ARGUMENTS", "Una solevación necesita al menos dos secciones.")
    if rails and center_line:
        raise error("INVALID_ARGUMENTS", "Pasá rails o center_line, no los dos.")
    params = {"fusionar_tangentes": merge_tangent_edges, "cadena": chain, "condicion_exacta": True}
    if rails:
        params["carriles"] = _seleccion(sesion, clase, "carriles", rails, body, curvas=True)
    if center_line:
        params["linea_central"] = _seleccion(sesion, clase, "linea_central", center_line, body, curvas=True)
    for clave, cond in (("condicion_inicio", start_condition), ("condicion_fin", end_condition)):
        if cond is not None:
            params[clave] = _condicion(cond, sesion, body)
    if section_conditions:
        n = len(refs)
        for k in section_conditions:
            if not str(k).isdigit() or not 1 < int(k) < n:
                raise error("INVALID_ARGUMENTS", f"section_conditions: «{k}» no es una sección intermedia (de 2 a {n - 1}).")
        params["condiciones_medias"] = {str(int(k) - 1): _condicion(c, sesion, body) for k, c in section_conditions.items()}
    return _crear(sesion, clase, secciones=refs, cerrada=closed, reglada=ruled, **params)


@herramienta("offset_surface", "solido", "Crea una superficie paralela a caras o cuerpos.", modifica=True)
def offset_surface(sesion, faces: Seleccion, distance: Expr = "2 mm",
                   offset_type: Literal["sharp", "rounded"] = "sharp", body: str | None = None,
                   chain: bool = True):
    """
    faces: caras (ids o selectores) o cuerpos por id, nombre o {"body": "Cuerpo1"}; admite listas.
    distance: desfase en mm o expresión; admite valores negativos.
    offset_type: sharp para esquinas agudas; rounded para redondeadas.
    body: cuerpo sobre el que evaluar selectores.
    chain: true suma a cada cara de faces las tangentes de su cuerpo (Chain Selection de Fusion, encendido por defecto); false usa solo las elegidas.
    """
    clase = ops.OpSupDesfase
    return _crear(sesion, clase, caras=_seleccion(sesion, clase, "caras", faces, body, tipo="cara"),
                  distancia=texto_expr(distance), tipo="agudo" if offset_type == "sharp" else "redondeado",
                  cadena=chain)


@herramienta("fillet_surface", "solido", "Redondea o bisela aristas entre superficies.", modifica=True)
def fillet_surface(sesion, edges: Seleccion, size: Expr = "1 mm",
                   fillet_type: Literal["fillet", "chamfer"] = "fillet", body: str | None = None):
    """
    edges: aristas por id o selector; admite listas y {"body": "Cuerpo1", "edges": "|Z"}.
    size: radio del empalme o distancia del chaflán en mm o expresión.
    fillet_type: fillet (empalme) o chamfer (chaflán).
    body: cuerpo sobre el que evaluar selectores.
    """
    _numero_positivo(size, "size")
    clase = ops.OpSupEmpalme
    return _crear(sesion, clase, aristas=_seleccion(sesion, clase, "aristas", edges, body),
                  medida=texto_expr(size), tipo="empalme" if fillet_type == "fillet" else "chaflan")


@herramienta("create_patch", "solido",
             "Tapa un contorno cerrado con continuidad G0, G1 o G2. group_edges=false permite una continuidad por arista "
             "(edge_continuity); interior guía el parche con curvas, aristas o puntos y flip da vuelta la normal.",
             modifica=True)
def create_patch(sesion, boundary: Seleccion, continuity: Literal["G0", "G1", "G2"] = "G0",
                 body: str | None = None, group_edges: bool = True,
                 edge_continuity: list[Literal["G0", "G1", "G2"]] | None = None,
                 interior: Seleccion | None = None, flip: bool = False, chain: bool = True):
    """
    boundary: curvas o perfiles {"sketch": "Boceto1", "profile": 0}, aristas, caras o cuerpos; admite listas, ids y selectores.
    continuity: G0 conexión, G1 tangencia o G2 curvatura; G1/G2 necesitan caras de soporte.
    body: cuerpo sobre el que evaluar selectores.
    group_edges: true usa continuity para todo el contorno; false usa edge_continuity, una por cada referencia de boundary.
    edge_continuity: con group_edges=false, la continuidad de cada referencia de boundary, en el mismo orden.
    interior: curvas, aristas o puntos de boceto que guían el parche (Interior Rails/Points).
    flip: true da vuelta la normal del parche.
    chain: true toma la cadena tangente entera de cada arista o curva de boceto de boundary (Tangent Chain de Fusion, encendido por defecto); false usa solo las elegidas.
    """
    clase = ops.OpParche
    refs = _seleccion(sesion, clase, "contorno", boundary, body, curvas=True)
    params = {"agrupar": group_edges, "invertir": flip, "cadena": chain}
    if not group_edges:
        if not edge_continuity or len(edge_continuity) != len(refs):
            raise error("INVALID_ARGUMENTS", f"group_edges=false necesita edge_continuity con una continuidad por "
                        f"referencia de boundary ({len(refs)}).")
        params["continuidades"] = list(edge_continuity)
    if interior is not None:
        params["interior"] = _seleccion(sesion, clase, "interior", interior, body)
    return _crear(sesion, clase, contorno=refs, continuidad=continuity, **params)


@herramienta("create_ruled_surface", "solido", "Crea superficies rectas desde aristas, con dirección y ángulo.", modifica=True)
def create_ruled_surface(sesion, edges: Seleccion, distance: Expr = "10 mm",
                         surface_type: Literal["normal", "tangent", "direction"] = "normal",
                         direction: Referencia | None = None, angle: Expr = 0, body: str | None = None,
                         mitered_corners: bool = False, alternate_faces: bool = False, chain: bool = True):
    """
    edges: curvas o perfiles de boceto, aristas, caras o cuerpos; admite listas, ids y selectores.
    distance: largo en mm o expresión.
    surface_type: normal, tangent o direction.
    direction: eje, plano, cara plana o arista lineal; obligatorio con surface_type=direction.
    angle: giro de la dirección en grados o expresión.
    body: cuerpo sobre el que evaluar selectores.
    mitered_corners: true corta en ángulo vivo las esquinas entre aristas rectas, arcos o curvas (Mitered Corners); donde dos curvas siguen tangentes no hay esquina; una esquina que no se puede cortar (curvas 3D que no se cruzan, tres aristas en un punto) queda como estaba y el resultado trae un aviso.
    alternate_faces: true usa la otra cara cuando una arista comparte dos (Alternate Faces).
    chain: true toma la cadena tangente entera de cada arista o curva de boceto de edges (Tangent Chain de Fusion, encendido por defecto); false usa solo las elegidas.
    """
    if surface_type == "direction" and direction is None:
        raise error("INVALID_ARGUMENTS", "Indicá direction para una superficie reglada por dirección.")
    clase = ops.OpReglada
    return _crear(sesion, clase, aristas=_seleccion(sesion, clase, "aristas", edges, body, curvas=True),
                  distancia=texto_expr(distance), tipo={"normal": "normal", "tangent": "tangente", "direction": "direccion"}[surface_type],
                  direccion=_una(sesion, clase, "direccion", direction, body) if direction is not None else None,
                  angulo=texto_expr(angle), ingletear=mitered_corners, alternas=alternate_faces, cadena=chain)


@herramienta("extend_surface", "solido", "Alarga bordes libres de superficies.", modifica=True)
def extend_surface(sesion, edges: Seleccion, distance: Expr = "5 mm",
                   extension_type: Literal["natural", "tangent", "perpendicular"] = "natural", body: str | None = None,
                   edge_alignment: Literal["free", "align"] = "align", chain: bool = True):
    """
    edges: bordes libres por id o selector; admite listas y {"body": "Cuerpo1", "edges": ">X"}.
    distance: extensión en mm o expresión.
    extension_type: natural, tangent o perpendicular.
    body: cuerpo sobre el que evaluar selectores.
    edge_alignment: con extension_type=natural, align (Align Edges, G1: la extensión sigue los lados de la cara; por defecto) o free (Free Edges, G0: además admite caras no rectangulares: las planas con una franja tangente, las curvas —esfera, cilindro, cono, toroide, B-spline— sobre su propia superficie).
    chain: true estira toda la cadena tangente de cada borde elegido (Enable Chaining de Fusion, encendido por defecto); false solo el borde.
    """
    clase = ops.OpExtenderSup
    return _crear(sesion, clase, aristas=_seleccion(sesion, clase, "aristas", edges, body),
                  distancia=texto_expr(distance), tipo="tangente" if extension_type == "tangent" else extension_type,
                  alineacion="alinear" if edge_alignment == "align" else "libre", cadena=chain)


@herramienta("trim_surface", "solido", "Recorta una superficie y quita la región indicada por un punto.", modifica=True)
def trim_surface(sesion, surface: str, tool: Referencia, remove_point: list[float], body: str | None = None):
    """
    surface: id o nombre del cuerpo de superficie que se recorta.
    tool: plano, cara, cuerpo o curva de boceto {"sketch": "Boceto1", "curve": 1} que corta la superficie.
    remove_point: punto [x, y, z] en mm sobre la región que se quita.
    body: cuerpo sobre el que evaluar el selector de tool.
    """
    if len(remove_point) != 3 or not all(math.isfinite(x) for x in remove_point):
        raise error("INVALID_ARGUMENTS", "remove_point necesita tres coordenadas finitas [x, y, z].")
    clase = ops.OpRecortar
    return _crear(sesion, clase, cuerpo=sesion.cuerpo(surface).id,
                  herramienta=_una(sesion, clase, "herramienta", tool, body), punto=remove_point)


@herramienta("untrim_surface", "solido",
             "Restaura límites naturales de caras recortadas: boundaries outer, inner, all o manual (solo los contornos "
             "de las aristas de edges). extend estira los bordes exteriores; keep_copy deja la superficie original.",
             modifica=True)
def untrim_surface(sesion, faces: Seleccion, boundaries: Literal["outer", "inner", "all", "manual"] = "outer",
                   body: str | None = None, edges: Seleccion | None = None, extend: Expr = 0,
                   keep_copy: bool = False):
    """
    faces: caras por id o selector; admite listas y {"body": "Cuerpo1", "faces": "all"}.
    boundaries: outer exteriores, inner interiores, all todos los contornos o manual los de edges.
    body: cuerpo sobre el que evaluar selectores.
    edges: con boundaries=manual, las aristas (de las caras) que se destriman.
    extend: distancia en mm (número o expresión) que se estiran los bordes exteriores de la superficie destrimada.
    keep_copy: true conserva una copia de la superficie original como cuerpo aparte.
    """
    clase = ops.OpDestrimar
    if boundaries == "manual" and not edges:
        raise error("INVALID_ARGUMENTS", "boundaries=manual necesita edges: las aristas a destrimar.")
    return _crear(sesion, clase, caras=_seleccion(sesion, clase, "caras", faces, body, tipo="cara"),
                  contornos={"outer": "exteriores", "inner": "interiores", "all": "todos", "manual": "manual"}[boundaries],
                  aristas=_seleccion(sesion, clase, "aristas", edges, body) if edges else [],
                  extension=texto_expr(extend), mantener_copia=keep_copy)


@herramienta("stitch_surfaces", "solido", "Cose superficies; un cierre completo produce un sólido.", modifica=True)
def stitch_surfaces(sesion, bodies: str | list[str], tolerance: Expr = "0.01 mm"):
    """
    bodies: ids o nombres de los cuerpos que se cosen; se conserva el primero y se consumen los demás.
    tolerance: tolerancia de costura en mm o expresión.
    """
    _numero_positivo(tolerance, "tolerance")
    return _crear(sesion, ops.OpCoser, cuerpos=_cuerpos(sesion, bodies), tolerancia=texto_expr(tolerance))


@herramienta("inspect_stitch", "solido",
             "Dice qué dejaría una costura sin hacerla: si se cierra un sólido, cuántas aristas se cosen y cada borde libre "
             "con su punto medio, su largo y su hueco (la tolerancia que haría falta para cerrarlo).")
def inspect_stitch(sesion, bodies: str | list[str], tolerance: float = 0.01):
    """
    bodies: ids o nombres de los cuerpos que se coserían.
    tolerance: tolerancia de costura en mm.
    """
    _numero_positivo(tolerance, "tolerance")
    from ..nucleo import superficies as sf
    r = sf.bordes_de_costura([sesion.cuerpo(c).forma for c in _cuerpos(sesion, bodies)], float(tolerance))
    return {"closes_solid": r["es_solido"], "stitched_edges": r["aristas_cosidas"], "free_edge_count": r["total_libres"],
            "free_edges": [{"point": b["punto"], "length": round(b["largo"], 4),
                            "gap": None if b["hueco"] is None else round(b["hueco"], 4)} for b in r["libres"]]}


@herramienta("unstitch_surfaces", "solido",
             "Separa cada cara en un cuerpo de superficie independiente: de los bodies enteros o solo de las faces "
             "elegidas (lo demás queda cosido).", modifica=True)
def unstitch_surfaces(sesion, bodies: str | list[str] | None = None, faces: Seleccion | None = None,
                      body: str | None = None, chain: bool = True):
    """
    bodies: ids o nombres de cuerpos; cada cara pasa a ser un cuerpo nuevo.
    faces: caras (ids o selectores) que se separan del resto; admite listas.
    body: cuerpo sobre el que evaluar selectores de faces.
    chain: true suma a cada cara de faces las tangentes de su cuerpo (Chain Selection de Fusion, encendido por defecto); false separa solo las elegidas.
    """
    if bodies is None and faces is None:
        raise error("INVALID_ARGUMENTS", "Elegí bodies (cuerpos enteros) o faces (caras sueltas).")
    clase = ops.OpDescoser
    return _crear(sesion, clase, cuerpos=_cuerpos(sesion, bodies) if bodies is not None else [],
                  caras=_seleccion(sesion, clase, "caras", faces, body, tipo="cara") if faces is not None else [],
                  cadena=chain)


@herramienta("reverse_surface_normal", "solido", "Invierte la orientación de cuerpos de superficie.", modifica=True)
def reverse_surface_normal(sesion, bodies: str | list[str]):
    """
    bodies: ids o nombres de superficies cuya normal se invierte.
    """
    return _crear(sesion, ops.OpInvertirNormal, cuerpos=_cuerpos(sesion, bodies))


def _primitiva(sesion, forma, base, medidas, x, y, z, plane, body, **extra):
    doc, clase = sesion.doc, ops.OpSupPrimitiva
    p = {"forma": forma, "x": texto_expr(x), "y": texto_expr(y), "z": texto_expr(z)}
    p.update({k: texto_expr(v) for k, v in medidas.items()})
    p.update(_plano_primitiva(sesion, plane, body), **extra)
    return _agregar(sesion, clase(doc.nuevo_id(), nombre_nuevo(doc, base, clase, lambda o: o.p["forma"] == forma), **p))


@herramienta("create_surface_box", "solido",
             "Crea una superficie con forma de caja (Fusion: Surface › Box). length es el tamaño en X, width en Y y height en Z.",
             modifica=True)
def create_surface_box(sesion, length: Expr, width: Expr, height: Expr, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                       anchor: Literal["center", "corner"] = "center", plane: str | dict | None = None,
                       body: str | None = None):
    """
    length: tamaño en X (mm, positivo).
    width: tamaño en Y (mm, positivo).
    height: tamaño en Z (mm, positivo).
    x: x del centro de la base o de la esquina mínima, según anchor (mm).
    y: y del centro de la base o de la esquina mínima, según anchor (mm).
    z: z de la base (mm).
    anchor: "center" sitúa (x, y, z) en el centro de la base; "corner", en la esquina mínima.
    plane: plano o cara plana sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano y z la distancia sobre su normal.
    body: cuerpo donde se evalúa el selector de plane.
    """
    for valor, que in ((length, "length"), (width, "width"), (height, "height")):
        _numero_positivo(valor, que)
    return _primitiva(sesion, "caja", "Caja", {"ancho": length, "largo": width, "alto": height}, x, y, z, plane, body,
                      caja_centrada=anchor == "center")


@herramienta("create_surface_cylinder", "solido",
             "Crea una superficie con forma de cilindro (Fusion: Surface › Cylinder). La medida va como radius o diameter.",
             modifica=True)
def create_surface_cylinder(sesion, height: Expr, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                            diameter: Expr | None = None, plane: str | dict | None = None, body: str | None = None):
    """
    height: altura en mm (positiva).
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro de la base (mm).
    y: y del centro de la base (mm).
    z: z de la base (mm).
    diameter: diámetro en mm, en vez de radius.
    plane: plano o cara plana sobre el que se crea; vacío = el mundo. Con plane, el eje va por su normal.
    body: cuerpo donde se evalúa el selector de plane.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    _numero_positivo(height, "height")
    return _primitiva(sesion, "cilindro", "Cilindro", {"radio": radio, "alto": height}, x, y, z, plane, body)


@herramienta("create_surface_sphere", "solido",
             "Crea una superficie con forma de esfera (Fusion: Surface › Sphere). La medida va como radius o diameter.",
             modifica=True)
def create_surface_sphere(sesion, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                          diameter: Expr | None = None, plane: str | dict | None = None, body: str | None = None):
    """
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro (mm).
    y: y del centro (mm).
    z: z del centro (mm).
    diameter: diámetro en mm, en vez de radius.
    plane: plano o cara plana sobre el que se crea; vacío = el mundo.
    body: cuerpo donde se evalúa el selector de plane.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    return _primitiva(sesion, "esfera", "Esfera", {"radio": radio}, x, y, z, plane, body)


@herramienta("create_surface_torus", "solido",
             "Crea una superficie con forma de toroide (Fusion: Surface › Torus). Medidas como radios o diámetros, uno de cada "
             "par; position pone el tubo adentro, centrado o afuera del círculo.", modifica=True)
def create_surface_torus(sesion, major_radius: Expr | None = None, minor_radius: Expr | None = None, x: Expr = 0, y: Expr = 0,
                         z: Expr = 0, major_diameter: Expr | None = None, minor_diameter: Expr | None = None,
                         plane: str | dict | None = None, body: str | None = None,
                         position: Literal["inside", "center", "outside"] = "center"):
    """
    major_radius: radio del círculo de referencia en mm; tiene que ser mayor que minor_radius.
    minor_radius: radio menor en mm (del tubo).
    x: x del centro (mm).
    y: y del centro (mm).
    z: z del centro (mm).
    major_diameter: diámetro del círculo de referencia, en vez de major_radius.
    minor_diameter: diámetro del tubo, en vez de minor_radius.
    plane: plano o cara plana sobre el que se crea; vacío = el mundo. Con plane, el eje va por su normal.
    body: cuerpo donde se evalúa el selector de plane.
    position: inside (el tubo adentro del círculo), center (centrado) u outside (afuera).
    """
    mayor = _radio_o_diametro(major_radius, major_diameter, "major_radius", "major_diameter")
    menor = _radio_o_diametro(minor_radius, minor_diameter, "minor_radius", "minor_diameter")
    return _primitiva(sesion, "toroide", "Toroide", {"radio_mayor": mayor, "radio_menor": menor}, x, y, z, plane, body,
                      posicion_toroide={"inside": "interior", "center": "centro", "outside": "exterior"}[position])


@herramienta("create_surface_coil", "solido", "Crea una superficie con forma de bobina o espiral (Fusion: Surface › Coil).",
             modifica=True)
def create_surface_coil(sesion, diameter: Expr = 20,
                        coil_type: Literal["revolutions_height", "revolutions_pitch", "height_pitch", "spiral"] = "revolutions_height",
                        revolutions: Expr = 5, height: Expr = 30, pitch: Expr = 6, angle: Expr = 0,
                        section: Literal["circular", "square", "triangle_external", "triangle_internal"] = "circular",
                        section_size: Expr = 3, position: Literal["on", "inside", "outside"] = "on",
                        clockwise: bool = False, plane: Referencia = "XY", center_point: list[float] | None = None,
                        body: str | None = None):
    """
    diameter: diámetro de la bobina en mm o expresión.
    coil_type: revolutions_height, revolutions_pitch, height_pitch o spiral.
    revolutions: cantidad de vueltas (número o expresión escalar).
    height: altura axial en mm para los tipos con altura.
    pitch: paso axial, o radial en la espiral, en mm.
    angle: ángulo de conicidad en grados; no se usa en espiral.
    section: circular, square, triangle_external o triangle_internal.
    section_size: diámetro del círculo circunscrito de la sección en mm.
    position: sección on (sobre el diámetro), inside (dentro) u outside (fuera).
    clockwise: true invierte el sentido de giro.
    plane: plano XY/XZ/YZ, plano de construcción o cara plana.
    center_point: [x, y, z] del centro en mm; vacío = el origen del plano.
    body: cuerpo donde se evalúan los selectores.
    """
    _numero_positivo(diameter, "diameter")
    _numero_positivo(section_size, "section_size")
    return _crear(sesion, ops.OpSupBobina, plano=_referencia(sesion, plane, {"plano", "cara"}, body, "plano"),
                  centro_xyz=[float(x) for x in center_point] if center_point else None, diametro=texto_expr(diameter),
                  tipo={"revolutions_height": "rev_altura", "revolutions_pitch": "rev_paso", "height_pitch": "altura_paso",
                        "spiral": "espiral"}[coil_type],
                  revoluciones=texto_expr(revolutions), altura=texto_expr(height), paso=texto_expr(pitch),
                  angulo=texto_expr(angle), tamano=texto_expr(section_size), horario=clockwise,
                  seccion={"circular": "circular", "square": "cuadrada", "triangle_external": "triangular_externa",
                           "triangle_internal": "triangular_interna"}[section],
                  posicion={"on": "sobre", "inside": "dentro", "outside": "fuera"}[position])


@herramienta("create_surface_pipe", "solido", "Crea una superficie con forma de tubería sobre una ruta (Fusion: Surface › Pipe).",
             modifica=True)
def create_surface_pipe(sesion, path: Seleccion, section: Literal["circular", "square", "triangle"] = "circular",
                        section_size: Expr = 5, end: Expr = 1, start: Expr = 0, chain: bool = True, hollow: bool = False,
                        thickness: Expr = 0.5, body: str | None = None):
    """
    path: curvas de boceto o aristas (ids o selectores) de la ruta; admite listas.
    section: circular, square o triangle.
    section_size: diámetro del círculo circunscrito de la sección en mm.
    end: fracción final de la ruta, entre 0 y 1.
    start: fracción inicial de la ruta, entre 0 y 1, menor que end.
    chain: true incluye la cadena tangente conectada a la ruta elegida.
    hollow: true hace la sección hueca.
    thickness: espesor de la pared en mm con hollow=true.
    body: cuerpo donde se evalúan los selectores.
    """
    _numero_positivo(section_size, "section_size")
    if hollow:
        _numero_positivo(thickness, "thickness")
    clase = ops.OpSupTuberia
    return _crear(sesion, clase, ruta=_seleccion(sesion, clase, "ruta", path, body, curvas=True), cadena=chain,
                  distancia=texto_expr(end), distancia2=texto_expr(start), tamano=texto_expr(section_size),
                  seccion={"circular": "circular", "square": "cuadrada", "triangle": "triangular"}[section],
                  hueca=hollow, espesor=texto_expr(thickness))
