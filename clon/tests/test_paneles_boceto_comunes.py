# -*- coding: utf-8 -*-
"""UI-5: los paneles del boceto (Simetría, Patrón, Escala/Mover y Carácter) usan lo mismo que `PanelComando` en vez de repetirlo:
cabecera movible (`formulario.armar_cabecera`), ancho por tipo (`formulario.ANCHOS`) y mensajes con símbolo
(`formulario.poner_mensaje`). Los preajustes no corresponden: Fusion solo los tiene en las herramientas de sólido."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton, QWidget  # noqa: E402

from omnicad.ui import formulario as F  # noqa: E402
from omnicad.ui.modo_boceto import PanelCaracter  # noqa: E402
from omnicad.ui.panel_patron import PanelPatron  # noqa: E402
from omnicad.ui.panel_simetria import PanelSimetria  # noqa: E402
from omnicad.ui.panel_transformar import PanelTransformar  # noqa: E402
from omnicad.ui.superposiciones import CabeceraMovible  # noqa: E402


class _Area(QWidget):
    """Hace de `AreaVisor`: solo cuenta las veces que se pide reubicar."""

    def __init__(self):
        super().__init__()
        self.reubicados = 0
        self.resize(900, 600)

    def reubicar(self):
        self.reubicados += 1


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def _paneles(area):
    return {"simetria": PanelSimetria(area), "patron": PanelPatron(area), "transformar": PanelTransformar(area),
            "caracter": PanelCaracter(area)}


def _evento(w, tipo, global_):
    QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(w.mapFromGlobal(global_)), QPointF(global_), Qt.LeftButton,
                                          Qt.LeftButton, Qt.NoModifier))


def test_todos_tienen_la_cabecera_movible_con_su_titulo(app_qt):
    area = _Area()
    for nombre, p in _paneles(area).items():
        cab = p.findChild(CabeceraMovible)
        assert cab is not None and cab.objectName() == "cabecera_comando", nombre
        assert p.findChild(QWidget, "titulo_comando").text(), nombre
        assert p.posicion_usuario is None, nombre


def test_arrastrar_la_cabecera_mueve_el_panel_y_el_doble_clic_lo_devuelve(app_qt):
    area = _Area()
    for nombre, p in _paneles(area).items():
        p.show()
        cab = p.findChild(CabeceraMovible)
        ini = cab.mapToGlobal(QPoint(30, 8))
        _evento(cab, QEvent.MouseButtonPress, ini)
        for i in (1, 2, 3):
            _evento(cab, QEvent.MouseMove, ini + QPoint(-20 * i, 15 * i))
        _evento(cab, QEvent.MouseButtonRelease, ini + QPoint(-60, 45))
        assert p.posicion_usuario is not None, nombre
        antes = area.reubicados
        _evento(cab, QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
        assert p.posicion_usuario is None and area.reubicados > antes, nombre


def test_el_ancho_sale_de_la_tabla_comun(app_qt):
    area = _Area()
    p = _paneles(area)
    p["simetria"].ajustar()
    p["patron"].ajustar()
    p["transformar"].ajustar()
    assert p["simetria"].width() == F.ANCHOS["simple"]
    assert p["patron"].width() == p["transformar"].width() == F.ANCHOS["normal"]
    assert p["caracter"].width() >= PanelCaracter.ANCHO


def test_la_cruz_cancela_y_no_toma_el_foco(app_qt):
    area = _Area()
    for p in (PanelSimetria(area), PanelPatron(area)):
        cerradas = []
        p.cancelado.connect(lambda c=cerradas: c.append(1))
        cruz = next(b for b in p.findChildren(QToolButton) if b.text() == "✕")
        assert cruz.focusPolicy() == Qt.NoFocus and cruz.toolTip() == "Cancelar (Esc)"
        cruz.click()
        assert cerradas == [1]
    assert not [b for b in PanelCaracter(area).findChildren(QToolButton) if b.text() == "✕"]     # Carácter no se cancela


def test_la_instruccion_y_el_error_llevan_su_simbolo_y_se_ocultan_vacios(app_qt):
    area = _Area()
    area.show()
    p = PanelSimetria(area)
    p.show()
    estado = {"objetos": 0, "eje": False, "campo": "seleccion", "valido": False, "previa": True,
              "guia": "Elegí la geometría a reflejar.", "error": "Falta el eje de simetría."}
    p.mostrar(estado)
    assert p.guia.text() == estado["guia"] and p.icono_guia.text() == "➜" and p.guia.property("tipo") == "instruccion"
    assert p.mensaje.text() == estado["error"] and p.icono_mensaje.text() == "✖" and p.mensaje.property("tipo") == "invalido"
    assert p.guia.isVisible() and p.mensaje.isVisible()
    alto = p.height()
    p.mostrar(estado | {"guia": "", "error": ""})
    assert not p.guia.isVisible() and not p.mensaje.isVisible() and not p.icono_guia.isVisible()
    assert p.height() < alto                                              # sin mensajes la línea no ocupa lugar


def test_patron_y_transformar_usan_las_mismas_lineas_de_estado(app_qt):
    area = _Area()
    for p in (PanelPatron(area), PanelTransformar(area)):
        p.show()
        F.poner_estado(p, "Elegí el centro.", "La cantidad tiene que ser 2 o más.")
        assert p.icono_guia.text() == "➜" and p.icono_mensaje.text() == "✖"
        assert p.guia.text() == "Elegí el centro." and p.mensaje.text() == "La cantidad tiene que ser 2 o más."
        assert p.mensaje.maximumWidth() == p.ANCHO - 44


@pytest.mark.parametrize("alto", [720, 520, 420])
def test_el_panel_caracter_no_pasa_del_alto_del_lienzo_y_su_cuerpo_se_desplaza(app_qt, alto):
    """UI-8: mide ≈ 540 px; en una ventana baja se achica, la cabecera queda a la vista y lo de abajo se alcanza con la barra,
    también con todas las secciones abiertas (que lo hacen más alto todavía)."""
    area = _Area()
    area.resize(900, alto)
    p = PanelCaracter(area)
    area.show()
    p.show()
    p.ajustar_alto(alto - 16)
    app_qt.processEvents()
    assert p.height() <= alto - 16 and p.findChild(CabeceraMovible).isVisible()
    barra = p.desplazador.verticalScrollBar()
    natural = p.findChild(CabeceraMovible).sizeHint().height() + p.cuerpo.sizeHint().height()
    assert (barra.maximum() > 0) == (natural > alto - 16)
    for seccion in ("Decoraciones", "Transformaciones", "Avanzado"):
        next(b for b in p.findChildren(QToolButton) if b.text().endswith(seccion)).click()
    p.ajustar_alto(alto - 16)
    app_qt.processEvents()
    assert p.height() <= alto - 16 and barra.maximum() > 0
    barra.setValue(barra.maximum())
    vista = p.desplazador.viewport()
    assert p.sin_division.mapTo(vista, QPoint(0, p.sin_division.height())).y() <= vista.height()
