# -*- coding: utf-8 -*-
"""PREP: opción «Interior / Redondeo de puntas / Redondeo de valles (numérico)» de la tarjeta de Estrella del boceto
(preparado/opciones_asas_boceto.md). La estrella es propia de OmniCAD (BOC-84, Fusion no la tiene): sus redondeos siguen
al «Fillet» de boceto de Fusion, que pide un valor de radio y dibuja la geometría resultante
(docs/fusion_docs/contenido/fusion-sketch/add-fillets-to-sketch-geometry-89d2b427f79.md); el radio que no entra se
achica en la misma proporción dejando recto el 10 % del lado, con aviso (B-496)."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

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


def _tecrear(sp, texto):
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


def _estrella(mb, radio=20.0, **valores):
    """Activa Estrella, teclea las opciones numéricas de la tarjeta y dibuja centro (0,0) y punta (0, radio)."""
    lz = mb.lienzo
    mb.acciones["sk_estrella"].trigger()
    for etiqueta, valor in valores.items():
        _tecrear(_spin(mb, etiqueta), valor)
    _clic(lz, 0, 0)
    _clic(lz, 0, radio)
    assert lz.resultado.ok
    return lz


def _curvas(lz, tipo):
    return [c for c in lz.b.curvas.values() if c.tipo == tipo and not c.construccion]


def _radio_arco(lz, arco):
    return math.dist(lz.b.coords(arco.inicio), lz.b.coords(arco.centro))


def _circulos(lz):
    return sorted((c for c in lz.b.curvas.values() if c.tipo == "circulo"), key=lambda c: -c.radio)


def test_interior_y_los_dos_redondeos_juntos_entran_con_lo_tecleado(boceto):
    lz = boceto.lienzo
    avisos = []
    lz.mensaje.connect(avisos.append)
    lz = _estrella(boceto, 20.0, **{"Interior (0 = regular)": "50", "Redondeo de puntas": "1,5",
                                    "Redondeo de valles": "0,75"})
    assert (lz.opciones["interior_estrella"], lz.opciones["redondeo_puntas"],
            lz.opciones["redondeo_valles"]) == (50.0, 1.5, 0.75)
    assert _circulos(lz)[1].radio == pytest.approx(10.0)                    # Interior: 50 % del radio exterior
    radios = sorted(_radio_arco(lz, a) for a in _curvas(lz, "arco"))
    assert radios == pytest.approx([0.75] * 5 + [1.5] * 5)                 # 5 valles + 5 puntas, tal cual lo tecleado
    assert not [t for t in avisos if "no entraba" in t]                     # entran: sin aviso de B-496


def test_redondeo_de_puntas_que_no_entra_se_achica_y_avisa(boceto):
    lz = boceto.lienzo
    avisos = []
    lz.mensaje.connect(avisos.append)
    _estrella(boceto, 20.0, **{"Redondeo de puntas": "50"})
    assert lz.opciones["redondeo_puntas"] == 50.0
    arcos = _curvas(lz, "arco")
    assert len(arcos) == 5 and len(_curvas(lz, "linea")) == 10             # achicado: no se comió las puntas
    r_in = _circulos(lz)[1].radio                                          # regular {5/2}: interior = 38,2 % del exterior
    lado = math.dist((20.0, 0.0), (r_in * math.cos(math.pi / 5), r_in * math.sin(math.pi / 5)))
    esperado = 0.9 * lado * math.tan(math.pi / 10)                         # B-496: recto el 10 % del lado (punta de 36°)
    assert esperado < 50.0 and all(_radio_arco(lz, a) == pytest.approx(esperado) for a in arcos)
    assert any("no entraba" in t and "puntas" in t for t in avisos)
