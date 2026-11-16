# -*- coding: utf-8 -*-
"""P-164: cinta personalizable (cuántos botones por sección, su orden y la sección FAVORITAS), en Preferencias y por MCP/CLI."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import cinta_personal as cp  # noqa: E402


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


def test_el_catalogo_de_la_cinta_esta_al_dia(qapp):
    ruta = Path(__file__).resolve().parents[2] / "scripts" / "claves_cinta.py"
    espec = importlib.util.spec_from_file_location("claves_cinta_script", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    assert modulo.DESTINO.read_text(encoding="utf-8") == modulo.contenido(), \
        "Falta regenerar: clon/.venv/bin/python scripts/claves_cinta.py"


def test_todo_boton_de_fabrica_es_un_comando_conocido():
    assert {c for v in cp.SECCIONES.values() for c in v} <= set(cp.COMANDOS)


def test_leer_ignora_lo_ajeno_los_repetidos_y_el_exceso():
    datos = {"SÓLIDO/CREAR": ["medir", "medir", "no_existe", 3] + ["extruir"] * 2, "NO/EXISTE": ["medir"], "SÓLIDO/MODIFICAR": "x"}
    assert cp.leer(json.dumps(datos)) == {"SÓLIDO/CREAR": ["medir", "extruir"]}
    assert cp.leer("no es json") == {} and cp.leer("[1]") == {}
    muchos = list(cp.COMANDOS)[:cp.MAXIMO + 3]
    assert len(cp.leer(json.dumps({"SÓLIDO/CREAR": muchos}))["SÓLIDO/CREAR"]) == cp.MAXIMO


def test_herramientas_get_set_y_reset(ajustes):
    r = _llamar("get_ribbon", tab="SÓLIDO")
    crear = next(s for s in r["sections"] if s["section"] == "SÓLIDO/CREAR")
    assert crear["tools"][0]["command"] == "extruir" and not crear["changed"] and r["max_tools"] == cp.MAXIMO
    assert _llamar("set_ribbon_section", section="SÓLIDO/CREAR", tools=["medir", "extruir"])["ok"]
    assert json.loads(ajustes.value("cinta/personal")) == {"SÓLIDO/CREAR": ["medir", "extruir"]}
    assert _llamar("set_ribbon_section", section="SÓLIDO/FAVORITAS", tools=["vaciado"])["ok"]
    for malo in ({"section": "SÓLIDO/NO", "tools": []}, {"section": "SÓLIDO/CREAR", "tools": ["nada"]},
                 {"section": "SÓLIDO/CREAR", "tools": ["medir", "medir"]},
                 {"section": "SÓLIDO/CREAR", "tools": list(cp.COMANDOS)[:cp.MAXIMO + 1]}):
        assert _llamar("set_ribbon_section", **malo)["error_kind"] == "INVALID_ARGUMENTS", malo
    assert _llamar("reset_ribbon", section="SÓLIDO/CREAR")["changed"] == 1
    assert json.loads(ajustes.value("cinta/personal")) == {"SÓLIDO/FAVORITAS": ["vaciado"]}
    assert _llamar("reset_ribbon")["changed"] == 0
    assert _llamar("reset_ribbon", section="SÓLIDO/NO")["error_kind"] == "INVALID_ARGUMENTS"


def _botones(cinta, pestana, titulo_grupo=None):
    pagina = cinta.pila.widget([n for n, _ in cinta._paginas].index(pestana))
    return [b.defaultAction().property("clave") for b in pagina.findChildren(QToolButton, "boton_cinta")]


def test_la_cinta_toma_los_botones_elegidos_y_la_seccion_favoritas(qapp, tmp_path):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        antes = _botones(v.cinta, "SÓLIDO")
        assert antes[:5] == ["extruir", "revolucion", "agujero", "patron_rectangular_3d", "boceto"]
        v.prefs["cinta/personal"] = json.dumps({"SÓLIDO/CREAR": ["boceto", "extruir"], "SÓLIDO/FAVORITAS": ["medir", "vaciado"]})
        v.aplicar_preferencias()
        despues = _botones(v.cinta, "SÓLIDO")
        assert despues[:4] == ["medir", "vaciado", "boceto", "extruir"]       # FAVORITAS primero, luego CREAR reordenada
        assert len(despues) == len(antes) - 3 + 2                              # CREAR pasó de 5 a 2 botones; +2 favoritas
        v.prefs["cinta/personal"] = "{}"
        v.aplicar_preferencias()
        assert _botones(v.cinta, "SÓLIDO") == antes                            # de fábrica: vuelve y FAVORITAS desaparece
    finally:
        v.doc.modificado = False
        v.close()


class _Soltar:
    """Evento de soltar con origen (QDropEvent no deja fabricar el origen: lo da el arrastre real)."""
    def __init__(self, origen, punto):
        self._origen, self._punto, self.accion, self.aceptado = origen, punto, None, False

    def source(self):
        return self._origen

    def position(self):
        return QPointF(self._punto)

    def setDropAction(self, a):
        self.accion = a

    def accept(self):
        self.aceptado = True


def test_la_pagina_arrastra_reordena_agrega_y_limita(qapp, tmp_path, monkeypatch):
    from omnicad.ui.preferencias import DialogoPreferencias, Preferencias
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    prefs = Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    dlg = DialogoPreferencias(prefs, inicial="cinta")
    dlg.show()
    pagina = dlg.controles["cinta/personal"]
    pagina.seccion.setCurrentIndex(pagina.seccion.findData("SÓLIDO/FAVORITAS"))
    assert pagina.tira.count() == 0 and "Sin botones" in pagina.aviso.text()
    # soltar «Medir» desde la lista de herramientas sobre la tira
    pagina.buscar.setText("medir")
    medir = next(pagina.lista.item(i) for i in range(pagina.lista.count()) if pagina.lista.item(i).data(Qt.UserRole) == "medir")
    pagina.lista.setCurrentItem(medir)
    evento = _Soltar(pagina.lista, QPoint(5, 5))
    pagina.tira.dropEvent(evento)
    assert evento.aceptado and [pagina.tira.item(i).data(Qt.UserRole) for i in range(pagina.tira.count())] == ["medir"]
    assert json.loads(pagina.value()) == {"SÓLIDO/FAVORITAS": ["medir"]}
    pagina.tira.dropEvent(_Soltar(pagina.lista, QPoint(5, 5)))              # la misma otra vez: no se repite
    assert pagina.tira.count() == 1 and "ya está" in pagina.aviso.text()
    # reordenar: agregar otra y mover la primera al final
    pagina._agregar("vaciado", None)
    it = pagina.tira.takeItem(0)
    pagina.tira.insertItem(1, it)
    pagina.tira.cambio.emit()
    assert json.loads(pagina.value()) == {"SÓLIDO/FAVORITAS": ["vaciado", "medir"]}
    # el tope
    for clave in list(cp.COMANDOS)[:cp.MAXIMO]:
        pagina._agregar(clave, None)
    assert len(json.loads(pagina.value())["SÓLIDO/FAVORITAS"]) == cp.MAXIMO and "quitá uno" in pagina.aviso.text()
    # quitar con la tecla Suprimir y volver a fábrica
    pagina.tira.setCurrentRow(0)
    pagina.tira.keyPressEvent(type("K", (), {"key": lambda s: Qt.Key_Delete})())
    assert pagina.tira.count() == cp.MAXIMO - 1
    pagina.b_fabrica.click()
    assert pagina.tira.count() == 0 and pagina.value() == "{}"
    # Aceptar guarda en las preferencias
    pagina._agregar("medir", None)
    dlg.b_aplicar.setEnabled(True)
    assert dlg._aplicar() and json.loads(prefs["cinta/personal"]) == {"SÓLIDO/FAVORITAS": ["medir"]}
    dlg.reject()
    dlg.deleteLater()
