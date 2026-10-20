"""Creación avanzada de sólidos y alineación/escala, sin depender de la interfaz."""
from typing import Literal

from ..nucleo import referencias
from ..timeline import entidades as ent
from ..timeline.ops_modificar import OpAlinear, OpEscala
from ..timeline.ops_solido import (OpBobina, OpLabio, OpNervio, OpRed, OpRellenoContorno,
                                   OpRepujado, OpSaliente, OpSolidoEnvolvente, OpTuberia)
from ..timeline.ops_superficie import OpEngrosar
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_boceto import boceto_activo, nombre_nuevo, seleccionar_perfiles, texto_expr
from .herramientas_solido import (OPERACIONES, Cuerpos, Operacion, Perfiles, _agregar,
                                  _ids_cuerpos, _numero_positivo, _objetivos, _ref_perfil)
from .registro import Expr, herramienta

Referencia = str | dict
Elementos = str | list[str]
_GEOMETRIA = ('Plano XY/XZ/YZ, eje X/Y/Z, punto O, nombre/id de geometría de construcción, '
             'selector de cara o arista (edges:), id de find_faces/find_edges, '
             '{"sketch": nombre, "point": id}, {"sketch": nombre, "curve": id} '
             'o {"body": nombre, "vertex": índice desde 1}.')


def _crear(sesion, clase, **params):
    doc = sesion.doc
    return _agregar(sesion, clase(doc.nuevo_id(), nombre_nuevo(doc, clase.ETIQUETA, clase), **params))


def _cuerpos(sesion, bodies):
    ids = _ids_cuerpos(sesion, bodies)
    if not ids:
        raise error("INVALID_ARGUMENTS", "Seleccioná al menos un cuerpo.")
    return ids


def _curvas(sesion, sketch, curves):
    sop, br = boceto_activo(sesion, sketch)
    ids = list(dict.fromkeys(curves)) if curves is not None else [
        c.id for c in br.boceto.curvas.values() if not c.construccion]
    if not ids:
        raise error("INVALID_ARGUMENTS", "Seleccioná curvas del boceto.")
    for cid in ids:
        if cid not in br.boceto.curvas:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene la curva {cid}.")
    return [{"tipo": "curva_boceto", "boceto": sop.id, "curva": cid} for cid in ids]


def _referencia(sesion, spec, body=None, tipos=None):
    """Traduce referencias públicas con claves inglesas y valida antes de crear el paso."""
    ref = None
    if isinstance(spec, dict):
        claves = set(spec)
        if claves in ({"sketch", "point"}, {"sketch", "curve"}):
            if not isinstance(spec["sketch"], str):
                raise error("INVALID_ARGUMENTS", "sketch debe ser el nombre o id de un boceto.")
            sop, br = boceto_activo(sesion, spec["sketch"])
            punto = "point" in spec
            clave = "point" if punto else "curve"
            indice = spec[clave]
            datos = br.boceto.puntos if punto else br.boceto.curvas
            if isinstance(indice, bool) or not isinstance(indice, int) or indice not in datos:
                raise error("ENTITY_NOT_FOUND", f"No existe {clave}={indice!r} en «{sop.nombre}».")
            ref = {"tipo": "punto_boceto" if punto else "curva_boceto", "boceto": sop.id,
                   "punto" if punto else "curva": indice}
        elif claves == {"body", "vertex"}:
            if not isinstance(spec["body"], str):
                raise error("INVALID_ARGUMENTS", "body debe ser el nombre o id de un cuerpo.")
            c = sesion.cuerpo(spec["body"])
            vertices = referencias.subformas(c.forma, "vertice")
            i = spec["vertex"]
            if isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= len(vertices):
                raise error("INVALID_ARGUMENTS", "vertex debe ser un índice válido desde 1.")
            ref = referencias.referencia(c.id, vertices[i - 1], c.forma)
        else:
            raise error("INVALID_ARGUMENTS", "Referencia no reconocida. " + _GEOMETRIA)
    elif isinstance(spec, str):
        texto = spec.strip()
        origenes = {"XY": "plano", "XZ": "plano", "YZ": "plano", "X": "eje", "Y": "eje",
                    "Z": "eje", "O": "punto"}
        if texto.upper() in origenes:
            ref = {"tipo": origenes[texto.upper()], "id": texto.upper()}
        else:
            estado = sesion.doc.estado_final
            nombres = {o.id: o.nombre for o in sesion.doc.operaciones}        # un SCU deja ids que no son pasos (op4_xy)
            for mapa, tipo in ((estado.planos, "plano"), (estado.ejes, "eje"), (estado.puntos, "punto")):
                for id_ in mapa:
                    if texto in (id_, nombres.get(id_)):
                        ref = {"tipo": tipo, "id": id_}
                        break
                if ref:
                    break
            if ref is None:
                c, e = sl.elegir_uno(sesion, texto, body=body)
                ref = sl.referencia(c, e)
    if ref is None:
        raise error("INVALID_ARGUMENTS", "Falta una referencia geométrica. " + _GEOMETRIA)
    if tipos is not None and ref["tipo"] not in tipos:
        raise error("INVALID_ARGUMENTS", "La referencia no es del tipo requerido: " + ", ".join(tipos) + ".")
    try:
        ent.resolver(ref, sesion.doc.estado_final)
    except ent.ErrorReferencia as exc:
        raise error("REFERENCE_LOST", str(exc)) from exc
    return ref


