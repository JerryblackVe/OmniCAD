"""Creación avanzada de sólidos y alineación/escala, sin depender de la interfaz."""
from typing import Literal

from ..nucleo import referencias
from ..timeline import entidades as ent
from ..timeline.ops_modificar import OpAlinear, OpEscala, OpMover
from ..timeline.ops_solido import (OpBobina, OpLabio, OpNervio, OpPatronGeometrico, OpRed, OpRellenoContorno, OpReticulaVolumetrica,
                                   OpRepujado, OpSaliente, OpSolidoEnvolvente, OpTuberia, OpVolumenFluido)
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


def _nervio(sesion, clase, sketch, curves, thickness, extension, depth, direction, reverse, target, draft_angle=0,
            fillet_radius=0, extend_curves=True, pull_direction=None):
    _numero_positivo(thickness, "thickness")
    if extension == "depth":
        _numero_positivo(depth, "depth")
    if isinstance(fillet_radius, (int, float)) and fillet_radius < 0:
        raise error("INVALID_ARGUMENTS", f"fillet_radius no puede ser negativo (recibió {fillet_radius}).")
    if isinstance(draft_angle, (int, float)) and not -45 <= draft_angle <= 45:
        raise error("INVALID_ARGUMENTS", f"draft_angle tiene que estar entre -45 y 45 grados (recibió {draft_angle}).")
    extra = {}
    if pull_direction is not None:
        from .herramientas_construccion import _referencia as _ref_construccion
        extra["direccion_desmoldeo"] = _ref_construccion(sesion, pull_direction, {"plano", "cara", "eje", "arista"},
                                                         None, "direccion")
    return _crear(sesion, clase, curvas=_curvas(sesion, sketch, curves), espesor=texto_expr(thickness),
                  extension="profundidad" if extension == "depth" else "hasta_siguiente", profundidad=texto_expr(depth),
                  direccion={"symmetric": "simetrica", "side1": "lado1", "side2": "lado2"}[direction],
                  invertir=reverse, objetivo=sesion.cuerpo(target).id if target is not None else "",
                  angulo_desmoldeo=texto_expr(draft_angle), radio_empalme=texto_expr(fillet_radius),
                  extender=bool(extend_curves), **extra)


@herramienta("create_rib", "solido", "Crea un nervio paralelo al plano del boceto, hasta el cuerpo o a profundidad. "
             "direction: symmetric, o un solo lado empezando abajo (side1, Start: Bottom) o arriba (side2, Start: Top). "
             "draft_angle afina el nervio hacia su borde libre; pull_direction (plano, cara o eje) es la dirección de "
             "extracción del desmoldeo (por defecto, del cuerpo hacia la curva).", modifica=True)
def create_rib(sesion, sketch: str, curves: list[int] | None = None, thickness: Expr = 2,
               extension: Literal["to_next", "depth"] = "to_next", depth: Expr = 10,
               direction: Literal["symmetric", "side1", "side2"] = "symmetric", reverse: bool = False,
               target: str | None = None, draft_angle: Expr = 0, pull_direction: Referencia | None = None):
    """
    sketch: nombre/id del boceto con curvas abiertas.
    curves: ids de curvas; vacío = todas las no constructivas.
    thickness: grosor en mm.
    extension: to_next (hasta el siguiente cuerpo) o depth (profundidad).
    depth: profundidad en mm con extension=depth.
    direction: grosor symmetric, side1 (un lado, empieza abajo) o side2 (un lado, empieza arriba).
    reverse: true invierte la dirección de crecimiento.
    target: nombre/id del cuerpo objetivo; vacío = el más cercano.
    draft_angle: ángulo de desmoldeo en grados (entre -45 y 45; positivo = más fino en el borde libre), número o expresión.
    pull_direction: plano, cara o eje que da la dirección de extracción; vacío = del cuerpo hacia la curva del nervio.
    """
    return _nervio(sesion, OpNervio, sketch, curves, thickness, extension, depth, direction, reverse, target,
                   draft_angle=draft_angle, pull_direction=pull_direction)


