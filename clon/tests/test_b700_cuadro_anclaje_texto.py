# -*- coding: utf-8 -*-
"""B-700: con el cuadro dibujado (2 clics), el «Anclaje» del panel Carácter se guarda y ancla el texto
en el borde del cuadro que pide (Fusion aplica la alineación vertical dentro del marco)."""
import os

import pytest


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("ancla, y", [("base", 0.0), ("arriba", 20.0), ("medio", 10.0), ("abajo", 0.0)])
def test_el_cuadro_respeta_el_anclaje_del_panel(app_qt, ancla, y):
    """E7 (PRUEBA-TEXTO-SIM): con el cuadro, 3 de 4 anclajes no se guardaban: quedaban en «arriba»."""
    from test_texto_vectores import _lienzo_con_cuadro
    b, lz = _lienzo_con_cuadro("HH")                 # cuadro dibujado de (0, 0) a (80, 20)
    lz.opciones["ancla_v"] = ancla                    # lo que deja elegir el panel Carácter a mitad de edición
    lz.entrada.aceptado.emit(["HH", "20", "0", "0", "1"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.ancla_v == ancla                         # se guarda lo elegido (antes: siempre «arriba»)
    assert t.ancho_caja == pytest.approx(80.0)
    assert b.coords(t.punto) == pytest.approx((0.0, y))   # el borde del cuadro que pide el anclaje
    lz.close()
    lz.deleteLater()


def test_el_anclaje_elegido_antes_de_dibujar_queda_en_el_borde(app_qt):
    """El Anclaje ya elegido al dibujar el cuadro: la previa nace anclada en su borde y aceptar no la mueve."""
    from test_texto_vectores import _lienzo_con_cuadro
    b, lz = _lienzo_con_cuadro("", clics=((0.0, 0.0),))    # primera esquina; la segunda va con el Anclaje ya puesto
    lz.opciones["ancla_v"] = "medio"
    lz.clics.append((None, (80.0, 20.0)))
    lz._procesar_clics()
    assert lz._previa_texto["pos"] == pytest.approx((0.0, 10.0))
    lz.entrada.aceptado.emit(["HH", "20", "0", "0", "1"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert (t.ancla_v, b.coords(t.punto)) == ("medio", pytest.approx((0.0, 10.0)))
    lz.close()
    lz.deleteLater()
