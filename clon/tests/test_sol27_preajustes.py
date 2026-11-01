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


def _accion(boton, texto):
    """La entrada del menú de preajustes que empieza con `texto` (se arma al abrirlo, como cuando la persona lo despliega)."""
    boton.menu.aboutToShow.emit()
    acciones = boton.menu.actions()
    return next((a for a in acciones if a.text() == texto), None) or next(a for a in acciones if a.text().startswith(texto))


def test_panel_guarda_aplica_y_abre_con_el_predeterminado(monkeypatch):
    from omnicad.ui.comandos.crear import Nervio
    from omnicad.ui.preajustes_ui import BotonPreajustes
    panel = _panel(Nervio())
    boton = panel.boton_preajustes
    cabecera = boton.parentWidget()
    assert isinstance(boton, BotonPreajustes) and cabecera.objectName() == "cabecera_comando"     # UI-4: va en la cabecera
    assert panel.findChildren(BotonPreajustes) == [boton]
    assert _accion(boton, "Valores de fábrica").isChecked()
    clave = next(c.clave for c in panel.campos if c.clave == "espesor")
    panel.set_valor(clave, "7 mm")
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Siete", True))
    _accion(boton, "Guardar los valores actuales como nuevo").trigger()
    assert pre.obtener("nervio", "Siete")[clave] == "7 mm" and boton.actual == "Siete" and _accion(boton, "Siete").isChecked()
    panel.set_valor(clave, "3 mm")
    _accion(boton, "Valores de fábrica").trigger()
    assert panel.valores[clave] == "2 mm" and boton.actual is None
    _accion(boton, "Siete").trigger()
    assert panel.valores[clave] == "7 mm" and boton.actual == "Siete"
    boton._predeterminado("Siete")
    assert _accion(boton, "Siete").text() == "Siete (predeterminado)"
    assert _panel(Nervio()).valores[clave] == "7 mm"               # un diálogo nuevo abre con el predeterminado
    panel.set_valor(clave, "9 mm")
    _accion(boton, "Guardar").trigger()                            # «Guardar»: pisa el preajuste elegido
    assert pre.obtener("nervio", "Siete")[clave] == "9 mm"
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Siete", True))
    _accion(boton, "Guardar los valores actuales como nuevo").trigger()    # el nombre repetido avisa y no pisa
    assert "Ya existe" in panel.mensaje.text()
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Nueve", True))
    _accion(boton, "Renombrar").trigger()
    assert pre.listar("nervio")["presets"] == ["Nueve"] and boton.actual == "Nueve"
    _accion(boton, "Eliminar").trigger()
    assert pre.listar("nervio") == {"presets": [], "default": "fabrica"} and boton.actual is None


def test_los_paneles_sin_valores_guardables_no_traen_el_boton(monkeypatch):
    from omnicad.ui.comandos.crear import Nervio
    panel = _panel(Nervio())
    assert panel.boton_preajustes is not None
    from omnicad.ui import preajustes_ui
    monkeypatch.setattr(preajustes_ui, "tiene_preajustes", lambda _p: False)
    assert _panel(Nervio()).boton_preajustes is None


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


def test_el_boton_de_preajustes_se_alcanza_con_tab_y_abre_con_espacio_o_enter():
    """Con teclado: Tab llega a «⋯» después de Cancelar y Espacio o Enter abren su menú (Enter no acepta el comando)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtTest import QTest
    from omnicad.ui.comandos.crear import Nervio
    panel = _panel(Nervio())
    aceptado = []
    panel.aceptado.connect(aceptado.append)
    atajo = []
    accion = QAction(panel)                         # la ventana real tiene Espacio como atajo («Boceto sobre la cara»)
    accion.setShortcut(QKeySequence(Qt.Key_Space))
    accion.triggered.connect(lambda *_: atajo.append(1))
    panel.addAction(accion)
    panel.show()
    panel.activateWindow()
    assert QTest.qWaitForWindowActive(panel)
    boton = panel.boton_preajustes
    assert boton.focusPolicy() == Qt.StrongFocus
    panel.boton_cancelar.setFocus()
    QTest.keyClick(panel.boton_cancelar, Qt.Key_Tab)
    assert QApplication.focusWidget() is boton
    abierto = []
    boton.menu.aboutToShow.connect(lambda: abierto.append(True))
    for tecla in (Qt.Key_Space, Qt.Key_Return):
        QTest.keyClick(boton, tecla)
        boton.menu.close()
    assert abierto == [True, True] and aceptado == [] and atajo == [] and panel.isVisible()      # Espacio no disparó el atajo
    panel.close()