def _caras_o_cuerpos(sesion, specs, body=None, planos=False):
    refs = []
    for spec in [specs] if isinstance(specs, str) else specs:
        if planos and spec.upper() in ("XY", "XZ", "YZ"):
            refs.append(_referencia(sesion, spec))
            continue
        try:
            cuerpo = sesion.cuerpo(spec)
        except ErrorAPI as exc:
            if exc.error_kind != "BODY_NOT_FOUND":
                raise
        else:
            refs.append({"tipo": "cuerpo", "cuerpo": cuerpo.id})
            continue
        if planos:
            try:
                sop = sesion.paso(spec)
            except ErrorAPI as exc:
                if exc.error_kind != "FEATURE_NOT_FOUND":
                    raise
            else:
                if sop.id in sesion.doc.estado_final.planos:
                    refs.append({"tipo": "plano", "id": sop.id})
                    continue
        refs.extend(sl.referencia(c, e) for c, e in sl.elegir(sesion, spec, "cara", body))
    if not refs:
        raise error("INVALID_ARGUMENTS", "Seleccioná caras, cuerpos o planos según la operación.")
    return refs


@herramienta("create_coil", "solido", "Crea una bobina o espiral con las opciones del comando Bobina.", modifica=True)
def create_coil(sesion, diameter: Expr = 20, coil_type: Literal["revolutions_height", "revolutions_pitch", "height_pitch", "spiral"] = "revolutions_height",
                revolutions: Expr = 5, height: Expr = 30, pitch: Expr = 6, angle: Expr = 0,
                section: Literal["circular", "square", "triangle_external", "triangle_internal"] = "circular",
                section_size: Expr = 3, position: Literal["on", "inside", "outside"] = "on",
                clockwise: bool = False, rotate: bool = False, plane: Referencia = "XY",
                center: Referencia | None = None, operation: Operacion = "new_body",
                target: Cuerpos | None = None, body: str | None = None):
    """
    diameter: diámetro de la bobina en mm o expresión.
    coil_type: revolutions_height, revolutions_pitch, height_pitch o spiral.
    revolutions: cantidad de vueltas (número o expresión escalar).
    height: altura axial en mm para los modos con altura.
    pitch: paso axial o radial de la espiral en mm.
    angle: ángulo de conicidad en grados; no se usa en espiral.
    section: circular, square, triangle_external o triangle_internal.
    section_size: diámetro del círculo circunscrito de la sección en mm.
    position: sección on (sobre), inside (dentro) u outside (fuera).
    clockwise: true invierte el sentido helicoidal.
    rotate: true gira 90 grados alrededor del eje Y local.
    plane: plano XY/XZ/YZ, nombre/id de plano de construcción o selector/id de una cara plana.
    center: punto del centro; O, nombre/id de punto, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana, por nombre o id; vacío = automático.
    body: cuerpo donde se evalúan selectores del plano o del centro.
    """
    _numero_positivo(diameter, "diameter")
    _numero_positivo(section_size, "section_size")
    plano = _referencia(sesion, plane, body, ("plano", "cara"))
    if plano["tipo"] == "cara":
        ent.como_plano(ent.resolver(plano, sesion.doc.estado_final))
    return _crear(sesion, OpBobina, plano=plano,
                  centro=_referencia(sesion, center, body, ("punto", "punto_boceto", "vertice")) if center is not None else None,
                  diametro=texto_expr(diameter), tipo={"revolutions_height": "rev_altura", "revolutions_pitch": "rev_paso",
                                                      "height_pitch": "altura_paso", "spiral": "espiral"}[coil_type],
                  revoluciones=texto_expr(revolutions), altura=texto_expr(height), paso=texto_expr(pitch),
                  angulo=texto_expr(angle), seccion={"circular": "circular", "square": "cuadrada",
                  "triangle_external": "triangular_externa", "triangle_internal": "triangular_interna"}[section],
                  tamano=texto_expr(section_size), posicion={"on": "sobre", "inside": "dentro", "outside": "fuera"}[position],
                  horario=clockwise, girar=rotate, operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))


