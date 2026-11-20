# -*- coding: utf-8 -*-
"""P-165: atajos de teclado en Preferencias y por MCP/CLI (equivale a «Change Keyboard Shortcut» de Fusion)."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import atajos as at  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ajustes(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "a.ini"))
    return QSettings(str(tmp_path / "a.ini"), QSettings.IniFormat)


def _llamar(herramienta, **args):
    r = api.llamar(api.Sesion(), herramienta, args)
    return {**r, **r.get("result", {})}


def test_normalizar_coincide_con_qt_en_las_combinaciones_de_fabrica():
    for _clave, (_titulo, defecto) in at.CATALOGO.items():
        if defecto:
            assert at.normalizar(defecto) == QKeySequence(defecto).toString(QKeySequence.PortableText), defecto
    assert at.normalizar("control+foo+s") is None and at.normalizar("Control+Shift+s") == "Ctrl+Shift+S"
    assert at.normalizar("") == "" and at.normalizar("Ctrl+") is None and at.normalizar("Ctrl+Ctrl+A") is None


def test_el_catalogo_de_atajos_esta_al_dia(qapp):
    ruta = Path(__file__).resolve().parents[2] / "scripts" / "claves_atajos.py"
    espec = importlib.util.spec_from_file_location("claves_atajos_script", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    assert (modulo.DESTINO.read_text(encoding="utf-8") == modulo.contenido()), \
        "Falta regenerar: clon/.venv/bin/python scripts/claves_atajos.py"


def test_set_shortcut_cambia_quita_y_rechaza_el_choque(ajustes):
    r = _llamar("set_shortcut", command="vaciado", keys="control+alt+v")
    assert r["ok"] and r["current"] == "Ctrl+Alt+V"
    assert json.loads(ajustes.value("atajos/teclas")) == {"vaciado": "Ctrl+Alt+V"}
    choque = _llamar("set_shortcut", command="medir", keys="Ctrl+Alt+V")           # ya la usa Vaciado
    assert not choque["ok"] and choque["error_kind"] == "SHORTCUT_CONFLICT" and choque["pistas"]
    assert not _llamar("set_shortcut", command="medir", keys="Ctrl+")["ok"]
    assert _llamar("set_shortcut", command="no_existe", keys="F5")["error_kind"] == "INVALID_ARGUMENTS"
    # la tecla de fábrica de otro comando también choca; quitársela libera la tecla
    assert _llamar("set_shortcut", command="vaciado", keys="E")["error_kind"] == "SHORTCUT_CONFLICT"
    assert _llamar("set_shortcut", command="extruir", keys="")["ok"]
    assert _llamar("set_shortcut", command="vaciado", keys="E")["ok"]
    filas = {f["command"]: f for f in _llamar("list_shortcuts", only_changed=True)["shortcuts"]}
    assert set(filas) == {"extruir", "vaciado"} and filas["extruir"]["current"] == "" and filas["vaciado"]["default"] != "E"


def test_reset_shortcuts_vuelve_a_fabrica(ajustes):
    _llamar("set_shortcut", command="vaciado", keys="Ctrl+Alt+V")
    _llamar("set_shortcut", command="medir", keys="Ctrl+Alt+M")
    assert _llamar("reset_shortcuts", command="vaciado")["changed"] == 1
    assert json.loads(ajustes.value("atajos/teclas")) == {"medir": "Ctrl+Alt+M"}
    assert _llamar("reset_shortcuts")["changed"] == 0 and json.loads(ajustes.value("atajos/teclas")) == {}
    assert _llamar("list_shortcuts", query="extruir")["shortcuts"][0]["current"] == "E"


def test_la_pagina_marca_el_choque_en_rojo_y_no_deja_aplicar(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)      # el aviso modal de «campos en rojo»
    from omnicad.ui.preferencias import DialogoPreferencias, Preferencias
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    dlg = DialogoPreferencias(prefs, inicial="atajos")
    dlg.show()
    QTest.qWait(1)
    pagina = dlg.controles["atajos/teclas"]
    pagina.buscar.setText("extruir")
    assert not pagina.items["extruir"].isHidden() and pagina.items["medir"].isHidden()
    pagina.arbol.setCurrentItem(pagina.items["medir"])
    pagina.editor.setKeySequence(QKeySequence("E"))                       # la de Extruir
    assert not pagina.valido() and "Extruir" in pagina.aviso.text()
    assert pagina.items["medir"].foreground(1).color() == pagina.items["extruir"].foreground(1).color() != \
        pagina.items["abrir"].foreground(1).color()
    assert pagina.items["medir"].toolTip(1) and not dlg._aplicar()          # hay un choque: no guarda nada
    assert json.loads(prefs["atajos/teclas"]) == {}
    pagina.b_quitar.click()                                               # Medir sin atajo: se resuelve
    assert pagina.valido() and "ya la usa" not in pagina.aviso.text()
    dlg.b_aplicar.setEnabled(True)
    assert dlg._aplicar() and json.loads(prefs["atajos/teclas"]) == {"medir": ""}
    dlg.reject()
    dlg.deleteLater()


def test_aplicar_cambia_el_atajo_de_la_ventana(qapp, tmp_path):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.prefs["atajos/teclas"] = json.dumps({"vaciado": "Ctrl+Alt+V"})
        v.aplicar_teclas()
        assert v.acciones["vaciado"].shortcut() == QKeySequence("Ctrl+Alt+V")
    finally:
        v.doc.modificado = False
        v.close()


def test_p189_las_herramientas_del_boceto_estan_y_chocan_solo_entre_ellas():
    from omnicad.api import atajos as at
    assert "sk_linea" in at.CATALOGO and at.contexto("sk_linea") == "boceto" and at.contexto("extruir") == "diseno"
    efectivo = at.efectivos({})
    efectivo["sk_linea"] = efectivo["extruir"] = "Ctrl+Alt+9"            # boceto y diseño: no chocan (el boceto tapa al de la ventana)
    assert at.choques(efectivo) == {}
    efectivo["sk_circulo"] = "Ctrl+Alt+9"                                  # dos del boceto: sí
    assert at.choques(efectivo) == {"sk_linea": ["sk_circulo"], "sk_circulo": ["sk_linea"]}


def test_p189_set_shortcut_cambia_una_del_boceto_y_no_choca_con_una_de_diseno(ajustes):
    r = _llamar("set_shortcut", command="sk_linea", keys="Ctrl+Alt+V")
    assert r["ok"] and r["result"]["current"] == "Ctrl+Alt+V"
    assert _llamar("set_shortcut", command="vaciado", keys="Ctrl+Alt+V")["ok"]       # otro contexto
    assert not _llamar("set_shortcut", command="sk_circulo", keys="Ctrl+Alt+V")["ok"]
