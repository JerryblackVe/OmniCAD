"""Desfase del boceto contra Fusion (auditoría 2026-10-31): la tabla numérica del círculo de 67,125 mm, Dos lados con
signo sobre la misma normal, Simétrico ligado, Selección de cadena, líneas, arcos, cadenas, elipses y splines, y el
recorrido de la ventana con eventos de ratón y teclado (asa, cambio de dirección con la barra abierta, errores por
campo, Enter/Esc/✓/✕, bordes y ventanas chicas). Evidencia de Fusion: el video 2026-10-31 06-46-25 y
docs/fusion_docs/.../offset-sketch-geometry (ver docs/auditorias/desfase_boceto_2026-10-31.md)."""
import json
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QFont, QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto, ErrorBoceto, puntos_primitiva  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402

R = 67.125                       # el círculo del video


def _radios(b):
    return sorted(round(c.radio, 6) for c in b.curvas.values() if c.tipo == "circulo")


# ---------------------------------------------------------------- núcleo: la tabla de aceptación
@pytest.mark.parametrize("kwargs,esperado", [
    (dict(distancia=20), [R, R + 20]),
    (dict(distancia=-20), [R - 20, R]),
    (dict(distancia=80), [R, R + 80]),
    (dict(distancia=20, direccion="dos", distancia2=-10), [R - 10, R, R + 20]),        # exterior 20 e interior 10
    (dict(distancia=-10, direccion="dos", distancia2=20), [R - 10, R, R + 20]),        # el orden de los campos no importa
    (dict(distancia=10, direccion="simetrico"), [R - 10, R, R + 10]),
    (dict(distancia=20, direccion="dos", distancia2=0), [R, R + 20]),                   # 0 = sin esa copia (Fusion)
])
def test_tabla_del_circulo_del_video(kwargs, esperado):
    b = Boceto()
    c = b.agregar_circulo((0, 0), R)
    b.desfasar(c, **kwargs)
    assert _radios(b) == pytest.approx(esperado, abs=1e-9)


def test_interior_de_80_se_rechaza_sin_tocar_el_boceto():
    b = Boceto()
    c = b.agregar_circulo((0, 0), R)
    antes = json.dumps(b.a_dict(), sort_keys=True)
    with pytest.raises(ErrorBoceto, match="deja el radio del círculo negativo"):
        b.desfasar(c, -80)
    assert json.dumps(b.a_dict(), sort_keys=True) == antes


def test_dos_lados_en_cero_las_dos_se_rechaza():
    b = Boceto()
    c = b.agregar_circulo((0, 0), R)
    with pytest.raises(ErrorBoceto, match="cero: no hay nada"):
        b.desfasar(c, 0, direccion="dos", distancia2=0)


def test_simetrico_con_match_topology_no_liga_el_lado_que_se_limito():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 30)
    _nuevos, avisos = b.desfasar(c, 45, expresion="45", direccion="simetrico", topologia=True)
    assert avisos and sorted(round(r) for r in _radios(b)) == [0, 30, 75]        # adentro se limitó, afuera no
    assert not any("igual_a" in k.datos for k in b.cotas.values())             # ligarlas arrastraría 45 al lado limitado


def test_una_cota_de_dos_lados_no_arrastra_a_la_otra():
    b = Boceto()
    c = b.agregar_circulo((0, 0), R)
    b.desfasar(c, 20, direccion="dos", distancia2=-10)
    cotas = [k for k in b.cotas.values() if k.tipo == "desfase"]
    assert [k.expresion for k in cotas] == ["20", "10"] and not any("igual_a" in k.datos for k in cotas)


# ---------------------------------------------------------------- núcleo: líneas, arcos y cadenas
def _extremos(b, ids):
    return [tuple(round(v, 6) for v in b.coords(p)) for k in ids for p in b.curvas[k].extremos()]


