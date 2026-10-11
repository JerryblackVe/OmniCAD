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
from ..timeline.ops_modificar import OpMover
from ..timeline.ops_solido import OpBarrido, OpMultitransformar, OpPatron, OpSimetria, OpSolevacion
from .errores import error
from .herramientas_boceto import (boceto_activo, nombre_nuevo, referencia_plano, seleccionar_perfiles,
                                  texto_expr)
from .registro import Expr, herramienta

OPERACIONES = {"new_body": "nuevo", "join": "unir", "cut": "cortar", "intersect": "intersecar"}
Operacion = Literal["new_body", "join", "cut", "intersect"]
Perfiles = int | list[int] | str
Cuerpos = str | list[str]


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


def _numero_positivo(valor, que):
    if isinstance(valor, (int, float)) and valor <= 0:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser positivo (recibió {valor}).")


def _exigir_instancias(total, que):
    """Tope de instancias de un patrón, antes de gastar un id (el núcleo lo vuelve a frenar en run_operation)."""
    from ..nucleo.solidos_crear import INSTANCIAS_MAXIMAS      # local: el núcleo se carga recién al calcular
    if total > INSTANCIAS_MAXIMAS:
        maximo, pedido = (f"{n:,}".replace(",", ".") for n in (INSTANCIAS_MAXIMAS, total))
        raise error("INVALID_ARGUMENTS", f"Un patrón admite como máximo {maximo} instancias, el original incluido "
                                         f"({que} = {pedido}).")


# ---------------------------------------------------------------- extrusión y revolución
@herramienta("extrude", "solido",
             "Extruye perfiles de un boceto. profile: índice, lista de índices, 'all' o 'largest' (el perfil de mayor "
             "área, p. ej. la placa con sus agujeros). distance acepta un número (mm) o una expresión con parámetros. "
             "El sentido positivo es la normal del plano del boceto (en XZ es −Y); reverse lo invierte. Como en Fusion, "
             "un cut desde un boceto sobre una cara entra al material sin pedirlo (reverse vacío). direction: "
             "one_side, two_sides (distance y distance2) o symmetric (distance es el largo TOTAL, mitad a cada "
             "lado). taper_angle inclina las paredes (grados; positivo ensancha el sólido hacia el final, negativo "
             "lo estrecha). operation: new_body, join, cut o intersect.",
             modifica=True)
def extrude(sesion, sketch: str, profile: Perfiles = 0, distance: Expr = "10 mm", operation: Operacion = "new_body",
            direction: Literal["one_side", "two_sides", "symmetric"] = "one_side", taper_angle: Expr = 0,
            target: Cuerpos | None = None, distance2: Expr | None = None, reverse: bool | None = None):
    """
    sketch: id o nombre del boceto.
    profile: perfil(es): índice (get_sketch los lista), lista de índices, "all" o "largest".
    distance: distancia de extrusión: número en mm o expresión, p. ej. "espesor" o "2 * radio".
    operation: "new_body", "join", "cut" o "intersect".
    direction: "one_side", "two_sides" o "symmetric".
    taper_angle: conicidad en grados (número o expresión): positivo ensancha hacia el final, negativo estrecha; 0 = recto.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    distance2: distancia del segundo lado con direction="two_sides"; vacío = igual a distance.
    reverse: true para extruir hacia el lado contrario de la normal del plano. Vacío = automático: solo un cut
        desde un boceto sobre una cara se invierte (entra al material, como Fusion).
    """
    sop, br = boceto_activo(sesion, sketch)
    perfiles = seleccionar_perfiles(br, sop, profile)
    if reverse is None:
        reverse = operation == "cut" and sop.p.get("plano") == "cara"
    doc = sesion.doc
    p = {"boceto": sop.id, "perfiles": [OpExtrusion.referencia_perfil(x) for x in perfiles],
         "distancia": texto_expr(distance), "operacion": OPERACIONES[operation],
         "objetivos": _objetivos(sesion, operation, target), "invertir": reverse,
         "conicidad": texto_expr(taper_angle), "conicidad2": texto_expr(taper_angle)}
    if direction == "two_sides":
        p.update(direccion="dos_lados", distancia2=texto_expr(distance if distance2 is None else distance2))
    elif direction == "symmetric":
        p.update(direccion="simetrica", simetrica=True, medida="total")
    op = OpExtrusion(doc.nuevo_id(), nombre_nuevo(doc, "Extrusión", OpExtrusion), **p)
    resultado = _agregar(sesion, op, operation != "new_body")
    resultado["profiles_used"] = [br.perfiles.index(x) for x in perfiles]
    return resultado


