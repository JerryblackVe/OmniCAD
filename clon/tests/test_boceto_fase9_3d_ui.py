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


@pytest.mark.parametrize("asa", ["giro", "eje"])
def test_clic_de_dibujo_sobre_un_asa_pone_el_punto_y_arrastrar_la_sigue_moviendo(boceto3d, asa):
    """B-120. Fusion gira y mueve la tríada al arrastrar un asa; un clic dibuja, con un poco de temblor incluido."""
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "spline")
    tri = it.triada
    sobre = tri.asas(it._largo())[("giro", 2)][1] if asa == "giro" else (0.8 * it._largo(), 0, 0)
    a = it.a_pantalla(sobre)
    assert it.asa_en(a) is not None
    _evento(m.lienzo, QEvent.MouseButtonPress, a)
    _evento(m.lienzo, QEvent.MouseMove, QPointF(a.x() + 2, a.y() + 1))
    _evento(m.lienzo, QEvent.MouseButtonRelease, a)
    assert len(it.picks) == 1 and np.allclose(it.picks[0], (sobre[0], sobre[1], 0), atol=0.05)
    assert np.allclose(tri.origen, it.picks[0]) and np.allclose(tri.R, np.identity(3))
    b = it.a_pantalla(tri.asas(it._largo())[("giro", 2)][1])
    _arrastrar(m.lienzo, b, QPointF(b.x() - 40, b.y() + 30))
    assert len(it.picks) == 1 and not np.allclose(tri.R, np.identity(3))


@pytest.mark.parametrize("asa", ["giro", "eje"])
def test_esc_con_el_boton_sobre_un_asa_no_pone_el_punto_al_soltar(boceto3d, asa):
    """Esc con el botón apretado sobre un asa cancela el clic: al soltar no queda el punto recordado."""
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "spline")
    sobre = it.triada.asas(it._largo())[("giro", 2)][1] if asa == "giro" else (0.8 * it._largo(), 0, 0)
    a = it.a_pantalla(sobre)
    _evento(m.lienzo, QEvent.MouseButtonPress, a)
    assert it._clic_asa is not None
    it.tecla(Qt.Key_Escape)
    assert it._clic_asa is None
    _evento(m.lienzo, QEvent.MouseButtonRelease, a)
    assert it.picks == [] and not m.boceto.geo3d.get("puntos")
    _clic(m.lienzo, a)                                                  # sin Esc, el mismo clic sí pone el punto
    assert len(it.picks) == 1


def test_boton_derecho_y_medio_siguen_navegando(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "punto")
    _evento(m.lienzo, QEvent.MouseButtonPress, it.a_pantalla((10, 10, 0)), Qt.MiddleButton)
    _evento(m.lienzo, QEvent.MouseButtonRelease, it.a_pantalla((10, 10, 0)), Qt.MiddleButton)
    assert not m.boceto.geo3d.get("puntos")


# ---------------------------------------------------------------- BOC-47: ayudas de dibujo en el Boceto 3D
def _mover(lz, pos):
    _evento(lz, QEvent.MouseMove, pos)


def _linea3d(m, p, q):
    b3.agregar_linea(m.boceto, p, q)
    m._cambio()


def test_ayuda_punto_medio_y_el_clic_cae_justo_en_el_medio(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 0, 0))
    _herramienta(m, "punto")
    _mover(m.lienzo, it.a_pantalla((20, 0, 0)) + QPointF(4, 3))            # a unos píxeles del medio
    assert it.ayuda.tipo == "punto_medio" and m.lienzo.ayuda_3d[2] == "Punto medio"
    _clic(m.lienzo, it.a_pantalla((20, 0, 0)) + QPointF(4, 3))
    nuevo = [p for p in m.boceto.geo3d["puntos"].values() if p[0] == pytest.approx(20, abs=1e-6)]
    assert nuevo and np.allclose(nuevo[-1], (20, 0, 0), atol=1e-6)


def test_ayuda_de_alineacion_con_un_punto_existente(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    b3.agregar_punto(m.boceto, (30, 12, 0), unir=False)
    m._cambio()
    _herramienta(m, "punto")
    _mover(m.lienzo, it.a_pantalla((30, 45, 0)) + QPointF(3, 0))
    assert it.ayuda.tipo == "alineado_v" and "misma X" in m.lienzo.ayuda_3d[2] and len(it.ayuda.guias) == 1
    _clic(m.lienzo, it.a_pantalla((30, 45, 0)) + QPointF(3, 0))
    nuevo = [p for p in m.boceto.geo3d["puntos"].values() if p[1] > 20]
    assert nuevo and nuevo[-1][0] == pytest.approx(30, abs=1e-6) and nuevo[-1][1] == pytest.approx(45, abs=2)   # la X se engancha, la Y es la del cursor


def test_ayuda_de_interseccion_de_dos_lineas(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 40, 0))
    _linea3d(m, (0, 40, 0), (40, 0, 0))
    _herramienta(m, "punto")
    _mover(m.lienzo, it.a_pantalla((20, 20, 0)) + QPointF(2, 2))
    assert it.ayuda.tipo == "interseccion" and m.lienzo.ayuda_3d[2] == "Intersección"
    _clic(m.lienzo, it.a_pantalla((20, 20, 0)) + QPointF(2, 2))
    assert any(np.allclose(p, (20, 20, 0), atol=1e-6) for p in m.boceto.geo3d["puntos"].values())


