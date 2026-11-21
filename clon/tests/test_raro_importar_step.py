# -*- coding: utf-8 -*-
"""Valores raros del comando «importar_step» (Insertar STEP): los campos de su diálogo son los de la herramienta
del catálogo en la que se apoya la clave de cinta (`test_cobertura_ui_api.py`): `path`, `mesh_units` y `name`, más
el campo de archivo del cuadro «Insertar STEP» de la ventana. La ayuda de Fusion
(`docs/fusion_docs/contenido/fusion-designs/insert-designs-*.md`) describe Insertar como elegir un archivo: no hay
campos numéricos donde tipear. Cada campo se prueba en vacío, 0, negativo, enorme, con unidades y con expresión:
ningún valor cierra la app, deja el documento roto ni contesta con un mensaje de más de un renglón.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

from omnicad import api  # noqa: E402
from test_abrir_externo import _step_con_estructura  # noqa: E402

RAROS = ("", "0", "-5", "1e9", "10 mm", "2*3")
RUTAS_RARAS = (*RAROS, "pieza 10 mm.step", "2*3.step")


def _llamar(sesion, **args):
    r = api.llamar(sesion, "insert_file", args)
    assert isinstance(r, dict) and isinstance(r.get("ok"), bool), r
    return r


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sesion(app_qt, tmp_path):
    assert app_qt is not None
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "name": "Viejo"})["ok"]
    s.step = str(_step_con_estructura(tmp_path / "pieza.step"))
    return s


def _sin_rotura(sesion, r):
    assert QApplication.instance() is not None, "la app se cerró"
    assert len(sesion.doc.operaciones) == 1 and sesion.doc.estado_final is not None, "el documento quedó roto"
    if not r["ok"]:
        assert isinstance(r.get("mensaje"), str) and r["mensaje"], r
        assert "\n" not in r["mensaje"] and "\r" not in r["mensaje"], r["mensaje"]


@pytest.mark.parametrize("path", RUTAS_RARAS)
def test_path_con_valor_raro_se_rechaza_sin_tocar_el_documento(sesion, path):
    r = _llamar(sesion, path=path)
    _sin_rotura(sesion, r)
    assert not r["ok"] and r["error_kind"] in ("UNSUPPORTED_FILE_TYPE", "FILE_NOT_FOUND"), r


@pytest.mark.parametrize("mesh_units", RAROS)
def test_mesh_units_con_valor_raro_se_rechaza_nombrando_el_campo(sesion, mesh_units):
    r = _llamar(sesion, path=sesion.step, mesh_units=mesh_units)
    _sin_rotura(sesion, r)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert "mesh_units" in r["mensaje"], r


@pytest.mark.parametrize("name", RAROS)
def test_name_con_valor_raro_inseta_sin_romper_el_documento(sesion, name):
    r = _llamar(sesion, path=sesion.step, name=name)
    assert QApplication.instance() is not None, "la app se cerró"
    assert r["ok"] and r["result"]["status"] == "ok", r
    assert len(sesion.doc.operaciones) == 2
    paso = sesion.doc.operaciones[-1]
    assert paso.nombre, "el paso quedó sin nombre"
    if name.strip():
        assert paso.nombre == name
    assert sesion.doc.estado_final.cuerpos, "no entró ningún cuerpo"
    assert all("\n" not in m and "\r" not in m for m in r["avisos"]), r["avisos"]


def test_name_enorme_se_rechaza_en_un_renglon(sesion):
    r = _llamar(sesion, path=sesion.step, name="x" * 300)
    _sin_rotura(sesion, r)
    assert not r["ok"], r


@pytest.fixture
def ventana(app_qt, tmp_path):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    s = api.Sesion()
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(900, 600)
    v.show()
    app_qt.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app_qt.processEvents()


@pytest.mark.parametrize("path", RAROS)
def test_cuadro_insertar_step_con_nombre_raro_no_cierra_la_app(ventana, monkeypatch, path):
    avisos = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (path, "")))
    monkeypatch.setattr(QMessageBox, "critical", lambda padre, titulo, texto: avisos.append(texto))
    antes = len(ventana.doc.operaciones)
    ventana.importar_step()
    app = QApplication.instance()
    assert app is not None and ventana.isVisible(), "la app se cerró"
    assert len(ventana.doc.operaciones) == antes and ventana.doc.estado_final is not None, "el documento quedó roto"
    if path == "":
        assert not avisos, avisos
    else:
        assert avisos and all("\n" not in m and "\r" not in m for m in avisos), avisos
