"""Desfase del boceto con signo (2026-10-31): distancia negativa = lado contrario, rechazos con su causa real,
vista previa viva que coincide con lo que se crea, «Invertir», cancelar, deshacer, guardar y extruir."""
import json
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto, ErrorBoceto  # noqa: E402
from omnicad.restricciones.boceto import expresion_sin_signo, mas_cercano, validar_valor_cota  # noqa: E402
from omnicad.restricciones.solver import resolver  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


def _radios(b):
    return sorted(round(c.radio, 6) for c in b.curvas.values() if hasattr(c, "radio") and c.tipo == "circulo")


# ---------------------------------------------------------------- núcleo: la tabla del círculo de 30 mm
@pytest.mark.parametrize("d,radio", [(10, 40), (20, 50), (-10, 20), (-20, 10), (-29, 1)])
def test_circulo_de_30_con_distancia_con_signo(d, radio):
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    b.desfase(c, d)                                      # sin lado: el positivo va afuera
    assert _radios(b) == pytest.approx(sorted([30, radio]))
    cota, = b.cotas.values()
    assert cota.tipo == "desfase" and float(cota.expresion) == pytest.approx(abs(d))   # la cota queda sin signo


def test_circulo_de_30_rechaza_cero_y_negativo_con_la_causa_real():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    with pytest.raises(ErrorBoceto, match="deja el radio del círculo en cero"):
        b.desfase(c, -30)
    with pytest.raises(ErrorBoceto, match="deja el radio del círculo negativo"):
        b.desfase(c, -40)
    with pytest.raises(ErrorBoceto, match="cero: no hay nada"):
        b.desfase(c, 0)
    with pytest.raises(ErrorBoceto, match="no es un número válido"):
        b.desfase(c, float("nan"))
    with pytest.raises(ErrorBoceto, match="no puede pasar de"):
        b.desfase(c, 1e9)
    assert _radios(b) == [30]                            # ningún intento dejó nada


def test_invertir_y_signo_son_la_misma_convencion():
    b1, b2, b3 = Boceto(), Boceto(), Boceto()
    for b in (b1, b2, b3):
        b.agregar_circulo((0, 0), 30)
    b1.desfase(1, -20)
    b2.desfase(1, 20, invertir=True)
    b3.desfase(1, -20, invertir=True)                    # los dos signos se anulan: vuelve afuera
    assert _radios(b1) == _radios(b2) == pytest.approx([10, 30])
    assert _radios(b3) == pytest.approx([30, 50])


def test_con_punto_de_lado_positivo_va_hacia_el_punto():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    b.desfase(c, 5, punto_lado=(0, 0))                   # el cursor adentro: el positivo va adentro
    b.desfase(c, -5, punto_lado=(0, 0))                  # y el negativo, afuera
    assert _radios(b) == pytest.approx([25, 30, 35])


def _distancia_a_circulo(b, ids, centro, r):
    return sorted({round(abs(math.dist(b.coords(p), centro) - r), 6) for k in ids for p in b.curvas[k].extremos()})


def test_cadena_cerrada_adentro_y_afuera_con_signo():
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (40, 20))
    b.desfase(lineas[0], -3)                             # hacia adentro
    xs = sorted({round(p.x, 6) for p in b.puntos.values()})
    ys = sorted({round(p.y, 6) for p in b.puntos.values()})
    assert xs == pytest.approx([0, 3, 37, 40]) and ys == pytest.approx([0, 3, 17, 20])
    b.desfase(lineas[0], 3)                              # hacia afuera
    assert min(p.x for p in b.puntos.values()) == pytest.approx(-3)


def test_cadena_cerrada_se_rechaza_con_su_causa():
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (40, 20))
    with pytest.raises(ErrorBoceto, match="largo cero o al revés"):
        b.desfase(lineas[0], -12)                        # el alto es 20: 12 por lado se pasa
    assert len(b.curvas) == 4


def test_cadena_abierta_con_signo_cambia_de_lado():
    b = Boceto()
    p = [b.agregar_punto(0, 0), b.agregar_punto(10, 0), b.agregar_punto(10, 10)]
    l1, l2 = b.agregar_linea(p[0], p[1]), b.agregar_linea(p[1], p[2])
    izq = b.desfase(l1, 2)                               # abierta: por defecto a la izquierda
    der = b.desfase(l1, -2)
    ys = lambda ids: sorted({round(b.coords(q)[1], 6) for k in ids for q in b.curvas[k].extremos()})  # noqa: E731
    assert ys(izq)[0] == pytest.approx(2) and ys(der)[0] == pytest.approx(-2)
    assert len(izq) == len(der) == 2 and l2 in b.curvas


