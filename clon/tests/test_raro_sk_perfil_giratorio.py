# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_perfil_giratorio» (Spun Profile de Fusion).

La ayuda oficial de Fusion («Project the spun profile of geometry») define Geometría, Eje, Tolerancia,
Vínculo de proyección, Proyectar eje e Invertir; la tarjeta de OmniCAD agrupa esos controles en «Tipo»,
«Geometría», «Eje», «Tolerancia», «Invertir», «Vínculo de proyección», «Solo contorno exterior» y «Proyectar eje».
Cada campo se prueba vacío, con cero, negativo, enorme, con unidades y con expresión; un valor inválido no puede
cerrar la app, romper el boceto ni devolver un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QFormLayout  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402

B814 = "B-814: la tarjeta no avisa cuando Tolerancia queda fuera de 0,001–10 mm"

VALORES = {
    "axis": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "edges": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "faces": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "bodies": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "vertices": (([], "vacio"), ([[0, 0, 0]], "cero"), ([[-5, -5, -5]], "negativo"),
                 ([[1e9, 1e9, 1e9]], "enorme"), ([["5 mm", 0, 0]], "unidad"), ([["5*2", 0, 0]], "expresion")),
    "tolerance": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "flip": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("1", "unidad"), ("1+1", "expresion")),
    "link": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("1", "unidad"), ("1+1", "expresion")),
    "construction": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("1", "unidad"), ("1+1", "expresion")),
    "body": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "sketch": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("5 mm", "unidad"), ("5*2", "expresion")),
    "outer_contour": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("1", "unidad"), ("1+1", "expresion")),
    "project_axis": (("", "vacio"), (0, "cero"), (-5, "negativo"), (1e9, "enorme"), ("1", "unidad"), ("1+1", "expresion")),
}

