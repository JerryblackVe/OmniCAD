"""CF-15: el ViewCube como el de Fusion: 26 zonas clicables (caras, aristas, vértices), 4 triángulos y 2 flechas curvas
que giran 90° en una vista de cara, el menú ▽, la casita y el resaltado azul al pasar. Todo con eventos de ratón
simulados al widget (QTest), nunca el cursor real."""
import itertools

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import superposiciones as sup
from omnicad.ui import visor3d as vis

DIRECCIONES = [d for d in itertools.product((-1, 0, 1), repeat=3) if any(d)]


@pytest.fixture
def cubo(monkeypatch):
    monkeypatch.setenv("OMNICAD_SIN_ANIMACION", "1")
    app = QApplication.instance() or QApplication([])
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    v = vis.Visor3D()
    v.resize(640, 480)
    v.show()
    v.set_modelo(d.estado_final)
    c = sup.ViewCube(v, v)
    c.set_tamano("grande")
    c.show()
    QTest.qWait(50)
    yield c
    c.close()
    v.close()
    v.deleteLater()
    app.processEvents()


def _pintar(c):
    c.grab()                       # fuerza paintEvent: arma las zonas de las caras visibles


def _mover(c, punto, botones=Qt.NoButton):
    """Movimiento simulado al widget (sin tocar el cursor real)."""
    p = QPointF(punto)
    QApplication.sendEvent(c, QMouseEvent(QEvent.MouseMove, p, c.mapToGlobal(p), Qt.NoButton, botones, Qt.NoModifier))


def _clic(c, punto, boton=Qt.LeftButton):
    _mover(c, punto)
    QTest.mouseClick(c, boton, Qt.NoModifier, QPoint(int(punto.x()), int(punto.y())))


def _centro_zona(c, d):
    _pintar(c)
    poli = next(p for p, dd in c._zonas if dd == d)
    return poli.boundingRect().center()


def _atras(c):
    return np.round(c.visor.R[2], 3)


def test_hay_26_zonas_y_cada_una_lleva_a_su_vista(cubo):
    """Clic al centro de cada zona, desde una cámara en el mismo octante: el ojo queda del lado de la zona."""
    for d in DIRECCIONES:
        n = np.array(d, float)
        cubo.visor.vista_direccion(n / np.linalg.norm(n) + 0.3 * np.array([d[0] or 1, d[1] or 1, d[2] or 1]))
        _clic(cubo, _centro_zona(cubo, d))
        esperado = n / np.linalg.norm(n)
        assert np.allclose(cubo.visor.R[2], esperado, atol=2e-3), (d, cubo.visor.R[2])


def test_las_caras_dan_la_vista_estandar_con_z_arriba(cubo):
    cubo.visor.vista("iso")
    _clic(cubo, _centro_zona(cubo, (1, 0, 0)))
    assert np.allclose(cubo.visor.R, [[0, 1, 0], [0, 0, 1], [1, 0, 0]], atol=1e-6)       # DERECHA: Y a la derecha, Z arriba


def test_vertice_es_la_isometrica_y_la_arista_a_45(cubo):
    cubo.visor.vista("frente")
    cubo.visor.vista_direccion((-1, -1, 1))
    _clic(cubo, _centro_zona(cubo, (1, -1, 1)))
    assert np.allclose(cubo.visor.R[2], np.array([1, -1, 1]) / np.sqrt(3), atol=1e-6)
    assert abs(cubo.visor.elevacion - 35.264) < 0.01
    _clic(cubo, _centro_zona(cubo, (1, -1, 0)))
    assert np.allclose(cubo.visor.R[2], np.array([1, -1, 0]) / np.sqrt(2), atol=1e-6)


def test_al_pasar_el_cursor_la_zona_se_resalta_y_al_salir_vuelve(cubo):
    cubo.visor.vista("iso")
    punto = _centro_zona(cubo, (1, -1, 0))
    _mover(cubo, punto)
    assert cubo._hover == ("zona", (1, -1, 0))
    img = cubo.grab().toImage()
    assert any(img.pixelColor(x, y).blue() > 200 and img.pixelColor(x, y).red() < 120
               for x in range(img.width()) for y in range(img.height()))       # hay azul
    cubo.leaveEvent(None)
    assert cubo._hover is None


