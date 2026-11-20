# -*- coding: utf-8 -*-
"""B-445: con una cara de cuerpo bajo el cursor, el clic elige la cara y no el plano de origen que queda adelante
(como Fusion); el plano se elige solo por su borde o donde no hay cuerpo."""
import numpy as np
import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def visor(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    # caja de 30 mm completa del lado +Y del plano XZ; boceto en XZ extruido hacia +Y
    r = api.llamar(s, "sketch_from_spec", {"plane": "XZ", "entities": [
        {"type": "rectangle", "corner1": [-15, -15], "corner2": [15, 15]}]})
    assert r["ok"], r
    sk = s.doc.operaciones[-1].id
    # dos cajas, una a cada lado del plano XZ (y 10..40 y y -40..-10): a una la tapa el plano según de dónde se mire
    for dist, desfase in ((30, 10), (-30, -10)):
        r = api.llamar(s, "extrude", {"sketch": sk, "profile": 0, "distance": dist, "start": "offset",
                                      "start_offset": desfase, "operation": "new_body"})
        assert r["ok"], r
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(150)
    v.visor.encuadrar()
    QTest.qWait(100)
    yield v.visor
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _pos(vis, p):
    q, ok = vis._a_pantalla(np.array([p], float), vis.matriz_mvp())
    assert ok[0]
    return QPointF(*q[0])


def test_la_cara_gana_al_plano_de_origen(visor):
    vis = visor
    vis.filtro = {"cara", "cara_plana", "plano"}
    vis.modo = "elegir_plano"
    o, _d = vis.rayo(_pos(vis, [0.0, 0.0, 0.0]))
    cerca = 10.0 if o[1] < 0 else -10.0            # la caja que queda detrás del plano XZ vista desde la cámara
    # B-762: (-12, -12) queda fuera del cuadro XZ (de 0 a 0,4 de la pieza): ahí la cara gana; dentro del cuadro gana el plano
    hit = vis.elegir_entidad(_pos(vis, [-12.0, cerca, -12.0]), vis.filtro)
    assert hit is not None and hit["tipo"] == "cara", hit and hit["ref"]
    # el borde del plano se sigue eligiendo aunque haya una caja detrás
    pl, (_u0, _v0, u1, v1) = next((p, r) for ref, p, r in vis.planos_elegibles() if ref == "XZ")    # B-610: el borde real
    fuera = vis.elegir_entidad(_pos(vis, pl.a_3d(u1, v1 * 0.5)), vis.filtro)
    assert fuera is not None and fuera["tipo"] == "plano"
