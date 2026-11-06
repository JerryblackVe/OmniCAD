"""SOL-10: Nervio y Red con ángulo de desmoldeo, dirección de extracción, inicio, empalme y «Extender curvas»."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _canal():
    """Canal en U de 40 x 20 x 20: paredes de 2 en x = 0..2 y 38..40, piso de 2 (z = 0..2), abierto arriba y de frente."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=20, height=20, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cid)
    return s, cid


def _linea(s, plano, offset, x1, y1, x2, y2):
    _ok(s, "create_construction_plane", plane=plano, offset=offset, name="Plano")
    b = _ok(s, "create_sketch", plane="Plano")["sketch"]["id"]
    _ok(s, "draw_line", sketch=b, start_x=x1, start_y=y1, end_x=x2, end_y=y2)
    return b


def _aumento(s, cid, antes):
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma)
    return geo.volumen(forma) - antes


@pytest.mark.parametrize("direccion", ["symmetric", "side1", "side2"])
def test_b213_nervio_en_el_borde_conserva_todo_el_espesor(direccion):
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=60, height=5,
              anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=5, width=60, height=50,
        anchor="corner", operation="join", target=cid)
    b = _linea(s, "XZ", 0, 35, 5, 5, 45)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, direction=direccion)
    assert _aumento(s, cid, 25500) == pytest.approx(1200)


def test_b213_nervio_invertido_sin_cara_da_error_y_conserva_el_cuerpo():
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=60, height=5, y=-30,
              anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=5, width=60, height=50, y=-30,
        anchor="corner", operation="join", target=cid)
    b = _linea(s, "XZ", 0, 35, 5, 5, 45)
    r = api.llamar(s, "create_rib", dict(sketch=b, thickness=2, target=cid, reverse=True))
    assert not r["ok"], r
    assert "no llega al cuerpo" in r["mensaje"].lower(), r
    assert _aumento(s, cid, 25500) == pytest.approx(0)


@pytest.mark.parametrize("extender", [False, True])
def test_b213_red_delante_de_la_boca_conserva_el_inicio(extender):
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=40, height=40,
              anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=36, width=38, height=36, x=2, z=2,
        anchor="corner", operation="cut", target=cid)
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XZ", 5, 10, 20, 30, 20)  # y = -5, delante de la boca
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=extender)
    aumento = _aumento(s, cid, antes)
    if extender:
        assert aumento > 1720
    else:
        assert aumento == pytest.approx(1720)  # 20 de largo · 43 hasta la pared · 2 de grosor
    assert geo.caja_envolvente(s.cuerpo(cid).forma)[0][1] == pytest.approx(-5)


@pytest.mark.parametrize("tipo", ["red", "nervio"])
@pytest.mark.parametrize("angulo", [-10, 10])
@pytest.mark.parametrize("profundidad", [None, 3])
@pytest.mark.parametrize("direccion,signo", [("simetrica", 0), ("lado1", 1), ("lado2", -1)])
def test_b213_llega_a_la_cara_oblicua_en_todo_el_espesor(tipo, angulo, profundidad, direccion, signo):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    from omnicad.nucleo import solidos_crear as sc

    piso = geo.rotar(geo.caja(40, 20, 2, (0, -10, -2)), (0, 0, 0), (1, 0, 0), angulo)
    curva = BRepBuilderAPI_MakeEdge(gp_Pnt(10, 0, 8), gp_Pnt(30, 0, 8)).Edge()
    normal = (0, 0, 1) if tipo == "red" else (0, 1, 0)
    pared = getattr(sc, tipo)(piso, [curva], normal, 2, extender=False, direccion=direccion,
                             profundidad=profundidad)
    assert geo.es_valida(pared)
    esperado = 120 if profundidad is not None else 320 - signo * 40 * math.tan(math.radians(angulo))
    assert geo.volumen(pared) == pytest.approx(esperado)
    assert geo.volumen(geo.booleano(pared, piso, "intersecar")) == pytest.approx(0, abs=1e-7)
    if profundidad is None:
        assert len(geo.solidos(geo.booleano(pared, piso, "unir"))) == 1


def test_nervio_con_desmoldeo_es_mas_fino_en_el_borde_libre():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)               # línea a z = 8: el nervio baja hasta el piso (6 mm)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, draft_angle=5)
    esperado = 36 * (6 * 2 + 2 * math.tan(math.radians(5)) * 18)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


def test_nervio_con_direccion_de_extraccion_explicita():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, draft_angle=5, pull_direction="Z")
    esperado = 36 * (6 * 2 + 2 * math.tan(math.radians(5)) * 18)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


