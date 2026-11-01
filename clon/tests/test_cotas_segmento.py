"""BOC-37: las cotas que antes solo mostraban el texto (distancia punto–línea, entre paralelas, con círculo o arco,
punto–spline y desfase) dibujan su línea de cota con flechas entre lo que miden."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _seg(b, cota):
    seg = b.segmento_cota(cota)
    return None if seg is None else [*seg[0], *seg[1]]


def _crear(b, tipo, ents, valor, datos):
    antes = set(b.cotas)
    b.agregar_cota(tipo, ents, valor, datos, referencia=True)
    return b.cotas[(set(b.cotas) - antes).pop()]


def test_punto_a_linea_va_del_punto_a_su_pie():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (20, 0))
    punto = b.agregar_punto(5, 7)
    assert _seg(b, _crear(b, "distancia", [punto, linea], "7", {})) == pytest.approx([5, 0, 5, 7])
    assert _seg(b, _crear(b, "distancia", [linea, punto], "7", {})) == pytest.approx([5, 0, 5, 7])


def test_entre_lineas_paralelas_va_en_perpendicular():
    b = Boceto()
    a = b.agregar_linea((0, 0), (20, 0))
    c = b.agregar_linea((3, 9), (30, 9))
    seg = _seg(b, _crear(b, "distancia", [a, c], "9", {}))
    assert seg == pytest.approx([3, 0, 3, 9])


@pytest.mark.parametrize("modo,esperado", [("centro", [0, 0, 10, 0]), ("tangente", [4, 0, 10, 0])])
def test_con_un_circulo_hasta_el_centro_o_al_borde(modo, esperado):
    b = Boceto()
    c = b.agregar_circulo((0, 0), 4)
    punto = b.agregar_punto(10, 0)
    assert _seg(b, _crear(b, "distancia", [c, punto], "10", {"modo": modo})) == pytest.approx(esperado)


def test_circulo_con_linea_y_entre_circulos_separados_y_anidados():
    b = Boceto()
    c = b.agregar_circulo((0, 5), 2)
    linea = b.agregar_linea((-10, 0), (10, 0))
    assert _seg(b, _crear(b, "distancia", [c, linea], "5", {"modo": "centro"})) == pytest.approx([0, 5, 0, 0])
    assert _seg(b, _crear(b, "distancia", [c, linea], "3", {"modo": "tangente"})) == pytest.approx([0, 3, 0, 0])
    d = Boceto()
    c1, c2 = d.agregar_circulo((0, 0), 3), d.agregar_circulo((20, 0), 5)
    assert _seg(d, _crear(d, "distancia", [c1, c2], "12", {"modo": "tangente"})) == pytest.approx([3, 0, 15, 0])
    assert _seg(d, _crear(d, "distancia", [c1, c2], "20", {"modo": "centro"})) == pytest.approx([0, 0, 20, 0])
    e = Boceto()
    grande, chico = e.agregar_circulo((0, 0), 10), e.agregar_circulo((3, 0), 2)         # el chico adentro, a la derecha
    assert _seg(e, _crear(e, "distancia", [grande, chico], "5", {"modo": "tangente"})) == pytest.approx([10, 0, 5, 0])


def test_punto_a_spline_va_al_punto_mas_cercano_de_la_curva():
    b = Boceto()
    s = b.agregar_spline([(0, 0), (10, 0), (20, 0)])
    punto = b.agregar_punto(10, 6)
    seg = _seg(b, _crear(b, "distancia", [punto, s], "6", {}))
    assert seg[2:] == pytest.approx([10, 6], abs=1e-6) and seg[:2] == pytest.approx([10, 0], abs=1e-3)


def test_desfase_de_linea_circulo_y_spline():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (20, 0))
    (copia,), _ = b.desfasar(linea, 3, cadena=False)
    cota, = b.cotas.values()
    assert _seg(b, cota) == pytest.approx([b.coords(b.curvas[copia].p1)[0], 0, b.coords(b.curvas[copia].p1)[0],
                                            b.coords(b.curvas[copia].p1)[1]])
    c = Boceto()
    circulo = c.agregar_circulo((0, 0), 10)
    c.desfasar(circulo, 4)
    seg = _seg(c, next(iter(c.cotas.values())))
    assert math.dist(seg[:2], seg[2:]) == pytest.approx(4)
    s = Boceto()
    spline = s.agregar_spline([(0, 0), (10, 5), (20, 0)])
    s.desfasar(spline, 2)
    seg = _seg(s, next(iter(s.cotas.values())))
    assert math.dist(seg[:2], seg[2:]) == pytest.approx(2, abs=0.05)


def test_las_cotas_que_ya_tienen_su_marco_o_no_son_de_distancia_no_usan_el_segmento():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (20, 0))
    assert b.segmento_cota(_crear(b, "distancia", [linea], "20", {})) is None
    circulo = b.agregar_circulo((50, 0), 3)
    assert b.segmento_cota(_crear(b, "radio", [circulo], "3", {})) is None


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def test_el_lienzo_dibuja_la_linea_de_cota_y_se_puede_agarrar(lienzo):
    lz = lienzo
    linea = lz.b.agregar_linea((0, 0), (40, 0))
    punto = lz.b.agregar_punto(15, 12)
    cota = _crear(lz.b, "distancia", [punto, linea], "12", {})
    lz.resolver()
    lz.grab()
    trazos = lz._trazos_cotas[cota.id]
    assert trazos, "la cota no dibujó ninguna raya"
    a, b = lz.a_px(15, 0), lz.a_px(15, 12)
    esperado = sorted([(round(a.x()), round(a.y())), (round(b.x()), round(b.y()))])
    assert any(sorted([(round(r[0].x()), round(r[0].y())), (round(r[1].x()), round(r[1].y()))]) == esperado
               for r in trazos)


def test_api_get_sketch_informa_el_segmento_medido_solo_donde_hay_segmento():
    from omnicad import api
    s = api.Sesion()
    for nombre, args in (("create_sketch", {"name": "S"}),
                         ("draw_line", {"start_x": 0, "start_y": 0, "end_x": 40, "end_y": 0}),
                         ("draw_line", {"start_x": 0, "start_y": 20, "end_x": 40, "end_y": 20})):
        assert api.llamar(s, nombre, args)["ok"]
    ids = [e["id"] for e in api.llamar(s, "get_sketch", {"sketch": "S"})["result"]["entities"]]
    assert api.llamar(s, "add_dimension", {"sketch": "S", "type": "distance", "entities": ids, "value": 20})["ok"]
    assert api.llamar(s, "add_dimension", {"sketch": "S", "type": "distance", "entities": [ids[0]], "value": 40})["ok"]
    dims = api.llamar(s, "get_sketch", {"sketch": "S"})["result"]["dimensions"]
    entre, propia = (next(d for d in dims if len(d["entities"]) == n) for n in (2, 1))
    seg = entre["measured_segment"]
    assert math.dist(seg[:2], seg[2:]) == pytest.approx(20) and abs(seg[0] - seg[2]) < 1e-9     # perpendicular
    assert "measured_segment" not in propia                                                     # la lineal usa su marco
