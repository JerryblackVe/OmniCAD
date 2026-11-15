# -*- coding: utf-8 -*-
"""B-503: lo que la ventana guarda de las respuestas del trabajador no es la lista del documento. Antes eran la misma:
un deshacer en la ventana la acortaba y el próximo paso calculado aparte (Cara de desfase sobre letras) abría un cuadro
«El cálculo recibido tiene pasos incompletos». Si el transporte igual queda desparejo, se pide todo de nuevo sin avisar."""
import pytest

from omnicad import api
from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_modificar import OpDesfaseCara


@pytest.fixture
def doc():
    """Una caja ya modificada por un desfase (regla de B-453: la vía aparte se prueba sobre un cuerpo ya cambiado)."""
    aislado.cerrar_trabajador()
    with motor.fijar_motor("opencascade"):
        s = api.Sesion()
        for nombre, args in (("create_box", {"length": 20, "width": 10, "height": 5}),
                             ("offset_faces", {"faces": ">Z", "distance": 2})):
            assert api.llamar(s, nombre, args)["ok"]
        yield s.doc
    aislado.cerrar_trabajador()


def _volumen(d):
    return sum(geo.volumen(c.forma) for c in d.estado_final.cuerpos.values())


def _falla(d):
    """Un paso que da error: su estado es el mismo objeto que el del paso anterior (en los dos procesos)."""
    return OpDesfaseCara(d.nuevo_id(), "Falla", caras=[], distancia="no_existe mm")


def test_deshacer_en_la_ventana_no_despareja_el_paso_siguiente_aparte(doc):
    assert _volumen(doc) == pytest.approx(20 * 10 * 7)
    assert doc.agregar(_falla(doc), aparte=True).estado == "error"
    assert aislado.estados_recibidos is not doc._estados
    doc.deshacer()                                   # en la ventana: recortaba también la lista del transporte
    assert doc.agregar(_falla(doc), aparte=True).estado == "error"      # antes: «pasos incompletos»
    assert len(doc._estados) == len(doc.operaciones) == 3
    assert _volumen(doc) == pytest.approx(20 * 10 * 7)


def test_si_el_transporte_quedo_desparejo_se_pide_todo_de_nuevo(doc):
    assert doc.agregar(_falla(doc), aparte=True).estado == "error"
    aislado.estados_recibidos = []                   # lo que dejaba el bug: la ventana tiene menos de lo que cree el hijo
    caja = OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="4", x="50")
    assert doc.agregar(caja, aparte=True).estado == "ok"
    assert len(doc._estados) == len(doc.operaciones) == 4
    assert _volumen(doc) == pytest.approx(20 * 10 * 7 + 64)
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
