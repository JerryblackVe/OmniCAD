"""BOC-9: ajustes geométricos puros durante el dibujo, sin interfaz."""
import math

import pytest

from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones.inferencia import Inferencia, inferir


@pytest.mark.parametrize("coincidente, tipo", [(False, "punto_medio"), (True, "coincidente")])
def test_punto_medio_gana_a_sobre_curva_y_mayus_cambia_la_restriccion(coincidente, tipo):
    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    r = inferir(b, (5.1, 0.05), 0.3, coincidente=coincidente)
    assert isinstance(r, Inferencia)
    assert r.tipo == "punto_medio"
    assert r.xy == pytest.approx((5, 0), abs=1e-9)
    assert r.objetivo == linea
    assert r.restriccion == (tipo, linea)


def test_punto_medio_de_arco_que_cruza_el_cero_angular():
    b = Boceto()
    arco = b.agregar_arco_centro((0, 0), (0, -5), (5, 0))
    medio = (5 / math.sqrt(2), -5 / math.sqrt(2))
    r = inferir(b, (medio[0] + 0.1, medio[1]), 0.2)
    assert r.tipo == "punto_medio"
    assert r.xy == pytest.approx(medio, abs=1e-9)
    assert r.restriccion == ("punto_medio", arco)


def test_sobre_circulo_proyecta_al_radio_exacto():
    b = Boceto()
    circulo = b.agregar_circulo((0, 0), 5)
    r = inferir(b, (5.05, 0.1), 0.2)
    assert r.tipo == "sobre_curva"
    assert math.hypot(*r.xy) == pytest.approx(5, abs=1e-9)
    assert r.restriccion == ("coincidente", circulo)


@pytest.mark.parametrize("signo", [-1, 1])
def test_tangente_desde_base_exterior_elige_el_contacto_mas_cercano(signo):
    b = Boceto()
    circulo = b.agregar_circulo((0, 0), 5)
    base = (10, 0)
    contacto = (2.5, signo * math.sqrt(18.75))
    r = inferir(b, (contacto[0] + 0.05, contacto[1] + 0.03), 0.2, base)
    assert r.tipo == "tangente"
    assert r.xy == pytest.approx(contacto, abs=1e-9)
    assert math.hypot(*r.xy) == pytest.approx(5, abs=1e-9)
    assert abs(sum((r.xy[i] - base[i]) * r.xy[i] for i in range(2))) < 1e-9
    assert r.restriccion == ("tangente", circulo)
    assert r.guias == [(base, r.xy)]


def test_tangente_a_elipse_girada_y_trasladada():
    b = Boceto()
    giro = math.radians(37)
    def mundo(x, y):
        return (3 + x * math.cos(giro) - y * math.sin(giro),
                7 + x * math.sin(giro) + y * math.cos(giro))
    elipse = b.agregar_elipse(mundo(0, 0), mundo(6, 0), 3, ejes=False)
    contacto = mundo(3, 3 * math.sqrt(3) / 2)
    r = inferir(b, (contacto[0] + 0.03, contacto[1] - 0.02), 0.15, mundo(12, 0))
    assert r.tipo == "tangente"
    assert r.xy == pytest.approx(contacto, abs=1e-9)
    assert r.restriccion == ("tangente", elipse)


def test_tangente_respeta_el_tramo_del_arco():
    b = Boceto()
    arco = b.agregar_arco_centro((0, 0), (5, 0), (0, 5))
    r = inferir(b, (2.52, math.sqrt(18.75) + 0.01), 0.15, (10, 0))
    assert r.tipo == "tangente" and r.objetivo == arco
    assert inferir(b, (2.5, -math.sqrt(18.75)), 0.15, (10, 0)) is None


def test_base_interior_no_inventa_tangencia():
    b = Boceto()
    b.agregar_circulo((0, 0), 5)
    r = inferir(b, (3, 4.01), 0.1, (0, 0))
    assert r.tipo == "sobre_curva"


def test_perpendicular_devuelve_pie_y_coincidencia_sobre_segmento():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    base = (3, 4)
    r = inferir(b, (3.05, 0.2), 0.3, base)
    assert r.tipo == "perpendicular"
    assert r.xy == pytest.approx((3, 0), abs=1e-9)
    assert r.objetivo == linea
    assert r.restriccion == ("perpendicular", linea, ("coincidente", linea))
    assert r.guias == [(base, r.xy)]


def test_perpendicular_en_prolongacion_no_declara_coincidencia():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    r = inferir(b, (10.1, 0.1), 0.25, (10.1, 4))
    assert r.tipo == "perpendicular"
    assert r.xy == pytest.approx((10.1, 0), abs=1e-9)
    assert r.restriccion == ("perpendicular", linea)


def test_perpendicular_a_linea_oblicua():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 10))
    r = inferir(b, (2.02, 1.99), 0.1, (4, 0))
    assert r.tipo == "perpendicular"
    assert r.xy == pytest.approx((2, 2), abs=1e-9)


def test_tolerancia_angular_descarta_perpendicular_y_tangente():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    assert inferir(b, (3.05, 0.2), 0.3, (3, 4), angulo_tol=0.001).tipo == "sobre_curva"
    b = Boceto()
    b.agregar_circulo((0, 0), 5)
    assert inferir(b, (2.55, math.sqrt(18.75)), 0.2, (10, 0), angulo_tol=0.001).tipo == "sobre_curva"


