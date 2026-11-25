"""B-760: el aviso del cuerpo creado usa su nombre del navegador."""
from types import SimpleNamespace

import pytest

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.ventana import VentanaPrincipal


def test_b760_nombre_del_cuerpo_en_aviso():
    doc = Documento()
    op = OpPrimitiva(doc.nuevo_id(), nombre="Caja1")
    res = doc.agregar(op)
    assert res.estado == "ok"
    mensajes = []
    ventana = SimpleNamespace(doc=doc, mensaje=lambda texto, ms: mensajes.append(texto))
    ventana.nombre_cuerpo = lambda cuerpo: VentanaPrincipal.nombre_cuerpo(ventana, cuerpo)
    cuerpo = next(iter(doc.estado_final.cuerpos.values()))
    assert cuerpo.nombre != op.nombre
    VentanaPrincipal._informar(ventana, op, res)
    assert mensajes == [f"{cuerpo.nombre}: listo."]


@pytest.mark.parametrize("largo", [36, 37, 38, 80])
def test_b760_aviso_de_nombre_largo_no_pasa_de_45_caracteres(largo):
    doc = Documento()
    op = OpPrimitiva(doc.nuevo_id(), nombre="Caja1")
    res = doc.agregar(op)
    cuerpo = next(iter(doc.estado_final.cuerpos.values()))
    nombre = "P" * largo
    doc.set_propiedad([cuerpo.id], "nombre", nombre)
    mensajes = []
    ventana = SimpleNamespace(doc=doc, mensaje=lambda texto, ms: mensajes.append(texto))
    ventana.nombre_cuerpo = lambda cuerpo: VentanaPrincipal.nombre_cuerpo(ventana, cuerpo)
    VentanaPrincipal._informar(ventana, op, res)
    esperado = nombre if largo <= 37 else nombre[:36] + "…"
    assert mensajes == [f"{esperado}: listo."]
    assert len(mensajes[0]) <= 45
    assert VentanaPrincipal.nombre_cuerpo(ventana, cuerpo) == nombre
    assert op.nombre == "Caja1"
