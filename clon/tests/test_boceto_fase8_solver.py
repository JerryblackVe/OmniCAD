# -*- coding: utf-8 -*-
"""SC4 + BOC-27: solver constructivo (coincidencias y horizontales/verticales por construcción) y boceto grande."""
import time

import numpy as np

from omnicad.restricciones import solver as S
from omnicad.restricciones.boceto import Boceto


def _cadena(n):
    """n líneas en escalera: coincidentes, horizontal/vertical alternadas y cota en las horizontales (gdl = n/2)."""
    b, valores, x, y, previo = Boceto(), {}, 0.0, 0.0, None
    for i in range(n):
        a = b.agregar_punto(x, y)
        if i % 2 == 0:
            x += 10.0 + i % 3
        else:
            y += 7.0 + i % 2
        c = b.agregar_punto(x + 0.3, y - 0.2)
        ln = b.agregar_linea(a, c)
        b.agregar_restriccion("fijo" if previo is None else "coincidente", [a] if previo is None else [previo, a])
        b.agregar_restriccion("horizontal" if i % 2 == 0 else "vertical", [ln])
        if i % 2 == 0:
            valores[b.agregar_cota("distancia", [ln], "10")] = 10.0
        previo = c
    return b, valores, previo


def _viejo(b, valores):
    """Camino viejo (sin fusionar coordenadas), grupo por grupo: (gdl, posiciones)."""
    gdl = 0
    for g in S._grupos(b):
        sis = S._Sistema(b, valores, g)
        x, _err, _J, rango = S._resolver_grupo(sis, None)
        sis.escribir(x)
        gdl += len(sis.x0) - rango
    return gdl, {p: b.coords(p) for p in b.puntos}


def _rectangulo_con_circulo():
    b = Boceto()
    lineas = b.agregar_rectangulo((0.3, -0.2), (40.0, 25.0))
    esquina = b.puntos[b.curvas[lineas[1]].p2]
    esquina.x, esquina.y = esquina.x + 0.4, esquina.y - 0.3     # fuera de escuadra: el solver tiene que moverla
    c = b.agregar_circulo(b.agregar_punto(20, 12), 5.0)
    valores = {b.agregar_cota("distancia", [lineas[0]], "42"): 42.0,
               b.agregar_cota("distancia", [lineas[1]], "27"): 27.0}
    b.agregar_restriccion("fijo", [b.curvas[lineas[0]].p1])
    b.agregar_restriccion("tangente", [lineas[0], c])
    return b, valores


def test_misma_solucion_y_gdl_que_el_camino_viejo():
    for armar in (lambda: _cadena(30)[:2], _rectangulo_con_circulo):
        b, valores = armar()
        viejo = b.copia()
        gdl_viejo, pos_viejo = _viejo(viejo, valores)
        r = S.resolver(b, valores)
        assert r.ok and r.gdl == gdl_viejo
        determinados = [p for p in b.puntos if p in r.determinadas]
        assert determinados, "la prueba necesita puntos determinados (su posición es única)"
        for p in determinados:
            assert np.allclose(b.coords(p), pos_viejo[p], atol=1e-6)


def test_cadena_grande_gdl_y_determinadas():
    b, valores, fin = _cadena(60)
    r = S.resolver(b, valores)
    assert r.ok and r.gdl == 30 and r.residuo_max < 1e-9
    assert fin not in r.determinadas                      # la última vertical no tiene cota: su extremo se mueve en y


def test_arrastre_mueve_lo_minimo():
    b, valores, fin = _cadena(60)
    previo = S.resolver(b, valores)
    antes = {p: b.coords(p) for p in b.puntos}
    p = b.puntos[fin]
    p.x, p.y = p.x + 1.0, p.y + 0.5                       # x está determinada; y la absorbe la última vertical
    r = S.resolver(b, valores, fin, previo)
    assert r.ok and r.gdl == previo.gdl
    assert np.allclose(b.coords(fin), (antes[fin][0], antes[fin][1] + 0.5), atol=1e-6)
    movidos = [q for q in b.puntos if q != fin and np.hypot(*np.subtract(b.coords(q), antes[q])) > 1e-6]
    assert movidos == []


def test_400_lineas_arrastre_y_soltado_rapidos():
    b, valores, fin = _cadena(400)
    previo = S.resolver(b, valores)
    assert previo.ok and previo.gdl == 200
    p = b.puntos[fin]
    p.x, p.y = p.x + 1.0, p.y + 0.5
    t = time.perf_counter()
    r = S.resolver(b, valores, fin, previo)
    arrastre = time.perf_counter() - t
    t = time.perf_counter()
    soltado = S.resolver(b, valores)
    soltar = time.perf_counter() - t
    assert r.ok and soltado.ok and soltado.gdl == 200
    assert arrastre < 1.0, f"arrastre con 400 líneas: {arrastre:.2f} s"   # meta 0,3 s; holgado para no ser frágil
    assert soltar < 2.0, f"soltar con 400 líneas: {soltar:.2f} s"


def test_arrastrar_punto_fusionado_sin_otros_terminos_no_salta():
    b = Boceto()
    a, c = b.agregar_punto(0, 0), b.agregar_punto(4, 2)
    b.agregar_restriccion("coincidente", [a, c])
    previo = S.resolver(b, {})
    assert b.coords(a) == b.coords(c)
    b.puntos[a].x, b.puntos[a].y = 10.0, -3.0
    assert S.resolver(b, {}, a, previo).ok
    assert b.coords(a) == b.coords(c) == (10.0, -3.0)


def test_coincidencia_entre_dos_fijos_distintos_sigue_en_conflicto():
    b = Boceto()
    a, c = b.agregar_punto(0, 0), b.agregar_punto(5, 0)
    b.agregar_restriccion("fijo", [a])
    b.agregar_restriccion("fijo", [c])
    b.agregar_restriccion("coincidente", [a, c])
    assert not S.resolver(b, {}).ok
