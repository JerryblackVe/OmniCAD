# -*- coding: utf-8 -*-
"""
Herramientas del grupo "solido": extrusión, revolución, barrido, solevación, primitivas, booleanas, simetría,
patrones y movimiento de cuerpos.

Todas devuelven lo necesario para seguir: el paso creado (`feature`: id, nombre, tipo), los cuerpos creados,
modificados y quitados (`bodies_created`, `bodies_modified` con id, nombre y volumen mm³, `bodies_removed` con
ids) y, en el sobre de `llamar`, los avisos.

`operation`: new_body (cuerpo nuevo), join (unir), cut (cortar) o intersect (intersecar). Con join, cut e
intersect, `target` elige los cuerpos afectados (ids o nombres); sin `target` son los sólidos que toca la
herramienta (como el modo automático de Fusion).

Empalmes, chaflanes, vaciado, agujeros y desmoldeo (los que eligen caras o aristas con selectores) están en
`herramientas_modificar.py`; los selectores, en `selectores.py`.
"""
import math
from typing import Literal

from ..nucleo import geometria as geo
from ..timeline.operaciones import OpCombinar, OpExtrusion, OpPrimitiva, OpRevolucion
from ..timeline.ops_modificar import OpApoyar, OpMover
from ..timeline.ops_solido import OpBarrido, OpMultitransformar, OpPatron, OpSimetria, OpSolevacion
from .errores import ErrorAPI, error
from .herramientas_boceto import (boceto_activo, nombre_nuevo, referencia_plano_o_cara, seleccionar_perfiles,
                                  texto_expr)
from .registro import Expr, herramienta

OPERACIONES = {"new_body": "nuevo", "join": "unir", "cut": "cortar", "intersect": "intersecar"}
Operacion = Literal["new_body", "join", "cut", "intersect"]
Perfiles = int | list[int] | str
Cuerpos = str | list[str]
Pasos = str | list[str]
Elementos = str | list[str]


def _r(x):
    return None if x is None else round(float(x), 4) + 0.0


# ---------------------------------------------------------------- informes y utilidades
def _lista(x):
    return [] if x is None else [x] if isinstance(x, str) else list(x)


def _ids_cuerpos(sesion, refs):
    return [sesion.cuerpo(r).id for r in _lista(refs)]


def _objetivos(sesion, operation, target):
    ids = _ids_cuerpos(sesion, target)
    if ids and operation == "new_body":
        sesion.avisar("«target» se ignora con operation=new_body: el cuerpo es nuevo.")
        return []
    return ids


def _foto(sesion):
    return {c.id: c.forma for c in sesion.doc.estado_final.cuerpos.values()}


def _info_cuerpo(sesion, c):
    return {"id": c.id, "name": sesion.nombre_cuerpo(c),
            "volume": _r(geo.volumen(c.forma)) if getattr(c, "tipo", "solido") == "solido" else None}


def _informe(sesion, op, antes, combina=False):
    """Paso creado y cuerpos que aparecieron, cambiaron o desaparecieron respecto de `antes` (`_foto`).
    Un cuerpo "modificado" es uno cuya forma recalculó el paso (trae también `previous_volume`). Con
    `combina` (join, cut, intersect) se avisa si ningún volumen cambió: la herramienta no tocó al objetivo."""
    cuerpos = sesion.doc.estado_final.cuerpos
    modificados = []
    for cid, c in cuerpos.items():
        if cid in antes and antes[cid] is not c.forma:
            info = _info_cuerpo(sesion, c)
            info["previous_volume"] = _r(geo.volumen(antes[cid])) if info["volume"] is not None else None
            modificados.append(info)
    creados = [_info_cuerpo(sesion, c) for cid, c in cuerpos.items() if cid not in antes]
    quitados = [cid for cid in antes if cid not in cuerpos]
    if combina and not creados and not quitados and all(
            m["volume"] is not None and abs(m["volume"] - m["previous_volume"]) < 1e-6 * max(1.0, m["volume"])
            for m in modificados):
        sesion.avisar("La operación no cambió el volumen de ningún cuerpo: ¿la herramienta toca al objetivo?")
    return {"feature": {"id": op.id, "name": op.nombre, "type": op.TIPO}, "bodies_created": creados,
            "bodies_modified": modificados, "bodies_removed": quitados}


def _agregar(sesion, op, combina=False):
    antes = _foto(sesion)
    sesion.doc.agregar(op)
    return _informe(sesion, op, antes, combina)


def _ref_perfil(sop, perfil):
    return dict(OpExtrusion.referencia_perfil(perfil), tipo="perfil", boceto=sop.id)


def _numero_positivo(valor, que, minimo=0.0):
    """Medida en mm: mayor que `minimo` (0 por defecto) y de hasta 1.000.000 (1 km), como las cotas (B-53). Solo
    números: las expresiones las valida el núcleo al calcular el paso (y también les pone el tope de 1 km)."""
    from ..restricciones.boceto import MEDIDA_MAXIMA
    if isinstance(valor, (int, float)) and not minimo < valor <= MEDIDA_MAXIMA:
        if minimo:
            raise error("INVALID_ARGUMENTS", f"{que} tiene que ser de más de {minimo:g} mm y de hasta 1.000.000 mm "
                                              f"(1 km) (recibió {valor:g}): menos que eso el kernel no lo distingue.")
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser mayor que 0 y de hasta 1.000.000 mm (1 km) "
                                          f"(recibió {valor:g}).")


def _exigir_instancias(total, que):
    """Tope de instancias de un patrón, antes de gastar un id (el núcleo lo vuelve a frenar en run_operation)."""
    from ..nucleo.solidos_crear import INSTANCIAS_MAXIMAS      # local: el núcleo se carga recién al calcular
    if total > INSTANCIAS_MAXIMAS:
        maximo, pedido = (f"{n:,}".replace(",", ".") for n in (INSTANCIAS_MAXIMAS, total))
        raise error("INVALID_ARGUMENTS", f"Un patrón admite como máximo {maximo} instancias, el original incluido "
                                         f"({que} = {pedido}).")


def _forma_del_objetivo(sesion, target):
    """Forma sobre la que medir el lado del material: el cuerpo de `target` si se dio, si no todos los sólidos
    (o None si no hay ninguno: no se invierte)."""
    if target is not None and (isinstance(target, str) and target.strip() or target):
        cuerpos = [sesion.cuerpo(x) for x in (target if isinstance(target, list) else [target])]
    else:
        cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
    if not cuerpos:
        return None
    from ..nucleo import geometria as geo
    return geo.compuesto([c.forma for c in cuerpos]) if len(cuerpos) > 1 else cuerpos[0].forma


# ---------------------------------------------------------------- extrusión y revolución
@herramienta("extrude", "solido",
             "Extruye perfiles de un boceto. profile: índice, lista de índices, 'all', 'largest' (el perfil de mayor "
             "área, p. ej. la placa con sus agujeros) o 'text' (las letras de los textos, sin los huecos de la «o»; "
             "'text:<id>' para uno solo). distance acepta un número (mm) o una expresión con parámetros. "
             "El sentido positivo es la normal del plano del boceto (en XZ es −Y); reverse lo invierte. Como en Fusion, "
              "un cut entra al material sin pedirlo con reverse vacío (sobre una cara va contra la normal exterior; "
              "en un boceto flotante va hacia el lado que tiene material). direction: "
             "one_side, two_sides (distance y distance2) o symmetric (distance es el largo TOTAL, mitad a cada "
             "lado). taper_angle inclina las paredes (grados; positivo ensancha el sólido hacia el final, negativo "
             "lo estrecha). operation: new_body, join, cut o intersect. Opciones de Extruir de Fusion: faces (caras "
             "planas como perfil, con o sin sketch), thin (extrusión delgada: wall_thickness, wall_location; con "
             "open_curves se extruyen curvas abiertas), start (profile_plane, offset u object: el inicio no es el "
             "plano del perfil), symmetric_measure (media longitud o largo total), extent (distance, to_object: hasta "
             "una cara, plano o cuerpo con to, to_mode y to_offset, o all: atraviesa todo) y taper_angle2 (conicidad "
             "propia del lado 2).",
             modifica=True)
