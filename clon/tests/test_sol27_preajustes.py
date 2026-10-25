# -*- coding: utf-8 -*-
"""SOL-27: preajustes de comandos (guardar, elegir, renombrar, borrar, predeterminado y último usado)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QInputDialog  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import preajustes as pre  # noqa: E402


@pytest.fixture(autouse=True)
def archivo_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv(pre.VAR_PREAJUSTES, str(tmp_path / "preajustes.json"))


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_nucleo_guardar_leer_renombrar_borrar_y_predeterminado():
    pre.guardar("nervio", "Fino", {"espesor": "1.5 mm", "invertir": True, "perfil": [{"x": 1}], "dibujo": None})
    assert pre.obtener("nervio", "Fino") == {"espesor": "1.5 mm", "invertir": True}      # lo de la vista no se guarda
    with pytest.raises(geo.ErrorGeometria):
        pre.guardar("nervio", "Fino", {"espesor": "2 mm"}, sobrescribir=False)
    with pytest.raises(geo.ErrorGeometria):
        pre.guardar("nervio", "  ", {"espesor": "2 mm"})
    pre.definir_defecto("nervio", "Fino")
    assert pre.valores_iniciales("nervio") == {"espesor": "1.5 mm", "invertir": True}
    pre.renombrar("nervio", "Fino", "Delgado")
    assert pre.listar("nervio") == {"presets": ["Delgado"], "default": "Delgado"}          # el predeterminado lo sigue
    pre.guardar_ultimo("nervio", {"espesor": "3 mm"})
    pre.definir_defecto("nervio", pre.ULTIMO)
    assert pre.valores_iniciales("nervio") == {"espesor": "3 mm"}
    pre.borrar("nervio", "Delgado")
    assert pre.listar("nervio")["presets"] == []
    pre.definir_defecto("nervio", pre.FABRICA)
    assert pre.valores_iniciales("nervio") == {}
    with pytest.raises(geo.ErrorGeometria):
        pre.definir_defecto("nervio", "No existe")


def test_archivo_dañado_o_ajeno_no_rompe():
    ruta = pre.ruta_preajustes()
    ruta.write_text("{esto no es json", encoding="utf-8")
    assert pre.listar("nervio") == {"presets": [], "default": "fabrica"}
    ruta.write_text("[1, 2]", encoding="utf-8")
    assert pre.valores_iniciales("nervio") == {}


def test_herramienta_manage_command_presets():
    s = api.Sesion()
    r = llamar(s, "manage_command_presets", command="red", action="save", name="Grueso", values={"espesor": "4 mm"})
    assert r["presets"] == ["Grueso"] and r["default"] == "factory"
    assert llamar(s, "manage_command_presets", command="red", action="get", name="Grueso")["values"] == {"espesor": "4 mm"}
    llamar(s, "manage_command_presets", command="red", action="set_default", default="Grueso")
    assert llamar(s, "manage_command_presets", command="red", action="list")["default"] == "Grueso"
    llamar(s, "manage_command_presets", command="red", action="rename", name="Grueso", new_name="Gordo")
    assert llamar(s, "manage_command_presets", command="red", action="delete", name="Gordo")["default"] == "factory"
    for args in ({"command": "red", "action": "get", "name": "Nada"}, {"command": "", "action": "list"},
                 {"command": "red", "action": "save", "name": "X", "values": {}},
                 {"command": "red", "action": "set_default", "default": "Nada"}):
        assert not api.llamar(s, "manage_command_presets", args)["ok"], args


def _panel(comando):
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    doc = Documento()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    return PanelComando(comando, ContextoComando(doc), visor)


def test_panel_guarda_aplica_y_abre_con_el_predeterminado(monkeypatch):
    from omnicad.ui.comandos.crear import Nervio
    from omnicad.ui.preajustes_ui import FilaPreajustes
    panel = _panel(Nervio())
    fila = panel.findChild(FilaPreajustes)
    assert fila is not None and fila.lista.count() == 1
    clave = next(c.clave for c in panel.campos if c.clave == "espesor")
    panel.set_valor(clave, "7 mm")
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Siete", True))
    fila.mas.click()                                               # «＋»: guarda los valores actuales
    assert pre.obtener("nervio", "Siete")[clave] == "7 mm" and fila.lista.currentData() == "Siete"
    panel.set_valor(clave, "3 mm")
    fila.lista.setCurrentIndex(0)                                  # valores de fábrica
    fila.lista.activated.emit(0)
    assert panel.valores[clave] == "2 mm"
    fila.lista.setCurrentIndex(fila.lista.findData("Siete"))
    fila.lista.activated.emit(fila.lista.currentIndex())
    assert panel.valores[clave] == "7 mm"
    fila._predeterminado("Siete")
    assert _panel(Nervio()).valores[clave] == "7 mm"               # un diálogo nuevo abre con el predeterminado
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Siete", True))
    fila.mas.click()                                               # el nombre repetido avisa y no pisa
    assert "Ya existe" in panel.mensaje.text()
    fila._eliminar()
    assert pre.listar("nervio") == {"presets": [], "default": "fabrica"}


def test_ultimo_usado_se_guarda_al_aceptar(monkeypatch):
    from omnicad.ui.comandos.crear import Nervio
    from omnicad.ui.preajustes_ui import recordar_ultimo
    pre.definir_defecto("nervio", pre.ULTIMO)
    panel = _panel(Nervio())
    clave = next(c.clave for c in panel.campos if c.clave == "espesor")
    panel.set_valor(clave, "5 mm")
    recordar_ultimo(panel)
    assert _panel(Nervio()).valores[clave] == "5 mm"


def test_manage_command_presets_rechaza_un_comando_que_no_existe():
    s = api.Sesion()
    r = api.llamar(s, "manage_command_presets", {"command": "nervvio", "action": "list"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS" and any("nervio" in p for p in r["pistas"])
