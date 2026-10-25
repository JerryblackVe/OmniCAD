# -*- coding: utf-8 -*-
"""Fase 9 del Boceto 3D, interfaz (FU-1): la tríada arrastrable en la vista (planos, ejes, asas de giro) y el dibujo,
la selección y el arrastre de geometría 3D con el ratón. Eventos de ratón simulados sobre el lienzo (offscreen)."""
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.restricciones import boceto3d as b3  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto  # noqa: E402
from omnicad.ui.triada3d import Triada  # noqa: E402
from test_p23_navegador import v as v, ventana as ventana  # noqa: E402, F401


def test_triada_pura_plano_eje_y_giro():
    t = Triada()
    t.plano = "yz"
    p = t.punto_en_plano(np.array([5.0, 3, 4]), np.array([-1.0, 0, 0]))
    assert np.allclose(p, (0, 3, 4))
    # rayo que pasa por (0, 0, 7) perpendicular al eje z: el parámetro sobre z es 7
    assert t.parametro_en_eje(2, np.array([10.0, 0, 7]), np.array([-1.0, 0, 0])) == pytest.approx(7)
    t.girar(2, math.pi / 2)
    assert np.allclose(t.R[0], (0, 1, 0), atol=1e-12) and np.allclose(t.R[2], (0, 0, 1))
    t.ciclar_plano()
    assert t.plano == "zx"
    t.reiniciar_orientacion()
    assert np.allclose(t.R, np.identity(3))


def _evento(lz, tipo, pos, boton=Qt.LeftButton):
    botones = Qt.NoButton if tipo == QEvent.MouseButtonRelease else boton
    ev = QMouseEvent(tipo, QPointF(pos), lz.mapToGlobal(QPointF(pos)), boton if tipo != QEvent.MouseMove else
                     Qt.NoButton, botones, Qt.NoModifier)
    QApplication.sendEvent(lz, ev)


def _clic(lz, pos):
    _evento(lz, QEvent.MouseButtonPress, pos)
    _evento(lz, QEvent.MouseButtonRelease, pos)


def _arrastrar(lz, a, b):
    _evento(lz, QEvent.MouseButtonPress, a)
    for f in (0.3, 0.6, 1.0):
        _evento(lz, QEvent.MouseMove, QPointF(a.x() + (b.x() - a.x()) * f, a.y() + (b.y() - a.y()) * f))
    _evento(lz, QEvent.MouseButtonRelease, b)


