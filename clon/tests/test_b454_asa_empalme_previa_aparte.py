# -*- coding: utf-8 -*-
"""B-454: con la previa en el proceso aparte (Windows: más de 30 ms), el asa del empalme arrastrada más allá del límite
frenaba en el radio con que se agarró («el asa frena en 1 mm») porque su bisección no probaba nada. El camino de
Gerardo: Boceto1 (rectángulo) → Extruir 113,23 → Empalme de la arista de arriba, arrastrando el asa."""
import time

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as g, referencias as refs
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.modificar import Empalme
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _esperar(p):
    limite = time.monotonic() + 60
    while (p._t_previa.isActive() or p._hijo_previa is not None) and time.monotonic() < limite:
        QTest.qWait(20)


def _raton(visor, tipo, q, boton, botones):
    q = QPointF(float(q[0]), float(q[1]))
    QApplication.sendEvent(visor, QMouseEvent(tipo, q, q, boton, botones, Qt.NoModifier))


def test_b454_el_asa_del_empalme_llega_al_limite_con_la_previa_aparte(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    monkeypatch.setattr(comando, "PREVIA_EN_VENTANA_MS", 1)     # como en Windows: toda previa del empalme va aparte
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [92.18, 51.84]}]})["ok"]
    boceto = s.doc.operaciones[-1].id
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        perfil = s.doc.estado_final.bocetos[boceto].perfiles[0]
        p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, p.ctx.estado))
        p.set_valor("distancia", "113.23 mm")
        _esperar(p)
        p.aceptar()
        limite = time.monotonic() + 60
        while not s.doc.estado_final.cuerpos and time.monotonic() < limite:
            QTest.qWait(20)
        cid, cuerpo = next(iter(s.doc.estado_final.cuerpos.items()))
        forma = cuerpo.forma
        arista = next(e for e in refs.subformas(forma, "arista")              # la de arriba, de 92,18 mm
                      if np.allclose(refs.firma_arista(e)["medio"], (46.09, 0, 113.23)))
        p = v.ejecutar_comando(Empalme())
        p._elegida(hit_desde_ref(refs.referencia(cid, arista, caja=g.caja_envolvente(forma)), p.ctx.estado))
        p.set_valor("radio", "1 mm")
        _esperar(p)
        assert p._previa_ok and p._previa_aparte, p.mensaje.text()
        gestor = p.manipuladores
        m = next(m for m in gestor.manips if m.ident == "flecha:radio")
        a, b = gestor.pantalla(m.puntos(gestor))[0]
        d = (b - a) / np.linalg.norm(b - a)
        desde = (a + b) / 2
        _raton(p.visor, QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
        # un tirón muy pasado del alto de 113,23 mm: la previa aparte falla sin ningún valor sano en el medio
        _raton(p.visor, QEvent.MouseMove, desde + d * 1600, Qt.NoButton, Qt.LeftButton)
        _esperar(p)                             # la previa (y el freno) vuelven antes de soltar
        _raton(p.visor, QEvent.MouseButtonRelease, desde + d * 1600, Qt.LeftButton, Qt.NoButton)
        _esperar(p)
        radio = p.ctx.evaluar(p.valores["radio"])
        # sin el arreglo: «el asa frena en 1 mm»; B-460: pasa del ancho de arriba (51,84) como en Fusion, no del alto
        assert 20 < radio < 113.23, (radio, p.mensaje.text())
        assert p._previa_ok and " máx. " in p.mensaje.text(), p.mensaje.text()
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