def test_arco_de_la_cadena_que_se_anula_dice_cual():
    b = Boceto()
    arco = b.agregar_arco_centro(b.agregar_punto(0, 0), b.agregar_punto(10, 0), b.agregar_punto(0, 10))
    with pytest.raises(ErrorBoceto, match="radio de un arco de la cadena"):
        b.desfase(arco, 10, punto_lado=(1, 1))


def test_desfasar_dos_lados_y_simetrico_con_signos():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    nuevos, _ = b.desfasar(c, 5, direccion="simetrico")
    assert _radios(b) == pytest.approx([25, 30, 35]) and len(nuevos) == 2
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    b.desfasar(c, 5, direccion="dos", distancia2=-2)     # las dos con signo sobre la misma normal (Fusion)
    assert _radios(b) == pytest.approx([28, 30, 35])
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    b.desfasar(c, -5, direccion="dos", distancia2=2)
    assert _radios(b) == pytest.approx([25, 30, 32])
    with pytest.raises(ErrorBoceto, match="segunda distancia"):
        b.desfasar(c, 5, direccion="dos")


def test_match_topology_limita_y_avisa():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    nuevos, avisos = b.desfasar(c, -45, topologia=True)
    assert len(nuevos) == 1 and avisos and "se limitó de 45 a" in avisos[0]
    assert 0 < b.curvas[nuevos[0]].radio < 1


def test_la_cota_de_desfase_acepta_negativo_y_rechaza_cero():
    with pytest.raises(ErrorBoceto, match="mayor que cero"):
        validar_valor_cota("desfase", 0)
    validar_valor_cota("desfase", -30)
    validar_valor_cota("desfase", 12)


def _cota_desfase(b):
    return next(c for c in b.cotas.values() if c.tipo == "desfase")


def _editar(b, valor):
    cota = _cota_desfase(b)
    cota.expresion = str(valor)
    r = resolver(b, {cota.id: valor})
    assert r.ok, r.descripcion()
    return cota


def test_cota_de_desfase_a_negativo_lleva_la_linea_del_otro_lado_y_vuelve():
    # Fusion real: línea en y = 0, copia en y = 10, cota −5: la copia queda en y = −5.
    b = Boceto()
    linea = b.agregar_linea(b.agregar_punto(0, 0), b.agregar_punto(30, 0))
    copia = b.curvas[b.desfase(linea, 10, punto_lado=(5, 5))[0]]
    assert b.coords(copia.p1)[1] == pytest.approx(10)
    cota = _editar(b, -5)
    assert b.coords(copia.p1)[1] == pytest.approx(-5) and b.coords(copia.p2)[1] == pytest.approx(-5)
    assert b.medir(cota) == pytest.approx(-5)
    _editar(b, -7)                                       # repetir no lo devuelve: sigue del mismo lado
    _editar(b, -7)
    assert b.coords(copia.p1)[1] == pytest.approx(-7)
    _editar(b, 10)
    assert b.coords(copia.p1)[1] == pytest.approx(10) and b.medir(cota) == pytest.approx(10)


def test_cota_negativa_sobrevive_a_guardar_y_abrir():
    b = Boceto()
    linea = b.agregar_linea(b.agregar_punto(0, 0), b.agregar_punto(30, 0))
    copia = b.desfase(linea, 10, punto_lado=(5, 5))[0]
    _editar(b, -5)
    otra = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))
    _editar(otra, -5)
    assert otra.coords(otra.curvas[copia].p1)[1] == pytest.approx(-5)
    _editar(otra, 4)
    assert otra.coords(otra.curvas[copia].p1)[1] == pytest.approx(4)


def test_cota_negativa_en_circulo_achica_y_si_no_entra_no_resuelve():
    b = Boceto()
    circulo = b.agregar_circulo(b.agregar_punto(0, 0), 10)
    copia = b.desfase(circulo, 5)[0]
    assert b.radio(copia) == pytest.approx(15)
    _editar(b, -4)
    assert b.radio(copia) == pytest.approx(6)
    assert not resolver(b, {_cota_desfase(b).id: -12}).ok   # quedaría con radio −2: no hay círculo que lo cumpla


