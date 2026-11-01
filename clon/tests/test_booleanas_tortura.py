# -*- coding: utf-8 -*-
"""Resultados malos de booleanas que encontró la tortura del 2026-11-01 (evidencias/tortura_2026-11-01/):
B-125 pieza perdida con contacto casi tangente, B-126 aristas no múltiples sin aviso, B-128 herramienta de ~1 µm,
T-20 cortar con K herramientas en una operación."""
import math
import sys
import time
from pathlib import Path

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import fuzz_b39 as fuzz  # noqa: E402

R, r = 14.0, 6.0
V_TORO = 2 * math.pi ** 2 * R * r ** 2


def ok(respuesta):
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def toros(solape):
    return geo.toroide(R, r, (0, 0, 10)), geo.toroide(R, r, (40 - solape, 0, 10))


def cuerpo_unico(sesion):
    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    return cuerpos[0].forma


@pytest.mark.parametrize("solape", [1e-6, 1e-5, 1e-4])
def test_b125_unir_toros_casi_tangentes_no_pierde_uno(solape):
    a, b = toros(solape)
    resultado = geo.booleano(a, b, "unir")
    assert geo.volumen_exacto(resultado) == pytest.approx(2 * V_TORO, abs=1e-2)
    assert geo.es_valida(resultado)


@pytest.mark.parametrize("solape", [1e-6, 1e-5, 1e-4])
def test_b125_intersecar_toros_casi_tangentes_no_devuelve_uno_entero(solape):
    a, b = toros(solape)
    resultado = geo.booleano(a, b, "intersecar")
    assert geo.esta_vacia(resultado) or geo.volumen_exacto(resultado) < 1e-3


@pytest.mark.parametrize("solape", [1e-6, 1e-5, 1e-4])
def test_b125_cortar_toros_casi_tangentes_no_borra_el_objetivo(solape):
    a, b = toros(solape)
    resultado = geo.booleano(a, b, "cortar")
    # 1e-5 sale por el reintento B-spline: 2,5e-6 de más por la integración de esas caras, no material agregado
    assert geo.volumen_exacto(resultado) == pytest.approx(V_TORO, rel=1e-5)
    assert geo.es_valida(resultado)


def test_b125_solape_real_sigue_igual():
    a, b = toros(1e-3)
    assert geo.volumen_exacto(geo.booleano(a, b, "unir")) == pytest.approx(19897.1185, abs=1e-3)


@pytest.mark.parametrize("operacion", ["unir", "intersecar"])
def test_b125_pieza_adentro_que_sobresale_apenas_no_se_rechaza(operacion):
    """El borde del rango es legítimo cuando la pieza chica sí está adentro."""
    caja = geo.caja(40, 40, 40, (0, 0, 0))
    pieza = geo.caja(10, 10, 10, (10, 10, 30 + 1e-5))
    resultado = geo.booleano(caja, pieza, operacion)
    esperado = 64000 + 100 * 1e-5 if operacion == "unir" else 1000 - 100 * 1e-5
    assert geo.volumen_exacto(resultado) == pytest.approx(esperado, abs=1e-6)
    assert geo.es_valida(resultado)


@pytest.mark.parametrize("solape", [1e-6, 1e-5, 1e-4])
def test_b125_unir_todos_no_pierde_una_pieza(solape):
    """Mismo defecto en la operación general: con 1e-4 devolvía dos toros de tres, con el volumen dentro del rango."""
    formas = [geo.toroide(R, r, (i * (40 - solape), 0, 10)) for i in range(3)]
    resultado = geo.unir_todos(formas)
    assert geo.volumen_exacto(resultado) == pytest.approx(3 * V_TORO, abs=1e-2)
    assert geo.es_valida(resultado)


def test_b125_unir_todos_con_piezas_que_se_solapan_sigue_igual():
    formas = [geo.caja(10, 10, 10, (i * 5.0, 0, 0)) for i in range(4)]
    assert geo.volumen_exacto(geo.unir_todos(formas)) == pytest.approx(25 * 10 * 10, abs=1e-6)


def test_b125_caso_del_fuzzer_que_perdia_parte_de_la_herramienta():
    """`fuzz_b39` otra-1135, paso 2: GlueShift devolvía el objetivo intacto, válido y sin aristas nuevas, y la caja sobresale
    0,0764 mm³. Ahora suma lo que sobresale; queda una arista no manifold real en el contacto, con aviso."""
    _, u, herr = fuzz.generar("otra", 1135)
    for *_, h in herr[:2]:
        u = geo.booleano(u, h, "unir")
    h = herr[2][-1]
    sobresale = geo.volumen_exacto(geo._booleana(h, u, "cortar"))
    assert sobresale == pytest.approx(0.0764, abs=1e-3)
    avisos = []
    resultado = geo.booleano(u, h, "unir", avisos)
    assert geo.volumen_exacto(resultado) - geo.volumen_exacto(u) == pytest.approx(sobresale, abs=1e-5)
    assert geo.es_valida(resultado) and rv.es_estanca(resultado)
    assert any("aristas compartidas" in a for a in avisos)