def test_linea_suelta_paralela_a_su_distancia():
    b = Boceto()
    l = b.agregar_linea(b.agregar_punto(0, 0), b.agregar_punto(30, 40))       # 3-4-5: largo 50
    nuevo, = b.desfase(l, 10)
    (x1, y1), (x2, y2) = _extremos(b, [nuevo])
    assert math.dist((x1, y1), (x2, y2)) == pytest.approx(50)
    assert abs((x2 - x1) * 4 - (y2 - y1) * 3) < 1e-6                           # paralela
    assert abs((x1 * 40 - y1 * 30) / 50) == pytest.approx(10)                  # a 10 mm de la recta madre
    otro, = b.desfase(l, -10)
    assert (_extremos(b, [otro])[0][0] * 40 - _extremos(b, [otro])[0][1] * 30) / 50 == pytest.approx(
        -(x1 * 40 - y1 * 30) / 50)                                             # el negativo, al otro lado


def test_arco_concentrico_y_radio_resultante():
    b = Boceto()
    centro = b.agregar_punto(0, 0)
    arco = b.agregar_arco_centro(centro, b.agregar_punto(30, 0), b.agregar_punto(0, 30))
    fuera, = b.desfase(arco, 5, punto_lado=(40, 40))
    dentro, = b.desfase(arco, 5, punto_lado=(1, 1))
    assert b.radio(fuera) == pytest.approx(35) and b.radio(dentro) == pytest.approx(25)
    assert b.curvas[fuera].centro == b.curvas[dentro].centro == centro          # concéntricos: comparten el centro
    with pytest.raises(ErrorBoceto, match="radio de un arco de la cadena"):
        b.desfase(arco, 30, punto_lado=(1, 1))                                  # el radio llegaría a 0


def _cadena_linea_arco_linea(b):
    p = [b.agregar_punto(0, 0), b.agregar_punto(40, 0), b.agregar_punto(60, 20)]
    l1 = b.agregar_linea(p[0], p[1])
    b.agregar_arco_centro(b.agregar_punto(40, 20), p[1], p[2])
    b.agregar_linea(p[2], b.agregar_punto(60, 50))
    return l1


@pytest.mark.parametrize("d,x_final", [(3, 57.0), (-3, 63.0)])
def test_cadena_abierta_linea_arco_linea_sigue_continua(d, x_final):
    b = Boceto()
    nuevos = b.desfase(_cadena_linea_arco_linea(b), d)
    assert [type(b.curvas[k]).__name__ for k in nuevos] == ["Linea", "Arco", "Linea"]
    pts = [b.coords(p) for k in nuevos for p in b.curvas[k].extremos()]
    assert pts[1] == pytest.approx(pts[2]) and pts[3] == pytest.approx(pts[4])  # se encadenan: sin saltos
    assert pts[5][0] == pytest.approx(x_final) and abs(pts[0][1]) == pytest.approx(3)


def test_cadena_cerrada_convexa_y_concava():
    b = Boceto()
    l = b.agregar_rectangulo((0, 0), (100, 60))
    b.desfase(l[0], 5)                                    # afuera: las esquinas se resuelven por intersección
    b.desfase(l[0], -5)                                   # adentro
    xs = sorted({round(p.x, 6) for p in b.puntos.values()})
    assert xs == pytest.approx([-5, 0, 5, 95, 100, 105])
    cc = Boceto()                                         # una «L» (esquina cóncava)
    p = [cc.agregar_punto(*q) for q in ((0, 0), (60, 0), (60, 20), (20, 20), (20, 60), (0, 60))]
    ls = [cc.agregar_linea(p[i], p[(i + 1) % 6]) for i in range(6)]
    cc.desfase(ls[0], 4)
    dentro = sorted({round(q.x, 6) for q in cc.puntos.values() if q.x > 0 and q.y > 0 and q.x < 60 and q.y < 60})
    assert 24 in dentro or 24.0 in dentro                 # la esquina cóncava se corre a (24, 24)