@herramienta("create_web", "solido", "Crea una red de nervios perpendicular al plano del boceto. draft_angle afina la "
             "red hacia su borde libre, fillet_radius redondea las aristas cóncavas donde se junta con el cuerpo y "
             "extend_curves=false la deja terminar donde terminan las curvas.", modifica=True)
def create_web(sesion, sketch: str, curves: list[int] | None = None, thickness: Expr = 2,
               extension: Literal["to_next", "depth"] = "to_next", depth: Expr = 10,
               direction: Literal["symmetric", "side1", "side2"] = "symmetric", reverse: bool = False,
               target: str | None = None, draft_angle: Expr = 0, fillet_radius: Expr = 0, extend_curves: bool = True):
    """
    sketch: nombre/id del boceto con curvas abiertas.
    curves: ids de curvas; vacío = todas las no constructivas.
    thickness: grosor en mm.
    extension: to_next (hasta el siguiente cuerpo) o depth (profundidad).
    depth: profundidad en mm con extension=depth.
    direction: grosor symmetric, side1 o side2.
    reverse: true invierte la normal usada por el comando Red.
    target: nombre/id del cuerpo objetivo; vacío = el más cercano.
    draft_angle: ángulo de desmoldeo en grados (entre -45 y 45; positivo = más fina en el borde libre), número o expresión.
    fillet_radius: radio en mm del empalme entre la red y el cuerpo (0 = sin empalme), número o expresión.
    extend_curves: true prolonga las curvas hasta el cuerpo; false deja la red del largo de las curvas.
    """
    return _nervio(sesion, OpRed, sketch, curves, thickness, extension, depth, direction, reverse, target,
                   draft_angle=draft_angle, fillet_radius=fillet_radius, extend_curves=extend_curves)


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


@herramienta("create_volumetric_lattice", "solido", "Llena un sólido o una malla cerrada con una estructura interna por "
             "celdas (SÓLIDO › MODIFICAR › Retícula volumétrica). cell_shape: cross (tres barras por celda), x_cell (las "
             "cuatro diagonales), x_cell_25d (las diagonales en XY como paredes extruidas en Z) y custom (barras a medida, "
             "custom_bars) quedan como sólido; gyroid, schwarz_p y schwarz_d (superficies mínimas) quedan como cuerpo de "
             "malla (resolution muestras por celda; el borde del cuerpo sale interpolado). solidity es el porcentaje de "
             "material; con solidity_end y gradient_path varía a lo largo de la ruta. offset_distance/offset_blend arman "
             "la zona de desfase (otra solidez cerca de caras, aristas o puntos). cell_offset y cell_rotation mueven y "
             "giran las celdas. El cuerpo queda reemplazado por la retícula (deshacer lo devuelve).", modifica=True)
