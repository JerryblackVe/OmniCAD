# -*- coding: utf-8 -*-
"""FL-1: toda previa que toca el kernel va al proceso aparte; con tres valores tecleados seguidos solo se ve el último,
y teclear la distancia de Extruir no rearma la base de sus asas."""
import math
import os
import time

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando, manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

# El trabajador tarda 0,8 s más en cada previa: los valores nuevos llegan mientras calcula el viejo. Lo carga el hijo por
# PYTHONPATH; este proceso ya arrancó y no lo ve.
LENTA = """
import time
from omnicad.nucleo import aislado

_previa = aislado._TAREAS_JSON["previa_visual"]

def _lenta(**args):
    time.sleep(0.8)
    return _previa(**args)

aislado._TAREAS_JSON["previa_visual"] = _lenta
"""


def _teclear(campo, texto):
    QTest.mouseClick(campo, Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)
    QTest.qWait(60)


def test_tres_valores_seguidos_solo_muestran_el_ultimo(tmp_path, monkeypatch):
    (tmp_path / "sitecustomize.py").write_text(LENTA, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, (str(tmp_path), os.environ.get("PYTHONPATH")))))
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"entities": [{"type": "rectangle", "corner1": [0, 0], "corner2": [20, 10]}]})["ok"]
    boceto = s.doc.operaciones[-1].id
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(Extruir())
        perfil = s.doc.estado_final.bocetos[boceto].perfiles[0]
        p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, p.ctx.estado))
        vistas, mostrar = [], p._previa_lista

        def anotar(estado):
            vistas.append((p._op_hijo if p._hijo_previa is not None else p.ultima_op).p["distancia"])
            mostrar(estado)

        monkeypatch.setattr(p, "_previa_lista", anotar)
        bases = []
        base_perfiles = mp.base_perfiles
        monkeypatch.setattr(mp, "base_perfiles", lambda *a: bases.append(1) or base_perfiles(*a))
        campo = p.widgets["distancia"]
        for texto in ("5", "10", "15"):
            _teclear(campo, texto)
        assert campo.text() == "15"             # el panel siguió tomando teclas mientras el trabajador calculaba
        limite = time.monotonic() + 60
        while (p._t_previa.isActive() or p._hijo_previa is not None) and time.monotonic() < limite:
            QTest.qWait(20)
        assert p._previa_ok, p.mensaje.text()
        assert vistas == ["15"], vistas         # ni el 5 que llegó tarde ni el 10 que nunca se calculó
        assert p._previa_aparte
        assert len(bases) <= 1                  # se arma una vez: la distancia no la rearma (350 ms por tecla con un texto)
        assert aislado.costo_reinicio() < math.inf   # ya contestó: se sabe lo que cuesta cortarlo
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_un_trabajador_que_todavia_no_contesto_no_se_corta(monkeypatch):
    """Cortar un trabajador que arranca no adelanta nada: el nuevo tarda lo mismo o más (texto «EMILIA»: 2,4 s y 5,6 s)."""
    monkeypatch.setattr(aislado, "_trabajador", None)
    assert aislado.costo_reinicio() == math.inf