def _eje_revolucion(sop, br, axis):
    s = str(axis).strip().casefold()
    if s == "sketch_x":
        return {"eje": "u"}
    if s == "sketch_y":
        return {"eje": "v"}
    if s in ("x", "y", "z"):
        return {"eje_ref": {"tipo": "eje", "id": s.upper()}}
    if s.isdigit() and int(s) in br.boceto.curvas and br.boceto.curvas[int(s)].tipo == "linea":
        return {"eje": str(int(s))}
    raise error("INVALID_AXIS", f"El eje '{axis}' no sirve para girar el boceto «{sop.nombre}»"
                + (": esa entidad no es una línea del boceto." if s.isdigit() else "."))


@herramienta("revolve", "solido",
             "Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del "
             "boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del "
             "boceto (get_sketch; puede ser de construcción). El perfil no debe cruzar el eje. angle acepta número "
             "(grados) o expresión. direction: one_side, two_sides (angle y angle2) o symmetric.", modifica=True)
def revolve(sesion, sketch: str, profile: Perfiles, axis: int | str, angle: Expr = "360 deg",
            operation: Operacion = "new_body", direction: Literal["one_side", "two_sides", "symmetric"] = "one_side",
            angle2: Expr | None = None, target: Cuerpos | None = None, reverse: bool = False):
    """
    sketch: id o nombre del boceto.
    profile: perfil(es): índice, lista de índices, "all" o "largest".
    axis: "sketch_x", "sketch_y", "x", "y", "z" o el id de una línea del boceto.
    angle: ángulo de giro: número en grados o expresión, p. ej. "270 deg" o "giro".
    operation: "new_body", "join", "cut" o "intersect".
    direction: "one_side", "two_sides" o "symmetric" (el ángulo se reparte a los dos lados).
    angle2: ángulo del segundo lado con direction="two_sides"; vacío = igual a angle.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    reverse: true para girar en el sentido contrario.
    """
    sop, br = boceto_activo(sesion, sketch)
    perfiles = seleccionar_perfiles(br, sop, profile)
    doc = sesion.doc
    p = {"boceto": sop.id, "perfiles": [OpRevolucion.referencia_perfil(x) for x in perfiles],
         "angulo": texto_expr(angle), "operacion": OPERACIONES[operation],
         "objetivos": _objetivos(sesion, operation, target), "invertir": reverse}
    p.update(_eje_revolucion(sop, br, axis))
    if direction == "two_sides":
        p.update(direccion="dos_lados", angulo2=texto_expr(angle if angle2 is None else angle2))
    elif direction == "symmetric":
        p["direccion"] = "simetrica"
    op = OpRevolucion(doc.nuevo_id(), nombre_nuevo(doc, "Revolución", OpRevolucion), **p)
    resultado = _agregar(sesion, op, operation != "new_body")
    resultado["profiles_used"] = [br.perfiles.index(x) for x in perfiles]
    return resultado


@herramienta("sweep", "solido",
             "Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). La ruta es una cadena continua de "
             "curvas: path_curves da sus ids (get_sketch) o, vacío, se usan todas las curvas no de construcción del "
             "boceto de la ruta. El perfil tiene que estar en el plano perpendicular al inicio de la ruta.",
             modifica=True)
