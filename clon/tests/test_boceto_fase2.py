import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo.perfiles import proyectar_forma
from omnicad.restricciones import Boceto, grados_de_libertad


def test_b99_proyectar_cilindro_no_duplica_circulos():
    b = Boceto()
    primitivas, puntos = proyectar_forma(g.cilindro(4, 10, (3, 5, -2)), g.Plano("XY"))
    assert sum(p[0] == "circulo" for p in primitivas) == 2

    ids = b.agregar_proyeccion(primitivas, puntos)

    circulos = [c for c in b.curvas.values() if c.tipo == "circulo"]
    assert len(circulos) == 1
    assert ids == [circulos[0].id]
    assert b.coords(circulos[0].centro) == pytest.approx((3, 5))
    assert circulos[0].radio == pytest.approx(4)
    assert circulos[0].proyectada
    assert grados_de_libertad(b) == 0


@pytest.mark.parametrize("centro,radio", [((3, 5), 6), ((15, 5), 4)])
def test_b99_proyeccion_conserva_circulos_distintos_y_no_repite_existentes(centro, radio):
    b = Boceto()
    primeras, _ = proyectar_forma(g.cilindro(4, 10, (3, 5, -2)), g.Plano("XY"))
    otras, _ = proyectar_forma(g.cilindro(radio, 10, (*centro, 2)), g.Plano("XY"))
    ids = b.agregar_proyeccion(primeras + otras)

    assert len(ids) == len(b.curvas) == 2
    assert b.geometria() == [("circulo", ids[0], pytest.approx((3, 5)), pytest.approx(4)),
                            ("circulo", ids[1], pytest.approx(centro), pytest.approx(radio))]
    assert b.agregar_proyeccion(primeras + otras) == []
    assert len(b.curvas) == 2


def test_b99_proyectar_caja_sigue_deduplicando_lineas():
    b = Boceto()
    primitivas, puntos = proyectar_forma(g.caja(10, 20, 5), g.Plano("XY"))
    ids = b.agregar_proyeccion(primitivas, puntos)

    assert len(ids) == len(b.curvas) == 4
    assert all(c.tipo == "linea" and c.proyectada for c in b.curvas.values())
    assert sorted(b.medir_cota("distancia", [i]) for i in ids) == pytest.approx([10, 10, 20, 20])
    assert b.agregar_proyeccion(primitivas, puntos) == []
    assert grados_de_libertad(b) == 0


@pytest.mark.parametrize("distancia", [5, 6, 5 - 1e-10])
def test_b98_desfase_interior_rechaza_segmentos_colapsados_o_invertidos(distancia):
    from omnicad.restricciones import ErrorBoceto

    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (20, 10))
    assert sorted(b.medir_cota("distancia", [i]) for i in lineas) == pytest.approx([10, 10, 20, 20])
    antes = b.a_dict()

    with pytest.raises(ErrorBoceto, match="segmento.*(cero|invierte)"):
        b.desfase(lineas[0], distancia, invertir=True)

    assert b.a_dict() == antes


@pytest.mark.parametrize("distancia,caja,largos", [
    (-4, (4, 4, 16, 6), [2, 2, 12, 12]),
    (3, (-3, -3, 23, 13), [16, 16, 26, 26]),
])
def test_b98_desfase_valido_conserva_dimensiones(distancia, caja, largos):
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (20, 10))

    nuevos = b.desfase(lineas[0], abs(distancia), invertir=distancia < 0)

    assert len(nuevos) == 4
    assert sorted(b.medir_cota("distancia", [i]) for i in nuevos) == pytest.approx(largos)
    puntos = [b.coords(p) for p in b.puntos_de(nuevos)]
    assert (min(x for x, y in puntos), min(y for x, y in puntos),
            max(x for x, y in puntos), max(y for x, y in puntos)) == pytest.approx(caja)


@pytest.mark.parametrize("distancia", [-5, -6])
def test_b98_api_desfase_invalido_devuelve_error_y_conserva_boceto(distancia):
    from omnicad import api

    sesion = api.Sesion()
    assert api.llamar(sesion, "create_sketch", {})["ok"]
    rectangulo = api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 10})
    assert rectangulo["ok"], rectangulo
    antes = api.llamar(sesion, "get_sketch", {})
    assert antes["ok"]
    assert antes["result"]["profiles"][0]["area"] == pytest.approx(200)
    entidad = rectangulo["result"]["entities"][0]["id"]

    resultado = api.llamar(sesion, "offset_sketch_curves", {"entity": entidad, "distance": distancia})

    assert resultado["ok"] is False, resultado
    assert resultado["error_kind"] == "INVALID_GEOMETRY"
    assert "segmento" in resultado["mensaje"]
    assert api.llamar(sesion, "get_sketch", {}) == antes


