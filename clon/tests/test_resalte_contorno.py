# -*- coding: utf-8 -*-
"""Resalte de la selección como CONTORNO mientras se elige un aspecto: el relleno translúcido tapaba el color real."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui.visor3d import contorno_de_triangulos

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def _segmentos_distintos(seg):
    """Cantidad de segmentos sin repetir (cada uno sin importar el sentido)."""
    pares = seg.reshape(-1, 2, 3).round(3)
    return len({tuple(sorted(map(tuple, p))) for p in pares})


# ---------------------------------------------------------------- la función pura
def test_el_contorno_de_una_caja_son_sus_12_aristas_sin_las_diagonales_de_las_caras():
    tris, _n = geo.teselar(geo.caja(100, 60, 20))
    seg = contorno_de_triangulos(tris)
    assert len(seg) == 24 and _segmentos_distintos(seg) == 12                  # 12 aristas × 2 puntos
    assert seg.dtype == np.float32
    assert seg.min(axis=0) == pytest.approx([0, 0, 0]) and seg.max(axis=0) == pytest.approx([100, 60, 20])


def test_el_contorno_de_una_cara_es_su_borde_y_el_de_un_cilindro_no_muestra_las_facetas():
    caja = geo.caja(10, 10, 10)
    cara = next(c for c in geo.caras(caja) if geo.plano_de_cara(c) is not None
                and abs(geo.plano_de_cara(c).normal[2]) > 0.9)
    tris, _n = geo.teselar(cara)
    assert _segmentos_distintos(contorno_de_triangulos(tris)) == 4              # el cuadrado, sin la diagonal
    cil, _n = geo.teselar(geo.cilindro(10, 30))
    seg = contorno_de_triangulos(cil)
    # los dos círculos de las tapas y las costuras: nada de una arista por faceta de la pared
    assert 0 < len(seg) // 2 < len(cil) // 3
    assert seg.min(axis=0)[2] == pytest.approx(0) and seg.max(axis=0)[2] == pytest.approx(30)


def test_sin_triangulos_no_hay_contorno_y_un_triangulo_suelto_tiene_tres_lados():
    assert contorno_de_triangulos(np.zeros((0, 3), np.float32)).shape == (0, 3)
    uno = np.array([[0, 0, 0], [5, 0, 0], [0, 5, 0]], np.float32)
    assert _segmentos_distintos(contorno_de_triangulos(uno)) == 3


# ---------------------------------------------------------------- el visor
@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("contorno") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1500, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_el_visor_dibuja_el_contorno_y_guarda_el_calculo(ventana):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    ventana.set_documento(s.doc)
    visor = ventana.visor
    tris = visor.triangulos_cuerpo(next(iter(s.doc.estado_final.cuerpos)))
    assert not visor.resalte_contorno
    visor.set_resalte_contorno(True)
    primero = visor._contorno(tris)
    assert visor._contorno(tris) is primero and len(primero) == 24            # el cálculo se hace una vez
    visor.set_resalte_contorno(False)
    assert not visor.resalte_contorno
    s.doc.modificado = False


def test_aspecto_en_diseno_resalta_con_contorno_mientras_esta_abierto(ventana):
    from omnicad.ui.comandos import CATALOGO
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    ventana.set_documento(s.doc)
    ventana.ejecutar_comando(CATALOGO["aspecto"]())
    assert ventana.panel is not None and ventana.visor.resalte_contorno
    ventana.panel.cancelar()
    assert not ventana.visor.resalte_contorno
    s.doc.modificado = False


def test_aspecto_en_render_resalta_con_contorno_solo_con_el_panel_abierto(app_qt):
    from omnicad.ui.render import VentanaRender
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    v = VentanaRender(s.doc)
    assert not v.lienzo.resalte_contorno
    v.mostrar_aspecto()
    assert v.lienzo.resalte_contorno
    v.panel_aspecto.cerrar()
    assert not v.lienzo.resalte_contorno
    s.doc.modificado = False
    v.close()
