"""B-362: las curvas también dan un tope geométrico rápido a las asas de Extruir."""
import math
import time

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _ok(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _perfil(nombre, plano="XY"):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane=plano)
    if nombre in ("circulo", "anillo"):
        _ok(sesion, "draw_circle", radius=10)
        if nombre == "anillo":
            _ok(sesion, "draw_circle", radius=3)
    elif nombre == "ranura":
        _ok(sesion, "draw_slot", points=[[0, 0], [20, 0]], width=10)
    elif nombre == "elipse":
        _ok(sesion, "draw_ellipse", major_radius=30, minor_radius=10)
    else:
        _ok(sesion, "draw_rectangle", x1=0, y1=0, x2=40, y2=20)
        lineas = list(sesion.doc.estado_final.bocetos["op1"].boceto.curvas)
        for a, b in zip(lineas, lineas[1:] + lineas[:1], strict=True):
            _ok(sesion, "sketch_fillet", entity1=a, entity2=b, radius=3)
    perfiles = sesion.doc.estado_final.bocetos["op1"].perfiles
    cara = max((p.cara for p in perfiles), key=geo.area)
    return sesion, cara


@pytest.mark.parametrize("nombre", ["circulo", "ranura", "rectangulo", "elipse"])
def test_b362_tope_finito_y_rapido_para_curvas(nombre):
    sesion, cara = _perfil(nombre)
    inicio = time.perf_counter()
    adentro, afuera = sc.radios_conicidad([cara])
    tiempo = time.perf_counter() - inicio
    assert tiempo < 1, (nombre, tiempo)
    assert math.isfinite(adentro) and adentro > 0
    assert math.isinf(afuera)
    if nombre == "circulo":
        assert adentro / math.tan(math.radians(10)) == pytest.approx(56.7128, rel=0.01)
    elif nombre == "ranura":
        assert adentro == pytest.approx(5, rel=0.01)
    elif nombre == "rectangulo":
        assert adentro == pytest.approx(3, rel=0.01)  # primero se cierra el arco de la esquina
    resultado = _ok(sesion, "extrude", sketch="Boceto1", profile=0, distance=2)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(geo.area(cara) * 2, rel=1e-6)


@pytest.mark.parametrize("plano", ["XY", "XZ", "YZ"])
def test_b362_el_hueco_conserva_su_sentido_en_cualquier_plano(plano):
    _, cara = _perfil("anillo", plano)
    assert sc.radios_conicidad([cara]) == pytest.approx((3.5, 3), rel=0.01)


@pytest.mark.parametrize("nombre,distancia,angulo", [
    ("circulo", 55, -10), ("circulo", 58, -10),
    ("rectangulo", 20, -10), ("elipse", 1, -45),
])
def test_b362_el_error_distingue_el_cierre_del_fallo_anterior_del_kernel(nombre, distancia, angulo):
    sesion, _ = _perfil(nombre)
    respuesta = api.llamar(sesion, "extrude", {
        "sketch": "Boceto1", "profile": 0, "distance": distancia, "taper_angle": angulo,
    })
    assert not respuesta["ok"] and respuesta["error_kind"] == "OPERATION_FAILED"
    assert "El perfil se cierra aproximadamente a" in respuesta["mensaje"]
    if (nombre, distancia) in (("circulo", 55), ("elipse", 1)):
        assert "El kernel falla antes de ese cierre" in respuesta["mensaje"]
    else:
        assert "La distancia alcanza o supera ese cierre" in respuesta["mensaje"]
    assert not sesion.doc.estado_final.cuerpos  # la API conserva su transacción atómica
