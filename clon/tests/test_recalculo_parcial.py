# -*- coding: utf-8 -*-
"""Recálculo parcial: al cambiar parámetros se rehace solo desde el primer paso que lee uno que cambió."""
import math

import pytest

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


def _doc():
    """Placa 40×40×10 (ancho), agujero de radio = base/4 (cortar) y una esfera fija unida arriba."""
    doc = Documento()
    doc.parametros.agregar("ancho", "40 mm")
    doc.parametros.agregar("base", "16 mm")
    doc.parametros.agregar("radio", "base / 4")
    doc.parametros.agregar("sin_uso", "3 mm")
    doc.operaciones = [
        OpPrimitiva("op1", "Placa", forma="caja", ancho="ancho", largo="40 mm", alto="10 mm",
                    x="0", y="0", z="0", operacion="nuevo"),
        OpPrimitiva("op2", "Agujero", forma="cilindro", radio="radio", alto="30 mm",
                    x="20 mm", y="20 mm", z="-10 mm", operacion="cortar"),
        OpPrimitiva("op3", "Esfera", forma="esfera", radio="5 mm", x="5 mm", y="5 mm", z="10 mm",
                    operacion="unir"),
    ]
    doc.marcador = 3
    doc.recalcular(0)
    return doc


def _cambiar(doc, **cambios):
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    for nombre, expr in cambios.items():
        tabla.modificar(nombre, expr)
    doc.aplicar_parametros(tabla)


def _volumen(doc):
    return sum(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())


def _completo(doc):
    """El mismo documento recalculado desde cero: la referencia contra la que se compara."""
    return Documento.desde_dict(doc.a_dict())


def test_cada_paso_anota_los_parametros_que_lee():
    doc = _doc()
    assert doc._usados == [{"ancho"}, {"radio"}, set()]


def test_cambiar_un_parametro_no_rehace_los_pasos_anteriores():
    doc = _doc()
    antes = list(doc._estados)
    _cambiar(doc, base="20 mm")                   # radio = base/4: solo lo lee el agujero (paso 2)
    assert doc._estados[0] is antes[0]            # la placa NO se recalculó
    assert doc._estados[1] is not antes[1]
    assert all(r.estado == "ok" for r in doc.resultados)
    assert _volumen(doc) == pytest.approx(_volumen(_completo(doc)), rel=1e-9)
    hueco, media_esfera = math.pi * 5 ** 2 * 10, 2 / 3 * math.pi * 5 ** 3   # radio 20/4 = 5
    assert _volumen(doc) == pytest.approx(40 * 40 * 10 - hueco + media_esfera, rel=1e-6)


def test_parametro_sin_uso_no_recalcula_nada():
    doc = _doc()
    antes = list(doc._estados)
    avisos = []
    doc.suscribir(lambda: avisos.append(1))
    _cambiar(doc, sin_uso="7 mm")
    assert all(a is b for a, b in zip(doc._estados, antes, strict=True))
    assert avisos == [1]                          # la interfaz se entera igual (tabla de parámetros)
    assert doc.parametros.valores()["sin_uso"] == 7


def test_el_primer_paso_que_lo_lee_manda():
    doc = _doc()
    antes = list(doc._estados)
    _cambiar(doc, ancho="50 mm", base="12 mm")
    assert all(a is not b for a, b in zip(doc._estados, antes, strict=True))
    (x0, _, _), (x1, _, _) = g.caja_envolvente(doc.estado_final.cuerpos["op1.c1"].forma)
    assert x1 - x0 == pytest.approx(50, abs=1e-6)


def test_parametro_que_faltaba_rehace_el_paso_que_lo_pedia():
    doc = _doc()
    doc.operaciones[2].p["radio"] = "r_esfera"    # todavía no existe: el paso da error
    doc.recalcular(2)
    assert doc.resultados[2].estado == "error"
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    tabla.agregar("r_esfera", "4 mm")
    doc.aplicar_parametros(tabla)
    assert doc.resultados[2].estado == "ok"


def test_ejemplo_parcial_igual_a_completo():
    """Con bocetos y cotas ligadas a parámetros, el parcial da lo mismo que recalcular todo."""
    doc = crear_documento_ejemplo()
    for nombre, expr in (("ancho", "75 mm"), ("alto_placa", "11 mm"), ("radio_agujero", "4 mm")):
        _cambiar(doc, **{nombre: expr})
        ref = _completo(doc)
        assert [r.estado for r in doc.resultados] == [r.estado for r in ref.resultados]
        assert sorted(g.volumen(c.forma) for c in doc.estado_final.cuerpos.values()) == pytest.approx(
            sorted(g.volumen(c.forma) for c in ref.estado_final.cuerpos.values()), rel=1e-9)


def test_configuracion_rehace_desde_la_supresion_que_cambia():
    doc = _doc()
    antes = list(doc._estados)
    datos = {"columnas": [{"tipo": "suprimir", "op": "op3"}], "filas": [{"nombre": "Sin esfera", "valores": ["sí"]}]}
    doc.aplicar_configuracion(datos, "Sin esfera")
    assert doc._estados[0] is antes[0] and doc._estados[1] is antes[1]
    assert doc.resultado("op3").estado == "suprimida"
    assert _volumen(doc) == pytest.approx(_volumen(_completo(doc)), rel=1e-9)
