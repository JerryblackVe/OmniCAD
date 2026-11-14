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


def test_lo_que_tarda_en_dibujarse_cuenta_para_volver_aparte(tmp_path, monkeypatch):
    """FL-1b: el barrido tarda 20 ms en el kernel y 0,4 s en mallarse en el visor; medir solo el kernel lo dejaba en la
    ventana y la trababa medio segundo por tecla."""
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
        p.set_valor("distancia", "5 mm")
        p._t_previa.stop()
        op = p.comando.construir(p.valores, p.ctx)
        p._ms_previa = comando._firma_previa(op), 1.0          # la última fue rápida: esta va en la ventana
        assert not p._previa_pesada(op)
        mostrar = p._previa_lista
        monkeypatch.setattr(p, "_previa_lista", lambda estado: time.sleep(0.06) or mostrar(estado))   # mallar tarda
        p._calcular_previa()
        assert p._previa_ok and not p._previa_aparte
        assert p._ms_previa[1] >= 60 and p._previa_pesada(op)    # la próxima vuelve al proceso aparte
        p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_la_caja_de_la_previa_aparte_sale_de_su_malla_sin_el_kernel(monkeypatch):
    """FL-1b: la caja exacta de un barrido con guía tardaba 0,15 s por previa solo para descartar cuerpos lejanos."""
    from types import SimpleNamespace

    import numpy as np

    from omnicad.nucleo import geometria as geo
    from omnicad.ui.comandos.comunes import caja_nueva
    malla = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    estado = SimpleNamespace(_mallas_previa={"c1": (malla, None, None)})
    monkeypatch.setattr(geo, "caja_envolvente", lambda forma: (_ for _ in ()).throw(AssertionError("usó el kernel")))
    assert caja_nueva(estado, "c1", object()) == ((-1.0, -1.0, -1.0), (2.0, 3.0, 4.0))
    monkeypatch.setattr(geo, "caja_envolvente", lambda forma: "exacta")
    assert caja_nueva(SimpleNamespace(), "c1", object()) == "exacta"      # previa de la ventana: la exacta
