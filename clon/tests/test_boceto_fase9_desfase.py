"""BOC-14b: desfase asociativo sobre la normal de splines y elipses (Offset de Fusion)."""
import json
import math

import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_resuelto
from omnicad.restricciones import Boceto, resolver
from omnicad.restricciones.boceto import evaluar_primitiva, mas_cercano


def _madre(b, tipo):
    if tipo == "elipse":
        return b.agregar_elipse((20, 20), (30, 20), 6, ejes=False)
    return b.agregar_spline([(10, 10), (20, 16), (30, 16), (40, 10)], modo=tipo)


def _mover_madre(b, madre):
    c = b.curvas[madre]
    pid = c.mayor if c.tipo == "elipse" else c.pts[1]
    b.puntos[pid].y += 3
    return pid


def _distancias(b, madre, copia):
    prim = b.primitivas(madre)[0]
    return [mas_cercano(prim, b.coords(p))[1] for p in b.curvas[copia].pts]


@pytest.mark.parametrize("tipo", ["ajuste", "control", "elipse"])
@pytest.mark.parametrize("invertir", [False, True])
def test_desfase_sigue_la_deformacion_de_la_madre(tipo, invertir):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1, invertir=invertir)
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    b.agregar_restriccion("fijo", [madre])
    pid = _mover_madre(b, madre)
    objetivo = b.coords(pid)
    valores = {k.id: 1 for k in b.cotas.values() if k.tipo == "desfase"}
    resultado = resolver(b, valores)
    assert resultado.ok, resultado.descripcion()
    assert b.coords(pid) == objetivo
    assert _distancias(b, madre, copia) == pytest.approx([1] * len(antes), abs=1e-3)
    assert max(math.dist(a, b.coords(p)) for a, p in zip(antes, b.curvas[copia].pts, strict=True)) > 0.1
    assert b.separacion(madre, copia) == pytest.approx(1, abs=1e-3)


@pytest.mark.parametrize("tipo", ["ajuste", "elipse"])
def test_cota_de_desfase_conserva_expresion_lado_y_asociacion_al_serializar(tipo):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1, expresion="separacion", invertir=True)
    cota, = [k for k in b.cotas.values() if k.tipo == "desfase"]
    assert cota.entidades == [madre, copia] and cota.expresion == "separacion"
    b = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))
    b.agregar_restriccion("fijo", [madre])
    _mover_madre(b, madre)
    assert resolver(b, {cota.id: 1.5}).ok
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    prim = b.primitivas(madre)[0]
    for pid in b.curvas[copia].pts:
        p = b.coords(pid)
        t, _, q = mas_cercano(prim, p)
        _, d = evaluar_primitiva(prim, t, 1)
        lado = (d[0] * (p[1] - q[1]) - d[1] * (p[0] - q[0])) / math.hypot(*d)
        assert lado == pytest.approx(1.5 if tipo == "elipse" else -1.5, abs=1e-3)


@pytest.mark.parametrize("tipo", ["ajuste", "elipse"])
@pytest.mark.parametrize("por_madre", [False, True])
@pytest.mark.parametrize("conservar_cota", [False, True])
def test_soltar_desfase_desliga_la_copia_sin_borrarla(tipo, por_madre, conservar_cota):
    b = Boceto()
    madre = _madre(b, tipo)
    copia, = b.desfase(madre, 1)
    b.agregar_restriccion("fijo", [madre])
    b.soltar_desfase(madre if por_madre else copia, conservar_cota=conservar_cota)
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    _mover_madre(b, madre)
    assert resolver(b, {k.id: 1 for k in b.cotas.values()}).ok
    assert [b.coords(p) for p in b.curvas[copia].pts] == antes
    assert max(abs(d - 1) for d in _distancias(b, madre, copia)) > 0.1
    assert len(b.cotas) == int(conservar_cota)
    assert all(k.referencia for k in b.cotas.values())


def test_separacion_de_curvas_libres_mide_la_distancia_a_la_madre():
    b = Boceto()
    madre = _madre(b, "elipse")
    copia, = b.desfase(madre, 1)
    assert b.separacion(madre, copia) == pytest.approx(1, abs=1e-3)


def test_distancia_a_elipse_busca_a_ambos_lados_del_cierre_periodico():
    b = Boceto()
    madre = _madre(b, "elipse")
    prim = b.primitivas(madre)[0]
    t = 2 * math.pi - 0.02
    q, d = evaluar_primitiva(prim, t, 1)
    n = math.hypot(*d)
    p = (q[0] + d[1] / n, q[1] - d[0] / n)
    parametro, distancia, _ = mas_cercano(prim, p)
    assert distancia == pytest.approx(1, abs=1e-6)
    assert parametro == pytest.approx(t, abs=1e-6)


@pytest.mark.parametrize("tipo", ["spline", "elipse"])
def test_api_parametro_arrastre_y_release_offset(tipo):
    sesion = api.Sesion()

    def llamar(nombre, **parametros):
        respuesta = api.llamar(sesion, nombre, parametros)
        assert respuesta["ok"], respuesta
        return respuesta["result"]

    llamar("create_sketch", plane="XY")
    llamar("create_parameter", name="separacion", expression="1 mm")
    dibujo = (llamar("draw_spline", points=[[10, 10], [20, 16], [30, 16], [40, 10]]) if tipo == "spline" else
              llamar("draw_ellipse", center_x=20, center_y=20, major_radius=10, minor_radius=6))
    madre = dibujo["entities"][0]["id"]
    copia = llamar("offset_sketch_curves", entity=madre, distance="separacion")["entities"][0]["id"]
    llamar("set_parameter", name="separacion", expression="1.5 mm")
    op = sesion.doc.operaciones[0]
    b = boceto_resuelto(sesion, op).boceto
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    c = b.curvas[madre]
    pid = c.mayor if tipo == "elipse" else c.pts[1]
    x, y = b.coords(pid)
    assert llamar("move_sketch_point", point=pid, x=x, y=y + 3)["reached"]
    b = boceto_resuelto(sesion, op).boceto
    assert _distancias(b, madre, copia) == pytest.approx([1.5] * len(b.curvas[copia].pts), abs=1e-3)
    llamar("release_offset", entity=copia)
    b = boceto_resuelto(sesion, op).boceto
    antes = [b.coords(p) for p in b.curvas[copia].pts]
    x, y = b.coords(pid)
    llamar("move_sketch_point", point=pid, x=x, y=y + 3)
    b = boceto_resuelto(sesion, op).boceto
    assert [b.coords(p) for p in b.curvas[copia].pts] == antes
