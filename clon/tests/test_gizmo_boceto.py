"""Asas de arrastre del editor de boceto (ui/asas_boceto.py): tirar de un asa escribe en la caja de valores."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


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


def _raton(lz, tipo, xy, botones=Qt.LeftButton):
    q = lz.a_px(*xy) if not isinstance(xy, QPointF) else xy
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton,
                                           botones if tipo != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier))


def arrastrar(lz, desde, hasta):
    """Press en `desde` (mm), mueve en tramos y suelta en `hasta` (mm), con eventos al widget."""
    _raton(lz, QEvent.MouseButtonPress, desde)
    for k in range(1, 7):
        punto = (desde[0] + (hasta[0] - desde[0]) * k / 6, desde[1] + (hasta[1] - desde[1]) * k / 6)
        _raton(lz, QEvent.MouseMove, punto, Qt.LeftButton)
    _raton(lz, QEvent.MouseButtonRelease, hasta)


def posicion(lz, i):
    asa = lz._asas.asas[i]
    return asa.posicion(lz._asas.valores())


def abrir(lz, herramienta, centro=None):
    """Abre la herramienta de patrón con su panel (sin mostrarlo), con un círculo elegido; con `centro`, el circular ya lo tiene."""
    from omnicad.ui.panel_patron import PanelPatron
    c = lz.b.agregar_circulo((20, 0) if herramienta == "patron_circular" else (0, 0), 3)
    panel = lz._panel_prueba = PanelPatron()
    ctl = lz.patron
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    panel.aceptado.connect(ctl.aceptar)
    panel.cancelado.connect(ctl.cancelar)
    lz.seleccion = [c]
    lz.set_herramienta(herramienta)
    if centro is not None:
        ctl.centro = centro
        ctl._emitir()
    lz.encuadrar()
    QApplication.processEvents()
    return panel


def textos(lz):
    return [c.text() for c in lz.entrada.campos]


def test_patron_rectangular_asas_de_distancia_y_cantidad(lienzo):
    lz = lienzo
    panel = abrir(lz, "patron_rectangular")
    assert lz._asas is not None and len(lz._asas.asas) == 3           # distancia, cantidad y ángulo de la dirección 1
    panel.campos["cantidad1"].setText("3")
    panel.campos["distancia1"].setText("20")                           # Extensión: la última copia queda a 20 mm
    assert posicion(lz, 0) == pytest.approx((20, 0), abs=1e-6)
    arrastrar(lz, posicion(lz, 0), (30, 0))
    assert float(panel.campos["distancia1"].text()) == pytest.approx(30, abs=0.3)      # escribe en el campo del panel
    # cantidad: tirar hacia afuera suma copias, de a una por paso
    paso = float(panel.campos["distancia1"].text()) / (int(panel.campos["cantidad1"].text()) - 1)
    arrastrar(lz, posicion(lz, 1), (posicion(lz, 1)[0] + 2 * paso, posicion(lz, 1)[1]))
    assert int(panel.campos["cantidad1"].text()) == 5
    arrastrar(lz, posicion(lz, 1), (-500, posicion(lz, 1)[1]))                 # pasa por cero y por debajo: mínimo 1
    assert int(panel.campos["cantidad1"].text()) == 1
    lz.patron.cancelar()
    assert lz._asas is None


def test_patron_rectangular_asa_de_angulo_gira_la_fila_sin_rearmar_las_asas(lienzo):
    """BOC-62: el asa del ángulo escribe en «Ángulo 1», y las asas siguen siendo las mismas mientras se arrastra."""
    lz = lienzo
    panel = abrir(lz, "patron_rectangular")
    panel.campos["cantidad1"].setText("3")
    panel.campos["distancia1"].setText("20")
    gestor = lz._asas
    centro = gestor.asas[2].ancla(None)                                  # la tercera asa es la del ángulo
    arrastrar(lz, posicion(lz, 2), (centro[0], centro[1] + 30))
    assert float(panel.campos["angulo1"].text()) == pytest.approx(90, abs=0.6)
    assert lz._asas is gestor                                            # la clave no incluye la dirección que se gira
    assert posicion(lz, 0) == pytest.approx((centro[0], centro[1] + 20), abs=0.2)   # la asa de distancia sigue la nueva fila
    lz.patron.cancelar()


def test_patron_rectangular_eje_y_vista_previa(lienzo):
    lz = lienzo
    panel = abrir(lz, "patron_rectangular")
    panel.casillas["dos"].setChecked(True)
    panel.campos["cantidad2"].setText("2")
    panel.campos["distancia2"].setText("15")
    assert len(lz._asas.asas) == 6                                     # distancia y cantidad de cada dirección, y sus dos ángulos
    arrastrar(lz, posicion(lz, 2), (0, 25))
    assert float(panel.campos["distancia2"].text()) == pytest.approx(25, abs=0.3)
    assert len(lz.patron.calcular()["polis"]) == 3 * 2 - 1                  # 3 x 2 copias menos el original
    lz.patron.cancelar()


def test_teclear_mueve_el_asa_y_un_valor_invalido_no_la_rompe(lienzo):
    lz = lienzo
    panel = abrir(lz, "patron_rectangular")
    antes = posicion(lz, 0)
    panel.campos["distancia1"].setText("45")
    assert posicion(lz, 0) != antes
    panel.campos["distancia1"].setText("4+")                   # a medio escribir: sin valores no hay asas, y nada se rompe
    assert lz._asas is None
    QApplication.processEvents()
    lz.repaint()
    panel.campos["distancia1"].setText("45")
    assert posicion(lz, 0) == pytest.approx((45, 0), abs=1e-6)
    lz.patron.cancelar()


def test_enter_aplica_lo_arrastrado_y_esc_cancela(lienzo):
    lz = lienzo
    panel = abrir(lz, "patron_rectangular")
    panel.campos["cantidad1"].setText("2")
    panel.campos["distancia1"].setText("10")
    arrastrar(lz, posicion(lz, 0), (18, 0))
    n0 = len(lz.b.curvas)
    QTest.keyClick(panel.campos["cantidad1"], Qt.Key_Return)
    assert len(lz.b.curvas) == n0 + 1 and lz.b.patrones[0]["params"]["distancia1"] == pytest.approx(18, abs=0.3)
    panel = abrir(lz, "patron_rectangular")
    QTest.keyClick(panel.campos["cantidad1"], Qt.Key_Escape)
    assert lz.patron.tipo is None and lz._asas is None and lz.herramienta == "seleccionar"


def test_patron_circular_angulo_y_cantidad(lienzo):
    lz = lienzo
    panel = abrir(lz, "patron_circular", centro=(0.0, 0.0))
    assert len(lz._asas.asas) == 2
    panel.campos["cantidad"].setText("4")
    panel.combos["distribucion"].setCurrentIndex(panel.combos["distribucion"].findData("parcial"))
    panel.campos["angulo_total"].setText("90")
    assert posicion(lz, 0) == pytest.approx((0.0, 20.0), abs=1e-6)          # el final del arco, a 90°
    arrastrar(lz, posicion(lz, 0), (-20 * math.cos(math.radians(30)), 20 * math.sin(math.radians(30))))
    assert float(panel.campos["angulo_total"].text().replace(",", ".")) == pytest.approx(150, abs=1.5)
    arrastrar(lz, posicion(lz, 0), (20, 0))
    t = float(panel.campos["angulo_total"].text().replace(",", "."))
    assert t == pytest.approx(0, abs=1.5) or t == pytest.approx(360, abs=1.5)
    panel.campos["angulo_total"].setText("90")
    p = posicion(lz, 1)
    assert int(panel.campos["cantidad"].text()) == 4
    a = math.atan2(p[1], p[0]) + math.radians(60)                # dos pasos de 30° más allá de la última copia
    r = math.hypot(*p)
    arrastrar(lz, p, (r * math.cos(a), r * math.sin(a)))
    assert int(panel.campos["cantidad"].text()) == 6
    assert len(lz.patron.calcular()["polis"]) == 5          # seis copias menos el original
    lz.patron.cancelar()


def _esquina(lz, herramienta):
    a = lz.b.agregar_linea((0, 0), (30, 0))
    b = lz.b.agregar_linea((0, 0), (0, 30))
    lz.set_herramienta(herramienta)
    lz.agregar_pick(a, (15.0, 0.0), QPointF(0, 0))
    lz.agregar_pick(b, (0.0, 15.0), QPointF(0, 0))
    lz.encuadrar()
    QApplication.processEvents()
    return a, b


def test_empalme_el_asa_del_arco_cambia_el_radio_y_pasa_por_cero(lienzo):
    lz = lienzo
    _esquina(lz, "empalme")
    assert len(lz._asas.asas) == 1
    lz.entrada.campos[0].setText("5")
    m = 5 - 5 / math.sqrt(2)
    assert posicion(lz, 0) == pytest.approx((m, m), abs=0.05)
    k = 10 - 10 / math.sqrt(2)
    arrastrar(lz, posicion(lz, 0), (k, k))
    assert float(textos(lz)[0]) == pytest.approx(10, abs=0.3)
    arrastrar(lz, posicion(lz, 0), (-8.0, -8.0))                # del otro lado de la esquina: nunca cero ni negativo
    assert float(textos(lz)[0]) > 0
    lz.entrada.campos[0].setText("8")
    assert len(lz._asas.previa(lz._asas.valores())) == 1
    n0 = len(lz.b.curvas)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert len(lz.b.curvas) == n0 + 1
    assert lz._asas is None


def test_empalme_con_radio_imposible_no_rompe_el_dibujo(lienzo):
    lz = lienzo
    _esquina(lz, "empalme")
    lz.entrada.campos[0].setText("500")                         # más grande que las líneas: sin vista previa, sin excepción
    lz.repaint()
    assert lz._asas.previa(lz._asas.valores()) == []
    lz._cerrar_entrada()


@pytest.mark.parametrize("herramienta,n", [("chaflan", 1), ("chaflan_dos_dist", 2), ("chaflan_dist_angulo", 2)])
def test_chaflan_asas_en_los_extremos_del_corte(lienzo, herramienta, n):
    lz = lienzo
    _esquina(lz, herramienta)
    assert len(lz._asas.asas) == n
    lz.entrada.campos[0].setText("6")
    if n == 2:
        lz.entrada.campos[1].setText("8" if herramienta == "chaflan_dos_dist" else "45")
    if herramienta == "chaflan":
        p = posicion(lz, 0)
        assert p == pytest.approx((3, 3), abs=0.05)                      # el medio de la línea de 6 y 6
        arrastrar(lz, p, (5, 5))
    else:
        p = posicion(lz, 0)
        assert p == pytest.approx((6, 0), abs=0.05)                      # el extremo sobre la primera línea
        arrastrar(lz, p, (10, 0))
    assert float(textos(lz)[0]) == pytest.approx(10, abs=0.3)
    if n == 2:
        q = posicion(lz, 1)
        if herramienta == "chaflan_dos_dist":
            assert q == pytest.approx((0, 8), abs=0.05)
            arrastrar(lz, q, (0, 12))
            assert float(textos(lz)[1]) == pytest.approx(12, abs=0.3)
        else:
            arrastrar(lz, q, (0, 10))                                    # el otro extremo cae sobre la segunda línea: 45° → atan(10/10)
            assert 0 < float(textos(lz)[1]) < 180
    lz._cerrar_entrada()


@pytest.mark.parametrize(("herramienta", "segundo", "tipo"), [("chaflan_dos_dist", "d2", "distancia"),
                                                             ("chaflan_dist_angulo", "ang", "angulo")])
def test_b235_el_segundo_valor_del_chaflan_sigue_a_su_parametro(app, herramienta, segundo, tipo):
    from omnicad.timeline.parametros import ANGULO
    tabla = TablaParametros()
    tabla.agregar("d1", "6 mm")
    tabla.agregar("d2", "8 mm")
    tabla.agregar("ang", "30 deg", ANGULO)
    lz = editor_boceto.Lienzo(Boceto(), tabla.evaluar)
    lz.ajustar_grilla = False
    _esquina(lz, herramienta)
    lz.entrada.campos[0].setText("d1")                       # se teclean los nombres de los parámetros
    lz.entrada.campos[1].setText(segundo)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    textos_cotas = {(c.tipo, c.expresion) for c in lz.b.cotas.values()}
    assert ("distancia", "d1") in textos_cotas
    assert any(t == tipo and segundo in e for t, e in textos_cotas)     # antes: «8» o «30», sin el parámetro
    lz.close()


def test_texto_asa_de_giro_del_marco(lienzo):
    lz = lienzo
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 0.0)))
    lz.clics.append((None, (40.0, 10.0)))
    lz._procesar_clics()
    lz.encuadrar()
    assert lz._asas is not None and len(lz._asas.asas) == 1
    ancla = (0.0, 10.0)                                                  # la esquina de arriba a la izquierda del marco
    assert posicion(lz, 0) == pytest.approx((ancla[0] + 40.0, ancla[1]), abs=1e-6)
    arrastrar(lz, posicion(lz, 0), (ancla[0] + 20.0, ancla[1] + 20.0))
    assert float(textos(lz)[2]) == pytest.approx(45, abs=1.0)
    arrastrar(lz, posicion(lz, 0), (ancla[0] - 30.0, ancla[1] + 5.0))
    assert float(textos(lz)[2]) == pytest.approx(math.degrees(math.atan2(5, -30)), abs=1.0)
    lz.entrada.campos[2].setText("90")
    assert posicion(lz, 0) == pytest.approx((ancla[0], ancla[1] + 40.0), abs=1e-6)
    lz._cerrar_entrada()


@pytest.fixture
def ventana_p71(app):
    """Editor real con eventos al widget: también puede correrse con Qt nativo sin tomar el foco de Windows."""
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.setWindowFlag(Qt.WindowDoesNotAcceptFocus)
    lz.setAttribute(Qt.WA_ShowWithoutActivating)
    lz.setAttribute(Qt.WA_TransparentForMouseEvents)
    lz.setWindowOpacity(0)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _clic_p71(lz, xy):
    _raton(lz, QEvent.MouseMove, xy, Qt.NoButton)
    _raton(lz, QEvent.MouseButtonPress, xy)
    _raton(lz, QEvent.MouseButtonRelease, xy)


def _teclear_p71(campo, texto):
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, texto)


@pytest.mark.parametrize("paralelas,radio", [(True, "3"), (True, "5"), (False, "3")])
def test_p71_empalme_avisa_el_mismo_radio_que_el_mcp(ventana_p71, paralelas, radio):
    from omnicad import api

    lz = ventana_p71
    segmentos = [((0, 0), (30, 0)), ((0, 10), (30, 10)) if paralelas else ((0, 0), (0, 30))]
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "B"})["ok"]
    ids = []
    for inicio, fin in segmentos:
        lz.b.agregar_linea(inicio, fin)
        r = api.llamar(s, "draw_line", {"sketch": "B", "start_x": inicio[0], "start_y": inicio[1],
                                        "end_x": fin[0], "end_y": fin[1]})
        assert r["ok"], r
        ids.append(r["result"]["entities"][0]["id"])
    lz.resolver()
    antes = lz.b.a_dict()
    lz.encuadrar()
    lz.set_herramienta("empalme")
    puntos = [(15, 0), (15, 10) if paralelas else (0, 15)]
    for xy in puntos:
        _clic_p71(lz, xy)
    assert lz.entrada is not None and len(lz.picks) == 2
    avisos = []
    lz.aviso.connect(avisos.append)
    campo = lz.entrada.campos[0]
    _teclear_p71(campo, radio)
    assert campo.text() == radio
    assert lz.b.a_dict() == antes                      # la previa no aplica ni avisa
    assert not avisos
    QTest.keyClick(campo, Qt.Key_Return)
    arcos = [i for i in lz.b.curvas if lz.b.tipo_de(i) == "arco"]
    assert len(arcos) == 1 and lz.resultado.ok
    assert lz.b.radio(arcos[0]) == pytest.approx(5 if paralelas else float(radio))
    r = api.llamar(s, "sketch_fillet", {"sketch": "B", "entity1": ids[0], "entity2": ids[1],
                                         "radius": radio, "point1": puntos[0], "point2": puntos[1]})
    assert r["ok"], r
    esperado = (["Entre líneas paralelas el radio es la mitad de su separación: 5 mm; se ignoró el radio pedido."]
                if paralelas and radio == "3" else [])
    assert r.get("avisos", []) == esperado
    assert avisos == esperado
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_p71_soltar_desfase_borra_la_cota_sin_dialogo_como_fusion(ventana_p71):
    from PySide6.QtWidgets import QToolButton
    from omnicad.ui.modo_boceto import ModoBoceto

    lz = ventana_p71
    linea = lz.b.agregar_linea((0, 0), (30, 0))
    lz.resolver()
    lz.encuadrar()
    lz.set_herramienta("desfase")
    _clic_p71(lz, (15, 0))
    campo = lz.entrada.campos[0]
    _teclear_p71(campo, "10")
    QTest.keyClick(campo, Qt.Key_Return)
    copia = next(i for i in lz.b.curvas if i != linea)
    assert len(lz.b.cotas) == 1 and any(r.tipo == "desfase" for r in lz.b.restricciones.values())
    antes = lz.b.a_dict()
    lz.set_herramienta("seleccionar")
    lz.encuadrar()
    a, b = lz.b._extremos_linea(copia)
    _clic_p71(lz, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    assert copia in lz.seleccion
    modo = ModoBoceto(lz)
    modo.lienzo = lz
    accion = modo.acciones["sk_soltar_desfase"]
    accion.setEnabled(True)
    boton = QToolButton(lz)
    boton.setDefaultAction(accion)
    boton.show()
    QTest.mouseClick(boton, Qt.LeftButton)
    assert len(lz.b.curvas) == 2 and not lz.b.cotas
    assert not any(r.tipo in ("desfase", "paralela") for r in lz.b.restricciones.values())
    assert QApplication.activeModalWidget() is None
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_p71_escala_exige_base_y_la_api_ofrece_el_centro_automatico(ventana_p71):
    from omnicad import api
    from omnicad.ui.panel_transformar import PanelTransformar

    lz = ventana_p71
    linea = lz.b.agregar_linea((10, 10), (30, 10))
    lz.resolver()
    lz.encuadrar()
    _clic_p71(lz, (20, 10))
    assert linea in lz.seleccion
    panel = PanelTransformar(lz)
    ctl = lz.transformar
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    panel.aceptado.connect(ctl.aceptar)
    lz.set_herramienta("escala")
    antes = lz.b.a_dict()
    _teclear_p71(panel.campos["factor"], "2")
    assert not panel.boton_ok.isEnabled() and "punto base" in panel.guia.text()
    QTest.keyClick(panel.campos["factor"], Qt.Key_Return)
    assert lz.b.a_dict() == antes and lz.herramienta == "escala"
    _clic_p71(lz, (10, 10))
    assert ctl.base == pytest.approx((10, 10)) and panel.boton_ok.isEnabled()
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    assert lz.b._extremos_linea(linea) == (pytest.approx((10, 10)), pytest.approx((50, 10)))
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "B"})["ok"]
    assert api.llamar(s, "draw_line", {"start_x": 10, "start_y": 10, "end_x": 30, "end_y": 10})["ok"]
    r = api.llamar(s, "transform_sketch", {"scale": 2})
    assert r["ok"], r
    entidad = api.llamar(s, "get_sketch", {})["result"]["entities"][0]
    assert entidad["start"] == pytest.approx((0, 10)) and entidad["end"] == pytest.approx((40, 10))


@pytest.mark.parametrize("y", [10, -10])
def test_h108_linea_arrastrar_desde_el_extremo_hace_arco_tangente_y_sigue(ventana_p71, y):
    """BOC-12 por eventos: Línea → arco tangente a cada lado → Línea, sin cortar la cadena."""
    lz = ventana_p71
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.set_herramienta("linea")
    _clic_p71(lz, (0, 0))
    _clic_p71(lz, (20, 0))
    assert len(lz.b.curvas) == 1
    linea = next(iter(lz.b.curvas.values()))
    assert linea.tipo == "linea"
    assert lz.b._extremos_linea(linea.id) == (pytest.approx((0, 0)), pytest.approx((20, 0)))

    arrastrar(lz, (20, 0), (30, y))
    assert len(lz.b.curvas) == 2
    arco = next(c for c in lz.b.curvas.values() if c.tipo == "arco")
    assert linea.p2 in arco.extremos()
    fin = next(p for p in arco.extremos() if p != linea.p2)
    assert lz.b.coords(linea.p2) == pytest.approx((20, 0))
    assert lz.b.coords(fin) == pytest.approx((30, y))
    assert lz.b.coords(arco.centro) == pytest.approx((20, y))  # radio perpendicular a la línea en la unión
    assert lz.b.radio(arco.id) == pytest.approx(10)
    assert any(r.tipo == "tangente" and set(r.entidades) == {linea.id, arco.id}
               for r in lz.b.restricciones.values())
    assert lz.resultado.ok and lz.herramienta == "linea"
    assert lz.clics == [(fin, pytest.approx((30, y)))]
    assert mensajes[-1] == "Arco tangente creado. Seguí con la línea o Esc."

    _clic_p71(lz, (30, 30))
    assert len(lz.b.curvas) == 3
    siguiente = next(c for c in lz.b.curvas.values() if c.id not in (linea.id, arco.id))
    assert siguiente.tipo == "linea" and siguiente.p1 == fin
    assert lz.b._extremos_linea(siguiente.id) == (pytest.approx((30, y)), pytest.approx((30, 30)))
    assert lz.resultado.ok and lz.herramienta == "linea"
