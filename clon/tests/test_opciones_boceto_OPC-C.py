# -*- coding: utf-8 -*-
"""Opciones de la tarjeta de Estrella del boceto (preparado/opciones_asas_boceto.md): Interior, Redondeos, Puntas y
Salto. Cada prueba dibuja en la ventana (offscreen) con la opción puesta y mide el resultado en el boceto."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones.boceto import proporcion_estrella  # noqa: E402
from omnicad.restricciones.boceto_crear import validar_puntas_estrella  # noqa: E402


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


def _teclear(sp, texto):
    sp.setFocus()
    QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
    for ch in texto:
        QTest.keyClick(sp, ch)


def _spin(mb, etiqueta):
    form = mb.tarjeta.form_contexto
    for i in range(form.rowCount()):
        if form.itemAt(i, form.ItemRole.LabelRole).widget().text() == etiqueta:
            return form.itemAt(i, form.ItemRole.FieldRole).widget()
    raise AssertionError(f"la tarjeta no tiene «{etiqueta}»")


def _estrella(mb, radio=20.0, **opciones):
    """Activa Estrella, teclea las opciones de la tarjeta y dibuja centro (0,0) y punta (0, radio)."""
    lz = mb.lienzo
    mb.acciones["sk_estrella"].trigger()
    for etiqueta, valor in opciones.items():
        _teclear(_spin(mb, etiqueta), valor)
    _clic(lz, 0, 0)
    _clic(lz, 0, radio)
    assert lz.resultado.ok
    return lz


def _lineas(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion]


def _arcos(lz):
    return [c for c in lz.b.curvas.values() if c.tipo == "arco" and not c.construccion]


def _area(lz):
    """Área del contorno por la fórmula del zapatero, con los vértices ordenados por ángulo (centro en 0,0)."""
    b = lz.b
    pts = {b.coords(q) for c in _lineas(lz) for q in (c.p1, c.p2)}
    pts = sorted(pts, key=lambda p: math.atan2(p[1], p[0]))
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True))) / 2


def _radio_arco(lz, arco):
    b = lz.b
    return math.dist(b.coords(arco.inicio), b.coords(arco.centro))


def _circulos(lz):
    return sorted((c for c in lz.b.curvas.values() if c.tipo == "circulo"), key=lambda c: -c.radio)


def test_interior_estrella_es_el_porcentaje_del_radio_exterior(boceto):
    lz = _estrella(boceto, 20.0, **{"Interior (0 = regular)": "40"})
    exterior, interior = _circulos(lz)
    assert exterior.radio == pytest.approx(20.0)
    assert interior.radio == pytest.approx(0.40 * 20.0)              # interior_estrella = 40 %
    assert _area(lz) == pytest.approx(5 * 20 * 8 * math.sin(math.pi / 5), rel=1e-6)


def test_interior_estrella_cero_usa_el_salto_y_no_el_porcentaje(boceto):
    lz = _estrella(boceto, 10.0, Puntas="7", **{"Interior (0 = regular)": "0",
                                                "Salto (con Interior 0)": "3"})
    interior = _circulos(lz)[1]
    r = 10 * proporcion_estrella(7, 3)
    assert interior.radio == pytest.approx(r)
    assert _area(lz) == pytest.approx(7 * 10 * r * math.sin(math.pi / 7), rel=1e-6)
    assert len(_lineas(lz)) == 14


def test_redondeo_puntas_redondea_las_cinco_puntas(boceto):
    lz = _estrella(boceto, 20.0, **{"Redondeo de puntas": "1,5"})
    arcos = _arcos(lz)
    assert len(arcos) == 5 and len(_lineas(lz)) == 10
    assert all(_radio_arco(lz, a) == pytest.approx(1.5) for a in arcos)
    assert _area(lz) < 5 * 20 * 20 * proporcion_estrella(5) * math.sin(math.pi / 5)


def test_redondeo_valles_redondea_los_cinco_valles_y_suma_area(boceto):
    lz = _estrella(boceto, 20.0, **{"Redondeo de valles": "1"})
    arcos = _arcos(lz)
    assert len(arcos) == 5 and len(_lineas(lz)) == 10
    assert all(_radio_arco(lz, a) == pytest.approx(1.0) for a in arcos)
    r = 20 * proporcion_estrella(5)
    assert _area(lz) > 5 * 20 * r * math.sin(math.pi / 5)            # el valle redondeado agrega material


@pytest.mark.parametrize("puntas", [3, 7, 64])
def test_puntas_estrella_da_dos_lineas_por_punta(boceto, puntas):
    lz = _estrella(boceto, 10.0, Puntas=str(puntas))
    assert len(_lineas(lz)) == 2 * puntas
    b = lz.b
    exteriores = {b.coords(q) for c in _lineas(lz) for q in (c.p1, c.p2)
                  if math.dist(b.coords(q), (0, 0)) == pytest.approx(10.0)}
    assert len(exteriores) == puntas


def test_puntas_estrella_fuera_de_rango_lo_dice_el_validador():
    assert validar_puntas_estrella(3) == 3 and validar_puntas_estrella(64) == 64
    for malas in (2, 65):
        with pytest.raises(ValueError, match="entre 3 y 64 puntas"):
            validar_puntas_estrella(malas)