def extrude(sesion, sketch: str | None = None, profile: Perfiles = 0, distance: Expr = "10 mm",
            operation: Operacion = "new_body",
            direction: Literal["one_side", "two_sides", "symmetric"] = "one_side", taper_angle: Expr = 0,
            target: Cuerpos | None = None, distance2: Expr | None = None, reverse: bool | None = None,
            faces: Cuerpos | None = None, thin: bool = False, wall_thickness: Expr = 1,
            wall_location: Literal["side1", "side2", "center"] = "side1",
            start: Literal["profile_plane", "offset", "object"] = "profile_plane", start_offset: Expr = 0,
            start_object: str | None = None, symmetric_measure: Literal["total", "half"] = "total",
            extent: Literal["distance", "to_object", "all"] = "distance", to: str | None = None,
            to_mode: Literal["face", "body", "through"] = "face", to_offset: Expr = 0,
            taper_angle2: Expr | None = None, open_curves: list[int] | None = None, body: str | None = None):
    """
    sketch: id o nombre del boceto de los perfiles; vacío si el perfil son solo caras (faces).
    profile: perfil(es): índice (get_sketch los lista), lista de índices, "all", "largest", "text" (las letras de los textos, sin sus huecos) o "text:<id>". Se ignora con open_curves.
    distance: distancia de extrusión: número en mm o expresión, p. ej. "espesor" o "2 * radio".
    operation: "new_body", "join", "cut" o "intersect".
    direction: "one_side", "two_sides" o "symmetric".
    taper_angle: conicidad en grados (número o expresión): positivo ensancha hacia el final, negativo estrecha; 0 = recto.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    distance2: distancia del segundo lado con direction="two_sides"; vacío = igual a distance.
    reverse: true para extruir hacia el lado contrario de la normal del plano. Vacío = automático: un cut entra al
        material (sobre una cara, o con faces como único perfil, va contra la normal exterior; en un boceto flotante
        va hacia el lado que tiene material, como Fusion).
    faces: caras planas (selector o id de find_faces, o lista) usadas como perfil, solas o junto con los perfiles de sketch; tienen que ser coplanares. Extruir solo una cara de un cuerpo: operation="join" la empuja hacia afuera (agrega material); operation="cut" la empuja hacia adentro (corta; ver reverse).
    thin: true hace una extrusión delgada (pared de wall_thickness) en lugar de sólida.
    wall_thickness: espesor de la pared en mm (número o expresión); solo con thin.
    wall_location: lado del contorno donde va la pared: "side1", "side2" o "center"; solo con thin.
    start: dónde empieza la extrusión: "profile_plane" (el plano del perfil), "offset" (a start_offset de él) o "object" (en la cara plana o plano start_object).
    start_offset: desfase del inicio en mm (número o expresión); con start=offset.
    start_object: cara plana (selector o id) o plano de construcción donde empieza; con start=object.
    symmetric_measure: con direction=symmetric, "total" (distance es el largo total) o "half" (distance es la mitad, a cada lado).
    extent: hasta dónde llega: "distance" (distance, por defecto), "to_object" (hasta to) o "all" (atraviesa todos los cuerpos).
    to: con extent=to_object: cara (selector o id), plano o cuerpo hasta donde llega.
    to_mode: con to_object: "face" (hasta la cara), "body" (hasta el cuerpo) o "through" (a través del cuerpo).
    to_offset: desfase en mm sobre el «hasta» (positivo = más lejos); con extent=to_object.
    taper_angle2: conicidad del lado 2 en grados con direction=two_sides; vacío = la misma que taper_angle.
    open_curves: ids de curvas ABIERTAS de sketch (get_sketch) para extruir con thin=true; reemplazan a profile.
    body: cuerpo donde se evalúan los selectores de faces, start_object y to; vacío = el único cuerpo.
    """
    if sketch is None and not faces:
        raise error("INVALID_ARGUMENTS", "Falta el perfil: sketch (con profile) o faces (caras planas).")
    if open_curves and not thin:
        raise error("INVALID_ARGUMENTS", "open_curves (curvas abiertas) necesita thin=true: una curva abierta solo se extruye con pared.")
    if open_curves and sketch is None:
        raise error("INVALID_ARGUMENTS", "open_curves necesita sketch: son curvas de ese boceto.")
    if thin:
        _numero_positivo(wall_thickness, "wall_thickness")
    sop = br = None
    perfiles = []
    if sketch is not None:
        sop, br = boceto_activo(sesion, sketch)
        if not open_curves:
            perfiles = seleccionar_perfiles(br, sop, profile)
    if reverse is None and br is not None:
        if operation == "cut" and sop.p.get("plano") == "cara":
            reverse = True                        # sobre una cara: entra al material (la normal mira afuera)
        elif operation == "cut" and direction == "one_side":
            # B-10: boceto flotante (p. ej. un plano de construcción por encima de la pieza): el cut va
            # hacia el lado que tiene material, no siempre hacia +normal.
            from .herramientas_modificar import _hacia_el_material
            forma = _forma_del_objetivo(sesion, target)
            if forma is not None and not _hacia_el_material(forma, br.plano.origen, br.plano.normal):
                reverse = True
    elif reverse is None and br is None and operation == "cut" and direction == "one_side":
        reverse = True                            # solo caras: su normal mira afuera, el cut entra al material
    from .herramientas_construccion import _referencia
    doc = sesion.doc
    p = {"boceto": sop.id if sop is not None else "", "perfiles": [OpExtrusion.referencia_perfil(x) for x in perfiles],
         "distancia": texto_expr(distance), "operacion": OPERACIONES[operation],
         "objetivos": _objetivos(sesion, operation, target), "invertir": reverse,
         "conicidad": texto_expr(taper_angle),
         "conicidad2": texto_expr(taper_angle if taper_angle2 is None else taper_angle2)}
    if faces:
        from .herramientas_modificar import _refs
        p["caras"] = _refs(sesion, faces, "cara", body)[0]
    if thin:
        p.update(tipo="delgada", espesor=texto_expr(wall_thickness),
                 ubicacion={"side1": "lado1", "side2": "lado2", "center": "centro"}[wall_location])
        if open_curves:
            p["curvas"] = [{"tipo": "curva_boceto", "boceto": sop.id, "curva": int(c)} for c in dict.fromkeys(open_curves)]
            for c in open_curves:
                if c not in br.boceto.curvas:
                    raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene la curva {c} (get_sketch las lista).")
    if start == "offset":
        p.update(inicio="desfase", desfase_inicio=texto_expr(start_offset))
    elif start == "object":
        if start_object is None:
            raise error("INVALID_ARGUMENTS", "start=object necesita start_object (una cara plana o un plano).")
        p.update(inicio="objeto", inicio_objeto=_referencia(sesion, start_object, {"cara", "plano"}, body, "plano"))
    if extent == "to_object":
        if to is None:
            raise error("INVALID_ARGUMENTS", "extent=to_object necesita to (una cara, un plano o un cuerpo).")
        p.update(extension="objeto", hasta=_referencia(sesion, to, {"cara", "plano", "cuerpo"}, body),
                 hasta_modo={"face": "cara", "body": "cuerpo", "through": "a_traves"}[to_mode],
                 desfase_hasta=texto_expr(to_offset))
    elif extent == "all":
        p["extension"] = "todo"
    if direction == "two_sides":
        p.update(direccion="dos_lados", distancia2=texto_expr(distance if distance2 is None else distance2))
    elif direction == "symmetric":
        if symmetric_measure == "half":
            p.update(direccion="simetrica", simetrica=False, medida="mitad")
        else:
            p.update(direccion="simetrica", simetrica=True, medida="total")
    op = OpExtrusion(doc.nuevo_id(), nombre_nuevo(doc, "Extrusión", OpExtrusion), **p)
    resultado = _agregar(sesion, op, operation != "new_body")
    resultado["profiles_used"] = [br.perfiles.index(x) for x in perfiles] if br is not None else []
    return resultado


def _eje_revolucion(sesion, sop, br, axis, body=None):
    s = str(axis).strip().casefold()
    if s == "sketch_x" and br is not None:
        return {"eje": "u"}
    if s == "sketch_y" and br is not None:
        return {"eje": "v"}
    if s in ("x", "y", "z"):
        return {"eje_ref": {"tipo": "eje", "id": s.upper()}}
    if br is not None and s.isdigit() and int(s) in br.boceto.curvas and br.boceto.curvas[int(s)].tipo == "linea":
        return {"eje": str(int(s))}
    if isinstance(axis, dict) or (isinstance(axis, str) and not s.isdigit() and s not in ("sketch_x", "sketch_y")):
        # un eje de construcción, una arista recta, una cara cilíndrica o una línea de OTRO boceto
        from .herramientas_construccion import _referencia
        try:
            return {"eje_ref": _referencia(sesion, axis, {"eje", "arista", "curva_boceto", "cara"}, body, "eje")}
        except ErrorAPI as e:
            if e.error_kind != "INVALID_ARGUMENTS":
                raise
    raise error("INVALID_AXIS", f"El eje '{axis}' no sirve para girar"
                + (f" el boceto «{sop.nombre}»" if sop is not None else "") +
                (": esa entidad no es una línea del boceto." if s.isdigit() else "."))


@herramienta("revolve", "solido",
             "Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del "
             "boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del "
             "boceto (get_sketch; puede ser de construcción); también un eje de construcción (id o nombre), una "
             "arista recta o una cara cilíndrica (selector o id de find_edges / find_faces) o una línea de OTRO boceto "
             "({\"sketch\": id, \"curve\": n}). El perfil no debe cruzar el eje; puede ser una cara plana (faces). angle "
             "acepta número (grados) o expresión. direction: one_side, two_sides (angle y angle2) o symmetric. to_object "
             "(Extent Type › To Object) gira el perfil hasta un vértice, un plano, una cara plana o un cuerpo en lugar "
             "de un ángulo (solo con one_side). project_axis lleva el eje al plano del perfil (Project Axis).",
             modifica=True)
def revolve(sesion, sketch: str | None = None, profile: Perfiles = 0, axis: int | str | dict | None = None,
            angle: Expr = "360 deg", operation: Operacion = "new_body",
            direction: Literal["one_side", "two_sides", "symmetric"] = "one_side",
            angle2: Expr | None = None, target: Cuerpos | None = None, reverse: bool = False,
            faces: Cuerpos | None = None, body: str | None = None, to_object: str | dict | list[float] | None = None,
            project_axis: bool = False):
    """
    sketch: id o nombre del boceto de los perfiles; vacío si el perfil son solo caras (faces).
    profile: perfil(es): índice, lista de índices, "all", "largest", "text" o "text:<id>".
    axis: "sketch_x", "sketch_y", "x", "y", "z", el id de una línea del boceto, un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id) o {"sketch": id, "curve": n} (línea de otro boceto).
    angle: ángulo de giro: número en grados o expresión, p. ej. "270 deg" o "giro".
    operation: "new_body", "join", "cut" o "intersect".
    direction: "one_side", "two_sides" o "symmetric" (el ángulo se reparte a los dos lados).
    angle2: ángulo del segundo lado con direction="two_sides"; vacío = igual a angle.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    reverse: true para girar en el sentido contrario.
    faces: caras planas (selector o id de find_faces, o lista) usadas como perfil, solas o junto con los perfiles de sketch.
    body: cuerpo donde se evalúan los selectores de faces y de axis (arista o cara); vacío = el único cuerpo.
    to_object: vértice ([x, y, z] o selector), plano (XY/XZ/YZ o de construcción), cara plana (selector o id) o cuerpo (id o nombre) hasta donde gira el perfil; reemplaza a angle.
    project_axis: true proyecta el eje al plano del perfil; false lo deja donde está.
    """
    if sketch is None and not faces:
        raise error("INVALID_ARGUMENTS", "Falta el perfil: sketch (con profile) o faces (caras planas).")
    sop = br = None
    perfiles = []
    if sketch is not None:
        sop, br = boceto_activo(sesion, sketch)
        perfiles = seleccionar_perfiles(br, sop, profile)
        if axis is None:                        # Fusion: la línea central del boceto es el eje
            centrales = [c.id for c in br.boceto.curvas.values() if c.eje and c.tipo == "linea"]
            if len(centrales) > 1:
                raise error("INVALID_AXIS", f"El boceto tiene {len(centrales)} líneas centrales ({centrales}): "
                            "indicá cuál es el eje con axis.")
            axis = centrales[0] if centrales else None
    if axis is None:
        raise error("INVALID_ARGUMENTS", "Falta axis: el eje de giro (o una línea central en el boceto).")
    doc = sesion.doc
    p = {"boceto": sop.id if sop is not None else "", "perfiles": [OpRevolucion.referencia_perfil(x) for x in perfiles],
         "angulo": texto_expr(angle), "operacion": OPERACIONES[operation],
         "objetivos": _objetivos(sesion, operation, target), "invertir": reverse}
    if faces:
        from .herramientas_modificar import _refs
        p["caras"] = _refs(sesion, faces, "cara", body)[0]
    p.update(_eje_revolucion(sesion, sop, br, axis, body))
    if project_axis:
        p["proyectar_eje"] = True
    if to_object is not None:
        if direction != "one_side":
            raise error("INVALID_ARGUMENTS", "to_object gira hacia un solo lado: usá direction=one_side.")
        from .herramientas_construccion import _referencia
        p.update(extension="objeto", hasta=_referencia(
            sesion, to_object, {"vertice", "punto", "punto_boceto", "plano", "cara", "cuerpo"}, body))
    if direction == "two_sides":
        p.update(direccion="dos_lados", angulo2=texto_expr(angle if angle2 is None else angle2))
    elif direction == "symmetric":
        p["direccion"] = "simetrica"
    op = OpRevolucion(doc.nuevo_id(), nombre_nuevo(doc, "Revolución", OpRevolucion), **p)
    resultado = _agregar(sesion, op, operation != "new_body")
    resultado["profiles_used"] = [br.perfiles.index(x) for x in perfiles] if br is not None else []
    return resultado


