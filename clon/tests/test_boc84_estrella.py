# -*- coding: utf-8 -*-
"""BOC-84: herramienta «Estrella» del boceto (propia de OmniCAD: Fusion no la tiene), por la API (`draw_star`) y en la
ventana como un usuario. P-154: cambiar Lados (o las opciones de la estrella) rehace la figura recién dibujada."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QSpinBox  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones.boceto import proporcion_estrella  # noqa: E402


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def area_estrella(n, R, r, r_punta=0.0):
    """Área de la estrella filosa menos lo que se lleva cada redondeo de punta (ángulo interior de la punta)."""
    area = n * R * r * math.sin(math.pi / n)
    if r_punta:
        p, v = (R, 0.0), (r * math.cos(math.pi / n), r * math.sin(math.pi / n))
        lado = math.dist(p, v)
        alfa = 2 * math.asin(abs(v[1]) / lado)                  # ángulo de la punta
        area -= n * r_punta ** 2 * (1 / math.tan(alfa / 2) - (math.pi - alfa) / 2)
    return area


@pytest.fixture
def sesion():
    s = api.Sesion()
    llamar(s, "create_sketch", name="E", plane="XY")
    return s


def test_estrella_de_5_puntas_redondeada_se_extruye_con_el_area_de_la_formula(sesion):
    s = sesion
    r = llamar(s, "draw_star", points=5, outer_radius=20, tip_fillet=1, sketch="E")
    assert r["dof"] == 3                                        # el centro anclado: quedan los dos radios y el giro
    llamar(s, "extrude", sketch="E", profile=0, distance=5)
    (cuerpo,) = s.doc.estado_final.cuerpos.values()
    assert geo.es_valida(cuerpo.forma)
    esperada = area_estrella(5, 20, 20 * proporcion_estrella(5), 1.0) * 5
    assert geo.volumen(cuerpo.forma) == pytest.approx(esperada, rel=1e-3)


@pytest.mark.parametrize("puntas", [3, 64])
def test_tres_y_64_puntas_dan_un_perfil_con_la_formula(sesion, puntas):
    llamar(sesion, "draw_star", points=puntas, outer_radius=30, inner_ratio=0.8, sketch="E")
    perfiles = llamar(sesion, "get_sketch", sketch="E")["profiles"]
    assert len(perfiles) == 1 and perfiles[0]["area"] == pytest.approx(area_estrella(puntas, 30, 24), rel=1e-6)


def test_regular_7_3_y_redondeo_de_valles(sesion):
    r = llamar(sesion, "draw_star", points=7, outer_radius=10, skip=3, valley_fillet=0.3, sketch="E")
    assert proporcion_estrella(7, 3) == pytest.approx(math.cos(3 * math.pi / 7) / math.cos(2 * math.pi / 7))
    assert r["profiles"] == 1 and r["dof"] == 3


@pytest.mark.parametrize("args, texto", [
    ({"tip_fillet": 50}, "redondeo de las puntas"), ({"points": 2}, "entre 3 y 64"), ({"points": 5, "skip": 3}, "salto"),
    ({"inner_radius": 25}, "menor que el exterior"), ({"inner_ratio": 1.5}, "inner_ratio"),
    ({"inner_ratio": 0.5, "skip": 2}, "solo uno")])
def test_lo_que_no_sirve_da_un_mensaje_claro_y_no_toca_el_boceto(sesion, args, texto):
    antes = llamar(sesion, "get_sketch", sketch="E")
    r = api.llamar(sesion, "draw_star", {"outer_radius": 20, "sketch": "E", **args})
    assert not r["ok"] and texto in r["mensaje"], r
    assert llamar(sesion, "get_sketch", sketch="E") == antes


# ---------------------------------------------------------------- en la ventana, como un usuario
@pytest.fixture
def boceto(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.restricciones import Boceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    v._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
    QTest.qWait(50)
    yield v.modo_boceto
    v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def _teclear(sp, texto):
    sp.setFocus()
    QTest.keyClick(sp, Qt.Key_A, Qt.ControlModifier)
    for ch in texto:
        QTest.keyClick(sp, ch)


def _spin(mb, etiqueta):
    form = mb.tarjeta.form_contexto
    for i in range(form.rowCount()):
        if form.itemAt(i, form.ItemRole.LabelRole).widget().text() == etiqueta:
            return form.itemAt(i, form.ItemRole.FieldRole).widget()
    raise AssertionError(f"la tarjeta no tiene «{etiqueta}»")


def _lineas(lz):
    return sum(1 for c in lz.b.curvas.values() if c.tipo == "linea" and not c.construccion)


def test_estrella_con_dos_clics_y_puntas_tecleadas_en_la_tarjeta(boceto):
    mb = boceto
    lz = mb.lienzo
    mb.acciones["sk_estrella"].trigger()
    _teclear(_spin(mb, "Puntas"), "6")                          # antes del primer clic
    _clic(lz, 0, 0)
    _clic(lz, 0, 15)
    assert _lineas(lz) == 12 and lz.resultado.ok
    _teclear(_spin(mb, "Puntas"), "8")                          # P-154: recién dibujada, se rehace
    assert _lineas(lz) == 16 and lz.resultado.ok
    lz.deshacer()
    assert _lineas(lz) == 12


def test_cambiar_lados_rehace_el_poligono_recien_dibujado_y_conserva_la_cota_del_circulo(boceto):
    mb = boceto
    lz = mb.lienzo
    mb.acciones["sk_poligono_inscrito"].trigger()
    _clic(lz, 0, 0)
    _clic(lz, 12, 0)
    assert _lineas(lz) == 6
    (circulo,) = [c.id for c in lz.b.curvas.values() if c.tipo == "circulo"]
    lz.aplicar_cambio(lambda: lz.b.agregar_cota("radio", [circulo], "12"))
    _teclear(mb.tarjeta.findChild(QSpinBox), "8")
    assert _lineas(lz) == 8 and lz.resultado.ok
    assert any(k.entidades == [circulo] for k in lz.b.cotas.values())        # la cota del círculo guía sigue
    vertice = lz.b.coords(next(c for c in lz.b.curvas.values() if c.tipo == "linea").p1)
    assert math.dist(vertice, (0, 0)) == pytest.approx(12)                     # mismo radio
    mb.acciones["sk_linea"].trigger()                           # otra herramienta: ya no rehace
    mb.acciones["sk_poligono_inscrito"].trigger()
    _teclear(mb.tarjeta.findChild(QSpinBox), "5")
    assert _lineas(lz) == 8


def test_rehacer_no_se_lleva_la_linea_donde_se_engancho_el_vertice(boceto):
    mb = boceto
    lz = mb.lienzo
    otra = []
    lz.aplicar_cambio(lambda: otra.append(lz.b.agregar_linea((20, 0), (40, 0))))
    mb.acciones["sk_poligono_inscrito"].trigger()
    _clic(lz, 0, 0)
    _clic(lz, 20, 0)                                            # el vértice cae en el extremo de la otra línea
    _teclear(mb.tarjeta.findChild(QSpinBox), "5")
    assert otra[0] in lz.b.curvas and lz.b.coords(lz.b.curvas[otra[0]].p2) == pytest.approx((40, 0))
    assert sum(1 for c in lz.b.curvas.values() if c.tipo == "linea" and c.id != otra[0]) == 5 and lz.resultado.ok


# ---------------------------------------------------------------- B-496: 22 puntas, salto 10, redondeos grandes
@pytest.mark.parametrize("puntas, salto", [(22, 10), (12, 4), (9, 3), (8, 3)])
def test_cantidad_de_puntas_es_la_pedida_tambien_con_mcd_mayor_que_1(sesion, puntas, salto):
    llamar(sesion, "draw_star", points=puntas, outer_radius=50, skip=salto, sketch="E")
    b = sesion.paso("E").boceto
    vertices = {round(math.atan2(*b.coords(q)[::-1]), 6) for c in b.curvas.values()
                if c.tipo == "linea" and not c.construccion for q in c.extremos()
                if math.dist(b.coords(q), (0, 0)) == pytest.approx(50)}
    assert len(vertices) == puntas
    perfiles = llamar(sesion, "get_sketch", sketch="E")["profiles"]
    r = 50 * proporcion_estrella(puntas, salto)
    assert len(perfiles) == 1 and perfiles[0]["area"] == pytest.approx(area_estrella(puntas, 50, r), rel=1e-6)


def test_redondeos_que_no_entran_se_achican_sin_perder_puntas(sesion):
    from omnicad.restricciones.boceto import redondeos_estrella
    assert redondeos_estrella(20, 20 * proporcion_estrella(5), 5, 1, 0.3) == (1, 0.3)       # entran: no se tocan
    rp, rv = redondeos_estrella(50, 9.5, 22, 3.5, 10.5)
    assert 0 < rp < 3.5 and rv / rp == pytest.approx(3)                                      # misma proporción
    llamar(sesion, "draw_star", points=22, outer_radius=50, inner_radius=9.5, tip_fillet=rp, valley_fillet=rv,
           sketch="E")
    b = sesion.paso("E").boceto
    assert sum(1 for c in b.curvas.values() if c.tipo == "arco") == 44
    assert len(llamar(sesion, "get_sketch", sketch="E")["profiles"]) == 1


def test_caso_de_gerardo_22_puntas_redondeadas_en_la_ventana(boceto):
    mb = boceto
    lz = mb.lienzo
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    mb.acciones["sk_estrella"].trigger()
    _clic(lz, 0, 0)
    _clic(lz, 0, 50)
    for etiqueta, valor in [("Interior (0 = regular)", "19"), ("Redondeo de puntas", "3,5"),
                            ("Redondeo de valles", "10,5"), ("Puntas", "22"), ("Salto (con Interior 0)", "10")]:
        _teclear(_spin(mb, etiqueta), valor)
    b = lz.b
    assert lz.resultado.ok and _lineas(lz) == 44 and sum(1 for c in b.curvas.values() if c.tipo == "arco") == 44
    exterior, interior = sorted((c for c in b.curvas.values() if c.tipo == "circulo"), key=lambda c: -c.radio)
    assert interior.radio == pytest.approx(0.19 * 50)                       # Interior 19 % vale al rehacer
    assert mensajes[-1].startswith("⚠ El redondeo no entraba")
    assert len(lz._vertices_virtuales_estrella()) == 44                     # las esquinas filosas no se dibujan
    lz.grab()
    assert len(lz._zonas_glifos) <= 4                                       # un glifo por tipo, no decenas
    _teclear(_spin(mb, "Interior (0 = regular)"), "0")                      # con 0, manda el salto
    interior = next(c for c in b.curvas.values() if c.tipo == "circulo" and c.id != exterior.id)
    assert interior.radio == pytest.approx(50 * proporcion_estrella(22, 10)) and _lineas(lz) == 44
