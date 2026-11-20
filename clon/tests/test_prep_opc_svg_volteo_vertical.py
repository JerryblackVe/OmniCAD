# -*- coding: utf-8 -*-
"""Opción «Volteo vertical (Casilla)» de «Insertar SVG en boceto», sin test automático en la tabla
`docs/seguimiento/preparado/opciones_asas_boceto.md` (PREP-OPCIONES-BOCETO).

Fusion (docs/fusion_docs › Design: Solid › Insert tools › «Add an SVG image»): «Vertical Flip: mirrors geometry
using the X axis»; ahí el dibujo entra centrado en el origen, así que ese eje pasa por el centro de la caja del
dibujo y lo que se ve es un espejo que deja el dibujo en su sitio (arriba ↔ abajo). OmniCAD inserta con las
coordenadas del archivo y voltea alrededor del centro de la caja (`boceto_archivos.boceto_desde_primitivas`):
mismo resultado visible. Un valor numérico (dibujo asimétrico: el círculo de arriba pasa abajo) y el borde
(dibujo simétrico respecto del eje del espejo: el volteo es la identidad).
"""
import os

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402

PLANO = g.Plano("XY")


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False                  # si no, al cerrar pregunta si se descartan los cambios (modal)
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana):
    """La ventana con un documento nuevo y sin boceto ni panel abiertos."""
    ventana.set_documento(Documento())
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()


def _svg(tmp_path, cy, nombre):
    """Rectángulo 40×20 de borde + círculo de r 2 en x=10. `cy` es la Y del SVG (apunta hacia abajo: el
    lector la invierte, CAD y = 20 − cy; svg.py › `Y = alto - (y - y0)`)."""
    ruta = tmp_path / nombre
    ruta.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
                    '<rect x="0" y="0" width="40" height="20" fill="none" stroke="#000"/>'
                    f'<circle cx="10" cy="{cy}" r="2" fill="none" stroke="#000"/></svg>', encoding="utf-8")
    return ruta


def _insertar(v, ruta):
    """Boceto XY abierto y panel de «Insertar SVG en boceto» con el archivo cargado (como el usuario)."""
    from omnicad.ui.comandos import CATALOGO
    mb = v.modo_boceto
    mb.iniciar(Boceto(), PLANO, {"op": None, "plano": "XY", "marco": None, "cara": None})
    panel = v.ejecutar_comando(CATALOGO["insertar_svg"](), valores={"archivo": str(ruta)})
    return mb.lienzo, panel


def _puntos(lz):
    return sorted(tuple(lz.b.coords(p)) for p in lz.b.puntos)


# ---------------------------------------------------------------- valor numérico (dibujo asimétrico)
def test_volteo_vertical_espeja_el_dibujo_en_su_sitio(v, tmp_path):
    """El círculo de arriba pasa abajo — (10, 15) → (10, 5), espejado alrededor de la línea y = 10 del
    centro de la caja — y la caja del dibujo no se mueve. La casilla mueve la vista previa y el insert
    entra en UN paso de deshacer, como cualquier cambio del boceto."""
    lz, panel = _insertar(v, _svg(tmp_path, 5, "asimetrico.svg"))     # SVG cy=5 → CAD y=15 (arriba)
    casilla = panel.widgets["voltear_v"]
    campo = next(c for c in panel.campos if c.clave == "voltear_v")
    assert isinstance(casilla, QCheckBox) and campo.etiqueta == "Volteo vertical" and not casilla.isChecked()
    panel._calcular_previa()
    sin = v.visor._capas["previa_insertar"][0][1].copy()
    panel.set_valor("voltear_v", True)
    assert casilla.isChecked() and panel.valores["voltear_v"] is True
    panel._calcular_previa()
    con = v.visor._capas["previa_insertar"][0][1]
    assert not np.allclose(sin, con)                                  # la vista previa sigue a la casilla
    assert np.allclose(sin.min(0), con.min(0)) and np.allclose(sin.max(0), con.max(0))
    antes = lz.b.a_dict()
    panel.aceptar()
    assert v.panel is None and len(lz.historial) == 1                 # todo el dibujo, un solo deshacer
    tipos = [type(c).__name__ for c in lz.b.curvas.values()]
    assert tipos.count("Linea") == 4 and tipos.count("Circulo") == 1
    circ = next(c for c in lz.b.curvas.values() if type(c).__name__ == "Circulo")
    assert lz.b.coords(circ.centro) == pytest.approx((10.0, 5.0)) and circ.radio == pytest.approx(2.0)
    assert _puntos(lz) == sorted([(0.0, 0.0), (40.0, 0.0), (0.0, 20.0), (40.0, 20.0), (10.0, 5.0)])
    lz.deshacer()
    assert lz.b.a_dict() == antes


# ---------------------------------------------------------------- borde (dibujo simétrico)
def test_volteo_vertical_de_un_dibujo_simetrico_no_lo_mueve(v, tmp_path):
    """Borde: el eje del espejo pasa por el centro de la caja; un círculo centrado en ese eje (y = 10) y
    un rectángulo simétrico quedan igual — marcar la casilla no cambia la geometría insertada."""
    lz, panel = _insertar(v, _svg(tmp_path, 10, "simetrico.svg"))     # SVG cy=10 → CAD y=10 (en el eje)
    panel.set_valor("voltear_v", True)
    panel._calcular_previa()
    assert len(v.visor._capas["previa_insertar"][0][1]) > 0
    panel.aceptar()
    assert len(lz.b.curvas) == 5
    assert _puntos(lz) == sorted([(0.0, 0.0), (40.0, 0.0), (0.0, 20.0), (40.0, 20.0), (10.0, 10.0)])