def test_cota_negativa_pasa_una_cadena_cerrada_entera_al_otro_lado():
    b = Boceto()
    a, c, d, e = (b.agregar_punto(*p) for p in ((0, 0), (40, 0), (40, 30), (0, 30)))
    lados = [b.agregar_linea(p, q) for p, q in ((a, c), (c, d), (d, e), (e, a))]
    copias = b.desfase(lados[0], 5)                      # una cadena cerrada va hacia afuera
    assert b.separacion(lados[0], copias[0]) == pytest.approx(5)
    afuera = [b.coords(p) for k in copias for p in (b.curvas[k].p1, b.curvas[k].p2)]
    assert min(x for x, _ in afuera) == pytest.approx(-5) and max(y for _, y in afuera) == pytest.approx(35)
    _editar(b, -3)
    adentro = [b.coords(p) for k in copias for p in (b.curvas[k].p1, b.curvas[k].p2)]
    assert min(x for x, _ in adentro) == pytest.approx(3) and max(x for x, _ in adentro) == pytest.approx(37)
    assert min(y for _, y in adentro) == pytest.approx(3) and max(y for _, y in adentro) == pytest.approx(27)


def test_cota_negativa_en_una_spline_la_pasa_del_otro_lado():
    b = Boceto()
    madre = b.agregar_spline([b.agregar_punto(*p) for p in ((0, 0), (10, 4), (20, 0), (30, 4))], "ajuste", 3, False)
    copia = b.desfase(madre, 2, punto_lado=(10, 8))[0]
    assert b.medir(_cota_desfase(b)) == pytest.approx(2, abs=1e-4)
    cota = _editar(b, -1.5)
    assert mas_cercano(b.primitivas(madre)[0], b.coords(b.curvas[copia].pts[0]))[1] == pytest.approx(1.5, abs=1e-4)
    assert b.medir(cota) == pytest.approx(-1.5, abs=1e-4)


def test_expresion_sin_signo():
    ev = {"20": 20, "a": 5, "a+b": 7}.get
    assert expresion_sin_signo("5", 5, ev) == "5"
    assert expresion_sin_signo("-20", -20, ev) == "20"
    assert expresion_sin_signo("-a", -5, ev) == "a"
    assert expresion_sin_signo("-a+b", -3, ev) == "-(-a+b)"      # lstrip("-") la habría vuelto «a+b» = 7


# ---------------------------------------------------------------- BOC-50 por la API y la ventana
def test_api_cota_de_desfase_negativa_y_por_parametro():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="B")
    linea = _llamar(s, "draw_line", start_x=0, start_y=0, end_x=30, end_y=0)["entities"][0]["id"]
    copia = _llamar(s, "offset_sketch_curves", entity=linea, distance=10, side_x=5, side_y=5)
    cota = copia["dimensions"][0]["id"]
    resuelto = lambda: s.doc.estado_final.bocetos["op1"].boceto  # noqa: E731
    y_copia = lambda: resuelto().coords(resuelto().curvas[copia["entities"][0]["id"]].p1)[1]  # noqa: E731
    assert y_copia() == pytest.approx(10)
    _llamar(s, "edit_dimension", dimension=cota, value=-5)
    assert y_copia() == pytest.approx(-5)
    assert resuelto().coords(resuelto().curvas[linea].p1)[1] == pytest.approx(0, abs=1e-6)      # la original no se mueve
    _llamar(s, "edit_dimension", dimension=cota, value=8)
    assert y_copia() == pytest.approx(8)
    _llamar(s, "create_parameter", name="d", expression="-3 mm")
    _llamar(s, "edit_dimension", dimension=cota, value="d")
    assert y_copia() == pytest.approx(-3)
    _llamar(s, "set_parameter", name="d", expression="6 mm")
    assert y_copia() == pytest.approx(6)
    assert _falla(s, "edit_dimension", dimension=cota, value=0)["error_kind"] == "INVALID_DIMENSION"


