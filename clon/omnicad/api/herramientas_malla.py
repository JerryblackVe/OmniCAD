# -*- coding: utf-8 -*-
"""
Herramientas del grupo "malla" (espacio MALLA de Fusion y Malla › Limpiar de Blender; operaciones en
`timeline/ops_malla.py`, núcleo en `nucleo/malla.py`): teselar un sólido, reparar, limpiar, generar grupos de caras,
reducir, remallar, suavizar, vaciar, cortar con un plano, combinar, separar, invertir normales, escalar y convertir
a sólido, más la información de cada malla.

Un cuerpo de malla (type "mesh" en get_scene_info) son triángulos indexados en mm. Se trae de un archivo con
insert_file (.stl, .obj, .3mf, .ply: entra en el documento ACTUAL; open_document en cambio lo abre como documento
nuevo) o se crea con tessellate desde un sólido o una superficie. Cada herramienta deja UN paso en el timeline
(editable con edit_feature) y devuelve los cuerpos creados, modificados (con sus números de antes) y quitados; de
cada malla: triángulos, vértices, grupos de caras, cáscaras, si es cerrada y orientada, aristas de borde y no
manifold, triángulos degenerados, volumen (mm³), área (mm²) y caja envolvente.
"""
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import malla as ml
from ..timeline import entidades as ent
from ..timeline.ops_malla import (OpCombinarMallas, OpConvertirMalla, OpCortarPlanoMalla, OpEscalarMalla,
                                  OpGruposCaras, OpInvertirNormalMalla, OpLimpiarMalla, OpReducirMalla, OpRemallar,
                                  OpRepararMalla, OpSepararMalla, OpSuavizarMalla, OpTeselar, OpVaciadoMalla)
from .errores import error
from .herramientas_boceto import referencia_plano, texto_expr
from .herramientas_ensamble import nombre_paso
from .registro import Expr, herramienta

Cuerpos = str | list[str]
_TIPOS = {"solido": "solid", "superficie": "surface", "malla": "mesh"}
_NO_ES_MALLA = ("Las herramientas del grupo malla trabajan con cuerpos de malla (type 'mesh' en get_scene_info).",
                "Un sólido o una superficie pasa a malla con tessellate; un .stl, .obj, .3mf o .ply entra con "
                "insert_file.", "get_scene_info dice el tipo de cada cuerpo.")


def _r(x):
    return None if x is None else round(float(x), 4) + 0.0


def _caja(caja):
    if not caja:
        return None
    p0, p1 = caja
    return {"min": [_r(v) for v in p0], "max": [_r(v) for v in p1],
            "size": [_r(b - a) for a, b in zip(p0, p1, strict=True)]}


def _es_malla(c):
    return getattr(c, "tipo", "solido") == "malla"


def _lista(x):
    return [] if x is None else [x] if isinstance(x, str) else list(x)


def _cuerpos(sesion, bodies, mallas=True, que="bodies"):
    """Cuerpos pedidos (id o nombre, sin repetir). `mallas`: True exige cuerpos de malla, False exige que NO lo sean."""
    refs = [r for r in _lista(bodies) if str(r).strip()]
    if not refs:
        raise error("INVALID_ARGUMENTS", f"Indicá al menos un cuerpo en {que}.", *_NO_ES_MALLA[:1],
                    "get_scene_info lista los cuerpos con su id, nombre y tipo.")
    salida = []
    for r in refs:
        c = sesion.cuerpo(r)
        if mallas and not _es_malla(c):
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» no es un cuerpo de malla (es "
                        f"{_TIPOS.get(getattr(c, 'tipo', 'solido'), 'solid')}).", *_NO_ES_MALLA)
        if not mallas and _es_malla(c):
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» ya es un cuerpo de malla.",
                        "tessellate convierte sólidos y superficies en mallas.",
                        "Para rehacer los triángulos de una malla: remesh; para bajarlos: reduce_mesh.")
        if c.id not in (x.id for x in salida):
            salida.append(c)
    return salida


def info_malla(sesion, c):
    """Números de un cuerpo de malla (los de get_mesh_info)."""
    a = ml.analizar(c.forma)
    return {"id": c.id, "name": sesion.nombre_cuerpo(c), "type": "mesh", "triangles": a["caras"],
            "vertices": a["vertices"], "face_groups": a["grupos"], "shells": a["cascaras"], "closed": a["cerrada"],
            "oriented": a["orientada"], "positive_volume": a["volumen_positivo"],
            "boundary_edges": a["aristas_borde"], "non_manifold_edges": a["aristas_no_manifold"],
            "degenerate_triangles": a["degenerados"], "volume": _r(a["volumen"]), "area": _r(a["area"]),
            "bounding_box": _caja(c.forma.caja())}


