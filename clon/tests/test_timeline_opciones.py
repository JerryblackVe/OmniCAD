# -*- coding: utf-8 -*-
"""FU-7: engranaje del timeline (Opciones de Fusion). «Muestra de color por componente»: el color de cada paso sigue a
su componente, la casilla se guarda en las preferencias (clave timeline/color_componente) y se maneja también con
get_preferences / set_preference."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.ui.panel_timeline import PALETA_COMPONENTES, PanelTimeline, colores_por_componente  # noqa: E402

CLAVE = "timeline/color_componente"


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def _sesion_con_dos_componentes():
    s = api.Sesion()
    ids = []
    for nombre, x in (("Base", 0), ("Bloque", 100)):
        caja = api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "x": x})["result"]
        ids.append(caja["bodies_created"][0]["id"])
    for cuerpo, nombre in zip(ids, ("Base", "Bloque"), strict=True):
        assert api.llamar(s, "create_component", {"bodies": [cuerpo], "name": nombre})["ok"]
    api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "x": 300})        # suelto: sin componente
    return s


def test_colores_por_componente_siguen_al_componente():
    doc = _sesion_con_dos_componentes().doc
    colores = colores_por_componente(doc)
    assert colores["op3"] == PALETA_COMPONENTES[0] and colores["op4"] == PALETA_COMPONENTES[1]    # los pasos Componente
    assert "op1" in colores and "op2" in colores                       # las cajas ya dentro de un componente
    assert "op5" not in colores                                        # la caja suelta no lleva color


def test_engranaje_pinta_los_pasos_y_avisa(app_qt):
    doc = _sesion_con_dos_componentes().doc
    t = PanelTimeline()
    avisos = []
    t.color_componente_cambiado.connect(avisos.append)
    t.actualizar(doc)
    fondos = lambda: [t.lista.item(i).background().color().name() for i in range(t.lista.count())]   # noqa: E731
    sin_color = fondos()
    assert not t.accion_color.isChecked() and t.engranaje.menu().actions() == [t.accion_color]
    t.accion_color.trigger()                                           # como un clic en la casilla del engranaje
    assert avisos == [True] and t.accion_color.isChecked()
    pintado = fondos()
    assert pintado != sin_color
    assert PALETA_COMPONENTES[0].name() in pintado and PALETA_COMPONENTES[1].name() in pintado
    t.poner_color_componente(False)                                    # apagar vuelve al fondo de antes
    assert avisos == [True, False] and fondos() == sin_color


def test_el_estado_de_error_manda_sobre_el_color_del_componente(app_qt):
    from omnicad.ui.panel_timeline import COLORES
    doc = _sesion_con_dos_componentes().doc
    doc.suprimir("op5", True)
    t = PanelTimeline()
    t.poner_color_componente(True)
    t.actualizar(doc)
    assert all(t.lista.item(i).background().color() != COLORES["error"] for i in range(t.lista.count()))


def test_preferencia_por_defecto_guardada_y_herramienta(tmp_path, monkeypatch):
    from omnicad.ui.preferencias import DEFECTOS, Preferencias
    ini = str(tmp_path / "prefs.ini")
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", ini)
    prefs = Preferencias(QSettings(ini, QSettings.IniFormat))
    assert DEFECTOS[CLAVE] is False and prefs[CLAVE] is False
    s = api.Sesion()
    fila = api.llamar(s, "get_preferences", {"keys": [CLAVE]})["result"]["preferences"][0]
    assert fila["value"] is False and fila["options"] == [False, True]
    assert api.llamar(s, "set_preference", {"key": CLAVE, "value": True})["ok"]
    prefs.q.sync()
    assert prefs[CLAVE] is True                                        # la ventana lee lo que guardó la herramienta
    assert not api.llamar(s, "set_preference", {"key": CLAVE, "value": "si"})["ok"]


def test_la_ventana_guarda_y_restaura_la_casilla(app_qt, tmp_path):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = str(tmp_path / "ventana.ini")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(ruta, QSettings.IniFormat)))
    try:
        assert not v.timeline.color_componente
        v.timeline.accion_color.trigger()
        assert v.prefs[CLAVE] is True
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
    v2 = VentanaPrincipal(prefs=Preferencias(QSettings(ruta, QSettings.IniFormat)))
    try:
        assert v2.timeline.color_componente and v2.timeline.accion_color.isChecked()
    finally:
        v2.doc.modificado = False
        v2.close()
        v2.deleteLater()
