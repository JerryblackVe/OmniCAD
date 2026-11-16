# -*- coding: utf-8 -*-
"""P-166: unos diez temas de color completos, con muestras en Preferencias › Apariencia y por MCP/CLI."""
import itertools
import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.ui import temas  # noqa: E402


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


def test_hay_diez_temas_con_el_del_sistema():
    assert len(temas.INCLUIDOS) + 1 == 10


@pytest.mark.parametrize("clave", list(temas.INCLUIDOS))
def test_cada_tema_define_todos_los_colores_y_se_lee_bien(clave):
    colores = temas.INCLUIDOS[clave]["colores"]
    assert set(colores) == set(temas.CLAVES_COLOR) and temas.contraste_bajo(colores) == []
    assert len(temas.INCLUIDOS[clave]["nombre"]) <= 18                      # el nombre entra en su tarjeta


@pytest.mark.parametrize("a,b", list(itertools.combinations(temas.INCLUIDOS, 2)))
def test_dos_temas_cualesquiera_cambian_la_mayor_parte_de_los_colores(a, b):
    ca, cb = temas.INCLUIDOS[a]["colores"], temas.INCLUIDOS[b]["colores"]
    distintos = [k for k in temas.CLAVES_COLOR if ca[k] != cb[k]]
    assert len(distintos) >= 12
    assert ca["fondo"] != cb["fondo"]                                       # ni dos temas con el mismo fondo


@pytest.mark.parametrize("clave", list(temas.INCLUIDOS))
def test_elegir_un_tema_cambia_el_estilo_de_toda_la_app(qapp, clave):
    colores = temas.INCLUIDOS[clave]["colores"]
    temas.activar(clave)
    try:
        assert temas.clave_activa() == clave and temas.color("fondo") == colores["fondo"]
        qss = temas.qss_activo()
        for token in ("fondo", "panel", "texto", "acento", "menu_fondo", "boton_primario", "borde"):
            assert colores[token] in qss, token
    finally:
        temas.activar(temas.DEFECTO)


def test_las_tarjetas_de_preferencias_muestran_los_diez(qapp, tmp_path, monkeypatch):
    from omnicad.ui.preferencias import DialogoPreferencias, Preferencias
    monkeypatch.setenv(temas.VAR_CARPETA, str(tmp_path))
    dlg = DialogoPreferencias(Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)), inicial="apariencia")
    dlg.show()
    tarjetas = dlg.selector_temas.findChildren(QToolButton, "tarjeta_tema")
    assert len(tarjetas) == 10 and len({t.property("clave_tema") for t in tarjetas}) == 10
    dlg.reject()
    dlg.deleteLater()


def test_list_themes_y_set_theme(ajustes):
    r = _llamar("list_themes")
    assert len(r["themes"]) == 10 and r["current"] == temas.DEFECTO
    assert next(t for t in r["themes"] if t["theme"] == "menta")["colors"]["acento"] == temas.INCLUIDOS["menta"]["colores"]["acento"]
    assert _llamar("set_theme", theme="grafito")["ok"] and ajustes.value("general/tema") == "grafito"
    assert _llamar("list_themes")["current"] == "grafito"
    assert _llamar("set_theme", theme="sistema")["ok"]
    mal = _llamar("set_theme", theme="../../etc/x")
    assert not mal["ok"] and mal["error_kind"] == "INVALID_ARGUMENTS" and ajustes.value("general/tema") == "sistema"
    json.dumps(r)                                                            # el resultado viaja por MCP: serializable