def test_ventana_teclear_una_cota_negativa_pasa_la_copia_y_muestra_el_signo(lienzo):
    linea = lienzo.b.agregar_linea((0, 0), (30, 0))
    copia = lienzo.b.curvas[lienzo.b.desfase(linea, 10, punto_lado=(5, 5))[0]]
    lienzo.resolver()
    cota = next(k for k in lienzo.b.cotas.values() if k.tipo == "desfase")
    lienzo.editar_cota(cota.id, QPointF(100, 100))
    _teclear(lienzo, "-5 mm")
    QTest.keyClick(lienzo.entrada.campos[0], Qt.Key_Return)
    assert lienzo.entrada is None and cota.expresion == "-5 mm"
    assert lienzo.b.coords(copia.p1)[1] == pytest.approx(-5)
    assert lienzo.b.coords(lienzo.b.curvas[linea].p1)[1] == pytest.approx(0, abs=1e-6)
    assert "-5" in lienzo._texto_cota(cota, lienzo.b.medir(cota))
    lienzo.deshacer()
    assert lienzo.b.coords(copia.p1)[1] == pytest.approx(10)


def test_ventana_una_cota_negativa_sin_solucion_se_deshace_y_avisa(lienzo):
    circulo = lienzo.b.agregar_circulo((0, 0), 10)
    copia = lienzo.b.desfase(circulo, 5)[0]
    lienzo.resolver()
    cota = next(k for k in lienzo.b.cotas.values() if k.tipo == "desfase")
    lienzo.editar_cota(cota.id, QPointF(100, 100))
    _teclear(lienzo, "-12")
    QTest.keyClick(lienzo.entrada.campos[0], Qt.Key_Return)
    assert lienzo.b.radio(copia) == pytest.approx(15) and lienzo.b.cotas[cota.id].expresion == "5"


# ---------------------------------------------------------------- API (MCP y CLI): el mismo resultado y los mismos rechazos
@pytest.fixture
def s():
    sesion = api.Sesion()
    api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})
    return sesion


