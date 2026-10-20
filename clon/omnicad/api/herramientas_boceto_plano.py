"""Redefinición del soporte de un boceto conservando sus entidades y restricciones."""
from ..nucleo import geometria as geo
from ..timeline.operaciones import resolver_plano
from . import selectores as sl
from .errores import error
from .herramientas_boceto import boceto_activo, info_boceto, plano_o_cara
from .registro import herramienta


@herramienta("redefine_sketch_plane", "boceto", "Redefine el plano o la cara de un boceto existente conservando "
             "curvas, restricciones y cotas. Los perfiles fuera del contorno de la cara se conservan y se informan.",
             modifica=True)
def redefine_sketch_plane(sesion, sketch: str, plane: str, body: str | None = None):
    """
    sketch: id o nombre del boceto existente.
    plane: plano XY, XZ, YZ, id/nombre de plano de construcción, selector de cara plana o id de find_faces.
    body: cuerpo donde evaluar el selector de cara; omitido usa el único cuerpo, como create_sketch.
    """
    op, previo = boceto_activo(sesion, sketch, derivados=False)
    ref, marco, cara, ref_cara = plano_o_cara(sesion, plane, body)
    nueva = op.copia()
    nueva.p.update(plano=ref, marco=marco, cara=ref_cara, desplazamiento="0")
    indice = sesion.doc.indice(op.id)
    anteriores = {o.id for o in sesion.doc.operaciones[:indice]}
    if not nueva.dependencias() <= anteriores:
        raise error("INVALID_ARGUMENTS", "El soporte del boceto debe existir antes que él en el timeline.")
    # Validar la cara en el estado anterior impide asociarla a la propia extrusión posterior.
    resolver_plano(ref, marco, sesion.doc.estado_en(indice), ref_cara)
    sesion.doc.reemplazar(op.id, nueva)
    _, br = boceto_activo(sesion, op.id, derivados=False)
    fuera = []
    if cara:
        _, elem = sl.elegir_uno(sesion, plane, "cara", body)
        for i, perfil in enumerate(br.perfiles):
            comun = geo.booleano(perfil.cara, elem.sub, "intersecar")
            if geo.area(comun) < perfil.area - max(1e-7, perfil.area * 1e-7):
                fuera.append(i)
    if fuera:
        sesion.avisar(f"Los perfiles {fuera} exceden el contorno de la cara nueva; se conservan sin recortar.")
    if previo.solver.ok and not br.solver.ok:
        sesion.avisar("El boceto sigue resolviéndose, pero sus restricciones quedaron en conflicto sobre el plano nuevo.")
    return {"sketch": info_boceto(sesion, nueva), "outside_profiles": fuera}