def test_seleccion_de_cadena_apagada_desfasa_solo_la_curva():
    b = Boceto()
    l = b.agregar_rectangulo((0, 0), (100, 60))
    todos = b.desfase(l[0], 5)
    assert len(todos) == 4
    c = Boceto()
    l = c.agregar_rectangulo((0, 0), (100, 60))
    solo, avisos = c.desfasar(l[0], 5, cadena=False)
    assert len(solo) == 1 and not avisos and len(c.curvas) == 5
    (x1, y1), (x2, y2) = _extremos(c, solo)
    assert (x1, x2) == pytest.approx((0, 100)) and abs(y1) == pytest.approx(5) == abs(y2)   # sin tocar las esquinas


# ---------------------------------------------------------------- núcleo: elipses y splines
def _distancia_a(b, k_nuevo, k_madre):
    madre = [q for prim in b.primitivas(k_madre) for q in puntos_primitiva(prim, 720)]
    nueva = [q for prim in b.primitivas(k_nuevo) for q in puntos_primitiva(prim, 96)]
    return [min(math.dist(q, m) for m in madre) for q in nueva]


@pytest.mark.parametrize("d", [4, -4])
def test_elipse_da_una_curva_a_distancia_constante(d):
    b = Boceto()
    e = b.agregar_elipse((0, 0), (50, 0), 30)
    nuevo, = b.desfase(e, d)
    dist = _distancia_a(b, nuevo, e)
    # Tolerancia: la curva libre pasa por 48 puntos exactos y entre ellos interpola; ±1,5 % de la distancia pedida.
    assert max(abs(x - abs(d)) for x in dist) < 0.015 * abs(d) + 0.02


def test_spline_cerrada_y_abierta_a_distancia_constante():
    b = Boceto()
    s = b.agregar_spline([(0, 0), (20, 15), (40, -5), (60, 10)])
    nuevo, = b.desfase(s, 3)
    assert max(abs(x - 3) for x in _distancia_a(b, nuevo, s)) < 0.15
    with pytest.raises(ErrorBoceto, match="se pliega sobre sí mismo"):
        b.desfase(s, 40)


def test_curva_de_construccion_conserva_su_tipo_en_todas_las_copias():
    b = Boceto()
    c = b.agregar_circulo((0, 0), R, True)
    nuevos, _ = b.desfasar(c, 10, direccion="simetrico")
    assert all(b.curvas[k].construccion for k in nuevos)


# ---------------------------------------------------------------- API: el mismo resultado y las ediciones posteriores
@pytest.fixture
def s():
    sesion = api.Sesion()
    api.llamar(sesion, "create_sketch", {"plane": "XY", "name": "B"})
    return sesion


def _llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _circulos(sesion):
    r = _llamar(sesion, "get_sketch", sketch="B")
    return sorted(round(e["radius"], 6) for e in r["entities"] if e["type"] == "circle")


@pytest.mark.parametrize("kwargs,esperado", [
    (dict(distance=20), [R, R + 20]), (dict(distance=-20), [R - 20, R]),
    (dict(distance=20, direction="two", distance2=-10), [R - 10, R, R + 20]),
    (dict(distance=10, direction="symmetric"), [R - 10, R, R + 10]),
])
def test_api_tabla_del_circulo_del_video(s, kwargs, esperado):
    c = _llamar(s, "draw_circle", radius=R)["entities"][0]["id"]
    _llamar(s, "offset_sketch_curves", entity=c, **kwargs)
    assert _circulos(s) == pytest.approx(esperado)


def test_api_chain_false_en_un_rectangulo(s):
    r = _llamar(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=60)
    linea = next(e["id"] for e in r["entities"] if e["type"] == "line")
    _llamar(s, "offset_sketch_curves", entity=linea, distance=5, chain=False)
    assert sum(1 for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "line") == 5