def _hueca():
    return geo.booleano(geo.caja(60, 40, 20, (-30, -20, 0)), geo.caja(54, 34, 20, (-27, -17, 3)), "cortar")


@pytest.mark.parametrize("radio,centro,comun", [(3.49, (1e-6, -19.999999, 10.000001), 86.52),
                                                (2.0, (-19.999999, -19.999999, 10.000001), 16.755)])
def test_b125_esfera_centrada_en_la_cara_de_una_pared(radio, centro, comun):
    """Cortar quitaba la esfera entera (178 mm³ en vez de 86,52) e intersecar daba vacío, los dos dentro del rango."""
    hueca, esfera = _hueca(), geo.esfera(radio, centro)
    v = geo.volumen_exacto(hueca)
    corte = geo.booleano(hueca, esfera, "cortar")
    assert v - geo.volumen_exacto(corte) == pytest.approx(comun, abs=1e-2)
    assert geo.es_valida(corte)
    assert geo.volumen_exacto(geo.booleano(_hueca(), geo.esfera(radio, centro), "intersecar")) == pytest.approx(comun, abs=1e-2)


def test_b125_esfera_casi_tangente_no_se_queda_sin_cortar():
    """Quitaba 0 de 122,5 mm³. Hoy quita 103,8: el resto sigue abierto en docs/seguimiento (B-144)."""
    hueca = _hueca()
    v = geo.volumen_exacto(hueca)
    corte = geo.booleano(hueca, geo.esfera(4.0, (18.537165, 20.0001, 10.0001)), "cortar")
    assert v - geo.volumen_exacto(corte) > 100
    assert geo.es_valida(corte)


def test_b125_las_muestras_no_se_confunden_con_una_entrada_invertida():
    """El kernel puede dejar invertida la orientación de una entrada: adentro y afuera se cambiarían."""
    grande, adentro, lejos = geo.caja(40, 40, 40), geo.caja(4, 4, 4, (10, 10, 10)), geo.caja(4, 4, 4, (100, 0, 0))
    assert geo._parte_afuera(adentro.Reversed(), grande) == 0
    assert geo._parte_afuera(lejos.Reversed(), grande) == 1
    assert geo._parte_afuera(adentro, grande.Reversed()) == 0


def test_b125_por_la_api_avisa_que_quedaron_partidos():
    s = api.Sesion()
    ok(api.llamar(s, "create_torus", {"major_radius": R, "minor_radius": r, "x": 0, "z": 10, "name": "A"}))
    ok(api.llamar(s, "create_torus", {"major_radius": R, "minor_radius": r, "x": 39.9999, "z": 10, "name": "B"}))
    respuesta = api.llamar(s, "boolean_operation", {"target": "A", "tools": ["B"], "operation": "join"})
    ok(respuesta)
    forma = cuerpo_unico(s)
    assert geo.volumen_exacto(forma) == pytest.approx(2 * V_TORO, abs=1e-2)
    assert geo.es_valida(forma)
    assert any("partido" in a for a in respuesta.get("avisos") or [])


def _hueca_contra_agujeros(s, operacion):
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "name": "A"}))
    ok(api.llamar(s, "shell", {"body": "A", "faces": ">Z", "thickness": 3}))
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "x": 20, "name": "B"}))
    puntos = [[x, y] for x in (8, 20, 32) for y in (-12, 0, 12)]
    ok(api.llamar(s, "create_hole", {"face": ">Z", "body": "B", "diameter": 6, "through_all": True, "points": puntos}))
    return api.llamar(s, "boolean_operation", {"target": "A", "tools": ["B"], "operation": operacion})


def test_b126_intersecar_con_agujero_tangente_a_la_pared_avisa():
    """Tres agujeros de r = 3 en x = 20 quedan tangentes a la pared interior x = 17: el material se pellizca en una
    línea. La geometría es correcta (el volumen cierra), así que se devuelve, pero avisando."""
    s = api.Sesion()
    respuesta = _hueca_contra_agujeros(s, "intersect")
    ok(respuesta)
    forma = cuerpo_unico(s)
    assert geo.volumen_exacto(forma) == pytest.approx(5071.301, abs=1e-3)
    assert geo._aristas_defectuosas(forma) == (0, 3)
    assert geo.es_valida(forma)
    assert any("3 aristas compartidas" in a for a in respuesta.get("avisos") or [])


