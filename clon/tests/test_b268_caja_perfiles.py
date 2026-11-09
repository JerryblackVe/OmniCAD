# -*- coding: utf-8 -*-
"""B-268: una caja en la vista elige perfiles, dentro de Extruir y antes de abrirlo (Fusion: una caja sobre el dibujo,
E, 3 y Enter). Antes la caja no elegía ningún perfil y Gerardo tuvo que hacer 17 clics."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto  # noqa: E402


@pytest.fixture(scope="module")
def v(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (30, 20))
    b.agregar_circulo((15, 10), 4)              # el disco y el anillo que deja en el rectángulo
    b.agregar_rectangulo((40, 0), (50, 20))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    ruta = tmp_path_factory.mktemp("b268") / "preferencias.ini"
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1500, 900)
    v.show()
    QTest.qWait(1)
    v.visor.vista("arriba")          # de arriba: un rectángulo de pantalla es un rectángulo del plano XY
    QTest.qWait(10)
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()


def _arrastrar(visor, desde, hasta):
    """Como una persona: apretar, varios movimientos y soltar (eventos al widget, no el cursor real)."""
    def ev(tipo, p, boton, botones):
        p = QPointF(*p)
        QApplication.sendEvent(visor, QMouseEvent(tipo, p, visor.mapToGlobal(p), boton, botones, Qt.NoModifier))
    ev(QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, 6):
        ev(QEvent.MouseMove, [a + (b - a) * k / 5 for a, b in zip(desde, hasta, strict=True)], Qt.NoButton, Qt.LeftButton)
    ev(QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


def _todo(visor):
    return (3, 3), (visor.width() - 3, visor.height() - 3)


def test_b268_caja_dentro_de_extruir_elige_todos_los_perfiles(v):
    from omnicad.ui.comandos import CATALOGO
    import numpy as np
    p = v.ejecutar_comando(CATALOGO["extruir"]())
    QTest.qWait(10)
    try:
        assert v.visor.ventana_en_comando
        _arrastrar(v.visor, *_todo(v.visor))
        perfiles = p.valores["perfiles"]
        assert len(perfiles) == 3 and {h["ref"]["tipo"] for h in perfiles} == {"perfil"}
        _arrastrar(v.visor, *_todo(v.visor))                    # otra vez: no duplica
        assert len(p.valores["perfiles"]) == 3
        p._limpiar(p.activa)
        # una ventana de cruce (de derecha a izquierda) que solo toca el rectángulo de la derecha
        q0, q1 = v.visor.proyectar(np.array([52.0, 22.0, 0.0])), v.visor.proyectar(np.array([45.0, 10.0, 0.0]))
        _arrastrar(v.visor, (q0.x(), q0.y()), (q1.x(), q1.y()))
        assert len(p.valores["perfiles"]) == 1
    finally:
        p.cancelar()


def test_b268_caja_antes_de_extruir_lo_abre_con_los_perfiles(v):
    from omnicad.ui.comandos import CATALOGO
    assert v.panel is None
    _arrastrar(v.visor, *_todo(v.visor))
    assert sum(h["ref"]["tipo"] == "perfil" for h in v.seleccion) == 3
    p = v.ejecutar_comando(CATALOGO["extruir"]())
    QTest.qWait(10)
    assert len(p.valores["perfiles"]) == 3
    p.cancelar()