def _info_cuerpo(sesion, c):
    if _es_malla(c):
        return info_malla(sesion, c)
    tipo = getattr(c, "tipo", "solido")
    return {"id": c.id, "name": sesion.nombre_cuerpo(c), "type": _TIPOS.get(tipo, tipo),
            "volume": _r(geo.volumen(c.forma)) if tipo == "solido" else None, "area": _r(geo.area(c.forma)),
            "valid": geo.es_valida(c.forma), "bounding_box": _caja(geo.caja_envolvente(c.forma))}


def _antes(forma):
    """Lo principal de una forma antes del paso (para comparar con lo de después)."""
    if hasattr(forma, "caras") and hasattr(forma, "vertices"):
        return {"triangles": int(len(forma.caras)), "vertices": int(len(forma.vertices)),
                "closed": forma.es_cerrada(), "volume": _r(forma.volumen()), "area": _r(forma.area())}
    return {"volume": _r(geo.volumen(forma)) if geo.solidos(forma) else None, "area": _r(geo.area(forma))}


def _agregar(sesion, op):
    """Agrega el paso (la transacción de la herramienta lo deshace si queda con error) e informa los cambios."""
    antes = {c.id: c.forma for c in sesion.doc.estado_final.cuerpos.values()}
    sesion.doc.agregar(op)
    cuerpos = sesion.doc.estado_final.cuerpos
    modificados = [dict(_info_cuerpo(sesion, c), before=_antes(antes[cid])) for cid, c in cuerpos.items()
                   if cid in antes and antes[cid] is not c.forma]
    return {"feature": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "bodies_created": [_info_cuerpo(sesion, c) for cid, c in cuerpos.items() if cid not in antes],
            "bodies_modified": modificados, "bodies_removed": [cid for cid in antes if cid not in cuerpos]}


def _paso(sesion, clase, name, base, **params):
    return clase(sesion.doc.nuevo_id(), nombre_paso(sesion, name, base, clase), **params)


def _positivo(valor, que):
    if isinstance(valor, (int, float)) and not valor > 0:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser mayor que cero (recibió {valor:g}).")


# ---------------------------------------------------------------- información
@herramienta("get_mesh_info", "malla", "Información de los cuerpos de malla (uno o todos): triángulos, vértices, grupos "
             "de caras, cáscaras (partes conexas), si es cerrada (estanca) y orientada, si el volumen es positivo "
             "(normales hacia afuera), aristas de borde (agujeros) y no manifold, triángulos degenerados, volumen "
             "(mm³), área (mm²) y caja envolvente. No cambia el documento.")
def get_mesh_info(sesion, body: str | None = None):
    """
    body: id o nombre del cuerpo de malla; vacío = todos los cuerpos de malla del documento.
    """
    if body is not None and str(body).strip():
        cuerpos = _cuerpos(sesion, body)
    else:
        cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if _es_malla(c)]
        if not cuerpos:
            sesion.avisar("El documento no tiene cuerpos de malla: insert_file trae un .stl/.obj/.3mf/.ply y "
                          "tessellate convierte un sólido.")
    return {"bodies": [info_malla(sesion, c) for c in cuerpos], "count": len(cuerpos),
            "units": {"length": "mm", "area": "mm2", "volume": "mm3"}}


# ---------------------------------------------------------------- crear y preparar
@herramienta("tessellate", "malla", "Convierte sólidos o superficies en cuerpos de malla (MALLA › Malla de cuerpo "
             "B-Rep de Fusion): un grupo de caras por cara del B-rep. refinement: low, medium o high (desvío de 0,2 % / "
             "0,05 % / 0,01 % de la diagonal de la caja y 30° / 15° / 8°). keep_original=false borra el cuerpo B-rep.",
             modifica=True)
