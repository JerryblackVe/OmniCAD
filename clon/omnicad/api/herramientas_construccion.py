"""Construcción, fijaciones, lienzos y cuerpos congelados, sin interfaz gráfica."""
import base64
import io
import warnings
from pathlib import Path
from typing import Literal

from PIL import Image

from ..nucleo import construccion as cs
from ..nucleo import fijaciones as fj
from ..nucleo import referencias
from ..nucleo.analisis import TABLA_MATERIALES
from ..timeline import entidades as ent
from ..timeline.operaciones import OpOperacionBase
from ..timeline.ops_construir import OpEje, OpPunto, OpSCU, lugar_en
from ..timeline.ops_fijacion import OpFijacion
from ..timeline.ops_insertar import OpLienzo
from . import selectores as sl
from .errores import desde_mensaje, error
from .herramientas_avanzado import _una
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_solido import Cuerpos, _agregar, _ids_cuerpos, _numero_positivo
from .registro import Expr, herramienta

Referencia = str | dict | list[float]      # una lista [x, y, z] elige el vértice que está ahí
_PLANO = {"plano", "cara"}
_EJE = {"eje", "arista", "curva_boceto"}
_PUNTO = {"punto", "vertice", "punto_boceto", "forzado"}
_CURVA = {"arista", "curva_boceto"}
Redimensionar = Literal["default", "extended"]
TipoExtension = Literal["distance", "to_object"]
_REDIMENSIONAR = {"default": "predeterminado", "extended": "extendido"}


def _referencia(sesion, valor, tipos, body=None, geometria=None):
    """Resuelve una selección abreviada y comprueba el filtro del diálogo. Un punto [x, y, z] elige el vértice que está
    ahí (`sl.vertice_cercano`)."""
    if sl.es_punto3(valor):
        ref = sl.vertice_cercano(sesion, valor, body)[1]
    elif isinstance(valor, dict) and set(valor) == {"body", "vertex"}:
        if not isinstance(valor["body"], str):
            raise error("INVALID_ARGUMENTS", "body debe ser el nombre o id de un cuerpo.")
        c = sesion.cuerpo(valor["body"])
        vertices = referencias.subformas(c.forma, "vertice")
        i = valor["vertex"]
        if isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= len(vertices):
            raise error("INVALID_ARGUMENTS", "vertex debe ser un índice válido desde 1.")
        ref = referencias.referencia(c.id, vertices[i - 1], c.forma)
    elif isinstance(valor, str) and (sl.es_id(valor) or sl._separar_prefijo(valor)[0] or sl.parece_selector(valor)):
        ref = sl.referencia(*sl.elegir_uno(sesion, valor, body=body))
    else:
        ref = _una(sesion, "refs", valor, True)
        if isinstance(ref, str) and "cuerpo" in tipos:
            ref = {"tipo": "cuerpo", "cuerpo": sesion.cuerpo(ref).id}
    try:
        ent.validar(ref)
    except ent.ErrorReferencia as e:                  # un texto que no nombra nada conocido
        raise error("INVALID_ARGUMENTS", f"Referencia inválida: {valor!r}. {e}",
                    "Usá un id o nombre de construcción, un selector, un id de find_faces / find_edges, "
                    "un vértice [x, y, z], {body, vertex} o {sketch, point | curve}.") from None
    if ref["tipo"] not in tipos:
        raise error("INVALID_ARGUMENTS", f"La referencia debe ser de tipo {', '.join(sorted(tipos))}.")
    try:
        entidad = ent.resolver(ref, sesion.doc.estado_final)
    except ent.ErrorReferencia as e:
        raise error("REFERENCE_LOST", str(e)) from e
    try:
        if geometria == "plano":
            ent.como_plano(entidad)
        elif geometria == "eje":
            ent.como_eje(entidad)
        elif geometria == "direccion":
            if entidad.tipo in _PLANO:
                ent.como_plano(entidad)
            else:
                ent.como_eje(entidad)
    except ent.ErrorReferencia as e:                  # B-131: una spline donde va una línea, una cara curva donde va un plano
        raise error("INVALID_ARGUMENTS", f"Esa referencia no sirve acá: {e}") from None
    return ref


def _crear(sesion, clase, name=None, **params):
    doc = sesion.doc
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, clase.ETIQUETA, clase)
    return clase(doc.nuevo_id(), nombre, **params)


def _vector(valores):
    return [round(float(v), 8) + 0.0 for v in valores]


def agregar_construccion(sesion, op):
    """Agrega el paso. Si no se pudo calcular responde la causa real (B-130), no el id que falta en el estado."""
    sesion.doc.agregar(op)
    resultado = sesion.doc.resultado(op.id)
    if resultado.estado == "error":
        raise desde_mensaje(resultado.mensaje)


