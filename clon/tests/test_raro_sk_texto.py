# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_texto»: cada campo de su diálogo (Texto, Altura, ∠, Espaciado (%) e
Interlineado) en vacío, 0, negativo, enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el
boceto roto, y todo aviso es de un renglón. La ayuda de Fusion (`reference-text-dialog`, `create-text-in-a-sketch`)
fija Altura en unidades del documento, Espaciado como porcentaje y el Texto con parámetros entre llaves."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.restricciones.boceto import Texto  # noqa: E402
from omnicad.timeline.parametros import ANGULO, TablaParametros  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos

CAMPOS = ("Texto", "Altura", "∠", "Espaciado (%)", "Interlineado")
BASE = ["Hola", "5", "0", "0", "1"]

# (índice del campo, valor raro, id legible). El «enorme» del Texto pasa el tope de 1000 caracteres; el de Altura,
# el tope de 10.000 mm; los de Espaciado/Interlineado son números finitos y se aceptan (Fusion no les pone tope).
CASOS = [
    (0, "", "texto_vacio"), (0, "0", "texto_cero"), (0, "-5", "texto_negativo"),
    (0, "1e9", "texto_enorme"), (0, "5 mm", "texto_unidad"), (0, "{ancho}", "texto_expresion"),
    (0, "X" * 1001, "texto_milenario"),
    (1, "", "altura_vacia"), (1, "0", "altura_cero"), (1, "-5", "altura_negativa"),
    (1, "1e9", "altura_enorme"), (1, "5 mm", "altura_unidad"), (1, "2*3", "altura_expresion"),
    (2, "", "angulo_vacio"), (2, "0", "angulo_cero"), (2, "-30", "angulo_negativo"),
    (2, "1e9", "angulo_enorme"), (2, "45 deg", "angulo_unidad"), (2, "giro", "angulo_expresion"),
    (3, "", "espaciado_vacio"), (3, "0", "espaciado_cero"), (3, "-5", "espaciado_negativo"),
    (3, "1e9", "espaciado_enorme"), (3, "10 mm", "espaciado_unidad"), (3, "10+20", "espaciado_expresion"),
    (4, "", "interlineado_vacio"), (4, "0", "interlineado_cero"), (4, "-5", "interlineado_negativo"),
    (4, "1e9", "interlineado_enorme"), (4, "2 mm", "interlineado_unidad"), (4, "2*3", "interlineado_expresion"),
]


def _abrir(app_qt, valores):
    """Barra de Texto abierta tras los 2 clics con los 5 campos escritos; recoge avisos y excepciones al Aceptar."""
    lz = T._lienzo(app_qt, Boceto())
    tabla = TablaParametros()
    tabla.agregar("ancho", "20 mm")
    tabla.agregar("giro", "45 deg", ANGULO)
    lz._evaluar_doc = tabla.evaluar
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.grab()
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 0.0)))
    lz.clics.append((None, (40.0, 20.0)))
    lz._procesar_clics()
    assert lz.entrada is not None, "los 2 clics abren la barra del Texto"
    assert len(lz.entrada.campos) == len(CAMPOS)
    for campo, valor in zip(lz.entrada.campos, valores, strict=True):
        campo.setText(valor)
    antes = lz.b.a_dict()
    avisos.clear()                                  # el cartel de la herramienta no es un aviso de error
    fallos = []
    try:
        lz.entrada.aceptado.emit([c.text().strip() for c in lz.entrada.campos])
    except Exception as e:  # noqa: BLE001 — cualquier excepción aquí es un bug: Aceptar no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()                                       # redibuja: Aceptar no puede cerrar la app
    return lz, avisos, fallos, antes


def _textos(lz):
    return [c for c in lz.b.curvas.values() if isinstance(c, Texto)]


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and lz.isVisible()
    lz.resolver()
    assert lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def _cerrar(lz):
    if lz.entrada is not None:
        lz.entrada.cancelado.emit()
        QApplication.instance().processEvents()


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


@pytest.mark.parametrize("indice,valor,id_caso", CASOS, ids=[c[2] for c in CASOS])
def test_cada_campo_con_valor_raro_no_rompe_el_boceto(app_qt, indice, valor, id_caso):
    """Vacío, cero, negativo, enorme, con unidades y con expresión: Aceptar nunca tumba la app ni deja el boceto roto."""
    valores = BASE.copy()
    valores[indice] = valor
    lz, avisos, fallos, antes = _abrir(app_qt, valores)
    _sin_rotura(lz, avisos, fallos)
    textos = _textos(lz)
    if textos:
        assert len(textos) == 1 and lz.entrada is None
        assert 0 < textos[0].altura < 2e4
    else:
        assert lz.entrada is not None and lz.b.a_dict() == antes
    _cerrar(lz)


