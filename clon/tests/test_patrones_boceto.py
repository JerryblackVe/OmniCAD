"""Patrón circular y rectangular del boceto (2026-10-31): fórmulas, edición, validación y vista previa.

La cantidad CUENTA el original. Circular: 360° reparte en `total / cantidad`; otro ángulo, en `total / (cantidad − 1)`
(el original y la última copia quedan en los extremos); negativo = horario. Rectangular: extensión = (n − 1) × espaciado.
Ventana, MCP y CLI usan los mismos métodos del núcleo (`validar_patron`, `previa_patron`)."""
import json
import math

import pytest

from omnicad import api
from omnicad.restricciones import Boceto, ErrorBoceto


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, {"sketch": "U", **args})
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, **args):
    r = api.llamar(s, nombre, {"sketch": "U", **args})
    assert not r["ok"], r
    return r


def nuevo():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"name": "U"})
    return s


def circulo(s, x=20.0, y=0.0, r=2.0):
    return [llamar(s, "draw_circle", center_x=x, center_y=y, radius=r)["entities"][0]["id"]]


def centros(s):
    return [tuple(e["center"]) for e in llamar(s, "get_sketch")["entities"] if e["type"] == "circle"]


def iguales(a, b, tol=1e-3):
    """Mismos puntos sin importar el orden (get_sketch redondea a 4 decimales)."""
    resto = list(b)
    if len(a) != len(b):
        return False
    for q in a:
        m = min(resto, key=lambda r: math.dist(q, r))
        if math.dist(q, m) > tol:
            return False
        resto.remove(m)
    return True


def en_circulo(c, r, grados):
    return [(c[0] + r * math.cos(math.radians(g)), c[1] + r * math.sin(math.radians(g))) for g in grados]


# ------------------------------------------------------------------ circular C1–C8
def test_c1_ocho_posiciones_a_45_grados_incluyendo_el_original():
    s = nuevo()
    llamar(s, "sketch_circular_pattern", entities=circulo(s), count=8)
    assert iguales(centros(s), en_circulo((0, 0), 20, range(0, 360, 45)))


def test_c2_el_centro_elegido_se_respeta():
    s = nuevo()
    llamar(s, "sketch_circular_pattern", entities=circulo(s, 30, 10), count=6, center_x=10, center_y=10)
    cs = centros(s)
    assert len(cs) == 6 and all(abs(math.dist(q, (10, 10)) - 20) < 1e-3 for q in cs)


def test_c3_cinco_posiciones_en_180_incluyen_ambos_extremos():
    s = nuevo()
    llamar(s, "sketch_circular_pattern", entities=circulo(s), count=5, total_angle=180)
    assert iguales(centros(s), en_circulo((0, 0), 20, (0, 45, 90, 135, 180)))


def test_c4_sentido_horario_con_angulo_negativo():
    s = nuevo()
    llamar(s, "sketch_circular_pattern", entities=circulo(s), count=5, total_angle=-180)
    assert iguales(centros(s), en_circulo((0, 0), 20, (0, -45, -90, -135, -180)))


def test_c5_cantidad_de_6_a_12_regenera_el_patron():
    s = nuevo()
    pid = llamar(s, "sketch_circular_pattern", entities=circulo(s), count=6)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, count=12)
    assert iguales(centros(s), en_circulo((0, 0), 20, range(0, 360, 30)))


def test_c6_excluir_una_copia_no_mueve_las_demas():
    s = nuevo()
    pid = llamar(s, "sketch_circular_pattern", entities=circulo(s), count=12)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, suppress=[2, 6])        # las posiciones 3 y 7
    quedan = [g for k, g in enumerate(range(0, 360, 30)) if k not in (3, 7)]
    assert iguales(centros(s), en_circulo((0, 0), 20, quedan))
    assert llamar(s, "get_sketch")["patterns"][0]["suppressed"] == [2, 6]


def test_c7_cambiar_el_centro_despues_regenera_el_patron():
    s = nuevo()
    pid = llamar(s, "sketch_circular_pattern", entities=circulo(s), count=4)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, center_x=5, center_y=5)
    cs = centros(s)
    assert len(cs) == 4 and all(abs(math.dist(q, (5, 5)) - math.dist((20, 0), (5, 5))) < 1e-3 for q in cs)
    assert llamar(s, "get_sketch")["patterns"][0]["parameters"]["center"] == [5.0, 5.0]


def test_c7_el_centro_puede_ser_un_punto_y_las_copias_lo_siguen():
    s = nuevo()
    p = llamar(s, "draw_point", x=0, y=0)["points"][0]
    pid = llamar(s, "sketch_circular_pattern", entities=circulo(s), count=3, center_point=p)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, count=4, center_x=1, center_y=1)
    assert len(centros(s)) == 4
    assert falla(s, "edit_sketch_pattern", pattern=pid, center_point=9999)["error_kind"] == "ENTITY_NOT_FOUND"
    assert falla(s, "edit_sketch_pattern", pattern=pid, center_x=3)["error_kind"] == "INVALID_ARGUMENTS"


