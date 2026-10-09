# -*- coding: utf-8 -*-
import math

import pytest

from omnicad.timeline.parametros import (ANGULO, ESCALAR, LONGITUD, ErrorExpresion, TablaParametros,
                                             evaluar, nombres_usados)


@pytest.mark.parametrize("expr,tipo,esperado", [
    ("10", LONGITUD, 10.0),
    ("10 mm", LONGITUD, 10.0),
    ("2 cm", LONGITUD, 20.0),
    ("1in", LONGITUD, 25.4),
    ("1.5 m", LONGITUD, 1500.0),
    ("10 mm + 2 cm", LONGITUD, 30.0),
    ("(3 + 4) * 2", LONGITUD, 14.0),
    ("2 ** 3", ESCALAR, 8.0),
    ("90", ANGULO, 90.0),
    ("90 deg", ANGULO, 90.0),
    ("90°", ANGULO, 90.0),
    ("pi rad", ANGULO, None),  # 'pi rad' no es número+unidad; se valida abajo por separado
    ("sqrt(16)", ESCALAR, 4.0),
    ("max(2, 7)", ESCALAR, 7.0),
    ("10,5", LONGITUD, 10.5),
])
def test_evaluar(expr, tipo, esperado):
    if esperado is None:
        with pytest.raises(ErrorExpresion):
            evaluar(expr, tipo)
        return
    assert evaluar(expr, tipo) == pytest.approx(esperado)


def test_radianes_a_grados():
    assert evaluar("1 rad", ANGULO) == pytest.approx(math.degrees(1))


@pytest.mark.parametrize("expr,tipo", [
    ("10 deg", LONGITUD),       # unidad de ángulo en una longitud
    ("5 mm", ANGULO),           # unidad de longitud en un ángulo
    ("", LONGITUD),
    ("2 +", LONGITUD),
    ("__import__('os')", LONGITUD),
    ("x", LONGITUD),            # nombre desconocido
    ("1/0", LONGITUD),
    ("[1, 2]", LONGITUD),
])
def test_evaluar_rechaza(expr, tipo):
    with pytest.raises(ErrorExpresion):
        evaluar(expr, tipo)


def test_tabla_con_dependencias_y_ciclos():
    t = TablaParametros()
    t.agregar("ancho", "60 mm")
    t.agregar("mitad", "ancho / 2")
    assert t.valores() == {"ancho": 60.0, "mitad": 30.0}
    assert t.evaluar("mitad + 1 cm") == pytest.approx(40.0)
    t.modificar("ancho", "100")
    assert t.valores()["mitad"] == 50.0
    with pytest.raises(ErrorExpresion):
        t.modificar("ancho", "mitad * 2")       # ciclo → se rechaza y se conserva el valor anterior
    assert t.obtener("ancho").expresion == "100"
    with pytest.raises(ErrorExpresion):
        t.eliminar("ancho")                     # lo usa 'mitad'
    with pytest.raises(ErrorExpresion):
        t.agregar("mm", "1")                    # palabra reservada
    with pytest.raises(ErrorExpresion):
        t.agregar("2x", "1")                    # nombre inválido


def test_tabla_serializa():
    t = TablaParametros()
    t.agregar("a", "5 mm", comentario="hola")
    t.agregar("ang", "45", tipo=ANGULO)
    t2 = TablaParametros.desde_lista(t.a_lista())
    assert t2.valores() == t.valores()
    assert t2.obtener("a").comentario == "hola"


def test_nombres_usados():
    assert nombres_usados("ancho * 2 + 3 mm + sqrt(alto)") == {"ancho", "alto"}