def create_volumetric_lattice(sesion, body: str | None = None,
                              cell_shape: Literal["cross", "x_cell", "x_cell_25d", "custom", "gyroid", "schwarz_p",
                                                  "schwarz_d"] = "gyroid",
                              cell_size: Expr = 5, cell_size_y: Expr | None = None, cell_size_z: Expr | None = None,
                              solidity: Expr = 30, resolution: int = 8, custom_bars: list[list[float]] | None = None,
                              solidity_end: Expr | None = None, gradient_path: list[Referencia] | None = None,
                              offset_distance: Expr = 0, offset_solidity: Expr = 100, offset_blend: Expr = 0,
                              offset_zones: list[Referencia] | None = None, cell_offset: list[float] | None = None,
                              cell_rotation: list[float] | None = None):
    """
    body: id o nombre del cuerpo sólido o de la malla cerrada; vacío = el único cuerpo.
    cell_shape: cross, x_cell, x_cell_25d, custom, gyroid, schwarz_p o schwarz_d.
    cell_size: tamaño de la celda en mm (en X, y en Y y Z si no se dan).
    cell_size_y: tamaño en Y, en mm, para celdas no uniformes; vacío = cell_size.
    cell_size_z: tamaño en Z, en mm, para celdas no uniformes; vacío = cell_size.
    solidity: porcentaje de material, de 1 a 99 (al principio de la ruta si hay gradiente).
    resolution: gyroid, schwarz_p y schwarz_d: muestras por celda (mínimo 4, por defecto 8); más es más fino y más lento.
    custom_bars: celda custom: barras [x1, y1, z1, x2, y2, z2] en fracciones de la celda (0 a 1).
    solidity_end: solidez al final de la ruta (1 a 99); vacío = solidez uniforme.
    gradient_path: ruta del gradiente: una arista o curva de boceto, o dos o más puntos o vértices (en orden).
    offset_distance: ancho en mm de la zona de desfase alrededor de offset_zones; 0 = sin zona.
    offset_solidity: solidez de la zona de desfase, de 0 a 100 (100 = macizo con superficies mínimas, 0 = sin retícula).
    offset_blend: distancia de mezcla en mm entre la zona de desfase y el resto.
    offset_zones: caras, aristas, puntos o cuerpos de la zona; vacío = todas las caras del cuerpo.
    cell_offset: [dx, dy, dz] en mm: mueve las celdas.
    cell_rotation: [rx, ry, rz] en grados: gira las celdas (primero en X, después Y, después Z).
    """
    if body is None or not str(body).strip():                                    # el único sólido o malla
        cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") in ("solido", "malla")]
        if len(cuerpos) != 1:
            raise error("BODY_NOT_FOUND" if not cuerpos else "AMBIGUOUS_REFERENCE",
                        "Indicá en body el sólido o la malla cerrada que se llena.")
        body = cuerpos[0].id
    cuerpo = sesion.cuerpo(body)
    for v, n in ((solidity, "solidity"), (solidity_end, "solidity_end")):
        if isinstance(v, (int, float)) and not 1 <= v <= 99:
            raise error("INVALID_ARGUMENTS", f"{n} va de 1 a 99 por ciento (recibió {v}).")
    if isinstance(offset_solidity, (int, float)) and not 0 <= offset_solidity <= 100:
        raise error("INVALID_ARGUMENTS", "offset_solidity va de 0 a 100 por ciento.")
    for v, n in ((cell_size, "cell_size"), (cell_size_y, "cell_size_y"), (cell_size_z, "cell_size_z")):
        if v is not None:
            _numero_positivo(v, n)
    if isinstance(resolution, bool) or not isinstance(resolution, int) or not 4 <= resolution <= 40:
        raise error("INVALID_ARGUMENTS", "resolution es un entero entre 4 y 40.")
    if cell_shape == "custom" and not custom_bars:
        raise error("INVALID_ARGUMENTS", "La celda custom necesita custom_bars: [[x1, y1, z1, x2, y2, z2], ...] de 0 a 1.")
    if custom_bars and any(len(b) != 6 or not all(0 <= x <= 1 for x in b) for b in custom_bars):
        raise error("INVALID_ARGUMENTS", "Cada barra de custom_bars son 6 números entre 0 y 1.")
    if solidity_end is not None and not gradient_path:
        raise error("INVALID_ARGUMENTS", "solidity_end necesita gradient_path (una arista o dos puntos).")
    for v, n in ((cell_offset, "cell_offset"), (cell_rotation, "cell_rotation")):
        if v is not None and len(v) != 3:
            raise error("INVALID_ARGUMENTS", f"{n} son 3 números [x, y, z].")
    mover = [f"{x} mm" for x in cell_offset or (0, 0, 0)]
    girar = [f"{x} deg" for x in cell_rotation or (0, 0, 0)]
    return _crear(sesion, OpReticulaVolumetrica, cuerpo=cuerpo.id, forma_celda=cell_shape, tamano=texto_expr(cell_size),
                  tamano_y="" if cell_size_y is None else texto_expr(cell_size_y),
                  tamano_z="" if cell_size_z is None else texto_expr(cell_size_z), solidez=texto_expr(solidity),
                  resolucion=resolution, barras=[list(map(float, b)) for b in custom_bars or []],
                  solidez_final="" if solidity_end is None else texto_expr(solidity_end),
                  ruta=[_referencia(sesion, r) for r in gradient_path or []] if solidity_end is not None else [],
                  zonas=[_referencia(sesion, r) for r in offset_zones or []], desfase=texto_expr(offset_distance),
                  solidez_desfase=texto_expr(offset_solidity), mezcla=texto_expr(offset_blend),
                  mover_x=mover[0], mover_y=mover[1], mover_z=mover[2], girar_x=girar[0], girar_y=girar[1],
                  girar_z=girar[2])


