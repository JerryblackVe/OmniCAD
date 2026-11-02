"""Revisión Fase 9: el parámetro de texto en el diálogo «Parámetros» y en el CSV."""
import os

import pytest

from omnicad import api

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def sesion_con_texto(texto="Hola"):
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="Rotulo")
    llamar(s, "add_text", text=texto)
    return s


def test_dialogo_parametros_edita_y_acepta_el_texto():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.dialogo_parametros import EXPRESION, NOMBRE, UNIDAD, VALOR, DialogoParametros
    QApplication.instance() or QApplication([])
    s = sesion_con_texto()
    dlg = DialogoParametros(s.doc)
    fila = dlg.arbol.findItems("Text", Qt.MatchExactly | Qt.MatchRecursive, NOMBRE)[0]
    assert fila.text(VALOR) == "Hola" and fila.text(UNIDAD) == "Text"
    fila.setText(EXPRESION, " Chau ")
    dlg._aceptar()
    assert s.doc.parametros.valores()["Text"] == " Chau "


def test_csv_ida_y_vuelta_del_texto(tmp_path):
    origen = sesion_con_texto("Hola")
    ruta = tmp_path / "p.csv"
    llamar(origen, "export_parameters", path=str(ruta))
    assert "Text,text,Hola" in ruta.read_text(encoding="utf-8")
    destino = api.Sesion()
    llamar(destino, "import_parameters", path=str(ruta))
    assert destino.doc.parametros.valores()["Text"] == "Hola"


def test_csv_viejo_sin_unidad_sigue_importando(tmp_path):
    ruta = tmp_path / "viejo.csv"
    ruta.write_text("Name,Unit,Expression,Value,Comments\nancho,mm,20 mm,20,\nk,,3,3,\n", encoding="utf-8")
    s = api.Sesion()
    llamar(s, "import_parameters", path=str(ruta))
    v = s.doc.parametros.valores()
    assert v["ancho"] == pytest.approx(20) and v["k"] == pytest.approx(3)