@pytest.mark.parametrize("clave, cara", [("der", (1, 0, 0)), ("izq", (-1, 0, 0)), ("arriba", (0, 0, 1)), ("abajo", (0, 0, -1))])
def test_triangulos_giran_90_a_la_cara_vecina(cubo, clave, cara):
    cubo.visor.vista("frente")
    _pintar(cubo)
    antes = cubo.visor.distancia
    _clic(cubo, cubo._rects_giro()[clave].center())
    assert np.allclose(cubo.visor.R[2], cara, atol=1e-6), cubo.visor.R
    assert cubo.visor.distancia == antes                  # gira sin cambiar el zoom
    assert np.allclose(cubo.visor.R @ cubo.visor.R.T, np.eye(3))


def test_triangulos_siguen_el_giro_de_la_pantalla_desde_una_cara_de_arriba(cubo):
    """De FRONTAL, ▽ de arriba lleva a SUPERIOR con Y arriba y otra vez ▽ a POSTERIOR dada vuelta (como el video de Fusion)."""
    cubo.visor.vista("frente")
    _pintar(cubo)
    _clic(cubo, cubo._rects_giro()["arriba"].center())
    assert np.allclose(cubo.visor.R, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], atol=1e-6)
    _pintar(cubo)
    _clic(cubo, cubo._rects_giro()["arriba"].center())
    assert np.allclose(cubo.visor.R, [[1, 0, 0], [0, 0, -1], [0, 1, 0]], atol=1e-6)    # eje atrás = +Y; Z queda hacia abajo


def test_las_flechas_curvas_giran_sobre_el_eje_de_la_pantalla(cubo):
    cubo.visor.vista("frente")
    _pintar(cubo)
    _clic(cubo, cubo._rects_giro()["antihorario"].center())
    assert np.allclose(cubo.visor.R, [[0, 0, -1], [1, 0, 0], [0, -1, 0]], atol=1e-6)    # el mismo ojo; arriba = antes la derecha
    for _ in range(3):
        _pintar(cubo)
        _clic(cubo, cubo._rects_giro()["antihorario"].center())
    assert np.allclose(cubo.visor.R, [[1, 0, 0], [0, 0, 1], [0, -1, 0]], atol=1e-6)
    _pintar(cubo)
    _clic(cubo, cubo._rects_giro()["horario"].center())
    assert np.allclose(cubo.visor.R[2], [0, -1, 0], atol=1e-6) and np.allclose(cubo.visor.R[1], [-1, 0, 0], atol=1e-6)


def test_fuera_de_una_vista_de_cara_no_hay_triangulos_ni_flechas(cubo):
    cubo.visor.vista("iso")
    _pintar(cubo)
    for clave, r in cubo._rects_giro().items():
        assert cubo._objetivo_en(r.center()) is None or cubo._objetivo_en(r.center())[0] != "giro", clave


def test_la_casita_y_el_menu(cubo):
    cubo.visor.vista("frente")
    _clic(cubo, cubo._rect_casa().center())
    assert abs(cubo.visor.elevacion - 35.264) < 0.01
    elegidas = []
    cubo.al_elegir_camara = elegidas.append
    _clic(cubo, cubo._rect_menu().center())
    m = cubo.menu_abierto
    assert m is not None and [a.text() for a in m.actions() if a.text()][:1] == ["Ir al inicio"]
    camara = next(a for a in m.actions() if a.menu() is not None and a.text() == "Cámara").menu()
    next(a for a in camara.actions() if a.text() == "Ortográfica").trigger()
    assert elegidas == ["ortografica"]
    m.close()


def test_clic_derecho_abre_el_mismo_menu_con_el_tamano(cubo):
    textos = [a.text() for a in cubo.menu().actions() if a.text()]
    assert textos == ["Ir al inicio", "Cámara", "Establecer la vista actual como Inicio", "Restablecer Inicio",
                      "Establecer la vista actual como cara", "Restablecer cara", "Tamaño de ViewCube"]
    tam = next(a for a in cubo.menu().actions() if a.text() == "Tamaño de ViewCube").menu()
    assert [a.text() for a in tam.actions()] == ["Automático", "Grande", "Normal", "Pequeño", "Diminuto"]


def test_arrastrar_sigue_orbitando_y_no_dispara_zona(cubo):
    cubo.visor.vista("iso")
    antes = cubo.visor.R.copy()
    QTest.mousePress(cubo, Qt.LeftButton, Qt.NoModifier, QPoint(60, 70))
    for x in range(60, 100, 8):
        _mover(cubo, QPointF(x, 70), Qt.LeftButton)
    QTest.mouseRelease(cubo, Qt.LeftButton, Qt.NoModifier, QPoint(100, 70))
    assert not np.allclose(cubo.visor.R, antes)
    assert abs(cubo.visor.elevacion - 35.264) > 0.01 or abs(cubo.visor.azimut + 45) > 0.01      # orbitó, no fue a una vista fija
    assert cubo.visor.R[2][2] < 0.99 and np.allclose(cubo.visor.R @ cubo.visor.R.T, np.eye(3), atol=1e-9)