@herramienta("create_geometric_pattern", "solido", "Reparte esferas, cilindros, cajas u objetos a medida sobre caras "
             "planas con un gradiente de tamaño (PLÁSTICO › CREAR › Patrón geométrico). El tamaño va de size1 (en el "
             "centro del patrón) a size2 (en la esquina de la caja de la cara) con la curva de spread. Distribuciones: "
             "rectangular, triangular (filas desfasadas), hexagonal (panal), circular (anillos) y radial (rayos). "
             "clear_perimeter descarta los objetos que se salen de la cara u ocupan el borde. Con operation=cut o "
             "intersect los cilindros y cajas entran en el material; con join o new_body salen de la cara. Máximo 2000 "
             "objetos.", modifica=True)
def create_geometric_pattern(sesion, faces: Elementos, object_type: Literal["sphere", "cylinder", "box", "custom"] = "sphere",
                             size1: Expr = 2, size2: Expr = 4, spread: Expr = 1,
                             distribution: Literal["rectangular", "triangular", "hexagonal", "circular", "radial"] = "rectangular",
                             spacing_type: Literal["increment", "extent"] = "increment", distance: Expr = 6,
                             quantity_u: int = 5, quantity_v: int = 5, radial_distance: Expr = 6, spokes: int = 8,
                             orientation: Literal["parallel", "face"] = "face",
                             u_alignment: Literal["left", "center", "right"] = "center", u_offset: Expr = 0,
                             v_alignment: Literal["bottom", "middle", "top"] = "middle", v_offset: Expr = 0,
                             clear_perimeter: bool = True, perimeter_offset: Expr = 0,
                             operation: Operacion = "cut", target: Cuerpos | None = None,
                             custom_body: str | None = None, body: str | None = None):
    """
    faces: caras planas donde va el patrón (selector, ids de find_faces o lista).
    object_type: sphere (size = diámetro), cylinder (diámetro y altura = size), box (lado = size) o custom (custom_body; size = su mayor dimensión).
    size1: tamaño en el centro del patrón, en mm.
    size2: tamaño en la esquina de la caja de la cara, en mm.
    spread: exponente de la transición entre size1 y size2 (1 = lineal; mayor, los objetos grandes llegan más tarde).
    distribution: rectangular, triangular, hexagonal, circular o radial.
    spacing_type: rectangular: increment (cada distance) o extent (quantity_u × quantity_v repartidos de borde a borde).
    distance: separación entre objetos vecinos, en mm (rectangular, triangular y hexagonal).
    quantity_u: con extent, objetos a lo largo de U.
    quantity_v: con extent, objetos a lo largo de V (rectangular).
    radial_distance: circular y radial: separación entre anillos u objetos de un rayo, en mm.
    spokes: radial: cantidad de rayos.
    orientation: face (los objetos siguen los ejes U y V de la cara) o parallel (sin rotación, ejes del modelo).
    u_alignment: left, center o right: dónde se apoya la rejilla respecto de U.
    u_offset: desfase en U desde el borde (o desde el centro), en mm.
    v_alignment: bottom, middle o top.
    v_offset: desfase en V, en mm.
    clear_perimeter: true quita los objetos que no entran enteros en la cara.
    perimeter_offset: distancia mínima al borde de la cara, en mm.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados; vacío = automático.
    custom_body: con object_type=custom, el cuerpo que se repite.
    body: cuerpo donde se evalúan los selectores de caras.
    """
    from .herramientas_modificar import _refs
    refs, _ = _refs(sesion, faces, "cara", body)
    if object_type == "custom" and not custom_body:
        raise error("INVALID_ARGUMENTS", "object_type=custom necesita custom_body.")
    for v, n in ((quantity_u, "quantity_u"), (quantity_v, "quantity_v"), (spokes, "spokes")):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1 or v > 1000:
            raise error("INVALID_ARGUMENTS", f"{n} es un entero entre 1 y 1000.")
    return _crear(sesion, OpPatronGeometrico, caras=refs, objeto={"sphere": "esfera", "cylinder": "cilindro", "box": "caja",
                  "custom": "personalizado"}[object_type],
                  personalizado={"tipo": "cuerpo", "cuerpo": sesion.cuerpo(custom_body).id} if custom_body else None,
                  tamano1=texto_expr(size1), tamano2=texto_expr(size2), dispersion=texto_expr(spread),
                  distribucion=distribution, separacion={"increment": "incremento", "extent": "extension"}[spacing_type],
                  distancia=texto_expr(distance), cantidad_u=quantity_u, cantidad_v=quantity_v,
                  distancia_radial=texto_expr(radial_distance), rayos=spokes,
                  orientacion={"parallel": "paralela", "face": "cara"}[orientation],
                  alineacion_u={"left": "izquierda", "center": "centro", "right": "derecha"}[u_alignment],
                  desfase_u=texto_expr(u_offset),
                  alineacion_v={"bottom": "abajo", "middle": "medio", "top": "arriba"}[v_alignment],
                  desfase_v=texto_expr(v_offset), limpiar_perimetro=bool(clear_perimeter),
                  desfase_perimetro=texto_expr(perimeter_offset), operacion=OPERACIONES[operation],
                  objetivos=_objetivos(sesion, operation, target))