@herramienta("sweep", "solido",
             "Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). La ruta es una cadena continua de "
             "curvas: path_curves da sus ids (get_sketch) o, vacío, se usan todas las curvas no de construcción del "
             "boceto de la ruta. El perfil tiene que estar en el plano perpendicular al inicio de la ruta. Opciones: "
             "faces (una cara plana como perfil), path_edges (aristas de un cuerpo como ruta, en lugar de path_sketch), "
             "rail_sketch y rail_curves (ruta + carril guía; rail_scale elige cómo sigue el perfil al carril: scale, "
             "stretch o none) y path_distance (fracción de la ruta que se barre, de 0 a 1). orientation=aligned mantiene "
             "el perfil con el eje align_axis como binormal (eje, arista recta, plano o cara plana). guide_surface (caras "
             "sobre las que va la ruta) es el tipo Ruta + Superficie guía: el perfil sigue la normal de la superficie. "
             "Todavía no están el barrido de un cuerpo sólido ni la selección encadenada de la ruta.",
             modifica=True)
def sweep(sesion, sketch: str | None = None, profile: Perfiles = 0, path_sketch: str | None = None,
          path_curves: list[int] | None = None,
          operation: Operacion = "new_body", orientation: Literal["perpendicular", "parallel", "aligned"] = "perpendicular",
          taper_angle: Expr = 0, twist_angle: Expr = 0, target: Cuerpos | None = None,
          faces: Cuerpos | None = None, path_edges: Cuerpos | None = None, rail_sketch: str | None = None,
          rail_curves: list[int] | None = None, rail_scale: Literal["scale", "stretch", "none"] = "scale",
          path_distance: Expr = 1, body: str | None = None, align_axis: str | dict | None = None,
          guide_surface: Cuerpos | None = None):
    """
    sketch: id o nombre del boceto con el perfil; vacío si el perfil es una cara (faces).
    profile: perfil(es): índice, lista de índices, "all", "largest", "text" o "text:<id>".
    path_sketch: id o nombre del boceto con la ruta; vacío si la ruta son aristas de un cuerpo (path_edges).
    path_curves: ids de las curvas de la ruta; vacío = todas las curvas no de construcción de path_sketch.
    operation: "new_body", "join", "cut" o "intersect".
    orientation: "perpendicular" (el perfil sigue la tangente de la ruta), "parallel" (mantiene su orientación) o "aligned" (mantiene align_axis como binormal).
    align_axis: con orientation=aligned, el eje: eje de construcción, arista recta, plano o cara plana (id o selector).
    guide_surface: caras (selector o ids de find_faces) sobre las que va la ruta: el perfil sigue su normal; no se combina con carril ni torsión.
    taper_angle: ángulo de conicidad en grados.
    twist_angle: torsión total en grados (máximo ±3600; ±1800 en rutas cerradas; la ruta no puede tener esquinas).
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    faces: cara plana (selector o id de find_faces) usada como perfil, sola o junto con los perfiles de sketch.
    path_edges: aristas de un cuerpo (selector "edges:…" o ids de find_edges, o lista) como ruta continua, en lugar de path_sketch.
    rail_sketch: id o nombre del boceto del carril guía (tipo «ruta + carril»); vacío = sin carril.
    rail_curves: ids de las curvas del carril; vacío = todas las curvas no de construcción de rail_sketch.
    rail_scale: con carril, cómo sigue el perfil al carril: "scale" (escala), "stretch" (se estira) o "none" (no cambia).
    path_distance: fracción de la ruta que se barre, mayor que 0 y hasta 1 (número o expresión); 1 = toda.
    body: cuerpo donde se evalúan los selectores de faces y path_edges; vacío = el único cuerpo.
    """
    if sketch is None and not faces:
        raise error("INVALID_ARGUMENTS", "Falta el perfil: sketch (con profile) o faces (una cara plana).")
    if path_sketch is None and not path_edges:
        raise error("INVALID_ARGUMENTS", "Falta la ruta: path_sketch (con path_curves) o path_edges (aristas de un cuerpo).")
    if path_sketch is not None and path_edges:
        raise error("INVALID_ARGUMENTS", "Pasá path_sketch o path_edges, no los dos.")
    if isinstance(path_distance, (int, float)) and not isinstance(path_distance, bool) and not 0 < path_distance <= 1:
        raise error("INVALID_ARGUMENTS", f"path_distance tiene que ser mayor que 0 y hasta 1 (recibió {path_distance}).")
    if isinstance(twist_angle, (int, float)) and not isinstance(twist_angle, bool):
        from ..nucleo.solidos_crear import TORSION_MAXIMA      # local: el núcleo se carga recién al calcular
        if not math.isfinite(twist_angle) or abs(twist_angle) > TORSION_MAXIMA:
            raise error("INVALID_ARGUMENTS", f"twist_angle admite como máximo ±{TORSION_MAXIMA:g}° "
                                             f"({TORSION_MAXIMA / 360:g} vueltas); recibió {twist_angle:g}°.")
    from .herramientas_modificar import _refs
    perfiles_refs = []
    if sketch is not None:
        sop, br = boceto_activo(sesion, sketch)
        perfiles_refs = [_ref_perfil(sop, x) for x in seleccionar_perfiles(br, sop, profile)]
    if faces:
        perfiles_refs += _refs(sesion, faces, "cara", body)[0]
    if path_edges:
        ruta = _refs(sesion, path_edges, "arista", body)[0]
    else:
        ruta = _curvas_de_boceto(sesion, path_sketch, path_curves, "la ruta")
    carril = _curvas_de_boceto(sesion, rail_sketch, rail_curves, "el carril") if rail_sketch is not None else []
    extra = {}
    if orientation == "aligned":
        if align_axis is None:
            raise error("INVALID_ARGUMENTS", "orientation=aligned necesita align_axis.")
        from .herramientas_construccion import _referencia as _ref_construccion
        extra["eje_alineado"] = _ref_construccion(sesion, align_axis, {"eje", "arista", "plano", "cara"}, body, "direccion")
    if guide_surface:
        if carril or (isinstance(twist_angle, (int, float)) and twist_angle):
            raise error("INVALID_ARGUMENTS", "guide_surface no se combina con carril ni con torsión.")
        extra["superficie_guia"] = _refs(sesion, guide_surface, "cara", body)[0]
    doc = sesion.doc
    op = OpBarrido(doc.nuevo_id(), nombre_nuevo(doc, "Barrido", OpBarrido), perfiles=perfiles_refs, ruta=ruta,
                   carril=carril, escala_carril={"scale": "escalar", "stretch": "estirar", "none": "ninguna"}[rail_scale],
                   distancia=texto_expr(path_distance), **extra,
                   orientacion={"perpendicular": "perpendicular", "parallel": "paralela", "aligned": "alineada"}[orientation],
                   conicidad=texto_expr(taper_angle), torsion=texto_expr(twist_angle),
                   operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))
    return _agregar(sesion, op, operation != "new_body")


def _curvas_de_boceto(sesion, boceto, curvas, que):
    """Referencias a curvas de un boceto: las `curvas` pedidas o, vacío, todas las que no son de construcción."""
    rop, rbr = boceto_activo(sesion, boceto)
    curvas3d = rbr.boceto.geo3d.get("curvas", {})        # las del Boceto 3D también sirven de ruta
    ids = list(curvas) if curvas else ([c.id for c in rbr.boceto.curvas.values() if not c.construccion]
                                       + [k for k, c in curvas3d.items() if not c["construccion"]])
    for cid in ids:
        if cid not in rbr.boceto.curvas and cid not in curvas3d:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{rop.nombre}» no tiene la curva {cid}.")
    if not ids:
        raise error("ENTITY_NOT_FOUND", f"El boceto de {que} «{rop.nombre}» no tiene curvas.")
    return [{"tipo": "curva_boceto", "boceto": rop.id, "curva": cid} for cid in ids]


def _condicion_borde(cond):
    """{"type", "angle", "weight"} de la API → la condición que guarda OpSolevacion."""
    if not isinstance(cond, dict) or set(cond) - {"type", "angle", "weight"}:
        raise error("INVALID_ARGUMENTS", 'La condición de borde es {"type": "free" | "direction", "angle": grados, "weight": número}.')
    tipo = cond.get("type", "free")
    if tipo not in ("free", "direction"):
        raise error("INVALID_ARGUMENTS", "type es free o direction (Tangente y Suave todavía no están).")
    angulo, peso = cond.get("angle", 90), cond.get("weight", 1)
    if isinstance(angulo, (int, float)) and not 0 < angulo < 180:
        raise error("INVALID_ARGUMENTS", "angle está entre 0 y 180 grados.")
    if isinstance(peso, (int, float)) and peso <= 0:
        raise error("INVALID_ARGUMENTS", "weight tiene que ser positivo.")
    return {"tipo": "libre" if tipo == "free" else "direccion", "angulo": texto_expr(angulo), "peso": texto_expr(peso)}


@herramienta("loft", "solido",
             "Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). "
             "profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa "
             "tramos rectos entre secciones y closed une la última con la primera. Opciones: sections (en lugar de "
             "sketches: cada sección es un perfil {\"sketch\", \"profile\"}, una cara o arista (selector o id), un "
             "vértice [x, y, z] o un punto de construcción: sirve para terminar en punta), rails (curvas guía: "
             "{\"sketch\", \"curve\"} o aristas) o center_line (una línea central), sin combinar las dos. start_condition y end_condition fijan cómo sale la "
             "superficie de la primera y la última sección: {\"type\": \"free\"} o {\"type\": \"direction\", \"angle\": "
             "grados desde el plano de la sección (90 = perpendicular), \"weight\": 1}; es una aproximación con una "
             "sección auxiliar cercana, solo en la solevación lisa (sin rails, center_line, ruled ni closed). "
             "merge_tangent_edges une las caras tangentes. Todavía no están las condiciones Tangente y Suave.",
             modifica=True)