def test_texto_vacio_avisa_en_un_renglon_y_no_crea_texto(app_qt):
    lz, avisos, fallos, antes = _abrir(app_qt, ["", *BASE[1:]])
    _sin_rotura(lz, avisos, fallos)
    assert _textos(lz) == [] and lz.entrada is not None and lz.b.a_dict() == antes
    assert "vacío" in _un_renglon(avisos).lower()
    _cerrar(lz)


def test_texto_milenario_avisa_y_no_crea_texto(app_qt):
    lz, avisos, fallos, antes = _abrir(app_qt, ["X" * 1001, *BASE[1:]])
    _sin_rotura(lz, avisos, fallos)
    assert _textos(lz) == [] and lz.entrada is not None and lz.b.a_dict() == antes
    assert "máximo" in _un_renglon(avisos) and "caracteres" in avisos[0]
    _cerrar(lz)


@pytest.mark.parametrize("altura", ["0", "-5", "1e9"])
def test_altura_invalida_avisa_y_no_crea_texto(app_qt, altura):
    lz, avisos, fallos, antes = _abrir(app_qt, [BASE[0], altura, *BASE[2:]])
    _sin_rotura(lz, avisos, fallos)
    assert _textos(lz) == [] and lz.entrada is not None and lz.b.a_dict() == antes
    assert "altura" in _un_renglon(avisos).lower()
    _cerrar(lz)


def test_altura_vacia_usa_el_valor_por_defecto(app_qt):
    lz, avisos, fallos, _antes = _abrir(app_qt, [BASE[0], "", *BASE[2:]])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos
    (texto,) = _textos(lz)
    assert texto.altura == pytest.approx(5.0)


@pytest.mark.parametrize("altura,esperado", [("5 mm", 5.0), ("2*3", 6.0), ("ancho", 20.0)])
def test_altura_con_unidades_o_expresion_acepta(app_qt, altura, esperado):
    lz, avisos, fallos, _antes = _abrir(app_qt, [BASE[0], altura, *BASE[2:]])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos
    (texto,) = _textos(lz)
    assert texto.altura == pytest.approx(esperado)


@pytest.mark.parametrize("angulo,esperado", [("", 0.0), ("0", 0.0), ("-30", -30.0), ("45 deg", 45.0), ("giro", 45.0)])
def test_angulo_cero_negativo_unidades_y_expresion_acepta(app_qt, angulo, esperado):
    lz, avisos, fallos, _antes = _abrir(app_qt, [BASE[0], BASE[1], angulo, *BASE[3:]])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos
    (texto,) = _textos(lz)
    assert texto.angulo == pytest.approx(esperado)


@pytest.mark.parametrize("espaciado", ["", "0", "-5", "1e9"])
def test_espaciado_vacio_cero_negativo_y_enorme_no_rompe(app_qt, espaciado):
    lz, avisos, fallos, _antes = _abrir(app_qt, [*BASE[:3], espaciado, BASE[4]])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos and len(_textos(lz)) == 1


@pytest.mark.parametrize("interlineado", ["0", "-5"])
def test_interlineado_cero_y_negativo_avisa_en_un_renglon(app_qt, interlineado):
    lz, avisos, fallos, antes = _abrir(app_qt, [*BASE[:4], interlineado])
    _sin_rotura(lz, avisos, fallos)
    assert _textos(lz) == [] and lz.entrada is not None and lz.b.a_dict() == antes
    assert "interlineado" in _un_renglon(avisos).lower()
    _cerrar(lz)


@pytest.mark.parametrize("campo,indice,valor", [("Espaciado (%)", 3, "10+20"), ("Interlineado", 4, "2*3")])
def test_campos_con_expresion_deben_evaluarla(app_qt, campo, indice, valor):
    lz, avisos, fallos, _antes = _abrir(app_qt, [*BASE[:indice], valor, *BASE[indice + 1:]])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos, (campo, avisos)
    (texto,) = _textos(lz)
    if campo == "Interlineado":
        assert texto.interlineado == pytest.approx(6.0)


@pytest.mark.parametrize("campo,indice,valor", [("Espaciado (%)", 3, "10 mm"), ("Interlineado", 4, "2 mm")])
def test_campos_con_unidad_deben_avisar_en_espanol(app_qt, campo, indice, valor):
    lz, avisos, fallos, antes = _abrir(app_qt, [*BASE[:indice], valor, *BASE[indice + 1:]])
    _sin_rotura(lz, avisos, fallos)
    assert _textos(lz) == [] and lz.entrada is not None and lz.b.a_dict() == antes
    mensaje = _un_renglon(avisos)
    assert "could not convert" not in mensaje.lower()
    assert campo.split(" ")[0].lower() in mensaje.lower() or "interlineado" in mensaje.lower() or "espaciado" in mensaje.lower()
    _cerrar(lz)


def test_interlineado_vacio_usa_uno(app_qt):
    lz, avisos, fallos, _antes = _abrir(app_qt, [*BASE[:4], ""])
    _sin_rotura(lz, avisos, fallos)
    assert not avisos
    (texto,) = _textos(lz)
    assert texto.interlineado == pytest.approx(1.0)
