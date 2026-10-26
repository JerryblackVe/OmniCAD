# -*- coding: utf-8 -*-
"""P-9g: los íconos siguen al tema sin reiniciar (`iconos.IconoVivo` + `iconos_tema`), y el navegador dibuja la insignia
de estado de cada fila a 16 px."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.ui import iconos, iconos_tema, temas  # noqa: E402
from omnicad.ui.navegador import ROL_ESTADO, Navegador  # noqa: E402
from omnicad.ui.panel_timeline import PanelTimeline  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    app = QApplication.instance() or QApplication([])
    iconos_tema.instalar()
    return app


@pytest.fixture(autouse=True)
def tema_de_fabrica():
    previo = temas.clave_activa()
    yield
    temas.activar(previo)


def _bytes(ico, tam=24):
    return bytes(ico.pixmap(tam, tam).toImage().constBits())


def test_el_icono_se_dibuja_al_tamano_pedido_y_con_pixeles_de_pantalla_densa():
    ico = iconos.icono("extruir")
    assert ico.pixmap(24, 24).size() == QSize(24, 24)
    denso = ico.pixmap(QSize(24, 24), 2.0)
    assert denso.size() == QSize(48, 48) and denso.devicePixelRatio() == 2.0


def test_paint_dibuja_el_icono_centrado_en_el_rectangulo_y_en_pantalla_densa():
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter
    img = QImage(96, 96, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    img.setDevicePixelRatio(2.0)                       # 48×48 unidades lógicas
    p = QPainter(img)
    iconos.icono("extruir").paint(p, QRect(8, 8, 32, 32))
    p.end()
    opacos = [(x, y) for x in range(96) for y in range(96) if img.pixelColor(x, y).alpha() > 40]
    assert len(opacos) > 200
    assert all(16 <= x < 80 and 16 <= y < 80 for x, y in opacos)       # solo dentro del rectángulo (8..40 unidades × 2)


def test_el_modo_deshabilitado_es_otra_imagen():
    ico = iconos.icono("extruir")
    assert ico.pixmap(24, 24, QIcon.Disabled).toImage() != ico.pixmap(24, 24).toImage()


def test_cambiar_de_tema_cambia_los_iconos_sin_recrearlos():
    ico = iconos.icono("tl_reproducir")             # trazo gris oscuro: sobre un tema oscuro pasa al color del texto
    temas.activar("claro_moderno")
    claro = _bytes(ico)
    temas.activar("oscuro_moderno")
    assert _bytes(ico) != claro
    temas.activar("claro_moderno")
    assert _bytes(ico) == claro


def test_el_timeline_reconstruye_sus_pasos_apagados_al_cambiar_de_tema():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    s.doc.operaciones[0].suprimida = True
    s.doc.recalcular(0)
    t = PanelTimeline()
    t.actualizar(s.doc)
    antes = t.lista.item(0).icon()
    t.resaltar(s.doc.operaciones[0].id)
    t.repintar_iconos()
    assert t.lista.item(0).icon().cacheKey() != antes.cacheKey()       # se armó de nuevo
    assert t.lista.currentItem().data(Qt.UserRole) == s.doc.operaciones[0].id      # y sigue en el mismo paso
    assert t.lista.count() == 2                                         # el paso y el marcador


def test_el_navegador_guarda_el_estado_de_cada_fila():
    nav = Navegador()
    vis = {k: True for k in ("todo", "origen", "planos", "cuerpos", "bocetos", "calcomanias")}
    nav.estados = {"op2.c1": "aviso"}
    nav.actualizar("Doc", [("op2.c1", "Cuerpo1"), ("op3.c1", "Cuerpo2")], [], set(), vis)
    assert nav.item("op2.c1").data(0, ROL_ESTADO) == "aviso" and nav.item("op3.c1").data(0, ROL_ESTADO) is None