def test_simetrico_queda_ligado_y_editar_una_cota_mueve_las_dos(s):
    c = _llamar(s, "draw_circle", radius=R)["entities"][0]["id"]
    _llamar(s, "add_dimension", sketch="B", type="radius", entities=[c], value=R)
    _llamar(s, "offset_sketch_curves", entity=c, distance=10, direction="symmetric")
    cotas = _llamar(s, "get_sketch", sketch="B")["dimensions"][1:]
    assert [k["expression"] for k in cotas] == ["10.0", cotas[0]["name"]]       # la 2.ª sigue a la 1.ª
    _llamar(s, "edit_dimension", dimension=cotas[0]["id"], value=25)
    assert _circulos(s) == pytest.approx([R - 25, R, R + 25])
    _llamar(s, "edit_dimension", dimension=cotas[1]["id"], value=5)               # editar la otra la suelta de la 1.ª
    assert _circulos(s) == pytest.approx([R - 5, R, R + 25])


def test_editar_el_original_y_la_distancia_mueve_el_desfase_y_deshacer_rehacer_en_cadena(s, tmp_path):
    c = _llamar(s, "draw_circle", radius=R)["entities"][0]["id"]
    _llamar(s, "add_dimension", sketch="B", type="radius", entities=[c], value=R)
    _llamar(s, "offset_sketch_curves", entity=c, distance=20, direction="two", distance2=-10)
    cotas = _llamar(s, "get_sketch", sketch="B")["dimensions"]
    radio, d1, d2 = (k["id"] for k in cotas)
    _llamar(s, "edit_dimension", dimension=radio, value=50)                       # cambia el original
    assert _circulos(s) == pytest.approx([40, 50, 70])
    _llamar(s, "edit_dimension", dimension=d1, value=30)                          # y la distancia exterior
    assert _circulos(s) == pytest.approx([40, 50, 80])
    ruta = str(tmp_path / "d.omnicad")
    _llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    _llamar(otra, "open_document", path=ruta)
    assert _circulos(otra) == pytest.approx([40, 50, 80])                         # guardar y reabrir
    for _ in range(3):
        _llamar(s, "undo")
    assert _circulos(s) == pytest.approx([R - 10, R, R + 20]) or _circulos(s) == pytest.approx([R])
    for _ in range(3):
        _llamar(s, "redo")
    assert _circulos(s) == pytest.approx([40, 50, 80])
    assert d2 != d1


def test_borrar_la_cota_libera_la_distancia_y_soltar_conserva_las_curvas(s):
    r = _llamar(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=60)
    linea = next(e["id"] for e in r["entities"] if e["type"] == "line")
    _llamar(s, "offset_sketch_curves", entity=linea, distance=5)
    cota = _llamar(s, "get_sketch", sketch="B")["dimensions"][0]["id"]
    _llamar(s, "delete_sketch_entities", sketch="B", entities=[cota])             # distancia libre, relación en pie
    sk = _llamar(s, "get_sketch", sketch="B")
    assert sk["dimensions"] == [] and sum(1 for e in sk["entities"] if e["type"] == "line") == 8
    _llamar(s, "release_offset", entity=linea)                                    # y ahora sí se suelta la asociación
    assert sum(1 for e in _llamar(s, "get_sketch", sketch="B")["entities"] if e["type"] == "line") == 8


def test_circulo_sin_cota_sigue_concentrico():
    b = Boceto()
    c = b.agregar_circulo((0, 0), R)
    nuevo, = b.desfase(c, 20)
    b.eliminar(next(iter(b.cotas)))
    assert not b.cotas and b.curvas[nuevo].centro == b.curvas[c].centro           # la relación (centro común) queda


# ---------------------------------------------------------------- ventana: el recorrido de la persona
def _evento(lz, tipo, pos, boton=Qt.NoButton, botones=Qt.NoButton):
    QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, boton, botones, Qt.NoModifier))


def _mover(lz, pos, botones=Qt.NoButton):
    _evento(lz, QEvent.MouseMove, pos, Qt.NoButton, botones)


def _clic(lz, pos):
    _mover(lz, pos)
    _evento(lz, QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton)
    _evento(lz, QEvent.MouseButtonRelease, pos, Qt.LeftButton, Qt.NoButton)