@herramienta("create_bounding_solid", "solido", "Crea una caja, un cilindro o un tubo envolvente de los cuerpos elegidos "
             "(SÓLIDO › CREAR › Sólido envolvente). orientation: model (ejes del modelo), automatic (la menor), "
             "z_x / z_y / x_y (dos ejes dados en axis_a y axis_b; el primero manda) o ucs (un sistema de coordenadas "
             "de usuario). Con component=true queda en un componente nuevo, como en Fusion, y rigid_group=true lo "
             "liga a los componentes de los cuerpos envueltos.", modifica=True)
def create_bounding_solid(sesion, bodies: Cuerpos, shape: Literal["box", "cylinder", "tube"] = "box",
                          axis: Literal["x", "y", "z"] = "z", margin: Expr = 0,
                          operation: Operacion = "new_body", target: Cuerpos | None = None,
                          orientation: Literal["model", "automatic", "z_x", "z_y", "x_y", "ucs"] = "model",
                          axis_a: Referencia | None = None, axis_b: Referencia | None = None,
                          ucs: str | None = None, tube_wall: Expr | None = None, component: bool = False,
                          rigid_group: bool = False, body: str | None = None,
                          origin: Literal["model", "center", "corner"] = "model"):
    """
    bodies: nombres/ids de los cuerpos a envolver.
    shape: box (caja), cylinder (cilindro) o tube (cilindro hueco).
    axis: eje del cilindro o tubo x, y o z cuando orientation=model.
    margin: desfase de la envolvente en mm.
    operation: new_body, join, cut o intersect.
    target: cuerpos afectados por la booleana; vacío = automático.
    orientation: model, automatic, z_x, z_y, x_y o ucs; con z_x, z_y y x_y hacen falta axis_a y axis_b.
    axis_a: primer eje de la orientación (eje de construcción, arista recta o línea de boceto; selector o id).
    axis_b: segundo eje de la orientación; se ortogonaliza respecto del primero.
    ucs: id o nombre del sistema de coordenadas de usuario cuando orientation=ucs.
    tube_wall: espesor de pared del tubo en mm (número o expresión); vacío = la décima parte del radio.
    component: true deja el sólido en un componente nuevo.
    rigid_group: true liga el sólido a los componentes de los cuerpos envueltos (solo vale si los cuerpos están en componentes).
    body: cuerpo donde se evalúan los selectores de los ejes.
    origin: dónde queda el origen del componente (Origin Mode): model (el del documento), center (centro del sólido) o corner (su esquina mínima); solo con component=true o rigid_group=true; get_assembly lo informa.
    """
    extra = {}
    if origin != "model" and not (component or rigid_group):
        raise error("INVALID_ARGUMENTS", "origin solo vale con component=true o rigid_group=true.")
    if orientation in ("z_x", "z_y", "x_y"):
        if axis_a is None or axis_b is None:
            raise error("INVALID_ARGUMENTS", f"orientation={orientation} necesita axis_a y axis_b.")
        tipos = ("eje", "arista", "curva_boceto")
        extra = {"eje_a": _referencia(sesion, axis_a, body, tipos), "eje_b": _referencia(sesion, axis_b, body, tipos)}
    elif orientation == "ucs":
        if ucs is None:
            raise error("INVALID_ARGUMENTS", "orientation=ucs necesita ucs (id o nombre del sistema de coordenadas).")
        extra = {"scu": _paso_ucs(sesion, ucs)}
    if shape != "tube" and tube_wall is not None:
        raise error("INVALID_ARGUMENTS", "tube_wall solo vale con shape=tube.")
    if tube_wall is not None:
        _numero_positivo(tube_wall, "tube_wall")
    return _crear(sesion, OpSolidoEnvolvente, cuerpos=_cuerpos(sesion, bodies),
                  tipo={"box": "caja", "cylinder": "cilindro", "tube": "tubo"}[shape], eje=axis,
                  margen=texto_expr(margin), operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target),
                  orientacion={"model": "modelo", "automatic": "automatica", "ucs": "scu"}.get(orientation, orientation),
                  espesor_tubo="" if tube_wall is None else texto_expr(tube_wall), componente=bool(component),
                  grupo_rigido=bool(rigid_group), origen={"model": "modelo", "center": "centro", "corner": "esquina"}[origin],
                  **extra)


