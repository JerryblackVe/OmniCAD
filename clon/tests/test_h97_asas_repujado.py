"""H-97: las asas de alineación de Repujado se arrastran sin confundirse entre sí."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def repujado(tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=40, width=30, height=10, anchor="corner")
    _llamar(sesion, "create_sketch", name="Marca", plane="XY")
    _llamar(sesion, "draw_rectangle", sketch="Marca", x1=10, y1=8, x2=18, y2=12)
    resultado = _llamar(sesion, "create_emboss", sketch="Marca", faces=">Z", depth=2,
                        horizontal_offset=0, vertical_offset=0, rotation=0)
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(
        QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)))
    ventana.resize(1280, 800)
    ventana.show()
    try:
        panel = ventana.ejecutar_comando(CATALOGO["repujado"](), op=sesion.paso(resultado["feature"]["id"]))
        ventana.visor.vista("arriba")
        ventana.visor.encuadrar()
        estados = []
        panel.previa.connect(estados.append)
        QTest.qWait(300)
        yield ventana, panel, estados
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def _mover(visor, punto, botones=Qt.NoButton):
    """Movimiento simulado: no cambia el cursor real."""
    posicion = QPointF(*punto)
    QApplication.sendEvent(visor, QMouseEvent(QEvent.MouseMove, posicion, visor.mapToGlobal(posicion),
                                             Qt.NoButton, botones, Qt.NoModifier))


def _arrastrar(visor, desde, hasta):
    QTest.mousePress(visor, Qt.LeftButton, pos=QPoint(*np.rint(desde).astype(int)))
    for fraccion in np.linspace(0.2, 1, 5):
        _mover(visor, desde + (hasta - desde) * fraccion, Qt.LeftButton)
        QTest.qWait(30)
    QTest.mouseRelease(visor, Qt.LeftButton, pos=QPoint(*np.rint(hasta).astype(int)))
    QTest.qWait(300)


def _relieve(estado):
    forma = next(iter(estado.cuerpos.values())).forma
    return next(c for c in geo.caras(forma)
                if (plano := geo.plano_de_cara(c)) is not None
                and plano.normal[2] > 0.9 and plano.origen[2] > 11)


@pytest.mark.parametrize("clave,giro", [("desfase_h", 0), ("desfase_v", 90), ("giro", 0)])
def test_arrastrar_cada_asa_cambia_su_campo_y_la_previa(repujado, clave, giro):
    ventana, panel, estados = repujado
    panel.set_valor("giro", f"{giro} deg")
    QTest.qWait(300)
    assert panel._previa_ok, panel.mensaje.text()
    anterior = _relieve(estados[-1])
    centro_anterior = np.array(geo.centro_masa(anterior, superficie=True))
    caja_anterior = np.array(geo.caja_envolvente(anterior))
    valores = {k: panel.valores[k] for k in ("desfase_h", "desfase_v", "giro")}
    gestor = panel.manipuladores
    asa = next(m for m in gestor.manips if m.clave == clave)
    if clave == "giro":
        desde = gestor.pantalla([asa.asa(gestor)])[0][0]
        angulo = math.radians(25)
        destino = asa.centro + (asa.u * math.cos(angulo) + asa.v * math.sin(angulo)) * asa._r(gestor)
        hasta = gestor.pantalla([destino])[0][0]
    else:
        a, b = asa.puntos(gestor)
        # El cuello de la flecha también se debe poder agarrar, incluso con giro 0°/90°.
        punto = a + (b - a) * 0.85
        desde, hasta = gestor.pantalla([punto, punto + asa.direccion * 3])[0]
    _mover(ventana.visor, desde)
    assert gestor._hover == (asa.ident, "asa" if clave == "giro" else "flecha")
    assert clave in gestor.cajas and gestor.cajas[clave].isVisible()
    cantidad = len(estados)
    _arrastrar(ventana.visor, desde, hasta)
    assert panel.valores[clave] != valores[clave]
    assert panel.widgets[clave].text() == panel.valores[clave]
    assert all(panel.valores[k] == v for k, v in valores.items() if k != clave)
    assert len(estados) > cantidad and panel._previa_ok, panel.mensaje.text()
    actual = _relieve(estados[-1])
    assert geo.es_valida(next(iter(estados[-1].cuerpos.values())).forma)
    assert geo.area(actual) == pytest.approx(32)
    if clave == "giro":
        assert gestor.valor(clave) == pytest.approx(25, abs=1)
        assert geo.centro_masa(actual, superficie=True) == pytest.approx(centro_anterior)
        assert not np.allclose(geo.caja_envolvente(actual), caja_anterior)
    else:
        assert gestor.valor(clave) == pytest.approx(3, abs=0.2)
        assert geo.centro_masa(actual, superficie=True) == pytest.approx(
            centro_anterior + asa.direccion * gestor.valor(clave), abs=1e-6)


def test_arrastrar_fuera_de_las_asas_no_cambia_campos_ni_previa(repujado):
    ventana, panel, estados = repujado
    assert panel._previa_ok, panel.mensaje.text()
    valores = dict(panel.valores)
    cantidad = len(estados)
    desde, hasta = np.array([100, 150]), np.array([140, 170])
    _mover(ventana.visor, desde)
    assert panel.manipuladores._hover is None
    _arrastrar(ventana.visor, desde, hasta)
    assert panel.valores == valores
    assert len(estados) == cantidad
