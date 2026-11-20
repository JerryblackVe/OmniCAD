# -*- coding: utf-8 -*-
"""PREP-OPC: «Volteo horizontal (Casilla)» de Insertar SVG en boceto.

Fusion 360 › Insert › Insert SVG [SLD-INS-SVG], artículo «Add an SVG image»: «Horizontal Flip
mirrors geometry using the Y axis» con el dibujo centrado en el origen del boceto. El lector de SVG
deja la esquina inferior izquierda en el origen (`svg._recorrer`), así que el espejo cruza los
extremos en X sin mover el borde del dibujo."""
import os

import pytest

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm" viewBox="0 0 10 10">
  <line x1="0" y1="0" x2="10" y2="4"/>
</svg>"""


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def svg(tmp_path):
    ruta = tmp_path / "asimetrico.svg"
    ruta.write_text(SVG, encoding="utf-8")
    return ruta


def _boceto(app_qt, svg, voltear_h):
    """Boceto que deja `InsertarSVG.construir` con la casilla `voltear_h` en el valor pedido."""
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.insertar import InsertarSVG
    doc = Documento()
    ctx = ContextoComando(doc)
    hit = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    cmd = InsertarSVG()
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    v.update(plano=[hit], archivo=str(svg), voltear_h=voltear_h)
    return cmd.construir(v, ctx).boceto


def _linea(b):
    """((x1, y1), (x2, y2)) de la única línea del boceto."""
    (prim,) = [p for p in b.geometria() if p[0] == "linea"]
    return tuple(map(tuple, prim[2:4]))


def _borde(b):
    """(xmin, ymin, xmax, ymax) de toda la geometría del boceto."""
    from omnicad.restricciones.objetos import limites_primitiva
    cajas = [limites_primitiva(p) for p in b.geometria()]
    return (min(c[0] for c in cajas), min(c[1] for c in cajas),
            max(c[2] for c in cajas), max(c[3] for c in cajas))


def test_el_volteo_horizontal_cruza_los_extremos_en_x(app_qt, svg):
    a1, a2 = _linea(_boceto(app_qt, svg, voltear_h=False))
    b1, b2 = _linea(_boceto(app_qt, svg, voltear_h=True))
    assert a1 == pytest.approx((0.0, 10.0)) and a2 == pytest.approx((10.0, 6.0))
    # valor numérico: el extremo de x=0 pasa a x=10 y el de x=10 a x=0; y queda igual en ambos
    assert b1 == pytest.approx((10.0, 10.0)) and b2 == pytest.approx((0.0, 6.0))


def test_el_volteo_horizontal_no_mueve_el_borde_del_dibujo(app_qt, svg):
    """El espejo no corre ni agranda el dibujo: la caja queda en los mismos bordes."""
    assert _borde(_boceto(app_qt, svg, voltear_h=False)) == pytest.approx((0.0, 6.0, 10.0, 10.0))
    assert _borde(_boceto(app_qt, svg, voltear_h=True)) == pytest.approx((0.0, 6.0, 10.0, 10.0))
