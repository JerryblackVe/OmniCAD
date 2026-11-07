"""Fase D: restricciones entre clics de ventana, catálogo MCP/API y archivo real."""
import math

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.restricciones import Boceto
from omnicad.restricciones.boceto import TIPOS_COTA, TIPOS_RESTRICCION
from omnicad.restricciones.solver import resolver
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    lz.setAttribute(Qt.WA_ShowWithoutActivating)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    lz.mensajes = []
    lz.mensaje.connect(lz.mensajes.append)
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _clic(lz, xy, mods=Qt.NoModifier):
    pos = lz.a_px(*xy)
    for tipo, boton, botones in ((QEvent.MouseMove, Qt.NoButton, Qt.NoButton),
                                 (QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton),
                                 (QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, boton, botones, mods))


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.mark.parametrize(("tipo", "delta"), [("horizontal", 0), ("vertical", 1)])
def test_s12_api_acota_proyeccion_de_una_linea(tipo, delta):
    s = api.Sesion()
    _llamar(s, "create_sketch", name="B")
    linea = _llamar(s, "draw_line", start_x=20, start_y=20, end_x=50, end_y=60)["entities"][0]["id"]
    _llamar(s, "add_dimension", sketch="B", type=tipo, entities=[linea], value=25)
    b = s.doc.estado_final.bocetos[s.doc.operaciones[0].id].boceto
    p, q = b._extremos_linea(linea)
    assert abs(q[delta] - p[delta]) == pytest.approx(25, abs=1e-6)


@pytest.mark.parametrize(("tipo", "ubicacion"), [("distancia_h", (35, 80)), ("distancia_v", (80, 40))])
@pytest.mark.xfail(strict=True, reason="S12: una línea sola en la ventana siempre crea distancia alineada")
def test_s12_ventana_acota_proyeccion_de_una_linea(lienzo, tipo, ubicacion):
    lz = lienzo
    linea = lz.b.agregar_linea((20, 20), (50, 60))
    lz.resolver()
    lz.set_herramienta("cota")
    _clic(lz, (35, 40))
    assert lz.picks == [linea]
    _clic(lz, ubicacion)
    assert lz.entrada is not None
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, "25")
    QTest.keyClick(campo, Qt.Key_Return)
    cota, = lz.b.cotas.values()
    assert cota.tipo == tipo, cota.a_dict()


@pytest.mark.parametrize("preseleccion", [False, True])
def test_s13_simetria_eje_primero_orienta_sin_cambiar_boceto(lienzo, preseleccion):
    lz = lienzo
    eje = lz.b.agregar_linea((10, 10), (10, 70))
    puntos = [lz.b.agregar_punto(30, 30), lz.b.agregar_punto(50, 30)]
    lz.resolver()
    if preseleccion:
        for xy in ((10, 50), (30, 30), (50, 30)):
            _clic(lz, xy, Qt.ControlModifier)
        assert lz.seleccion == [eje, *puntos]
    lz.set_herramienta("r_simetria")
    antes = lz.b.a_dict()
    if not preseleccion:
        for xy in ((10, 50), (30, 30), (50, 30)):
            _clic(lz, xy)
    assert not lz.b.restricciones
    assert lz.b.a_dict() == antes
    assert "elegí los dos elementos y después el eje" in lz.mensajes[-1], lz.mensajes


@pytest.mark.parametrize("invertir", [False, True])
def test_s8_fijo_desfija_la_misma_seleccion_en_cualquier_orden(lienzo, invertir):
    lz = lienzo
    lineas = [lz.b.agregar_linea((20, y), (60, y)) for y in (20, 60)]
    lz.resolver()
    for xy in ((40, 20), (40, 60)):
        _clic(lz, xy, Qt.ControlModifier)
    assert lz.seleccion == lineas
    lz.set_herramienta("r_fijo")
    assert len(lz.b.restricciones) == 1
    fijo = lz.b.a_dict()
    lz.set_herramienta("seleccionar")
    clics = [(40, 60), (40, 20)] if invertir else [(40, 20), (40, 60)]
    for xy in clics:
        _clic(lz, xy, Qt.ControlModifier)
    assert lz.seleccion == (lineas[::-1] if invertir else lineas)
    lz.set_herramienta("r_fijo")
    assert not lz.b.restricciones
    assert lz.resultado.ok
    lz.deshacer()
    assert lz.b.a_dict() == fijo