def loft(sesion, sketches: list[str] | None = None, profiles: list[int | str] | None = None,
         operation: Operacion = "new_body", ruled: bool = False, closed: bool = False, target: Cuerpos | None = None,
         sections: list[str | dict | list[float]] | None = None, rails: list[str | dict] | None = None,
         center_line: list[str | dict] | None = None, body: str | None = None, start_condition: dict | None = None,
         end_condition: dict | None = None, merge_tangent_edges: bool = False):
    """
    sketches: ids o nombres de los bocetos, en el orden de las secciones; vacío si se da sections.
    profiles: un perfil por boceto (índice o "largest"); vacío = el perfil 0 de cada boceto.
    operation: "new_body", "join", "cut" o "intersect".
    ruled: true para tramos rectos entre secciones.
    closed: true para cerrar el sólido uniendo la última sección con la primera.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    sections: secciones en orden, en lugar de sketches: {"sketch": id, "profile": índice} (profile 0 por defecto), una cara o arista (selector o id de find_faces / find_edges), un vértice [x, y, z] o un punto de construcción (id o nombre). Mínimo dos.
    rails: curvas guía {"sketch": id, "curve": n} o aristas (selector o id), una lista por carril.
    center_line: la línea central de la solevación: {"sketch": id, "curve": n} o aristas; no se combina con rails.
    body: cuerpo donde se evalúan los selectores de sections, rails y center_line; vacío = el único cuerpo.
    start_condition: condición de borde de la primera sección: {"type": "free" | "direction", "angle": grados (90 por defecto), "weight": número (1 por defecto)}.
    end_condition: lo mismo para la última sección.
    merge_tangent_edges: true une las caras que quedan tangentes entre sí (Tangent Edges › Merge).
    """
    if rails and center_line:
        raise error("INVALID_ARGUMENTS", "Pasá rails (carriles) o center_line (línea central), no los dos.")
    if sections is None and sketches is None:
        raise error("INVALID_ARGUMENTS", "Falta indicar las secciones: sketches o sections.")
    if sections is not None and sketches is not None:
        raise error("INVALID_ARGUMENTS", "Pasá sketches o sections, no los dos.")
    from .herramientas_construccion import _referencia
    if sections is not None:
        if len(sections) < 2:
            raise error("INVALID_ARGUMENTS", "Una solevación necesita al menos dos secciones.")
        secciones = []
        for item in sections:
            if isinstance(item, dict) and "sketch" in item and set(item) <= {"sketch", "profile"}:
                sop, br = boceto_activo(sesion, item["sketch"])
                secciones.append(_ref_perfil(sop, seleccionar_perfiles(br, sop, item.get("profile", 0))[0]))
            else:
                secciones.append(_referencia(sesion, item, {"cara", "arista", "curva_boceto", "vertice", "punto",
                                                             "punto_boceto"}, body))
    else:
        if len(sketches) < 2:
            raise error("INVALID_ARGUMENTS", "Una solevación necesita al menos dos bocetos.")
        if profiles is not None and len(profiles) != len(sketches):
            raise error("INVALID_ARGUMENTS", f"profiles tiene {len(profiles)} elementos y hay {len(sketches)} bocetos.")
        secciones = []
        for i, ref in enumerate(sketches):
            sop, br = boceto_activo(sesion, ref)
            secciones.append(_ref_perfil(sop, seleccionar_perfiles(br, sop, 0 if profiles is None else profiles[i])[0]))
    guias = {k: [_referencia(sesion, r, {"arista", "curva_boceto"}, body) for r in lista]
             for k, lista in (("carriles", rails), ("linea_central", center_line)) if lista}
    for clave, cond in (("condicion_inicio", start_condition), ("condicion_fin", end_condition)):
        if cond is not None:
            guias[clave] = _condicion_borde(cond)
    guias["fusionar_tangentes"] = bool(merge_tangent_edges)
    doc = sesion.doc
    op = OpSolevacion(doc.nuevo_id(), nombre_nuevo(doc, "Solevación", OpSolevacion), secciones=secciones,
                      cerrada=closed, reglada=ruled, operacion=OPERACIONES[operation],
                      objetivos=_objetivos(sesion, operation, target), **guias)
    return _agregar(sesion, op, operation != "new_body")


# ---------------------------------------------------------------- primitivas
def _plano_primitiva(sesion, plane, body=None):
    """Referencia del plano o la cara plana sobre la que se crea una primitiva (o {} si no se pidió)."""
    if plane is None:
        return {}
    from .herramientas_construccion import _referencia
    return {"plano": _referencia(sesion, plane, {"plano", "cara"}, body, "plano")}


def _primitiva(sesion, forma, base, medidas, x, y, z, operation, target, name=None, **extra):
    doc = sesion.doc
    objetivos = _objetivos(sesion, operation, target)
    if len(objetivos) > 1:
        sesion.avisar("Las primitivas solo aceptan un cuerpo en «target»: se usan los sólidos que toca.")
    p = {"forma": forma, "x": texto_expr(x), "y": texto_expr(y), "z": texto_expr(z),
         "operacion": OPERACIONES[operation], "objetivo": objetivos[0] if len(objetivos) == 1 else ""}
    p.update({k: texto_expr(v) for k, v in medidas.items()})
    p.update(extra)
    op = OpPrimitiva(doc.nuevo_id(), nombre_nuevo(doc, base, OpPrimitiva, lambda o: o.p["forma"] == forma), **p)
    res = _agregar(sesion, op, operation != "new_body")
    if name and operation == "new_body":          # B-23: nombrar el cuerpo al crearlo (el paso sigue «Caja N»)
        creados = [c["id"] for c in res["bodies_created"]]
        doc.set_propiedad(creados, "nombre", name.strip())
        for c in res["bodies_created"]:
            c["name"] = name.strip()
    return res


@herramienta("create_box", "solido",
             "Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) "
             "es el centro de la cara de abajo con anchor=center (por defecto), o la esquina mínima con anchor=corner. Medidas y posición "
             "aceptan expresiones con parámetros. En el timeline el paso guarda x, y, z con el mismo significado "
             "(caja_centrada) y edit_feature acepta length, width y height. Con plane la crea sobre un plano o una cara "
             "plana cualquiera, también inclinada.", modifica=True)
def create_box(sesion, length: Expr, width: Expr, height: Expr, x: Expr = 0, y: Expr = 0, z: Expr = 0,
               operation: Operacion = "new_body", target: Cuerpos | None = None, name: str | None = None,
               anchor: Literal["center", "corner"] = "center", plane: str | dict | None = None,
               body: str | None = None):
    """
    length: tamaño en X (mm, positivo).
    width: tamaño en Y (mm, positivo).
    height: tamaño en Z (mm, positivo).
    x: x del centro de la base o de la esquina mínima, según anchor (mm).
    y: y del centro de la base o de la esquina mínima, según anchor (mm).
    z: z de la base (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    name: nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
    anchor: "center" sitúa (x, y, z) en el centro de la base; "corner", en la esquina mínima (crece hacia +X, +Y, +Z).
    plane: plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y la altura crece por la normal.
    body: cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
    """
    for valor, que in ((length, "length"), (width, "width"), (height, "height")):
        _numero_positivo(valor, que)
    return _primitiva(sesion, "caja", "Caja", {"ancho": length, "largo": width, "alto": height},
                      x, y, z, operation, target, name, caja_centrada=anchor == "center",
                      **_plano_primitiva(sesion, plane, body))


def _radio_o_diametro(radio, diametro, nombre_radio, nombre_diametro):
    """El radio que guarda el paso, dado el radio o el diámetro (uno solo, como el campo Diámetro del panel de la
    app). Un diámetro numérico se guarda como su mitad; con parámetros, como «(expresión) / 2»."""
    if (radio is None) == (diametro is None):
        raise error("INVALID_ARGUMENTS", f"Indicá {nombre_radio} o {nombre_diametro} (uno solo).")
    if radio is not None:
        _numero_positivo(radio, nombre_radio)
        return radio
    _numero_positivo(diametro, nombre_diametro)
    return diametro / 2 if isinstance(diametro, (int, float)) else f"({diametro.strip()}) / 2"


@herramienta("create_cylinder", "solido",
             "Crea un cilindro con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). (x, y, z) "
             "es el centro de la base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo).",
             modifica=True)
