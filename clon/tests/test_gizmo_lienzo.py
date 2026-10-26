"""Gizmo del Lienzo (Insertar › Lienzo): eventos reales al widget, campos del panel, receta y deshacer."""
import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest

from omnicad import api
from omnicad.ui import manipuladores as mp
from test_gizmo_calcomania import arrastrar, control, punto_control
from test_manipuladores import _raton
from test_p23_navegador import ventana as ventana  # noqa: F401  (fixture)


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def lienzo(tmp_path):
    ruta = tmp_path / "foto.png"
    Image.new("RGB", (80, 40), "red").save(ruta)
    s = api.Sesion()
    ident = llamar(s, "insert_canvas", path=str(ruta), plane="XY", width=40)["feature"]["id"]
    return s, ident


@pytest.fixture
def panel(lienzo, ventana):  # noqa: F811
    s, ident = lienzo
    ventana.set_documento(s.doc)
    ventana.visor.vista("arriba")
    ventana.editar_operacion(ident)
    p = ventana.panel
    p._calcular_previa()
    p.manipuladores.actualizar()
    yield p
    if ventana.panel is not None:
        ventana.panel.cancelar()


def previo(p):
    return p.ctx.doc.previsualizar(p.ultima_op, p.ctx.indice)[0].lienzos[p.ultima_op.id]


def test_tiene_las_siete_asas_de_fusion(panel):
    clases = [type(m) for m in panel.manipuladores.manips]
    assert clases == [mp.PosicionCalcomania, mp.FlechaCalcomania, mp.FlechaCalcomania, mp.GiroCalcomania,
                      mp.EscalaCalcomania, mp.Volteo, mp.Volteo]


@pytest.mark.parametrize("clave,otra", [("dx", "dy"), ("dy", "dx")])
def test_flecha_mueve_solo_su_eje_y_el_campo_acompana(panel, clave, otra):
    m = control(panel, clave)
    arrastrar(panel, clave, punto_control(panel, clave) + m.u * 6 + m.v * 4)
    esperado = 6 if clave == "dx" else 4
    assert panel.manipuladores.valor(clave) == pytest.approx(esperado, abs=0.02)
    assert panel.manipuladores.valor(otra) == 0
    assert previo(panel)[clave] == pytest.approx(esperado, abs=0.02)
    assert panel.widgets[clave].text() == panel.valores[clave]


def test_cuadrado_central_mueve_libre_y_acepta_valores_negativos(panel):
    m = control(panel, "libre")
    arrastrar(panel, "libre", m.punto + m.u * 3 - m.v * 5)
    d = previo(panel)
    assert (d["dx"], d["dy"]) == pytest.approx((3, -5), abs=0.02)
    panel.aceptar()
    d = list(panel.ctx.doc.estado_final.lienzos.values())[-1]
    assert (d["dx"], d["dy"]) == pytest.approx((3, -5), abs=0.02)


def test_arrastrar_pasando_por_cero_no_rompe(panel):
    m = control(panel, "dx")
    arrastrar(panel, "dx", punto_control(panel, "dx") + m.u * 8)
    arrastrar(panel, "dx", punto_control(panel, "dx") - m.u * 14)
    assert panel.manipuladores.valor("dx") == pytest.approx(-6, abs=0.05)
    assert previo(panel)["dx"] == pytest.approx(-6, abs=0.05)


def test_teclear_en_el_panel_mueve_el_gizmo(panel):
    g = panel.manipuladores
    antes = control(panel, "libre").punto.copy()
    panel.set_valor("dx", "7 mm")
    panel.set_valor("dy", "-2 mm")
    despues = control(panel, "libre").punto
    assert despues - antes == pytest.approx(control(panel, "dx").u * 7 - control(panel, "dx").v * 2)
    assert g.pantalla([despues])[1].all()


def test_giro_por_asa_y_por_caja(panel):
    g = panel.manipuladores
    m = control(panel, "angulo")
    origen = m._origen_arco(g)
    destino = origen + m.v * m._r(g)                    # 90°
    arrastrar(panel, "angulo", destino)
    assert g.valor("angulo") == pytest.approx(90, abs=0.1)
    assert (g.valor("dx"), g.valor("dy")) == (0, 0)
    assert previo(panel)["angulo"] == pytest.approx(90, abs=0.1)
    caja = g.cajas["angulo"]
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "-45")
    QTest.keyClick(caja, Qt.Key_Return)
    panel._calcular_previa()
    assert g.valor("angulo") == -45 and panel.widgets["angulo"].text() == "-45"
    assert np.allclose(caja.punto, control(panel, "angulo").asa(g))


