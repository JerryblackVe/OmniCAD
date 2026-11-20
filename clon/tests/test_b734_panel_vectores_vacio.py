# -*- coding: utf-8 -*-
"""B-734: en la vista 3D, con un texto activo y sin selección, el panel «Objetos vectoriales y texto» no queda abierto vacío."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.restricciones import objetos as ob  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def test_panel_cerrado_sin_seleccion_y_abierto_con_ella(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "N", "plane": "XY"})
    api.llamar(s, "add_text", {"sketch": "N", "text": "Rochi", "x": 0, "y": 0, "height": 12})
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    QTest.qWait(300)
    try:
        lz = next(iter(v.vectores.capas.values()))
        v.vectores._activar(lz)
        v.vectores.seleccionar(lz.op_id, ob.raices(lz.b)[:1])
        QTest.qWait(50)
        assert lz.objetos.panel.isVisible()
        lz.seleccion = []
        lz._notificar_seleccion()
        v._refrescar_visibilidad()
        QTest.qWait(50)
        assert v.vectores.activo is lz and not lz.objetos.panel.isVisible()
    finally:
        v.doc.modificado = False
        v.close()