@herramienta("create_pipe", "solido", "Crea una tubería maciza o hueca sobre curvas de boceto o aristas.", modifica=True)
def create_pipe(sesion, path_sketch: str | None = None, path_curves: list[int] | None = None,
                edges: Elementos | None = None, body: str | None = None, chain: bool = True,
                end: Expr = 1, start: Expr = 0, section: Literal["circular", "square", "triangle"] = "circular",
                section_size: Expr = 5, hollow: bool = False, thickness: Expr = 0.5,
                operation: Operacion = "new_body", target: Cuerpos | None = None):
    """
    path_sketch: nombre/id del boceto de ruta; se combina con aristas si se dan ambas fuentes.
    path_curves: ids de curvas; vacío = todas las no constructivas; requiere path_sketch.
    edges: selector o ids de find_edges, o lista, como ruta adicional.
    body: cuerpo donde se evalúan los selectores de aristas.
    chain: true incluye la cadena tangente conectada a la ruta seleccionada.
    end: fracción final de la ruta, entre 0 y 1.
    start: fracción inicial de la ruta, entre 0 y 1, menor que end.
    section: circular, square o triangle.
    section_size: diámetro exterior del círculo circunscrito de la sección en mm.
    hollow: true crea una sección hueca.
    thickness: espesor de la pared en mm cuando hollow=true.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana; vacío = automático.
    """
    ruta = _curvas(sesion, path_sketch, path_curves) if path_sketch is not None else []
    if path_curves is not None and path_sketch is None:
        raise error("INVALID_ARGUMENTS", "path_curves requiere path_sketch.")
    if edges is not None:
        ruta += [sl.referencia(c, e) for c, e in sl.elegir(sesion, edges, "arista", body)]
    if not ruta:
        raise error("INVALID_ARGUMENTS", "Seleccioná la ruta con path_sketch o edges.")
    _numero_positivo(section_size, "section_size")
    if hollow:
        _numero_positivo(thickness, "thickness")
    return _crear(sesion, OpTuberia, ruta=ruta, cadena=chain, distancia=texto_expr(end), distancia2=texto_expr(start),
                  seccion={"circular": "circular", "square": "cuadrada", "triangle": "triangular"}[section],
                  tamano=texto_expr(section_size), hueca=hollow, espesor=texto_expr(thickness),
                  operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))


def _nervio(sesion, clase, sketch, curves, thickness, extension, depth, direction, reverse, target):
    _numero_positivo(thickness, "thickness")
    if extension == "depth":
        _numero_positivo(depth, "depth")
    return _crear(sesion, clase, curvas=_curvas(sesion, sketch, curves), espesor=texto_expr(thickness),
                  extension="profundidad" if extension == "depth" else "hasta_siguiente", profundidad=texto_expr(depth),
                  direccion={"symmetric": "simetrica", "side1": "lado1", "side2": "lado2"}[direction],
                  invertir=reverse, objetivo=sesion.cuerpo(target).id if target is not None else "")