def _paso_ucs(sesion, ref):
    """Id del paso SCU que se nombra por id o por nombre."""
    from ..timeline.ops_construir import OpSCU
    for o in sesion.doc.operaciones[:sesion.doc.marcador]:
        if isinstance(o, OpSCU) and str(ref).casefold() in (o.id.casefold(), o.nombre.casefold()):
            return o.id
    raise error("ENTITY_NOT_FOUND", f"No hay un sistema de coordenadas de usuario «{ref}».",
                "create_ucs crea uno; get_timeline lista los pasos.")


@herramienta("create_fluid_volume", "solido", "Crea el volumen de fluido de un diseño (SÓLIDO › CREAR › Volumen de fluido): "
             "el sólido del interior (internal, que copia las caras del modelo) o del exterior (external, una caja, "
             "cilindro o semiesfera que rodea el modelo menos el modelo). Las aberturas del modelo se tapan con "
             "cuerpos de superficie (caps); sin tapas el interior no queda cerrado y falla. split_faces deja una cara "
             "por superficie del modelo (Split Result). El resultado queda en un componente nuevo.", modifica=True)
def create_fluid_volume(sesion, bodies: Cuerpos, volume_type: Literal["internal", "external"] = "internal",
                        caps: Cuerpos | None = None, outer_shape: Literal["box", "cylinder", "hemisphere"] = "box",
                        margin: Expr = 10, split_faces: bool = False):
    """
    bodies: nombres/ids de los cuerpos sólidos del diseño.
    volume_type: internal (interior del modelo) o external (el aire alrededor).
    caps: cuerpos de superficie que cubren las aberturas; vacío = ninguno.
    outer_shape: forma que rodea al modelo con volume_type=external: box, cylinder (eje Z) o hemisphere (mitad superior).
    margin: distancia en mm entre el modelo y la forma exterior (número o expresión); no cuenta en el interno.
    split_faces: true deja una cara por cada superficie del modelo (Split Result); false funde las caras tangentes.
    """
    return _crear(sesion, OpVolumenFluido, cuerpos=_cuerpos(sesion, bodies), tapas=_ids_cuerpos(sesion, caps) if caps else [],
                  tipo={"internal": "interno", "external": "externo"}[volume_type],
                  forma_externa={"box": "caja", "cylinder": "cilindro", "hemisphere": "semiesfera"}[outer_shape],
                  margen=texto_expr(margin), separar_caras=bool(split_faces))


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