def _arrastrar_asa(lz, i, destino_mm):
    q = lz._asas.posiciones_px()[i][1]
    _mover(lz, q)
    _evento(lz, QEvent.MouseButtonPress, q, Qt.LeftButton, Qt.LeftButton)
    meta = lz.a_px(*destino_mm)
    for k in range(1, 6):                                        # un recorrido, no un salto
        _mover(lz, q + (meta - q) * (k / 5), Qt.LeftButton)
    _evento(lz, QEvent.MouseButtonRelease, meta, Qt.LeftButton, Qt.NoButton)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(1280, 720)
    lz.ajustar_grilla = False
    lz.escala = 2.0
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _abrir(lz, modo="un", radio=R):
    c = lz.b.agregar_circulo((0, 0), radio)
    lz.resolver()
    lz.opciones["direccion_desfase"] = modo
    lz.set_herramienta("desfase")
    _clic(lz, lz.a_px(radio, 0))                                  # el clic de la persona sobre la curva
    assert lz.entrada is not None
    return c


def _teclear(lz, texto, campo=0):
    c = lz.entrada.campos[campo]
    c.selectAll()
    QTest.keyClicks(c, texto)


def _previa(lz):
    polis, nota, error = lz._previa_desfase()
    return sorted({round(max(abs(q[0]) for q in poli), 1) for poli in polis}), nota, error


def _textos(lz):
    return [c.text() for c in lz.entrada.campos]


def test_el_valor_inicial_entra_para_los_dos_lados_aunque_la_curva_sea_chica(lienzo):
    lz = lienzo
    _abrir(lz)
    inicial = float(_textos(lz)[0])
    assert 0 < inicial < R / 2                                    # el viejo «largo/5» daba 80 (imposible hacia adentro)
    assert _previa(lz)[0] == [round(R + inicial, 1)]              # afuera por defecto, como Fusion
    lz.entrada.findChildren(QToolButton)[0].click()               # ⇄ pasa hacia adentro con ese mismo valor
    assert _previa(lz)[0] == [round(R - inicial, 1)] and not _previa(lz)[2]


def test_asa_arrastrar_escribe_el_valor_con_signo_y_el_hover_no(lienzo):
    lz = lienzo
    _abrir(lz)
    inicial = _textos(lz)
    for x, y in ((10, 10), (0, 90), (40, -40)):                   # pasar el cursor no cambia nada
        _mover(lz, lz.a_px(x, y))
    assert _textos(lz) == inicial
    _arrastrar_asa(lz, 0, (R + 20, 0))
    assert float(_textos(lz)[0]) == pytest.approx(20, abs=0.5) and _previa(lz)[0] == [round(R + float(_textos(lz)[0]), 1)]
    _arrastrar_asa(lz, 0, (R - 30, 0))                            # pasa por cero y sigue hacia adentro
    assert float(_textos(lz)[0]) == pytest.approx(-30, abs=0.5) and _previa(lz)[0] == [round(R + float(_textos(lz)[0]), 1)]
    _teclear(lz, "5")                                             # lo escrito manda y el movimiento no lo pisa
    for x, y in ((10, 10), (0, 90)):
        _mover(lz, lz.a_px(x, y))
    assert _textos(lz) == ["5"]
    _arrastrar_asa(lz, 0, (R + 12, 0))                            # volver al ajuste visual: tirar del asa de nuevo
    assert float(_textos(lz)[0]) == pytest.approx(12, abs=0.5)


def test_la_previa_coincide_con_lo_confirmado_y_nada_cambia_antes(lienzo):
    lz = lienzo
    c = _abrir(lz)
    antes = json.dumps(lz.b.a_dict(), sort_keys=True)
    _arrastrar_asa(lz, 0, (R - 20, 0))
    previa = _previa(lz)[0]
    assert json.dumps(lz.b.a_dict(), sort_keys=True) == antes     # no se modifica el boceto antes de confirmar
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    nuevo = [r for r in _radios(lz.b) if r != R]
    assert [round(r, 1) for r in nuevo] == previa and c in lz.b.curvas
    assert len(lz.historial) == 1 and lz.herramienta == "desfase"   # un paso de deshacer; el comando se repite
    lz.deshacer()
    assert _radios(lz.b) == [R]


