# -*- coding: utf-8 -*-
"""B-105: en una ventana chica el panel de un comando entra en el visor (con barra) y Aceptar/Cancelar se ven."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("panel_chico")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _perfil(v):
    from omnicad.restricciones import Boceto
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    v.doc.agregar(OpBoceto(v.doc.nuevo_id(), "Boceto1", boceto=b))
    paso = v.doc.operaciones[-1]
    datos = v.doc.estado_final.bocetos[paso.id].perfiles[0]
    return hit_desde_ref({"tipo": "perfil", "boceto": paso.id, **OpExtrusion.referencia_perfil(datos)},
                         v.doc.estado_final)


@pytest.mark.parametrize("ancho,alto", [(1024, 640), (800, 520)])
def test_panel_de_comando_entra_en_el_visor_y_los_botones_se_ven(ventana, ancho, alto):
    from omnicad.ui.comandos.solido import Extruir
    v = ventana
    if not hasattr(v, "_perfil_b105"):
        v._perfil_b105 = _perfil(v)
    perfil = v._perfil_b105
    v.resize(ancho, alto)
    QTest.qWait(30)
    p = v.ejecutar_comando(Extruir(), valores={"perfiles": [perfil]})
    assert p is not None
    QTest.qWait(30)
    marco = v.area.rect()
    assert marco.contains(p.geometry()), (ancho, alto, p.geometry().getRect(), marco.getRect())
    cancelar = next(b for b in p.findChildren(type(p.boton_ok)) if b.text() == "Cancelar")
    for boton in (p.boton_ok, cancelar):
        assert marco.contains(boton.mapTo(v.area, boton.rect().bottomRight())), (ancho, alto, boton.text())
    p.cancelar()
    QTest.qWait(10)