@pytest.mark.parametrize("extremo", ["inicio", "fin"])
@pytest.mark.parametrize("arco_primero", [True, False])
def test_b96_fusion_g2_conserva_radio_y_curvatura_del_arco(extremo, arco_primero):
    import math

    from omnicad.restricciones import resolver
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    b = Boceto()
    arco = b.agregar_arco_centro((0, 0), (10, 0), (0, 10))
    linea = b.agregar_linea((20, 15), (30, 15))
    union = b.coords(getattr(b.curvas[arco], extremo))
    argumentos = (arco, union, linea, (20, 15)) if arco_primero else (linea, (20, 15), arco, union)
    fusion = b.curva_fusion(*argumentos, "G2")

    assert resolver(b).ok

    prim = b.primitivas(fusion)[0]
    parametro = dominio(prim)[0 if arco_primero else 1]
    _, d1, d2 = evaluar_primitiva(prim, parametro, 2)
    curvatura = (d1[0] * d2[1] - d1[1] * d2[0]) / math.hypot(*d1) ** 3
    signo = (1 if extremo == "fin" else -1) * (1 if arco_primero else -1)
    assert curvatura == pytest.approx(signo / 10, abs=1e-3)
    assert b.radio(arco) == pytest.approx(10, abs=1e-6)


def test_b96_fusion_g2_entre_lineas_conserva_geometria_y_curvatura_cero():
    import math

    from omnicad.restricciones import resolver
    from omnicad.restricciones.boceto import dominio, evaluar_primitiva

    b = Boceto()
    primera = b.agregar_linea((0, 0), (10, 0))
    segunda = b.agregar_linea((20, 5), (30, 5))
    puntos = {pid: b.coords(pid) for pid in b.puntos}
    fusion = b.curva_fusion(primera, (10, 0), segunda, (20, 5), "G2")

    assert resolver(b).ok

    prim = b.primitivas(fusion)[0]
    for parametro in dominio(prim)[:2]:
        _, d1, d2 = evaluar_primitiva(prim, parametro, 2)
        curvatura = (d1[0] * d2[1] - d1[1] * d2[0]) / math.hypot(*d1) ** 3
        assert curvatura == pytest.approx(0, abs=1e-9)
    for pid, coordenadas in puntos.items():
        assert b.coords(pid) == pytest.approx(coordenadas, abs=1e-6)


@pytest.mark.parametrize("extremo", ["inicio", "fin"])
def test_b100_simetria_de_arcos_refleja_extremos_invertidos_al_arrastrar(extremo):
    import math

    from omnicad.restricciones import resolver

    b = Boceto()
    primero = b.agregar_arco_centro((10, 0), (13, 0), (10, 3))
    segundo = b.agregar_arco_centro((0, 10), (3, 10), (0, 13))
    eje = b.agregar_linea((-20, -20), (20, 20), construccion=True)
    assert grados_de_libertad(b) == 14

    b.agregar_restriccion("simetrica", [primero, segundo, eje])
    assert grados_de_libertad(b) == 9
    resultado = resolver(b)
    assert resultado.ok and resultado.gdl == 9

    a, c = b.curvas[primero], b.curvas[segundo]
    arrastrado = getattr(a, extremo)
    punto = b.puntos[arrastrado]
    destino = (punto.x + 2, punto.y + 1)
    punto.x, punto.y = destino
    resultado = resolver(b, arrastrado=arrastrado)
    assert resultado.ok and resultado.gdl == 9
    assert b.coords(arrastrado) == pytest.approx(destino, abs=1e-6)

    (ox, oy), (ex, ey) = b._extremos_linea(eje)
    dx, dy = ex - ox, ey - oy
    for pa, pc in [(a.centro, c.centro), (a.inicio, c.fin), (a.fin, c.inicio)]:
        x, y = b.coords(pa)
        proyeccion = ((x - ox) * dx + (y - oy) * dy) / (dx * dx + dy * dy)
        reflejo = (2 * (ox + proyeccion * dx) - x, 2 * (oy + proyeccion * dy) - y)
        assert math.dist(b.coords(pc), reflejo) < 1e-6
    assert math.dist(b.coords(c.inicio), b.coords(c.fin)) > 1