@herramienta("create_rib", "solido", "Crea un nervio paralelo al plano del boceto, hasta el cuerpo o a profundidad.", modifica=True)
def create_rib(sesion, sketch: str, curves: list[int] | None = None, thickness: Expr = 2,
               extension: Literal["to_next", "depth"] = "to_next", depth: Expr = 10,
               direction: Literal["symmetric", "side1", "side2"] = "symmetric", reverse: bool = False,
               target: str | None = None):
    """
    sketch: nombre/id del boceto con curvas abiertas.
    curves: ids de curvas; vacío = todas las no constructivas.
    thickness: grosor en mm.
    extension: to_next (hasta el siguiente cuerpo) o depth (profundidad).
    depth: profundidad en mm con extension=depth.
    direction: grosor symmetric, side1 o side2.
    reverse: true invierte la dirección de crecimiento.
    target: nombre/id del cuerpo objetivo; vacío = el más cercano.
    """
    return _nervio(sesion, OpNervio, sketch, curves, thickness, extension, depth, direction, reverse, target)


@herramienta("create_web", "solido", "Crea una red de nervios perpendicular al plano del boceto.", modifica=True)
def create_web(sesion, sketch: str, curves: list[int] | None = None, thickness: Expr = 2,
               extension: Literal["to_next", "depth"] = "to_next", depth: Expr = 10,
               direction: Literal["symmetric", "side1", "side2"] = "symmetric", reverse: bool = False,
               target: str | None = None):
    """
    sketch: nombre/id del boceto con curvas abiertas.
    curves: ids de curvas; vacío = todas las no constructivas.
    thickness: grosor en mm.
    extension: to_next (hasta el siguiente cuerpo) o depth (profundidad).
    depth: profundidad en mm con extension=depth.
    direction: grosor symmetric, side1 o side2.
    reverse: true invierte la normal usada por el comando Red.
    target: nombre/id del cuerpo objetivo; vacío = el más cercano.
    """
    return _nervio(sesion, OpRed, sketch, curves, thickness, extension, depth, direction, reverse, target)


@herramienta("create_emboss", "solido", "Repuja o graba perfiles en una o varias caras, con envoltura opcional.", modifica=True)
def create_emboss(sesion, sketch: str, faces: Elementos, profile: Perfiles = 0, depth: Expr = 1,
                  emboss_type: Literal["emboss", "deboss"] = "emboss", wrap: bool = False,
                  tangent_chain: bool = False, horizontal_offset: Expr = 0, vertical_offset: Expr = 0,
                  rotation: Expr = 0, reverse: bool = False, body: str | None = None):
    """
    sketch: nombre/id del boceto de perfiles o textos.
    faces: selector, ids de find_faces o lista de ambos.
    profile: índice, lista, all, largest, text o text:<id>, como extrude.
    depth: profundidad firmada en mm; negativa invierte relieve/grabado.
    emboss_type: emboss (relieve) o deboss (grabado).
    wrap: true envuelve sobre la cara.
    tangent_chain: true incluye las caras tangentes.
    horizontal_offset: desplazamiento horizontal en mm.
    vertical_offset: desplazamiento vertical en mm.
    rotation: giro de los perfiles en grados.
    reverse: true invierte la normal.
    body: cuerpo donde se evalúan selectores; vacío = el único cuerpo.
    """
    sop, br = boceto_activo(sesion, sketch)
    return _crear(sesion, OpRepujado, perfiles=[_ref_perfil(sop, p) for p in seleccionar_perfiles(br, sop, profile)],
                  caras=[sl.referencia(c, e) for c, e in sl.elegir(sesion, faces, "cara", body)],
                  profundidad=texto_expr(depth), tipo="relieve" if emboss_type == "emboss" else "grabado",
                  envolver=wrap, cadena_tangente=tangent_chain, desfase_h=texto_expr(horizontal_offset),
                  desfase_v=texto_expr(vertical_offset), giro=texto_expr(rotation), invertir=reverse)


