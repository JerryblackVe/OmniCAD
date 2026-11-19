"""B-671: recién ubicada una cota, lo tecleado reemplaza el valor (Fusion lo deja seleccionado), no se agrega."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest  # noqa: E402

import test_boceto_interaccion as T  # noqa: E402
from omnicad.restricciones.boceto import Boceto  # noqa: E402

app_qt = T.app_qt


def test_lo_escrito_reemplaza_el_valor_recien_ubicada_la_cota(app_qt):
    lz = T._lienzo(app_qt, Boceto())
    lz.b.agregar_circulo((0, 0), 30.996)
    lz.set_herramienta("cota")
    T._clic(lz, 0, 30.996)                          # el círculo: caja con el Ø medido (61.992)
    assert lz.entrada is not None and lz.entrada.campos[0].text() == "61.992"
    T._clic(lz, 30, 30)                             # el clic que la ubica (B-439): la caja conserva lo escrito
    QTest.qWait(30)                                 # _tomar_foco (B-664) corre aparte
    QTest.keyClicks(lz.entrada.campos[0], "33")
    assert lz.entrada.campos[0].text() == "33"      # el valor estaba seleccionado: se reemplaza
