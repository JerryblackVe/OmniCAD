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


def _caja_cerrada_hueca():
    """Caja 40³ cerrada, vaciada 2 mm: 64000 − 36³ = 17344 mm³."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=40, height=40, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "shell", body=cid, faces=[], thickness=2)
    return s, cid


@pytest.mark.parametrize("reverse,esperado", [(False, 18280.0), (True, 19000.0)])
def test_red_invertir_cambia_de_pared(reverse, esperado):
    """B-216 · «Cambiar dirección» (Flip Direction) manda la red a la otra pared. El boceto en y = 15 está a 13 mm de
    la pared de y = 2 y a 23 mm de la de y = 38: 17344 + 36·13·2 = 18280 sin invertir, 17344 + 36·23·2 = 19000
    invertida."""
    s, cid = _caja_cerrada_hueca()
    antes = s.cuerpo(cid).forma
    _ok(s, "create_construction_plane", plane="XZ", offset=-15, name="P15")
    b = _ok(s, "create_sketch", plane="P15")["sketch"]["id"]
    _ok(s, "draw_line", sketch=b, start_x=10, start_y=20, end_x=30, end_y=20)
    _ok(s, "create_web", sketch=b, thickness=2, target=cid, reverse=reverse)
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(esperado, rel=1e-4)
    (_, y0, _), (_, y1, _) = geo.caja_envolvente(geo.booleano(forma, antes, "cortar"))
    assert (round(y0), round(y1)) == ((15, 38) if reverse else (2, 15))      # la pared a la que llegó


def _caja_abierta():
    """Caja 40³ vaciada 2 mm con la cara y = 0 quitada (boca hacia −Y): 64000 − 36·36·38 = 14752 mm³, con un boceto
    adentro en y = 15 y la línea z = 20 de x 10 a 30."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=40, height=40, anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "shell", body=cid, faces="<Y", thickness=2)
    _ok(s, "create_construction_plane", plane="XZ", offset=-15, name="P15")
    b = _ok(s, "create_sketch", plane="P15")["sketch"]["id"]
    _ok(s, "draw_line", sketch=b, start_x=10, start_y=20, end_x=30, end_y=20)
    return s, cid, b


def test_red_invertir_hacia_la_boca_abierta_avisa():
    """B-216: con la boca abierta del otro lado, «Cambiar dirección» apunta al vacío y Fusion avisa. Sin invertir la
    red va a la pared del fondo: 14752 + 36·23·2 = 16408."""
    s, cid, b = _caja_abierta()
    _ok(s, "create_web", sketch=b, thickness=2, target=cid)
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(16408.0, rel=1e-4)
    _ok(s, "undo")
    r = api.llamar(s, "create_web", dict(sketch=b, thickness=2, target=cid, reverse=True))
    assert not r["ok"] and "no llega al cuerpo" in r["mensaje"], r
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(14752.0, rel=1e-4)   # el documento quedó como estaba


def _escuadra():
    """Escuadra de la auditoría: piso x 0..40 (y −30..30, z 0..5) + pared x 0..5 (z 0..50) = 25500 mm³, con un
    boceto XZ (en XZ la «y» del boceto es la Z del mundo)."""
    s = api.Sesion()
    cid = _ok(s, "create_box", length=40, width=60, height=5, x=0, y=-30, z=0,
              anchor="corner")["bodies_created"][0]["id"]
    _ok(s, "create_box", length=5, width=60, height=50, x=0, y=-30, z=0, anchor="corner", operation="join", target=cid)
    return s, cid, _ok(s, "create_sketch", plane="XZ")["sketch"]["id"]


@pytest.mark.parametrize("lineas", [[(35, 5, 5, 45)], [(35, 5, 5, 45), (30, 5, 5, 38.333333)]])
def test_nervio_con_varias_curvas_sueltas_hace_un_nervio_por_curva(lineas):
    """B-214: dos líneas sueltas dan un nervio por curva en UN paso (en la ayuda de Fusion «Create a rib» cuatro
    curvas hacen cuatro nervios). La segunda, (30,5)→(5,38,33), cae adentro del triángulo de la primera: la unión
    sigue siendo 600 mm² × 2 mm = 1200 mm³ sobre los 25500."""
    s, cid, b = _escuadra()
    for x1, z1, x2, z2 in lineas:
        _ok(s, "draw_line", sketch=b, start_x=x1, start_y=z1, end_x=x2, end_y=z2)
    _ok(s, "create_rib", sketch=b, thickness=2, target=cid)
    assert len([o for o in s.doc.operaciones if o.TIPO == "nervio"]) == 1
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(26700.0, rel=1e-4)


def test_argumentos_invalidos():
    s, cid = _canal()
    b = _linea(s, "XZ", -10, 10, 8, 30, 8)
    for args in ({"draft_angle": 60}, {"draft_angle": -50}, {"pull_direction": "no existe"}):
        r = api.llamar(s, "create_rib", dict(sketch=b, thickness=2, target=cid, **args))
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", args
    r = api.llamar(s, "create_web", dict(sketch=b, thickness=2, target=cid, fillet_radius=-1))
    assert not r["ok"]