@herramienta("create_boss", "solido", "Crea columnas para tornillo en puntos de boceto o vértices.", modifica=True)
def create_boss(sesion, positions: list[Referencia], outer_diameter: Expr = 8, hole_diameter: Expr = 3,
                height: Expr | None = None, draft_angle: Expr = 0, reverse: bool = False):
    """
    positions: puntos O o de construcción, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice desde 1}.
    outer_diameter: diámetro exterior en mm.
    hole_diameter: diámetro del agujero en mm, positivo y menor que outer_diameter.
    height: altura en mm; vacío = hasta el cuerpo.
    draft_angle: ángulo de desmoldeo en grados.
    reverse: true invierte el sentido automático respecto al material.
    """
    if not positions:
        raise error("INVALID_ARGUMENTS", "Seleccioná los puntos de los salientes.")
    _numero_positivo(outer_diameter, "outer_diameter")
    if height is not None:
        _numero_positivo(height, "height")
    return _crear(sesion, OpSaliente, posiciones=[_referencia(sesion, p, tipos=("punto", "punto_boceto", "vertice")) for p in positions],
                  diametro_exterior=texto_expr(outer_diameter), diametro_agujero=texto_expr(hole_diameter),
                  altura="" if height is None else texto_expr(height), angulo_desmoldeo=texto_expr(draft_angle), invertir=reverse)


@herramienta("create_lip_groove", "solido", "Crea un labio o una ranura a lo largo del borde de una pared.", modifica=True)
def create_lip_groove(sesion, edges: Elementos, lip_type: Literal["lip", "groove"] = "lip", width: Expr = 1,
                      height: Expr = 1.5, clearance: Expr = 0.1, direction: Referencia | None = None,
                      reverse: bool = False, body: str | None = None):
    """
    edges: selector o ids de find_edges, o lista; todas deben pertenecer al mismo cuerpo.
    lip_type: lip (labio) o groove (ranura).
    width: ancho en mm.
    height: alto en mm.
    clearance: holgura en mm para groove.
    direction: eje X/Y/Z, plano XY/XZ/YZ, geometría de construcción o selector/id de cara plana o arista recta; vacío = Z.
    reverse: true invierte la dirección de tirado.
    body: cuerpo donde se evalúan los selectores.
    """
    elegidos = sl.elegir(sesion, edges, "arista", body)
    if len({c.id for c, _ in elegidos}) != 1:
        raise error("INVALID_ARGUMENTS", "Las aristas del labio deben ser del mismo cuerpo.")
    _numero_positivo(width, "width")
    _numero_positivo(height, "height")
    return _crear(sesion, OpLabio, aristas=[sl.referencia(c, e) for c, e in elegidos],
                  tipo="labio" if lip_type == "lip" else "ranura", ancho=texto_expr(width), alto=texto_expr(height),
                  holgura=texto_expr(clearance), direccion=_referencia(sesion, direction, body) if direction is not None else None,
                  invertir=reverse)


@herramienta("create_boundary_fill", "solido", "Rellena celdas encerradas por cuerpos, caras y planos.", modifica=True)
def create_boundary_fill(sesion, tools: Elementos, cells: list[int] | None = None,
                         operation: Operacion = "new_body", target: Cuerpos | None = None, body: str | None = None):
    """
    tools: nombres/ids de cuerpos o planos, XY/XZ/YZ y selectores/ids de caras, solos o en lista.
    cells: números de celda desde 1, ordenadas por centroide XYZ como el diálogo; vacío = celda 1.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana; vacío = automático.
    body: cuerpo donde se evalúan selectores de caras.
    """
    if cells is not None and (not cells or any(i < 1 for i in cells)):
        raise error("INVALID_ARGUMENTS", "cells debe contener números de celda desde 1.")
    return _crear(sesion, OpRellenoContorno, herramientas=_caras_o_cuerpos(sesion, tools, body, planos=True),
                  celdas=[i - 1 for i in cells] if cells is not None else [0],
                  operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))