def test_ayuda_de_tangente_al_dibujar_una_linea_hacia_un_circulo(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    b3.agregar_circulo(m.boceto, (60, 0, 0), 15, (0, 0, 1))
    m._cambio()
    _herramienta(m, "linea")
    _clic(m.lienzo, it.a_pantalla((0, 0, 0)))
    d = math.sqrt(60 ** 2 - 15 ** 2)
    a = math.asin(15 / 60)
    punto = (d * math.cos(a), d * math.sin(a), 0)                         # donde la visual toca el círculo
    _mover(m.lienzo, it.a_pantalla(punto) + QPointF(3, -2))
    assert it.ayuda.tipo == "tangente" and m.lienzo.ayuda_3d[2] == "Tangente a la curva"
    _clic(m.lienzo, it.a_pantalla(punto) + QPointF(3, -2))
    lineas = [c for c in m.boceto.geo3d["curvas"].values() if c["tipo"] == "linea"]
    fin = np.array(m.boceto.geo3d["puntos"][lineas[-1]["puntos"][1]])
    assert np.allclose(fin, punto, atol=1e-6) and np.linalg.norm(fin - (60, 0, 0)) == pytest.approx(15, abs=1e-6)


def test_la_ayuda_se_apaga_con_seleccionar_y_al_alejarse(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 0, 0))
    _herramienta(m, "seleccionar")
    _mover(m.lienzo, it.a_pantalla((20, 0, 0)))
    assert it.ayuda is None and m.lienzo.ayuda_3d is None
    _herramienta(m, "punto")
    _mover(m.lienzo, it.a_pantalla((20, 0, 0)))
    assert it.ayuda is not None
    _mover(m.lienzo, it.a_pantalla((10, 70, 0)))
    assert it.ayuda is None and m.lienzo.ayuda_3d is None


def test_la_ayuda_trabaja_en_el_plano_activo_de_la_triada(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (0, 40, 0))                                   # en el plano XY pero…
    _linea3d(m, (0, 0, 30), (0, 40, 30))                                 # …esta a 30 mm de altura
    _herramienta(m, "punto")
    esquinas = it.triada.asas(it._largo())[("plano", "yz")]
    _clic(m.lienzo, it.a_pantalla(np.mean(esquinas, axis=0)))            # plano YZ activo: la segunda línea se ve de costado
    assert it.triada.plano == "yz"
    _mover(m.lienzo, it.a_pantalla((0, 20, 30)) + QPointF(3, 2))
    assert it.ayuda is not None and it.ayuda.tipo == "punto_medio" and np.allclose(it.ayuda.punto, (0, 20, 30), atol=1e-6)


# ---------------------------------------------------------------- BOC-74: la ayuda deja la restricción 3D
def _restricciones3d(m):
    return list(m.boceto.geo3d.get("restricciones", {}).values())


def test_el_clic_en_el_punto_medio_deja_la_restriccion_de_punto_medio(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 0, 0))
    largo = next(iter(m.boceto.geo3d["curvas"]))
    _herramienta(m, "punto")
    _clic(m.lienzo, it.a_pantalla((20, 0, 0)) + QPointF(4, 3))
    (r,) = _restricciones3d(m)
    punto = m.boceto.geo3d["puntos"][r["entidades"][0]]
    assert r["tipo"] == "punto_medio" and r["entidades"][1] == largo and np.allclose(punto, (20, 0, 0), atol=1e-6)
    m.lienzo.deshacer()                                                    # un solo paso: el punto y su restricción
    assert not _restricciones3d(m) and len(m.boceto.geo3d["puntos"]) == 2


def test_si_el_medio_cae_fuera_del_plano_el_clic_lo_engancha_y_deja_la_restriccion(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 7), (40, 0, 7))                                      # su medio real está a 7 mm del plano activo
    _herramienta(m, "punto")
    _clic(m.lienzo, it.a_pantalla((20, 0, 7)) + QPointF(4, 3))
    assert any(np.allclose(p, (20, 0, 7), atol=1e-6) for p in m.boceto.geo3d["puntos"].values())
    assert [r["tipo"] for r in _restricciones3d(m)] == ["punto_medio"]


def test_la_interseccion_une_el_punto_nuevo_con_las_dos_lineas(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 40, 0))
    _linea3d(m, (0, 40, 0), (40, 0, 0))
    _herramienta(m, "punto")
    _clic(m.lienzo, it.a_pantalla((20, 20, 0)) + QPointF(2, 2))
    rs = _restricciones3d(m)
    assert sorted(r["tipo"] for r in rs) == ["coincidente", "coincidente"] and len({r["entidades"][0] for r in rs}) == 1


def test_una_linea_horizontal_a_la_triada_queda_con_la_restriccion_de_eje(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _herramienta(m, "linea")
    _clic(m.lienzo, it.a_pantalla((30, -20, 0)))
    _mover(m.lienzo, it.a_pantalla((90, -20, 0)) + QPointF(0, 2))
    assert it.ayuda is not None and it.ayuda.tipo == "horizontal"
    _clic(m.lienzo, it.a_pantalla((90, -20, 0)) + QPointF(0, 2))
    (r,) = _restricciones3d(m)
    assert r["tipo"] == "eje" and r["eje"] == "x"
    p = [m.boceto.geo3d["puntos"][i] for i in m.boceto.geo3d["curvas"][r["entidades"][0]]["puntos"]]
    assert p[0][1] == pytest.approx(p[1][1], abs=1e-6)


def test_un_clic_sin_ayuda_no_hereda_la_union_de_un_clic_anterior_en_ese_lugar(boceto3d):
    m, it = boceto3d, boceto3d.interaccion3d
    _linea3d(m, (0, 0, 0), (40, 0, 0))
    _herramienta(m, "punto")
    _clic(m.lienzo, it.a_pantalla((20, 0, 0)) + QPointF(4, 3))
    assert len(it.uniones) == 1
    _clic(m.lienzo, it.a_pantalla((20, 0, 0)))                            # cae sobre el punto ya creado: no hay ayuda
    assert not it.uniones