def test_c8_lineas_arcos_y_compuestas_conservan_su_forma():
    s = nuevo()
    ids = [llamar(s, "draw_line", start_x=10, start_y=0, end_x=15, end_y=2)["entities"][0]["id"]]
    ids += [llamar(s, "draw_arc", center_x=12, center_y=-8, start_x=15, start_y=-8, sweep_angle=90)["entities"][0]["id"]]
    ids += [e["id"] for e in llamar(s, "draw_rectangle", x1=20, y1=10, x2=26, y2=14)["entities"]]
    llamar(s, "sketch_circular_pattern", entities=ids, count=3)
    g = llamar(s, "get_sketch")["entities"]
    assert sum(e["type"] == "line" for e in g) == 3 * 5 and sum(e["type"] == "arc" for e in g) == 3


def test_c8_la_copia_gira_sin_deformarse():
    b = Boceto()
    c = b.agregar_circulo((20, 0), 3)
    a = b.agregar_linea((10, 0), (14, 3))
    b.patron_circular([c, a], (0, 0), 4, 90)
    medidas = sorted(round(math.dist(b.coords(l.p1), b.coords(l.p2)), 9) for l in b.curvas.values()
                     if l.tipo == "linea")
    assert medidas == [5.0] * 4
    assert sorted(round(x.radio, 9) for x in b.curvas.values() if x.tipo == "circulo") == [3.0] * 4


# ------------------------------------------------------------------ rectangular R1–R10
def test_r1_r2_cuatro_columnas_tres_filas_con_espaciado():
    s = nuevo()
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=4, distance1=20, count2=3,
           distance2=15, spacing="spacing")
    assert iguales(centros(s), [(20 * i, 15 * j) for i in range(4) for j in range(3)])


def test_r3_cambiar_cantidades_conserva_el_paso():
    s = nuevo()
    pid = llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=4, distance1=20, count2=3,
                 distance2=15, spacing="spacing")["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, count1=2, count2=2)
    assert iguales(centros(s), [(0, 0), (20, 0), (0, 15), (20, 15)])


def test_r4_direccion_inclinada_30_grados():
    s = nuevo()
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=3, distance1=10, angle=30,
           spacing="spacing")
    assert iguales(centros(s), [(10 * k * math.cos(math.radians(30)), 10 * k * math.sin(math.radians(30)))
                                for k in range(3)])


def test_r5_dos_vectores_no_ortogonales():
    s = nuevo()
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=2, distance1=10, count2=2,
           distance2=10, angle=0, angle2=60, spacing="spacing")
    w = (10 * math.cos(math.radians(60)), 10 * math.sin(math.radians(60)))
    assert iguales(centros(s), [(0, 0), (10, 0), w, (10 + w[0], w[1])])


def test_r5_la_direccion_2_puede_ser_una_linea_del_boceto():
    s = nuevo()
    linea = llamar(s, "draw_line", start_x=100, start_y=100, end_x=100, end_y=105)["entities"][0]["id"]
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=2, distance1=10, count2=2,
           distance2=7, spacing="spacing", direction2_line=linea)
    assert iguales(centros(s), [(0, 0), (10, 0), (0, 7), (10, 7)])


def test_r6_invertir_una_direccion_con_distancia_negativa():
    s = nuevo()
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=3, distance1=-10, spacing="spacing")
    assert iguales(centros(s), [(0, 0), (-10, 0), (-20, 0)])


def test_r7_extension_y_espaciado_se_relacionan_con_n_menos_1():
    s = nuevo()
    pid = llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=5, distance1=40,
                 spacing="extent")["pattern"]
    assert iguales(centros(s), [(10 * k, 0) for k in range(5)])
    llamar(s, "edit_sketch_pattern", pattern=pid, spacing="spacing")
    assert iguales(centros(s), [(40 * k, 0) for k in range(5)])


def test_r8_excluir_posiciones_individuales():
    s = nuevo()
    pid = llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=5, distance1=40)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, suppress=[1, 3])
    assert iguales(centros(s), [(0, 0), (10, 0), (30, 0)])


def test_r8_simetrico_por_direccion():
    s = nuevo()
    llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=3, distance1=10, count2=3, distance2=10,
           spacing="spacing", symmetric=True, symmetric2=False)
    assert iguales(centros(s), [(10 * i, 10 * j) for i in (-1, 0, 1) for j in (0, 1, 2)])