CASOS = [
    pytest.param(campo, valor, id=f"{campo}_{nombre}")
    for campo, valores in VALORES.items()
    for valor, nombre in valores
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sesion(app):
    s = api.Sesion()
    assert _llamar(s, "create_box", length=20, width=20, height=10)["ok"]
    assert _llamar(s, "create_sketch", plane="XZ", name="Giro")["ok"]
    return s


@pytest.fixture
def tarjeta(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XZ"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    lz.set_herramienta("perfil_giratorio")
    t = modo_boceto.TarjetaHerramienta(lz)
    t.lienzo = lz
    t.ajuste.connect(lambda clave, valor: lz.opciones.__setitem__(clave, valor))
    t.set_herramienta("perfil_giratorio", opciones=lz.opciones)
    yield lz, t
    t.deleteLater()
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _llamar(sesion, herramienta, **args):
    resultado = api.llamar(sesion, herramienta, args)
    assert isinstance(resultado, dict) and isinstance(resultado.get("ok"), bool), resultado
    return resultado


def _argumentos(campo, valor):
    if campo == "axis":
        return {"axis": valor}
    if campo in ("edges", "faces", "bodies", "vertices"):
        return {"axis": "Z", campo: valor}
    if campo == "body":
        return {"axis": "Z", "faces": [">Z"], "body": valor}
    if campo == "sketch":
        return {"axis": "Z", "bodies": ["Cuerpo1"], "sketch": valor}
    return {"axis": "Z", "bodies": ["Cuerpo1"], campo: valor}


def _control(tarjeta, etiqueta):
    form = tarjeta.form_contexto
    for fila in range(form.rowCount()):
        nombre = form.itemAt(fila, QFormLayout.LabelRole)
        if nombre and nombre.widget().text() == etiqueta:
            return form.itemAt(fila, QFormLayout.FieldRole).widget()
    pytest.fail(f"Falta el control {etiqueta}")


def _escribir(campo, texto):
    """Toca el texto del campo y lo interpreta, sin tocar Enter (en el boceto Enter acepta la proyección)."""
    linea = campo.lineEdit()
    linea.selectAll()
    if texto:
        QTest.keyClicks(linea, texto)
    else:
        QTest.keyClick(linea, Qt.Key_Backspace)
    campo.interpretText()
    QApplication.instance().processEvents()


def _avisos(avisos, tarjeta):
    textos = list(avisos)
    if tarjeta.mensaje.text() and tarjeta.mensaje.text() not in textos:
        textos.append(tarjeta.mensaje.text())
    return textos


def test_la_tarjeta_tiene_los_campos_de_fusion(tarjeta):
    lz, t = tarjeta
    form = t.form_contexto
    etiquetas = {
        form.itemAt(fila, QFormLayout.LabelRole).widget().text()
        for fila in range(form.rowCount())
        if form.itemAt(fila, QFormLayout.LabelRole)
    }
    assert etiquetas == {
        "Tipo", "Geometría", "Eje", "Tolerancia", "Invertir", "Vínculo de proyección",
        "Solo contorno exterior", "Proyectar eje",
    }
    assert lz.herramienta == "perfil_giratorio"


@pytest.mark.parametrize(("campo", "valor"), CASOS)
def test_cada_campo_con_valor_raro_no_cierra_app_ni_deja_boceto_roto(sesion, campo, valor):
    antes = _llamar(sesion, "get_sketch", sketch="Giro")
    assert antes["ok"]

    resultado = _llamar(sesion, "project_spun_profile", **_argumentos(campo, valor))

    despues = _llamar(sesion, "get_sketch", sketch="Giro")
    assert QApplication.instance() is not None
    assert despues["ok"]
    assert despues["result"]["status"] != "error"
    if not resultado["ok"]:
        assert despues["result"] == antes["result"], (campo, valor, resultado)
        mensaje = resultado.get("mensaje")
        assert isinstance(mensaje, str) and mensaje, (campo, valor, resultado)
        assert "\n" not in mensaje and "\r" not in mensaje, (campo, valor, mensaje)
        assert resultado.get("error_kind"), (campo, valor, resultado)
    else:
        assert resultado["result"]["entities"], (campo, valor, resultado)
        assert despues["result"] != antes["result"], (campo, valor, resultado)


def test_valores_validos_siguen_proyectando_el_perfil(sesion):
    resultado = _llamar(sesion, "project_spun_profile", axis="Z", bodies=["Cuerpo1"])
    assert resultado["ok"], resultado
    assert resultado["result"]["entities"], resultado


def test_tolerancia_fuera_de_rango_avisa_en_un_renglon(tarjeta):
    lz, t = tarjeta
    avisos = []
    lz.mensaje.connect(avisos.append)
    campo = _control(t, "Tolerancia")
    assert isinstance(campo, QDoubleSpinBox)

    for texto in ("0", "-0.1", "10000"):
        avisos.clear()
        _escribir(campo, texto)

        assert QApplication.instance() is not None
        assert lz.isVisible()
        assert campo.minimum() <= campo.value() <= campo.maximum(), texto
        assert lz.opciones["tolerancia_giro"] == pytest.approx(campo.value()), texto
        resolver(lz.b)
        mensajes = _avisos(avisos, t)
        assert mensajes, texto
        assert all("\n" not in mensaje and "\r" not in mensaje for mensaje in mensajes), mensajes


def test_tolerancia_vacia_conserva_el_valor_por_defecto(tarjeta):
    lz, t = tarjeta
    avisos = []
    lz.mensaje.connect(avisos.append)
    campo = _control(t, "Tolerancia")

    _escribir(campo, "")

    assert campo.value() == pytest.approx(0.1)
    assert lz.opciones["tolerancia_giro"] == pytest.approx(0.1)
    assert not _avisos(avisos, t)
    resolver(lz.b)


def test_tolerancia_con_unidad_conserva_la_medida(tarjeta):
    lz, t = tarjeta
    avisos = []
    lz.mensaje.connect(avisos.append)
    campo = _control(t, "Tolerancia")

    _escribir(campo, "0.1 mm")

    assert campo.value() == pytest.approx(0.1)
    assert lz.opciones["tolerancia_giro"] == pytest.approx(0.1)
    assert not _avisos(avisos, t)
    resolver(lz.b)


@pytest.mark.parametrize(("texto", "esperado"), [("0.05*2", 0.1), ("0,05*2", 0.1), ("5*2", 10.0)])
def test_tolerancia_con_expresion_evalua_la_medida(tarjeta, texto, esperado):
    lz, t = tarjeta
    avisos = []
    lz.mensaje.connect(avisos.append)
    campo = _control(t, "Tolerancia")

    _escribir(campo, texto)

    assert campo.value() == pytest.approx(esperado)
    assert lz.opciones["tolerancia_giro"] == pytest.approx(esperado)
    assert not _avisos(avisos, t)
    resolver(lz.b)


def test_tolerancia_con_expresion_invalida_avisa_en_un_renglon(tarjeta):
    lz, t = tarjeta
    avisos = []
    lz.mensaje.connect(avisos.append)
    campo = _control(t, "Tolerancia")

    _escribir(campo, "0,05*")

    assert campo.value() == pytest.approx(0.05)         # queda el último valor válido tecleado (el campo actualiza al teclear)
    assert lz.opciones["tolerancia_giro"] == pytest.approx(0.05)
    mensajes = _avisos(avisos, t)
    assert mensajes
    assert all("\n" not in mensaje and "\r" not in mensaje for mensaje in mensajes), mensajes
    assert any("Tolerancia" in mensaje for mensaje in mensajes), mensajes
