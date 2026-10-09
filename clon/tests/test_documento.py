# -*- coding: utf-8 -*-
import math

import pytest

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpCombinar, OpPrimitiva

VOL_PLACA = (60 * 40 - math.pi * 36) * 8 + math.pi * 16 * 12 - 2 / 3 * math.pi * 125
VOL_ARO_TOROIDE = math.pi * (86 ** 2 - 80 ** 2) * 12 + 2 * math.pi ** 2 * 12 * 9


@pytest.fixture(scope="module")
def ejemplo():
    return crear_documento_ejemplo()


def _volumenes(doc):
    return sorted(round(g.volumen(c.forma), 2) for c in doc.estado_final.cuerpos.values())


def test_ejemplo_todo_ok(ejemplo):
    assert [r.estado for r in ejemplo.resultados] == ["ok"] * len(ejemplo.operaciones)
    assert _volumenes(ejemplo) == sorted([round(VOL_PLACA, 2), round(VOL_ARO_TOROIDE, 2)])


def test_parametro_cambia_el_modelo():
    doc = crear_documento_ejemplo()
    tabla = type(doc.parametros).desde_lista(doc.parametros.a_lista())
    tabla.modificar("ancho", "80 mm")
    doc.aplicar_parametros(tabla)
    assert all(r.estado == "ok" for r in doc.resultados)
    placa = doc.estado_final.cuerpos["op2.c1"]
    (x0, _, _), (x1, _, _) = g.caja_envolvente(placa.forma)
    assert x1 - x0 == pytest.approx(80, abs=1e-3)
    esperado = (80 * 40 - math.pi * 36) * 8 + math.pi * 16 * 12 - 2 / 3 * math.pi * 125
    assert g.volumen(placa.forma) == pytest.approx(esperado, rel=1e-6)


def test_marcador_suprimir_y_deshacer():
    doc = crear_documento_ejemplo()
    n = len(doc.operaciones)
    doc.mover_marcador(2)                         # solo boceto + extrusión
    assert doc.resultados[2].estado == "retrocedida"
    assert len(doc.estado_final.cuerpos) == 1
    doc.mover_marcador(n)
    doc.suprimir("op4", True)                     # sin el hueco esférico, la placa gana volumen
    assert doc.resultado("op4").estado == "suprimida"
    vol = g.volumen(doc.estado_final.cuerpos["op2.c1"].forma)
    assert vol == pytest.approx(VOL_PLACA + 2 / 3 * math.pi * 125, rel=1e-6)
    doc.deshacer()
    assert doc.operacion("op4").suprimida is False
    doc.rehacer()
    assert doc.operacion("op4").suprimida is True


def test_dependencias_bloquean_borrado_y_reorden():
    doc = crear_documento_ejemplo()
    with pytest.raises(ErrorDocumento):
        doc.eliminar("op1")                       # la extrusión usa el boceto
    ok, _ = doc.puede_mover("op2", 0)             # la extrusión no puede ir antes de su boceto
    assert not ok
    with pytest.raises(ErrorDocumento):
        doc.mover("op2", 0)
    ok, _ = doc.puede_mover("op7", 0)             # el toroide no depende de nada
    assert ok


def test_referencia_rota_da_error_sin_romper_el_resto():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja"))
    r = doc.agregar(OpCombinar(doc.nuevo_id(), objetivo="op1.c1", herramientas=["op99.c1"]))
    assert r.estado == "error"
    assert len(doc.estado_final.cuerpos) == 1     # el paso con error no altera el modelo


def test_operaciones_cortar_e_intersecar_con_primitivas():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="2", alto="20", x="5", y="5", z="-5",
                            operacion="cortar"))
    vol = g.volumen(doc.estado_final.cuerpos["op1.c1"].forma)
    assert vol == pytest.approx(1000 - math.pi * 4 * 10)
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="100", operacion="intersecar"))
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(vol)


def test_receta_ida_y_vuelta(ejemplo):
    copia = Documento.desde_dict(ejemplo.a_dict())
    assert copia.a_dict() == ejemplo.a_dict()
    assert _volumenes(copia) == _volumenes(ejemplo)