@pytest.mark.parametrize("herramienta,argumentos,gdl_iniciales", [
    ("draw_point", {"x": 0, "y": 5}, 2),
    ("draw_arc", {"center_x": 0, "center_y": 10, "start_x": 0, "start_y": 5,
                  "sweep_angle": 90}, 5),
    ("draw_conic", {"start_x": 3, "start_y": 0, "vertex_x": 7, "vertex_y": 8,
                    "end_x": 12, "end_y": 4}, 6),
])
def test_b102_auto_restringir_cierra_distancias_cero(herramienta, argumentos, gdl_iniciales):
    from omnicad import api

    sesion = api.Sesion()
    assert api.llamar(sesion, "create_sketch", {})["ok"]
    dibujo = api.llamar(sesion, herramienta, argumentos)
    assert dibujo["ok"], dibujo
    assert dibujo["result"]["dof"] == gdl_iniciales
    antes = api.llamar(sesion, "get_sketch", {})
    assert antes["ok"], antes
    coordenadas = {p["id"]: (p["x"], p["y"]) for p in antes["result"]["points"]}

    resultado = api.llamar(sesion, "auto_constrain", {})

    assert resultado["ok"], resultado
    assert resultado["result"]["dof"] == 0
    despues = api.llamar(sesion, "get_sketch", {})
    assert despues["ok"], despues
    assert despues["result"]["dof"] == 0
    assert any(c["value"] == 0 for c in despues["result"]["dimensions"])
    for punto in despues["result"]["points"]:
        if punto["id"] in coordenadas:
            assert (punto["x"], punto["y"]) == pytest.approx(coordenadas[punto["id"]], abs=1e-6)


@pytest.mark.parametrize("largo", [2e4, 1e5, 1e6])
def test_b101_angulo_en_lineas_grandes_converge_y_resta_un_gdl(largo):
    from omnicad.restricciones import resolver

    b = Boceto()
    primera = b.agregar_linea((0, 0), (largo, 0))
    segunda = b.agregar_linea((0, largo), (largo, 2 * largo))
    cota = b.agregar_cota("angulo", [primera, segunda], "60")

    resultado = resolver(b, {cota: 60})

    assert resultado.ok, resultado.descripcion()
    assert resultado.gdl == grados_de_libertad(b, {cota: 60}) == 7
    assert b.medir_cota("angulo", [primera, segunda]) == pytest.approx(60, abs=1e-6)


