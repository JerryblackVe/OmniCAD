"""Construcción, fijaciones, lienzos y cuerpos congelados, sin interfaz gráfica."""
import base64
import io
import warnings
from pathlib import Path
from typing import Literal

from PIL import Image

from ..nucleo import fijaciones as fj
from ..nucleo.analisis import TABLA_MATERIALES
from ..timeline import entidades as ent
from ..timeline.operaciones import OpOperacionBase
from ..timeline.ops_construir import OpEje, OpPunto, OpSCU
from ..timeline.ops_fijacion import OpFijacion
from ..timeline.ops_insertar import OpLienzo
from . import selectores as sl
from .errores import error
from .herramientas_avanzado import _una
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_solido import Cuerpos, _agregar, _ids_cuerpos, _numero_positivo
from .registro import Expr, herramienta

Referencia = str | dict | list[float]      # una lista [x, y, z] elige el vértice que está ahí
_PLANO = {"plano", "cara"}
_EJE = {"eje", "arista", "curva_boceto"}
_PUNTO = {"punto", "vertice", "punto_boceto"}
_CURVA = {"arista", "curva_boceto"}


def _referencia(sesion, valor, tipos, body=None, geometria=None):
    """Resuelve una selección abreviada y comprueba el filtro del diálogo. Un punto [x, y, z] elige el vértice que está
    ahí (`sl.vertice_cercano`)."""
    if sl.es_punto3(valor):
        ref = sl.vertice_cercano(sesion, valor, body)[1]
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
                    "un vértice [x, y, z] o {sketch, point | curve}.") from None
    if ref["tipo"] not in tipos:
        raise error("INVALID_ARGUMENTS", f"La referencia debe ser de tipo {', '.join(sorted(tipos))}.")
    entidad = ent.resolver(ref, sesion.doc.estado_final)
    if geometria == "plano":
        ent.como_plano(entidad)
    elif geometria == "eje":
        ent.como_eje(entidad)
    elif geometria == "direccion":
        if entidad.tipo in _PLANO:
            ent.como_plano(entidad)
        else:
            ent.como_eje(entidad)
    return ref


def _crear(sesion, clase, name=None, **params):
    doc = sesion.doc
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, clase.ETIQUETA, clase)
    return clase(doc.nuevo_id(), nombre, **params)


def _vector(valores):
    return [round(float(v), 8) + 0.0 for v in valores]


@herramienta("create_construction_axis", "boceto", "Crea un eje con cualquiera de las cinco variantes de CONSTRUIR.",
             modifica=True)
def create_construction_axis(sesion, type: Literal["cilindro", "perpendicular_cara", "dos_planos", "dos_puntos", "arista"],
                             references: list[Referencia], body: str | None = None, name: str | None = None):
    """
    type: variante de TIPOS_EJE: cilindro, perpendicular_cara, dos_planos, dos_puntos o arista.
    references: referencias en orden: cara de revolución; cara/plano y punto; dos planos; dos puntos; arista/eje.
        Acepta XY/XZ/YZ, X/Y/Z, O, construcción por id/nombre, selectores, ids de find_faces/find_edges,
        {sketch, point} o {sketch, curve}; edges: selecciona aristas, faces: caras.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del eje; vacío = automático.
    """
    filtros = {"cilindro": [({"cara"}, None)], "perpendicular_cara": [(_PLANO, None), (_PUNTO, None)],
               "dos_planos": [(_PLANO, "plano"), (_PLANO, "plano")],
               "dos_puntos": [(_PUNTO, None), (_PUNTO, None)], "arista": [(_EJE, "eje")]}
    refs = _referencias(sesion, references, filtros[type], body)
    op = _crear(sesion, OpEje, name, tipo=type, refs=refs)
    sesion.doc.agregar(op)
    punto, direccion, _ = sesion.doc.estado_final.ejes[op.id]
    return {"axis": {"id": op.id, "name": op.nombre, "type": op.TIPO},
            "origin": _vector(punto), "direction": _vector(direccion)}


def _referencias(sesion, referencias, filtros, body):
    if len(referencias) != len(filtros):
        raise error("INVALID_ARGUMENTS", f"Esta variante necesita {len(filtros)} referencias en orden.")
    return [_referencia(sesion, r, tipos, body, geometria)
            for r, (tipos, geometria) in zip(referencias, filtros, strict=True)]


@herramienta("create_construction_point", "boceto", "Crea un punto con las seis variantes de CONSTRUIR.", modifica=True)
def create_construction_point(sesion, type: Literal["vertice", "dos_aristas", "tres_planos", "centro", "arista_plano", "ruta"],
                              references: list[Referencia], position: Expr = 0.5,
                              body: str | None = None, name: str | None = None):
    """
    type: variante de TIPOS_PUNTO: vertice, dos_aristas, tres_planos, centro, arista_plano o ruta.
    references: referencias en orden: punto/vértice; dos aristas/ejes; tres planos; círculo/esfera/toroide;
        arista/eje y plano; curva de ruta. Formatos como create_construction_axis, incluidos puntos de boceto.
    position: proporción del largo de la ruta entre 0 y 1, número o expresión; solo con ruta.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del punto; vacío = automático.
    """
    filtros = {"vertice": [(_PUNTO, None)], "dos_aristas": [(_EJE, None), (_EJE, None)],
               "tres_planos": [(_PLANO, "plano")] * 3, "centro": [(_CURVA | {"cara"}, None)],
               "arista_plano": [(_EJE, "eje"), (_PLANO, "plano")], "ruta": [(_CURVA, None)]}
    refs = _referencias(sesion, references, filtros[type], body)
    op = _crear(sesion, OpPunto, name, tipo=type, refs=refs, posicion=texto_expr(position))
    sesion.doc.agregar(op)
    punto, _ = sesion.doc.estado_final.puntos[op.id]
    return {"point": {"id": op.id, "name": op.nombre, "type": op.TIPO}, "position": _vector(punto)}


@herramienta("create_ucs", "boceto", "Crea un sistema de coordenadas de usuario con origen, ejes, giros y desfases.",
             modifica=True)
def create_ucs(sesion, origin: Referencia, x_axis: Referencia = "X", y_axis: Referencia | None = None,
               dx: Expr = 0, dy: Expr = 0, dz: Expr = 0, rx: Expr = 0, ry: Expr = 0, rz: Expr = 0,
               body: str | None = None, name: str | None = None):
    """
    origin: punto/vértice de origen: O, construcción o {sketch, point}.
    x_axis: dirección X: eje, arista recta o línea de boceto; por defecto X.
    y_axis: dirección Y opcional; se ortogonaliza respecto de X.
    dx: desfase local X en mm o expresión.
    dy: desfase local Y en mm o expresión.
    dz: desfase local Z en mm o expresión.
    rx: giro X en grados o expresión.
    ry: giro Y en grados o expresión.
    rz: giro Z en grados o expresión.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    name: nombre del sistema; vacío = automático.
    """
    op = _crear(sesion, OpSCU, name, origen=_referencia(sesion, origin, _PUNTO, body),
                eje_x=_referencia(sesion, x_axis, _EJE, body, "eje"),
                eje_y=_referencia(sesion, y_axis, _EJE, body, "eje") if y_axis is not None else None,
                **{k: texto_expr(v) for k, v in dict(dx=dx, dy=dy, dz=dz, rx=rx, ry=ry, rz=rz).items()})
    sesion.doc.agregar(op)
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