def create_cylinder(sesion, height: Expr, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                    operation: Operacion = "new_body", target: Cuerpos | None = None, diameter: Expr | None = None,
                    name: str | None = None, plane: str | dict | None = None, body: str | None = None):
    """
    height: altura en mm (positiva).
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro de la base (mm).
    y: y del centro de la base (mm).
    z: z de la base (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    diameter: diámetro en mm, en vez de radius (como el panel Cilindro de la app); el paso guarda la mitad.
    name: nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
    plane: plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el eje va por la normal.
    body: cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    _numero_positivo(height, "height")
    return _primitiva(sesion, "cilindro", "Cilindro", {"radio": radio, "alto": height}, x, y, z, operation, target,
                      name, **_plano_primitiva(sesion, plane, body))


@herramienta("create_sphere", "solido", "Crea una esfera. (x, y, z) es su centro. La medida va como radius o como "
             "diameter (uno solo).", modifica=True)
def create_sphere(sesion, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                  operation: Operacion = "new_body", target: Cuerpos | None = None, diameter: Expr | None = None,
                  name: str | None = None, plane: str | dict | None = None, body: str | None = None):
    """
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro (mm).
    y: y del centro (mm).
    z: z del centro (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    diameter: diámetro en mm, en vez de radius (como el panel Esfera de la app); el paso guarda la mitad.
    name: nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
    plane: plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el centro queda a esa altura.
    body: cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    return _primitiva(sesion, "esfera", "Esfera", {"radio": radio}, x, y, z, operation, target, name,
                      **_plano_primitiva(sesion, plane, body))


@herramienta("create_torus", "solido", "Crea un toroide con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). "
             "(x, y, z) es su centro. Medidas como radios (major_radius, minor_radius) o diámetros (major_diameter, "
             "minor_diameter), uno de cada par.", modifica=True)
def create_torus(sesion, major_radius: Expr | None = None, minor_radius: Expr | None = None, x: Expr = 0, y: Expr = 0,
                 z: Expr = 0, operation: Operacion = "new_body", target: Cuerpos | None = None,
                 major_diameter: Expr | None = None, minor_diameter: Expr | None = None, name: str | None = None,
                 plane: str | dict | None = None, body: str | None = None):
    """
    major_radius: radio mayor en mm (del centro al centro del tubo); tiene que ser mayor que minor_radius.
    minor_radius: radio menor en mm (del tubo).
    x: x del centro (mm).
    y: y del centro (mm).
    z: z del centro (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    major_diameter: diámetro del círculo que recorre el centro del tubo, en vez de major_radius (panel Toroide).
    minor_diameter: diámetro del tubo, en vez de minor_radius.
    name: nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
    plane: plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el eje va por la normal.
    body: cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
    """
    mayor = _radio_o_diametro(major_radius, major_diameter, "major_radius", "major_diameter")
    menor = _radio_o_diametro(minor_radius, minor_diameter, "minor_radius", "minor_diameter")
    return _primitiva(sesion, "toroide", "Toroide", {"radio_mayor": mayor, "radio_menor": menor},
                      x, y, z, operation, target, name, **_plano_primitiva(sesion, plane, body))


# ---------------------------------------------------------------- booleanas, simetría, patrones, movimiento
@herramienta("boolean_operation", "solido",
             "Combina cuerpos: join (unir), cut (restar las herramientas al objetivo) o intersect (quedarse con lo "
             "común). El resultado queda en el cuerpo objetivo; las herramientas se consumen salvo keep_tools.",
             modifica=True)
def boolean_operation(sesion, target: str, tools: list[str], operation: Literal["join", "cut", "intersect"] = "join",
                      keep_tools: bool = False):
    """
    target: cuerpo objetivo (id o nombre).
    tools: cuerpos herramienta (ids o nombres).
    operation: "join", "cut" o "intersect".
    keep_tools: true para conservar los cuerpos herramienta.
    """
    objetivo = sesion.cuerpo(target).id
    herramientas = _ids_cuerpos(sesion, tools)
    doc = sesion.doc
    op = OpCombinar(doc.nuevo_id(), nombre_nuevo(doc, "Combinar", OpCombinar), objetivo=objetivo,
                    herramientas=herramientas, operacion=OPERACIONES[operation], mantener=keep_tools)
    return _agregar(sesion, op, True)


@herramienta("mirror", "solido",
             "Refleja cuerpos respecto de un plano (origen, de construcción o una CARA PLANA de un cuerpo: selector o "
             "id de find_faces). Crea cuerpos nuevos, o con combine=true une cada reflejo a su cuerpo original. En vez "
             "de cuerpos puede reflejar caras (faces: cada reflejo queda como una superficie nueva), componentes "
             "(components: copias reflejadas) u operaciones del timeline (features: su herramienta se refleja y se "
             "aplica con la misma operación).", modifica=True)
def mirror(sesion, bodies: Cuerpos | None = None, plane: str = "YZ", combine: bool = False,
           plane_body: str | None = None, features: Pasos | None = None, faces: Elementos | None = None,
           components: list[str] | None = None):
    """
    bodies: cuerpo(s) a reflejar (id o nombre).
    plane: plano de simetría: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana (selector ">X" o id de find_faces).
    combine: true para unir el reflejo al cuerpo original en vez de crear un cuerpo nuevo (solo con bodies).
    plane_body: cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo.
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se refleja en vez de cuerpos. No se combina con bodies.
    faces: caras a reflejar (selector, ids de find_faces o lista): cada reflejo queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a reflejar (id o nombre): cada reflejo es un componente nuevo con copias reflejadas de sus cuerpos. No se combina con bodies, features ni faces.
    """
    objeto = _objeto_patron(sesion, bodies, features, False, combine, faces, components)
    ref = referencia_plano_o_cara(sesion, plane, plane_body)     # antes de gastar un id: si falla, el documento no cambia
    doc = sesion.doc
    op = OpSimetria(doc.nuevo_id(), nombre_nuevo(doc, "Simetría", OpSimetria), plano=ref,
                    combinar=combine and objeto["objeto"] == "cuerpos", **objeto)
    return _agregar_patron(sesion, op)


def _objeto_patron(sesion, bodies, features, lightweight, combine, faces=None, components=None):
    """objeto, cuerpos y pasos de un patrón: cuerpos (bodies), operaciones del timeline (features), caras (faces) o
    componentes (components). `ligeras` solo tiene sentido con cuerpos y sin combine (las copias unidas al original
    no quedan como instancias)."""
    from ..timeline.ops_solido import TIPOS_REPETIBLES
    ids = _ids_cuerpos(sesion, bodies)
    pasos = [sesion.paso(f) for f in _lista(features)]
    if faces is not None or components is not None:
        if ids or pasos or (faces is not None and components is not None):
            raise error("INVALID_ARGUMENTS", "Un patrón repite cuerpos (bodies), operaciones (features), caras (faces) "
                                             "o componentes (components): una sola cosa.")
        if lightweight or combine:
            raise error("INVALID_ARGUMENTS", "lightweight y combine son para cuerpos (bodies): las caras dejan "
                                             "superficies nuevas y los componentes, componentes nuevos.")
        if faces is not None:
            from .herramientas_modificar import _refs
            return {"objeto": "caras", "caras": _refs(sesion, faces, "cara", None)[0]}
        estado = sesion.doc.estado_final
        from ..timeline.ops_ensamblar import componente_por_ref
        lista = _lista(components)
        ids_comp = []
        for c in lista:
            k = componente_por_ref(estado, c)
            if k is None:
                raise error("ENTITY_NOT_FOUND", f"No hay un componente «{c}».", "get_assembly lista los componentes.")
            ids_comp.append(k)
        if not ids_comp:
            raise error("INVALID_ARGUMENTS", "Indicá al menos un componente en 'components'.")
        return {"objeto": "componentes", "componentes": ids_comp}
    if lightweight and pasos:
        raise error("INVALID_ARGUMENTS", "lightweight (copias ligeras) es para cuerpos (bodies): las operaciones "
                                         "(features) no se pueden instanciar.")
    if lightweight and combine:
        sesion.avisar("lightweight se ignora con combine: las copias se unen al original y no quedan como instancias.")
    if ids and pasos:
        raise error("INVALID_ARGUMENTS", "Un patrón repite cuerpos (bodies) u operaciones (features), no las dos cosas.")
    if not ids and not pasos:
        raise error("INVALID_ARGUMENTS", "Indicá al menos un cuerpo en 'bodies', una operación del timeline en "
                                         "'features', caras en 'faces' o componentes en 'components'.")
    doc = sesion.doc
    for op in pasos:
        if doc.indice(op.id) >= doc.marcador:
            raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» está después del marcador del timeline: no se "
                                             "puede repetir desde acá.")
        if op.TIPO not in TIPOS_REPETIBLES or (op.TIPO in ("patron", "multitransformar")
                                               and op.p.get("objeto") != "operaciones"):
            raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» ({op.ETIQUETA}) no deja una herramienta para "
                        "repetir.", "Se repiten los pasos que cortan, unen o crean con una herramienta: "
                        + ", ".join(TIPOS_REPETIBLES) + " (patrones y multitransformaciones, solo de operaciones).",
                        "Para repetir un cuerpo entero usá bodies.")
        if op.p.get("operacion") == "intersecar":
            raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» interseca: repetirlo dejaría solo lo común a todas "
                                             "las copias. Se repiten los que cortan, unen o crean un cuerpo nuevo.")
    return {"objeto": "operaciones" if pasos else "cuerpos", "cuerpos": ids, "pasos": [o.id for o in pasos]}


def _agregar_patron(sesion, op):
    return _agregar(sesion, op, op.p["objeto"] == "operaciones")


_DOC_FACES = ("    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie "
              "nuevo. No se combina con bodies, features ni components.\n")
_DOC_COMPONENTS = ("    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus "
                   "cuerpos. No se combina con bodies, features ni faces.\n")


def _dir_patron(sesion, valor, que, body=None):
    """Dirección o eje de un patrón: "x", "y", "z" (ejes del origen) o un eje de construcción, una arista recta, una
    cara plana (su normal) o un plano (selector, id o nombre)."""
    texto = str(valor).strip()
    if texto.lower() in ("x", "y", "z"):
        return {"tipo": "eje", "id": texto.upper()}
    from .herramientas_construccion import _referencia
    return _referencia(sesion, valor, {"eje", "arista", "curva_boceto", "cara", "plano"}, body, "direccion")


def _suprimir(suppress, limite, simetrico=False, que="suppress"):
    """Índices de copia a suprimir (0 = el original no se puede suprimir): enteros de 1 a limite − 1; con simetría
    también sus opuestos (−1 es la primera copia hacia el otro lado)."""
    if not suppress:
        return []
    if limite <= 1:
        raise error("INVALID_ARGUMENTS", f"{que}: no hay copias para suprimir (con una sola instancia solo existe el original).")
    for i in suppress:
        if (isinstance(i, bool) or not isinstance(i, int) or i == 0 or abs(i) >= limite
                or (i < 0 and not simetrico)):
            raise error("INVALID_ARGUMENTS", f"{que}: cada índice es un entero de 1 a {limite - 1}"
                        f"{' (o negativo, hacia el otro lado)' if simetrico else ''}; el original, 0, no se suprime: "
                        f"llegó {i!r}.")
    return sorted(set(suppress))


@herramienta("realize_copies", "solido",
             "Vuelve copias de verdad las copias ligeras (instancias) de un patrón o de Mover/copiar («Realizar "
             "instancias» de Plasticity): cada copia pasa a tener su propia geometría y deja de seguir a la original. "
             "Las posiciones y los volúmenes no cambian. Falla con INVALID_ARGUMENTS si el paso no tiene copias "
             "ligeras (lightweight=true en el patrón o en move_body).", modifica=True)
def realize_copies(sesion, feature: str):
    """
    feature: id (p. ej. "op3") o nombre del paso (patrón, multitransformación o mover) con copias ligeras.
    """
    op = sesion.paso(feature)
    clave = "ligera" if op.TIPO == "mover" else "ligeras"
    sin_copias = op.p.get("combinar") if op.TIPO != "mover" else not op.p.get("copiar")   # unidas al original / sin copia
    if clave not in op.PARAMS or not op.p.get(clave) or sin_copias:
        raise error("INVALID_ARGUMENTS", f"El paso «{op.nombre}» ({op.TIPO}) no tiene copias ligeras.",
                    "Las crean los patrones y la multitransformación con lightweight=true, y move_body con "
                    "copy=true y lightweight=true.")
    nueva = op.copia()
    nueva.p[clave] = False
    antes = _foto(sesion)
    sesion.doc.reemplazar(op.id, nueva)
    resultado = _informe(sesion, nueva, antes)
    propios = f"{nueva.id}.c"      # los cuerpos de otro paso que siguen a estos (otro patrón) cambian de forma pero no son copias de acá
    resultado["realized"] = sum(1 for c in resultado["bodies_modified"] + resultado["bodies_created"]
                                if c["id"].startswith(propios))
    return resultado


@herramienta("rectangular_pattern", "solido",
             "Patrón rectangular de cuerpos (bodies) o de operaciones del timeline (features: un agujero, una "
             "extrusión que corta… se repiten sobre la pieza, como el patrón de features de Fusion): copias en una o "
             "dos direcciones (ejes del origen), con la separación entre copias consecutivas. Con bodies las copias "
             "son cuerpos nuevos (o se unen al original con combine). Cantidades incluyen el original.", modifica=True)
