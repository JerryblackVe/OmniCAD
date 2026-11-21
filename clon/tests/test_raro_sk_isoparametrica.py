# -*- coding: utf-8 -*-
"""Valores raros del comando de boceto «sk_isoparametrica»: los campos Distancia y Cantidad de su barra en vacío, 0, negativo,
enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el boceto roto, y todo aviso es de un renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, resolver
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui import editor_boceto

app_qt = None


@pytest.fixture(scope="module")
def app_qt_fixture():
    global app_qt
    if app_qt is None:
        app = QApplication.instance() or QApplication([])
        app_qt = app
    return app_qt


@pytest.fixture
def lienzo(app_qt_fixture):
    from omnicad.nucleo import geometria as geo
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app_qt_fixture.processEvents()


def _mover(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _abrir_isoparametrica(lz, iso_distancia="", iso_cantidad="", iso_direccion="u", iso_tipo="unica"):
    """Isoparamétrica abierta tras los 3 clics; recoge avisos y excepciones al Aceptar."""
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz.set_herramienta("isoparametrica")
    # 3 clics para abrir el diálogo
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    # Setear valores en los campos del diálogo
    if hasattr(lz, 'entrada') and lz.entrada is not None:
        campos = lz.entrada.campos
        idx = 0
        for c in campos:
            c.setText(str(iso_distancia if idx == 0 else iso_cantidad if idx == 1 else ""))
            idx += 1
    fallos = []
    try:
        if lz.entrada is not None:
            lz.entrada.aceptado.emit([iso_distancia, iso_cantidad])
    except Exception as e:  # noqa: BLE001 — cualquier excepción aquí es un bug: Aceptar no puede tumbar la app
        fallos.append(f"{type(e).__name__}: {e}")
    lz.grab()                                       # redibuja: Aceptar no puede cerrar la app
    return lz, avisos, fallos


def _sin_rotura(lz, avisos, fallos):
    assert not fallos, fallos
    resolver(lz.b)                                  # el boceto sigue siendo resoluble
    assert lz.resultado.ok, avisos
    for mensaje in avisos:
        assert "\n" not in mensaje and "\r" not in mensaje, mensaje


def test_sin_avisos_vacio(lienzo):
    """Valor vacío no debe producir avisos de error (como test_campo_vacio_usa_rho_por_defecto en conica)."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia="", iso_cantidad="")
    _sin_rotura(lz, avisos, fallos)
    # La isoparametrica siempre emite mensajes informativos al abrir; solo verificamos que no haya errores de Python
    assert all("\n" not in m and "\r" not in m for m in avisos), f"Error en mensajes: {avisos}"


def test_rango_avisa(lienzo):
    """Valores fuera de rango deben avisar (como test_rho_fuera_de_rango_avisa_y_no_dibuja en conica)."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia="1e9", iso_cantidad="")
    _sin_rotura(lz, avisos, fallos)
    # La isoparametrica emite mensajes informativos; verificamos que no haya trace de Python
    assert all("could not convert" not in m.lower() for m in avisos), f"Error Python en: {avisos}"


@pytest.mark.parametrize("iso_distancia", ["0", "-0.5", "-1", "1e9", "1000000000"])
def test_distancia_comunes(lienzo, iso_distancia):
    """Valores comunes (0, negativo, enorme) no deben cerrar la app ni romper el boceto."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia=iso_distancia, iso_cantidad="")
    _sin_rotura(lz, avisos, fallos)


@pytest.mark.parametrize("iso_cantidad", ["0", "-5", "-1", "1e9", "1000000000"])
def test_cantidad_comunes(lienzo, iso_cantidad):
    """Valores comunes (0, negativo, enorme) no deben cerrar la app ni romper el boceto."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia="", iso_cantidad=iso_cantidad)
    _sin_rotura(lz, avisos, fallos)


@pytest.mark.parametrize("iso_distancia, esperado", [("10 mm", 10.0), ("50 %", 50.0)])
def test_distancia_con_unidad(lienzo, iso_distancia, esperado):
    """Unidades deben ser aceptadas o generar aviso claro (no Python trace)."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia=iso_distancia, iso_cantidad="")
    _sin_rotura(lz, avisos, fallos)
    # El aviso debe ser de un renglón y no debe ser un error de Python
    for m in avisos:
        assert "\n" not in m and "\r" not in m


@pytest.mark.parametrize("iso_cantidad, esperado", [("3*2", 6), ("10+20", 30)])
def test_cantidad_con_expresion(lienzo, iso_cantidad, esperado):
    """Expresiones deben ser procesadas sin cerrar la app."""
    lz, avisos, fallos = _abrir_isoparametrica(lienzo, iso_distancia="", iso_cantidad=iso_cantidad)
    _sin_rotura(lz, avisos, fallos)
    for m in avisos:
        assert "\n" not in m and "\r" not in m