def sweep(sesion, sketch: str, profile: Perfiles, path_sketch: str, path_curves: list[int] | None = None,
          operation: Operacion = "new_body", orientation: Literal["perpendicular", "parallel"] = "perpendicular",
          taper_angle: Expr = 0, twist_angle: Expr = 0, target: Cuerpos | None = None):
    """
    sketch: id o nombre del boceto con el perfil.
    profile: perfil(es): índice, lista de índices, "all" o "largest".
    path_sketch: id o nombre del boceto con la ruta.
    path_curves: ids de las curvas de la ruta; vacío = todas las curvas no de construcción de path_sketch.
    operation: "new_body", "join", "cut" o "intersect".
    orientation: "perpendicular" (el perfil sigue la tangente de la ruta) o "parallel" (mantiene su orientación).
    taper_angle: ángulo de conicidad en grados.
    twist_angle: torsión total en grados (máximo ±3600; ±1800 en rutas cerradas; la ruta no puede tener esquinas).
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    """
    if isinstance(twist_angle, (int, float)) and not isinstance(twist_angle, bool):
        from ..nucleo.solidos_crear import TORSION_MAXIMA      # local: el núcleo se carga recién al calcular
        if not math.isfinite(twist_angle) or abs(twist_angle) > TORSION_MAXIMA:
            raise error("INVALID_ARGUMENTS", f"twist_angle admite como máximo ±{TORSION_MAXIMA:g}° "
                                             f"({TORSION_MAXIMA / 360:g} vueltas); recibió {twist_angle:g}°.")
    sop, br = boceto_activo(sesion, sketch)
    perfiles = seleccionar_perfiles(br, sop, profile)
    rop, rbr = boceto_activo(sesion, path_sketch)
    curvas = list(path_curves) if path_curves else [c.id for c in rbr.boceto.curvas.values() if not c.construccion]
    for cid in curvas:
        if cid not in rbr.boceto.curvas:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{rop.nombre}» no tiene la curva {cid}.")
    if not curvas:
        raise error("ENTITY_NOT_FOUND", f"El boceto de la ruta «{rop.nombre}» no tiene curvas.")
    doc = sesion.doc
    op = OpBarrido(doc.nuevo_id(), nombre_nuevo(doc, "Barrido", OpBarrido),
                   perfiles=[_ref_perfil(sop, x) for x in perfiles],
                   ruta=[{"tipo": "curva_boceto", "boceto": rop.id, "curva": cid} for cid in curvas],
                   orientacion=orientation if orientation == "perpendicular" else "paralela",
                   conicidad=texto_expr(taper_angle), torsion=texto_expr(twist_angle),
                   operacion=OPERACIONES[operation], objetivos=_objetivos(sesion, operation, target))
    return _agregar(sesion, op, operation != "new_body")


@herramienta("loft", "solido",
             "Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). "
             "profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa "
             "tramos rectos entre secciones y closed une la última con la primera.", modifica=True)
def loft(sesion, sketches: list[str], profiles: list[int | str] | None = None, operation: Operacion = "new_body",
         ruled: bool = False, closed: bool = False, target: Cuerpos | None = None):
    """
    sketches: ids o nombres de los bocetos, en el orden de las secciones.
    profiles: un perfil por boceto (índice o "largest"); vacío = el perfil 0 de cada boceto.
    operation: "new_body", "join", "cut" o "intersect".
    ruled: true para tramos rectos entre secciones.
    closed: true para cerrar el sólido uniendo la última sección con la primera.
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    """
    if len(sketches) < 2:
        raise error("INVALID_ARGUMENTS", "Una solevación necesita al menos dos bocetos.")
    if profiles is not None and len(profiles) != len(sketches):
        raise error("INVALID_ARGUMENTS", f"profiles tiene {len(profiles)} elementos y hay {len(sketches)} bocetos.")
    secciones = []
    for i, ref in enumerate(sketches):
        sop, br = boceto_activo(sesion, ref)
        secciones.append(_ref_perfil(sop, seleccionar_perfiles(br, sop, 0 if profiles is None else profiles[i])[0]))
    doc = sesion.doc
    op = OpSolevacion(doc.nuevo_id(), nombre_nuevo(doc, "Solevación", OpSolevacion), secciones=secciones,
                      cerrada=closed, reglada=ruled, operacion=OPERACIONES[operation],
                      objetivos=_objetivos(sesion, operation, target))
    return _agregar(sesion, op, operation != "new_body")


# ---------------------------------------------------------------- primitivas
def _primitiva(sesion, forma, base, medidas, x, y, z, operation, target, **extra):
    doc = sesion.doc
    objetivos = _objetivos(sesion, operation, target)
    if len(objetivos) > 1:
        sesion.avisar("Las primitivas solo aceptan un cuerpo en «target»: se usan los sólidos que toca.")
    p = {"forma": forma, "x": texto_expr(x), "y": texto_expr(y), "z": texto_expr(z),
         "operacion": OPERACIONES[operation], "objetivo": objetivos[0] if len(objetivos) == 1 else ""}
    p.update({k: texto_expr(v) for k, v in medidas.items()})
    p.update(extra)
    op = OpPrimitiva(doc.nuevo_id(), nombre_nuevo(doc, base, OpPrimitiva, lambda o: o.p["forma"] == forma), **p)
    return _agregar(sesion, op, operation != "new_body")


