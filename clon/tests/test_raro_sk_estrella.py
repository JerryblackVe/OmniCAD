# -*- coding: utf-8 -*-
"""Valores raros en cada campo de la herramienta de boceto «sk_estrella» (BOC-84, propia de OmniCAD: Fusion no
tiene estrella; su ayuda de «Create polygons» fija Radio como longitud y Número de lados como entero, que es lo que
acá son los campos de la tarjeta y la barra de valores).

Se prueban los cinco campos numéricos de la tarjeta (Interior, Redondeo de puntas, Redondeo de valles, Puntas y
Salto) y los dos de la barra de valores (Radio y Puntas) en vacío, 0, negativo, enorme, con unidades y con
expresión; la casilla de Círculos de construcción, por ser booleana, se prueba en sus dos estados. Escribir un
valor raro nunca cierra la app, no deja el boceto roto y todo aviso es de un renglón. Puntas admite expresiones
y rechaza unidades ajenas con un aviso en español (B-798).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto, resolver  # noqa: E402

RAROS = ("", "0", "-5", "1000000000", "30 mm", "3+2")
CAMPOS_NUMERICOS = (
    ("Interior (0 = regular)", 0.0, 99.0),
    ("Redondeo de puntas", 0.0, 10000.0),
    ("Redondeo de valles", 0.0, 10000.0),
    ("Puntas", 3, 64),
    ("Salto (con Interior 0)", 2, 31),
)


@pytest.fixture
def ventana(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    v._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
    QTest.qWait(50)
    yield v
    v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _mover(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _teclear(sp, texto):
    sp.setFocus()
    QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
    for ch in texto:
        QTest.keyClick(sp, ch)


def _fila(mb, etiqueta):
    form = mb.tarjeta.form_contexto
    for i in range(form.rowCount()):
        if form.itemAt(i, form.ItemRole.LabelRole).widget().text() == etiqueta:
            return form.itemAt(i, form.ItemRole.FieldRole).widget()
    raise AssertionError(f"la tarjeta no tiene «{etiqueta}»")


def _lineas(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion]


def _sin_rotura(v, lz, avisos, fallos):
    assert not fallos, fallos
    assert QApplication.instance() is not None and v.isVisible() and lz.isVisible()
    resolver(lz.b)
    assert lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def _un_renglon(avisos):
    assert len(avisos) == 1, avisos
    assert "\n" not in avisos[0] and "\r" not in avisos[0], avisos[0]
    return avisos[0]


def _valor_en_rango(sp, minimo, maximo):
    """Lo tecleado fuera de rango lo sujeta el widget del formulario, como en Fusion."""
    valor = sp.value()
    assert minimo <= valor <= maximo, valor


# ---------------------------------------------------------------- tarjeta: cinco campos numéricos y una casilla
@pytest.mark.parametrize("etiqueta, minimo, maximo", CAMPOS_NUMERICOS)
@pytest.mark.parametrize("texto", RAROS)
def test_campo_de_la_tarjeta_con_valor_raro_no_rompe_el_boceto(ventana, etiqueta, minimo, maximo, texto):
    mb, lz = ventana.modo_boceto, ventana.modo_boceto.lienzo
    avisos = []
    lz.mensaje.connect(avisos.append)
    mb.acciones["sk_estrella"].trigger()
    sp = _fila(mb, etiqueta)
    fallos = []
    try:
        _teclear(sp, texto)
        _clic(lz, 0, 0)
        _clic(lz, 0, 20)
        lz.grab()
    except Exception as e:  # noqa: BLE001 — cualquier excepción acá es un bug: no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    _sin_rotura(ventana, lz, avisos, fallos)
    _valor_en_rango(sp, minimo, maximo)
    lineas = _lineas(lz)
    assert len(lineas) >= 6 and len(lineas) % 2 == 0, len(lineas)      # nunca media estrella
    assert any(c.tipo == "circulo" for c in lz.b.curvas.values())


@pytest.mark.parametrize("marcado", [True, False])
def test_casilla_circulos_de_construccion_no_rompe_el_boceto(ventana, marcado):
    """La casilla es booleana: no admite los otros valores raros, pero sus dos estados se dibujan sin romper."""
    mb, lz = ventana.modo_boceto, ventana.modo_boceto.lienzo
    avisos = []
    lz.mensaje.connect(avisos.append)
    mb.acciones["sk_estrella"].trigger()
    casilla = _fila(mb, "Círculos de construcción")
    assert isinstance(casilla, QCheckBox)
    casilla.setChecked(marcado)
    _clic(lz, 0, 0)
    _clic(lz, 0, 20)
    lz.grab()
    _sin_rotura(ventana, lz, avisos, [])
    construccion = [c for c in lz.b.curvas.values() if c.tipo == "circulo" and c.construccion]
    assert len(construccion) == (2 if marcado else 0)
    assert len(_lineas(lz)) == 10


# ---------------------------------------------------------------- barra de valores: Radio y Puntas
def _barra(ventana, campo, texto):
    """Un clic en el centro, ratón a 20 mm, escribir en la caja activa y Enter: recoge avisos y excepciones."""
    mb, lz = ventana.modo_boceto, ventana.modo_boceto.lienzo
    mb.acciones["sk_estrella"].trigger()
    _clic(lz, 0, 0)
    _mover(lz, 0, 20)
    avisos = []
    lz.mensaje.connect(avisos.append)
    assert [c.clave for c in lz._campos_vivos()] == ["radio", "puntas"]
    lz._activo = 0 if campo == "radio" else 1
    lz._editar_campo_vivo("")
    assert lz.entrada is not None and len(lz.entrada.campos) == 1
    lz.entrada.campos[0].setText(texto)
    avisos.clear()                                  # el cartel de la herramienta no es un aviso de error
    fallos = []
    try:
        lz.entrada.aceptado.emit([texto])
    except Exception as e:  # noqa: BLE001 — cualquier excepción acá es un bug: Enter no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()
    return lz, avisos, fallos


@pytest.mark.parametrize("texto, esperado", [("", 20.0), ("30 mm", 30.0), ("3+2", 5.0)])
def test_radio_con_valor_raro_valido_dibuja_la_estrella(ventana, texto, esperado):
    lz, avisos, fallos = _barra(ventana, "radio", texto)
    _sin_rotura(ventana, lz, avisos, fallos)
    assert not avisos and lz.entrada is None
    exterior = max((c for c in lz.b.curvas.values() if c.tipo == "circulo"), key=lambda c: c.radio)
    assert exterior.radio == pytest.approx(esperado)
    assert len(_lineas(lz)) == 10


@pytest.mark.parametrize("texto", ["0", "-5", "1000000000"])
def test_radio_fuera_de_rango_avisa_y_no_dibuja(ventana, texto):
    lz, avisos, fallos = _barra(ventana, "radio", texto)
    _sin_rotura(ventana, lz, avisos, fallos)
    assert _lineas(lz) == [] and lz.entrada is not None
    assert "radio" in _un_renglon(avisos).lower()


@pytest.mark.parametrize("texto, esperado", [("", 5), ("6", 6)])
def test_puntas_con_valor_raro_valido_dibuja_la_estrella(ventana, texto, esperado):
    lz, avisos, fallos = _barra(ventana, "puntas", texto)
    _sin_rotura(ventana, lz, avisos, fallos)
    assert not avisos and lz.entrada is None
    assert len(_lineas(lz)) == 2 * esperado


@pytest.mark.parametrize("texto", ["0", "-5", "1000000000"])
def test_puntas_fuera_de_rango_avisa_y_no_dibuja(ventana, texto):
    lz, avisos, fallos = _barra(ventana, "puntas", texto)
    _sin_rotura(ventana, lz, avisos, fallos)
    assert _lineas(lz) == [] and lz.entrada is not None
    assert "puntas" in _un_renglon(avisos).lower()


def test_puntas_con_expresion_debe_dibujar_la_estrella(ventana):
    """Como Vueltas de Espiral: «3+2» evalúa a 5 puntas, sin error de Python."""
    lz, avisos, fallos = _barra(ventana, "puntas", "3+2")
    _sin_rotura(ventana, lz, avisos, fallos)
    assert not avisos and lz.entrada is None
    assert len(_lineas(lz)) == 10


def test_puntas_con_unidad_ajena_debe_rechazarla_en_espanol(ventana):
    """Como Cantidad de Patrón (B-712): «6 mm» no puede crear 6 puntas y el aviso no puede ser error de Python."""
    lz, avisos, fallos = _barra(ventana, "puntas", "6 mm")
    _sin_rotura(ventana, lz, avisos, fallos)
    mensaje = _un_renglon(avisos)
    assert "puntas" in mensaje.lower() and "could not convert" not in mensaje.lower(), mensaje
    assert _lineas(lz) == [] and lz.entrada is not None
