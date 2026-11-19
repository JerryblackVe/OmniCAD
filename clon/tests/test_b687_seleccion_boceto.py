# -*- coding: utf-8 -*-
"""B-687: los modos de selección por región de la cinta respetan el boceto abierto."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto


@pytest.fixture
def ventana(tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    b.agregar_rectangulo((-40, 0), (-20, 10))
    doc = Documento()
    doc.agregar(OpBoceto("sk", "Boceto1", boceto=b, plano="XY"))
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    app.processEvents()
    v.editar_operacion("sk")
    app.processEvents()
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("clave", ["sel_ventana", "sel_libre"])
def test_modo_seleccion_no_cierra_el_boceto(ventana, clave):
    assert ventana.modo_boceto.activo
    ventana.acciones[clave].trigger()
    QApplication.processEvents()
    assert ventana.modo_boceto.activo, f"{clave} cerró el boceto"
    assert ventana.visor.modo is None, f"{clave} dejó el visor en selección 3D"
    assert ventana.modo_boceto.lienzo.herramienta == "seleccionar", f"{clave} no eligió la geometría del boceto"
