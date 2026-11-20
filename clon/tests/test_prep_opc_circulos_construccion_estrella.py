# -*- coding: utf-8 -*-
"""PREP: opción «Círculos de construcción (Casilla)» de la tarjeta de Estrella del boceto
(preparado/opciones_asas_boceto.md). La estrella es propia de OmniCAD (BOC-84, Fusion no la tiene): sus círculos
guía son geometría de construcción de Fusion, que no forma perfiles y da el centro y el radio que definen la figura
(docs/fusion_docs/contenido/fusion-sketch/circles-in-sketches-032acc404df.md y create-polygons-5ca92735d53.md)."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402


@pytest.fixture
def boceto(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.restricciones import Boceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    v._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
    QTest.qWait(50)
    yield v.modo_boceto
    v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _casilla(mb, etiqueta):
    form = mb.tarjeta.form_contexto
    for i in range(form.rowCount()):
        w = form.itemAt(i, form.ItemRole.FieldRole).widget()
        if isinstance(w, QCheckBox):
            if form.itemAt(i, form.ItemRole.LabelRole).widget().text() == etiqueta:
                return w
    raise AssertionError(f"la tarjeta no tiene la casilla «{etiqueta}»")


def _dibujar(mb, radio=20.0, con_circulos=None):
    lz = mb.lienzo
    mb.acciones["sk_estrella"].trigger()
    if con_circulos is not None:
        _casilla(mb, "Círculos de construcción").setChecked(con_circulos)
    _clic(lz, 0, 0)
    _clic(lz, 0, radio)
    assert lz.resultado.ok
    return lz


def _circulos(lz):
    return sorted((c for c in lz.b.curvas.values() if c.tipo == "circulo"), key=lambda c: -c.radio)


def test_los_circulos_de_construccion_tienen_los_radios_exterior_e_interior(boceto):
    lz = _dibujar(boceto)
    assert lz.opciones["circulos_estrella"] is True
    circulos = _circulos(lz)
    assert len(circulos) == 2
    assert all(c.construccion for c in circulos)
    esperado = [20.0, 20.0 * math.cos(2 * math.pi / 5) / math.cos(math.pi / 5)]
    assert [c.radio for c in circulos] == pytest.approx(esperado)
    assert all(math.hypot(*lz.b.coords(c.centro)) == pytest.approx(0.0) for c in circulos)
    coincidentes = [r for r in lz.b.restricciones.values() if r.tipo == "coincidente"]
    assert len(coincidentes) == 10


def test_al_deseleccionar_la_casilla_no_hay_circulos_ni_coincidencias(boceto):
    lz = _dibujar(boceto, con_circulos=False)
    assert lz.opciones["circulos_estrella"] is False
    assert _circulos(lz) == []
    assert len([c for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion]) == 10
    assert not [r for r in lz.b.restricciones.values() if r.tipo == "coincidente"]
