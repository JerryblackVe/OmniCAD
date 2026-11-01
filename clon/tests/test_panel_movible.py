# -*- coding: utf-8 -*-
"""UI-3, UI-4 y UI-7: el panel de comando se mueve por la cabecera (y se recuerda), los preajustes viven en la cabecera y
ninguna selección cae en «Más opciones»."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

CLAVE_PREF = "vista/posicion_panel_comando"


def _ventana(ini):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ini), QSettings.IniFormat)))
    v.resize(1024, 640)
    v.show()
    QTest.qWait(1)
    return v


@pytest.fixture
def ventana(tmp_path):
    v = _ventana(tmp_path / "p.ini")
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _perfil(v):
    """Un perfil de boceto para abrir Extruir: sin nada que extruir, el comando se niega a abrir."""
    from omnicad.restricciones import Boceto
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    v.doc.agregar(OpBoceto(v.doc.nuevo_id(), "Boceto1", boceto=b))
    paso = v.doc.operaciones[-1]
    datos = v.doc.estado_final.bocetos[paso.id].perfiles[0]
    return hit_desde_ref({"tipo": "perfil", "boceto": paso.id, **OpExtrusion.referencia_perfil(datos)}, v.doc.estado_final)


def _abrir(v):
    from omnicad.ui.comandos.solido import Extruir
    if v.panel is not None:
        v.panel.cancelar()
    if not hasattr(v, "_perfil_prueba"):
        v._perfil_prueba = _perfil(v)
    p = v.ejecutar_comando(Extruir(), valores={"perfiles": [v._perfil_prueba]})
    QTest.qWait(30)
    return p


def _evento(w, tipo, global_):
    QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(w.mapFromGlobal(global_)), QPointF(global_), Qt.LeftButton,
                                          Qt.LeftButton, Qt.NoModifier))


def _arrastrar(p, dx, dy):
    from omnicad.ui.superposiciones import CabeceraMovible
    cab = p.findChild(CabeceraMovible)
    ini = cab.mapToGlobal(QPoint(30, 8))
    _evento(cab, QEvent.MouseButtonPress, ini)
    for i in range(1, 6):
        _evento(cab, QEvent.MouseMove, ini + QPoint(dx * i // 5, dy * i // 5))
    _evento(cab, QEvent.MouseButtonRelease, ini + QPoint(dx, dy))


def _botones_sin_tapar(v, p):
    barra = v.area.barra.geometry()
    cancelar = next(b for b in p.findChildren(type(p.boton_ok)) if b.text() == "Cancelar")
    return all(v.area.rect().contains(b.mapTo(v.area, b.rect().bottomRight())) for b in (p.boton_ok, cancelar)) \
        and not barra.intersects(p.geometry())


def test_arrastrar_la_cabecera_mueve_el_panel_y_lo_deja_dentro_de_la_vista(ventana):
    v = ventana
    p = _abrir(v)
    base, tamano = p.pos(), p.size()
    _arrastrar(p, -300, 40)
    assert p.pos() != base and p.size() == tamano and v.area.rect().contains(p.geometry())
    _arrastrar(p, -9000, 9000)                       # más allá de cualquier borde: se queda dentro y sin tapar sus botones
    assert v.area.rect().contains(p.geometry()) and _botones_sin_tapar(v, p)
    _arrastrar(p, 9000, -9000)
    assert v.area.rect().contains(p.geometry()) and p.x() + p.width() <= v.area.width()


def test_la_posicion_se_recuerda_en_el_panel_siguiente_y_en_la_preferencia(tmp_path):
    ini = tmp_path / "p.ini"
    v = _ventana(ini)
    p = _abrir(v)
    _arrastrar(p, -260, 30)
    esquina = (p.x() + p.width(), p.y())
    guardado = v.prefs[CLAVE_PREF]
    assert guardado.count(",") == 1
    p2 = _abrir(v)                                   # el panel siguiente abre en el mismo lugar (anclado al borde derecho)
    assert (p2.x() + p2.width(), p2.y()) == esquina
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    v2 = _ventana(ini)                               # y la ventana siguiente también
    p3 = _abrir(v2)
    assert (p3.x() + p3.width(), p3.y()) == esquina and v2.prefs[CLAVE_PREF] == guardado
    v2.doc.modificado = False
    v2.close()
    v2.deleteLater()


def test_un_clic_suelto_no_borra_y_el_doble_clic_vuelve_a_su_lugar(ventana):
    from omnicad.ui.superposiciones import CabeceraMovible
    v = ventana
    p = _abrir(v)
    lugar = p.pos()
    _arrastrar(p, -250, 30)
    guardado = v.prefs[CLAVE_PREF]
    cab = p.findChild(CabeceraMovible)
    QTest.mouseClick(cab, Qt.LeftButton, Qt.NoModifier, QPoint(30, 8))
    assert v.prefs[CLAVE_PREF] == guardado and p.pos() != lugar
    _evento(cab, QEvent.MouseButtonDblClick, cab.mapToGlobal(QPoint(30, 8)))
    QTest.qWait(10)
    assert v.prefs[CLAVE_PREF] == "" and v.area.posicion_panel is None and p.pos() == lugar


def test_al_achicar_la_ventana_el_panel_recordado_entra_y_sus_botones_se_ven(ventana):
    v = ventana
    p = _abrir(v)
    _arrastrar(p, -200, 9000)
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        QTest.qWait(30)
        assert v.area.rect().contains(p.geometry()) and _botones_sin_tapar(v, p), (ancho, alto)


def test_esc_cancela_el_panel_movido(ventana):
    v = ventana
    p = _abrir(v)
    _arrastrar(p, -200, 20)
    QTest.keyClick(p.widgets["distancia"], Qt.Key_Escape)       # Tab se prueba en la ventana real: scripts/prueba_ui/panel_movible.py
    assert v.panel is None


def test_los_preajustes_van_en_la_cabecera_y_no_ocupan_una_fila(ventana):
    p = _abrir(ventana)
    cab = p.boton_preajustes.parentWidget()
    assert cab.objectName() == "cabecera_comando" and cab.geometry().contains(p.boton_preajustes.geometry())
    assert p.desplazador.y() <= cab.y() + cab.height() + 2          # el cuerpo empieza pegado a la cabecera: sin fila de 36 px


def test_ninguna_seleccion_vive_en_mas_opciones():
    """UI-7: una selección nunca es avanzada (si se preelige algo antes del comando, no puede caer en un campo plegado)."""
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, Seleccion
    from omnicad.ui.comandos import CATALOGO
    ctx = ContextoComando(Documento())
    malas, vistos = [], 0
    for clave, clase in sorted(CATALOGO.items()):
        try:
            campos = clase().campos(ctx)
        except Exception:  # noqa: BLE001 — los que piden un documento armado los cubre pieza panel_movible de scripts/prueba_ui
            continue
        vistos += 1
        malas += [f"{clave}.{c.clave}" for c in campos if isinstance(c, Seleccion) and c.avanzado]
    assert vistos > 100, vistos                      # que el «except» no deje la comprobación vacía
    assert not malas, malas


def test_el_panel_de_render_no_hereda_el_lugar_del_panel_de_comando(ventana):
    """El lugar recordado es de los paneles de comando: los de render no tienen cabecera movible."""
    from PySide6.QtWidgets import QFrame
    v = ventana
    p = _abrir(v)
    _arrastrar(p, -300, 30)
    p.cancelar()
    otro = QFrame(v.area)
    v.area.set_panel(otro)
    otro.show()
    v.area.reubicar()
    assert v.area._posicion_fija_panel(v.visor.geometry()) is None
    assert otro.x() + otro.width() == v.area.visor.geometry().right() - 10     # el lugar de siempre: a la derecha del ViewCube
    v.area.set_panel(None)
    otro.deleteLater()