def test_r9_modificar_los_parametros_de_un_patron_existente():
    s = nuevo()
    pid = llamar(s, "sketch_rectangular_pattern", entities=circulo(s, 0, 0), count1=2, distance1=10)["pattern"]
    llamar(s, "edit_sketch_pattern", pattern=pid, count1=3, distance1=30, count2=2, distance2=8, angle=90)
    assert iguales(centros(s), [(-8 * j, 15 * i) for i in range(3) for j in range(2)])
    p = llamar(s, "get_sketch")["patterns"][0]["parameters"]
    assert (p["count1"], p["distance1"], p["count2"], p["angle"], p["angle2"]) == (3, 30.0, 2, 90.0, 180.0)


def test_r10_entidades_compuestas_conservan_la_forma_y_las_relaciones():
    s = nuevo()
    r = [e["id"] for e in llamar(s, "draw_rectangle", x1=0, y1=0, x2=5, y2=3)["entities"]]
    llamar(s, "sketch_rectangular_pattern", entities=r, count1=3, distance1=10, count2=2, distance2=8,
           spacing="spacing")
    g = llamar(s, "get_sketch")
    assert sum(e["type"] == "line" for e in g["entities"]) == 6 * 4
    assert [p["area"] for p in g["profiles"]] == [15.0] * 6          # seis rectángulos cerrados e iguales


# ------------------------------------------------------------------ casos límite
@pytest.mark.parametrize("args", [
    {"count": 0}, {"count": 1}, {"count": -3}, {"count": 3, "total_angle": 0}, {"count": 3, "total_angle": 361},
    {"count": 3, "total_angle": -400}, {"count": 3, "total_angle": float("nan")},
    {"count": 3, "center_x": 20, "center_y": 0}])
def test_circular_rechaza_lo_invalido_sin_crear_nada(args):
    s = nuevo()
    c = circulo(s)
    r = api.llamar(s, "sketch_circular_pattern", {"sketch": "U", "entities": c, **args})
    assert not r["ok"]
    assert len(centros(s)) == 1


@pytest.mark.parametrize("args", [
    {"count1": 0, "distance1": 5}, {"count1": -2, "distance1": 5}, {"count1": 1, "distance1": 5},
    {"count1": 3, "distance1": 0}, {"count1": 3, "distance1": float("inf")},
    {"count1": 2, "distance1": 5, "count2": 2, "distance2": 5, "angle": 0, "angle2": 180},
    {"count1": 2, "distance1": 5, "count2": 0}])
def test_rectangular_rechaza_lo_invalido_sin_crear_nada(args):
    s = nuevo()
    c = circulo(s)
    r = api.llamar(s, "sketch_rectangular_pattern", {"sketch": "U", "entities": c, **args})
    assert not r["ok"]
    assert len(centros(s)) == 1


def test_cantidades_decimales_se_rechazan():
    s = nuevo()
    c = circulo(s)
    assert not api.llamar(s, "sketch_rectangular_pattern", {"sketch": "U", "entities": c, "count1": 2.5,
                                                              "distance1": 5})["ok"]


def test_con_una_sola_copia_en_la_direccion_2_su_distancia_no_se_usa():
    Boceto.validar_patron("rectangular", {"cantidad1": 3, "distancia1": 5, "cantidad2": 1, "distancia2": 0,
                                           "dir1": [1, 0], "dir2": [0, 1], "modo": "extension"})


def test_el_tope_de_copias_es_el_mismo_en_ventana_y_api():
    with pytest.raises(ErrorBoceto, match="admite hasta 200"):
        Boceto.validar_patron("circular", {"cantidad": 202, "angulo_total": 360})
    s = nuevo()
    assert falla(s, "sketch_circular_pattern", entities=circulo(s), count=202)["error_kind"] == "INVALID_ARGUMENTS"


def test_referencia_perdida_del_centro_se_dice_y_no_rompe():
    b = Boceto()
    c = b.agregar_circulo((20, 0), 1)
    centro = b.agregar_punto(0, 0)
    b.patron_circular([c], centro, 3)
    pid = b.patrones[0]["id"]
    del b.puntos[centro]
    with pytest.raises(ErrorBoceto, match="No existe el punto"):
        b.editar_patron(pid, cantidad=4)


# ------------------------------------------------------------------ la vista previa es el mismo cálculo que el patrón
def test_la_vista_previa_coincide_con_las_copias_creadas():
    b = Boceto()
    a = b.agregar_linea((10, 0), (14, 3))
    params = {"centro": [1.0, 2.0], "cantidad": 5, "angulo_total": 200.0, "simetrico": False}
    previa = b.previa_patron("circular", params, [[(10, 0), (14, 3)]], suprimidos={1})
    assert len(previa) == 3                                    # 4 copias menos la suprimida
    b.patron_circular([a], (1.0, 2.0), 5, 200.0, suprimir=[1])
    creadas = sorted(tuple(round(v, 9) for q in (b.coords(c.p1), b.coords(c.p2)) for v in q)
                     for k, c in b.curvas.items() if k != a)
    esperadas = sorted(tuple(round(v, 9) for q in poli[0] for v in q) for poli in previa)
    assert creadas == esperadas