@herramienta("create_box", "solido",
             "Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) "
             "es el centro de la cara de abajo: la caja queda centrada en X e Y y apoyada en z. Medidas y posición "
             "aceptan expresiones con parámetros. En el timeline el paso guarda x, y, z con el mismo significado "
             "(caja_centrada) y edit_feature acepta length, width y height.", modifica=True)
def create_box(sesion, length: Expr, width: Expr, height: Expr, x: Expr = 0, y: Expr = 0, z: Expr = 0,
               operation: Operacion = "new_body", target: Cuerpos | None = None):
    """
    length: tamaño en X (mm, positivo).
    width: tamaño en Y (mm, positivo).
    height: tamaño en Z (mm, positivo).
    x: x del centro de la base (mm).
    y: y del centro de la base (mm).
    z: z de la base (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    """
    for valor, que in ((length, "length"), (width, "width"), (height, "height")):
        _numero_positivo(valor, que)
    return _primitiva(sesion, "caja", "Caja", {"ancho": length, "largo": width, "alto": height},
                      x, y, z, operation, target, caja_centrada=True)


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
             "Crea un cilindro con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es el centro de la "
             "base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo).", modifica=True)
def create_cylinder(sesion, height: Expr, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                    operation: Operacion = "new_body", target: Cuerpos | None = None, diameter: Expr | None = None):
    """
    height: altura en mm (positiva).
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro de la base (mm).
    y: y del centro de la base (mm).
    z: z de la base (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    diameter: diámetro en mm, en vez de radius (como el panel Cilindro de la app); el paso guarda la mitad.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    _numero_positivo(height, "height")
    return _primitiva(sesion, "cilindro", "Cilindro", {"radio": radio, "alto": height}, x, y, z, operation, target)


@herramienta("create_sphere", "solido", "Crea una esfera. (x, y, z) es su centro. La medida va como radius o como "
             "diameter (uno solo).", modifica=True)
def create_sphere(sesion, radius: Expr | None = None, x: Expr = 0, y: Expr = 0, z: Expr = 0,
                  operation: Operacion = "new_body", target: Cuerpos | None = None, diameter: Expr | None = None):
    """
    radius: radio en mm (positivo). Alternativa: diameter.
    x: x del centro (mm).
    y: y del centro (mm).
    z: z del centro (mm).
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    diameter: diámetro en mm, en vez de radius (como el panel Esfera de la app); el paso guarda la mitad.
    """
    radio = _radio_o_diametro(radius, diameter, "radius", "diameter")
    return _primitiva(sesion, "esfera", "Esfera", {"radio": radio}, x, y, z, operation, target)


@herramienta("create_torus", "solido", "Crea un toroide con el eje en Z (para otro eje, girarlo con move_body). "
             "(x, y, z) es su centro. Medidas como radios (major_radius, minor_radius) o diámetros (major_diameter, "
             "minor_diameter), uno de cada par.", modifica=True)
def create_torus(sesion, major_radius: Expr | None = None, minor_radius: Expr | None = None, x: Expr = 0, y: Expr = 0,
                 z: Expr = 0, operation: Operacion = "new_body", target: Cuerpos | None = None,
                 major_diameter: Expr | None = None, minor_diameter: Expr | None = None):
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
    """
    mayor = _radio_o_diametro(major_radius, major_diameter, "major_radius", "major_diameter")
    menor = _radio_o_diametro(minor_radius, minor_diameter, "minor_radius", "minor_diameter")
    return _primitiva(sesion, "toroide", "Toroide", {"radio_mayor": mayor, "radio_menor": menor},
                      x, y, z, operation, target)


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
             "Refleja cuerpos respecto de un plano (origen o de construcción). Crea cuerpos nuevos, o con combine=true "
             "une cada reflejo a su cuerpo original.", modifica=True)
def mirror(sesion, bodies: Cuerpos, plane: str = "YZ", combine: bool = False):
    """
    bodies: cuerpo(s) a reflejar (id o nombre).
    plane: plano de simetría: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    combine: true para unir el reflejo al cuerpo original en vez de crear un cuerpo nuevo.
    """
    ids = _ids_cuerpos(sesion, bodies)
    if not ids:
        raise error("INVALID_ARGUMENTS", "Indicá al menos un cuerpo en 'bodies'.")
    ref = referencia_plano(sesion, plane)          # antes de gastar un id: si falla, el documento no cambia
    doc = sesion.doc
    op = OpSimetria(doc.nuevo_id(), nombre_nuevo(doc, "Simetría", OpSimetria), cuerpos=ids,
                    plano={"tipo": "plano", "id": ref}, combinar=combine)
    return _agregar(sesion, op)