def tessellate(sesion, bodies: Cuerpos, refinement: Literal["low", "medium", "high"] = "medium",
               keep_original: bool = True, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos sólidos o de superficie (uno o una lista).
    refinement: finura de los triángulos: "low", "medium" o "high".
    keep_original: true conserva el cuerpo B-rep además de la malla nueva.
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies, mallas=False)]
    refinamiento = {"low": "bajo", "medium": "medio", "high": "alto"}[refinement]
    return _agregar(sesion, _paso(sesion, OpTeselar, name, "Teselar", cuerpos=ids, refinamiento=refinamiento,
                                  mantener=keep_original))


_REPARAR = {"close_holes": "cerrar_agujeros", "merge_vertices": "unir_vertices", "stitch_and_remove": "coser_y_quitar",
            "rebuild": "reconstruir"}


@herramienta("repair_mesh", "malla", "Repara mallas (MALLA › PREPARAR › Reparar de Fusion). kind: close_holes (une "
             "vértices idénticos, orienta las normales y tapa los agujeros), merge_vertices (solo une los vértices "
             "casi coincidentes), stitch_and_remove (además cose, corrige triángulos degenerados, quita caras dobles y "
             "partes diminutas) o rebuild (lo anterior y un remallado uniforme). Para elegir cada paso de limpieza por "
             "separado: clean_mesh.", modifica=True)
def repair_mesh(sesion, bodies: Cuerpos, kind: Literal["close_holes", "merge_vertices", "stitch_and_remove",
                                                         "rebuild"] = "close_holes", name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    kind: "close_holes", "merge_vertices", "stitch_and_remove" o "rebuild".
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpRepararMalla, name, "Reparar", cuerpos=ids, tipo=_REPARAR[kind]))


@herramienta("clean_mesh", "malla", "Limpia mallas paso por paso (Malla › Limpiar de Blender), en este orden y cada "
             "uno con su casilla: merge_by_distance (une los vértices a distance mm o menos), dissolve_degenerate "
             "(colapsa aristas de distance o menos y arregla triángulos sin área y caras dobles), delete_loose "
             "(vértices sin caras, triángulos aislados y, con min_shell_fraction, partes chicas), recalculate_normals "
             "(orientación consistente y hacia afuera) y fill_holes (tapa los agujeros de hasta max_hole_sides "
             "lados; 0 = todos). Triángulos a cuadriláteros no existe: la malla es solo de triángulos.", modifica=True)
def clean_mesh(sesion, bodies: Cuerpos, merge_by_distance: bool = True, distance: Expr = "0.001 mm",
               dissolve_degenerate: bool = True, delete_loose: bool = True, min_shell_fraction: float = 0.0,
               recalculate_normals: bool = True, fill_holes: bool = False, max_hole_sides: int = 0,
               name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    merge_by_distance: true une los vértices que están a distance o menos.
    distance: umbral en mm (número o expresión) para unir vértices y colapsar aristas cortas; 0 = solo los idénticos.
    dissolve_degenerate: true colapsa las aristas cortas y arregla los triángulos sin área.
    delete_loose: true borra vértices sin caras y triángulos que no comparten aristas con otros.
    min_shell_fraction: con delete_loose, borra también las partes conexas con menos de esta fracción (0 a 1) del
        área total (p. ej. 0.01 = 1 %); 0 = no.
    recalculate_normals: true orienta los triángulos de forma consistente y hacia afuera.
    fill_holes: true tapa los agujeros (cada tapa es un grupo de caras nuevo).
    max_hole_sides: con fill_holes, solo los agujeros de hasta esta cantidad de lados; 0 = todos.
    name: nombre del paso en el timeline; vacío = automático.
    """
    if isinstance(distance, (int, float)) and distance < 0:
        raise error("INVALID_ARGUMENTS", f"distance no puede ser negativa (recibió {distance:g}).")
    if not 0 <= min_shell_fraction < 1:
        raise error("INVALID_ARGUMENTS", f"min_shell_fraction es una fracción del área entre 0 y 1 (recibió "
                    f"{min_shell_fraction:g}).")
    if max_hole_sides < 0:
        raise error("INVALID_ARGUMENTS", f"max_hole_sides no puede ser negativo (recibió {max_hole_sides}).")
    if not (merge_by_distance or dissolve_degenerate or delete_loose or recalculate_normals or fill_holes):
        raise error("INVALID_ARGUMENTS", "Todos los pasos de limpieza están apagados: activá al menos uno.")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpLimpiarMalla, name, "Limpiar", cuerpos=ids, fusionar=merge_by_distance,
                                  distancia=texto_expr(distance), degenerados=dissolve_degenerate,
                                  sueltos=delete_loose, area_minima=texto_expr(min_shell_fraction),
                                  normales=recalculate_normals, rellenar=fill_holes, lados=max_hole_sides))


@herramienta("generate_face_groups", "malla", "Agrupa las caras de mallas por ángulo (MALLA › PREPARAR › Generar grupos "
             "de caras de Fusion): las vecinas cuyas normales difieren menos de angle quedan en el mismo grupo. Sirve "
             "para separate_mesh by=face_groups y para convertir con method=prismatic.", modifica=True)
def generate_face_groups(sesion, bodies: Cuerpos, angle: Expr = 30, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    angle: ángulo límite entre caras vecinas, en grados (número o expresión), entre 0 y 180.
    name: nombre del paso en el timeline; vacío = automático.
    """
    if isinstance(angle, (int, float)) and not 0 < angle < 180:
        raise error("INVALID_ARGUMENTS", f"angle va entre 0 y 180 grados (recibió {angle:g}).")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpGruposCaras, name, "Grupos de caras", cuerpos=ids,
                                  angulo=texto_expr(angle)))