@pytest.mark.parametrize("direccion", ["symmetric", "side1", "side2"])
@pytest.mark.parametrize("angulo,extraccion", [(-1, None), (1, "XY"), (1, "Z"), (5, None)])
def test_b215_nervio_diagonal_con_desmoldeo_negativo_o_extraccion_z(angulo, extraccion, direccion):
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=60, height=5, y=-30,
              anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=5, width=60, height=50, y=-30,
        anchor="corner", operation="join", target=cid)
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(25500)
    b = _linea(s, "XZ", 0, 35, 5, 5, 45)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid,
        draft_angle=angulo, pull_direction=extraccion, direction=direccion)
    # Triángulo de 600 mm²; profundidad media: 8 hacia la curva, 20/3 hacia z = 25.
    esperado = 1200 + (9600 if extraccion is None else 8000) * math.tan(math.radians(angulo))
    assert _aumento(s, cid, 25500) == pytest.approx(esperado, rel=1e-5)
    assert len(geo.solidos(s.cuerpo(cid).forma)) == 1


@pytest.mark.parametrize("direction,y_centro", [("side1", 9.0), ("side2", 11.0), ("symmetric", 10.0)])
def test_nervio_inicio_abajo_o_arriba(direction, y_centro):
    s, cid = _canal()
    antes = s.cuerpo(cid).forma
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid, direction=direction)
    nervio = geo.booleano(s.cuerpo(cid).forma, antes, "cortar")
    assert geo.volumen(nervio) == pytest.approx(36 * 6 * 2, rel=1e-5)
    assert geo.centro_masa(nervio)[1] == pytest.approx(y_centro, abs=1e-6)


def test_red_con_desmoldeo():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, draft_angle=5)
    esperado = 36 * (10 * 2 + 2 * math.tan(math.radians(5)) * 50)
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-3)


def test_b215_red_con_desmoldeo_negativo():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, draft_angle=-1)
    esperado = 36 * (20 - 100 * math.tan(math.radians(1)))
    assert _aumento(s, cid, antes) == pytest.approx(esperado, rel=1e-5)


def test_b215_red_curva_desmoldea_los_laterales_cilindricos():
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.GeomAbs import GeomAbs_Cone
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    from omnicad.nucleo import solidos_crear as sc

    base = geo.caja(40, 40, 2)
    base = geo.booleano(base, geo.caja(40, 2, 20, (0, 38, 0)), "unir")
    arco = GC_MakeArcOfCircle(gp_Pnt(12, 20, 12), gp_Pnt(20, 28, 12), gp_Pnt(28, 20, 12)).Value()
    pared = sc.red(base, [BRepBuilderAPI_MakeEdge(arco).Edge()], (0, 0, 1), 2,
                   extender=False, angulo_desmoldeo=1)
    assert geo.es_valida(pared)
    assert geo.volumen(pared) > math.pi * 8 * 2 * 10
    assert sum(BRepAdaptor_Surface(c).GetType() == GeomAbs_Cone for c in geo.caras(pared)) == 2


def test_red_sin_extender_las_curvas():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False)
    assert _aumento(s, cid, antes) == pytest.approx(20 * 10 * 2, rel=1e-5)


def test_red_con_empalme_redondea_las_juntas_con_la_placa():
    """Una red suelta de 20 mm sobre la placa de una L: la junta mide 2 · 20 de los lados más 2 · 2 de los extremos."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=60, width=40, height=4, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=60, width=2, height=20, y=38, anchor="corner", operation="join", target=cid)   # el fondo alto
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 14, 10, 20, 30, 20)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False)
    sin = _aumento(s, cid, antes)
    assert sin == pytest.approx(20 * 10 * 2, rel=1e-5)         # entre z = 4 y z = 14
    _ok(s, "undo")
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, extend_curves=False, fillet_radius=1)
    extra = _aumento(s, cid, antes) - sin
    assert extra == pytest.approx(44 * (1 - math.pi / 4), abs=1.5)


def test_red_con_empalme_en_el_canal_es_valida_y_suma_material():
    s, cid = _canal()
    antes = geo.volumen(s.cuerpo(cid).forma)
    b = _linea(s, "XY", 12, 10, 10, 30, 10)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid)
    sin = _aumento(s, cid, antes)
    _ok(s, "undo")
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, fillet_radius=1)
    assert _aumento(s, cid, antes) > sin + 20


def test_argumentos_invalidos():
    s, cid = _canal()
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    for args in ({"draft_angle": 60}, {"draft_angle": -50}, {"pull_direction": "no existe"}):
        r = api.llamar(s, "create_rib", dict(sketch=b, thickness=2, target=cid, **args))
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", args
    r = api.llamar(s, "create_web", dict(sketch=b, thickness=2, target=cid, fillet_radius=-1))
    assert not r["ok"]
