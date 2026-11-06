"""B-206: conicidad desde el objeto inclinado, conservando su plano neutro."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta.get("mensaje", respuesta)
    return respuesta["result"]


@pytest.mark.parametrize("angulo,distancia", [(5, 10), (-5, 10), (5, -10)])
def test_b206_rectangulo_conserva_el_plano_neutro_y_el_volumen(angulo, distancia):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_rectangle", sketch="Perfil", x1=-10, y1=-5, x2=10, y2=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "extrude", sketch="Perfil", start="object", start_object="Inicio",
                    distance=distancia, taper_angle=angulo)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    # Integración de las secciones s = z - y·tan(30°). Cada lateral forma el ángulo pedido con Z.
    t, k, h = math.tan(math.radians(angulo)), math.tan(math.radians(30)), abs(distancia)
    q = t / math.sqrt(1 - (k * t) ** 2)
    r = t / (1 - (k * t) ** 2)
    esperado = 200 * h + (20 * r + 10 * q) * h ** 2 + 4 * q * r * h ** 3 / 3
    assert geo.volumen_exacto(forma) == pytest.approx(esperado, rel=1e-8)
    planos = [geo.plano_de_cara(c) for c in geo.caras(forma)]
    tapas = [p for p in planos if abs(abs(float(p.normal[2])) - math.cos(math.radians(30))) < 1e-7]
    assert len(tapas) == 2
    assert sorted(float(p.origen[2] - k * p.origen[1]) for p in tapas) == pytest.approx(
        sorted([0, distancia]), abs=1e-6)


@pytest.mark.xfail(strict=True, reason="B-206 Parcial: círculo inclinado con conicidad (DraftAngle no admite el lateral elíptico)")
def test_b206_circulo_inclinado_con_conicidad_es_un_solido_valido():
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_circle", sketch="Perfil", radius=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "extrude", sketch="Perfil", start="object", start_object="Inicio",
                    distance=10, taper_angle=5)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma) > 250 * math.pi
    plano = geo.Plano.desde_marco((0, 0, 0), (0, -0.5, math.cos(math.radians(30))), (1, 0, 0))
    base = [c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is not None
            and abs(float(p.normal @ plano.normal)) > 1 - 1e-8
            and abs(float(p.origen @ plano.normal)) < 1e-7]
    assert len(base) == 1
    assert geo.area(base[0]) == pytest.approx(25 * math.pi / math.cos(math.radians(30)), rel=1e-7)