# ---------------------------------------------------------------- modificar
_REDUCIR = {"proportion": "proporcion", "face_count": "caras", "tolerance": "tolerancia"}


@herramienta("reduce_mesh", "malla", "Baja la cantidad de triángulos de mallas (MALLA › MODIFICAR › Reducir de Fusion; "
             "colapso de aristas con error cuadrático). mode: proportion (fracción de los triángulos actuales), "
             "face_count (cantidad objetivo) o tolerance (desvío máximo en mm).", modifica=True)
def reduce_mesh(sesion, bodies: Cuerpos, mode: Literal["proportion", "face_count", "tolerance"] = "proportion",
                proportion: Expr = 0.5, face_count: int = 1000, tolerance: Expr = 0.1, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    mode: "proportion", "face_count" o "tolerance".
    proportion: con mode=proportion, fracción de triángulos que queda (mayor que 0 y hasta 1).
    face_count: con mode=face_count, cantidad de triángulos objetivo (al menos 4).
    tolerance: con mode=tolerance, desvío máximo en mm (número o expresión).
    name: nombre del paso en el timeline; vacío = automático.
    """
    if mode == "proportion" and isinstance(proportion, (int, float)) and not 0 < proportion <= 1:
        raise error("INVALID_ARGUMENTS", f"proportion va de 0 (sin incluir) a 1 (recibió {proportion:g}).")
    if mode == "face_count" and face_count < 4:
        raise error("INVALID_ARGUMENTS", f"face_count tiene que ser al menos 4 (recibió {face_count}).")
    if mode == "tolerance":
        _positivo(tolerance, "tolerance")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpReducirMalla, name, "Reducir", cuerpos=ids, tipo=_REDUCIR[mode],
                                  proporcion=texto_expr(proportion), caras=face_count,
                                  tolerancia=texto_expr(tolerance)))


@herramienta("remesh", "malla", "Rehace los triángulos de mallas con un tamaño parejo (MALLA › MODIFICAR › Remallar de "
             "Fusion). density > 1 da más triángulos (el largo de arista objetivo es el largo medio / √density). "
             "Tiene un tope de 100.000 triángulos: si se pasaría, falla antes de calcular y dice cuánto bajar.",
             modifica=True)
def remesh(sesion, bodies: Cuerpos, density: Expr = 1, preserve_boundaries: bool = True,
           preserve_sharp_edges: bool = True, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    density: densidad relativa de triángulos (mayor que 0; 1 = parecida a la actual).
    preserve_boundaries: true no toca los bordes abiertos.
    preserve_sharp_edges: true conserva las aristas vivas (más de 30° entre caras) y los bordes entre grupos.
    name: nombre del paso en el timeline; vacío = automático.
    """
    _positivo(density, "density")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpRemallar, name, "Remallar", cuerpos=ids, densidad=texto_expr(density),
                                  preservar_bordes=preserve_boundaries,
                                  preservar_aristas_vivas=preserve_sharp_edges))


@herramienta("smooth_mesh", "malla", "Suaviza mallas sin encogerlas (MALLA › MODIFICAR › Suavizar de Fusion; filtro de "
             "Taubin). Los bordes abiertos quedan fijos; redondea las aristas vivas (avisa si el volumen de una malla "
             "cerrada cambia más de 1 %).", modifica=True)