def parametros_tamano(sesion, resize, size_type, size, size_object, body):
    """Parámetros del paso para Redimensionar y Tipo de extensión."""
    if size_type == "to_object" and size_object is None:
        raise error("INVALID_ARGUMENTS", "Con size_type=to_object falta size_object.")
    return {"redimensionar": _REDIMENSIONAR[resize], "tipo_extension": "objeto" if size_type == "to_object" else "distancia",
            "medida": texto_expr(size),
            "objeto_extension": None if size_object is None else _referencia(sesion, size_object, _PUNTO | _PLANO | _EJE | {"cuerpo"}, body)}


def referencias_ruta(sesion, references, body, con_eje=False):
    """Una arista, una curva de boceto o una cadena de ellas; con `con_eje`, también un eje de construcción."""
    if not references:
        raise error("INVALID_ARGUMENTS", "Elegí la ruta: una arista, una curva de boceto o una cadena de ellas.")
    if con_eje and len(references) == 1:
        return [_referencia(sesion, references[0], _CURVA | {"eje"}, body)]
    return [_referencia(sesion, r, _CURVA, body) for r in references]


def referencia_lugar(sesion, ref, location):
    """Lugar de la cara o plano `ref`: `location` si se da, o su centro."""
    if ref["tipo"] not in _PLANO:
        raise error("INVALID_ARGUMENTS", "Sin un punto de referencia hace falta una cara o un plano.")
    return lugar_en(ref, location, sesion.doc.estado_final)


@herramienta("create_construction_axis", "boceto", "Crea un eje con cualquiera de las cinco variantes de CONSTRUIR.",
             modifica=True)
def create_construction_axis(sesion, type: Literal["cilindro", "perpendicular_cara", "dos_planos", "dos_puntos", "arista"],
                             references: list[Referencia], body: str | None = None, name: str | None = None,
                             location: list[float] | None = None, resize: Redimensionar = "default",
                             size_type: TipoExtension = "distance", size: Expr = 0, size_object: Referencia | None = None):
    """
    type: variante de TIPOS_EJE: cilindro, perpendicular_cara, dos_planos, dos_puntos o arista.
    references: referencias en orden: cara de revolución; cara/plano y punto (el punto es opcional: ver location); dos planos;
        dos puntos; arista/eje. Acepta XY/XZ/YZ, X/Y/Z, O, construcción por id/nombre, selectores, ids de find_faces/find_edges,
        {sketch, point}, {sketch, curve} o una referencia de find_snap_points; edges: selecciona aristas, faces: caras.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del eje; vacío = automático.
    location: perpendicular_cara sin punto: [x, y, z] del lugar de la cara; vacío = su centro.
    resize: Redimensionar: default ajusta el dibujo a lo elegido, extended llena la vista. Solo cambia cómo se ve.
    size_type: Tipo de extensión: distance fija el largo con size; to_object lo lleva hasta size_object.
    size: largo del eje en mm; 0 = el que sale de lo elegido.
    size_object: objeto hasta donde llega el eje, con size_type=to_object.
    """
    filtros = {"cilindro": [({"cara"}, None)], "perpendicular_cara": [(_PLANO, None), (_PUNTO, None)],
               "dos_planos": [(_PLANO, "plano"), (_PLANO, "plano")],
               "dos_puntos": [(_PUNTO, None), (_PUNTO, None)], "arista": [(_EJE, "eje")]}[type]
    if type == "perpendicular_cara" and len(references) == 1:
        filtros = filtros[:1]
    refs = _referencias(sesion, references, filtros, body)
    lugar = referencia_lugar(sesion, refs[0], location) if type == "perpendicular_cara" and len(refs) == 1 else None
    op = _crear(sesion, OpEje, name, tipo=type, refs=refs, lugar=lugar,
                **parametros_tamano(sesion, resize, size_type, size, size_object, body))
    agregar_construccion(sesion, op)
    estado = sesion.doc.estado_final
    punto, direccion, _ = estado.ejes[op.id]
    return {"axis": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "origin": _vector(punto), "direction": _vector(direccion), "display": estado.medidas[op.id]}


def _referencias(sesion, referencias, filtros, body):
    if len(referencias) != len(filtros):
        raise error("INVALID_ARGUMENTS", f"Esta variante necesita {len(filtros)} referencias en orden.")
    return [_referencia(sesion, r, tipos, body, geometria)
            for r, (tipos, geometria) in zip(referencias, filtros, strict=True)]