@pytest.mark.parametrize("cursor, tipo, ajustado", [
    ((7, 2.1), "horizontal", (7, 2)), ((1.1, 8), "vertical", (1, 8)),
    ((-8, 2.1), "horizontal", (-8, 2)), ((1.1, -8), "vertical", (1, -8)),
])
def test_horizontal_vertical_con_guia(cursor, tipo, ajustado):
    base = (1, 2)
    r = inferir(Boceto(), cursor, 0.2, base)
    assert r.tipo == tipo and r.objetivo is None
    assert r.xy == pytest.approx(ajustado, abs=1e-9)
    assert r.guias == [(base, r.xy)]


@pytest.mark.parametrize("curva", ["linea", "elipse", "spline", "conica"])
def test_sobre_curvas_reutiliza_proyeccion_del_modelo(curva):
    b = Boceto()
    if curva == "linea":
        cid = b.agregar_linea((0, 0), (10, 0))
        cursor, esperado = (2, 0.05), (2, 0)
    elif curva == "elipse":
        cid = b.agregar_elipse((0, 0), (6, 0), 3, ejes=False)
        cursor, esperado = (6.05, 0), (6, 0)
    elif curva == "spline":
        cid = b.agregar_spline([(0, 0), (2, 0), (4, 0)], modo="control", grado=2)
        cursor, esperado = (1, 0.05), (1, 0)
    else:
        cid = b.agregar_conica((0, 0), (2, 2), (4, 0), 0.5)
        cursor, esperado = (2, 1.05), (2, 1)
    r = inferir(b, cursor, 0.1)
    assert r.tipo == "sobre_curva" and r.objetivo == cid
    assert r.xy == pytest.approx(esperado, abs=1e-7)


@pytest.mark.parametrize("por_punto", [False, True])
def test_excluir_curva_o_sus_puntos_evita_autoinferencia(por_punto):
    b = Boceto()
    cid = b.agregar_linea((0, 0), (10, 0))
    excluir = (b.curvas[cid].p1,) if por_punto else (cid,)
    assert inferir(b, (5, 0), 0.2, excluir=excluir) is None


def test_no_hay_inferencia_ni_saltos_a_geometria_lejana():
    b = Boceto()
    b.agregar_circulo((0, 0), 5)
    b.agregar_linea((0, -20), (10, -20))
    assert inferir(b, (50, 50), 0.2) is None
    assert inferir(b, (-65, 25 * math.sqrt(3)), 0.2, (10, 0)) is None
    assert inferir(Boceto(), (0, 0), 0.2, (0, 0)) is None


def test_inferencia_es_determinista_y_no_modifica_el_boceto():
    b = Boceto()
    primero = b.agregar_linea((0, 0), (10, 0))
    b.agregar_linea((0, 0), (10, 0))
    antes = b.a_dict()
    r = inferir(b, (5, 0.1), 0.2)
    assert r.objetivo == primero
    assert inferir(b, (5, 0.1), 0.2) == r
    assert b.a_dict() == antes


def test_a_igual_prioridad_gana_la_curva_mas_cercana():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    cercana = b.agregar_linea((0, 0.2), (10, 0.2))
    assert inferir(b, (2, 0.15), 0.3).objetivo == cercana
    assert inferir(Boceto(), (2, 3), 0.3) is None


@pytest.mark.parametrize("tipo", ["punto_medio", "coincidente", "tangente", "perpendicular",
                                  "horizontal", "vertical"])
def test_restricciones_propuestas_son_aplicables_y_no_mueven_el_ajuste(tipo):
    b = Boceto()
    base = (3, 4)
    if tipo == "tangente":
        b.agregar_circulo((0, 0), 5)
        base, cursor = (10, 0), (2.52, math.sqrt(18.75))
    elif tipo in ("horizontal", "vertical"):
        cursor = (8, 4.05) if tipo == "horizontal" else (3.05, 9)
    else:
        b.agregar_linea((0, 0), (10, 0))
        cursor = (5.05, 0.01) if tipo == "punto_medio" else (3.01, 0.02)
    r = inferir(b, cursor, 0.2, base if tipo != "coincidente" else None)
    assert r.restriccion[0] == tipo
    for cid in b.curvas:
        b.agregar_restriccion("fijo", [cid])
    inicio = b.agregar_punto(*base)
    b.agregar_restriccion("fijo", [inicio])
    fin = b.agregar_punto(*r.xy)
    if tipo in ("punto_medio", "coincidente"):
        b.agregar_restriccion(tipo, [fin, r.objetivo])
    else:
        linea = b.agregar_linea(inicio, fin)
        b.agregar_restriccion(tipo, [linea, r.objetivo] if r.objetivo is not None else [linea])
        if len(r.restriccion) > 2:
            adicional, objetivo = r.restriccion[2]
            b.agregar_restriccion(adicional, [fin, objetivo])
    resultado = resolver(b)
    assert resultado.ok, resultado.descripcion()
    assert b.coords(fin) == pytest.approx(r.xy, abs=1e-7)