def rectangular_pattern(sesion, bodies: Cuerpos | None = None, x_count: int = 1, x_spacing: Expr = "10 mm",
                        y_count: int = 1, y_spacing: Expr = "10 mm", axis1: str = "x",
                        axis2: str = "y", combine: bool = False, features: Pasos | None = None,
                        faces: Elementos | None = None, components: list[str] | None = None,
                        lightweight: bool = False, distribution: Literal["spacing", "extent"] = "spacing",
                        symmetric: bool = False, suppress: list[int] | None = None, body: str | None = None):
    """
    bodies: cuerpo(s) a repetir (id o nombre).
    x_count: cantidad de instancias en la dirección 1, original incluido (1 = sin copias; x_count × y_count ≤ 10.000).
    x_spacing: separación entre instancias consecutivas en la dirección 1 (mm o expresión). Se guarda como d1 con distribucion="espaciado": edit_feature d1 sigue siendo la separación.
    y_count: cantidad de instancias en la dirección 2, original incluido (x_count × y_count ≤ 10.000).
    y_spacing: separación entre instancias consecutivas en la dirección 2 (se guarda como d2).
    axis1: dirección 1: "x", "y", "z", o un eje de construcción (id o nombre), una arista recta, una cara plana (su normal) o un plano (selector o id).
    axis2: dirección 2 (mismas formas que axis1).
    distribution: "spacing" (x_spacing e y_spacing son la separación entre copias consecutivas) o "extent" (son la distancia TOTAL de la primera a la última).
    symmetric: true reparte las copias a los dos lados del original.
    suppress: copias a suprimir de la primera fila, por su posición en la dirección 1 (1 a x_count−1; 0 es el original; con symmetric también negativos, hacia el otro lado).
    body: cuerpo donde se evalúan los selectores de axis1 y axis2; vacío = el único cuerpo.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos: su herramienta (el agujero, la extrusión que corta o une…) se copia y se aplica con la misma operación a los mismos cuerpos, como el patrón de features de Fusion. No se combina con bodies.
    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
    lightweight: true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
    """
    objeto = _objeto_patron(sesion, bodies, features, lightweight, combine, faces, components)
    if x_count < 1 or y_count < 1:
        raise error("INVALID_ARGUMENTS", "x_count e y_count tienen que ser 1 o más.")
    if x_count == 1 and y_count == 1:
        raise error("INVALID_ARGUMENTS", "Con x_count = 1 e y_count = 1 el patrón no crea copias.")
    if y_count > 1 and str(axis1).strip().lower() == str(axis2).strip().lower():
        raise error("INVALID_ARGUMENTS", "axis1 y axis2 tienen que ser direcciones distintas.")
    k = 2 if symmetric else 1
    total = (k * x_count - k + 1) * (k * y_count - k + 1)
    _exigir_instancias(total, "x_count × y_count")
    dir1 = _dir_patron(sesion, axis1, "axis1", body)
    dir2 = _dir_patron(sesion, axis2, "axis2", body) if y_count > 1 else None
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón rectangular", OpPatron,
                                               lambda o: o.p["forma_patron"] == "rectangular"),
                  forma_patron="rectangular", dir1=dir1, n1=x_count, d1=texto_expr(x_spacing), dir2=dir2,
                  n2=y_count, d2=texto_expr(y_spacing),
                  distribucion="espaciado" if distribution == "spacing" else "extension", simetrico=bool(symmetric),
                  suprimir=_suprimir(suppress, x_count, symmetric), combinar=combine, ligeras=lightweight and not combine,
                  **objeto)
    return _agregar_patron(sesion, op)


@herramienta("circular_pattern", "solido",
             "Patrón circular de cuerpos (bodies) o de operaciones del timeline (features) alrededor de un eje del "
             "origen (x, y o z). Con 360° las copias se reparten en toda la vuelta; con menos, entre el original y el "
             "ángulo total. count incluye el original.", modifica=True)
def circular_pattern(sesion, count: int, bodies: Cuerpos | None = None, axis: str = "z",
                     total_angle: Expr = 360, combine: bool = False, features: Pasos | None = None,
                     faces: Elementos | None = None, components: list[str] | None = None,
                     lightweight: bool = False, distribution: Literal["extent", "spacing"] = "extent",
                     symmetric: bool = False, suppress: list[int] | None = None, body: str | None = None):
    """
    count: cantidad de instancias, original incluido (2 a 10.000).
    bodies: cuerpo(s) a repetir (id o nombre).
    axis: eje de giro: "x", "y", "z", o un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id).
    total_angle: ángulo en grados (número o expresión): con distribution=extent, el total (360 = vuelta completa); con spacing, el ángulo entre copias consecutivas.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
    lightweight: true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
    distribution: "extent" (total_angle es el ángulo TOTAL entre la primera y la última copia) o "spacing" (es el ángulo entre copias consecutivas).
    symmetric: true reparte las copias a los dos lados del original.
    suppress: copias a suprimir por su posición (1 a count−1; 0 es el original; con symmetric también negativos, hacia el otro lado).
    body: cuerpo donde se evalúan los selectores de axis; vacío = el único cuerpo.
    """
    objeto = _objeto_patron(sesion, bodies, features, lightweight, combine, faces, components)
    if count < 2:
        raise error("INVALID_ARGUMENTS", "count tiene que ser 2 o más (el original cuenta).")
    total = 2 * count - 1 if symmetric else count
    _exigir_instancias(total, "count")
    eje = _dir_patron(sesion, axis, "axis", body)
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón circular", OpPatron,
                                               lambda o: o.p["forma_patron"] == "circular"),
                  forma_patron="circular", eje=eje, n=count, angulo=texto_expr(total_angle),
                  distribucion="extension" if distribution == "extent" else "espaciado", simetrico=bool(symmetric),
                  suprimir=_suprimir(suppress, count, symmetric), combinar=combine, ligeras=lightweight and not combine,
                  **objeto)
    return _agregar_patron(sesion, op)


def _xyz_api(valores, que):
    if not isinstance(valores, (list, tuple)) or len(valores) != 3:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser [x, y, z] (3 valores): recibió {valores!r}.")
    return [texto_expr(v) for v in valores]


def _params_puntos(sesion, points, sketch, reference, point_refs=None, reference_point=None, body=None):
    """Parámetros del Patrón en puntos: coordenadas (points), vértices o puntos de construcción (point_refs), los
    puntos sueltos de un boceto (sketch) y la referencia (reference [x, y, z] o reference_point asociativo)."""
    from .herramientas_construccion import _PUNTO, _referencia
    coordenadas = [_xyz_api(p, f"points[{i}]") for i, p in enumerate(points or [])]
    puntos = [_referencia(sesion, p, _PUNTO, body) for p in point_refs or []]
    if sketch is not None:
        sop, br = boceto_activo(sesion, sketch)
        en_curvas = {i for c in br.boceto.curvas.values() for i in c.puntos()}
        if not [i for i in br.boceto.puntos if i not in en_curvas]:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene puntos sueltos (puntos que no son de "
                                            "ninguna curva).", "Dibujalos con draw_point.")
        puntos.append({"tipo": "boceto", "boceto": sop.id})
    if not coordenadas and not puntos:
        raise error("INVALID_ARGUMENTS", "Indicá los puntos: coordenadas en 'points', vértices o puntos de construcción "
                                         "en 'point_refs' y/o un boceto con puntos sueltos en 'sketch'.")
    if reference is not None and reference_point is not None:
        raise error("INVALID_ARGUMENTS", "Pasá reference o reference_point, no los dos.")
    salida = {"forma_patron": "puntos", "coordenadas": coordenadas, "puntos": puntos,
              "referencia_xyz": _xyz_api(reference, "reference") if reference is not None else []}
    if reference_point is not None:
        salida["referencia"] = _referencia(sesion, reference_point, _PUNTO | {"punto_boceto"}, body)
    return salida


ESPACIADOS = {"extent": "extension", "spacing": "espaciado"}
ORIENTACIONES = {"identical": "identica", "path_direction": "direccion_ruta"}


def _params_ruta(sesion, path_sketch, path_curves, count, distance, spacing_mode, start, orientation, twist, symmetric,
                 path_edges=None, body=None):
    """Parámetros del Patrón en ruta (curvas de un boceto, como la ruta de sweep, o aristas de un cuerpo)."""
    if count < 2:
        raise error("INVALID_ARGUMENTS", "count tiene que ser 2 o más (el original cuenta).")
    if distance is None:
        raise error("INVALID_ARGUMENTS", "Falta distance (el largo total o la separación entre copias).")
    _exigir_instancias(2 * count - 1 if symmetric else count, "count")
    if path_edges:
        if path_sketch is not None:
            raise error("INVALID_ARGUMENTS", "Pasá path_sketch o path_edges, no los dos.")
        from .herramientas_modificar import _refs
        ruta = _refs(sesion, path_edges, "arista", body)[0]
    elif path_sketch is None:
        raise error("INVALID_ARGUMENTS", "Falta la ruta: path_sketch (con path_curves) o path_edges (aristas de un cuerpo).")
    else:
        ruta = _curvas_de_boceto(sesion, path_sketch, path_curves, "la ruta")
    if spacing_mode not in ESPACIADOS or orientation not in ORIENTACIONES:
        raise error("INVALID_ARGUMENTS", f"spacing_mode: {', '.join(ESPACIADOS)}; orientation: "
                                         f"{', '.join(ORIENTACIONES)}.")
    return {"forma_patron": "ruta", "ruta": ruta,
            "n1": count, "d1": texto_expr(distance), "distribucion": ESPACIADOS[spacing_mode],
            "inicio": texto_expr(start), "orientacion": ORIENTACIONES[orientation], "giro": texto_expr(twist),
            "simetrico": bool(symmetric)}


@herramienta("point_pattern", "solido",
             "Patrón en puntos (Point Pattern de FreeCAD; en Fusion, los agujeros en varios puntos de boceto): copia "
             "cuerpos (bodies) —o repite operaciones del timeline (features), p. ej. un agujero o una extrusión que "
             "corta— en cada punto. Los puntos son coordenadas (points) y/o todos los puntos sueltos de un boceto "
             "(sketch). Cada copia lleva el punto de referencia (reference; por defecto el origen) a uno de los "
             "puntos: para repetir un agujero, reference es el punto donde está el agujero. Un punto igual a la "
             "referencia no repite la copia.", modifica=True)
