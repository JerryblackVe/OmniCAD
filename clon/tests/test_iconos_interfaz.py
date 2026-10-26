# -*- coding: utf-8 -*-
"""Íconos existentes en los menús del navegador, las herramientas del chat y los diálogos."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QToolButton, QTreeWidget, QTreeWidgetItem, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import acciones_navegador as navegador, asistente, dialogos, dialogos_boceto, iconos  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("mapa", [navegador.ICONOS_MENU, asistente.ICONO_HERRAMIENTA, asistente.ICONO_GRUPO])
def test_los_mapas_solo_usan_dibujos_existentes(mapa):
    assert set(mapa.values()) <= iconos.DIBUJOS.keys()


def test_todo_el_catalogo_resuelve_por_herramienta_o_grupo():
    catalogo = api.catalogo()
    assert set(asistente.ICONO_HERRAMIENTA) <= {h["nombre"] for h in catalogo}
    assert {h["grupo"] for h in catalogo} <= asistente.ICONO_GRUPO.keys()
    for herramienta in catalogo:
        assert asistente.icono_herramienta(herramienta["nombre"]) in iconos.DIBUJOS
    assert asistente.icono_herramienta("extrude") == "extruir"
    assert asistente.icono_herramienta("draw_arc") == asistente.ICONO_GRUPO["boceto"]
    assert asistente.icono_herramienta("no_existe") == "asistente"


def test_con_iconos_recorre_submenus_y_respeta_atajos_y_acciones(app_qt):
    menu = QMenu()
    extruir = menu.addAction("Extruir\tE")
    submenu = menu.addMenu("Desplazar al grupo")
    carpeta = submenu.addAction("Carpeta original")
    suprimir = submenu.addAction("Suprimir\tSuprimir")
    suprimir.setEnabled(False)
    desconocida = submenu.addAction("Sin dibujo")
    separador = menu.addSeparator()
    activadas = []
    extruir.triggered.connect(lambda: activadas.append(True))
    assert navegador.con_iconos(menu) is menu
    for accion in (extruir, submenu.menuAction(), carpeta, suprimir):
        assert not accion.icon().isNull(), accion.text()
    assert desconocida.icon().isNull() and separador.icon().isNull()
    assert not suprimir.isEnabled() and extruir.text() == "Extruir\tE"
    extruir.trigger()
    assert activadas == [True]


@pytest.mark.parametrize("tipo", ["cuerpo", "raiz", "boceto", "calcomania"])
def test_menu_aplica_iconos_a_mas_del_80_por_ciento_de_sus_textos(app_qt, monkeypatch, tipo):
    arbol = QTreeWidget()
    arbol.arbol = arbol
    estado = SimpleNamespace(cuerpos={"cuerpo": None}, componentes={},
                             bocetos={"boceto": SimpleNamespace(perfiles=[])})
    ventana = SimpleNamespace(navegador=arbol, doc=SimpleNamespace(estado_final=estado, operaciones=[]),
                              modo_boceto=SimpleNamespace(activo=False), ocultos=set(),
                              acciones={clave: QAction(arbol) for clave in ("configurar", "nuevo_dibujo", "grupo_rigido")})
    monkeypatch.setattr(navegador, "datos_navegador", lambda doc: {"grupos": {}})
    item = QTreeWidgetItem()
    item.setData(0, navegador.ROL_CLAVE, tipo)
    item.setData(0, navegador.ROL_TIPO, tipo)
    menu = navegador.menu(ventana, item)
    acciones = [a for a in menu.actions() if not a.isSeparator()]
    con_dibujo = [a for a in acciones if a.text().split("\t")[0] in navegador.ICONOS_MENU]
    assert len(con_dibujo) / len(acciones) >= 0.8
    assert all(not a.icon().isNull() for a in con_dibujo)


def test_la_linea_del_chat_muestra_icono_y_texto_y_sigue_plegandose(app_qt):
    panel = SimpleNamespace(ventana=SimpleNamespace(prefs={"asistente/ver_herramientas": True}),
                            _agregar=lambda widget: widget)
    caja = asistente.PanelAsistente._agregar_herramienta(panel, "extrude", {}, {"ok": True})
    linea = caja.findChild(QToolButton, "herramienta_asistente")
    assert not linea.icon().isNull()
    assert linea.toolButtonStyle() == Qt.ToolButtonTextBesideIcon
    assert linea.text() == "✓ extrude"
    detalle = caja.layout().itemAt(1).widget()
    assert detalle.isHidden()
    linea.click()
    assert not detalle.isHidden()
    linea.click()
    assert detalle.isHidden()
    caja.close()


def test_los_dialogos_generales_tienen_el_icono_correspondiente(app_qt):
    casos = [(dialogos.DialogoParametros(TablaParametros()), "parametros"),
             (dialogos.DialogoRejilla(), "rejilla"), (dialogos.DialogoRecuperados([]), "archivo")]
    for forma, titulo in OpPrimitiva.ETIQUETAS.items():
        casos.append((dialogos._DialogoBase(titulo), forma))
    for dialogo, nombre in casos:
        assert nombre in iconos.DIBUJOS
        assert not dialogo.windowIcon().isNull()
        assert dialogo.windowIcon().cacheKey() == iconos.icono(nombre).cacheKey()
        dialogo.close()


@pytest.mark.parametrize("tipo", ["rectangular", "circular"])
def test_el_dialogo_del_patron_usa_su_tipo_de_patron(app_qt, tipo):
    registro = {"tipo": tipo, "suprimidos": [], "params": {
        "cantidad1": 2, "cantidad2": 2, "distancia1": 10, "distancia2": 10, "modo": "espaciado",
        "dir1": [1, 0], "dir2": [0, 1], "cantidad": 3, "angulo_total": 360, "simetrico": False,
    }}
    dialogo = dialogos_boceto.DialogoPatron(SimpleNamespace(curvas={}), registro)
    nombre = f"patron_{tipo}"
    assert nombre in iconos.DIBUJOS
    assert not dialogo.windowIcon().isNull()
    assert dialogo.windowIcon().cacheKey() == iconos.icono(nombre).cacheKey()
    dialogo.close()


def test_el_dialogo_de_proyecciones_perdidas_tiene_icono(app_qt):
    lienzo = QWidget()
    lienzo.perdidas = []
    dialogo = dialogos_boceto.DialogoPerdidas(lienzo)
    assert "proyectar" in iconos.DIBUJOS
    assert not dialogo.windowIcon().isNull()
    assert dialogo.windowIcon().cacheKey() == iconos.icono("proyectar").cacheKey()
    dialogo.close()