Pasos = str | list[str]


def _objeto_patron(sesion, bodies, features):
    """objeto, cuerpos y pasos de un patrón: cuerpos (bodies) u operaciones del timeline (features)."""
    from ..timeline.ops_solido import TIPOS_REPETIBLES
    ids = _ids_cuerpos(sesion, bodies)
    pasos = [sesion.paso(f) for f in _lista(features)]
    if ids and pasos:
        raise error("INVALID_ARGUMENTS", "Un patrón repite cuerpos (bodies) u operaciones (features), no las dos cosas.")
    if not ids and not pasos:
        raise error("INVALID_ARGUMENTS", "Indicá al menos un cuerpo en 'bodies' o una operación del timeline en "
                                         "'features'.")
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


@herramienta("rectangular_pattern", "solido",
             "Patrón rectangular de cuerpos (bodies) o de operaciones del timeline (features: un agujero, una "
             "extrusión que corta… se repiten sobre la pieza, como el patrón de features de Fusion): copias en una o "
             "dos direcciones (ejes del origen), con la separación entre copias consecutivas. Con bodies las copias "
             "son cuerpos nuevos (o se unen al original con combine). Cantidades incluyen el original.", modifica=True)
def rectangular_pattern(sesion, bodies: Cuerpos | None = None, x_count: int = 1, x_spacing: Expr = "10 mm",
                        y_count: int = 1, y_spacing: Expr = "10 mm", axis1: Literal["x", "y", "z"] = "x",
                        axis2: Literal["x", "y", "z"] = "y", combine: bool = False, features: Pasos | None = None):
    """
    bodies: cuerpo(s) a repetir (id o nombre).
    x_count: cantidad de instancias en la dirección 1, original incluido (1 = sin copias; x_count × y_count ≤ 10.000).
    x_spacing: separación entre instancias consecutivas en la dirección 1 (mm o expresión). Se guarda como d1 con distribucion="espaciado": edit_feature d1 sigue siendo la separación.
    y_count: cantidad de instancias en la dirección 2, original incluido (x_count × y_count ≤ 10.000).
    y_spacing: separación entre instancias consecutivas en la dirección 2 (se guarda como d2).
    axis1: eje de la dirección 1 ("x", "y" o "z").
    axis2: eje de la dirección 2.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos: su herramienta (el agujero, la extrusión que corta o une…) se copia y se aplica con la misma operación a los mismos cuerpos, como el patrón de features de Fusion. No se combina con bodies.
    """
    objeto = _objeto_patron(sesion, bodies, features)
    if x_count < 1 or y_count < 1:
        raise error("INVALID_ARGUMENTS", "x_count e y_count tienen que ser 1 o más.")
    if x_count == 1 and y_count == 1:
        raise error("INVALID_ARGUMENTS", "Con x_count = 1 e y_count = 1 el patrón no crea copias.")
    if y_count > 1 and axis1 == axis2:
        raise error("INVALID_ARGUMENTS", "axis1 y axis2 tienen que ser ejes distintos.")
    _exigir_instancias(x_count * y_count, "x_count × y_count")
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón rectangular", OpPatron,
                                               lambda o: o.p["forma_patron"] == "rectangular"),
                  forma_patron="rectangular", dir1={"tipo": "eje", "id": axis1.upper()}, n1=x_count,
                  d1=texto_expr(x_spacing), dir2={"tipo": "eje", "id": axis2.upper()} if y_count > 1 else None,
                  n2=y_count, d2=texto_expr(y_spacing), distribucion="espaciado", combinar=combine, **objeto)
    return _agregar_patron(sesion, op)


@herramienta("circular_pattern", "solido",
             "Patrón circular de cuerpos (bodies) o de operaciones del timeline (features) alrededor de un eje del "
             "origen (x, y o z). Con 360° las copias se reparten en toda la vuelta; con menos, entre el original y el "
             "ángulo total. count incluye el original.", modifica=True)