@herramienta("align_bodies", "solido", "Alinea puntos, planos enfrentados o ejes de los cuerpos, con copia opcional "
             "(Fusion: Alinear, con Flip y Angle). angle gira el resultado alrededor de la normal o del eje del destino "
             "(Fusion lo hace de a 90°; acá vale cualquier ángulo); con un punto de destino no hay eje y angle falla.",
             modifica=True)
def align_bodies(sesion, bodies: Cuerpos, source: Referencia, destination: Referencia,
                 flip: bool = False, copy: bool = False, source_body: str | None = None,
                 destination_body: str | None = None, angle: float = 0.0):
    """
    bodies: nombres/ids de los cuerpos a mover o copiar; un componente (id o nombre) mueve todos sus cuerpos.
    source: plano/eje/punto de origen, nombre/id de construcción, selector/id de cara o arista; {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}.
    destination: geometría de destino, con el mismo formato que source.
    flip: true voltea 180 grados la alineación.
    copy: true crea copias; false mueve los originales.
    source_body: cuerpo donde se evalúa el selector de source.
    destination_body: cuerpo donde se evalúa el selector de destination.
    angle: giro extra en grados alrededor de la normal o del eje del destino, después de alinear (0 = sin giro).
    """
    if not -360.0 <= angle <= 360.0:
        raise error("INVALID_ARGUMENTS", f"angle va de -360 a 360 grados (llegó {angle!r}).")
    return _crear(sesion, OpAlinear, cuerpos=_cuerpos(sesion, _con_componentes(sesion, bodies)), origen=_referencia(sesion, source, source_body),
                  destino=_referencia(sesion, destination, destination_body), voltear=flip, copiar=copy, angulo=angle)


@herramienta("move_faces", "solido", "Mueve o copia caras planas de un cuerpo (SÓLIDO › MODIFICAR › Mover/copiar › Caras): "
             "las caras vecinas se extienden o se recortan para seguirlas. type=translate con direction (eje, arista "
             "recta, cara plana o plano) y distance, o con translate [dx, dy, dz]; type=rotate alrededor de axis un "
             "angle. Con copy=true el cuerpo no cambia y cada cara movida queda como un cuerpo de superficie nuevo. "
             "Mover caras que no son planas todavía no está.", modifica=True)
