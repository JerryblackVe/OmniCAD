"""División, sustitución y eliminación mediante referencias persistentes."""
from ..timeline.ops_modificar import (OpBorrarCaras, OpDividirCara, OpDividirCuerpo, OpDivisionSilueta,
                                      OpQuitar, OpReemplazarCara)
from .herramientas_construccion import Referencia, _crear, _referencia
from .herramientas_modificar import Elementos, _refs
from .herramientas_solido import Cuerpos, _agregar, _ids_cuerpos
from .errores import error
from .registro import herramienta


@herramienta("split_face", "solido", "Divide caras con un plano, cara, arista o curva de boceto.", modifica=True)
def split_face(sesion, faces: Elementos, tool: Referencia, extend: bool = True, body: str | None = None):
    """
    faces: caras a dividir: selector, ids de find_faces o lista de ambos.
    tool: plano, cara, arista o {sketch, curve}; acepta id/nombre de construcción, selector o id de find_faces/find_edges.
    extend: extiende la herramienta de división.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    refs, _ = _refs(sesion, faces, "cara", body)
    corte = _referencia(sesion, tool, {"plano", "cara", "arista", "curva_boceto"}, body)
    return _agregar(sesion, _crear(sesion, OpDividirCara, caras=refs, herramienta=corte, extender=extend))


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


@herramienta("silhouette_split", "solido", "Divide las caras de un cuerpo por su silueta vista desde una dirección.",
             modifica=True)
def silhouette_split(sesion, body: str, direction: Referencia = "Z"):
    """
    body: id o nombre del cuerpo de destino.
    direction: eje, arista recta, plano o cara plana: X/Y/Z, XY/XZ/YZ, construcción, selector o id.
    """
    cuerpo = sesion.cuerpo(body)
    ref = _referencia(sesion, direction, {"plano", "cara", "eje", "arista"}, cuerpo.id, "direccion")
    return _agregar(sesion, _crear(sesion, OpDivisionSilueta, cuerpo=cuerpo.id, direccion=ref))


@herramienta("replace_face", "solido", "Lleva caras de un cuerpo hasta otra cara o un plano.", modifica=True)
def replace_face(sesion, faces: Elementos, target: Referencia, body: str | None = None):
    """
    faces: caras de origen: selector, ids de find_faces o lista.
    target: una cara o plano de destino: selector, id de find_faces, XY/XZ/YZ o construcción por id/nombre.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    """
    refs, _ = _refs(sesion, faces, "cara", body)
    destino = _referencia(sesion, target, {"plano", "cara"}, body)
    return _agregar(sesion, _crear(sesion, OpReemplazarCara, caras=refs, destino=destino))


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
