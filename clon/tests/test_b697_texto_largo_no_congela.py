# -*- coding: utf-8 -*-
"""B-697: aceptar un texto de 400 letras no congela la ventana (~1,4 s): el relleno en vivo de un texto
largo no se pinta (tope de primitivas de texto, como el tope de perfiles del boceto terminado);
Extruir sigue calculando sus perfiles."""
import time

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
    doc = Documento()
    doc.agregar(OpBoceto("sk", "Boceto1", boceto=Boceto(), plano="XY"))
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


def _texto(lz, contenido):
    """Crea un texto como la herramienta Texto de la ventana: dos clics, contenido y aceptar."""
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -10.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    lz.entrada.campos[0].setText(contenido)
    lz.entrada.aceptado.emit([contenido, "20", "0", "0", "1"])


def test_b697_un_texto_largo_no_congela_la_ventana_al_aceptarlo(ventana):
    lz = ventana.modo_boceto.lienzo
    # un texto corto se rellena como siempre (y deja la fuente cargada para el largo)
    _texto(lz, "HOLA")
    ventana.modo_boceto._actualizar_perfiles()
    assert len(ventana.visor._perfiles) > 0
    # el caso del bug: 400 letras tardaban ~1,4 s de relleno y bloqueaban la ventana
    t0 = time.perf_counter()
    _texto(lz, "X" * 400)
    ventana.modo_boceto._actualizar_perfiles()      # lo que el temporizador corre al aceptar, en el hilo de la ventana
    dt = time.perf_counter() - t0
    assert dt < 1.0, f"aceptar 400 letras bloqueó la ventana {dt:.2f} s"
    assert len(ventana.visor._perfiles) == 0         # el relleno del texto largo no se pinta (B-697)
