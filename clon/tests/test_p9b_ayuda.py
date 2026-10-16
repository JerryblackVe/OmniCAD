# -*- coding: utf-8 -*-
"""P9 (segunda tanda): el globo de ayuda de los comandos principales trae su imagen «antes → después»
(`scripts/ayuda_imagenes.py` las genera con el propio núcleo) y Ctrl+/ la muestra."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QUrl  # noqa: E402
from PySide6.QtGui import QImage, QTextDocument  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import RECURSOS  # noqa: E402

PRINCIPALES = ("extruir", "revolucion", "empalme_3d", "chaflan_3d", "vaciado", "agujero", "patron_rectangular_3d",
               "simetria_3d")


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path_factory.mktemp("prefs") / "p.ini"),
                                                      QSettings.IniFormat)))
    v.show()
    QTest.qWait(50)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def test_cada_comando_principal_tiene_su_imagen_y_es_una_imagen_de_verdad():
    for clave in PRINCIPALES:
        img = QImage(str(RECURSOS / "ayuda" / f"{clave}.png"))
        assert not img.isNull() and img.height() == 150 and img.width() in (200, 436), clave


def test_el_globo_de_los_comandos_principales_lleva_la_imagen(ventana):
    for clave in PRINCIPALES:
        tip = ventana.acciones[clave].toolTip()
        assert f"{clave}.png" in tip and tip.index("<img") < tip.index("Ctrl+/"), clave
        doc = QTextDocument()
        doc.setHtml(tip)
        sin = QTextDocument()
        sin.setHtml(tip.replace(tip[tip.index("<br><img"):tip.index("<br><br>")], ""))
        assert doc.size().height() - sin.size().height() > 140, f"{clave}: la imagen no ocupa lugar en el globo"


def test_un_comando_sin_imagen_conserva_su_globo_de_siempre(ventana):
    tip = ventana.acciones["boceto"].toolTip()
    assert "<img" not in tip and "Ctrl+/" in tip


def test_ctrl_barra_muestra_la_imagen(ventana):
    caja = ventana.ayuda_comando(ventana.acciones["vaciado"])
    assert "vaciado.png" in caja.text() and QUrl.fromLocalFile(str(RECURSOS / "ayuda" / "vaciado.png")).isValid()
    caja.close()