def smooth_mesh(sesion, bodies: Cuerpos, strength: Expr = 0.5, iterations: int = 10, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    strength: intensidad del suavizado, de 0 a 1.
    iterations: cantidad de pasadas (al menos 1).
    name: nombre del paso en el timeline; vacío = automático.
    """
    if isinstance(strength, (int, float)) and not 0 <= strength <= 1:
        raise error("INVALID_ARGUMENTS", f"strength va de 0 a 1 (recibió {strength:g}).")
    if iterations < 1:
        raise error("INVALID_ARGUMENTS", f"iterations tiene que ser al menos 1 (recibió {iterations}).")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpSuavizarMalla, name, "Suavizar", cuerpos=ids,
                                  intensidad=texto_expr(strength), iteraciones=iterations))


@herramienta("shell_mesh", "malla", "Ahueca mallas cerradas con un espesor de pared (MALLA › MODIFICAR › Vaciado de "
             "Fusion): suma una cáscara interior desplazada thickness mm hacia adentro. Aproximado: avisa si la pared "
             "interior se pliega o se cruza (usá un espesor menor).", modifica=True)
def shell_mesh(sesion, bodies: Cuerpos, thickness: Expr = 2, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla (tienen que ser cerrados).
    thickness: espesor de la pared en mm (número o expresión, mayor que cero).
    name: nombre del paso en el timeline; vacío = automático.
    """
    _positivo(thickness, "thickness")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpVaciadoMalla, name, "Vaciado de malla", cuerpos=ids,
                                  espesor=texto_expr(thickness)))


_CORTES = {"trim": "recortar", "split_body": "partir", "split_faces": "partir_caras"}


@herramienta("plane_cut_mesh", "malla", "Corta mallas con un plano (MALLA › MODIFICAR › Corte de plano de Fusion). "
             "kind: trim (queda el lado hacia donde apunta la normal del plano; flip conserva el otro), split_body "
             "(dos cuerpos, uno por lado) o split_faces (una malla con los triángulos partidos sobre el plano). fill "
             "tapa el corte (un grupo de caras nuevo). Normales: XY = +Z, YZ = +X, XZ = −Y; kept_side_normal en el "
             "resultado dice cuál quedó.", modifica=True)
def plane_cut_mesh(sesion, bodies: Cuerpos, plane: str, kind: Literal["trim", "split_body", "split_faces"] = "trim",
                   fill: bool = True, flip: bool = False, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    plane: "XY", "XZ", "YZ" o el id o nombre de un plano de construcción.
    kind: "trim", "split_body" o "split_faces".
    fill: true tapa el corte con triángulos.
    flip: true invierte el lado que se conserva (en trim) o el orden de las partes (en split_body).
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    ref = {"tipo": "plano", "id": referencia_plano(sesion, plane)}
    resultado = _agregar(sesion, _paso(sesion, OpCortarPlanoMalla, name, "Corte de plano", cuerpos=ids, plano=ref,
                                       tipo=_CORTES[kind], rellenar=fill, invertir=flip))
    plano = ent.resolver(ref, sesion.doc.estado_final).plano
    signo = -1.0 if flip else 1.0
    resultado["plane"] = {"origin": [_r(v) for v in plano.origen], "normal": [_r(v) for v in plano.normal]}
    resultado["kept_side_normal"] = [_r(signo * v) for v in plano.normal]
    return resultado


_COMBINAR = {"join": "unir", "cut": "cortar", "intersect": "intersecar", "merge": "fusionar"}


@herramienta("combine_meshes", "malla", "Combina cuerpos de malla (MALLA › MODIFICAR › Combinar de Fusion). operation: "
             "join, cut o intersect (booleanas reales: las mallas tienen que ser cerradas; repair_mesh o clean_mesh "
             "antes si no) o merge (junta los triángulos sin tocarlos). El resultado queda en target; las "
             "herramientas se borran salvo keep_tools=true.", modifica=True)
def combine_meshes(sesion, target: str, tools: Cuerpos, operation: Literal["join", "cut", "intersect", "merge"] = "join",
                   keep_tools: bool = False, name: str | None = None):
    """
    target: id o nombre del cuerpo de malla de destino.
    tools: id o nombre de los cuerpos de malla herramienta (uno o una lista).
    operation: "join", "cut", "intersect" o "merge".
    keep_tools: true conserva los cuerpos herramienta.
    name: nombre del paso en el timeline; vacío = automático.
    """
    (destino,) = _cuerpos(sesion, target, que="target")
    herramientas = _cuerpos(sesion, tools, que="tools")
    if any(h.id == destino.id for h in herramientas):
        raise error("INVALID_ARGUMENTS", "El cuerpo de destino no puede ser también herramienta.")
    return _agregar(sesion, _paso(sesion, OpCombinarMallas, name, "Combinar mallas", objetivo=destino.id,
                                  herramientas=[h.id for h in herramientas], operacion=_COMBINAR[operation],
                                  mantener=keep_tools))


@herramienta("separate_mesh", "malla", "Separa mallas en varios cuerpos (MALLA › MODIFICAR › Separar de Fusion): by "
             "shells, un cuerpo por parte conexa; by face_groups, uno por grupo de caras (generate_face_groups los "
             "crea). Si una malla tiene una sola parte, avisa y no cambia.", modifica=True)
def separate_mesh(sesion, bodies: Cuerpos, by: Literal["shells", "face_groups"] = "shells", name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    by: "shells" (partes conexas) o "face_groups" (grupos de caras).
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpSepararMalla, name, "Separar", cuerpos=ids,
                                  tipo={"shells": "cascaras", "face_groups": "grupos"}[by]))