@herramienta("create_bounding_solid", "solido", "Crea una caja o cilindro envolvente de los cuerpos elegidos.", modifica=True)
def create_bounding_solid(sesion, bodies: Cuerpos, shape: Literal["box", "cylinder"] = "box",
                          axis: Literal["x", "y", "z"] = "z", margin: Expr = 0,
                          operation: Operacion = "new_body", target: Cuerpos | None = None):
    """
    bodies: nombres/ids de los cuerpos a envolver.
    shape: box (caja) o cylinder (cilindro).
    axis: eje del cilindro x, y o z.
    margin: desfase de la envolvente en mm.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana; vacío = automático.
    """
    return _crear(sesion, OpSolidoEnvolvente, cuerpos=_cuerpos(sesion, bodies), tipo="caja" if shape == "box" else "cilindro",
                  eje=axis, margen=texto_expr(margin), operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))


@herramienta("thicken", "solido", "Da espesor a caras o cuerpos de superficie y crea un sólido.", modifica=True)
def thicken(sesion, faces: Elementos, thickness: Expr = 2, direction: Literal["one_side", "symmetric"] = "one_side",
            thicken_type: Literal["sharp", "rounded"] = "sharp", operation: Operacion = "new_body",
            target: Cuerpos | None = None, body: str | None = None):
    """
    faces: selector/ids de caras o nombres/ids de cuerpos de superficie, solos o en lista.
    thickness: grosor firmado en mm; negativo invierte el lado.
    direction: one_side (un lado) o symmetric (mitad a cada lado).
    thicken_type: sharp (afilado) o rounded (redondeado).
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana; vacío = automático.
    body: cuerpo donde se evalúan selectores de caras.
    """
    return _crear(sesion, OpEngrosar, caras=_caras_o_cuerpos(sesion, faces, body), espesor=texto_expr(thickness),
                  direccion="un_lado" if direction == "one_side" else "simetrica",
                  tipo="agudo" if thicken_type == "sharp" else "redondeado",
                  operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))


@herramienta("align_bodies", "solido", "Alinea puntos, planos enfrentados o ejes de los cuerpos, con copia opcional.", modifica=True)
def align_bodies(sesion, bodies: Cuerpos, source: Referencia, destination: Referencia,
                 flip: bool = False, copy: bool = False, source_body: str | None = None,
                 destination_body: str | None = None):
    """
    bodies: nombres/ids de los cuerpos a mover o copiar.
    source: plano/eje/punto de origen, nombre/id de construcción, selector/id de cara o arista; {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}.
    destination: geometría de destino, con el mismo formato que source.
    flip: true voltea 180 grados la alineación.
    copy: true crea copias; false mueve los originales.
    source_body: cuerpo donde se evalúa el selector de source.
    destination_body: cuerpo donde se evalúa el selector de destination.
    """
    return _crear(sesion, OpAlinear, cuerpos=_cuerpos(sesion, bodies), origen=_referencia(sesion, source, source_body),
                  destino=_referencia(sesion, destination, destination_body), voltear=flip, copiar=copy)


@herramienta("scale_body", "solido", "Escala sólidos respecto de un punto, uniforme o con un factor por eje.", modifica=True)
def scale_body(sesion, bodies: Cuerpos, factor: Expr = 1, scale_type: Literal["uniform", "non_uniform"] = "uniform",
                factor_x: Expr = 1, factor_y: Expr = 1, factor_z: Expr = 1, point: Referencia | None = None):
    """
    bodies: nombres/ids de los sólidos a escalar.
    factor: factor escalar uniforme, número o expresión.
    scale_type: uniform o non_uniform.
    factor_x: factor del eje X para non_uniform.
    factor_y: factor del eje Y para non_uniform.
    factor_z: factor del eje Z para non_uniform.
    point: punto base O o de construcción, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}; vacío = origen.
    """
    ids = _cuerpos(sesion, bodies)
    if any(getattr(sesion.cuerpo(cid), "tipo", "solido") != "solido" for cid in ids):
        raise error("INVALID_ARGUMENTS", "scale_body requiere cuerpos sólidos.")
    return _crear(sesion, OpEscala, cuerpos=ids, tipo="uniforme" if scale_type == "uniform" else "no_uniforme",
                  factor=texto_expr(factor), fx=texto_expr(factor_x), fy=texto_expr(factor_y), fz=texto_expr(factor_z),
                  punto=_referencia(sesion, point, tipos=("punto", "punto_boceto", "vertice")) if point is not None else None)