@pytest.mark.parametrize("modo,textos,esperado", [
    ("un", ["20"], [R, R + 20]), ("un", ["-20"], [R - 20, R]),
    ("dos", ["20", "-10"], [R - 10, R, R + 20]), ("simetrico", ["10"], [R - 10, R, R + 10]),
])
def test_los_tres_modos_con_la_ventana_confirman_lo_que_se_ve(lienzo, modo, textos, esperado):
    lz = lienzo
    _abrir(lz, modo)
    assert len(lz.entrada.campos) == (2 if modo == "dos" else 1)
    for i, t in enumerate(textos):
        _teclear(lz, t, i)
    polis, _nota, error = lz._previa_desfase()
    assert not error and len(polis) == (2 if modo != "un" else 1)
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert _radios(lz.b) == pytest.approx(esperado, abs=1e-6)


def test_interior_de_80_dice_por_que_marca_el_campo_y_deja_corregir_sin_reiniciar(lienzo):
    lz = lienzo
    _abrir(lz)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    _teclear(lz, "-80")
    assert _previa(lz)[2] == (0,) and "negativo" in mensajes[-1] and "background" in lz.entrada.campos[0].styleSheet()
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)           # Enter no confirma ni crea nada
    assert lz.entrada is not None and _radios(lz.b) == [R]
    _teclear(lz, "-20")                                           # y al corregir, el mismo comando sigue
    assert _previa(lz)[0] == [round(R - 20, 1)] and lz.entrada.campos[0].styleSheet() == ""


def test_dos_lados_marca_solo_el_campo_que_falla_y_conserva_el_valido(lienzo):
    lz = lienzo
    _abrir(lz, "dos")
    _teclear(lz, "20", 0)
    _teclear(lz, "-80", 1)
    assert _previa(lz)[2] == (1,)                                 # solo la Distancia 2; la 1.ª sigue siendo válida
    assert lz.entrada.campos[0].styleSheet() == "" and "background" in lz.entrada.campos[1].styleSheet()
    assert _textos(lz) == ["20", "-80"] and _radios(lz.b) == [R]
    _teclear(lz, "-10", 1)
    assert not _previa(lz)[2] and _previa(lz)[0] == [round(R - 10, 1), round(R + 20, 1)]
    _teclear(lz, "x", 0)                                          # un error de lo escrito en la 1.ª no señala la 2.ª
    assert _previa(lz)[2] == (0,)


def test_cambiar_la_direccion_con_la_barra_abierta_rearma_todo(lienzo):
    lz = lienzo
    _abrir(lz, "dos")
    _teclear(lz, "20", 0)
    _teclear(lz, "-10", 1)
    lz.cambiar_opcion_desfase("direccion_desfase", "simetrico")        # lo que hace el combo de la paleta
    assert len(lz.entrada.campos) == 1 and _textos(lz) == ["20"] and lz._desfase_modo == "simetrico"
    assert lz.picks and lz.seleccion and len(lz._asas.asas) == 1
    assert _previa(lz) == ([round(R - 20, 1), round(R + 20, 1)], "Simétrico", False)
    lz.cambiar_opcion_desfase("direccion_desfase", "dos")
    assert _textos(lz) == ["20", "-20"] and len(lz._asas.asas) == 2    # el simétrico es (d, -d)
    lz.cambiar_opcion_desfase("direccion_desfase", "un")
    assert _textos(lz) == ["20"] and lz._desfase_modo == "un" and _previa(lz)[0] == [round(R + 20, 1)]
    assert _radios(lz.b) == [R]
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)               # confirma el modo que se ve
    assert _radios(lz.b) == pytest.approx([R, R + 20])


