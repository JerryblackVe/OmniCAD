"""División, sustitución y eliminación mediante referencias persistentes."""
from typing import Literal

from ..timeline import entidades as ent
from ..timeline.ops_modificar import (OpBorrarCaras, OpDividirCara, OpDividirCuerpo, OpDivisionSilueta, OpEditarCara,
                                      OpQuitar, OpReemplazarCara)
from .herramientas_construccion import Referencia, _crear, _referencia
from .herramientas_modificar import Elementos, _refs
from .herramientas_solido import Cuerpos, _agregar, _ids_cuerpos
from .errores import error
from .registro import herramienta


@herramienta("split_face", "solido", "Divide caras con un plano, cara, arista o curva de boceto. split_type: surface "
             "(proyecta la herramienta sobre la cara, por defecto), vector (la proyecta a lo largo de direction y parte "
             "una vez por cada cruce) o closest_point (cada punto de la herramienta va al más cercano de la cara).",
             modifica=True)
def split_face(sesion, faces: Elementos, tool: Referencia, extend: bool = True, body: str | None = None,
               split_type: Literal["surface", "vector", "closest_point"] = "surface",
               direction: Referencia | None = None, chain: bool = False):
    """
    faces: caras a dividir: selector, ids de find_faces o lista de ambos.
    tool: plano, cara, arista o {sketch, curve}; acepta id/nombre de construcción, selector o id de find_faces/find_edges.
    extend: extiende la herramienta de división (solo con split_type=surface).
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    split_type: surface, vector o closest_point; vector y closest_point necesitan curvas, aristas o una cara como tool.
    direction: dirección de proyección con split_type=vector: eje X/Y/Z, eje o arista recta de construcción, plano o cara plana (su normal).
    chain: true suma a las caras las que les siguen tangentes (Chain Selection).
    """
    refs, _ = _refs(sesion, faces, "cara", body)
    if split_type == "vector" and direction is None:
        raise error("INVALID_ARGUMENTS", "split_type=vector necesita direction.")
    if split_type != "vector" and direction is not None:
        raise error("INVALID_ARGUMENTS", "direction solo vale con split_type=vector.")
    permitidas = {"plano", "cara", "arista", "curva_boceto"} if split_type == "surface" else {"cara", "arista", "curva_boceto"}
    corte = _referencia(sesion, tool, permitidas, body)
    extra = {}
    if split_type != "surface":
        extra["tipo"] = {"vector": "vector", "closest_point": "cercano"}[split_type]
    if direction is not None:
        extra["direccion"] = _referencia(sesion, direction, {"plano", "cara", "eje", "arista"}, body, "direccion")
    return _agregar(sesion, _crear(sesion, OpDividirCara, caras=refs, herramienta=corte, extender=extend, cadena=bool(chain),
                                   **extra))


@herramienta("split_body", "solido", "Parte un cuerpo en varios con un plano, una cara u otro cuerpo.", modifica=True)
def split_body(sesion, body: str, tool: Referencia, extend: bool = True):
    """
    body: id o nombre del cuerpo a dividir.
    tool: plano de origen/construcción, una cara (selector o id), o cuerpo herramienta por id/nombre o {body: nombre}.
    extend: extiende la herramienta de división.
    """
    cuerpo = sesion.cuerpo(body)
    corte = _referencia(sesion, tool, {"plano", "cara", "cuerpo"}, cuerpo.id)
    return _agregar(sesion, _crear(sesion, OpDividirCuerpo, cuerpo=cuerpo.id, herramienta=corte, extender=extend))


@herramienta("silhouette_split", "solido", "Divide un cuerpo por su silueta vista desde una dirección. operation: "
             "faces_only (solo parte las caras; el cuerpo sigue siendo uno), shelled_body (parte en dos un cuerpo "
             "vaciado) o solid_body (parte en dos un sólido). Las dos últimas necesitan que la línea de partición sea "
             "plana.", modifica=True)
def silhouette_split(sesion, body: str, direction: Referencia = "Z",
                     operation: Literal["faces_only", "shelled_body", "solid_body"] = "faces_only"):
    """
    body: id o nombre del cuerpo de destino.
    direction: eje, arista recta, plano o cara plana: X/Y/Z, XY/XZ/YZ, construcción, selector o id.
    operation: faces_only, shelled_body (cuerpo vaciado) o solid_body (cuerpo sólido).
    """
    cuerpo = sesion.cuerpo(body)
    ref = _referencia(sesion, direction, {"plano", "cara", "eje", "arista"}, cuerpo.id, "direccion")
    return _agregar(sesion, _crear(sesion, OpDivisionSilueta, cuerpo=cuerpo.id, direccion=ref,
                                   operacion={"faces_only": "caras", "shelled_body": "vaciado",
                                              "solid_body": "solido"}[operation]))