@pytest.mark.parametrize("cantidad", [160, 300])
def test_b101_arrastre_de_cadena_rigida_converge(cantidad):
    from time import perf_counter

    from omnicad.restricciones import resolver

    inicio = perf_counter()
    b = Boceto()
    punto = b.agregar_punto(0, 0)
    lineas = []
    for i in range(cantidad):
        extremo = b.agregar_punto(10 * ((i + 2) // 2), 10 * ((i + 1) // 2))
        linea = b.agregar_linea(punto, extremo)
        b.agregar_restriccion("horizontal" if i % 2 == 0 else "vertical", [linea])
        if lineas:
            b.agregar_restriccion("igual", [lineas[-1], linea])
        lineas.append(linea)
        punto = extremo
    cota = b.agregar_cota("distancia", [lineas[0]], "10")
    previo = resolver(b, {cota: 10})
    assert previo.ok and previo.gdl == 2
    destino = (b.puntos[punto].x + 50, b.puntos[punto].y)
    b.puntos[punto].x, b.puntos[punto].y = destino

    resultado = resolver(b, {cota: 10}, arrastrado=punto, previo=previo)

    assert resultado.ok, resultado.descripcion()
    assert resultado.gdl == 2
    assert b.coords(punto) == pytest.approx(destino, abs=1e-3)
    assert resultado.residuo_max / 10 < 1e-8
    for i, linea in enumerate(lineas):
        a, c = b._extremos_linea(linea)
        assert abs(a[1 if i % 2 == 0 else 0] - c[1 if i % 2 == 0 else 0]) / 10 < 1e-8
        assert b.medir_cota("distancia", [linea]) == pytest.approx(10, abs=1e-7)
    assert perf_counter() - inicio < 60


def _b103_grilla(cantidad):
    b = Boceto()
    puntos = {}
    for i in range(cantidad):
        x, y = 10 * ((i // 2) % 20), 10 * ((i // 2) // 20)
        extremos = [(x, y), (x + 10, y) if i % 2 == 0 else (x, y + 10)]
        for p in extremos:
            if p not in puntos:
                puntos[p] = b.agregar_punto(*p)
        b.agregar_linea(*(puntos[p] for p in extremos))
    return b


@pytest.mark.parametrize("cantidad", [120, 260, 440])
def test_b103_auto_restringir_rendimiento(cantidad):
    from time import perf_counter

    from omnicad.restricciones import auto_restringir

    b = _b103_grilla(cantidad)
    assert len(b.curvas) == cantidad
    assert grados_de_libertad(b) == 2 * len(b.puntos)
    coordenadas = {pid: b.coords(pid) for pid in b.puntos}
    inicio = perf_counter()
    agregado = auto_restringir(b)
    segundos = perf_counter() - inicio
    print(f"B-103 {cantidad} entidades: {segundos:.3f} s; {len(agregado)} agregados", flush=True)
    assert segundos < 30
    valores = {k.id: float(k.expresion) for k in b.cotas.values()}
    assert grados_de_libertad(b, valores) == 0
    assert len(b.curvas) == cantidad
    assert {pid: b.coords(pid) for pid in coordenadas} == coordenadas


def test_b103_auto_restringir_tope_sin_modificar_boceto():
    from omnicad.restricciones import ErrorBoceto, auto_restringir

    b = _b103_grilla(501)
    for c in b.curvas.values():
        b.agregar_restriccion("fijo", [c.id])
    antes = b.a_dict()
    with pytest.raises(ErrorBoceto, match=r"501.*500.*(simplific|divid)"):
        auto_restringir(b)
    assert b.a_dict() == antes


@pytest.mark.parametrize("desplazamiento,acotado", [(0, False), (3, False), (0, True)])
def test_b103_auto_restringir_conserva_candidatos_del_calculo_completo(monkeypatch, desplazamiento, acotado):
    from omnicad.restricciones import solver

    b = Boceto()
    for i in range(6):
        b.agregar_rectangulo((30 * i + desplazamiento, desplazamiento),
                            (30 * i + 10 + desplazamiento, 10 + desplazamiento))
    for i in range(3):
        b.agregar_circulo((30 * i, 30), 5)
        b.agregar_linea((30 * i, 50), (30 * i + 6, 58))
    assert len(b.curvas) == 30
    valores = {}
    if acotado:
        linea = next(iter(b.curvas))
        b.agregar_restriccion("fijo", [b.curvas[linea].p1])
        valores[b.agregar_cota("distancia", [linea], "ancho")] = 10
    original = Boceto.desde_dict(b.a_dict())
    agregado = solver.auto_restringir(b, valores)

    # Oráculo anterior: recalcular el rango de TODO el boceto después de cada candidato.
    monkeypatch.setattr(solver, "_GradosAuto",
                        lambda boceto, valores: lambda ident=None: solver.grados_de_libertad(boceto, valores),
                        raising=False)
    esperado = solver.auto_restringir(original, valores)

    assert agregado == esperado
    assert {(r.tipo, tuple(r.entidades)) for r in b.restricciones.values()} == {
        (r.tipo, tuple(r.entidades)) for r in original.restricciones.values()}
    assert {(k.tipo, tuple(k.entidades), k.expresion) for k in b.cotas.values()} == {
        (k.tipo, tuple(k.entidades), k.expresion) for k in original.cotas.values()}
    valores.update({k.id: float(k.expresion) for k in b.cotas.values() if k.id not in valores})
    assert grados_de_libertad(b, valores) == 0


def test_b103_auto_restringir_440_lineas_aisladas():
    from time import perf_counter

    from omnicad.restricciones import auto_restringir

    b = Boceto()
    for i in range(440):
        x, y = 20 * (i % 20), 20 * (i // 20)
        b.agregar_linea((x, y), (x + 10, y))
    inicio = perf_counter()
    agregado = auto_restringir(b)
    segundos = perf_counter() - inicio
    print(f"B-103 aisladas 440 entidades: {segundos:.3f} s; {len(agregado)} agregados", flush=True)
    assert segundos < 30
    assert len(agregado) == 1759
    assert grados_de_libertad(b, {k.id: float(k.expresion) for k in b.cotas.values()}) == 0


def test_b103_api_tope_de_puntos_es_error_atomico():
    from omnicad import api

    sesion = api.Sesion()
    resultado = api.llamar(sesion, "sketch_from_spec", {
        "entities": [{"type": "point", "at": [i, 0]} for i in range(501)]})
    assert resultado["ok"], resultado
    antes = sesion.doc.a_dict()

    resultado = api.llamar(sesion, "auto_constrain", {})

    assert resultado["ok"] is False, resultado
    assert resultado["error_kind"] == "INVALID_GEOMETRY"
    assert "501" in resultado["mensaje"] and "500" in resultado["mensaje"]
    assert "dividí" in resultado["mensaje"]
    assert sesion.doc.a_dict() == antes


def test_b103_auto_restringir_admite_el_tope_exacto():
    from omnicad.restricciones import auto_restringir

    b = Boceto()
    for i in range(500):
        p = b.agregar_punto(i, 0)
        b.agregar_restriccion("fijo", [p])
    assert auto_restringir(b) == []
    assert grados_de_libertad(b) == 0
