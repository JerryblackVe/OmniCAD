# -*- coding: utf-8 -*-
"""B-310 (resto): Gerardo vio que la previa del desfase +0,1 mm del cilindro Ø31 de su pieza movía solo algunas franjas.
Guardia con el caso rearmado (el estado de su error no se guardó): un cilindro Ø31 partido en 5 franjas por planos."""
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, referencias as refs
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.modificar import CaraDesfase
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def test_la_previa_mueve_todas_las_franjas_del_cilindro(tmp_path):
    s = api.Sesion()
    _llamar(s, "create_cylinder", height=15, radius=15.5, name="Buje")
    cid = next(iter(s.doc.estado_final.cuerpos))
    for z in (3, 6, 9, 12):
        _llamar(s, "create_construction_plane", plane="XY", offset=z, name=f"P{z}")
        _llamar(s, "split_face", faces="%CYLINDER", body=cid, tool=f"P{z}")
    franjas = [c for c in geo.caras(s.doc.estado_final.cuerpos[cid].forma) if refs.firma_cara(c)["geom"] == "cilindro"]
    assert len(franjas) == 5
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(CaraDesfase())
        p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": cid, "firma": refs.firma_cara(franjas[2])}, p.ctx.estado))
        p.set_valor("distancia", "0,1 mm")                     # como lo tecleó Gerardo
        p._t_previa.stop()
        p._calcular_previa()
        assert p._previa_ok and not p._previa_aparte
        malla = next(m for m in v.visor._mallas if m["id"] == cid)
        pts = np.asarray(malla["v"], float)
        lateral = pts[(pts[:, 2] > 1e-3) & (pts[:, 2] < 15 - 1e-3)]       # sin las tapas
        assert np.hypot(lateral[:, 0], lateral[:, 1]) == pytest.approx(15.6, abs=1e-4)
        p.cancelar()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
