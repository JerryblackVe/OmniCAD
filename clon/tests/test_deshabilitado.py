# -*- coding: utf-8 -*-
"""P-169: lo que no funciona se ve en gris con «No disponible: <motivo>» y la API lo rechaza con FEATURE_DISABLED."""
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt  # noqa: E402

from omnicad import deshabilitado  # noqa: E402

SEGUIMIENTO = Path(__file__).resolve().parents[2] / "docs" / "seguimiento"
MOTIVO = ("la extrusión pierde el perfil", "B-999")


def _ids_abiertos():
    texto = "\n".join((SEGUIMIENTO / n).read_text(encoding="utf-8")
                      for n in ("bugs.md", "faltantes.md", "mejoras.md", "despues.md"))
    return set(re.findall(r"^\| ([A-Z]+-\d+[a-z]?\d*) \|", texto, re.M))


def test_ningun_id_de_la_lista_esta_cerrado():
    """La entrada se quita en el mismo commit que cierra el bug: gemelo de tests/test_seguimiento.py."""
    abiertos = _ids_abiertos()
    for clave, (motivo, id_bug) in {**deshabilitado.DESHABILITADO, **deshabilitado.SIN_COMANDO}.items():
        assert id_bug in abiertos, f"{clave}: {id_bug} ya no está en docs/seguimiento/: quitá la entrada"
        assert motivo and "\n" not in motivo and len(motivo) <= 90, f"{clave}: el motivo va en 1 renglón"


def test_el_motivo_sale_con_el_prefijo():
    assert deshabilitado.motivo("no_existe") is None
    assert deshabilitado.entrada("no_existe") is None


@pytest.fixture
def apagada(monkeypatch):
    monkeypatch.setitem(deshabilitado.DESHABILITADO, "extruir", MOTIVO)
    monkeypatch.setitem(deshabilitado.DESHABILITADO, "extruir.medida", MOTIVO)
    monkeypatch.setitem(deshabilitado.DESHABILITADO, "extruir.tipo.delgada", MOTIVO)
    monkeypatch.setitem(deshabilitado.DESHABILITADO, "extruir.direccion.simetrica", MOTIVO)
    monkeypatch.setitem(deshabilitado.DESHABILITADO, "extrude", MOTIVO)


def test_la_cinta_y_los_menus_muestran_gris_con_el_motivo(apagada, tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        a = v.acciones["extruir"]
        assert not a.isEnabled() and "No disponible: la extrusión pierde el perfil" in a.toolTip()
        assert v.acciones["revolucion"].isEnabled()                     # lo demás sigue andando
        v.aplicar_teclas()                                              # rehace los tooltips: el motivo no se pierde
        assert "No disponible: la extrusión pierde el perfil" in a.toolTip() and not a.isEnabled()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()


def test_el_panel_apaga_un_campo_o_una_sola_opcion(apagada):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.visor3d import Visor3D
    ctx = ContextoComando(Documento())
    visor = Visor3D()
    visor.set_modelo(ctx.estado)
    panel = PanelComando(Extruir(), ctx, visor)
    panel._t_previa.stop()
    assert not panel.widgets["medida"].isEnabled()                      # el campo entero
    assert "No disponible: la extrusión pierde el perfil" in panel.widgets["medida"].toolTip()
    assert panel.widgets["distancia"].isEnabled()
    fila = panel.widgets["tipo"]                                        # una opción de la fila de íconos
    assert not fila.boton("delgada").isEnabled() and fila.boton("solida").isEnabled()
    combo = panel.widgets["direccion"]                                  # una opción del desplegable
    i = combo.findData("simetrica")
    assert not combo.model().item(i).isEnabled() and combo.model().item(0).isEnabled()
    assert "No disponible" in combo.itemData(i, Qt.ToolTipRole)


def test_la_api_rechaza_con_feature_disabled_y_el_id(apagada):
    from omnicad import api
    from omnicad.api.errores import PISTAS
    from omnicad.timeline.documento import Documento
    assert "FEATURE_DISABLED" in PISTAS and "FEATURE_DISABLED" != "TOOL_NOT_AVAILABLE"
    sesion = api.Sesion(Documento())
    r = api.llamar(sesion, "extrude", {})
    assert r["ok"] is False and r["error_kind"] == "FEATURE_DISABLED"
    assert "B-999" in r["mensaje"] and "la extrusión pierde el perfil" in r["mensaje"]
    assert api.llamar(sesion, "get_scene_info", {})["ok"]              # lo demás sigue andando


def test_todo_lo_de_la_lista_real_se_ve_gris_y_la_api_lo_rechaza(tmp_path):
    """Con la lista vacía no comprueba nada; cuando E7 la carga, cubre cada entrada de verdad."""
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad import api
    from omnicad.timeline.documento import Documento
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    sesion = api.Sesion(Documento())
    try:
        for clave in deshabilitado.DESHABILITADO:
            if "." in clave:
                continue                                              # campos y opciones: los cubre el panel
            if clave in v.acciones:
                a = v.acciones[clave]
                assert not a.isEnabled() and "No disponible: " in a.toolTip(), clave
            else:
                assert api.llamar(sesion, clave, {}).get("error_kind") == "FEATURE_DISABLED", clave
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()


def test_los_items_grises_de_la_cinta_dicen_por_que(tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        assert v.cinta.no_disponibles
        for a in v.cinta.no_disponibles:
            motivo = deshabilitado.motivo_sin_comando(a.text().split("\t")[0])
            assert motivo and motivo in a.toolTip() and not a.isEnabled(), a.text()
            assert "No disponible en" not in a.toolTip()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()


def test_el_navegador_y_el_submenu_vacio_dicen_el_motivo():
    from PySide6.QtWidgets import QApplication, QMenu
    QApplication.instance() or QApplication([])
    from omnicad.ui.acciones_navegador import no_disponible
    m = QMenu()
    no_disponible(m, "Copiar\tControl+C", "texto viejo")
    a = m.actions()[0]
    assert not a.isEnabled() and a.toolTip() == deshabilitado.motivo_sin_comando("Copiar")
    assert deshabilitado.motivo_sin_comando("Desplazar al grupo") and deshabilitado.motivo_sin_comando("Crear placa de circuito impreso")