def _llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _falla(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert not r["ok"], r
    return r


def _circulos(s):
    r = _llamar(s, "get_sketch", sketch="B")
    return sorted(round(e["radius"], 6) for e in r["entities"] if e["type"] == "circle")


@pytest.mark.parametrize("d,radio", [(10, 40), (20, 50), (-10, 20), (-20, 10), (-29, 1)])
def test_api_desfase_de_circulo_de_30(s, d, radio):
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    _llamar(s, "offset_sketch_curves", entity=c, distance=d)
    assert _circulos(s) == pytest.approx(sorted([30, radio]))


def test_api_rechaza_con_la_causa_y_no_deja_rastro(s):
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = _falla(s, "offset_sketch_curves", entity=c, distance=-30)
    assert r["error_kind"] == "INVALID_GEOMETRY" and "en cero" in r["mensaje"] and "30" in r["mensaje"]
    r = _falla(s, "offset_sketch_curves", entity=c, distance=-40)
    assert "negativo" in r["mensaje"]
    assert _falla(s, "offset_sketch_curves", entity=c, distance=0)["error_kind"] == "INVALID_DIMENSION"
    assert _falla(s, "offset_sketch_curves", entity=c, distance="abc")["ok"] is False
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes


def test_api_expresion_con_signo_deja_la_cota_positiva(s):
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    _llamar(s, "add_dimension", sketch="B", type="radius", entities=[c], value=30)     # el original no se mueve
    _llamar(s, "create_parameter", name="pared", expression="4 mm")
    r = _llamar(s, "offset_sketch_curves", entity=c, distance="-pared")
    assert r["dimensions"][0]["expression"] == "pared"
    assert _circulos(s) == pytest.approx([26, 30])
    _llamar(s, "set_parameter", name="pared", expression="6 mm")
    assert _circulos(s) == pytest.approx([24, 30])


def test_api_desfase_interior_se_puede_extruir_como_perfil_cerrado(s):
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    _llamar(s, "offset_sketch_curves", entity=c, distance=-10)
    perfiles = _llamar(s, "get_sketch", sketch="B")["profiles"]
    assert sorted(round(p["area"], 3) for p in perfiles) == pytest.approx(sorted([400 * math.pi, 500 * math.pi]), abs=1e-2)
    anillo = [i for i, p in enumerate(perfiles) if abs(p["area"] - 500 * math.pi) < 1e-2]
    _llamar(s, "extrude", sketch="B", profile=anillo, distance="5 mm")
    assert _llamar(s, "get_physical_properties")["total"]["volume"] == pytest.approx(2500 * math.pi, abs=1e-2)


def test_api_deshacer_rehacer_y_guardar_reabrir(s, tmp_path):
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    _llamar(s, "offset_sketch_curves", entity=c, distance=-20)
    assert _circulos(s) == pytest.approx([10, 30])
    _llamar(s, "undo")
    assert _circulos(s) == [30]
    _llamar(s, "redo")
    assert _circulos(s) == pytest.approx([10, 30])
    ruta = str(tmp_path / "desfase.omnicad")
    _llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    _llamar(otra, "open_document", path=ruta)
    assert _circulos(otra) == pytest.approx([10, 30])
    cota = [k for k in _llamar(otra, "get_sketch", sketch="B")["dimensions"] if k["type"] == "offset"]
    assert cota and float(cota[0]["value"]) == pytest.approx(20)


# ---------------------------------------------------------------- ventana: vista previa viva y lo que pasa al teclear
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


def _abrir(lz, radio=30, cursor=(60, 0)):
    c = lz.b.agregar_circulo((0, 0), radio)
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.cursor = cursor
    lz.agregar_pick(c, (radio, 0))
    return c


def _teclear(lz, texto):
    campo = lz.entrada.campos[0]
    campo.selectAll()
    QTest.keyClicks(campo, texto)


def _previa(lz):
    polis, nota, error = lz._previa_desfase()
    return sorted({round(max(abs(q[0]) for q in poli), 1) for poli in polis}), nota, error


def test_la_previa_cambia_de_lado_al_teclear_sin_confirmar(lienzo):
    lz = lienzo
    _abrir(lz)
    _teclear(lz, "20")
    assert _previa(lz) == ([50.0], "Hacia afuera", False)
    _teclear(lz, "-20")
    radios, nota, error = _previa(lz)
    assert radios == [10.0] and nota == "Hacia adentro" and not error
    assert _radios(lz.b) == [30]                         # la geometría real sigue intacta


def test_la_previa_dibuja_exactamente_lo_que_se_crea(lienzo):
    lz = lienzo
    c = _abrir(lz)
    dibujado = []
    original = lz._dibujar_polilinea
    lz._dibujar_polilinea = lambda p, pts, *a, **k: (dibujado.append(list(pts)), original(p, pts, *a, **k))[1]
    _teclear(lz, "-20")
    dibujado.clear()
    lz.grab()
    previas = [pts for pts in dibujado if len(pts) > 8 and max(abs(q[0]) for q in pts) < 29.5]
    assert previas and max(abs(q[0]) for q in previas[0]) == pytest.approx(10, abs=0.2)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert _radios(lz.b) == pytest.approx([10, 30]) and c in lz.b.curvas


@pytest.mark.parametrize("texto,fragmento", [("-30", "en cero"), ("-40", "negativo"), ("0", "cero: no hay nada"),
                                              ("", "Escribí la distancia"), ("abc", "Nombre desconocido"),
                                              ("1e9", "no puede pasar de")])
def test_valor_invalido_no_deja_previa_vieja_y_explica(lienzo, texto, fragmento):
    lz = lienzo
    _abrir(lz)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    _teclear(lz, "20")
    assert _previa(lz)[0] == [50.0]
    _teclear(lz, texto) if texto else lz.entrada.campos[0].clear()
    radios, nota, error = _previa(lz)
    assert radios == [] and error and fragmento in nota
    assert fragmento in mensajes[-1]                     # también en la barra de estado
    assert "background" in lz.entrada.campos[0].styleSheet()          # el campo en rojo
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)  # Enter no confirma ni crea nada y repite la causa
    assert lz.entrada is not None and _radios(lz.b) == [30] and fragmento in mensajes[-1]
    _teclear(lz, "-20")                                  # y al corregir, el rojo se va y la previa vuelve
    assert _previa(lz)[0] == [10.0] and lz.entrada.campos[0].styleSheet() == ""


def test_cambios_rapidos_nunca_dejan_una_previa_ajena(lienzo):
    lz = lienzo
    _abrir(lz)
    esperado = {"20": 50.0, "-20": 10.0, "-30": None, "5": 35.0, "-29": 1.0, "x": None, "-1": 29.0, "": None}
    for _ in range(3):
        for texto, radio in esperado.items():
            _teclear(lz, texto) if texto else lz.entrada.campos[0].clear()
            assert _previa(lz)[0] == ([] if radio is None else [radio]), texto
    assert _radios(lz.b) == [30]


