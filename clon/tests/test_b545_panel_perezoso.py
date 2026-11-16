# -*- coding: utf-8 -*-
"""B-545 / B-546: el panel arma recién al mostrarse (o al pedirla) la fila de un campo oculto al abrir, con el Tab en el
orden de los campos; y Extruir reusa sus asas al reabrirse sobre el mismo estado."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QWidget

from omnicad import api
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.crear import Agujero
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    _llamar(s, "create_box", length=80, width=50, height=10)
    _llamar(s, "fillet", edges="all", radius=1)                                  # el cuerpo ya modificado
    _llamar(s, "create_sketch", plane="XY")
    _llamar(s, "draw_rectangle", x1=100, y1=0, x2=120, y2=20)
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    app.processEvents()


def _cadena(panel):
    """Los campos armados en el orden en que el Tab los recorre (solo lo que toma el foco)."""
    armados = {id(dict.__getitem__(panel.widgets, k)): k for k in list(dict.keys(panel.widgets))}
    orden, w = [], panel
    for _ in range(2000):
        w = w.nextInFocusChain()
        if w.focusPolicy() == Qt.NoFocus and w is not panel:
            continue                                                            # el Tab no se detiene ahí
        clave = next((armados[id(x)] for x in _ancestros(w) if id(x) in armados), None)
        if clave is not None and clave not in orden:
            orden.append(clave)
        if w is panel:
            break
    return orden


def _ancestros(w):
    while w is not None and isinstance(w, QWidget):
        yield w
        w = w.parentWidget()


def test_b545_agujero_arma_solo_lo_visible_y_lo_demas_al_pedirlo_con_el_tab_de_siempre(ventana, monkeypatch):
    from omnicad.ui import comando
    monkeypatch.setattr(comando, "_PEREZOSOS", ())
    p = ventana.ejecutar_comando(Agujero())                                     # todo armado al abrir, como antes
    antes = _cadena(p)
    p.cancelar()
    monkeypatch.undo()
    p = ventana.ejecutar_comando(Agujero())
    armados = set(dict.keys(p.widgets))
    assert len(armados) < len(p.campos) / 2 and set(p.widgets) == {c.clave for c in p.campos}   # el dict de siempre
    oculto = next(c.clave for c in p.campos if c.clave in p._pendientes)
    w = p.widgets[oculto]                                                       # pedirla la arma, oculta
    assert w is p.widgets.get(oculto) and not w.isVisible() and oculto not in p._pendientes
    assert p.etiquetas[oculto].campo_w is w                                     # B-548: su rótulo también enfoca
    p.widgets.values()                                                          # todas armadas
    assert _cadena(p) == antes                                                  # el Tab de siempre
    p.cancelar()


def _abrir_extruir(ventana):
    perfil = ventana.doc.estado_final.bocetos["op3"].perfiles[0]
    ventana.seleccion = [hit_desde_ref({"tipo": "perfil", "boceto": "op3", **OpExtrusion.referencia_perfil(perfil)},
                                       ventana.doc.estado_final)]               # elegido antes, como lo usa la gente
    p = ventana.ejecutar_comando(Extruir())
    p.set_valor("distancia", "5 mm")
    p.cancelar()


def test_b546_extruir_reabre_sin_rearmar_las_asas_y_las_rearma_si_cambia_el_estado(ventana, monkeypatch):
    llamadas, base = [], mp.base_perfiles
    monkeypatch.setattr(mp, "base_perfiles", lambda *a, **k: llamadas.append(1) or base(*a, **k))
    monkeypatch.setattr(Extruir, "_base_asas", None)
    _abrir_extruir(ventana)
    _abrir_extruir(ventana)
    assert len(llamadas) == 1                                                  # al reabrir, las mismas asas
    _llamar(api.Sesion(ventana.doc), "create_box", length=5, width=5, height=5, x=-50)    # otro estado
    _abrir_extruir(ventana)
    assert len(llamadas) == 2