@pytest.fixture
def boceto3d(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Ruta 3D", plano="XY", boceto=Boceto()))
    assert PuenteAgentes(v, archivo=tmp_path / "puente.json").ejecutar("sketch_view", {"sketch": ident,
                                                                                         "action": "edit"})["ok"]
    m = v.modo_boceto
    m.paleta.checks["boceto3d"].setChecked(True)
    visor = v.visor
    visor.vista("iso")
    visor.objetivo, visor.distancia = np.zeros(3), 200.0
    QApplication.processEvents()
    return m


def _herramienta(m, clave):
    m.paleta.h3d.setCurrentIndex(m.paleta.h3d.findData(clave))


def test_dibuja_una_linea_con_dos_clics_y_la_triada_se_muda(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "linea")
    _clic(m.lienzo, it.a_pantalla((20, 10, 0)))
    _clic(m.lienzo, it.a_pantalla((40, 30, 0)))
    g = m.boceto.geo3d
    (curva,) = g["curvas"].values()
    p, q = (np.array(g["puntos"][i]) for i in curva["puntos"])
    assert np.allclose(p, (20, 10, 0), atol=0.05) and np.allclose(q, (40, 30, 0), atol=0.05)
    assert np.allclose(it.triada.origen, q)                          # la tríada pasa al último punto
    m.lienzo.deshacer()                                              # Ctrl+Z deshace lo dibujado con el ratón
    assert not m.boceto.geo3d.get("curvas")


def test_clic_en_un_plano_de_la_triada_lo_activa_y_dibuja_fuera_del_plano(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "punto")
    esquinas = it.triada.asas(it._largo())[("plano", "yz")]
    _clic(m.lienzo, it.a_pantalla(np.mean(esquinas, axis=0)))
    assert it.triada.plano == "yz"
    _clic(m.lienzo, it.a_pantalla((0, 15, 25)))                       # sobre el plano YZ: fuera del plano del boceto
    (p,) = m.boceto.geo3d["puntos"].values()
    assert np.allclose(p, (0, 15, 25), atol=0.05)


def test_arrastrar_el_eje_z_sube_la_triada(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    largo = it._largo()
    a = it.a_pantalla((0, 0, 0.8 * largo))
    b = it.a_pantalla((0, 0, 0.8 * largo + 30))
    _arrastrar(m.lienzo, a, b)
    assert np.allclose(it.triada.origen, (0, 0, 30), atol=0.3)


def test_arrastrar_el_asa_de_giro_rota_la_triada(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    arco, asa = it.triada.asas(it._largo())[("giro", 2)]
    r = np.linalg.norm(asa)
    a0 = math.atan2(asa[1], asa[0])
    destino = (r * math.cos(a0 + math.radians(30)), r * math.sin(a0 + math.radians(30)), 0)
    _arrastrar(m.lienzo, it.a_pantalla(asa), it.a_pantalla(destino))
    angulo = math.degrees(math.atan2(it.triada.R[0][1], it.triada.R[0][0]))
    assert angulo == pytest.approx(30, abs=0.5)
    assert np.allclose(it.triada.R @ it.triada.R.T, np.identity(3), atol=1e-9)
    m.paleta.b_triada.click()                                        # «Restablecer orientación de la tríada»
    assert np.allclose(it.triada.R, np.identity(3))


def test_seleccionar_y_arrastrar_un_punto_3d(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    cid = b3.agregar_linea(m.boceto, (0, 0, 0), (30, 0, 0))
    m._cambio()
    _herramienta(m, "seleccionar")
    fin = m.boceto.geo3d["curvas"][cid]["puntos"][1]
    _arrastrar(m.lienzo, it.a_pantalla((30, 0, 0)), it.a_pantalla((30, 20, 0)))
    assert it.seleccion == [fin]
    assert np.allclose(m.boceto.geo3d["puntos"][fin], (30, 20, 0), atol=0.05)
    m.lienzo.deshacer()
    assert np.allclose(m.boceto.geo3d["puntos"][fin], (30, 0, 0))
    pasos = len(m.lienzo.historial)
    _clic(m.lienzo, it.a_pantalla((30, 0, 0)))                        # elegir sin mover: no deja paso de deshacer
    assert len(m.lienzo.historial) == pasos


def test_arrastrar_una_curva_respeta_las_restricciones(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    cid = b3.agregar_linea(m.boceto, (0, 20, 0), (30, 20, 0))       # lejos de los ejes de la tríada (mandan ellos)
    b3.agregar_restriccion(m.boceto, "eje", [cid], eje="x")
    m._cambio()
    _herramienta(m, "seleccionar")
    _arrastrar(m.lienzo, it.a_pantalla((20, 20, 0)), it.a_pantalla((20, 30, 0)))
    assert it.seleccion == [cid]
    p, q = (np.array(m.boceto.geo3d["puntos"][i]) for i in m.boceto.geo3d["curvas"][cid]["puntos"])
    assert np.allclose([p[1], q[1]], 30, atol=0.05) and abs(p[1] - q[1]) < 1e-6   # sigue paralela a X
    assert q[0] - p[0] == pytest.approx(30, abs=1e-6)


def test_circulo_y_rectangulo_con_el_raton(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "circulo")
    _clic(m.lienzo, it.a_pantalla((0, 0, 0)))
    _clic(m.lienzo, it.a_pantalla((6, 8, 0)))                         # fuera de los ejes de la tríada
    (c,) = m.boceto.geo3d["curvas"].values()
    assert c["tipo"] == "circulo" and c["radio"] == pytest.approx(10, abs=0.05)
    _herramienta(m, "rectangulo")
    _clic(m.lienzo, it.a_pantalla((40, 0, 0)))
    _clic(m.lienzo, it.a_pantalla((60, 15, 0)))
    lineas = [k for k, d in m.boceto.geo3d["curvas"].items() if d["tipo"] == "linea"]
    assert len(lineas) == 4


def test_spline_termina_con_intro_y_esc_cancela(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "spline")
    for p in ((0, 0, 0), (10, 10, 0), (20, 0, 0)):
        _clic(m.lienzo, it.a_pantalla(p))
    assert not m.boceto.geo3d.get("curvas") and len(it.picks) == 3
    it.tecla(Qt.Key_Return)
    (c,) = m.boceto.geo3d["curvas"].values()
    assert c["tipo"] == "spline" and len(c["puntos"]) == 3
    _clic(m.lienzo, it.a_pantalla((30, 0, 0)))
    it.tecla(Qt.Key_Escape)
    assert it.picks == []


def test_boton_derecho_y_medio_siguen_navegando(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "punto")
    _evento(m.lienzo, QEvent.MouseButtonPress, it.a_pantalla((10, 10, 0)), Qt.MiddleButton)
    _evento(m.lienzo, QEvent.MouseButtonRelease, it.a_pantalla((10, 10, 0)), Qt.MiddleButton)
    assert not m.boceto.geo3d.get("puntos")
