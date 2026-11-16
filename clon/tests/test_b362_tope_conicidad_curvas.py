"""B-362: las curvas también dan un tope geométrico rápido a las asas de Extruir."""
import math
import time

import numpy as np
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


def test_b508_el_circulo_pasado_el_cierre_es_un_cono():
    sesion, _ = _perfil("circulo")
    assert api.llamar(sesion, "extrude", {"sketch": "Boceto1", "profile": 0, "distance": 58, "taper_angle": -10})["ok"]
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.volumen(forma) == pytest.approx(math.pi * 100 * 10 / math.tan(math.radians(10)) / 3, rel=1e-3)


# Un empalme de R3 o la punta de la elipse se cierran antes que el perfil entero: sigue el error (no hay vértice).
@pytest.mark.parametrize("nombre,distancia,angulo", [("rectangulo", 20, -10), ("elipse", 3, -45)])
def test_b362_pasado_el_cierre_el_error_lo_indica(nombre, distancia, angulo):
    sesion, _ = _perfil(nombre)
    respuesta = api.llamar(sesion, "extrude", {
        "sketch": "Boceto1", "profile": 0, "distance": distancia, "taper_angle": angulo,
    })
    assert not respuesta["ok"] and respuesta["error_kind"] == "OPERATION_FAILED"
    assert "El perfil se cierra aproximadamente a" in respuesta["mensaje"]
    assert "La distancia alcanza o supera ese cierre" in respuesta["mensaje"]
    assert not sesion.doc.estado_final.cuerpos  # la API conserva su transacción atómica


def _volumen_conico(area, perimetro, distancia, angulo):
    """Volumen exacto de inclinar un perfil convexo y suave (Steiner: A(s) = A + P·s + π·s²)."""
    t = math.tan(math.radians(angulo))
    return area * distancia + perimetro * t * distancia ** 2 / 2 + math.pi * t * t * distancia ** 3 / 3


@pytest.mark.parametrize("nombre,distancia,angulo", [
    ("circulo", 56.5, -10), ("circulo", 13, -37), ("circulo", 5.7, -60),   # el kernel fallaba desde el 96 % del cierre
    ("elipse", 2.8, -45), ("elipse", 3, 10),                             # y con cualquier elipse
])
def test_b362_la_conicidad_curva_llega_hasta_el_cierre(nombre, distancia, angulo):
    from scipy.special import ellipe
    sesion, cara = _perfil(nombre)
    perimetro = 20 * math.pi if nombre == "circulo" else 4 * 30 * ellipe(1 - (10 / 30) ** 2)
    resultado = _ok(sesion, "extrude", sketch="Boceto1", profile=0, distance=distancia, taper_angle=angulo)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(_volumen_conico(geo.area(cara), perimetro, distancia, angulo), rel=1e-5)


@pytest.mark.parametrize("angulo", [-10, 10])
def test_b362_el_lateral_reglado_agranda_el_hueco_al_achicar_el_material(angulo):
    _, cara = _perfil("anillo")
    forma = sc._prisma_curvo_inclinado(cara, np.array([0, 0, 1.0]), 5, angulo)
    t = math.tan(math.radians(angulo))
    assert geo.es_valida(forma)
    # R10 menos R3: el hueco crece cuando el exterior se achica, así el perímetro total suma
    assert geo.volumen(forma) == pytest.approx(91 * math.pi * 5 + t * 25 * 13 * math.pi, rel=1e-6)


def test_b362_las_letras_de_splines_se_inclinan_y_frenan_donde_se_cierran():
    sesion = api.Sesion()
    boceto = _ok(sesion, "sketch_from_spec", entities=[{"type": "text", "text": "O", "height": 20}])["sketch"]["id"]
    caras = [p.cara for p in sesion.doc.estado_final.bocetos[boceto].perfiles]
    assert caras
    for cara in caras:
        forma = sc._prisma(cara, (0, 0, 1), 3, -10)                 # DraftAngle fallaba con cualquier distancia
        assert geo.es_valida(forma)
        # achicar el contorno s quita como mucho perímetro·s de área (los dos lazos de la O lo igualan)
        minimo = geo.area(cara) * 3 - geo.longitud(cara) * math.tan(math.radians(10)) * 9 / 2
        assert 0.99 * minimo < geo.volumen(forma) < geo.area(cara) * 3
        with pytest.raises(geo.ErrorGeometria):
            sc._prisma(cara, (0, 0, 1), 60, -10)                    # 60·tan 10° = 10,6 mm: el trazo ya se cerró


def test_b362_la_pared_delgada_del_hueco_de_un_boceto_no_se_pierde():
    _, cara = _perfil("anillo")          # el hueco de una cara de boceto viene al revés que el de una booleana
    bandas = sc._bandas_cerradas([cara], 1.0, "lado1")
    assert sorted(geo.area(b) for b in bandas) == pytest.approx([7 * math.pi, 21 * math.pi], rel=1e-6)


def test_b362_el_lateral_reglado_frena_donde_el_hueco_alcanza_el_borde():
    _, cara = _perfil("anillo")          # pared de 7 mm: se cierra a 3,5 / tan 10° = 19,85 mm
    assert geo.es_valida(sc._prisma_curvo_inclinado(cara, np.array([0, 0, 1.0]), 19.5, -10))
    with pytest.raises(geo.ErrorGeometria, match="cierra parte del perfil"):
        sc._prisma_curvo_inclinado(cara, np.array([0, 0, 1.0]), 20.5, -10)