def circular_pattern(sesion, count: int, bodies: Cuerpos | None = None, axis: Literal["x", "y", "z"] = "z",
                     total_angle: Expr = 360, combine: bool = False, features: Pasos | None = None):
    """
    count: cantidad de instancias, original incluido (2 a 10.000).
    bodies: cuerpo(s) a repetir (id o nombre).
    axis: eje de giro del origen: "x", "y" o "z".
    total_angle: ángulo total en grados (número o expresión); 360 = vuelta completa. Se guarda como angulo con distribucion="extension".
    combine: true para unir las copias al cuerpo original (solo con bodies).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    """
    objeto = _objeto_patron(sesion, bodies, features)
    if count < 2:
        raise error("INVALID_ARGUMENTS", "count tiene que ser 2 o más (el original cuenta).")
    _exigir_instancias(count, "count")
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón circular", OpPatron,
                                               lambda o: o.p["forma_patron"] == "circular"),
                  forma_patron="circular", eje={"tipo": "eje", "id": axis.upper()}, n=count,
                  angulo=texto_expr(total_angle), distribucion="extension", combinar=combine, **objeto)
    return _agregar_patron(sesion, op)


def _xyz_api(valores, que):
    if not isinstance(valores, (list, tuple)) or len(valores) != 3:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser [x, y, z] (3 valores): recibió {valores!r}.")
    return [texto_expr(v) for v in valores]


def _params_puntos(sesion, points, sketch, reference):
    """Parámetros del Patrón en puntos: coordenadas (points), los puntos sueltos de un boceto (sketch) y la
    referencia."""
    coordenadas = [_xyz_api(p, f"points[{i}]") for i, p in enumerate(points or [])]
    puntos = []
    if sketch is not None:
        sop, br = boceto_activo(sesion, sketch)
        en_curvas = {i for c in br.boceto.curvas.values() for i in c.puntos()}
        if not [i for i in br.boceto.puntos if i not in en_curvas]:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{sop.nombre}» no tiene puntos sueltos (puntos que no son de "
                                            "ninguna curva).", "Dibujalos con draw_point.")
        puntos.append({"tipo": "boceto", "boceto": sop.id})
    if not coordenadas and not puntos:
        raise error("INVALID_ARGUMENTS", "Indicá los puntos: coordenadas en 'points' y/o un boceto con puntos sueltos "
                                         "en 'sketch'.")
    return {"forma_patron": "puntos", "coordenadas": coordenadas, "puntos": puntos,
            "referencia_xyz": _xyz_api(reference, "reference") if reference is not None else []}


ESPACIADOS = {"extent": "extension", "spacing": "espaciado"}
ORIENTACIONES = {"identical": "identica", "path_direction": "direccion_ruta"}


def _params_ruta(sesion, path_sketch, path_curves, count, distance, spacing_mode, start, orientation, twist, symmetric):
    """Parámetros del Patrón en ruta (curvas de un boceto, como la ruta de sweep)."""
    if count < 2:
        raise error("INVALID_ARGUMENTS", "count tiene que ser 2 o más (el original cuenta).")
    _exigir_instancias(2 * count - 1 if symmetric else count, "count")
    rop, rbr = boceto_activo(sesion, path_sketch)
    curvas = list(path_curves) if path_curves else [c.id for c in rbr.boceto.curvas.values() if not c.construccion]
    for cid in curvas:
        if cid not in rbr.boceto.curvas:
            raise error("ENTITY_NOT_FOUND", f"El boceto «{rop.nombre}» no tiene la curva {cid}.")
    if not curvas:
        raise error("ENTITY_NOT_FOUND", f"El boceto de la ruta «{rop.nombre}» no tiene curvas.")
    if spacing_mode not in ESPACIADOS or orientation not in ORIENTACIONES:
        raise error("INVALID_ARGUMENTS", f"spacing_mode: {', '.join(ESPACIADOS)}; orientation: "
                                         f"{', '.join(ORIENTACIONES)}.")
    return {"forma_patron": "ruta", "ruta": [{"tipo": "curva_boceto", "boceto": rop.id, "curva": c} for c in curvas],
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
                  points: list[list[Expr]] | None = None, sketch: str | None = None,
                  reference: list[Expr] | None = None, combine: bool = False):
    """
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    points: puntos [[x, y, z], …] en mm (números o expresiones) donde va cada copia.
    sketch: id o nombre de un boceto: se usan todos sus puntos sueltos (los que no son de ninguna curva) y siguen al boceto si se edita.
    reference: punto [x, y, z] que se lleva a cada punto; vacío = el origen [0, 0, 0].
    combine: true para unir las copias al cuerpo original (solo con bodies).
    """
    objeto = _objeto_patron(sesion, bodies, features)
    params = _params_puntos(sesion, points, sketch, reference)
    _exigir_instancias(len(params["coordenadas"]) + 1, "points")
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón en puntos", OpPatron,
                                               lambda o: o.p["forma_patron"] == "puntos"),
                  combinar=combine, **params, **objeto)
    return _agregar_patron(sesion, op)