def test_cambiar_de_modo_con_un_error_no_deja_campos_viejos(lienzo):
    lz = lienzo
    _abrir(lz, "dos")
    _teclear(lz, "-80", 0)
    assert _previa(lz)[2]
    lz.cambiar_opcion_desfase("direccion_desfase", "un")
    assert len(lz.entrada.campos) == 1 and _previa(lz)[2] == (0,) and _textos(lz) == ["-80"]
    lz.cambiar_opcion_desfase("direccion_desfase", "dos")
    assert _textos(lz) == ["-80", "0"] and _previa(lz)[2] == (0,)


def test_clic_en_el_lienzo_no_cierra_cambia_de_curva_y_enter_acepta(lienzo):
    lz = lienzo
    _abrir(lz)
    otra = lz.b.agregar_circulo((300, 0), 20)
    lz.resolver()
    _teclear(lz, "7")
    _clic(lz, lz.a_px(-100, 150))                                     # el vacío no cierra ni cambia nada
    assert lz.entrada is not None and _textos(lz) == ["7"] and lz.picks
    _clic(lz, lz.a_px(320, 0))                                        # otra curva: se pasa a ella con el mismo valor
    assert lz.picks == [otra] and _textos(lz) == ["7"] and lz.entrada is not None
    QTest.keyClick(lz, Qt.Key_Return)                                  # Enter con el foco en el lienzo: acepta
    assert lz.entrada is None and _radios(lz.b) == pytest.approx([20, 27, R])


def test_esc_cancela_sin_tocar_nada_y_el_boton_cancelar_tambien(lienzo):
    lz = lienzo
    _abrir(lz)
    antes = json.dumps(lz.b.a_dict(), sort_keys=True)
    _teclear(lz, "-20")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    assert lz.entrada is None and json.dumps(lz.b.a_dict(), sort_keys=True) == antes and lz.herramienta == "desfase"
    _clic(lz, lz.a_px(R, 0))
    botones = lz.entrada.findChildren(QToolButton)
    assert [b.text() for b in botones] == ["⇄", "✓", "✕"] and "Esc" in botones[2].toolTip() and "Enter" in botones[1].toolTip()
    botones[2].click()
    assert lz.entrada is None and json.dumps(lz.b.a_dict(), sort_keys=True) == antes
    _clic(lz, lz.a_px(R, 0))
    lz.entrada.findChildren(QToolButton)[1].click()                   # ✓ acepta
    assert len(_radios(lz.b)) == 2


def test_tab_pasa_de_campo_y_acepta_expresiones_y_coma_decimal(lienzo):
    lz = lienzo
    _abrir(lz, "dos")
    c0, c1 = lz.entrada.campos
    c0.setFocus()
    QTest.keyClick(c0, Qt.Key_Tab)
    assert c1.hasFocus() or lz.entrada.focusWidget() is c1
    _teclear(lz, "2 * 5", 0)
    _teclear(lz, "-2,5", 1)
    assert not _previa(lz)[2] and _previa(lz)[0] == [round(R - 2.5, 1), round(R + 10, 1)]


def test_seleccion_de_cadena_apagada_en_la_ventana(lienzo):
    lz = lienzo
    lineas = lz.b.agregar_rectangulo((0, 0), (100, 60))
    lz.resolver()
    lz.set_herramienta("desfase")
    _clic(lz, lz.a_px(50, 0))
    assert sorted(lz.seleccion) == sorted(lineas)
    lz.cambiar_opcion_desfase("seleccion_cadena", False)
    assert lz.seleccion == [lineas[0]] and lz.entrada is not None
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    assert len(lz.b.curvas) == 5


def test_repintar_sin_cambiar_nada_no_recalcula_la_previa(lienzo, monkeypatch):
    lz = lienzo
    _abrir(lz)
    llamadas = []
    original = Boceto.copia
    monkeypatch.setattr(Boceto, "copia", lambda self: (llamadas.append(1), original(self))[1])
    for _ in range(5):
        lz.grab()
    assert llamadas == []                                             # BOC-51: repintar no vuelve a armar el desfase
    _teclear(lz, "9")
    assert llamadas