def test_b126_sin_tangencia_no_avisa():
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "name": "A"}))
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "x": 20, "name": "B"}))
    respuesta = api.llamar(s, "boolean_operation", {"target": "A", "tools": ["B"], "operation": "intersect"})
    ok(respuesta)
    assert geo.volumen_exacto(cuerpo_unico(s)) == pytest.approx(16000, abs=1e-6)
    assert not respuesta.get("avisos")


def _diminuta(lado, x, y, z):
    return geo.caja(lado, lado, lado, (x - lado / 2, y - lado / 2, z))


@pytest.mark.parametrize("lado", [1e-6, 3e-7, 5e-6])
@pytest.mark.parametrize("donde", [(20, 20, 20), (20, 0, 20), (20, 20, 0), (5, 5, 20)])
@pytest.mark.parametrize("operacion", ["cortar", "unir"])
def test_b128_herramienta_diminuta_no_cambia_nada_y_avisa(lado, donde, operacion):
    caja = geo.caja(40, 40, 40, (-20, -20, 0))
    avisos = []
    resultado = geo.booleano(caja, _diminuta(lado, *donde), operacion, avisos)
    assert geo.volumen_exacto(resultado) == pytest.approx(64000, abs=1e-6)
    assert len(geo.caras(resultado)) == 6 and len(geo.solidos(resultado)) == 1
    assert geo.es_valida(resultado)
    assert rv._autointersecciones(resultado, 1)[0] == 0
    assert any("no cambió nada" in a for a in avisos)


def test_b128_unir_diminuta_como_objetivo_devuelve_la_otra():
    caja = geo.caja(40, 40, 40, (-20, -20, 0))
    assert geo.booleano(_diminuta(1e-6, 5, 5, 20), caja, "unir") is caja


@pytest.mark.parametrize("donde", [(20, 20, 20), (20, 0, 20), (5, 5, 20)])
def test_b128_intersecar_con_una_diminuta_da_vacio(donde):
    """Con 3e-7 adentro devolvía un sólido con 28 autointersecciones; en (20, 0, 20) el kernel fallaba."""
    assert geo.esta_vacia(geo.booleano(geo.caja(40, 40, 40, (-20, -20, 0)), _diminuta(3e-7, *donde), "intersecar"))


def test_b128_desde_1e5_el_rasgo_se_conserva():
    """Lo que hoy da un resultado sano sigue igual: 1e-5 corta de verdad (hoyuelo de 10 caras)."""
    caja = geo.caja(40, 40, 40, (-20, -20, 0))
    assert len(geo.caras(geo.booleano(caja, _diminuta(1e-5, 20, 20, 20), "cortar"))) == 10


def test_b128_por_la_api_avisa():
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 40, "name": "A"}))
    ok(api.llamar(s, "create_box", {"length": 1e-6, "width": 1e-6, "height": 1e-6, "x": 20, "y": 20, "z": 20, "name": "B"}))
    respuesta = api.llamar(s, "boolean_operation", {"target": "A", "tools": ["B"], "operation": "cut"})
    ok(respuesta)
    revision = ok(api.llamar(s, "check_geometry", {}))["bodies"][0]
    assert revision["self_intersections"] == 0 and revision["valid"]
    assert any("no cambió nada" in a for a in respuesta.get("avisos") or [])


def _barra_con_ranuras(k):
    s = api.Sesion()
    paso, ancho = 10.0, 2.0
    ok(api.llamar(s, "create_box", {"length": (k + 1) * paso, "width": 40, "height": 10, "name": "A", "anchor": "corner"}))
    for i in range(k):
        ok(api.llamar(s, "create_box", {"length": ancho, "width": 60, "height": 20, "x": (i + 1) * paso - ancho / 2,
                                        "y": -10, "z": -5, "name": f"R{i}", "anchor": "corner"}))
    return s, (k + 1) * paso * 400 - k * ancho * 400


def _partes(k):
    """{id del cuerpo: (volumen, caja)} tras cortar la barra con sus K ranuras."""
    s, esperado = _barra_con_ranuras(k)
    ok(api.llamar(s, "boolean_operation", {"target": "A", "tools": [f"R{i}" for i in range(k)], "operation": "cut"}))
    cuerpos = s.doc.estado_final.cuerpos
    assert sum(geo.volumen_exacto(c.forma) for c in cuerpos.values()) == pytest.approx(esperado, abs=1e-6)
    assert all(geo.es_valida(c.forma) for c in cuerpos.values())
    return {i: (round(geo.volumen_exacto(c.forma), 6), geo.caja_envolvente(c.forma)) for i, c in cuerpos.items()}