@herramienta("path_pattern", "solido",
             "Patrón en ruta (Pattern on Path de Fusion; con twist, el Twisted Path Array de FreeCAD): copias de "
             "cuerpos (bodies) —o de operaciones del timeline (features)— a lo largo de curvas de un boceto. count "
             "incluye el original. distance es el largo TOTAL de la primera a la última (spacing_mode=\"extent\") o la "
             "separación entre copias (\"spacing\"). start ubica el original sobre la ruta (0 a 1). "
             "orientation=\"path_direction\" gira cada copia con la ruta; twist además la gira alrededor de la ruta, "
             "de a poco, hasta ese ángulo total en la última.", modifica=True)
def path_pattern(sesion, path_sketch: str, count: int, distance: Expr, bodies: Cuerpos | None = None,
                 features: Pasos | None = None, path_curves: list[int] | None = None,
                 spacing_mode: Literal["extent", "spacing"] = "extent", start: Expr = 0,
                 orientation: Literal["identical", "path_direction"] = "identical", twist: Expr = 0,
                 symmetric: bool = False, combine: bool = False):
    """
    path_sketch: id o nombre del boceto con la ruta.
    count: cantidad de instancias, original incluido (2 a 10.000).
    distance: largo total (extent) o separación entre copias (spacing), en mm o expresión.
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    path_curves: ids de las curvas de la ruta (get_sketch); vacío = todas las curvas no de construcción del boceto.
    spacing_mode: "extent" (distance es el largo total) o "spacing" (distance es la separación).
    start: dónde está el original sobre la ruta, de 0 (inicio) a 1 (fin).
    orientation: "identical" (las copias solo se trasladan) o "path_direction" (giran con la tangente de la ruta).
    twist: giro total alrededor de la ruta en grados (número o expresión): la copia k gira twist · k / (count − 1).
    symmetric: true para repartir count copias hacia cada lado del original.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    """
    objeto = _objeto_patron(sesion, bodies, features)
    params = _params_ruta(sesion, path_sketch, path_curves, count, distance, spacing_mode, start, orientation, twist,
                          symmetric)
    doc = sesion.doc
    op = OpPatron(doc.nuevo_id(), nombre_nuevo(doc, "Patrón en ruta", OpPatron, lambda o: o.p["forma_patron"] == "ruta"),
                  combinar=combine, **params, **objeto)
    return _agregar_patron(sesion, op)


_CLAVES_TRANSFORMACION = {
    "rectangular": {"type", "axis", "count", "spacing", "axis2", "count2", "spacing2", "symmetric"},
    "circular": {"type", "axis", "count", "total_angle", "symmetric"},
    "mirror": {"type", "plane"},
    "points": {"type", "points", "sketch", "reference"},
    "path": {"type", "path_sketch", "path_curves", "count", "distance", "spacing_mode", "start", "orientation",
             "twist", "symmetric"},
}