@herramienta("create_construction_point", "boceto", "Crea un punto con las seis variantes de CONSTRUIR.", modifica=True)
def create_construction_point(sesion, type: Literal["vertice", "dos_aristas", "tres_planos", "centro", "arista_plano", "ruta"],
                              references: list[Referencia], position: Expr = 0.5,
                              body: str | None = None, name: str | None = None,
                              extent: Literal["proportional", "physical"] = "proportional", distance: Expr = 0,
                              tangent_chain: bool = True):
    """
    type: variante de TIPOS_PUNTO: vertice, dos_aristas, tres_planos, centro, arista_plano o ruta.
    references: referencias en orden: punto/vértice o referencia de find_snap_points; dos aristas/ejes; tres planos;
        círculo/esfera/toroide; arista/eje y plano; ruta (una curva o una cadena). Formatos como create_construction_axis.
    position: con ruta y extent=proportional: proporción del largo entre 0 y 1, número o expresión; se puede pasar de los extremos.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del punto; vacío = automático.
    extent: con ruta: proportional usa position; physical usa distance.
    distance: con ruta y extent=physical: mm a lo largo de la ruta desde su inicio.
    tangent_chain: con ruta de una sola curva: suma las curvas que siguen por tangencia.
    """
    filtros = {"vertice": [(_PUNTO, None)], "dos_aristas": [(_EJE, None), (_EJE, None)],
               "tres_planos": [(_PLANO | {"perfil"}, "plano")] * 3, "centro": [(_CURVA | {"cara", "perfil"}, None)],
               "arista_plano": [(_EJE, "eje"), (_PLANO, "plano")]}
    refs = referencias_ruta(sesion, references, body) if type == "ruta" else _referencias(sesion, references, filtros[type], body)
    op = _crear(sesion, OpPunto, name, tipo=type, refs=refs, posicion=texto_expr(position),
                tipo_distancia="absoluto" if extent == "physical" else "proporcional", distancia=texto_expr(distance),
                cadena_tangente=tangent_chain and type == "ruta")
    agregar_construccion(sesion, op)
    punto, _ = sesion.doc.estado_final.puntos[op.id]
    return {"point": {"id": op.id, "name": op.nombre, "type": op.TIPO}, "position": _vector(punto)}


@herramienta("find_snap_points", "boceto", "Lista los puntos de forzado de una cara o arista, los mismos que ofrece la ventana "
             "en Punto en vértice, Eje a través de dos puntos, Plano a través de tres puntos, Eje perpendicular y SCU: centro de "
             "cara, puntos tangenciales de caras curvas y centro de arista. Cada ref sirve de referencia en esas herramientas.")
