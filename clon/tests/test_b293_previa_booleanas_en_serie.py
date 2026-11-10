# -*- coding: utf-8 -*-
"""B-293: la previa de un comando, calculada dentro de la ventana, corre las booleanas EN SERIE. Con el paralelismo de
OpenCascade, sumar perfiles del llavero a una Extrusión cerraba la app en el perfil 12 (access violation en
`geometria._booleana`); en serie llega a los 17 y tarda lo mismo (medido con `perfil_ventana.py extruir`)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.api import selectores as sl  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture
def v(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ventana = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)))
    ventana.show()
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    ventana.set_documento(s.doc)
    ventana.sesion = s
    QTest.qWait(20)
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    ventana.doc.modificado = False
    ventana.close()
    ventana.deleteLater()
    QTest.qWait(1)


def test_la_previa_del_panel_corre_las_booleanas_en_serie(v, monkeypatch):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    paralelo = []
    original = v.doc.previsualizar
    monkeypatch.setattr(v.doc, "previsualizar", lambda *a, **k: (paralelo.append(geo.PARALELO), original(*a, **k))[1])
    antes = geo.PARALELO
    v.ejecutar_comando(CATALOGO["agujero"]())
    p = v.panel
    (c, e), = sl.elegir(v.sesion, ">Z", "cara", None)
    hit = hit_desde_ref(sl.referencia(c, e), v.doc.estado_final)
    hit["punto"] = (50.0, 30.0, 20.0)
    p._activar(next(x for x in p.campos if x.clave == "colocacion"))
    p._elegida(hit)
    QTest.qWait(50)

    assert p._previa_ok, p.mensaje.text()
    assert paralelo and not any(paralelo), paralelo     # cada previa del panel, sin paralelismo
    assert geo.PARALELO == antes                         # y al terminar vuelve como estaba
