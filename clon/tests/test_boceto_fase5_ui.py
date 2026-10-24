"""BOC-9: inferencias al dibujar con eventos de ratón simulados, sin mover el cursor real."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto, ErrorBoceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
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


def _objetivo(lz, circulo=False):
    cid = lz.b.agregar_circulo((20, 20), 10) if circulo else lz.b.agregar_linea((11, 20), (52, 20))
    lz.b.agregar_restriccion("fijo", [cid])
    lz.resolver()
    lz.set_herramienta("linea")
    return cid


@pytest.mark.parametrize("mods,tipo", [(Qt.NoModifier, "punto_medio"), (Qt.ShiftModifier, "coincidente")])
@pytest.mark.parametrize("primero", [False, True])
def test_boc9_medio_con_mayus_y_en_ambos_extremos(lienzo, mods, tipo, primero):
    lz = lienzo
    objetivo = _objetivo(lz)
    lz.ajustar_grilla = True
    antes = lz.b.a_dict()
    clics = [((31.8, 20.2), mods), ((37, 43), Qt.NoModifier)]
    for xy, modificadores in clics if primero else reversed(clics):
        _clic(lz, *xy, modificadores)
    linea = lz.b.curvas[lz._ultima_linea]
    extremo = linea.p1 if primero else linea.p2
    assert lz.b.coords(extremo) == pytest.approx((31.5, 20), abs=1e-8)
    assert any(r.tipo == tipo and r.entidades == [extremo, objetivo] for r in lz.b.restricciones.values())
    assert lz.resultado.ok
    assert len(lz.historial) == 1
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_boc9_extremo_sobre_circulo(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz, circulo=True)
    _clic(lz, 40, 45)
    _clic(lz, 26.2, 28.1)
    linea = lz.b.curvas[lz._ultima_linea]
    assert math.dist(lz.b.coords(linea.p2), (20, 20)) == pytest.approx(10, abs=1e-8)
    assert any(r.tipo == "coincidente" and r.entidades == [linea.p2, objetivo]
               for r in lz.b.restricciones.values())
    assert lz.resultado.ok


def test_boc9_tangente_desde_base_exterior(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz, circulo=True)
    _clic(lz, 40, 20)
    contacto = (25, 20 + math.sqrt(75))
    _mover(lz, contacto[0] + 0.2, contacto[1] + 0.1)
    assert lz.inf_actual.tipo == "tangente"
    assert lz.inf_actual.guias == [((40, 20), contacto)]
    _clic(lz, contacto[0] + 0.2, contacto[1] + 0.1)
    linea = lz.b.curvas[lz._ultima_linea]
    a, b = lz.b._extremos_linea(linea.id)
    assert b == pytest.approx(contacto, abs=1e-8)
    assert abs(sum((b[i] - (20, 20)[i]) * (b[i] - a[i]) for i in range(2))) < 1e-6
    assert any(r.tipo == "tangente" and r.entidades == [linea.id, objetivo]
               for r in lz.b.restricciones.values())
    assert lz.resultado.ok


def test_boc9_perpendicular_incluye_coincidencia_del_pie(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz)
    _clic(lz, 23, 45)
    _clic(lz, 23.2, 20.2)
    linea = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(linea.p2) == pytest.approx((23, 20), abs=1e-8)
    assert any(r.tipo == "perpendicular" and r.entidades == [linea.id, objetivo]
               for r in lz.b.restricciones.values())
    assert any(r.tipo == "coincidente" and r.entidades == [linea.p2, objetivo]
               for r in lz.b.restricciones.values())
    assert lz.resultado.ok


def test_boc9_punto_existente_y_origen_ganan_y_limpian_inferencia(lienzo):
    lz = lienzo
    _objetivo(lz)
    punto = lz.b.agregar_punto(30, 21)
    _mover(lz, 19, 20.1)
    assert lz.inf_actual is not None
    pid, xy = lz._ajustar(lz.a_px(30.1, 20.1))
    assert pid == punto and xy == (30, 21)
    assert lz.inf_actual is None
    assert lz._ajustar(lz.a_px(0.1, 0.1)) == (None, (0, 0))
    assert lz.inf_actual is None


@pytest.mark.parametrize("rechazo", ["validacion", "solver"])
def test_boc9_inferencia_rechazada_conserva_geometria_y_un_deshacer(lienzo, monkeypatch, rechazo):
    lz = lienzo
    objetivo = _objetivo(lz)
    antes = lz.b.a_dict()
    agregar = lz.b.agregar_restriccion
    intentos = []

    def rechazar(tipo, entidades, datos=None):
        if tipo == "punto_medio":
            intentos.append(tipo)
            if rechazo == "validacion":
                raise ErrorBoceto("Conflicto simulado de inferencia")
            return agregar("coincidente", [entidades[0], lz.b.curvas[objetivo].p1])
        return agregar(tipo, entidades, datos)

    monkeypatch.setattr(lz.b, "agregar_restriccion", rechazar)
    _clic(lz, 37, 43)
    # Dos anclajes incompatibles en el extremo solo en el caso de rechazo por solver.
    if rechazo == "solver":
        original = lz.b.agregar_linea

        def crear(*args, **kwargs):
            cid = original(*args, **kwargs)
            agregar("fijo", [lz.b.curvas[cid].p2])
            return cid

        monkeypatch.setattr(lz.b, "agregar_linea", crear)
    _clic(lz, 31.7, 20.1)
    assert intentos == ["punto_medio"]
    assert len(lz.b.curvas) == 2
    assert lz.b.coords(lz.b.curvas[lz._ultima_linea].p2) == pytest.approx((31.5, 20), abs=1e-8)
    assert lz.resultado.ok
    assert len(lz.historial) == 1
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_boc9_guia_punteada_y_glifo_en_el_lienzo(lienzo, monkeypatch):
    lz = lienzo
    lz.set_herramienta("linea")
    _clic(lz, 10, 20)
    _mover(lz, 40, 20.5)
    assert lz.inf_actual.tipo == lz.inferencia == "horizontal"
    guias, iconos = [], []
    dibujar, icono = lz._dibujar_polilinea, editor_boceto.icono

    def registrar(p, puntos):
        if p.pen().style() == Qt.DashLine:
            guias.append(list(puntos))
        return dibujar(p, puntos)

    def registrar_icono(nombre):
        iconos.append(nombre)
        return icono(nombre)

    monkeypatch.setattr(lz, "_dibujar_polilinea", registrar)
    monkeypatch.setattr(editor_boceto, "icono", registrar_icono)
    assert not lz.grab().isNull()
    assert [(10, 20), (40, 20)] in guias
    assert "r_horizontal_vertical" in iconos
    lz.cancelar()
    assert lz.inf_actual is None


@pytest.mark.parametrize("mods,nombre", [(Qt.NoModifier, "r_punto_medio"), (Qt.ShiftModifier, "r_coincidente")])
def test_boc9_glifo_del_medio_sigue_a_mayus(lienzo, monkeypatch, mods, nombre):
    lz = lienzo
    _objetivo(lz)
    _mover(lz, 31.7, 20.1, mods)
    nombres = []
    original = editor_boceto.icono

    def registrar(clave):
        nombres.append(clave)
        return original(clave)

    monkeypatch.setattr(editor_boceto, "icono", registrar)
    lz.grab()
    assert nombre in nombres


def test_boc9_largo_escrito_gana_al_ajuste_del_extremo(lienzo):
    lz = lienzo
    _objetivo(lz)
    _clic(lz, 37, 43)
    lz._bloquear("largo", "10", 10)
    _clic(lz, 31.7, 20.1)
    linea = lz.b.curvas[lz._ultima_linea]
    a, b = lz.b._extremos_linea(linea.id)
    assert math.dist(a, b) == pytest.approx(10, abs=1e-8)
    assert not any(r.tipo == "punto_medio" for r in lz.b.restricciones.values())
    assert lz.resultado.ok


def test_boc9_clic_de_largo_cero_conserva_inferencia_del_inicio(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz)
    _clic(lz, 31.7, 20.1)
    _clic(lz, 31.7, 20.1)
    _clic(lz, 37, 43)
    linea = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(linea.p1) == pytest.approx((31.5, 20), abs=1e-8)
    assert any(r.tipo == "punto_medio" and r.entidades == [linea.p1, objetivo]
               for r in lz.b.restricciones.values())


def test_boc9_linea_encadenada_excluye_la_curva_en_dibujo(lienzo):
    lz = lienzo
    lz.set_herramienta("linea")
    _clic(lz, 10, 20)
    _clic(lz, 40, 20)
    _mover(lz, 25, 20.1)
    assert lz.inf_actual.tipo == "horizontal"
    assert lz.inf_actual.objetivo is None
    lz.set_herramienta("seleccionar")
    assert lz.inf_actual is None


def test_boc9_horizontal_rechazada_no_borra_la_linea(lienzo, monkeypatch):
    lz = lienzo
    lz.set_herramienta("linea")
    agregar = lz.b.agregar_restriccion
    intentos = []

    def rechazar(tipo, entidades, datos=None):
        if tipo == "horizontal":
            intentos.append(tipo)
            raise ErrorBoceto("Conflicto simulado horizontal")
        return agregar(tipo, entidades, datos)

    monkeypatch.setattr(lz.b, "agregar_restriccion", rechazar)
    _clic(lz, 10, 20)
    _clic(lz, 40, 20.1)
    assert intentos == ["horizontal"]
    assert len(lz.b.curvas) == len(lz.historial) == 1
    assert lz.b._extremos_linea(lz._ultima_linea) == ((10, 20), (40, 20))
    assert lz.resultado.ok


def test_boc9_enganche_al_punto_existente_comparte_el_extremo(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz)
    punto = lz.b.agregar_punto(31.5, 21)
    _clic(lz, 37, 43)
    _clic(lz, 31.7, 20.1)
    linea = lz.b.curvas[lz._ultima_linea]
    assert linea.p2 == punto
    assert lz.b.coords(linea.p2) == (31.5, 21)
    assert not any(objetivo in r.entidades and r.tipo == "punto_medio" for r in lz.b.restricciones.values())


def _boc26_iniciar(lz):
    lz.set_herramienta("conica")
    for xy in ((20, 20), (40, 20), (35, 40)):
        _clic(lz, *xy)
    assert len(lz.clics) == 3 and lz.entrada is not None


@pytest.mark.parametrize("rho", [0.25, 0.5, 0.75])
def test_boc26_raton_previa_y_clic_comparten_rho(lienzo, monkeypatch, rho):
    from omnicad.restricciones.boceto import evaluar_primitiva, puntos_primitiva

    lz = lienzo
    _boc26_iniciar(lz)
    antes = lz.b.a_dict()
    punto = (30 + 5 * rho, 20 + 20 * rho)
    # Desplazamiento perpendicular: Rho depende de la proyección, no de la distancia al cursor.
    cursor = (punto[0] + 4, punto[1] - 1)
    lz.ajustar_grilla = True
    _mover(lz, *cursor)
    assert float(lz.entrada.campos[0].text()) == pytest.approx(rho, abs=1e-6)
    esperado = Boceto()
    cid = esperado.agregar_conica((20, 20), (35, 40), (40, 20), rho)
    poli = puntos_primitiva(esperado.primitivas(cid)[0])
    dibujadas = []
    original = lz._dibujar_polilinea

    def registrar(p, puntos):
        if p.pen().style() == Qt.SolidLine:
            dibujadas.append(list(puntos))
        return original(p, puntos)

    monkeypatch.setattr(lz, "_dibujar_polilinea", registrar)
    assert not lz.grab().isNull()
    assert any(len(q) == len(poli) and max(math.dist(a, b) for a, b in zip(q, poli, strict=True)) < 1e-6
               for q in dibujadas)
    assert lz.b.a_dict() == antes
    _clic(lz, *cursor)
    curva = next(c for c in lz.b.curvas.values() if c.tipo == "conica")
    assert curva.rho == pytest.approx(rho, abs=1e-6)
    assert evaluar_primitiva(lz.b.primitivas(curva.id)[0], 0.5)[0] == pytest.approx(punto, abs=1e-6)
    assert lz.resultado.ok and not lz.clics and lz.entrada is None
    assert len(lz.historial) == 1
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_boc26_arrastre_confirma_el_rho_al_soltar(lienzo):
    lz = lienzo
    _boc26_iniciar(lz)
    inicio, fin = lz.a_px(32.5, 30), lz.a_px(33.75, 35)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonPress, inicio, inicio,
                                          Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, fin, fin,
                                          Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    assert not lz.b.curvas
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonRelease, fin, fin,
                                          Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    assert next(iter(lz.b.curvas.values())).rho == pytest.approx(0.75, abs=1e-6)


@pytest.mark.parametrize("confirmar", ["clic", "enter"])
def test_boc26_rho_escrito_manda_y_se_previsualiza(lienzo, monkeypatch, confirmar):
    from PySide6.QtTest import QTest

    lz = lienzo
    _boc26_iniciar(lz)
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, "0.3")
    previas = []
    original = lz._temporal

    def registrar(construir):
        b = Boceto()
        construir(b)
        previas.extend(c.rho for c in b.curvas.values() if c.tipo == "conica")
        return original(construir)

    monkeypatch.setattr(lz, "_temporal", registrar)
    lz.grab()
    assert previas[-1] == pytest.approx(0.3)
    _mover(lz, 34, 36)
    lz.grab()
    assert campo.text() == "0.3" and previas[-1] == pytest.approx(0.3)
    if confirmar == "clic":
        _clic(lz, 34, 36)
    else:
        QTest.keyClick(campo, Qt.Key_Return)
    assert next(iter(lz.b.curvas.values())).rho == pytest.approx(0.3)


@pytest.mark.parametrize("fase", ["vertice", "rho", "seleccion", "sin_seleccion"])
def test_boc26_guias_tangentes_punteadas(lienzo, monkeypatch, fase):
    lz = lienzo
    if fase in ("seleccion", "sin_seleccion"):
        cid = lz.b.agregar_conica((20, 20), (35, 40), (40, 20))
        lz.resolver()
        lz.seleccion = [cid] if fase == "seleccion" else []
    else:
        lz.set_herramienta("conica")
        _clic(lz, 20, 20)
        _clic(lz, 40, 20)
        if fase == "rho":
            _clic(lz, 35, 40)
            _mover(lz, 32.5, 30)
        else:
            _mover(lz, 35, 40)
    segmentos = []
    original = lz._dibujar_polilinea

    def registrar(p, puntos):
        if p.pen().style() in (Qt.DotLine, Qt.DashLine):
            segmentos.extend(zip(puntos, puntos[1:], strict=False))
        return original(p, puntos)

    monkeypatch.setattr(lz, "_dibujar_polilinea", registrar)
    assert not lz.grab().isNull()
    tangentes = [((20, 20), (35, 40)), ((35, 40), (40, 20))]
    assert all(t in segmentos for t in tangentes) == (fase != "sin_seleccion")


@pytest.mark.parametrize("punto,rho", [((25, 0), 1e-6), ((40, 60), 1 - 1e-6)])
def test_boc26_raton_limita_rho_sin_crear_curva_degenerada(lienzo, punto, rho):
    lz = lienzo
    _boc26_iniciar(lz)
    _clic(lz, *punto)
    curva = next(iter(lz.b.curvas.values()))
    assert curva.rho == pytest.approx(rho, abs=1e-12)
    assert lz.resultado.ok


@pytest.mark.parametrize("texto", ["0", "1", "nan", "inf", "-"])
def test_boc26_rho_invalido_conserva_puntos_y_permite_corregir(lienzo, texto):
    from PySide6.QtTest import QTest

    lz = lienzo
    _boc26_iniciar(lz)
    antes = lz.b.a_dict()
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    assert not lz.grab().isNull()
    _clic(lz, 32.5, 30)
    assert lz.b.a_dict() == antes and not lz.historial
    assert len(lz.clics) == 3 and lz.entrada is not None
    campo.selectAll()
    QTest.keyClicks(campo, "0.4")
    QTest.keyClick(campo, Qt.Key_Return)
    assert next(iter(lz.b.curvas.values())).rho == pytest.approx(0.4)
    assert len(lz.historial) == 1


def test_boc26_cancelar_rho_no_deja_geometria(lienzo):
    lz = lienzo
    _boc26_iniciar(lz)
    _mover(lz, 33.75, 35)
    lz.cancelar()
    lz.cancelar()
    assert not lz.b.curvas and not lz.b.puntos and not lz.historial
    assert lz.entrada is None and not lz.clics


def test_boc12_arco_tangente_desde_el_extremo_de_un_arco(lienzo):
    lz = lienzo
    previo = lz.b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    lz.set_herramienta("arco_tangente")
    _clic(lz, 0, 10)                       # extremo del arco existente (no de una línea)
    _clic(lz, -10, 20)
    nuevo = max(lz.b.curvas)
    arco = lz.b.curvas[nuevo]
    assert arco.tipo == "arco" and nuevo != previo
    assert lz.b.coords(arco.centro) == pytest.approx((0, 20), abs=1e-6)
    assert lz.b.radio(nuevo) == pytest.approx(10, abs=1e-6)
    assert any(r.tipo == "tangente" and set(r.entidades) == {previo, nuevo} for r in lz.b.restricciones.values())


# ---------------------------------------------------------------- BOC-24: valores escritos en todas las herramientas
def _escribir(lz, texto):
    from PySide6.QtTest import QTest
    QTest.keyClick(lz, texto[0])
    assert lz.entrada is not None, "escribir un número abre la caja activa"
    for ch in texto[1:]:
        QTest.keyClick(lz.entrada.campos[0], ch)


def _tecla(lz, tecla):
    from PySide6.QtTest import QTest
    QTest.keyClick(lz.entrada.campos[0], tecla)


def _lineas(lz, construccion=False):
    return [c for c in lz.b.curvas.values() if c.tipo == "linea" and c.construccion == construccion]


def _largo(lz, c):
    return math.dist(lz.b.coords(c.p1), lz.b.coords(c.p2))


def test_boc24_circulo_de_2_puntos_diametro_escrito(lienzo):
    lz = lienzo
    lz.set_herramienta("circulo_2p")
    _clic(lz, 0, 0)
    _mover(lz, 30, 0)
    _escribir(lz, "20")
    _tecla(lz, Qt.Key_Return)
    (circulo,) = [c for c in lz.b.curvas.values() if c.tipo == "circulo"]
    assert lz.b.radio(circulo.id) == pytest.approx(10, abs=1e-6)
    assert lz.b.coords(circulo.centro) == pytest.approx((10, 0), abs=1e-6)
    assert [k.tipo for k in lz.b.cotas.values()] == ["diametro"]


def test_boc24_linea_de_punto_medio_largo_total_y_angulo(lienzo):
    lz = lienzo
    lz.set_herramienta("linea_medio")
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    _escribir(lz, "50")
    _tecla(lz, Qt.Key_Tab)
    _escribir(lz, "90")
    _tecla(lz, Qt.Key_Return)
    (linea,) = _lineas(lz)
    assert _largo(lz, linea) == pytest.approx(50, abs=1e-6)
    xs = sorted(lz.b.coords(p)[0] for p in (linea.p1, linea.p2))
    assert xs == pytest.approx([0, 0], abs=1e-6)                       # vertical, centrada en el clic
    assert {k.tipo for k in lz.b.cotas.values()} == {"distancia"}
    assert any(r.tipo == "vertical" for r in lz.b.restricciones.values())


def test_boc24_elipse_ejes_escritos(lienzo):
    lz = lienzo
    lz.set_herramienta("elipse")
    _clic(lz, 0, 0)
    _mover(lz, 30, 5)
    _escribir(lz, "20")
    _tecla(lz, Qt.Key_Tab)
    _escribir(lz, "0")
    _tecla(lz, Qt.Key_Return)                       # eje mayor: 20 mm a 0 grados
    _mover(lz, 3, 12)
    _escribir(lz, "8")
    _tecla(lz, Qt.Key_Return)
    (elipse,) = [c for c in lz.b.curvas.values() if c.tipo == "elipse"]
    assert lz.b.coords(elipse.mayor) == pytest.approx((20, 0), abs=1e-6)
    assert elipse.radio_menor == pytest.approx(8, abs=1e-6)
    ejes = sorted(round(_largo(lz, c), 6) for c in _lineas(lz, True))
    assert ejes == [16, 40]
    assert sorted(k.expresion for k in lz.b.cotas.values()) == ["16", "40"]


def test_boc24_arco_tangente_radio_escrito(lienzo):
    lz = lienzo
    previo = lz.b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    lz.set_herramienta("arco_tangente")
    _clic(lz, 0, 10)
    _mover(lz, -10, 20)
    _escribir(lz, "15")
    _tecla(lz, Qt.Key_Return)
    nuevo = max(lz.b.curvas)
    assert nuevo != previo and lz.b.radio(nuevo) == pytest.approx(15, abs=1e-6)
    assert any(r.tipo == "tangente" and set(r.entidades) == {previo, nuevo} for r in lz.b.restricciones.values())
    assert [k.tipo for k in lz.b.cotas.values()] == ["radio"]


def test_boc24_poligono_por_arista_largo_y_lados(lienzo):
    lz = lienzo
    lz.set_herramienta("poligono_arista")
    _clic(lz, 0, 0)
    _mover(lz, 14, 1)
    _escribir(lz, "10")
    _tecla(lz, Qt.Key_Tab)
    _escribir(lz, "0")
    _tecla(lz, Qt.Key_Tab)
    _escribir(lz, "4")
    _tecla(lz, Qt.Key_Return)                       # arista de 10 mm a 0 grados, cuadrado
    _clic(lz, 5, 20)                                # el lado del polígono
    lados = _lineas(lz)
    assert len(lados) == 4
    assert [round(_largo(lz, c), 6) for c in lados] == [10] * 4
    assert any(r.tipo == "horizontal" for r in lz.b.restricciones.values())


def test_boc24_ranura_con_angulo_escrito(lienzo):
    lz = lienzo
    lz.set_herramienta("ranura_centro")
    _clic(lz, 0, 0)
    _mover(lz, 30, 40)
    _escribir(lz, "20")
    _tecla(lz, Qt.Key_Tab)
    _escribir(lz, "90")
    _tecla(lz, Qt.Key_Return)
    _mover(lz, 6, 10)
    _escribir(lz, "8")
    _tecla(lz, Qt.Key_Return)
    eje = [c for c in _lineas(lz, True)][-1]
    (x1, y1), (x2, y2) = lz.b.coords(eje.p1), lz.b.coords(eje.p2)
    assert x1 == pytest.approx(x2, abs=1e-6) and math.dist((x1, y1), (x2, y2)) == pytest.approx(20, abs=1e-6)
    assert any(r.tipo == "vertical" for r in lz.b.restricciones.values())


def test_boc19_cota_ui_con_la_linea_central_es_un_diametro(lienzo):
    lz = lienzo
    eje = lz.b.agregar_linea((0, -10), (0, 30), construccion=False)
    lz.b.curvas[eje].eje = True
    punto = lz.b.agregar_punto(7, 5)
    lz.b.agregar_restriccion("fijo", [eje])
    lz._abrir_cota("distancia", [punto, eje], lz._pos_cursor)
    assert lz.entrada.campos[0].text() == "14"                 # propone el diámetro, el doble de la distancia al eje
    lz.entrada.aceptado.emit(["20"])
    (cota,) = lz.b.cotas.values()
    assert cota.datos.get("diametral") is True
    lz.resolver()
    assert lz.b.coords(punto)[0] == pytest.approx(10, abs=1e-4)