def find_snap_points(sesion, entity: Referencia, location: list[float] | None = None, body: str | None = None):
    """
    entity: una cara o arista: selector, id de find_faces / find_edges o {sketch, curve}.
    location: [x, y, z] opcional: agrega el punto de la cara o arista más cercano a ese lugar (lugar de cara, punto de arista).
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    ref = _referencia(sesion, entity, _CURVA | {"cara"}, body)
    forma = ent.resolver(ref, sesion.doc.estado_final).forma
    if ref["tipo"] == "cara":
        puntos = list(cs.puntos_forzado_cara(forma))
        if location is not None:
            uv = cs.lugar_en_cara(forma, location)
            puntos.append(("lugar_cara", {"uv": uv}, cs.punto_lugar(forma, uv)))
    else:
        puntos = [("centro_arista", {}, cs.centro_arista(forma))]
        if location is not None:
            f = cs.distancia_en_ruta(forma, location) / cs.largo_ruta(forma)
            puntos.append(("en_arista", {"fraccion": f}, cs.punto_en_ruta(forma, f)))
    return {"snap_points": [{"kind": modo, "position": _vector(p), "ref": {"tipo": "forzado", "modo": modo, "base": ref, **datos}}
                            for modo, datos, p in puntos]}


@herramienta("create_ucs", "boceto", "Crea un sistema de coordenadas de usuario con origen, ejes, giros y desfases.",
             modifica=True)
def create_ucs(sesion, origin: Referencia, x_axis: Referencia | None = None, y_axis: Referencia | None = None,
               dx: Expr = 0, dy: Expr = 0, dz: Expr = 0, rx: Expr = 0, ry: Expr = 0, rz: Expr = 0,
               body: str | None = None, name: str | None = None, z_axis: Referencia | None = None):
    """
    origin: punto de forzado (Forzar): O, construcción, vértice, {sketch, point} o una referencia de find_snap_points.
    x_axis: alinea X con un eje, arista recta, línea de boceto o cara (su normal); vacío = X del diseño.
    y_axis: dirección Y opcional; se ortogonaliza respecto de X; no cuenta con z_axis.
    dx: desfase local X en mm o expresión.
    dy: desfase local Y en mm o expresión.
    dz: desfase local Z en mm o expresión.
    rx: giro X en grados o expresión.
    ry: giro Y en grados o expresión.
    rz: giro Z en grados o expresión.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del sistema; vacío = automático.
    z_axis: alinea Z con un eje, arista recta o cara (su normal); X se ortogonaliza contra Z.
    """
    op = _crear(sesion, OpSCU, name, origen=_referencia(sesion, origin, _PUNTO, body),
                eje_x=_referencia(sesion, x_axis, _EJE | _PLANO, body, "eje") if x_axis is not None else None,
                eje_y=_referencia(sesion, y_axis, _EJE, body, "eje") if y_axis is not None else None,
                eje_z=_referencia(sesion, z_axis, _EJE | _PLANO, body, "eje") if z_axis is not None else None,
                **{k: texto_expr(v) for k, v in dict(dx=dx, dy=dy, dz=dz, rx=rx, ry=ry, rz=rz).items()})
    agregar_construccion(sesion, op)
    estado = sesion.doc.estado_final
    return {"ucs": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "origin": _vector(estado.puntos[f"{op.id}_o"][0]),
            "axes": {k: {"id": f"{op.id}_{k}", "direction": _vector(estado.ejes[f"{op.id}_{k}"][1])}
                     for k in ("x", "y", "z")},
            "planes": {k: f"{op.id}_{k}" for k in ("xy", "xz", "yz")}}


@herramienta("insert_fastener", "solido", "Inserta fijaciones normalizadas sobre agujeros o puntos, con tamaño automático.",
             modifica=True)
def insert_fastener(sesion, positions: list[Referencia], family: Literal["screw", "nut", "washer", "rod", "stud"] = "screw",
                    standard: str | None = None, size: str = "auto", length: str | float = "auto",
                    thread: Literal["cosmetic", "modeled"] = "cosmetic", similar: bool = True,
                    direction: Referencia | None = None, flip: bool = False, material: str = "Acero",
                    body: str | None = None):
    """
    positions: aristas circulares, caras cilíndricas/cónicas, puntos o ejes; ids, selectores o {sketch, point}.
        En un eje se usa su origen y dirección.
    family: screw (tornillo), nut (tuerca), washer (arandela), rod (varilla) o stud (espárrago).
    standard: norma ISO/DIN de la familia; vacío = la primera de su catálogo.
    size: tamaño nominal, por ejemplo M6, o auto según el agujero; se corrige al tamaño normalizado más cercano.
    length: largo nominal en mm o auto según el espesor; se corrige al largo normalizado más cercano.
    thread: cosmetic o modeled (filete helicoidal real).
    similar: agrega agujeros iguales de la misma cara.
    direction: dirección en puntos: eje, arista recta, plano o cara plana; vacío = normal del boceto o Z.
    flip: invierte la colocación; sobre una cara usa el otro extremo.
    material: Acero, Acero inoxidable, Latón, Aluminio 6061, Titanio o Nylon.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    familias = dict(screw="tornillo", nut="tuerca", washer="arandela", rod="varilla", stud="esparrago")
    familia = familias[family]
    norma = standard or fj.normas(familia)[0]
    if norma not in fj.normas(familia):
        raise error("INVALID_ARGUMENTS", f"La norma {norma} no pertenece a {familia}.")
    materiales = {"Acero", "Acero inoxidable", "Latón", "Aluminio 6061", "Titanio", "Nylon"} & TABLA_MATERIALES.keys()
    if material not in materiales:
        raise error("INVALID_ARGUMENTS", f"Material de fijación inválido: {material}.")
    if not positions:
        raise error("INVALID_ARGUMENTS", "Elegí dónde colocar la fijación.")
    refs = []
    for posicion in positions:
        if isinstance(posicion, str) and (sl.es_id(posicion) or sl._separar_prefijo(posicion)[0]
                                         or sl.parece_selector(posicion)):
            tipo = sl._separar_prefijo(posicion)[0] or ("arista" if sl.es_id(posicion) and "/E" in posicion.upper() else "cara")
            refs.extend(sl.referencia(c, e) for c, e in sl.elegir(sesion, posicion, tipo, body))
        else:
            refs.append(_referencia(sesion, posicion, _PUNTO | {"arista", "cara", "eje"}, body))
    direccion = None
    if direction is not None:
        direccion = _referencia(sesion, direction, _EJE | _PLANO, body, "direccion")
    op = _crear(sesion, OpFijacion, posiciones=refs, familia=familia, norma=norma, tamano=size,
                largo=str(length), rosca="modelada" if thread == "modeled" else "cosmetica",
                similares=similar, direccion=direccion, voltear=flip, material=material)
    return _agregar(sesion, op)