def test_set_view_roll_hace_lo_mismo_que_las_flechas_curvas():
    from omnicad import api
    sesion = api.Sesion()
    api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10})
    r = api.llamar(sesion, "set_view", {"view": "front", "roll": 90})
    assert r["ok"], r
    assert np.allclose(r["result"]["camera"]["R"], [[0, 0, -1], [1, 0, 0], [0, -1, 0]], atol=1e-6)
    assert not api.llamar(sesion, "set_view", {"view": "front", "roll": float("nan")})["ok"]


def _accion(menu, texto):
    return next(a for a in menu.actions() if a.text() == texto)


def test_establecer_y_restablecer_el_inicio(cubo):
    guardados = []
    cubo.al_guardar_vistas = lambda: guardados.append(1)
    cubo.visor.vista("derecha")
    sub = _accion(cubo.menu(), "Establecer la vista actual como Inicio").menu()
    _accion(sub, "Distancia fija").trigger()
    assert cubo.visor.home["modo"] == "distancia_fija" and len(guardados) == 1
    cubo.visor.vista("frente")
    cubo.visor.acercar(3)
    _clic(cubo, cubo._rect_casa().center())                       # la casita vuelve a la vista elegida, con su distancia
    assert np.allclose(cubo.visor.R[2], [1, 0, 0], atol=1e-6)
    assert abs(cubo.visor.distancia - cubo.visor.home["distancia"]) < 1e-6
    assert _accion(cubo.menu(), "Restablecer Inicio").isEnabled()
    _accion(cubo.menu(), "Restablecer Inicio").trigger()
    assert cubo.visor.home is None and len(guardados) == 2
    _clic(cubo, cubo._rect_casa().center())
    assert abs(cubo.visor.elevacion - 35.264) < 0.01
    sub = _accion(cubo.menu(), "Establecer la vista actual como Inicio").menu()
    _accion(sub, "Ajustar a la vista").trigger()
    assert cubo.visor.home["modo"] == "ajustar"


def test_la_vista_de_una_cara_se_puede_cambiar_y_restablecer(cubo):
    cubo.visor.vista("frente")
    _pintar(cubo)
    cubo._activar(("giro", "antihorario"))                        # FRONTAL girada 90°
    giro = cubo.visor.R.copy()
    _accion(cubo.menu(), "Establecer la vista actual como Frontal").trigger()
    assert "frente" in cubo.visor.vistas_cara
    cubo.visor.vista("iso")
    _clic(cubo, _centro_zona(cubo, (0, -1, 0)))                   # la cara FRONTAL usa la vista elegida
    assert np.allclose(cubo.visor.R, giro, atol=1e-6)
    _accion(cubo.menu(), "Restablecer Frontal").trigger()
    assert cubo.visor.vistas_cara == {}
    cubo.visor.vista("iso")
    _clic(cubo, _centro_zona(cubo, (0, -1, 0)))
    assert np.allclose(cubo.visor.R[1], [0, 0, 1], atol=1e-6)     # Z arriba otra vez


def test_set_home_view_y_set_view_con_aristas_y_vertices():
    from omnicad import api
    sesion = api.Sesion()
    api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10})
    r = api.llamar(sesion, "set_view", {"direction": [1, -1, 0]})            # una arista del ViewCube
    assert r["ok"] and np.allclose(np.asarray(r["result"]["camera"]["R"])[2], np.array([1, -1, 0]) / np.sqrt(2), atol=1e-6)
    r = api.llamar(sesion, "set_home_view", {"direction": [1, 1, 1], "mode": "fixed_distance"})
    assert r["ok"] and r["result"]["home"]["modo"] == "distancia_fija"
    r = api.llamar(sesion, "set_home_view", {"face": "front", "roll": 90})
    assert r["ok"] and r["result"]["face_views"] == ["frente"]
    assert np.allclose(sesion.doc.espacios["visor"]["vistas_cara"]["frente"]["R"], [[0, 0, -1], [1, 0, 0], [0, -1, 0]], atol=1e-6)
    r = api.llamar(sesion, "set_home_view", {"face": "front", "reset": True})
    assert r["ok"] and r["result"]["face_views"] == [] and r["result"]["home"] is not None
    r = api.llamar(sesion, "set_home_view", {"reset": True})
    assert r["ok"] and r["result"]["home"] is None
    assert not api.llamar(sesion, "set_home_view", {"direction": [0, 0, 0]})["ok"]