def point_pattern(sesion, bodies: Cuerpos | None = None, features: Pasos | None = None,
                  faces: Elementos | None = None, components: list[str] | None = None,
                  points: list[list[Expr]] | None = None, sketch: str | None = None,
                  reference: list[Expr] | None = None, combine: bool = False, lightweight: bool = False,
                  point_refs: list[str | dict | list[float]] | None = None,
                  reference_point: str | dict | list[float] | None = None, suppress: list[int] | None = None,
                  body: str | None = None):
    """
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
    points: puntos [[x, y, z], …] en mm (números o expresiones) donde va cada copia.
    sketch: id o nombre de un boceto: se usan todos sus puntos sueltos (los que no son de ninguna curva) y siguen al boceto si se edita.
    reference: punto [x, y, z] que se lleva a cada punto; vacío = el origen [0, 0, 0].
    point_refs: puntos asociativos: vértices [x, y, z] del modelo, puntos de construcción (id o nombre) o {"sketch", "point"}; siguen al modelo si cambia.
    reference_point: punto de referencia asociativo (vértice [x, y, z], punto de construcción o de boceto) en lugar de reference.
    suppress: índices de las copias a suprimir (1 a N−1; 0 es el original), en este orden de puntos: primero los de point_refs y sketch y al final los de points.
    body: cuerpo donde se buscan los vértices de point_refs y reference_point; vacío = todos.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    lightweight: true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
    """
    objeto = _objeto_patron(sesion, bodies, features, lightweight, combine, faces, components)
    params = _params_puntos(sesion, points, sketch, reference, point_refs, reference_point, body)
    cantidad = len(params["coordenadas"]) + len(params["puntos"]) + 1
    _exigir_instancias(cantidad, "points")
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón en puntos", OpPatron,
                                               lambda o: o.p["forma_patron"] == "puntos"),
                  combinar=combine, suprimir=_suprimir(suppress, 10 ** 6 if sketch is not None else cantidad),
                  **params, **objeto, ligeras=lightweight and not combine)
    return _agregar_patron(sesion, op)


@herramienta("path_pattern", "solido",
             "Patrón en ruta (Pattern on Path de Fusion; con twist, el Twisted Path Array de FreeCAD): copias de "
             "cuerpos (bodies) —o de operaciones del timeline (features)— a lo largo de curvas de un boceto. count "
             "incluye el original. distance es el largo TOTAL de la primera a la última (spacing_mode=\"extent\") o la "
             "separación entre copias (\"spacing\"). start ubica el original sobre la ruta (0 a 1). "
             "orientation=\"path_direction\" gira cada copia con la ruta; twist además la gira alrededor de la ruta, "
             "de a poco, hasta ese ángulo total en la última.", modifica=True)
def path_pattern(sesion, path_sketch: str | None = None, count: int = 0, distance: Expr | None = None,
                 bodies: Cuerpos | None = None,
                 features: Pasos | None = None, faces: Elementos | None = None,
                 components: list[str] | None = None, path_curves: list[int] | None = None,
                 spacing_mode: Literal["extent", "spacing"] = "extent", start: Expr = 0,
                 orientation: Literal["identical", "path_direction"] = "identical", twist: Expr = 0,
                 symmetric: bool = False, combine: bool = False, lightweight: bool = False,
                 path_edges: Cuerpos | None = None, suppress: list[int] | None = None, body: str | None = None):
    """
    path_sketch: id o nombre del boceto con la ruta; vacío si la ruta son aristas de un cuerpo (path_edges).
    count: cantidad de instancias, original incluido (2 a 10.000).
    distance: largo total (extent) o separación entre copias (spacing), en mm o expresión.
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
    path_curves: ids de las curvas de la ruta (get_sketch); vacío = todas las curvas no de construcción del boceto.
    spacing_mode: "extent" (distance es el largo total) o "spacing" (distance es la separación).
    start: dónde está el original sobre la ruta, de 0 (inicio) a 1 (fin).
    orientation: "identical" (las copias solo se trasladan) o "path_direction" (giran con la tangente de la ruta).
    twist: giro total alrededor de la ruta en grados (número o expresión): la copia k gira twist · k / (count − 1).
    path_edges: aristas de un cuerpo (selector "edges:…" o ids de find_edges, o lista) como ruta continua, en lugar de path_sketch.
    suppress: copias a suprimir por su posición sobre la ruta (1 a count−1; 0 es el original; con symmetric también negativos).
    body: cuerpo donde se evalúan los selectores de path_edges; vacío = el único cuerpo.
    symmetric: true para repartir count copias hacia cada lado del original.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    lightweight: true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
    """
    objeto = _objeto_patron(sesion, bodies, features, lightweight, combine, faces, components)
    params = _params_ruta(sesion, path_sketch, path_curves, count, distance, spacing_mode, start, orientation, twist,
                          symmetric, path_edges, body)
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón en ruta", OpPatron, lambda o: o.p["forma_patron"] == "ruta"),
                  combinar=combine, suprimir=_suprimir(suppress, count, symmetric), **params, **objeto,
                  ligeras=lightweight and not combine)
    return _agregar_patron(sesion, op)


_CLAVES_TRANSFORMACION = {
    "rectangular": {"type", "axis", "count", "spacing", "axis2", "count2", "spacing2", "symmetric", "body"},
    "circular": {"type", "axis", "count", "total_angle", "symmetric", "body"},
    "mirror": {"type", "plane", "body"},
    "points": {"type", "points", "sketch", "reference", "point_refs", "reference_point", "body"},
    "path": {"type", "path_sketch", "path_curves", "count", "distance", "spacing_mode", "start", "orientation",
             "twist", "symmetric", "path_edges", "body"},
}


def _entero_api(valor, que, minimo=1):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or int(valor) != valor or valor < minimo:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser un entero ≥ {minimo}: recibió {valor!r}.")
    return int(valor)


def _transformacion_api(sesion, t, i):
    """Una transformación de multi_transform (claves en inglés) → dict de OpMultitransformar. Devuelve (dict,
    cantidad de instancias que aporta, el original incluido)."""
    que = f"transforms[{i}]"
    if not isinstance(t, dict) or t.get("type") not in _CLAVES_TRANSFORMACION:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser un dict con \"type\": "
                                         f"{', '.join(_CLAVES_TRANSFORMACION)}.")
    tipo = t["type"]
    sobran = set(t) - _CLAVES_TRANSFORMACION[tipo]
    if sobran:
        raise error("INVALID_ARGUMENTS", f"{que} ({tipo}) no acepta {', '.join(sorted(sobran))}.",
                    f"Claves válidas: {', '.join(sorted(_CLAVES_TRANSFORMACION[tipo]))}.")
    if tipo == "rectangular":
        n1 = _entero_api(t.get("count", 2), f"{que}.count")
        n2 = _entero_api(t.get("count2", 1), f"{que}.count2")
        dir2 = _dir_patron(sesion, t["axis2"], f"{que}.axis2", t.get("body")) if n2 > 1 and "axis2" in t else None
        d = {"tipo": "rectangular", "dir1": _dir_patron(sesion, t.get("axis", "x"), f"{que}.axis", t.get("body")),
             "n1": n1,
             "d1": texto_expr(t.get("spacing", 10)), "dir2": dir2, "n2": n2, "d2": texto_expr(t.get("spacing2", 10)),
             "distribucion": "espaciado", "simetrico": bool(t.get("symmetric", False))}
        if n2 > 1 and "axis2" not in t:
            raise error("INVALID_ARGUMENTS", f"{que}: con count2 > 1 falta axis2.")
        k = 2 if d["simetrico"] else 1
        return d, (k * n1 - k + 1) * (k * n2 - k + 1)
    if tipo == "circular":
        n = _entero_api(t.get("count", 2), f"{que}.count", 2)
        d = {"tipo": "circular", "eje": _dir_patron(sesion, t.get("axis", "z"), f"{que}.axis", t.get("body")), "n": n,
             "angulo": texto_expr(t.get("total_angle", 360)), "distribucion": "extension",
             "simetrico": bool(t.get("symmetric", False))}
        return d, 2 * n - 1 if d["simetrico"] else n
    if tipo == "mirror":
        return {"tipo": "simetria", "plano": referencia_plano_o_cara(sesion, t.get("plane", "YZ"), t.get("body"))}, 2
    if tipo == "points":
        d = _params_puntos(sesion, t.get("points"), t.get("sketch"), t.get("reference"), t.get("point_refs"),
                           t.get("reference_point"), t.get("body"))
        d["tipo"] = d.pop("forma_patron")
        return d, len(d["coordenadas"]) + len(d["puntos"]) + 1
    d = _params_ruta(sesion, t.get("path_sketch"), t.get("path_curves"), _entero_api(t.get("count"), f"{que}.count", 2),
                     t.get("distance", 10), t.get("spacing_mode", "extent"), t.get("start", 0),
                     t.get("orientation", "identical"), t.get("twist", 0), bool(t.get("symmetric", False)),
                     t.get("path_edges"), t.get("body"))
    d["tipo"] = d.pop("forma_patron")
    return d, d["n1"]


@herramienta("multi_transform", "solido",
             "Multitransformación (MultiTransform de FreeCAD): patrón + simetría + patrón… en UN paso. transforms es "
             "una lista ordenada y cada transformación se aplica a TODAS las instancias de las anteriores (rectangular "
             "de 3 + mirror = 6). Tipos: {\"type\": \"rectangular\", \"axis\": \"x\", \"count\": 3, \"spacing\": 20} "
             "(y axis2, count2, spacing2, symmetric), {\"type\": \"circular\", \"axis\": \"z\", \"count\": 6, "
             "\"total_angle\": 360}, {\"type\": \"mirror\", \"plane\": \"YZ\"}, {\"type\": \"points\", \"points\": "
             "[[x, y, z]], \"sketch\": …, \"reference\": [x, y, z]} y {\"type\": \"path\", \"path_sketch\": …, "
             "\"count\": 4, \"distance\": 60, \"twist\": 90} (las mismas opciones que path_pattern). Repite cuerpos "
             "(bodies) u operaciones del timeline (features).", modifica=True)
def multi_transform(sesion, transforms: list[dict], bodies: Cuerpos | None = None, features: Pasos | None = None,
                    combine: bool = False, lightweight: bool = False, faces: Elementos | None = None,
                    components: list[str] | None = None):
    """
    transforms: lista ordenada de transformaciones (dicts con "type": rectangular, circular, mirror, points o path; ver la descripción).
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    faces: caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
    components: componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    lightweight: true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
    """
    objeto = _objeto_patron(sesion, bodies, features, lightweight, combine, faces, components)
    if not transforms:
        raise error("INVALID_ARGUMENTS", "transforms necesita al menos una transformación.")
    lista, total = [], 1
    for i, t in enumerate(transforms):
        d, n = _transformacion_api(sesion, t, i)
        lista.append(d)
        total *= n
    _exigir_instancias(total, "el producto de las transformaciones")
    if lightweight and any(d["tipo"] == "simetria" for d in lista):
        sesion.avisar("Las copias de una simetría son copias de verdad (un espejo no es un movimiento rígido): solo las "
                      "demás transformaciones quedan como copias ligeras.")
    doc = sesion.doc
    op = OpMultitransformar(doc.nuevo_id(), nombre_nuevo(doc, "Multitransformación", OpMultitransformar),
                            transformaciones=lista, combinar=combine, **objeto, ligeras=lightweight and not combine)
    return _agregar_patron(sesion, op)