def test_la_previa_rectangular_no_toca_el_boceto():
    b = Boceto()
    b.agregar_circulo((0, 0), 1)
    antes = (len(b.puntos), len(b.curvas), len(b.restricciones))
    previa = b.previa_patron("rectangular", {"cantidad1": 4, "distancia1": 30, "cantidad2": 3, "distancia2": 10,
                                             "dir1": [1, 0], "dir2": [0, 1], "modo": "extension", "simetrico": False,
                                             "linea1": None, "linea2": None}, [[(0, 0), (1, 1)]])
    assert len(previa) == 11
    assert (len(b.puntos), len(b.curvas), len(b.restricciones)) == antes


# ------------------------------------------------------------------ compatibilidad con archivos guardados
def test_un_patron_guardado_antes_de_simetrico2_se_abre_y_se_edita_igual():
    b = Boceto()
    c = b.agregar_circulo((0, 0), 1)
    b.patron_rectangular([c], 3, 10, 2, 8, modo="espaciado", simetrico=True)
    d = json.loads(json.dumps(b.a_dict()))
    assert "simetrico2" not in d["patrones"][0]["params"]
    b2 = Boceto.desde_dict(d)
    b2.editar_patron(b2.patrones[0]["id"], cantidad1=4)
    xs = sorted(round(b2.coords(p.id)[0], 6) for p in b2.puntos.values())
    assert len(xs) == 4 * 2 and min(xs) == -20.0 and max(xs) == 10.0


def test_el_centro_puede_ser_el_punto_central_de_lo_elegido_y_se_rechaza():
    b = Boceto()
    c = b.agregar_circulo((20, 0), 2)
    with pytest.raises(ErrorBoceto, match="coincide con la geometría"):
        b.patron_circular([c], b.curvas[c].centro, 4)
    with pytest.raises(ErrorBoceto, match="coincide con la geometría"):
        b.patron_circular([c], (20.0, 0.0), 4)
    assert len(b.curvas) == 1 and not b.patrones


# ------------------------------------------------------------------ el controlador de la ventana (panel + lienzo, sin mostrarla)
@pytest.fixture
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app_qt):
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui import editor_boceto
    from omnicad.ui.panel_patron import PanelPatron
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lz.resize(800, 600)
    panel = PanelPatron()
    ctl = lz.patron
    ctl.panel = panel
    panel.cambio.connect(ctl.recibir)
    panel.invertir.connect(ctl.invertir)
    yield lz, panel, ctl
    panel.deleteLater()


def test_escribir_el_centro_con_decimales_no_se_pisa_a_mitad_de_camino(ventana):
    lz, panel, ctl = ventana
    c = lz.b.agregar_circulo((20, 0), 2)
    lz.seleccion = [c]
    lz.set_herramienta("patron_circular")
    for texto in ("1", "12", "12.", "12.5"):
        panel.campos["centro_x"].setText(texto)
        assert panel.campos["centro_x"].text() == texto          # antes: «12.» se reescribía como «12» y se perdía el punto
    panel.campos["centro_y"].setText("-3")
    assert ctl.calcular()["params"]["centro"] == [12.5, -3.0]


def test_invertir_una_expresion_la_niega_entera_y_dos_veces_vuelve_igual(ventana):
    lz, panel, ctl = ventana
    lz.seleccion = [lz.b.agregar_circulo((0, 0), 1)]
    lz.set_herramienta("patron_rectangular")
    campo = panel.campos["distancia1"]
    campo.setText("2+3*4")
    panel.invertir.emit("distancia1")
    assert campo.text() == "-(2+3*4)" and ctl.calcular()["params"]["distancia1"] == -14
    panel.invertir.emit("distancia1")
    assert campo.text() == "2+3*4"
    campo.setText("20")
    panel.invertir.emit("distancia1")
    assert campo.text() == "-20"


def test_las_exclusiones_de_una_cantidad_anterior_no_se_guardan(ventana):
    lz, panel, ctl = ventana
    lz.seleccion = [lz.b.agregar_circulo((0, 0), 1)]
    lz.set_herramienta("patron_rectangular")
    panel.campos["cantidad1"].setText("6")
    ctl.suprimidos = {1, 4}
    panel.campos["cantidad1"].setText("3")                 # ahora hay 2 copias: el índice 4 ya no existe
    assert ctl.aceptar()
    assert lz.b.patrones[0]["suprimidos"] == [1]