def test_boton_invertir_pasa_al_otro_lado_sin_cambiar_la_distancia(lienzo):
    lz = lienzo
    _abrir(lz)
    _teclear(lz, "20")
    boton = lz.entrada.findChildren(editor_boceto.QToolButton)[0]
    assert boton.toolTip().startswith("Invertir")
    boton.click()
    assert _previa(lz)[0] == [10.0] and lz.entrada.campos[0].text() == "20"
    boton.click()
    assert _previa(lz)[0] == [50.0]
    boton.click()
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert _radios(lz.b) == pytest.approx([10, 30])
    cota, = [k for k in lz.b.cotas.values() if k.tipo == "desfase"]
    assert cota.expresion == "20"                        # la cota queda positiva


def test_escape_descarta_todo_y_no_crea_nada(lienzo):
    lz = lienzo
    _abrir(lz)
    _teclear(lz, "-20")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    assert lz.entrada is None and _radios(lz.b) == [30] and not lz.b.cotas


def test_deshacer_y_rehacer_desde_la_ventana(lienzo):
    lz = lienzo
    _abrir(lz)
    _teclear(lz, "-20")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert _radios(lz.b) == pytest.approx([10, 30]) and len(lz.historial) == 1
    lz.deshacer()
    assert _radios(lz.b) == [30]
    lz.rehacer()
    assert _radios(lz.b) == pytest.approx([10, 30])
    assert lz.resultado.ok


def test_dos_lados_y_simetrico_se_previsualizan_enteros(lienzo):
    lz = lienzo
    lz.opciones["direccion_desfase"] = "simetrico"
    _abrir(lz)
    _teclear(lz, "5")
    assert _previa(lz) == ([25.0, 35.0], "Simétrico", False)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert _radios(lz.b) == pytest.approx([25, 30, 35])


def test_cadena_cerrada_con_signo_en_la_ventana(lienzo):
    lz = lienzo
    lineas = lz.b.agregar_rectangulo((0, 0), (40, 20))
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.cursor = (20, -10)
    lz.agregar_pick(lineas[0], (20, 0))
    _teclear(lz, "-3")
    polis, nota, error = lz._previa_desfase()
    assert not error and nota == "Hacia adentro"
    assert sorted({round(q[0], 3) for poli in polis for q in poli}) == pytest.approx([3, 37])
    _teclear(lz, "-12")
    assert lz._previa_desfase()[2] and "largo cero o al revés" in lz._previa_desfase()[1]


def test_la_previa_es_fluida_con_una_cadena_larga(lienzo):
    import time
    lz = lienzo
    n = 300
    pts = [lz.b.agregar_punto(100 * math.cos(2 * math.pi * i / n), 100 * math.sin(2 * math.pi * i / n))
           for i in range(n)]
    ids = [lz.b.agregar_linea(pts[i], pts[(i + 1) % n]) for i in range(n)]
    lz.set_herramienta("desfase")
    lz.cursor = (0, 0)
    lz.agregar_pick(ids[0], (100, 0))
    t0 = time.perf_counter()
    for texto in ("2", "-2", "3", "-3", "4", "-4", "x", "5"):
        _teclear(lz, texto)
    medio = (time.perf_counter() - t0) / 8
    assert medio < 1.0, f"{medio:.3f} s por cambio de valor"


def test_dos_lados_con_el_segundo_invalido_no_deja_el_primero(lienzo, s):
    lz = lienzo
    lz.opciones["direccion_desfase"] = "dos"
    _abrir(lz)
    lz.entrada.campos[0].setText("5")
    lz.entrada.campos[1].setText("-40")                  # el 2.º va hacia adentro: 40 > radio 30
    assert "negativo" in lz._previa_desfase()[1]
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert lz.entrada is not None and _radios(lz.b) == [30]
    c = _llamar(s, "draw_circle", radius=30)["entities"][0]["id"]
    r = _falla(s, "offset_sketch_curves", entity=c, distance=5, direction="two", distance2=-40)
    assert r["error_kind"] == "INVALID_GEOMETRY" and _circulos(s) == [30]
