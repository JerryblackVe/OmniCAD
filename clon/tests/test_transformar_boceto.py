"""Escala y Mover/copiar del boceto con su panel (BOC-41): valores escritos, vista previa, rechazos y equivalencia con la API.

El panel (`ui/panel_transformar.py`) y el controlador (`ui/transformar_boceto.py`) cambian el boceto con el mismo método
del núcleo que usa `transform_sketch` (MCP y CLI): lo que se ve en la vista previa es lo que queda."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402
from omnicad.ui.panel_transformar import PanelTransformar  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    panel = lz._panel_prueba = PanelTransformar()
    ctl = lz.transformar
    ctl.panel = panel
    panel.campo.connect(ctl.elegir_campo)
    panel.limpiar.connect(ctl.limpiar_campo)
    panel.cambio.connect(ctl.recibir)
    panel.previa.connect(ctl.set_previa)
    panel.aceptado.connect(ctl.aceptar)
    panel.cancelado.connect(ctl.cancelar)
    yield lz, panel, ctl
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy) if not isinstance(xy, QPointF) else xy
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def clic(lz, xy):
    _raton(lz, QEvent.MouseButtonPress, xy)
    _raton(lz, QEvent.MouseButtonRelease, xy)


def abrir(lz, herramienta, *ids):
    lz.seleccion = list(ids)
    lz.set_herramienta(herramienta)
    lz.encuadrar()
    QApplication.processEvents()


def test_escala_con_base_y_factor_escritos_cambia_la_linea_y_su_cota(ventana):
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((1, 1), (5, 1))
    lz.b.agregar_cota("distancia", [ln], "4")
    lz.resolver()
    abrir(lz, "escala", ln)
    assert ctl.campo == "base" and not panel.boton_ok.isEnabled()           # con la geometría lista pide el punto base
    panel.campos["base_x"].setText("1")
    panel.campos["base_y"].setText("1")
    panel.campos["factor"].setText("2.5")
    assert panel.boton_ok.isEnabled() and ctl.calcular()["polis"][0][-1] == pytest.approx((11, 1))
    panel.boton_ok.click()
    assert lz.b._extremos_linea(ln) == (pytest.approx((1, 1)), pytest.approx((11, 1)))
    assert next(iter(lz.b.cotas.values())).expresion == "10" and lz.resultado.ok
    assert lz.herramienta == "seleccionar"
    lz.deshacer()                                                          # UN paso de deshacer
    assert lz.b._extremos_linea(ln) == (pytest.approx((1, 1)), pytest.approx((5, 1)))


def test_escala_el_clic_en_el_punto_base_llena_los_campos(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    abrir(lz, "escala", c)
    clic(lz, (2.5, 4.0))
    assert ctl.base == (2.5, 4.0) and panel.campos["base_x"].text() == "2.5" and panel.campos["base_y"].text() == "4"
    panel.campos["factor"].setText("2")
    ctl.aceptar()
    assert lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((2.5 + 15, 4 - 8)) and lz.b.curvas[c].radio == 6


@pytest.mark.parametrize("texto", ["0", "-1", "", "abc", "1e300", "2/0"])
def test_escala_rechaza_factores_que_no_sirven_y_no_toca_el_boceto(ventana, texto):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    abrir(lz, "escala", c)
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    panel.campos["factor"].setText(texto)
    e = ctl.estado()
    assert not e["valido"] and "factor" in e["malos"] and e["error"]
    assert not panel.boton_ok.isEnabled() and panel.mensaje.text() == e["error"]
    assert not ctl.aceptar() and lz.b.curvas[c].radio == 3 and lz.herramienta == "escala"


def test_escala_sin_punto_base_dice_que_falta_y_no_acepta(ventana):
    lz, panel, ctl = ventana
    abrir(lz, "escala", lz.b.agregar_circulo((10, 0), 3))
    assert not ctl.estado()["valido"] and "punto base" in panel.guia.text()


def test_sin_geometria_elegida_pide_elegirla(ventana):
    lz, panel, ctl = ventana
    abrir(lz, "mover")
    assert ctl.campo == "seleccion" and not panel.boton_ok.isEnabled() and "Elegí la geometría" in panel.guia.text()


def test_mover_con_dx_dy_y_angulo_coincide_con_la_vista_previa(ventana):
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((10, 0), (20, 0))
    abrir(lz, "mover", ln)
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    panel.campos["dx"].setText("3")
    panel.campos["dy"].setText("-2")
    panel.campos["angulo"].setText("90")
    previa = ctl.calcular()["polis"][0]
    assert previa[0] == pytest.approx((3, 8)) and previa[-1] == pytest.approx((3, 18))
    ctl.aceptar()
    a, b = lz.b._extremos_linea(ln)
    assert a == pytest.approx((3, 8)) and b == pytest.approx((3, 18))


def test_mover_con_copiar_deja_el_original_y_recuerda_la_opcion(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    abrir(lz, "mover", c)
    ctl.base = (0.0, 0.0)
    panel.campos["dx"].setText("5")
    panel.campos["dy"].setText("3")
    panel.casillas["copiar"].setChecked(True)
    assert lz.opciones["copiar"] is True
    ctl.aceptar()
    centros = sorted(lz.b.coords(k.centro) for k in lz.b.curvas.values() if k.tipo == "circulo")
    assert centros == [pytest.approx((0, 0)), pytest.approx((5, 3))]
    lz.opciones["copiar"] = False


def test_mover_el_clic_en_el_destino_llena_dx_dy_y_la_vista_previa_lo_sigue(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    abrir(lz, "mover", c)
    clic(lz, (1.0, 1.0))                                                   # punto base
    assert ctl.base == (1.0, 1.0) and ctl.campo == "destino" and lz.fase == "destino"
    clic(lz, (6.0, -3.0))                                                  # destino
    assert panel.campos["dx"].text() == "5" and panel.campos["dy"].text() == "-4"
    assert panel.sel["destino"].boton.text() == "(6, -3)"
    ctl.aceptar()
    assert lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((5, -4))


def test_mover_sin_punto_base_gira_alrededor_del_centro_de_lo_elegido(ventana):
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((0, 0), (10, 0))
    abrir(lz, "mover", ln)
    panel.campos["angulo"].setText("90")
    assert panel.sel["base"].boton.text() == "Centro de la selección" and ctl.estado()["valido"]
    ctl.aceptar()
    a, b = lz.b._extremos_linea(ln)
    assert a == pytest.approx((5, -5)) and b == pytest.approx((5, 5))


@pytest.mark.parametrize("campo,texto", [("dx", ""), ("dy", "x"), ("angulo", "1/0"), ("dx", "1e300")])
def test_mover_rechaza_valores_que_no_sirven(ventana, campo, texto):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    abrir(lz, "mover", c)
    panel.campos[campo].setText(texto)
    assert campo in ctl.estado()["malos"] and not panel.boton_ok.isEnabled()
    assert not ctl.aceptar() and lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((0, 0))


def test_geometria_fija_se_rechaza_en_el_panel_antes_de_aceptar(ventana):
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((0, 0), (10, 0))
    lz.b.agregar_restriccion("fijo", [ln])
    abrir(lz, "mover", ln)
    panel.campos["dx"].setText("4")
    e = ctl.estado()
    assert not e["valido"] and "fija" in e["error"] and not panel.boton_ok.isEnabled()


def test_cancelar_y_esc_no_tocan_el_boceto_y_vuelven_a_seleccionar(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    abrir(lz, "mover", c)
    panel.campos["dx"].setText("9")
    panel.cancelado.emit()
    assert lz.herramienta == "seleccionar" and lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((0, 0))
    abrir(lz, "escala", c)
    lz.cancelar()                                                          # Esc
    assert lz.herramienta == "seleccionar" and lz.b.curvas[c].radio == 2


def test_enter_con_la_geometria_lista_pasa_al_punto_base_y_con_todo_bien_acepta(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    lz.set_herramienta("mover")
    assert ctl.campo == "seleccion"
    lz.seleccion = [c]
    ctl.enter()                                                            # Enter con lo elegido → punto base
    assert ctl.campo == "base"
    panel.campos["dx"].setText("2")
    ctl.enter()                                                            # Enter con todo bien → acepta
    assert lz.herramienta == "seleccionar" and lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((2, 0))


def test_enter_y_esc_dentro_de_un_campo_aceptan_y_cancelan(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((0, 0), 2)
    abrir(lz, "mover", c)
    panel.campos["dx"].setText("2")
    panel.campos["dx"].aceptar.emit()
    assert lz.b.coords(lz.b.curvas[c].centro) == pytest.approx((2, 0))
    abrir(lz, "mover", c)
    panel.campos["dx"].cancelar.emit()
    assert lz.herramienta == "seleccionar"


def test_el_asa_del_factor_escribe_en_el_campo_del_panel(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    abrir(lz, "escala", c)
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    panel.campos["factor"].setText("1")
    ctl._emitir()
    assert len(lz._asas.asas) == 1
    p = lz._asas.asas[0].posicion(lz._asas.valores())
    _raton(lz, QEvent.MouseButtonPress, p)
    for k in range(1, 7):
        _raton(lz, QEvent.MouseMove, (p[0] * (1 + k / 6), 0), Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, (p[0] * 2, 0))
    assert float(panel.campos["factor"].text()) == pytest.approx(2, abs=0.05)
    p = lz._asas.asas[0].posicion(lz._asas.valores())
    _raton(lz, QEvent.MouseButtonPress, p)
    _raton(lz, QEvent.MouseMove, (-30, 0), Qt.LeftButton)                  # del otro lado del punto base: tope positivo
    _raton(lz, QEvent.MouseButtonRelease, (-30, 0))
    assert float(panel.campos["factor"].text()) > 0
    lz.cancelar()


def _arrastrar(lz, desde, hasta, pasos=6):
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, pasos + 1):
        t = k / pasos
        _raton(lz, QEvent.MouseMove, (desde[0] + (hasta[0] - desde[0]) * t, desde[1] + (hasta[1] - desde[1]) * t), Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def _mover_con_base(ventana):
    lz, panel, ctl = ventana
    ln = lz.b.agregar_linea((10, 0), (20, 0))
    abrir(lz, "mover", ln)
    ctl.base = (0.0, 0.0)
    ctl._texto_base()
    ctl._emitir()
    return lz, panel, ctl, ln


def test_el_asa_de_mover_escribe_dx_y_dy_a_la_vez_y_la_vista_previa_la_sigue(ventana):
    lz, panel, ctl, ln = _mover_con_base(ventana)
    asas = lz._asas.asas
    assert len(asas) == 2 and asas[0].campo == (0, 1) and asas[1].campo == 2
    assert asas[0].posicion(lz._asas.valores()) == pytest.approx((0, 0))            # sin desplazar, sobre el punto base
    _arrastrar(lz, (0, 0), (7, -4))
    assert float(panel.campos["dx"].text()) == pytest.approx(7) and float(panel.campos["dy"].text()) == pytest.approx(-4)
    assert asas[0].posicion(lz._asas.valores()) == pytest.approx((7, -4)) and lz._asas.asas is asas       # el asa quedó en el destino
    assert ctl.calcular()["polis"][0][0] == pytest.approx((17, -4))
    ctl.aceptar()
    a, b = lz.b._extremos_linea(ln)
    assert a == pytest.approx((17, -4)) and b == pytest.approx((27, -4))


def test_el_asa_de_giro_de_mover_gira_alrededor_del_punto_base_desplazado(ventana):
    lz, panel, ctl, ln = _mover_con_base(ventana)
    panel.campos["dx"].setText("5")
    panel.campos["dy"].setText("5")
    giro = lz._asas.asas[1]
    p = giro.posicion(lz._asas.valores())
    assert p == pytest.approx((5 + 20, 5))                                           # a 20 mm (lo más lejano de la selección)
    _arrastrar(lz, p, (5, 25))                                                        # hacia arriba: 90°
    assert float(panel.campos["angulo"].text()) == pytest.approx(90)
    assert ctl.calcular()["polis"][0][0] == pytest.approx((5, 15)) and ctl.calcular()["polis"][0][-1] == pytest.approx((5, 25))
    panel.campos["angulo"].setText("400")                                            # varias vueltas: sigue en la misma
    p = giro.posicion(lz._asas.valores())
    _arrastrar(lz, p, (5 + 20 * math.cos(math.radians(50)), 5 + 20 * math.sin(math.radians(50))))
    assert float(panel.campos["angulo"].text()) == pytest.approx(410)
    lz.cancelar()


def test_sin_punto_base_elegido_no_hay_asas_y_el_clic_en_el_centro_fija_la_base(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    abrir(lz, "mover", c)
    assert ctl.campo == "base" and lz._asas is None                              # el asa del centro taparía el clic de la base
    clic(lz, (10, 0))
    assert ctl.base == (10.0, 0.0) and ctl.campo == "destino" and len(lz._asas.asas) == 2


def test_las_asas_de_mover_siguen_al_punto_base_y_a_lo_elegido(ventana):
    lz, panel, ctl, ln = _mover_con_base(ventana)
    ctl.base = (3.0, 4.0)
    ctl._texto_base()
    ctl._emitir()
    assert lz._asas.asas[0].posicion(lz._asas.valores()) == pytest.approx((3, 4))
    panel.campos["dx"].setText("not-a-number")                                       # a medio escribir: las asas se retiran sin romper
    ctl._emitir()
    assert lz._asas is None
    lz.cancelar()
    assert lz._asas is None


def test_cambiar_de_herramienta_cierra_el_panel_y_las_asas(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((10, 0), 3)
    abrir(lz, "escala", c)
    ctl.base = (0.0, 0.0)
    ctl._emitir()
    assert lz._asas is not None
    lz.set_herramienta("linea")
    assert lz._asas is None and ctl.tipo is None and not ctl.activo


def test_la_vista_previa_se_apaga_con_su_casilla(ventana):
    lz, panel, ctl = ventana
    abrir(lz, "mover", lz.b.agregar_circulo((0, 0), 2))
    panel.casilla_previa.setChecked(False)
    assert ctl.previa is False
    panel.casilla_previa.setChecked(True)
    assert ctl.previa is True


def _api_circulo():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    api.llamar(s, "draw_circle", {"sketch": "U", "center_x": 4, "center_y": 1, "radius": 2})
    return s


def _circulos(s):
    r = api.llamar(s, "get_sketch", {"sketch": "U"})["result"]
    return sorted((tuple(round(v, 4) for v in e["center"]), round(e["radius"], 4)) for e in r["entities"]
                  if e["type"] == "circle")


def test_el_panel_hace_lo_mismo_que_transform_sketch_con_los_mismos_valores(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((4, 1), 2)
    abrir(lz, "escala", c)
    ctl.base = (1.0, -1.0)
    ctl._texto_base()
    ctl._emitir()
    panel.campos["factor"].setText("1.5")
    ctl.aceptar()
    abrir(lz, "mover", c)
    ctl.base = (1.0, -1.0)
    ctl._texto_base()
    ctl._emitir()
    for k, v in (("dx", "3"), ("dy", "-2"), ("angulo", "30")):
        panel.campos[k].setText(v)
    panel.casillas["copiar"].setChecked(True)
    ctl.aceptar()
    lz.opciones["copiar"] = False
    ventana_ = sorted((tuple(round(v, 4) for v in lz.b.coords(k.centro)), round(k.radio, 4))
                      for k in lz.b.curvas.values() if k.tipo == "circulo")
    s = _api_circulo()
    r = api.llamar(s, "transform_sketch", {"sketch": "U", "scale": 1.5, "center_x": 1, "center_y": -1})
    assert r["ok"], r
    r = api.llamar(s, "transform_sketch", {"sketch": "U", "dx": 3, "dy": -2, "angle": 30, "center_x": 1, "center_y": -1,
                                           "copy": True})
    assert r["ok"], r
    assert len(ventana_) == 2 and ventana_ == _circulos(s)
    assert math.isclose(ventana_[0][1], 3.0)


def test_borrar_los_dos_campos_de_la_base_quita_el_punto_base(ventana):
    lz, panel, ctl = ventana
    abrir(lz, "escala", lz.b.agregar_circulo((10, 0), 3))
    panel.campos["base_x"].setText("1")
    panel.campos["base_y"].setText("2")
    assert ctl.base == (1.0, 2.0)
    panel.campos["base_x"].setText("")
    assert ctl.base == (1.0, 2.0)                                          # con uno solo borrado todavía vale el último par
    panel.campos["base_y"].setText("")
    assert ctl.base is None and not panel.boton_ok.isEnabled()


def test_b245_mover_lo_anclado_al_origen_no_acepta_en_silencio(ventana):
    from test_boceto_modificar_restringido import _crear
    lz, panel, ctl = ventana
    s, curvas = _crear("ranura")                    # ranura acotada con el centro coincidente con el origen
    lz._restaurar(next(o for o in s.doc.operaciones if hasattr(o, "boceto")).boceto.a_dict())
    lz.resolver()
    p = lz.b.curvas[curvas[0]].puntos()[0]
    antes, pasos, mensajes = lz.b.coords(p), len(lz.historial), []
    lz.mensaje.connect(mensajes.append)
    abrir(lz, "mover", *curvas)
    panel.campos["dx"].setText("200")
    assert not ctl.aceptar()
    assert lz.b.coords(p) == pytest.approx(antes) and len(lz.historial) == pasos
    assert "origen" in mensajes[-1] and lz.herramienta == "mover"