def test_s13_simetria_eje_ultimo_sigue_funcionando(lienzo):
    lz = lienzo
    lz.b.agregar_linea((10, 10), (10, 70))
    puntos = [lz.b.agregar_punto(30, 30), lz.b.agregar_punto(50, 30)]
    lz.resolver()
    lz.set_herramienta("r_simetria")
    for xy in ((30, 30), (50, 30), (10, 50)):
        _clic(lz, xy)
    restriccion, = lz.b.restricciones.values()
    assert restriccion.tipo == "simetrica" and restriccion.entidades[:2] == puntos
    assert lz.resultado.ok


def _boceto_completo():
    """Islas independientes: exactamente una restricción y una cota de cada tipo."""
    b = Boceto()
    b.agregar_restriccion("coincidente", [b.agregar_punto(20, 20), b.agregar_punto(20, 20)])
    for tipo, fin in (("horizontal", (30, 20)), ("vertical", (20, 30)), ("fijo", (30, 25))):
        b.agregar_restriccion(tipo, [b.agregar_linea((20, 20), fin)])
    for tipo, inicio, fin in (("paralela", (20, 30), (30, 30)),
                               ("perpendicular", (25, 20), (25, 30)),
                               ("igual", (20, 30), (30, 30)),
                               ("colineal", (25, 20), (35, 20))):
        b.agregar_restriccion(tipo, [b.agregar_linea((20, 20), (30, 20)), b.agregar_linea(inicio, fin)])
    b.agregar_restriccion("tangente", [b.agregar_linea((20, 20), (30, 20)), b.agregar_circulo((25, 23), 3)])
    b.agregar_restriccion("concentrica", [b.agregar_circulo((20, 20), 3), b.agregar_circulo((20, 20), 5)])
    b.agregar_restriccion("punto_medio", [b.agregar_punto(25, 20), b.agregar_linea((20, 20), (30, 20))])
    b.agregar_restriccion("simetrica", [b.agregar_punto(15, 25), b.agregar_punto(25, 25),
                                        b.agregar_linea((20, 20), (20, 30))])
    fin = b.agregar_punto(30, 25)
    b.agregar_restriccion("curvatura", [b.agregar_spline([(20, 20), (25, 22), fin]),
                                       b.agregar_arco_centro((40, 25), fin, (40, 35))])
    vertices = [b.agregar_punto(*xy) for xy in ((20, 20), (30, 20), (25, 20 + 5 * math.sqrt(3)))]
    b.agregar_restriccion("poligono", [b.agregar_linea(vertices[i], vertices[(i + 1) % 3]) for i in range(3)])
    b.agregar_restriccion("desfase", [b.agregar_linea((20, 20), (30, 20)),
                                     b.agregar_punto(25, 20), b.agregar_punto(25, 23)])
    b.agregar_restriccion("patron", [b.agregar_punto(20, 20), b.agregar_punto(23, 24)], {"dx": 3, "dy": 4})
    for tipo, valor in (("distancia", 10), ("distancia_h", 8), ("distancia_v", 6)):
        b.agregar_cota(tipo, [b.agregar_linea((20, 20), (28, 26))], str(valor))
    for tipo, valor in (("radio", 5), ("diametro", 10)):
        b.agregar_cota(tipo, [b.agregar_circulo((20, 20), 5)], str(valor))
    b.agregar_cota("angulo", [b.agregar_linea((20, 20), (30, 20)),
                              b.agregar_linea((20, 20), (25, 20 + 5 * math.sqrt(3)))], "60")
    b.agregar_cota("desfase", [b.agregar_linea((20, 20), (30, 20)), b.agregar_linea((20, 23), (30, 23))], "3")
    assert sorted(r.tipo for r in b.restricciones.values()) == sorted(TIPOS_RESTRICCION)
    assert sorted(c.tipo for c in b.cotas.values()) == sorted(TIPOS_COTA)
    return b


