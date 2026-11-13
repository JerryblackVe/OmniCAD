# -*- coding: utf-8 -*-
"""FU-5: como en Fusion («a sketch profile is shaded blue when it is closed»), dibujar un rectángulo con el ratón deja el
perfil cerrado relleno de azul en el visor; mientras se estira el relleno todavía no está."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def test_el_rectangulo_dibujado_con_el_raton_rellena_su_perfil(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad import api
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "S", "plane": "XY"})["ok"]
    prefs = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(s.doc, prefs=prefs)
    v.resize(1500, 900)
    v.show()
    QTest.qWait(500)
    try:
        v.editar_operacion(s.paso("S").id)
        QTest.qWait(600)
        lz = v.modo_boceto.lienzo
        lz.visor.objetivo = lz.plano.a_3d(30, 20)
        lz.visor.distancia = 200
        px = lambda x, y: lz.a_px(x, y).toPoint()  # noqa: E731
        v.modo_boceto.acciones["sk_rectangulo"].trigger()
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(0, 0))
        q = QPointF(px(60, 40))
        QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, q, lz.mapToGlobal(q), Qt.NoButton, Qt.NoButton,
                                               Qt.NoModifier))
        QTest.qWait(150)
        assert len(v.visor._perfiles) == 0                      # estirando: todavía no hay perfil cerrado
        QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, px(60, 40))
        QTest.qWait(1200)
        assert len(lz.b.curvas) == 4 and len(v.visor._perfiles) == 6      # cerrado: 2 triángulos con 3 vértices
    finally:
        v.modo_boceto.terminar()
        v.doc.modificado = False
        v._confirmar_descartar = lambda *a, **k: True        # cerrar sin preguntar
        v.close()
