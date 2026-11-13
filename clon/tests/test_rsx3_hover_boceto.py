"""RS-X3: el hover del boceto mide todos los segmentos de una vez (numpy) y ya no se apaga con más de 400 curvas."""
import os
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo, _dist_px  # noqa: E402


def _boceto(n):
    b, rnd = Boceto(), random.Random(1)
    for i in range(n):
        x, y = rnd.uniform(-200, 200), rnd.uniform(-120, 120)
        if i % 4 == 0:
            b.agregar_linea(b.agregar_punto(x, y), b.agregar_punto(x + rnd.uniform(-20, 20), y + rnd.uniform(-20, 20)))
        elif i % 4 == 1:
            b.agregar_circulo(b.agregar_punto(x, y), rnd.uniform(1, 8))
        elif i % 4 == 2:
            r = rnd.uniform(2, 10)
            b.agregar_arco_centro(b.agregar_punto(x, y), b.agregar_punto(x + r, y), b.agregar_punto(x, y + r))
        else:
            b.agregar_spline([b.agregar_punto(x + 5 * j, y + rnd.uniform(-5, 5)) for j in range(4)])
    return b


def _lienzo(n):
    QApplication.instance() or QApplication([])
    lz = Lienzo(_boceto(n), TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resize(1200, 800)
    lz.encuadrar()
    lz.set_herramienta("seleccionar")
    return lz


def _a_mano(lz, pos, radio_px=6.0):
    """La cuenta de antes: segmento por segmento, la curva visible más cercana (sin textos ni el interior de los círculos)."""
    mejor, dmin = None, radio_px
    for c in lz.b.curvas.values():
        for poli in lz._polilineas(c, 48):
            px = lz._poli_px(poli)
            d = min(_dist_px(pos, a, b) for a, b in zip(px, px[1:], strict=False))
            if d < dmin:
                mejor, dmin = c.id, d
    return mejor


def test_rsx3_la_curva_bajo_el_cursor_es_la_misma_que_segmento_por_segmento():
    lz = _lienzo(300)
    rnd = random.Random(5)
    polis = [lz._poli_px(lz._polilineas(c, 48)[0]) for c in list(lz.b.curvas.values())[::7]]
    puntos = [px[len(px) // 2] for px in polis]                                                  # sobre curvas
    puntos += [QPointF(rnd.uniform(0, 1200), rnd.uniform(0, 800)) for _ in range(60)]             # y al azar
    halladas = 0
    for p in puntos:
        q = QPointF(p.x() + rnd.uniform(-3, 3), p.y() + rnd.uniform(-3, 3))
        esperada = _a_mano(lz, q)
        assert lz._curva_cercana(q) == esperada
        halladas += esperada is not None
    assert halladas >= 40
    lz.close()


def test_rsx3_el_hover_resalta_con_mas_de_400_curvas():
    lz = _lienzo(500)
    lz.show()
    linea = next(c for c in lz.b.curvas.values() if c.tipo == "linea")
    (x1, y1), (x2, y2) = lz.b._extremos_linea(linea.id)
    medio = lz.a_px(x1 + 0.37 * (x2 - x1), y1 + 0.37 * (y2 - y1))
    QTest.mouseMove(lz, medio.toPoint())
    esperada = lz.entidad_en(QPointF(medio.toPoint()))
    assert esperada is not None and lz._sobre == esperada       # antes, con más de 400 curvas, no se resaltaba nada
    lz.close()