@herramienta("insert_canvas", "solido", "Embebe una imagen de referencia sobre un plano o cara plana (máximo 32 MB).",
             modifica=True)
def insert_canvas(sesion, path: str, plane: Referencia = "XY", width: Expr = 100, dx: Expr = 0, dy: Expr = 0,
                  angle: Expr = 0, opacity: int = 50, flip: bool = False, flip_v: bool = False,
                  height: Expr | None = None, keep_aspect: bool = True, scale: Expr = 1,
                  body: str | None = None, name: str | None = None):
    """
    path: ruta de una imagen PNG, JPG o BMP; se copia embebida y no depende del archivo original.
    plane: plano XY/XZ/YZ, construcción por id/nombre o una cara plana (selector o id).
    width: ancho real en mm, positivo; con keep_aspect la altura conserva la proporción de la imagen.
    dx: desplazamiento X sobre el plano, en mm o expresión.
    dy: desplazamiento Y sobre el plano, en mm o expresión.
    angle: giro sobre el plano en grados o expresión.
    opacity: opacidad de 0 a 100 por ciento.
    flip: volteo horizontal de la imagen.
    flip_v: volteo vertical de la imagen.
    height: altura en mm, positiva; solo cuenta con keep_aspect=false (vacío = la del ancho y la proporción).
    keep_aspect: la altura sale del ancho y la proporción de la imagen (como el candado del gizmo).
    scale: factor uniforme positivo sobre ancho y altura; 1 conserva el tamaño.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del lienzo; vacío = automático.
    """
    _numero_positivo(width, "width")
    _numero_positivo(scale, "scale")
    if height is not None:
        _numero_positivo(height, "height")
    if not 0 <= opacity <= 100:
        raise error("INVALID_ARGUMENTS", "La opacidad debe estar entre 0 y 100.")
    ref = _referencia(sesion, plane, _PLANO, body, "plano")
    ruta = Path(path)
    if not ruta.is_file():
        raise error("FILE_NOT_FOUND", "No encuentro la imagen del lienzo.")
    with ruta.open("rb") as archivo:
        datos = archivo.read(32 * 1024 * 1024 + 1)
    if len(datos) > 32 * 1024 * 1024:
        raise error("INVALID_ARGUMENTS", "La imagen supera 32 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(datos)) as imagen:
                if imagen.format not in ("PNG", "JPEG", "BMP"):
                    raise ValueError("Formato no compatible")
                proporcion = imagen.height / imagen.width
                imagen.verify()
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise error("INVALID_ARGUMENTS", "La imagen está dañada o no es PNG, JPG o BMP.") from None
    op = _crear(sesion, OpLienzo, name, plano=ref, archivo=ruta.name,
                imagen=base64.b64encode(datos).decode("ascii"), proporcion=proporcion,
                ancho=texto_expr(width), dx=texto_expr(dx), dy=texto_expr(dy), angulo=texto_expr(angle),
                opacidad=opacity, voltear=flip, voltear_v=flip_v, calcomania=False,
                mantener_proporcion=keep_aspect or height is None, escala=texto_expr(scale),
                **({} if height is None else {"alto": texto_expr(height)}))
    resultado = _agregar(sesion, op)
    lienzo = sesion.doc.estado_final.lienzos[op.id]
    resultado.update(width=lienzo["ancho"], height=lienzo["alto"])
    return resultado


@herramienta("create_base_feature", "solido", "Congela cuerpos sólidos o superficies como B-rep en un paso del timeline.",
             modifica=True)
def create_base_feature(sesion, bodies: Cuerpos, name: str | None = None):
    """
    bodies: cuerpos a congelar (id, nombre o lista); conservan su geometría aunque cambien pasos anteriores.
    name: nombre del paso; vacío = automático.
    """
    cuerpos = [sesion.cuerpo(cid) for cid in _ids_cuerpos(sesion, bodies)]
    if not cuerpos or any(getattr(c, "tipo", "solido") == "malla" for c in cuerpos):
        raise error("INVALID_ARGUMENTS", "Elegí cuerpos sólidos o de superficie, sin mallas.")
    params = OpOperacionBase.desde_cuerpos("_", cuerpos).p
    return _agregar(sesion, _crear(sesion, OpOperacionBase, name, **params))