@herramienta("replace_face", "solido", "Lleva caras de un cuerpo hasta otra cara o un plano.", modifica=True)
def replace_face(sesion, faces: Elementos, target: Referencia, body: str | None = None, tangent_chain: bool = False):
    """
    faces: caras de origen: selector, ids de find_faces o lista.
    target: una cara o plano de destino: selector, id de find_faces, XY/XZ/YZ o construcción por id/nombre.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    tangent_chain: true suma a las caras de origen las que les siguen tangentes (Tangent Chain).
    """
    refs, _ = _refs(sesion, faces, "cara", body)
    destino = _referencia(sesion, target, {"plano", "cara"}, body)
    return _agregar(sesion, _crear(sesion, OpReemplazarCara, caras=refs, destino=destino, cadena_tangente=bool(tangent_chain)))


@herramienta("get_face_grid", "inspeccion", "Grilla de control de una cara para edit_face (no cambia el documento): sus puntos sobre "
             "la cara y cuáles quedan fijos porque tocan el contorno.")
def get_face_grid(sesion, face: Elementos, length_factor: int = 1, width_factor: int = 1, body: str | None = None):
    """
    face: una cara: selector o id de find_faces.
    length_factor: Factor de longitud, desde 1: la grilla tiene length_factor + 3 puntos a lo largo.
    width_factor: Factor de anchura, desde 1: la grilla tiene width_factor + 3 puntos a lo ancho.
    body: cuerpo donde se evalúa el selector; vacío = el único cuerpo.
    """
    from ..nucleo import editar_cara
    refs, _ = _refs(sesion, face, "cara", body)
    if len(refs) != 1:
        raise error("INVALID_ARGUMENTS", "Elegí una sola cara.")
    g = editar_cara.grilla_cara(ent.resolver(refs[0], sesion.doc.estado_final).forma, length_factor, width_factor)
    return {"size": list(g["fijos"].shape), "points": [[[round(float(x), 6) for x in p] for p in fila] for fila in g["puntos"]],
            "fixed": [[bool(x) for x in fila] for fila in g["fijos"]]}


@herramienta("edit_face", "solido", "Deforma una cara con una grilla de control (Editar cara): mueve puntos de la grilla; el contorno "
             "de la cara queda fijo y sigue cosida a sus vecinas. get_face_grid muestra la grilla.", modifica=True)
def edit_face(sesion, face: Elementos, moves: list[dict], length_factor: int = 1, width_factor: int = 1, body: str | None = None):
    """
    face: una cara: selector o id de find_faces.
    moves: puntos a mover: [{"u": i, "v": j, "offset": [dx, dy, dz]}], con i y j desde 0 y el desplazamiento en mm.
    length_factor: Factor de longitud, desde 1 (Dividir caras).
    width_factor: Factor de anchura, desde 1 (Dividir caras).
    body: cuerpo donde se evalúa el selector; vacío = el único cuerpo.
    """
    refs, _ = _refs(sesion, face, "cara", body)
    if len(refs) != 1:
        raise error("INVALID_ARGUMENTS", "Elegí una sola cara.")
    try:
        despl = {f"{int(m['u'])},{int(m['v'])}": [float(x) for x in m["offset"]] for m in moves}
    except (KeyError, TypeError, ValueError) as e:
        raise error("INVALID_ARGUMENTS", 'Cada movimiento es {"u": i, "v": j, "offset": [dx, dy, dz]}.') from e
    if any(len(d) != 3 for d in despl.values()):
        raise error("INVALID_ARGUMENTS", "offset lleva tres números: dx, dy y dz.")
    return _agregar(sesion, _crear(sesion, OpEditarCara, cara=refs[0], n_u=length_factor, n_v=width_factor, desplazamientos=despl))


@herramienta("remove_bodies", "solido", "Quita cuerpos del diseño conservando la operación en el timeline.", modifica=True)
def remove_bodies(sesion, bodies: Cuerpos):
    """
    bodies: id, nombre o lista de cuerpos a quitar.
    """
    ids = _ids_cuerpos(sesion, bodies)
    if not ids:
        raise error("INVALID_ARGUMENTS", "Elegí los cuerpos a quitar.")
    return _agregar(sesion, _crear(sesion, OpQuitar, cuerpos=list(dict.fromkeys(ids))))


@herramienta("delete_faces", "solido", "Borra caras y cierra el hueco extendiendo sus vecinas.", modifica=True)
def delete_faces(sesion, faces: Elementos, body: str | None = None):
    """
    faces: caras a borrar: selector, ids de find_faces o lista.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    refs, _ = _refs(sesion, faces, "cara", body)
    return _agregar(sesion, _crear(sesion, OpBorrarCaras, caras=refs))
