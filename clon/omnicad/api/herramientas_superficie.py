"""Herramientas de SUPERFICIE: referencias cortas y las mismas operaciones que la ventana."""
import math
from typing import Literal

from ..timeline import entidades as ent
from ..timeline import ops_superficie as ops
from . import selectores as sl
from .errores import error
from .herramientas_avanzado import traducir_referencias
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_solido import _agregar, _ids_cuerpos, _numero_positivo
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


@herramienta("create_surface_extrude", "solido", "Extruye curvas abiertas o cerradas en una superficie.", modifica=True)
def create_surface_extrude(sesion, profiles: Seleccion, distance: Expr = "10 mm",
                           direction: Referencia | None = None, symmetric: bool = False,
                           taper_angle: Expr = 0, body: str | None = None):
    """
    profiles: curvas {"sketch": "Boceto1", "curve": [1, 2]}, perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas o cuerpos; admite listas, ids y selectores.
    distance: distancia en mm o expresión; negativa invierte el sentido.
    direction: eje, plano, cara plana o arista lineal; vacío = normal del boceto (o Z).
    symmetric: reparte la distancia total a ambos lados.
    taper_angle: ángulo de conicidad en grados o expresión.
    body: cuerpo sobre el que evaluar selectores sin cuerpo explícito.
    """
    clase = ops.OpSupExtruir
    return _crear(sesion, clase, curvas=_seleccion(sesion, clase, "curvas", profiles, body, curvas=True),
                  distancia=texto_expr(distance), direccion=_una(sesion, clase, "direccion", direction, body)
                  if direction is not None else None, simetrica=symmetric, conicidad=texto_expr(taper_angle))


@herramienta("create_surface_revolve", "solido", "Gira curvas alrededor de un eje para crear una superficie.", modifica=True)
def create_surface_revolve(sesion, profiles: Seleccion, axis: Referencia, angle: Expr = "360 deg",
                           body: str | None = None):
    """
    profiles: curvas o perfiles de boceto ({"sketch": "Boceto1", "curve": 1} o "profile": 0), caras, aristas o cuerpos; admite listas, ids y selectores.
    axis: eje X, Y, Z, eje de construcción o referencia a una línea de boceto/arista lineal.
    angle: ángulo en grados o expresión.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpSupRevolucion
    return _crear(sesion, clase, curvas=_seleccion(sesion, clase, "curvas", profiles, body, curvas=True),
                  eje=_una(sesion, clase, "eje", axis, body), angulo=texto_expr(angle))


@herramienta("create_surface_sweep", "solido", "Barre curvas por una ruta con orientación, torsión y distancia sobre la ruta.",
             modifica=True)
def create_surface_sweep(sesion, profiles: Seleccion, path: Seleccion,
                         orientation: Literal["perpendicular", "parallel"] = "perpendicular",
                         twist_angle: Expr = 0, body: str | None = None, path_distance: Expr = 1):
    """
    profiles: curvas o perfiles {"sketch": "Boceto1", "curve": 1} o {"sketch": "Boceto1", "profile": 0}; también caras, aristas o cuerpos.
    path: cadena de curvas de boceto, aristas (ids o selectores), caras o cuerpos.
    orientation: perpendicular sigue la ruta; parallel mantiene la orientación.
    twist_angle: torsión total en grados o expresión; solo con orientación perpendicular.
    body: cuerpo sobre el que evaluar selectores.
    path_distance: hasta dónde llega el barrido sobre la ruta, fracción de 0 (sin incluir) a 1 (toda la ruta).
    """
    clase = ops.OpSupBarrido
    return _crear(sesion, clase, perfil=_seleccion(sesion, clase, "perfil", profiles, body, curvas=True),
                  ruta=_seleccion(sesion, clase, "ruta", path, body, curvas=True),
                  orientacion="paralela" if orientation == "parallel" else "perpendicular",
                  torsion=texto_expr(twist_angle), distancia=texto_expr(path_distance))


@herramienta("create_surface_loft", "solido", "Crea una superficie entre secciones ordenadas, abiertas o cerradas.", modifica=True)
def create_surface_loft(sesion, profiles: list[str | dict], closed: bool = False, ruled: bool = False,
                        body: str | None = None):
    """
    profiles: secciones ordenadas: curvas o perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas, cuerpos o puntos de boceto {"sketch": "Boceto1", "point": 1}.
    closed: une la última sección con la primera.
    ruled: usa tramos rectos entre secciones.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpSupSolevacion
    refs = _seleccion(sesion, clase, "secciones", profiles, body, curvas=True)
    if len(refs) < 2:
        raise error("INVALID_ARGUMENTS", "Una solevación necesita al menos dos secciones.")
    return _crear(sesion, clase, secciones=refs, cerrada=closed, reglada=ruled)