def test_t20_cortar_con_varias_da_lo_mismo_que_de_a_una(monkeypatch):
    """Mismos cuerpos, con los mismos ids: las recetas guardadas siguen apuntando a la misma parte."""
    juntas = _partes(5)
    assert len(juntas) == 6

    def falla(*a, **k):
        raise geo.ErrorGeometria("no")
    monkeypatch.setattr(geo, "cortar_varias", falla)
    assert _partes(5) == juntas


def test_t20_tiempo_lineal_una_sola_booleana(monkeypatch):
    """40 herramientas: una pasada con todas, no 40 sobre un resultado cada vez más grande (eso crecía como K²)."""
    pasadas = []
    original = geo._booleana_verificada

    def contar(*a, **k):
        pasadas.append(k.get("varias", False))
        return original(*a, **k)
    monkeypatch.setattr(geo, "_booleana_verificada", contar)
    s, esperado = _barra_con_ranuras(40)
    t = time.perf_counter()
    ok(api.llamar(s, "boolean_operation", {"target": "A", "tools": [f"R{i}" for i in range(40)], "operation": "cut"}))
    assert sum(pasadas) == 1
    assert time.perf_counter() - t < 5
    assert sum(geo.volumen_exacto(c.forma) for c in s.doc.estado_final.cuerpos.values()) == pytest.approx(esperado, abs=1e-6)


def test_t20_herramientas_que_se_solapan_van_de_a_una():
    """Solapadas no se puede sumar lo que quita cada una, así que no hay con qué comprobar la pasada conjunta."""
    with pytest.raises(geo.ErrorGeometria):
        geo.cortar_varias(geo.caja(40, 40, 10), [geo.caja(20, 60, 20, (5, -10, -5)), geo.caja(20, 60, 20, (15, -10, -5))])
    s = api.Sesion()
    ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 10, "name": "A", "anchor": "corner"}))
    for nombre, x in (("B", 5), ("C", 15)):
        ok(api.llamar(s, "create_box", {"length": 20, "width": 60, "height": 20, "x": x, "y": -10, "z": -5, "name": nombre,
                                        "anchor": "corner"}))
    ok(api.llamar(s, "boolean_operation", {"target": "A", "tools": ["B", "C"], "operation": "cut"}))
    assert sum(geo.volumen_exacto(c.forma) for c in s.doc.estado_final.cuerpos.values()) == pytest.approx(2 * 5 * 40 * 10, abs=1e-6)


def test_t20_si_la_pasada_conjunta_saltea_una_herramienta_se_rechaza(monkeypatch):
    """Sin esta comprobación salteaba herramientas sin salirse del rango de volumen (1433 mm³ en 300 casos al azar)."""
    hueca = _hueca()
    original = geo._booleana_verificada
    monkeypatch.setattr(geo, "_booleana_verificada", lambda *a, **k: hueca if k.get("varias") else original(*a, **k))
    with pytest.raises(geo.ErrorGeometria):
        geo.cortar_varias(hueca, [geo.caja(4, 60, 30, (-10, -30, -5)), geo.caja(4, 60, 30, (10, -30, -5))])


def test_t20_avisa_la_herramienta_que_no_toca():
    s, _ = _barra_con_ranuras(2)
    ok(api.llamar(s, "create_box", {"length": 2, "width": 2, "height": 2, "x": 500, "name": "Lejos"}))
    respuesta = api.llamar(s, "boolean_operation", {"target": "A", "tools": ["R0", "R1", "Lejos"], "operation": "cut"})
    ok(respuesta)
    assert any("Lejos no toca a A: no le cortó nada" in a for a in respuesta.get("avisos") or [])


def test_t20_si_el_kernel_no_puede_junto_corta_de_a_una(monkeypatch):
    def falla(*a, **k):
        raise geo.ErrorGeometria("no")
    monkeypatch.setattr(geo, "cortar_varias", falla)
    s, esperado = _barra_con_ranuras(3)
    ok(api.llamar(s, "boolean_operation", {"target": "A", "tools": ["R0", "R1", "R2"], "operation": "cut"}))
    assert sum(geo.volumen_exacto(c.forma) for c in s.doc.estado_final.cuerpos.values()) == pytest.approx(esperado, abs=1e-6)
