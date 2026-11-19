"""B-664: si algo le saca el foco a la caja de la cota recién ubicada, la caja lo recupera y se puede teclear sin otro clic."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt
_cerrar_lienzos = T._cerrar_lienzos


def test_la_caja_de_la_cota_nueva_recupera_el_foco(app_qt):
    lz = T._lienzo(app_qt, Boceto())
    lz.activateWindow()
    lz._abrir_entrada(["Distancia"], ["20"], lz.rect().center(), lambda v: True)
    lz.setFocus()                                   # lo que hacía el lienzo justo después de abrir la caja
    QTest.qWait(30)
    assert lz.entrada.campos[0].hasFocus()
    QTest.keyClicks(lz.entrada.campos[0], "5")
    assert lz.entrada.campos[0].text() == "5"       # lo seleccionado se reemplaza