def _centro(cuerpos, exacto=False):
    """Centro de un grupo de cuerpos como el pivote por defecto de Mover: promedio de los centros de sus cajas
    (redondeado a 1e-4 mm para informar; `exacto` sin redondear, para calcular)."""
    centros = []
    for c in cuerpos:
        caja = c.forma.caja() if getattr(c, "tipo", "solido") == "malla" else geo.caja_envolvente(c.forma)
        if caja:
            centros.append([(a + b) / 2 for a, b in zip(caja[0], caja[1], strict=True)])
    if not centros:
        return None
    return [(float if exacto else _r)(sum(v) / len(centros)) for v in zip(*centros, strict=True)]


def _menos(expr, valor):
    """Expresión «expr − valor» (valor en mm, ya calculado): un número si expr lo es; si no, texto que conserva los
    parámetros de expr («(alto_eje) - (15.0 mm)»)."""
    if isinstance(expr, (int, float)):
        return repr(round(float(expr) - valor, 6) + 0.0)
    if abs(valor) < 1e-9:
        return expr.strip()
    return f"({expr.strip()}) - ({round(valor, 6) + 0.0!r} mm)"


@herramienta("drop_to_plane", "solido",
             "Apoya cuerpos en el plano del piso (Z = 0): los baja o sube en Z hasta que lo más bajo toque Z = 0. "
             "No es 'ground_component' (eso fija una pieza del ensamble). Sin body, apoya todos los cuerpos. El paso "
             "se recalcula con el modelo. El resultado trae z_min.before y z_min.after.", modifica=True)
def drop_to_plane(sesion, body: Cuerpos | None = None, keep_relative: bool = True):
    """
    body: cuerpo(s) a apoyar (id o nombre); vacío = todos los cuerpos del diseño.
    keep_relative: true mueve todo junto (conserva las posiciones relativas); false apoya cada cuerpo por su cuenta.
    """
    ids = _ids_cuerpos(sesion, body) if body else []
    doc = sesion.doc
    estado = doc.estado_final
    objetivo = ids or list(estado.cuerpos)
    if not objetivo:
        raise error("INVALID_ARGUMENTS", "No hay cuerpos para apoyar en el plano.")

    def z_min(cuerpos):
        zs = [OpApoyar._z_min(c) for c in cuerpos]
        zs = [z for z in zs if z is not None]
        return round(min(zs), 6) if zs else None
    antes = z_min([estado.cuerpos[i] for i in objetivo if i in estado.cuerpos])
    op = OpApoyar(doc.nuevo_id(), nombre_nuevo(doc, "Apoyar en el plano", OpApoyar), cuerpos=ids,
                  juntos=bool(keep_relative))
    foto = _foto(sesion)
    doc.agregar(op)
    resultado = _informe(sesion, op, foto)
    final = sesion.doc.estado_final.cuerpos
    resultado["z_min"] = {"before": antes, "after": z_min([final[i] for i in objetivo if i in final])}
    return resultado


@herramienta("move_body", "solido",
             "Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] "
             "grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA "
             "a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate "
             "[0, 0, 15] queda en z = 17). Para llevarlo a una posición absoluta usá position = [x, y, z]: el centro de "
             "la caja de los cuerpos (después del giro) queda ahí. pivot='center' es el promedio de los centros de las "
             "cajas de los cuerpos y se RECALCULA con la geometría (si la pieza es asimétrica o se edita, el giro "
             "cambia de lugar); pivot='origin' gira alrededor del origen y da un giro estable. El resultado trae "
             "center.before y center.after. Otros tipos de movimiento (type): translate con direction (un eje, arista "
             "recta, cara plana o plano) y distance; rotate alrededor de axis (eje de construcción o arista recta) un "
             "angle; point_to_point lleva origin_point (vértice [x, y, z] o punto de construcción) a "
             "destination_point. pivot_point fija el pivote del giro libre en un vértice o punto.", modifica=True)
def move_body(sesion, body: Cuerpos, translate: list[Expr] | None = None, rotate: list[Expr] | None = None,
              pivot: Literal["center", "origin"] = "center", copy: bool = False, position: list[Expr] | None = None,
              lightweight: bool = False, type: Literal["free", "translate", "rotate", "point_to_point"] = "free",
              direction: str | dict | None = None, distance: Expr = 10, axis: str | dict | None = None,
              angle: Expr = 90, origin_point: str | dict | list[float] | None = None,
              destination_point: str | dict | list[float] | None = None,
              pivot_point: str | dict | list[float] | None = None, ref_body: str | None = None):
    """
    body: cuerpo(s) a mover (id o nombre).
    translate: DESPLAZAMIENTO [dx, dy, dz] en mm que se suma a la posición actual (números o expresiones); vacío = sin desplazamiento.
    rotate: giro [rx, ry, rz] en grados (números o expresiones); vacío = sin giro.
    pivot: centro del giro: "center" (centro de las cajas de los cuerpos, se recalcula) u "origin" (origen, estable).
    copy: true para dejar el original y crear cuerpos nuevos con el movimiento.
    position: posición ABSOLUTA [x, y, z] en mm (números o expresiones) del centro de la caja de los cuerpos; no se
        combina con translate. El paso guarda el desplazamiento que hace falta ahora (position − centro, con los
        parámetros de position): si después cambia la forma de la pieza, el centro se corre con ella.
    lightweight: true (con copy=true) deja una copia ligera: comparte la geometría del original y editar el original la cambia; realize_copies la vuelve copia de verdad.
    type: "free" (translate/rotate/position, por defecto), "translate" (con direction y distance, o con translate si no hay direction), "rotate" (alrededor de axis un angle) o "point_to_point".
    direction: type=translate: eje de construcción, arista recta, cara plana o plano (selector, id o nombre); se mueve distance a lo largo de él.
    distance: type=translate con direction: desplazamiento en mm (número o expresión).
    axis: type=rotate: eje de construcción (id o nombre), arista recta o línea de boceto {"sketch", "curve"}.
    angle: type=rotate: ángulo en grados (número o expresión).
    origin_point: type=point_to_point: punto de partida: vértice [x, y, z], punto de construcción (id o nombre) o {"sketch", "point"}.
    destination_point: type=point_to_point: punto de llegada (mismas formas que origin_point).
    pivot_point: type=free: pivote del giro en un vértice [x, y, z], punto de construcción o {"sketch", "point"}; reemplaza a pivot.
    ref_body: cuerpo donde se evalúan los selectores de direction, axis y los puntos; vacío = el único cuerpo.
    """
    if type != "free" and (rotate is not None or position is not None):
        raise error("INVALID_ARGUMENTS", f"type={type} no se combina con rotate ni position: son del movimiento libre.")
    if lightweight and not copy:
        raise error("INVALID_ARGUMENTS", "lightweight (copia ligera) necesita copy=true: sin copia no hay "
                                         "qué compartir.")
    ids = _ids_cuerpos(sesion, body)
    if not ids:
        raise error("INVALID_ARGUMENTS", "Indicá al menos un cuerpo en 'body'.")
    for valor, que in ((translate, "translate"), (rotate, "rotate"), (position, "position")):
        if valor is not None and len(valor) != 3:
            raise error("INVALID_ARGUMENTS", f"{que} tiene que ser [x, y, z] (3 valores).")
    if translate is not None and position is not None:
        raise error("INVALID_ARGUMENTS", "translate (desplazamiento) y position (posición absoluta) no se combinan: "
                    "usá uno de los dos.")
    t, g = translate or [0, 0, 0], rotate or [0, 0, 0]
    doc = sesion.doc
    from .herramientas_construccion import _PUNTO, _referencia
    nuevos = {}
    if type == "translate":
        nuevos = dict(tipo="traslacion")
        if direction is not None:
            nuevos.update(direccion=_referencia(sesion, direction, {"eje", "arista", "cara", "plano"}, ref_body,
                                                "direccion"), distancia=texto_expr(distance))
    elif type == "rotate":
        if axis is None:
            raise error("INVALID_ARGUMENTS", "type=rotate necesita axis (un eje de construcción o una arista recta).")
        nuevos = dict(tipo="rotacion", eje=_referencia(sesion, axis, {"eje", "arista", "curva_boceto"}, ref_body, "eje"),
                      angulo=texto_expr(angle))
    elif type == "point_to_point":
        if origin_point is None or destination_point is None:
            raise error("INVALID_ARGUMENTS", "type=point_to_point necesita origin_point y destination_point.")
        nuevos = dict(tipo="punto_a_punto", origen=_referencia(sesion, origin_point, _PUNTO, ref_body),
                      destino=_referencia(sesion, destination_point, _PUNTO, ref_body))
    pivote = {"tipo": "punto", "id": "O"} if pivot == "origin" else None
    if pivot_point is not None and type == "free":
        pivote = _referencia(sesion, pivot_point, _PUNTO, ref_body)
    op = OpMover(doc.nuevo_id(), nombre_nuevo(doc, "Mover", OpMover), cuerpos=ids, tipo="libre",
                 dx=texto_expr(t[0]), dy=texto_expr(t[1]), dz=texto_expr(t[2]),
                 rx=texto_expr(g[0]), ry=texto_expr(g[1]), rz=texto_expr(g[2]),
                 pivote=pivote, copiar=copy, ligera=lightweight)
    for k, v in nuevos.items():
        op.p[k] = v
    cuerpos = sesion.doc.estado_final.cuerpos
    antes = _centro([cuerpos[i] for i in ids])
    foto = _foto(sesion)
    doc.agregar(op)
    if position is not None:
        movidos = [c for c in doc.estado_final.cuerpos if c not in foto] if copy else ids
        girado = _centro([doc.estado_final.cuerpos[i] for i in movidos if i in doc.estado_final.cuerpos], exacto=True)
        if girado is None:
            raise error("INVALID_ARGUMENTS", "Los cuerpos no tienen caja (están vacíos): no hay centro que llevar a "
                        "position.")
        nueva = op.copia()
        nueva.p.update({k: _menos(texto_expr(v) if isinstance(v, str) else v, c)
                        for k, v, c in zip(("dx", "dy", "dz"), position, girado, strict=True)})
        doc.reemplazar(op.id, nueva)
        op = nueva
    resultado = _informe(sesion, op, foto)
    cuerpos = sesion.doc.estado_final.cuerpos
    movidos = [b["id"] for b in resultado["bodies_created"]] if copy else ids
    resultado["center"] = {"before": antes, "after": _centro([cuerpos[i] for i in movidos if i in cuerpos])}
    return resultado