def move_faces(sesion, faces: Elementos, type: Literal["translate", "rotate"] = "translate",
               translate: list[Expr] | None = None, direction: Referencia | None = None, distance: Expr = 10,
               axis: Referencia | None = None, angle: Expr = 90, copy: bool = False, body: str | None = None):
    """
    faces: caras a mover: selector, ids de find_faces o lista de ambos.
    type: "translate" o "rotate".
    translate: con type=translate y sin direction: desplazamiento [dx, dy, dz] en mm (números o expresiones).
    direction: con type=translate: eje de construcción, arista recta, cara plana o plano; se mueve distance a lo largo de él.
    distance: con direction: desplazamiento en mm (número o expresión).
    axis: con type=rotate: eje de construcción (id o nombre), arista recta o línea de boceto {"sketch", "curve"}.
    angle: con type=rotate: ángulo en grados (número o expresión).
    copy: true deja el cuerpo como está y crea una superficie con cada cara movida.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    from .herramientas_construccion import _referencia as _ref_construccion
    from .herramientas_modificar import _refs
    refs, _ = _refs(sesion, faces, "cara", body)
    if type == "translate":
        if (direction is None) == (translate is None):
            raise error("INVALID_ARGUMENTS", "type=translate necesita direction (con distance) o translate, uno solo.")
        if translate is not None and len(translate) != 3:
            raise error("INVALID_ARGUMENTS", "translate tiene que ser [dx, dy, dz] (3 valores).")
        nuevos = dict(tipo="traslacion")
        if direction is not None:
            nuevos.update(direccion=_ref_construccion(sesion, direction, {"eje", "arista", "cara", "plano"}, body,
                                                      "direccion"), distancia=texto_expr(distance))
        else:
            nuevos.update(dx=texto_expr(translate[0]), dy=texto_expr(translate[1]), dz=texto_expr(translate[2]))
    else:
        if axis is None:
            raise error("INVALID_ARGUMENTS", "type=rotate necesita axis.")
        nuevos = dict(tipo="rotacion", eje=_ref_construccion(sesion, axis, {"eje", "arista", "curva_boceto"}, body, "eje"),
                      angulo=texto_expr(angle))
    return _crear(sesion, OpMover, caras=refs, cuerpos=[], copiar=bool(copy), **nuevos)


def _con_componentes(sesion, bodies):
    """`bodies` con cada nombre o id de un COMPONENTE cambiado por los ids de sus cuerpos (Scale › Components)."""
    estado = sesion.doc.estado_final
    salida = []
    for b in ([bodies] if isinstance(bodies, str) else list(bodies)):
        try:
            sesion.cuerpo(b)
            salida.append(b)
            continue
        except ErrorAPI:
            pass
        comp = next((k for k, d in estado.componentes.items()
                     if b.casefold() in (k.casefold(), (d.get("nombre") or "").casefold())), None)
        if comp is None:
            salida.append(b)                    # que el error sea el de siempre: cuerpo no encontrado
        else:
            salida += [c.id for c in estado.cuerpos.values() if (c.componente or "") == comp]
    return salida


@herramienta("scale_body", "solido", "Escala sólidos o componentes (con todos sus cuerpos) respecto de un punto, uniforme "
             "o con un factor por eje. sketches escala bocetos enteros (solo uniforme).", modifica=True)
def scale_body(sesion, bodies: Cuerpos | None = None, factor: Expr = 1, scale_type: Literal["uniform", "non_uniform"] = "uniform",
                factor_x: Expr = 1, factor_y: Expr = 1, factor_z: Expr = 1, point: Referencia | None = None,
                sketches: list[str] | None = None):
    """
    bodies: nombres/ids de los sólidos a escalar; un componente (id o nombre) escala todos sus cuerpos. Vacío si solo se escalan bocetos.
    sketches: bocetos enteros a escalar (id o nombre), solo uniform.
    factor: factor escalar uniforme, número o expresión.
    scale_type: uniform o non_uniform.
    factor_x: factor del eje X para non_uniform.
    factor_y: factor del eje Y para non_uniform.
    factor_z: factor del eje Z para non_uniform.
    point: punto base O o de construcción, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}; vacío = origen.
    """
    ids = _cuerpos(sesion, _con_componentes(sesion, bodies)) if bodies or not sketches else []
    bocetos = [sesion.paso(b).id for b in sketches or []]
    if any(getattr(sesion.cuerpo(cid), "tipo", "solido") != "solido" for cid in ids):
        raise error("INVALID_ARGUMENTS", "scale_body requiere cuerpos sólidos.")
    return _crear(sesion, OpEscala, cuerpos=ids, bocetos=bocetos, tipo="uniforme" if scale_type == "uniform" else "no_uniforme",
                  factor=texto_expr(factor), fx=texto_expr(factor_x), fy=texto_expr(factor_y), fz=texto_expr(factor_z),
                  punto=_referencia(sesion, point, tipos=("punto", "punto_boceto", "vertice")) if point is not None else None)
