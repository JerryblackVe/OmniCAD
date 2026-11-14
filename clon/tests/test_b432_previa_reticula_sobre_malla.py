"""B-432: la previa en el proceso aparte de una retícula sobre un cuerpo de malla no falla (antes: `MapShapes_s` recibía una Malla)."""
from omnicad.nucleo.render_cpu import es_malla
from omnicad.timeline.calculo_aislado import leer_previa_visual, previa_visual
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_solido import OpReticulaVolumetrica


def test_previa_visual_de_reticula_sobre_una_malla():
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    cid = next(iter(d.estado_final.cuerpos))
    d.agregar(OpReticulaVolumetrica(d.nuevo_id(), cuerpo=cid, forma_celda="gyroid", tamano="10", resolucion=6))
    assert es_malla(d.estado_final.cuerpo(cid).forma)               # el cuerpo ya es una malla
    op = OpReticulaVolumetrica(d.nuevo_id(), cuerpo=cid, forma_celda="gyroid", tamano="10", resolucion=6)
    salida = previa_visual(d.a_dict(), op.a_dict(), None, 0.05, 0.3)
    vista, avisos = leer_previa_visual(salida, d.estado_final)
    assert not avisos and es_malla(vista.cuerpo(cid).forma) and len(vista.cuerpo(cid).forma.vertices) > 0