@pytest.mark.parametrize("cache", [False, True])
def test_archivo_real_conserva_todos_los_tipos_y_solver(tmp_path, cache):
    b = _boceto_completo()
    valores = {c.id: float(c.expresion) for c in b.cotas.values()}
    resultado = resolver(b, valores)
    assert resultado.ok
    doc = Documento()
    op = OpBoceto(doc.nuevo_id(), nombre="Todos", boceto=b)
    doc.agregar(op)
    receta = op.boceto.a_dict()
    resuelto = doc.estado_final.bocetos[op.id]
    assert resuelto.solver.ok
    coordenadas = {i: resuelto.boceto.coords(i) for i in resuelto.boceto.puntos}
    ruta = proyecto.guardar(doc, tmp_path / "todos.omnicad", incluir_cache=cache)
    assert ruta.is_file()
    del doc, op, resuelto
    abierto = proyecto.abrir(ruta)
    assert abierto.operaciones[0].boceto.a_dict() == receta
    nuevo = abierto.estado_final.bocetos[abierto.operaciones[0].id]
    assert nuevo.solver.ok and nuevo.solver.gdl == resultado.gdl
    recalculado = resolver(nuevo.boceto, valores)
    assert recalculado.ok and recalculado.gdl == resultado.gdl
    for i, xy in coordenadas.items():
        assert nuevo.boceto.coords(i) == pytest.approx(xy, abs=1e-7)


@pytest.mark.parametrize("caso", ["coincidente_origen", "medio_linea_primero", "tangente_circulo_primero"])
def test_clics_y_mcp_dan_mismas_coordenadas_y_undo_redo(lienzo, caso):
    lz = lienzo
    if caso == "coincidente_origen":
        p = lz.b.agregar_punto(30, 20)
        tipo, herramienta, entidades, clics = "coincident", "r_coincidente", [p, Boceto.ORIGEN], [(30, 20), (0, 0)]
    elif caso == "medio_linea_primero":
        linea = lz.b.agregar_linea((20, 20), (60, 20))
        p = lz.b.agregar_punto(30, 45)
        tipo, herramienta, entidades, clics = "midpoint", "r_punto_medio", [linea, p], [(45, 20), (30, 45)]
    else:
        circulo = lz.b.agregar_circulo((40, 40), 10)
        linea = lz.b.agregar_linea((20, 20), (60, 20))
        tipo, herramienta, entidades, clics = "tangent", "r_tangente", [circulo, linea], [(50, 40), (30, 20)]
    s = api.Sesion()
    op = OpBoceto(s.doc.nuevo_id(), nombre="Paridad", boceto=lz.b.copia())
    s.doc.agregar(op)
    antes = _llamar(s, "get_sketch", sketch="Paridad")
    lz.resolver()
    lz.set_herramienta(herramienta)
    for xy in clics:
        _clic(lz, xy)
    assert lz.resultado.ok and len(lz.b.restricciones) == 1, lz.mensajes
    _llamar(s, "add_constraint", sketch="Paridad", type=tipo, entities=entidades)
    despues = _llamar(s, "get_sketch", sketch="Paridad")
    assert despues != antes
    b = s.doc.estado_final.bocetos[op.id].boceto
    for i in b.puntos:
        assert lz.b.coords(i) == pytest.approx(b.coords(i), abs=1e-7)
    for i in b.curvas:
        if b.tipo_de(i) == "circulo":
            assert lz.b.radio(i) == pytest.approx(b.radio(i), abs=1e-7)
    if caso == "coincidente_origen":
        assert b.coords(p) == pytest.approx((0, 0), abs=1e-7)
    elif caso == "medio_linea_primero":
        a, c = b._extremos_linea(linea)
        assert b.coords(p) == pytest.approx(tuple((x + y) / 2 for x, y in zip(a, c, strict=True)), abs=1e-7)
    else:
        assert b.radio(circulo) == pytest.approx(10, abs=1e-7)
        a, c = b._extremos_linea(linea)
        x, y = b.coords(b.curvas[circulo].centro)
        distancia = abs((c[0] - a[0]) * (a[1] - y) - (a[0] - x) * (c[1] - a[1])) / math.dist(a, c)
        assert distancia == pytest.approx(10, abs=1e-7)
    _llamar(s, "undo")
    assert _llamar(s, "get_sketch", sketch="Paridad") == antes
    _llamar(s, "redo")
    assert _llamar(s, "get_sketch", sketch="Paridad") == despues