@herramienta("reverse_mesh_normals", "malla", "Da vuelta la orientación de todos los triángulos de mallas (MALLA › "
             "MODIFICAR › Invertir normal de Fusion): el volumen cambia de signo. Para orientar bien una malla con "
             "normales mezcladas: clean_mesh con recalculate_normals.", modifica=True)
def reverse_mesh_normals(sesion, bodies: Cuerpos, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpInvertirNormalMalla, name, "Invertir normal", cuerpos=ids))


@herramienta("scale_mesh", "malla", "Escala mallas desde el origen (MALLA › MODIFICAR › Escalar malla de Fusion): "
             "uniforme con factor_x solo, o distinto en cada eje. Un factor negativo espeja (las normales siguen "
             "hacia afuera).", modifica=True)
def scale_mesh(sesion, bodies: Cuerpos, factor_x: Expr = 1, factor_y: Expr | None = None,
               factor_z: Expr | None = None, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    factor_x: factor de escala en X (número o expresión, distinto de cero); sin factor_y ni factor_z, en los tres ejes.
    factor_y: factor en Y; vacío = el de factor_x.
    factor_z: factor en Z; vacío = el de factor_x.
    name: nombre del paso en el timeline; vacío = automático.
    """
    factores = [factor_x, factor_x if factor_y is None else factor_y, factor_x if factor_z is None else factor_z]
    for valor, que in zip(factores, ("factor_x", "factor_y", "factor_z"), strict=True):
        if isinstance(valor, (int, float)) and valor == 0:
            raise error("INVALID_ARGUMENTS", f"{que} no puede ser cero.")
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    fx, fy, fz = (texto_expr(f) for f in factores)
    return _agregar(sesion, _paso(sesion, OpEscalarMalla, name, "Escalar malla", cuerpos=ids, fx=fx, fy=fy, fz=fz))


@herramienta("convert_mesh", "malla", "Convierte mallas en cuerpos B-rep (MALLA › MODIFICAR › Convertir malla de Fusion): "
             "sólido si la malla es cerrada, superficie si no. method: faceted (una cara plana por triángulo) o "
             "prismatic (une las caras coplanares vecinas del mismo grupo; no reconoce cilindros). Máximo 50.000 "
             "triángulos: reduce_mesh antes si hay más. keep_original=true conserva la malla.", modifica=True)
def convert_mesh(sesion, bodies: Cuerpos, method: Literal["faceted", "prismatic"] = "faceted",
                 keep_original: bool = False, name: str | None = None):
    """
    bodies: id o nombre de los cuerpos de malla.
    method: "faceted" o "prismatic".
    keep_original: true conserva el cuerpo de malla además del B-rep nuevo.
    name: nombre del paso en el timeline; vacío = automático.
    """
    ids = [c.id for c in _cuerpos(sesion, bodies)]
    return _agregar(sesion, _paso(sesion, OpConvertirMalla, name, "Convertir malla", cuerpos=ids,
                                  metodo={"faceted": "facetado", "prismatic": "prismatico"}[method],
                                  mantener=keep_original))