def _eje_api(valor, que):
    eje = str(valor or "").strip().lower()
    if eje not in ("x", "y", "z"):
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser \"x\", \"y\" o \"z\": recibió {valor!r}.")
    return {"tipo": "eje", "id": eje.upper()}


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
        dir2 = _eje_api(t["axis2"], f"{que}.axis2") if n2 > 1 else None
        d = {"tipo": "rectangular", "dir1": _eje_api(t.get("axis", "x"), f"{que}.axis"), "n1": n1,
             "d1": texto_expr(t.get("spacing", 10)), "dir2": dir2, "n2": n2, "d2": texto_expr(t.get("spacing2", 10)),
             "distribucion": "espaciado", "simetrico": bool(t.get("symmetric", False))}
        if n2 > 1 and "axis2" not in t:
            raise error("INVALID_ARGUMENTS", f"{que}: con count2 > 1 falta axis2.")
        k = 2 if d["simetrico"] else 1
        return d, (k * n1 - k + 1) * (k * n2 - k + 1)
    if tipo == "circular":
        n = _entero_api(t.get("count", 2), f"{que}.count", 2)
        d = {"tipo": "circular", "eje": _eje_api(t.get("axis", "z"), f"{que}.axis"), "n": n,
             "angulo": texto_expr(t.get("total_angle", 360)), "distribucion": "extension",
             "simetrico": bool(t.get("symmetric", False))}
        return d, 2 * n - 1 if d["simetrico"] else n
    if tipo == "mirror":
        return {"tipo": "simetria", "plano": {"tipo": "plano", "id": referencia_plano(sesion, t.get("plane", "YZ"))}}, 2
    if tipo == "points":
        d = _params_puntos(sesion, t.get("points"), t.get("sketch"), t.get("reference"))
        d["tipo"] = d.pop("forma_patron")
        return d, len(d["coordenadas"]) + 1
    d = _params_ruta(sesion, t.get("path_sketch"), t.get("path_curves"), _entero_api(t.get("count"), f"{que}.count", 2),
                     t.get("distance", 10), t.get("spacing_mode", "extent"), t.get("start", 0),
                     t.get("orientation", "identical"), t.get("twist", 0), bool(t.get("symmetric", False)))
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
                    combine: bool = False):
    """
    transforms: lista ordenada de transformaciones (dicts con "type": rectangular, circular, mirror, points o path; ver la descripción).
    bodies: cuerpo(s) a repetir (id o nombre).
    features: pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
    combine: true para unir las copias al cuerpo original (solo con bodies).
    """
    objeto = _objeto_patron(sesion, bodies, features)
    if not transforms:
        raise error("INVALID_ARGUMENTS", "transforms necesita al menos una transformación.")
    lista, total = [], 1
    for i, t in enumerate(transforms):
        d, n = _transformacion_api(sesion, t, i)
        lista.append(d)
        total *= n
    _exigir_instancias(total, "el producto de las transformaciones")
    doc = sesion.doc
    op = OpMultitransformar(doc.nuevo_id(), nombre_nuevo(doc, "Multitransformación", OpMultitransformar),
                            transformaciones=lista, combinar=combine, **objeto)
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


@herramienta("move_body", "solido",
             "Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] "
             "grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA "
             "a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate "
             "[0, 0, 15] queda en z = 17). Para llevarlo a una posición absoluta usá position = [x, y, z]: el centro de "
             "la caja de los cuerpos (después del giro) queda ahí. pivot='center' es el promedio de los centros de las "
             "cajas de los cuerpos y se RECALCULA con la geometría (si la pieza es asimétrica o se edita, el giro "
             "cambia de lugar); pivot='origin' gira alrededor del origen y da un giro estable. El resultado trae "
             "center.before y center.after.", modifica=True)
def move_body(sesion, body: Cuerpos, translate: list[Expr] | None = None, rotate: list[Expr] | None = None,
              pivot: Literal["center", "origin"] = "center", copy: bool = False, position: list[Expr] | None = None):
    """
    body: cuerpo(s) a mover (id o nombre).
    translate: DESPLAZAMIENTO [dx, dy, dz] en mm que se suma a la posición actual (números o expresiones); vacío = sin desplazamiento.
    rotate: giro [rx, ry, rz] en grados (números o expresiones); vacío = sin giro.
    pivot: centro del giro: "center" (centro de las cajas de los cuerpos, se recalcula) u "origin" (origen, estable).
    copy: true para dejar el original y crear cuerpos nuevos con el movimiento.
    position: posición ABSOLUTA [x, y, z] en mm (números o expresiones) del centro de la caja de los cuerpos; no se
        combina con translate. El paso guarda el desplazamiento que hace falta ahora (position − centro, con los
        parámetros de position): si después cambia la forma de la pieza, el centro se corre con ella.
    """
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
    op = OpMover(doc.nuevo_id(), nombre_nuevo(doc, "Mover", OpMover), cuerpos=ids, tipo="libre",
                 dx=texto_expr(t[0]), dy=texto_expr(t[1]), dz=texto_expr(t[2]),
                 rx=texto_expr(g[0]), ry=texto_expr(g[1]), rz=texto_expr(g[2]),
                 pivote={"tipo": "punto", "id": "O"} if pivot == "origin" else None, copiar=copy)
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

