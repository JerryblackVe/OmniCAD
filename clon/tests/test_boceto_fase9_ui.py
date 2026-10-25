"""Fase 9 del boceto, editor 2D: restricciones inferidas en todas las herramientas (BOC-9), datum con un clic y
resultados fijados en AutoConstrain (BOC-5), línea central al dibujar (BOC-19) y perfil con un clic (BOC-23).
Eventos de ratón simulados: no dependen del cursor real."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.dialogo_autorestringir import ELEGIR_DATUM, DialogoAutoRestringir  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _mover(lz, x, y, mods=Qt.NoModifier):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, mods))


def _clic(lz, x, y, mods=Qt.NoModifier):
    _mover(lz, x, y, mods)
    pos = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, mods))


def _linea_fija(lz):
    lid = lz.b.agregar_linea((11, 20), (52, 20))
    lz.b.agregar_restriccion("fijo", [lid])
    lz.resolver()
    return lid


def _restriccion(lz, tipo, objetivo, xy):
    """Restricción `tipo` entre un punto en `xy` y `objetivo` (o None)."""
    for r in lz.b.restricciones.values():
        if r.tipo == tipo and r.entidades[-1] == objetivo and r.entidades[0] in lz.b.puntos \
                and math.dist(lz.b.coords(r.entidades[0]), xy) < 1e-6:
            return r
    return None


# ---------------------------------------------------------------- BOC-9: la restricción inferida en todas las herramientas
@pytest.mark.parametrize("herramienta,clics", [
    ("rectangulo", [(31.8, 20.2), (45, 35)]),
    ("rectangulo_centro", [(31.8, 20.2), (45, 35)]),
    ("circulo", [(31.8, 20.2), (40, 30)]),
    ("poligono_inscrito", [(31.8, 20.2), (40, 30)]),
    ("elipse", [(31.8, 20.2), (45, 30), (35, 33)]),
])
def test_boc9_punto_medio_inferido_en_otras_herramientas(lienzo, herramienta, clics):
    lz = lienzo
    lid = _linea_fija(lz)
    lz.set_herramienta(herramienta)
    for xy in clics:
        _clic(lz, *xy)
    assert _restriccion(lz, "punto_medio", lid, (31.5, 20)) is not None
    assert lz.resultado.ok and len(lz.historial) == 1         # un solo paso de deshacer


@pytest.mark.parametrize("herramienta,clics,xy", [
    ("circulo", [(40, 20.3), (40, 30)], (40, 20)),
    ("arco_centro", [(40, 30), (40, 20.3), (30, 30)], (40, 20)),
    ("ranura_centro", [(40, 20.3), (40, 40), (43, 30)], (40, 20)),
])
def test_boc9_punto_sobre_curva_inferido(lienzo, herramienta, clics, xy):
    lz = lienzo
    lid = _linea_fija(lz)
    lz.set_herramienta(herramienta)
    for p in clics:
        _clic(lz, *p)
    assert _restriccion(lz, "coincidente", lid, xy) is not None
    assert lz.resultado.ok


def test_boc9_spline_con_extremo_sobre_curva(lienzo):
    lz = lienzo
    lid = _linea_fija(lz)
    lz.set_herramienta("spline_ajuste")
    for xy in ((20, 20.3), (30, 35), (45, 30)):
        _clic(lz, *xy)
    assert lz._terminar_spline() is not None
    assert _restriccion(lz, "coincidente", lid, (20, 20)) is not None


def test_boc9_clic_en_punto_existente_lo_une(lienzo):
    lz = lienzo
    p = lz.b.agregar_punto(10, 30)
    lz.resolver()
    lz.set_herramienta("rectangulo_3p")
    for xy in ((10, 30), (30, 30), (30, 45)):
        _clic(lz, *xy)
    r = _restriccion(lz, "coincidente", p, (10, 30))
    assert r is not None and r.entidades[0] != p
    # el rectángulo de 2 puntos ya unía sus esquinas: no se duplica la coincidencia
    lz.set_herramienta("rectangulo")
    q = lz.b.agregar_punto(-20, -20)
    lz.resolver()
    _clic(lz, -20, -20)
    _clic(lz, -5, -10)
    assert sum(r.tipo == "coincidente" and q in r.entidades for r in lz.b.restricciones.values()) == 1


# ---------------------------------------------------------------- BOC-19: línea central al dibujar
@pytest.mark.parametrize("herramienta,clics,esperadas", [
    ("rectangulo", [(0, 0), (20, 10)], 4),
    ("arco_centro", [(0, 0), (10, 0), (0, 10)], 1),
    ("poligono_inscrito", [(0, 0), (10, 0)], 6),      # el círculo de construcción del polígono no cambia
    ("ranura_centro", [(0, 0), (20, 0), (20, 4)], 4),
])
def test_boc19_las_herramientas_dibujan_lineas_centrales(lienzo, herramienta, clics, esperadas):
    lz = lienzo
    lz.set_herramienta(herramienta)
    lz.alternar_eje()                       # el interruptor «Línea central» de la paleta
    assert lz.eje
    for xy in clics:
        _clic(lz, *xy)
    assert sum(c.eje for c in lz.b.curvas.values()) == esperadas
    assert not any(c.eje and c.construccion for c in lz.b.curvas.values())


# ---------------------------------------------------------------- BOC-5: resultado fijado y datum con un clic
def _boceto_auto():
    b = Boceto()
    b.agregar_linea((-10, 0), (10, 0))
    b.agregar_circulo((2, 3), 3)
    return b


def test_boc5_resultado_fijado_sobrevive_a_generar_mas_y_empezar_de_nuevo(app):
    d = DialogoAutoRestringir(_boceto_auto(), {})
    assert not d.lista.item(0).icon().isNull()                 # candado (totalmente / parcialmente restringido)
    d.lista.setCurrentRow(1)
    d.cantidad.setValue(1)
    d.lista.item(1).setCheckState(Qt.Checked)                 # fija el segundo resultado
    fijado = d.resultados[1]
    d._generar_mas()
    assert d.resultados[0] is fijado and len(d.resultados) == 5
    assert d.lista.item(0).checkState() == Qt.Checked
    d._reiniciar()
    assert d.resultados[0] is fijado and d.lista.item(0).checkState() == Qt.Checked
    claves = [tuple(s.clave for s in r.sugerencias) for r in d.resultados]
    assert len(set(claves)) == len(claves)                    # sin repetir el fijado
    d.lista.item(0).setCheckState(Qt.Unchecked)
    d._reiniciar()
    assert all(r is not fijado for r in d.resultados) and len(d.resultados) == 3


def test_boc5_fijar_datum_lo_suma_a_la_lista(app):
    b = _boceto_auto()
    d = DialogoAutoRestringir(b, {})
    pid = next(iter(b.puntos))
    d.fijar_datum(pid)
    assert d.datum.currentData() == pid and d.opciones()["datum"] == pid


def test_boc5_elegir_el_datum_con_un_clic_en_el_lienzo(lienzo, monkeypatch):
    lz = lienzo
    for k, v in _boceto_auto().__dict__.items():
        setattr(lz.b, k, v)
    lz.resolver()
    lz.encuadrar()
    extremo = next(p for p in lz.b.puntos if lz.b.coords(p) == pytest.approx((10, 0)))
    vistos = []

    def exec_falso(self):
        vistos.append(self.datum.currentData())
        if len(vistos) == 1:
            QTimer.singleShot(0, lambda: _clic(lz, 10, 0))     # el clic llega con el diálogo cerrado
            return ELEGIR_DATUM
        return QDialog.Accepted
    monkeypatch.setattr(DialogoAutoRestringir, "exec", exec_falso)
    agregado = lz.auto_restringir_dialogo()
    assert vistos == [None, extremo]
    assert agregado and lz.resultado.gdl == 0


def test_boc5_esc_cancela_la_eleccion_del_datum(lienzo):
    lz = lienzo
    lz.b.agregar_linea((0, 0), (10, 0))
    lz.resolver()
    QTimer.singleShot(0, lz.cancelar)
    assert lz.elegir_punto_en_lienzo() is None


# ---------------------------------------------------------------- BOC-23: perfil con un clic
def test_boc23_clic_dentro_de_una_region_elige_el_perfil(lienzo):
    lz = lienzo
    lz.b.agregar_rectangulo((0, 0), (40, 20))
    lz.b.agregar_circulo((10, 10), 5)
    lz.resolver()
    lz.centro, lz.escala = [20.0, 10.0], 19.0                 # círculo grande en pantalla: no se agarra desde adentro
    _clic(lz, 12, 12)                                         # adentro del círculo (lejos del centro)
    (disco,) = lz.perfiles_seleccionados()
    assert lz.seleccion == []
    assert disco.area == pytest.approx(math.pi * 25, rel=1e-3)
    assert "perfil" in lz.describir_seleccion()
    _clic(lz, 30, 10, Qt.ControlModifier)                     # Ctrl suma el anillo
    areas = sorted(p.area for p in lz.perfiles_seleccionados())
    assert areas == pytest.approx([math.pi * 25, 800 - math.pi * 25], rel=1e-3)
    assert "2 perfiles" in lz.describir_seleccion()
    img = lz.grab().toImage()                                 # el perfil elegido se pinta resaltado
    q = lz.a_px(30, 15)
    assert img.pixelColor(int(q.x()), int(q.y())) != img.pixelColor(lz.width() - 5, 5)
    _clic(lz, 60, 40)                                         # clic afuera: se vacía
    assert lz.perfiles_seleccionados() == []
    _clic(lz, 30, 10)
    lz.b.agregar_linea((20, 0), (20, 20))                     # el boceto cambió: los perfiles se recalculan
    lz.aplicar_cambio(lambda: None)
    assert lz.perfiles_seleccionados() == []