@herramienta("offset_surface", "solido", "Crea una superficie paralela a caras o cuerpos.", modifica=True)
def offset_surface(sesion, faces: Seleccion, distance: Expr = "2 mm",
                   offset_type: Literal["sharp", "rounded"] = "sharp", body: str | None = None):
    """
    faces: caras (ids o selectores) o cuerpos por id, nombre o {"body": "Cuerpo1"}; admite listas.
    distance: desfase en mm o expresión; admite valores negativos.
    offset_type: sharp para esquinas agudas; rounded para redondeadas.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpSupDesfase
    return _crear(sesion, clase, caras=_seleccion(sesion, clase, "caras", faces, body, tipo="cara"),
                  distancia=texto_expr(distance), tipo="agudo" if offset_type == "sharp" else "redondeado")


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


@herramienta("create_patch", "solido", "Tapa un contorno cerrado con continuidad G0, G1 o G2.", modifica=True)
def create_patch(sesion, boundary: Seleccion, continuity: Literal["G0", "G1", "G2"] = "G0",
                 body: str | None = None):
    """
    boundary: curvas o perfiles {"sketch": "Boceto1", "profile": 0}, aristas, caras o cuerpos; admite listas, ids y selectores.
    continuity: G0 conexión, G1 tangencia o G2 curvatura; G1/G2 necesitan caras de soporte.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpParche
    return _crear(sesion, clase, contorno=_seleccion(sesion, clase, "contorno", boundary, body, curvas=True),
                  continuidad=continuity)


@herramienta("create_ruled_surface", "solido", "Crea superficies rectas desde aristas, con dirección y ángulo.", modifica=True)
def create_ruled_surface(sesion, edges: Seleccion, distance: Expr = "10 mm",
                         surface_type: Literal["normal", "tangent", "direction"] = "normal",
                         direction: Referencia | None = None, angle: Expr = 0, body: str | None = None):
    """
    edges: curvas o perfiles de boceto, aristas, caras o cuerpos; admite listas, ids y selectores.
    distance: largo en mm o expresión.
    surface_type: normal, tangent o direction.
    direction: eje, plano, cara plana o arista lineal; obligatorio con surface_type=direction.
    angle: giro de la dirección en grados o expresión.
    body: cuerpo sobre el que evaluar selectores.
    """
    if surface_type == "direction" and direction is None:
        raise error("INVALID_ARGUMENTS", "Indicá direction para una superficie reglada por dirección.")
    clase = ops.OpReglada
    return _crear(sesion, clase, aristas=_seleccion(sesion, clase, "aristas", edges, body, curvas=True),
                  distancia=texto_expr(distance), tipo={"normal": "normal", "tangent": "tangente", "direction": "direccion"}[surface_type],
                  direccion=_una(sesion, clase, "direccion", direction, body) if direction is not None else None,
                  angulo=texto_expr(angle))


@herramienta("extend_surface", "solido", "Alarga bordes libres de superficies.", modifica=True)
def extend_surface(sesion, edges: Seleccion, distance: Expr = "5 mm",
                   extension_type: Literal["natural", "tangent", "perpendicular"] = "natural", body: str | None = None):
    """
    edges: bordes libres por id o selector; admite listas y {"body": "Cuerpo1", "edges": ">X"}.
    distance: extensión en mm o expresión.
    extension_type: natural, tangent o perpendicular.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpExtenderSup
    return _crear(sesion, clase, aristas=_seleccion(sesion, clase, "aristas", edges, body),
                  distancia=texto_expr(distance), tipo="tangente" if extension_type == "tangent" else extension_type)


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


@herramienta("untrim_surface", "solido", "Restaura límites naturales de caras recortadas.", modifica=True)
def untrim_surface(sesion, faces: Seleccion, boundaries: Literal["outer", "inner", "all"] = "outer",
                   body: str | None = None):
    """
    faces: caras por id o selector; admite listas y {"body": "Cuerpo1", "faces": "all"}.
    boundaries: outer exteriores, inner interiores o all todos los contornos.
    body: cuerpo sobre el que evaluar selectores.
    """
    clase = ops.OpDestrimar
    return _crear(sesion, clase, caras=_seleccion(sesion, clase, "caras", faces, body, tipo="cara"),
                  contornos={"outer": "exteriores", "inner": "interiores", "all": "todos"}[boundaries])


@herramienta("stitch_surfaces", "solido", "Cose superficies; un cierre completo produce un sólido.", modifica=True)
def stitch_surfaces(sesion, bodies: str | list[str], tolerance: Expr = "0.01 mm"):
    """
    bodies: ids o nombres de los cuerpos que se cosen; se conserva el primero y se consumen los demás.
    tolerance: tolerancia de costura en mm o expresión.
    """
    _numero_positivo(tolerance, "tolerance")
    return _crear(sesion, ops.OpCoser, cuerpos=_cuerpos(sesion, bodies), tolerancia=texto_expr(tolerance))


@herramienta("unstitch_surfaces", "solido", "Separa cada cara en un cuerpo de superficie independiente.", modifica=True)
def unstitch_surfaces(sesion, bodies: str | list[str]):
    """
    bodies: ids o nombres de cuerpos; cada cara pasa a ser un cuerpo nuevo.
    """
    return _crear(sesion, ops.OpDescoser, cuerpos=_cuerpos(sesion, bodies))


@herramienta("reverse_surface_normal", "solido", "Invierte la orientación de cuerpos de superficie.", modifica=True)
def reverse_surface_normal(sesion, bodies: str | list[str]):
    """
    bodies: ids o nombres de superficies cuya normal se invierte.
    """
    return _crear(sesion, ops.OpInvertirNormal, cuerpos=_cuerpos(sesion, bodies))