@pytest.mark.parametrize("ancho,alto", [(1280, 720), (1024, 640), (800, 520), (640, 400)])
def test_barra_y_nota_quedan_a_la_vista_junto_a_los_bordes_y_al_achicar(lienzo, ancho, alto):
    lz = lienzo
    lz.resize(ancho, alto)
    lz.escala = 1.0
    lz.centro = [R * 0.8, 0.0]                                        # la curva queda pegada al borde derecho
    c = lz.b.agregar_circulo((0, 0), R)
    lz.resolver()
    lz.opciones["direccion_desfase"] = "dos"
    lz.set_herramienta("desfase")
    _clic(lz, lz.a_px(R, 0))
    _teclear(lz, "-900")                                              # un error largo para que la nota se parta
    barra = lz.entrada.geometry()
    zona = lz.rect()
    assert zona.contains(barra), (barra, zona)
    marco, texto = lz._marco_nota_desfase(lz._previa_desfase()[1], QFont())
    assert marco.left() >= 0 and marco.right() <= zona.right() and marco.top() >= 0 and marco.bottom() <= zona.bottom()
    assert "Enter" in texto and c in lz.b.curvas
    lz.resize(ancho - 200, alto - 100)                                # al cambiar el tamaño de la ventana
    QApplication.processEvents()
    assert lz.rect().contains(lz.entrada.geometry())


def test_la_paleta_a_la_derecha_no_tapa_la_barra(lienzo, app):
    lz = lienzo
    from PySide6.QtWidgets import QWidget
    area = QWidget()
    area.resize(1280, 720)
    lz.setParent(area)
    lz.setGeometry(0, 0, 1280, 720)
    paleta = QWidget(area)
    paleta.setGeometry(1000, 100, 260, 400)
    paleta.show()
    area.paleta, area.laterales = paleta, []
    area.show()
    lz.show()
    lz.escala, lz.centro = 1.0, [R * 0.8, 0.0]
    lz.b.agregar_circulo((0, 0), R)
    lz.resolver()
    lz.set_herramienta("desfase")
    _clic(lz, lz.a_px(R, 0))
    assert lz.entrada.geometry().right() < 1000                       # queda a la izquierda de la paleta
    area.deleteLater()


def test_fijar_el_valor_escrito_y_cambiar_de_lado_con_invertir_no_pierde_el_valor(lienzo):
    lz = lienzo
    _abrir(lz)
    _teclear(lz, "20")
    boton = lz.entrada.findChildren(QToolButton)[0]
    boton.click()
    assert _textos(lz) == ["20"] and _previa(lz)[0] == [round(R - 20, 1)]
    _arrastrar_asa(lz, 0, (R + 5, 0))                                 # con ⇄ activo el asa mide hacia el otro lado
    assert float(_textos(lz)[0]) == pytest.approx(-5, abs=0.5)


def test_con_la_curva_ya_elegida_el_desfase_arranca_sin_otro_clic(lienzo):
    lz = lienzo
    c = lz.b.agregar_circulo((0, 0), R)
    lz.resolver()
    lz.seleccion = [c]                                                # elegida antes de pulsar Desfase (video de Fusion)
    lz.set_herramienta("desfase")
    assert lz.entrada is not None and lz.picks == [c] and _previa(lz)[0] == [round(R + float(_textos(lz)[0]), 1)]
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Escape)
    assert lz.entrada is None and lz.seleccion == []                  # cancelar no deja la curva «elegida»
    lz.set_herramienta("desfase")
    assert lz.entrada is None                                         # y sin selección pide el clic, como siempre


def test_la_barra_se_mide_con_el_estilo_puesto_y_no_corta_las_etiquetas(lienzo):
    lz = lienzo
    _abrir(lz, "dos")
    from PySide6.QtWidgets import QLabel
    for etiqueta in lz.entrada.findChildren(QLabel):
        assert etiqueta.width() >= etiqueta.sizeHint().width(), etiqueta.text()
    assert all(c.width() >= 70 for c in lz.entrada.campos)