def test_escala_por_codo_y_por_caja_con_y_sin_proporcion(panel):
    g = panel.manipuladores
    base = previo(panel)
    caja = g.cajas["escala"]
    assert caja.text() == "1.00"
    m = control(panel, "ancho")
    arrastrar(panel, "ancho", m.origen + (punto_control(panel, "ancho") - m.origen) * 1.5)
    d = previo(panel)
    assert (d["ancho"], d["alto"]) == pytest.approx((base["ancho"] * 1.5, base["alto"] * 1.5), abs=0.02)
    assert caja.text() == "1.50"
    caja.setText("0")
    assert not g.aplicar_caja(caja) and panel.valores["escala"] == "1.5"
    caja.setText("-2")
    assert not g.aplicar_caja(caja)
    caja.setText("2.00")
    QTest.keyClick(caja, Qt.Key_Return)
    panel._calcular_previa()
    assert previo(panel)["ancho"] == pytest.approx(base["ancho"] * 2)
    panel.set_valor("mantener_proporcion", False)                 # candado abierto: la altura es independiente
    panel.set_valor("alto", "5 mm")
    panel._calcular_previa()
    assert (previo(panel)["ancho"], previo(panel)["alto"]) == pytest.approx((base["ancho"] * 2, 10))


def test_proporcion_bloqueada_enlaza_ancho_y_alto(panel):
    panel.set_valor("ancho", "60 mm")
    assert panel.valores["alto"] == "30 mm" and panel.valores["mantener_proporcion"] is True
    panel.set_valor("alto", "10 mm")
    assert panel.valores["ancho"] == "20 mm"


@pytest.mark.parametrize("clave,eje", [("voltear", 0), ("voltear_v", 1)])
def test_clic_volteo_ida_y_vuelta_e_invertir_en_la_vista(panel, clave, eje):
    g = panel.manipuladores
    for esperado in (True, False):
        xy = g.pantalla([punto_control(panel, clave)])[0][0]
        _raton(panel.visor, QEvent.MouseButtonPress, xy, Qt.LeftButton, Qt.LeftButton)
        _raton(panel.visor, QEvent.MouseButtonRelease, xy, Qt.LeftButton, Qt.NoButton)
        panel._calcular_previa()
        assert panel.valores[clave] is esperado and panel.widgets[clave].isChecked() is esperado
        assert previo(panel)[clave] is esperado


def test_esc_cancela_y_deshacer_rehacer(panel, ventana):  # noqa: F811
    doc, ident = panel.ctx.doc, panel.ultima_op.id
    m = control(panel, "dx")
    arrastrar(panel, "dx", punto_control(panel, "dx") + m.u * 5)
    panel.cancelar()
    assert ventana.panel is None and doc.estado_final.lienzos[ident]["dx"] == 0
    ventana.editar_operacion(ident)
    p = ventana.panel
    p._calcular_previa()
    p.manipuladores.actualizar()
    arrastrar(p, "dx", punto_control(p, "dx") + control(p, "dx").u * 5)
    p.aceptar()
    assert doc.estado_final.lienzos[ident]["dx"] == pytest.approx(5, abs=0.02)
    ventana._deshacer()
    assert doc.estado_final.lienzos[ident]["dx"] == 0
    ventana._rehacer()
    assert doc.estado_final.lienzos[ident]["dx"] == pytest.approx(5, abs=0.02)


def test_reabrir_para_editar_devuelve_el_gizmo_en_su_lugar(panel, ventana):  # noqa: F811
    ident = panel.ultima_op.id
    arrastrar(panel, "angulo", control(panel, "angulo")._origen_arco(panel.manipuladores)
              + control(panel, "angulo").v * control(panel, "angulo")._r(panel.manipuladores))
    arrastrar(panel, "libre", control(panel, "libre").punto + control(panel, "libre").u * 4)
    panel.aceptar()
    ventana.editar_operacion(ident)
    nuevo = ventana.panel
    nuevo.manipuladores.actualizar()
    g = nuevo.manipuladores
    assert len(g.manips) == 7 and set(g.cajas) >= {"angulo", "escala"}
    assert g.valor("angulo") == pytest.approx(90, abs=0.1) and g.valor("dx") == pytest.approx(4, abs=0.05)
    assert control(nuevo, "libre").punto == pytest.approx(
        nuevo.ctx.doc.estado_final.lienzos[ident]["plano"].a_3d(g.valor("dx"), 0), abs=0.05)


def test_lienzo_nuevo_sin_plano_no_muestra_asas_y_con_plano_si(ventana):  # noqa: F811
    ventana.set_documento(api.Sesion().doc)
    from omnicad.ui.comandos import CATALOGO
    ventana.ejecutar_comando(CATALOGO["lienzo"]())
    p = ventana.panel
    assert p.manipuladores.manips == []
    p.cancelar()


def test_api_insert_canvas_acepta_volteo_vertical_proporcion_y_escala(tmp_path):
    ruta = tmp_path / "foto.png"
    Image.new("RGB", (80, 40), "red").save(ruta)
    s = api.Sesion()
    r = llamar(s, "insert_canvas", path=str(ruta), width=40, height=10, keep_aspect=False, scale=2, flip_v=True)
    d = s.doc.estado_final.lienzos[r["feature"]["id"]]
    assert (d["ancho"], d["alto"], d["voltear_v"]) == (80, 20, True)
    r = llamar(s, "insert_canvas", path=str(ruta), width=40, height=10)       # con proporción, la altura sale del ancho
    assert s.doc.estado_final.lienzos[r["feature"]["id"]]["alto"] == 20
    for malo in ({"scale": 0}, {"height": -1}):
        assert not api.llamar(s, "insert_canvas", {"path": str(ruta), **malo})["ok"]
